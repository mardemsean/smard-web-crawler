"""Unified scraper with three-level fallback: self-hosted → Site Unblocker → Web Data API."""

import asyncio
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

import aiofiles

from .config import config
from ..crawl4ai.client import Crawl4AIClient
from ..firecrawl.client import FirecrawlClient
from ..decodo.site_unblocker import SiteUnblockerClient
from ..decodo.web_data_api import WebDataAPIClient

logger = logging.getLogger(__name__)

Engine = Literal["crawl4ai", "firecrawl", "site_unblocker", "web_data_api", "auto"]

FALLBACK_ORDER = ["crawl4ai", "firecrawl", "site_unblocker", "web_data_api"]


class UnifiedScraper:
    """Routes scraping requests through a three-level fallback chain.

    Level 1: Self-hosted engines (Crawl4AI / Firecrawl) + residential proxy
    Level 2: Decodo Site Unblocker (proxy-like, managed anti-bot)
    Level 3: Decodo Web Data API (REST, fully managed)
    """

    def __init__(self):
        self.crawl4ai = Crawl4AIClient()
        self.firecrawl = FirecrawlClient()
        self.site_unblocker = SiteUnblockerClient()
        self.web_data_api = WebDataAPIClient()
        self._engine_health: dict[str, bool] = {}

    async def check_engines(self) -> dict[str, bool]:
        c4ai, fc, su, wda = await asyncio.gather(
            self.crawl4ai.health(),
            self.firecrawl.health(),
            self.site_unblocker.health(),
            self.web_data_api.health(),
        )
        self._engine_health = {
            "crawl4ai": c4ai,
            "firecrawl": fc,
            "site_unblocker": su,
            "web_data_api": wda,
        }
        return self._engine_health

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
    ) -> dict:
        """Scrape a URL with automatic engine selection and fallback."""
        if engine != "auto":
            return await self._scrape_with(engine, url, strategy=strategy, stealth=stealth, js_render=js_render, save=save)

        engines = await self._fallback_order()
        last_error = None

        for eng in engines:
            try:
                result = await self._scrape_with(eng, url, strategy=strategy, stealth=stealth, js_render=js_render, save=save)
                if result.get("success") and result.get("markdown"):
                    return result
                logger.warning(f"[{eng}] {url}: empty result, trying next engine")
            except Exception as e:
                last_error = e
                logger.warning(f"[{eng}] {url}: {e}, trying next engine")
                if not fallback:
                    raise

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
    ) -> dict:
        start = time.monotonic()

        if engine == "crawl4ai":
            result = await self.crawl4ai.scrape(url, strategy=strategy, stealth=stealth)
        elif engine == "firecrawl":
            result = await self.firecrawl.scrape(url)
        elif engine == "site_unblocker":
            result = await self.site_unblocker.scrape(url, js_render=js_render, markdown=True)
        elif engine == "web_data_api":
            result = await self.web_data_api.scrape(url, markdown=True, js_render=js_render)
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
    ) -> list[dict]:
        """Scrape multiple URLs with concurrency control and fallback."""
        semaphore = asyncio.Semaphore(concurrency)
        results: list[dict] = []

        async def _do(url: str):
            async with semaphore:
                if delay_between > 0 and results:
                    await asyncio.sleep(delay_between)
                return await self.scrape(url, engine=engine)

        tasks = [_do(u) for u in urls]
        gathered = await asyncio.gather(*tasks, return_exceptions=True)

        return [
            r if isinstance(r, dict) else {"url": urls[i], "error": str(r), "success": False}
            for i, r in enumerate(gathered)
        ]

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
        for eng in FALLBACK_ORDER:
            if eng in ("crawl4ai", "firecrawl"):
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
                "Start containers (docker compose up -d) or configure SITE_UNBLOCKER_URL / DECODO_API_KEY"
            )
        return order

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
