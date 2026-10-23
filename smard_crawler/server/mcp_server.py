"""MCP server (stdio) exposing the scraper as tools for Claude Code and other MCP clients."""

from __future__ import annotations

from typing import Any, Optional

from mcp.server.mcpserver import MCPServer

from ..common.budget import BudgetExceeded
from ..common.robots import RobotsDisallowed
from ..common.urlguard import UnsafeURL
from .service import ScrapeService

INSTRUCTIONS = (
    "SMard Web Crawler: fetch web pages as clean Markdown through a fallback chain "
    "(Obscura -> Crawl4AI -> Firecrawl -> CloakBrowser -> Decodo Site Unblocker -> Decodo Web Data API). "
    "Use scrape for one URL, scrape_batch for several, crawl for a site section, map_site to list URLs, "
    "engines_health to see which engines are up. robots.txt is respected; paid Decodo engines are rate-limited "
    "and capped per day."
)


def _error(e: Exception) -> dict[str, Any]:
    kind = {
        UnsafeURL: "unsafe_url",
        RobotsDisallowed: "robots_disallowed",
        BudgetExceeded: "budget_exhausted",
    }.get(type(e), "invalid_request" if isinstance(e, ValueError) else "engines_failed")
    return {"success": False, "error": kind, "detail": str(e)}


def build_server(service: Optional[ScrapeService] = None) -> MCPServer:
    svc = service or ScrapeService()
    server = MCPServer(name="smard-crawler", instructions=INSTRUCTIONS, version="0.2.0")

    async def guarded(coro) -> Any:
        try:
            return await coro
        except (UnsafeURL, RobotsDisallowed, BudgetExceeded, ValueError, RuntimeError) as e:
            return _error(e)

    @server.tool(description="Scrape one URL and return Markdown. engine: auto (fallback chain) or a specific engine name.")
    async def scrape(url: str, engine: str = "auto", max_chars: int = 50_000) -> dict:
        return await guarded(svc.scrape(url, engine=engine, save=False, max_chars=max_chars))

    @server.tool(description="Scrape up to 100 URLs concurrently. Returns one result per URL (markdown truncated to max_chars each).")
    async def scrape_batch(urls: list[str], engine: str = "auto", concurrency: int = 5, max_chars: int = 10_000) -> dict:
        async def run() -> dict:
            results = await svc.batch(urls, engine=engine, concurrency=concurrency, save=False, max_chars=max_chars)
            return {"count": len(results), "succeeded": sum(1 for r in results if r.get("success")), "results": results}

        return await guarded(run())

    @server.tool(description="Crawl a site from a start URL (Firecrawl self-hosted, falling back to Decodo Web Data API).")
    async def crawl(url: str, limit: int = 20, max_depth: int = 2) -> dict:
        return await guarded(svc.crawl(url, limit=limit, max_depth=max_depth))

    @server.tool(description="List the URLs of a site (Decodo Web Data API /map; needs DECODO_API_KEY).")
    async def map_site(url: str) -> dict:
        return await guarded(svc.map_site(url))

    @server.tool(description="Report which engines are up, the active fallback order and today's paid-request budget.")
    async def engines_health() -> dict:
        return await svc.health()

    return server


def main() -> None:
    build_server().run("stdio")


if __name__ == "__main__":
    main()

