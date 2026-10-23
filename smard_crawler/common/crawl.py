"""Breadth-first crawl built on top of any scrape function that returns links.

This is the free fallback for UnifiedScraper.crawl() when Firecrawl's self-hosted
stack is not running: it reuses the browser engines already in the chain (Obscura,
CloakBrowser, Crawl4AI) instead of requiring Firecrawl's seven services. Firecrawl
stays the preferred crawl engine; this keeps the feature alive without it.
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable
from urllib.parse import urldefrag, urlsplit

# fetch(url) -> scrape result dict carrying at least "markdown"; "links" and "title" when available.
FetchFn = Callable[[str], Awaitable[dict[str, Any]]]


def _norm(url: str) -> str:
    """Drop the fragment and a trailing slash so the same page is not visited twice."""
    url, _ = urldefrag(url)
    if url.endswith("/") and urlsplit(url).path != "/":
        url = url[:-1]
    return url


def _same_site(a: str, b: str) -> bool:
    pa, pb = urlsplit(a), urlsplit(b)
    return pa.scheme in ("http", "https") and pa.netloc == pb.netloc


async def bfs_crawl(
    fetch: FetchFn,
    start_url: str,
    *,
    limit: int = 50,
    max_depth: int = 2,
    same_domain: bool = True,
    concurrency: int = 4,
) -> dict[str, Any]:
    """Crawl start_url breadth-first, following same-site links up to limit/max_depth.

    Returns {"pages": [...], "total", "crawl_id": "native", "success"}. Each page is
    {"url", "markdown", "title", "depth"}. A page that fails to fetch is recorded with
    an "error" and does not contribute links. Order within a depth level is not
    guaranteed; the set of pages and the limit are.
    """
    start = _norm(start_url)
    seen: set[str] = {start}
    pages: list[dict[str, Any]] = []
    errors = 0
    level = [start]  # the current BFS depth level
    depth = 0
    sem = asyncio.Semaphore(max(1, concurrency))

    async def _fetch_one(url: str) -> tuple[str, dict[str, Any] | None, Exception | None]:
        async with sem:
            try:
                return url, await fetch(url), None
            except Exception as e:  # a dead link must not abort the crawl
                return url, None, e

    # One while-iteration is exactly one depth level, so `depth` stays accurate.
    while level and len(pages) < limit and depth <= max_depth:
        batch = level[: limit - len(pages)]
        results = await asyncio.gather(*(_fetch_one(u) for u in batch))
        next_level: list[str] = []
        for url, result, err in results:
            if err is not None or result is None:
                errors += 1
                pages.append({"url": url, "depth": depth, "error": str(err), "success": False})
                continue
            pages.append({
                "url": result.get("final_url") or url,
                "markdown": result.get("markdown", ""),
                "title": result.get("title", ""),
                "depth": depth,
                "success": result.get("success", True),
            })
            if depth < max_depth:
                for link in result.get("links") or []:
                    n = _norm(link)
                    if n in seen or (same_domain and not _same_site(n, start)):
                        continue
                    seen.add(n)
                    next_level.append(n)
        level = next_level
        depth += 1

    return {
        "crawl_id": "native",
        "url": start,
        "total": len(pages),
        "errors": errors,
        "pages": pages,
        "success": any(p.get("success") for p in pages),
    }
