"""Transport-agnostic operations shared by the HTTP API and the MCP server."""

from __future__ import annotations

from typing import Any, Optional

from ..common.scraper import FALLBACK_ORDER, UnifiedScraper
from ..common.urlguard import validate_url

MAX_BATCH = 100
MAX_CONCURRENCY = 20
MAX_MARKDOWN_CHARS = 200_000


class ScrapeService:
    def __init__(self, scraper: Optional[UnifiedScraper] = None):
        self._scraper = scraper

    @property
    def scraper(self) -> UnifiedScraper:
        if self._scraper is None:
            self._scraper = UnifiedScraper()
        return self._scraper

    @staticmethod
    def _check_engine(engine: str) -> str:
        if engine != "auto" and engine not in FALLBACK_ORDER:
            raise ValueError(f"unknown engine {engine!r}; choose auto or one of {FALLBACK_ORDER}")
        return engine

    @staticmethod
    def _trim(result: dict[str, Any], max_chars: int) -> dict[str, Any]:
        md = result.get("markdown") or ""
        if len(md) > max_chars:
            result = {**result, "markdown": md[:max_chars], "truncated": True, "total_chars": len(md)}
        return result

    async def health(self) -> dict[str, Any]:
        engines = await self.scraper.check_engines()
        guard = getattr(self.scraper, "paid_guard", None)
        return {
            "engines": engines,
            "order": getattr(self.scraper, "engine_order", FALLBACK_ORDER),
            "respect_robots": getattr(self.scraper, "robots", None) is not None,
            "paid_budget": {"used_today": guard.budget.used(), "daily_limit": guard.budget.limit} if guard else None,
        }

    async def scrape(self, url: str, engine: str = "auto", save: bool = False, max_chars: int = MAX_MARKDOWN_CHARS) -> dict[str, Any]:
        await validate_url(url)
        result = await self.scraper.scrape(url, engine=self._check_engine(engine), save=save)
        return self._trim(result, max_chars)

    async def batch(self, urls: list[str], engine: str = "auto", concurrency: int = 5, save: bool = False,
                    max_chars: int = 20_000) -> list[dict[str, Any]]:
        if not urls:
            return []
        if len(urls) > MAX_BATCH:
            raise ValueError(f"at most {MAX_BATCH} URLs per batch")
        for u in urls:
            await validate_url(u)
        results = await self.scraper.scrape_batch(
            urls, engine=self._check_engine(engine), concurrency=max(1, min(concurrency, MAX_CONCURRENCY)), save=save,
        )
        return [self._trim(r, max_chars) for r in results]

    async def crawl(self, url: str, limit: int = 20, max_depth: int = 2) -> dict[str, Any]:
        await validate_url(url)
        return await self.scraper.crawl(url, limit=max(1, min(limit, 500)), max_depth=max(1, min(max_depth, 5)))

    async def map_site(self, url: str) -> dict[str, Any]:
        await validate_url(url)
        return await self.scraper.map_site(url)

    async def close(self) -> None:
        if self._scraper is not None:
            await self._scraper.close()

