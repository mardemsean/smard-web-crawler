"""Crawl4AI client for the Docker server API (typed-config payloads) or direct library usage.

The 0.9.x server treats request bodies as untrusted: proxy settings, js_code, magic,
simulate_user and override_navigator are rejected, and timeouts are capped at 60s.
Route the server's egress through a proxy with CRAWL4AI_UPSTREAM_PROXY on the container.
"""

import os
from typing import Any, Optional

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from ..common.config import config

_CONTENT_FILTERS: dict[str, dict] = {
    "pruning": {"type": "PruningContentFilter", "params": {"threshold": 0.48, "threshold_type": "dynamic"}},
    "bm25": {"type": "BM25ContentFilter", "params": {"bm25_threshold": 1.0}},
}


MAX_SERVER_TIMEOUT_MS = 60_000


def _retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500


def _markdown_text(md: Any) -> str:
    if isinstance(md, dict):
        return md.get("fit_markdown") or md.get("raw_markdown") or ""
    return md or ""


def _internal_links(result: dict) -> list[str]:
    """Absolute hrefs of same-site links, from Crawl4AI's links.internal[*].href."""
    internal = (result.get("links") or {}).get("internal") or []
    seen: dict[str, None] = {}
    for link in internal:
        href = (link.get("href") or "").strip() if isinstance(link, dict) else ""
        if href.startswith(("http://", "https://")):
            seen.setdefault(href, None)
    return list(seen)


class Crawl4AIClient:
    """Client for the Crawl4AI server (Docker) or direct library usage."""

    def __init__(self, base_url: Optional[str] = None, api_token: Optional[str] = None):
        self.base_url = (base_url or config.crawl4ai_base_url).rstrip("/")
        self.strategy = config.crawl4ai_strategy
        self.api_token = api_token if api_token is not None else os.getenv("CRAWL4AI_API_TOKEN", "")

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_token}"} if self.api_token else {}

    def build_payload(
        self,
        url: str,
        *,
        strategy: Optional[str] = None,
        stealth: bool = True,
        wait_for: Optional[str] = None,
        timeout: int = 30000,
    ) -> dict:
        stealth = stealth and config.stealth.enabled
        browser: dict[str, Any] = {
            "headless": config.browser.headless,
            "viewport_width": config.browser.viewport_width,
            "viewport_height": config.browser.viewport_height,
            "enable_stealth": stealth,
        }
        crawler: dict[str, Any] = {
            "cache_mode": "bypass",
            "word_count_threshold": 10,
            "page_timeout": min(timeout, MAX_SERVER_TIMEOUT_MS),
            "remove_overlay_elements": stealth,
            "remove_consent_popups": stealth,
        }
        content_filter = _CONTENT_FILTERS.get(strategy or self.strategy)
        if content_filter:
            crawler["markdown_generator"] = {"type": "DefaultMarkdownGenerator", "params": {"content_filter": content_filter}}
        if wait_for:
            crawler["wait_for"] = wait_for

        return {
            "urls": [url],
            "browser_config": {"type": "BrowserConfig", "params": browser},
            "crawler_config": {"type": "CrawlerRunConfig", "params": crawler},
        }

    async def scrape(
        self,
        url: str,
        *,
        strategy: Optional[str] = None,
        stealth: bool = True,
        wait_for: Optional[str] = None,
        timeout: int = 30000,
    ) -> dict:
        """Scrape a URL and return markdown + metadata via the Crawl4AI server.

        wait_for must be a CSS condition ("css:#main"); JS conditions are refused by the server.
        """
        payload = self.build_payload(url, strategy=strategy, stealth=stealth, wait_for=wait_for, timeout=timeout)
        result = await self._request(payload, timeout)
        result["extraction_strategy"] = strategy or self.strategy
        return result

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10),
           retry=retry_if_exception(_retryable), reraise=True)
    async def _request(self, payload: dict, timeout: int) -> dict:
        async with httpx.AsyncClient(timeout=timeout / 1000 + 30) as client:
            resp = await client.post(f"{self.base_url}/crawl", json=payload, headers=self._headers())
            if resp.status_code == 400:
                raise ValueError(f"Crawl4AI rejected the request: {resp.text[:300]}")
            resp.raise_for_status()
            data = resp.json()

        if not data.get("results"):
            raise ValueError(f"No results from Crawl4AI: {str(data)[:300]}")

        result = data["results"][0]
        if not result.get("success", True):
            raise RuntimeError(f"Crawl4AI failed: {result.get('error_message') or result.get('status_code')}")
        return {
            "url": result.get("url", payload["urls"][0]),
            "status": result.get("status_code"),
            "markdown": _markdown_text(result.get("markdown")),
            "links": _internal_links(result),
            "metadata": result.get("metadata") or {},
            "success": True,
        }

    async def scrape_direct(self, url: str, *, strategy: Optional[str] = None, stealth: bool = True) -> dict:
        """Scrape using the crawl4ai library directly (no server required; pip install 'smard-web-crawler[direct]')."""
        try:
            from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
        except ImportError:
            raise RuntimeError("crawl4ai not installed. Run: pip install 'smard-web-crawler[direct]'")

        browser_cfg = BrowserConfig(
            headless=config.browser.headless,
            viewport_width=config.browser.viewport_width,
            viewport_height=config.browser.viewport_height,
            enable_stealth=stealth,
            proxy=config.proxy.url if config.proxy.enabled else None,
        )
        run_cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, word_count_threshold=10, magic=stealth)
        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            result = await crawler.arun(url=url, config=run_cfg)

        return {
            "url": url,
            "status": result.status_code,
            "markdown": _markdown_text(getattr(result.markdown, "model_dump", lambda: result.markdown)()),
            "metadata": result.metadata or {},
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
