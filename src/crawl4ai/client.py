"""Crawl4AI client with stealth mode and proxy support."""

import asyncio
import json
import random
import time
from pathlib import Path
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..common.config import config


class Crawl4AIClient:
    """Client for Crawl4AI server (Docker) or direct library usage."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or config.crawl4ai_base_url).rstrip("/")
        self.strategy = config.crawl4ai_strategy

    async def scrape(
        self,
        url: str,
        *,
        strategy: Optional[str] = None,
        stealth: bool = True,
        proxy: Optional[str] = None,
        wait_for: Optional[str] = None,
        timeout: int = 30000,
    ) -> dict:
        """Scrape a URL and return markdown + metadata via the Crawl4AI server."""
        proxy_url = proxy or (config.proxy.url if config.proxy.enabled else None)

        payload = {
            "urls": [url],
            "browser_config": {
                "headless": config.browser.headless,
                "viewport_width": config.browser.viewport_width,
                "viewport_height": config.browser.viewport_height,
            },
            "crawler_params": {
                "word_count_threshold": 10,
                "extraction_strategy": strategy or self.strategy,
                "verbose": False,
            },
        }

        if proxy_url:
            payload["browser_config"]["proxy"] = proxy_url

        if stealth and config.stealth.enabled:
            payload["browser_config"]["stealth_mode"] = True
            payload["browser_config"]["simulate_user"] = config.stealth.human_simulation

        if wait_for:
            payload["crawler_params"]["wait_for"] = wait_for

        return await self._request(payload, timeout)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def _request(self, payload: dict, timeout: int) -> dict:
        async with httpx.AsyncClient(timeout=timeout / 1000 + 10) as client:
            resp = await client.post(f"{self.base_url}/crawl", json=payload)
            resp.raise_for_status()
            data = resp.json()

        if not data.get("results"):
            raise ValueError(f"No results from Crawl4AI: {data}")

        result = data["results"][0]
        return {
            "url": result.get("url", payload["urls"][0]),
            "markdown": result.get("markdown", ""),
            "cleaned_html": result.get("cleaned_html", ""),
            "metadata": result.get("metadata", {}),
            "success": result.get("success", True),
            "extraction_strategy": payload["crawler_params"]["extraction_strategy"],
        }

    async def scrape_direct(
        self,
        url: str,
        *,
        strategy: Optional[str] = None,
        stealth: bool = True,
    ) -> dict:
        """Scrape using the crawl4ai library directly (no server required)."""
        try:
            from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
        except ImportError:
            raise RuntimeError("crawl4ai not installed. Run: pip install crawl4ai")

        browser_cfg = BrowserConfig(
            headless=config.browser.headless,
            viewport_width=config.browser.viewport_width,
            viewport_height=config.browser.viewport_height,
        )

        if config.proxy.enabled:
            browser_cfg.proxy = config.proxy.url

        run_cfg = CrawlerRunConfig(
            word_count_threshold=10,
        )

        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            result = await crawler.arun(url=url, config=run_cfg)

        return {
            "url": url,
            "markdown": result.markdown or "",
            "cleaned_html": result.cleaned_html or "",
            "metadata": {"title": result.metadata.get("title", "") if result.metadata else ""},
            "success": result.success,
            "extraction_strategy": strategy or self.strategy,
        }

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/health")
                return resp.status_code == 200
        except Exception:
            return False
