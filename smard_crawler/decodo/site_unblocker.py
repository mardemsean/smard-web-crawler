"""Decodo Site Unblocker client — proxy-like interface with built-in anti-bot bypass."""

import logging
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..common.config import config

logger = logging.getLogger(__name__)


class SiteUnblockerClient:
    """Fallback level 2: Decodo Site Unblocker (proxy endpoint with managed anti-bot)."""

    def __init__(self, proxy_url: Optional[str] = None):
        self.proxy_url = proxy_url or config.site_unblocker_url

    @property
    def enabled(self) -> bool:
        return bool(self.proxy_url)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def scrape(
        self,
        url: str,
        *,
        js_render: bool = True,
        markdown: bool = True,
        geo: Optional[str] = None,
        session_id: Optional[str] = None,
        timeout: int = 60000,
    ) -> dict:
        """Scrape a URL via Site Unblocker proxy with optional JS rendering and markdown output."""
        headers: dict[str, str] = {}
        if js_render:
            headers["X-SU-Headless"] = "html"
        if markdown:
            headers["X-SU-Markdown"] = "1"
        if geo:
            headers["X-SU-Geo"] = geo
        if session_id:
            headers["X-SU-Session"] = session_id

        async with httpx.AsyncClient(
            proxy=self.proxy_url,
            verify=False,
            timeout=timeout / 1000 + 10,
        ) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()

        content = resp.text
        is_markdown = markdown and not content.strip().startswith("<")

        return {
            "url": url,
            "markdown": content if is_markdown else "",
            "html": content if not is_markdown else "",
            "success": True,
            "metadata": {
                "status_code": resp.status_code,
                "js_rendered": js_render,
                "markdown_mode": markdown,
                "geo": geo,
            },
        }

    async def health(self) -> bool:
        # Requests through the unblocker are billed, so availability is judged from configuration only.
        return self.enabled
