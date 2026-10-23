"""Decodo Web Data API client — REST API for /scrape, /crawl, /map endpoints."""

import asyncio
import logging
import time
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..common.config import config

logger = logging.getLogger(__name__)


class WebDataAPIClient:
    """Fallback level 3: Decodo Web Data API (fully managed scraping)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key or config.decodo_api_key
        self.base_url = (base_url or config.decodo_api_url).rstrip("/")

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def scrape(
        self,
        url: str,
        *,
        markdown: bool = True,
        js_render: bool = False,
        proxy_pool: str = "standard",
        geo: Optional[str] = None,
        timeout: int = 60000,
    ) -> dict:
        """Scrape a single URL via /v1/scrape."""
        payload: dict = {"url": url}
        if markdown:
            payload["markdown"] = True
        if js_render:
            payload["headless"] = "html"
        if proxy_pool != "premium":
            payload["proxy_pool"] = proxy_pool
        if geo:
            payload["geo"] = geo

        async with httpx.AsyncClient(timeout=timeout / 1000 + 15) as client:
            resp = await client.post(
                f"{self.base_url}/scrape",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results", [])
        if not results:
            raise ValueError(f"No results from Web Data API: {data}")

        result = results[0]
        content = result.get("content", "")
        is_markdown = markdown and not content.strip().startswith("<")

        return {
            "url": url,
            "markdown": content if is_markdown else "",
            "html": content if not is_markdown else "",
            "success": True,
            "metadata": {
                "task_id": result.get("task_id"),
                "status_code": result.get("status_code"),
                "proxy_pool": proxy_pool,
                "js_rendered": js_render,
            },
        }

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=3, max=15))
    async def crawl(
        self,
        url: str,
        *,
        limit: int = 50,
        max_depth: int = 2,
        js_retry: bool = True,
        select_paths: Optional[list[str]] = None,
        callback_url: Optional[str] = None,
        timeout: int = 300000,
    ) -> dict:
        """Start a crawl job via /v1/crawl and poll until complete."""
        payload: dict = {
            "url": url,
            "limit": limit,
            "max_depth": max_depth,
        }
        if js_retry:
            payload["JS_retry"] = True
        if select_paths:
            payload["select_paths"] = select_paths
        if callback_url:
            payload["callback_url"] = callback_url

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/crawl",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            job = resp.json()

        crawl_id = job.get("crawl_id")
        if not crawl_id:
            raise ValueError(f"No crawl_id returned: {job}")

        if callback_url:
            return {"crawl_id": crawl_id, "status": "pending", "success": True}

        return await self._poll_crawl(crawl_id, timeout)

    async def _poll_crawl(self, crawl_id: str, timeout: int) -> dict:
        deadline = time.time() + timeout / 1000
        async with httpx.AsyncClient(timeout=15) as client:
            while time.time() < deadline:
                resp = await client.get(
                    f"{self.base_url}/crawl/{crawl_id}?type=content",
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()

                if data.get("status") == "done":
                    results = data.get("results", [])
                    return {
                        "crawl_id": crawl_id,
                        "total": data.get("completed", len(results)),
                        "pages": [
                            {
                                "url": r.get("url", ""),
                                "markdown": r.get("content", ""),
                                "metadata": r.get("metadata", {}),
                            }
                            for r in results
                        ],
                        "success": True,
                    }

                if data.get("status") == "failed":
                    raise RuntimeError(f"Crawl failed: {data}")

                await asyncio.sleep(3)

        raise TimeoutError(f"Crawl {crawl_id} timed out after {timeout}ms")

    async def map_site(
        self,
        url: str,
        *,
        timeout: int = 30000,
    ) -> dict:
        """List URLs from a site via /v1/map."""
        async with httpx.AsyncClient(timeout=timeout / 1000 + 10) as client:
            resp = await client.post(
                f"{self.base_url}/map",
                headers=self._headers(),
                json={"url": url},
            )
            resp.raise_for_status()
            data = resp.json()

        return {
            "url": url,
            "urls": data.get("urls", []),
            "total": len(data.get("urls", [])),
            "success": True,
        }

    async def health(self) -> bool:
        # Every /scrape call is billed, so availability is judged from configuration only;
        # auth or quota errors surface on the first real request and trigger fallback.
        return self.enabled
