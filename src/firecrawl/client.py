"""Firecrawl self-hosted client with proxy and stealth support."""

import time
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..common.config import config


class FirecrawlClient:
    """Client for Firecrawl self-hosted API."""

    def __init__(
        self,
        host: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.host = (host or config.firecrawl_host).rstrip("/")
        self.api_key = api_key or config.firecrawl_api_key

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def scrape(
        self,
        url: str,
        *,
        formats: Optional[list[str]] = None,
        wait_for: int = 0,
        timeout: int = 30000,
        only_main_content: bool = True,
    ) -> dict:
        """Scrape a single URL via Firecrawl /v1/scrape endpoint."""
        payload = {
            "url": url,
            "formats": formats or ["markdown"],
            "onlyMainContent": only_main_content,
            "timeout": timeout,
        }

        if wait_for:
            payload["waitFor"] = wait_for

        async with httpx.AsyncClient(timeout=timeout / 1000 + 15) as client:
            resp = await client.post(
                f"{self.host}/v1/scrape",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        if not data.get("success"):
            raise ValueError(f"Firecrawl scrape failed: {data}")

        result = data.get("data", {})
        return {
            "url": result.get("metadata", {}).get("sourceURL", url),
            "markdown": result.get("markdown", ""),
            "html": result.get("html", ""),
            "metadata": result.get("metadata", {}),
            "success": True,
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def crawl(
        self,
        url: str,
        *,
        max_depth: int = 2,
        limit: int = 50,
        formats: Optional[list[str]] = None,
        timeout: int = 120000,
    ) -> dict:
        """Start a crawl job via /v1/crawl and poll until complete."""
        payload = {
            "url": url,
            "maxDepth": max_depth,
            "limit": limit,
            "scrapeOptions": {
                "formats": formats or ["markdown"],
                "onlyMainContent": True,
            },
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.host}/v1/crawl",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            job = resp.json()

        job_id = job.get("id")
        if not job_id:
            raise ValueError(f"No job ID returned: {job}")

        return await self._poll_crawl(job_id, timeout)

    async def _poll_crawl(self, job_id: str, timeout: int) -> dict:
        deadline = time.time() + timeout / 1000
        async with httpx.AsyncClient(timeout=15) as client:
            while time.time() < deadline:
                resp = await client.get(
                    f"{self.host}/v1/crawl/{job_id}",
                    headers=self._headers(),
                )
                resp.raise_for_status()
                status = resp.json()

                if status.get("status") == "completed":
                    pages = status.get("data", [])
                    return {
                        "job_id": job_id,
                        "total": status.get("total", len(pages)),
                        "pages": [
                            {
                                "url": p.get("metadata", {}).get("sourceURL", ""),
                                "markdown": p.get("markdown", ""),
                                "metadata": p.get("metadata", {}),
                            }
                            for p in pages
                        ],
                        "success": True,
                    }

                if status.get("status") == "failed":
                    raise RuntimeError(f"Crawl failed: {status}")

                await asyncio.sleep(2)

        raise TimeoutError(f"Crawl job {job_id} timed out after {timeout}ms")

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.host}/")
                return resp.status_code == 200
        except Exception:
            return False
