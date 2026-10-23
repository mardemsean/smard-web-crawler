"""Unified scraper with configurable fallback: self-hosted engines → Site Unblocker → Web Data API.

Default order (ENGINE_ORDER): obscura, crawl4ai, firecrawl, cloakbrowser, site_unblocker, web_data_api.

Resilience patterns (rota-inspired):
- Retry intra-engine: variant params within the same engine before escalating
- Periodic liveness: recheck engine health on failure and on a timer
- Pool cascade with recheck: re-verify failed engines during long batches
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

import aiofiles

from .budget import BudgetExceeded, PaidGuard
from .config import DEFAULT_ENGINE_ORDER, config
from .robots import RobotsChecker, RobotsDisallowed
from ..browsers.client import CloakBrowserClient, ObscuraClient
from ..crawl4ai.client import Crawl4AIClient
from ..firecrawl.client import FirecrawlClient
from ..decodo.site_unblocker import SiteUnblockerClient
from ..decodo.web_data_api import WebDataAPIClient

logger = logging.getLogger(__name__)

Engine = Literal["obscura", "crawl4ai", "firecrawl", "cloakbrowser", "site_unblocker", "web_data_api", "auto"]

FALLBACK_ORDER = DEFAULT_ENGINE_ORDER.split(",")

SELF_HOSTED_ENGINES = {"obscura", "crawl4ai", "firecrawl", "cloakbrowser"}
PAID_ENGINES = {"site_unblocker", "web_data_api"}

LIVENESS_INTERVAL = 300  # seconds between automatic health rechecks

BATCH_RECHECK_INTERVAL = 10  # items between failed-engine rechecks in batch mode

_INTRA_ENGINE_VARIANTS: dict[str, list[dict]] = {
    "obscura": [
        {"wait_for": 3000},
    ],
    "cloakbrowser": [
        {"wait_for": 3000},
    ],
    "crawl4ai": [
        {"strategy": "bm25"},
        {"strategy": "semantic"},
    ],
    "firecrawl": [
        {"wait_for": 5000},
    ],
    "site_unblocker": [
        {"js_render": False},
    ],
    "web_data_api": [
        {"proxy_pool": "premium"},
    ],
}


class UnifiedScraper:
    """Routes scraping requests through the configured fallback chain.

    Level 1: Self-hosted engines (Obscura / Crawl4AI / Firecrawl / CloakBrowser) + residential proxy
    Level 2: Decodo Site Unblocker (proxy-like, managed anti-bot)
    Level 3: Decodo Web Data API (REST, fully managed)
    """

    def __init__(self):
        self.obscura = ObscuraClient()
        self.crawl4ai = Crawl4AIClient()
        self.firecrawl = FirecrawlClient()
        self.cloakbrowser = CloakBrowserClient()
        self.site_unblocker = SiteUnblockerClient()
        self.web_data_api = WebDataAPIClient()
        self.engine_order: list[str] = [e for e in config.engine_order if e in FALLBACK_ORDER]
        self.robots: Optional[RobotsChecker] = (
            RobotsChecker(config.robots_user_agent) if config.respect_robots else None
        )
        self.paid_guard: Optional[PaidGuard] = PaidGuard(
            config.budget.max_rps, config.budget.daily_limit, config.budget.state_file,
        )
        self._engine_health: dict[str, bool] = {}
        self._last_health_check: float = 0
        self._failed_engines: set[str] = set()

    def _engines_present(self) -> list[str]:
        return [e for e in FALLBACK_ORDER if hasattr(self, e)]

    async def check_engines(self) -> dict[str, bool]:
        names = self._engines_present()
        results = await asyncio.gather(
            *(getattr(self, e).health() for e in names), return_exceptions=True,
        )
        self._engine_health = {e: r is True for e, r in zip(names, results)}
        self._last_health_check = time.monotonic()
        self._failed_engines = {k for k, v in self._engine_health.items() if not v}
        return self._engine_health

    async def _maybe_refresh_health(self, force: bool = False) -> None:
        """Recheck engine health if stale or forced."""
        elapsed = time.monotonic() - self._last_health_check
        if force or elapsed > LIVENESS_INTERVAL or not self._engine_health:
            await self.check_engines()

    async def _recheck_failed_engines(self) -> list[str]:
        """Re-verify previously-failed engines; return any that recovered."""
        if not self._failed_engines:
            return []

        recovered: list[str] = []
        checks: dict[str, asyncio.Task] = {}
        for eng in list(self._failed_engines):
            client = getattr(self, eng)
            checks[eng] = asyncio.ensure_future(client.health())

        results = await asyncio.gather(*checks.values(), return_exceptions=True)
        for eng, result in zip(checks.keys(), results):
            if result is True:
                self._engine_health[eng] = True
                self._failed_engines.discard(eng)
                recovered.append(eng)
                logger.info(f"[liveness] {eng} recovered")

        if recovered:
            self._last_health_check = time.monotonic()
        return recovered

    async def scrape(
        self,
        url: str,
        *,
        engine: Engine = "auto",
        strategy: Optional[str] = None,
        stealth: bool = True,
        js_render: bool = True,
        save: bool = True,
        fallback: bool = True,
        intra_retry: bool = True,
    ) -> dict:
        """Scrape a URL with automatic engine selection and fallback.

        When intra_retry=True (default), each engine tries variant parameters
        before the fallback chain escalates to the next engine.
        Raises RobotsDisallowed when robots.txt forbids the URL (RESPECT_ROBOTS=true).
        """
        robots = getattr(self, "robots", None)
        if robots is not None and not await robots.allowed(url):
            raise RobotsDisallowed(f"robots.txt disallows {url}")

        if engine != "auto":
            return await self._scrape_with(
                engine, url, strategy=strategy, stealth=stealth,
                js_render=js_render, save=save,
            )

        await self._maybe_refresh_health()
        engines = await self._fallback_order()
        last_error = None

        for eng in engines:
            # Primary attempt with caller's parameters
            try:
                result = await self._scrape_with(
                    eng, url, strategy=strategy, stealth=stealth,
                    js_render=js_render, save=save,
                )
                if result.get("success") and result.get("markdown"):
                    return result
                logger.warning(f"[{eng}] {url}: empty result, trying variants")
            except BudgetExceeded as e:
                last_error = e
                logger.warning(f"[{eng}] {url}: {e}; skipping paid engine")
                continue
            except Exception as e:
                last_error = e
                logger.warning(f"[{eng}] {url}: {e}")
                if not fallback:
                    raise

            # Intra-engine retry: try variant params before escalating
            if intra_retry and eng in _INTRA_ENGINE_VARIANTS:
                for variant in _INTRA_ENGINE_VARIANTS[eng]:
                    try:
                        result = await self._scrape_with(
                            eng, url,
                            strategy=variant.get("strategy", strategy),
                            stealth=stealth,
                            js_render=variant.get("js_render", js_render),
                            save=save,
                            wait_for=variant.get("wait_for", 0),
                            proxy_pool=variant.get("proxy_pool", "standard"),
                        )
                        if result.get("success") and result.get("markdown"):
                            logger.info(f"[{eng}] {url}: succeeded with variant {variant}")
                            return result
                    except BudgetExceeded as e:
                        last_error = e
                        break
                    except Exception as e:
                        last_error = e
                        logger.warning(f"[{eng}] {url} variant {variant}: {e}")

            # Mark engine failed after all intra-engine attempts exhausted
            self._failed_engines.add(eng)
            self._engine_health[eng] = False

        raise RuntimeError(f"All engines failed for {url}. Last error: {last_error}")

    async def _scrape_with(
        self,
        engine: str,
        url: str,
        *,
        strategy: Optional[str] = None,
        stealth: bool = True,
        js_render: bool = True,
        save: bool = True,
        wait_for: int = 0,
        proxy_pool: str = "standard",
    ) -> dict:
        guard = getattr(self, "paid_guard", None)
        if engine in PAID_ENGINES and guard is not None:
            await guard.acquire()

        start = time.monotonic()

        if engine == "obscura":
            result = await self.obscura.scrape(url, wait_for=wait_for)
        elif engine == "cloakbrowser":
            result = await self.cloakbrowser.scrape(url, wait_for=wait_for)
        elif engine == "crawl4ai":
            result = await self.crawl4ai.scrape(url, strategy=strategy, stealth=stealth)
        elif engine == "firecrawl":
            result = await self.firecrawl.scrape(url, wait_for=wait_for)
        elif engine == "site_unblocker":
            result = await self.site_unblocker.scrape(url, js_render=js_render, markdown=True)
        elif engine == "web_data_api":
            result = await self.web_data_api.scrape(
                url, markdown=True, js_render=js_render, proxy_pool=proxy_pool,
            )
        else:
            raise ValueError(f"Unknown engine: {engine}")

        elapsed = time.monotonic() - start
        result["engine"] = engine
        result["elapsed_ms"] = round(elapsed * 1000)

        if save and result.get("markdown"):
            result["saved_path"] = await self._save(url, result)

        logger.info(f"[{engine}] {url} -> {len(result.get('markdown', ''))} chars in {result['elapsed_ms']}ms")
        return result

    async def scrape_batch(
        self,
        urls: list[str],
        *,
        engine: Engine = "auto",
        concurrency: int = 5,
        delay_between: float = 0,
        recheck_interval: int = BATCH_RECHECK_INTERVAL,
        save: bool = True,
    ) -> list[dict]:
        """Scrape multiple URLs with concurrency control, fallback, and pool cascade recheck."""
        semaphore = asyncio.Semaphore(concurrency)
        completed_count = 0
        lock = asyncio.Lock()

        async def _do(url: str, index: int) -> dict:
            nonlocal completed_count
            async with semaphore:
                if delay_between > 0 and completed_count > 0:
                    await asyncio.sleep(delay_between)

                # Pool cascade: periodically recheck failed engines
                async with lock:
                    if (
                        completed_count > 0
                        and completed_count % recheck_interval == 0
                        and self._failed_engines
                    ):
                        recovered = await self._recheck_failed_engines()
                        if recovered:
                            logger.info(
                                f"[batch] engines recovered at item {completed_count}: {recovered}"
                            )

                try:
                    result = await self.scrape(url, engine=engine, save=save)
                except Exception as e:
                    result = {"url": url, "error": str(e), "success": False}

                async with lock:
                    completed_count += 1

                return result

        tasks = [_do(u, i) for i, u in enumerate(urls)]
        return list(await asyncio.gather(*tasks))

    async def crawl(
        self,
        url: str,
        *,
        limit: int = 50,
        max_depth: int = 2,
    ) -> dict:
        """Multi-page crawl with fallback: Firecrawl self-hosted → Web Data API /crawl."""
        try:
            if self._engine_health.get("firecrawl", True):
                return await self.firecrawl.crawl(url, limit=limit, max_depth=max_depth)
        except Exception as e:
            logger.warning(f"[firecrawl] crawl failed: {e}")

        if self.web_data_api.enabled:
            return await self.web_data_api.crawl(url, limit=limit, max_depth=max_depth)

        raise RuntimeError("No crawl engine available")

    async def map_site(self, url: str) -> dict:
        """Map site URLs via Web Data API /map."""
        if not self.web_data_api.enabled:
            raise RuntimeError("Web Data API not configured — set DECODO_API_KEY")
        return await self.web_data_api.map_site(url)

    async def _fallback_order(self) -> list[str]:
        if not self._engine_health:
            await self.check_engines()

        order = []
        for eng in getattr(self, "engine_order", FALLBACK_ORDER):
            if eng in SELF_HOSTED_ENGINES:
                if self._engine_health.get(eng):
                    order.append(eng)
            elif eng == "site_unblocker":
                if config.site_unblocker.enabled:
                    order.append(eng)
            elif eng == "web_data_api":
                if config.decodo_api.enabled:
                    order.append(eng)

        if not order:
            raise RuntimeError(
                "No scraping engine available. "
                "Start containers (docker compose up -d), enable CLOAKBROWSER_ENABLED, "
                "or configure SITE_UNBLOCKER_URL / DECODO_API_KEY"
            )
        return order

    async def close(self) -> None:
        for eng in ("obscura", "cloakbrowser"):
            client = getattr(self, eng, None)
            if client is not None and hasattr(client, "close"):
                await client.close()

    async def _save(self, url: str, result: dict) -> str:
        output_dir = config.output.dir
        output_dir.mkdir(parents=True, exist_ok=True)

        safe_name = url.replace("https://", "").replace("http://", "").replace("/", "_").replace("?", "_")[:120]
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{ts}_{safe_name}.md"
        filepath = output_dir / filename

        content = result["markdown"]
        if config.output.include_meta:
            meta = (
                f"---\n"
                f"source: {url}\n"
                f"engine: {result.get('engine', 'unknown')}\n"
                f"scraped_at: {datetime.now(timezone.utc).isoformat()}\n"
                f"elapsed_ms: {result.get('elapsed_ms', 0)}\n"
                f"chars: {len(content)}\n"
                f"---\n\n"
            )
            content = meta + content

        async with aiofiles.open(filepath, "w") as f:
            await f.write(content)

        return str(filepath)
