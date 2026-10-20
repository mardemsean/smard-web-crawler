"""Unified scraper interface that routes to Crawl4AI or Firecrawl."""

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

logger = logging.getLogger(__name__)

Engine = Literal["crawl4ai", "firecrawl", "auto"]


class UnifiedScraper:
    """Routes scraping requests to the best available engine."""

    def __init__(self):
        self.crawl4ai = Crawl4AIClient()
        self.firecrawl = FirecrawlClient()
        self._engine_health: dict[str, bool] = {}

    async def check_engines(self) -> dict[str, bool]:
        c4ai, fc = await asyncio.gather(
            self.crawl4ai.health(),
            self.firecrawl.health(),
        )
        self._engine_health = {"crawl4ai": c4ai, "firecrawl": fc}
        return self._engine_health

    async def scrape(
        self,
        url: str,
        *,
        engine: Engine = "auto",
        strategy: Optional[str] = None,
        stealth: bool = True,
        save: bool = True,
    ) -> dict:
        """Scrape a URL with the specified or best available engine."""
        if engine == "auto":
            engine = await self._pick_engine()

        start = time.monotonic()

        if engine == "crawl4ai":
            result = await self.crawl4ai.scrape(url, strategy=strategy, stealth=stealth)
        else:
            result = await self.firecrawl.scrape(url)

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
        """Scrape multiple URLs with concurrency control."""
        semaphore = asyncio.Semaphore(concurrency)
        results = []

        async def _do(url: str):
            async with semaphore:
                if delay_between > 0 and results:
                    await asyncio.sleep(delay_between)
                return await self.scrape(url, engine=engine)

        tasks = [_do(u) for u in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [
            r if isinstance(r, dict) else {"url": urls[i], "error": str(r), "success": False}
            for i, r in enumerate(results)
        ]

    async def _pick_engine(self) -> str:
        if not self._engine_health:
            await self.check_engines()
        if self._engine_health.get("crawl4ai"):
            return "crawl4ai"
        if self._engine_health.get("firecrawl"):
            return "firecrawl"
        raise RuntimeError("No scraping engine available. Start containers with: docker compose up -d")

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
