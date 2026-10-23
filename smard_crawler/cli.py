"""smard-crawler command line: scrape, batch, crawl, map, health, serve, mcp, bench."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any


def _print(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


async def _with_scraper(fn):
    from .common.scraper import UnifiedScraper

    scraper = UnifiedScraper()
    try:
        return await fn(scraper)
    finally:
        await scraper.close()


def _cmd_scrape(a: argparse.Namespace) -> int:
    result = asyncio.run(_with_scraper(lambda s: s.scrape(a.url, engine=a.engine, save=not a.no_save)))
    if a.json:
        _print(result)
    else:
        print(f"# engine={result.get('engine')} elapsed_ms={result.get('elapsed_ms')} saved={result.get('saved_path')}", file=sys.stderr)
        print(result.get("markdown", ""))
    return 0 if result.get("success") else 1


def _cmd_batch(a: argparse.Namespace) -> int:
    urls = [line.strip() for line in Path(a.file).read_text().splitlines() if line.strip() and not line.startswith("#")]
    results = asyncio.run(_with_scraper(lambda s: s.scrape_batch(urls, engine=a.engine, concurrency=a.concurrency, save=not a.no_save)))
    _print([{k: r.get(k) for k in ("url", "engine", "success", "saved_path", "error")} for r in results])
    return 0 if all(r.get("success") for r in results) else 1


def _cmd_crawl(a: argparse.Namespace) -> int:
    _print(asyncio.run(_with_scraper(lambda s: s.crawl(a.url, limit=a.limit, max_depth=a.max_depth))))
    return 0


def _cmd_map(a: argparse.Namespace) -> int:
    _print(asyncio.run(_with_scraper(lambda s: s.map_site(a.url))))
    return 0


def _cmd_health(a: argparse.Namespace) -> int:
    from .server.service import ScrapeService

    async def run():
        svc = ScrapeService()
        try:
            return await svc.health()
        finally:
            await svc.close()

    report = asyncio.run(run())
    _print(report)
    return 0 if any(report["engines"].values()) else 1


def _cmd_serve(a: argparse.Namespace) -> int:
    from .server.api import serve

    serve(a.host, a.port)
    return 0


def _cmd_mcp(a: argparse.Namespace) -> int:
    from .server.mcp_server import main

    main()
    return 0


def build_parser() -> argparse.ArgumentParser:
    from .common.scraper import FALLBACK_ORDER

    engines = ["auto", *FALLBACK_ORDER]
    ap = argparse.ArgumentParser(prog="smard-crawler", description="Self-hosted scraping with a multi-engine fallback chain.")
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("scrape", help="scrape one URL to Markdown")
    p.add_argument("url")
    p.add_argument("--engine", choices=engines, default="auto")
    p.add_argument("--no-save", action="store_true", help="do not write to OUTPUT_DIR")
    p.add_argument("--json", action="store_true", help="print the full result as JSON")
    p.set_defaults(fn=_cmd_scrape)

    p = sub.add_parser("batch", help="scrape every URL in a file (one per line)")
    p.add_argument("file")
    p.add_argument("--engine", choices=engines, default="auto")
    p.add_argument("--concurrency", type=int, default=5)
    p.add_argument("--no-save", action="store_true")
    p.set_defaults(fn=_cmd_batch)

    p = sub.add_parser("crawl", help="crawl a site")
    p.add_argument("url")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--max-depth", type=int, default=2)
    p.set_defaults(fn=_cmd_crawl)

    p = sub.add_parser("map", help="list a site's URLs (Decodo Web Data API)")
    p.add_argument("url")
    p.set_defaults(fn=_cmd_map)

    p = sub.add_parser("health", help="show engine availability, order and paid budget")
    p.set_defaults(fn=_cmd_health)

    p = sub.add_parser("serve", help="run the HTTP API")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8787)
    p.set_defaults(fn=_cmd_serve)

    p = sub.add_parser("mcp", help="run the MCP server on stdio")
    p.set_defaults(fn=_cmd_mcp)

    sub.add_parser("bench", help="engine comparison battery (see: smard-crawler bench -h)", add_help=False)
    return ap


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["bench"]:
        from .bench.run import main as bench_main

        bench_main(argv[1:])
        return 0
    args = build_parser().parse_args(argv)
    # stdout carries the MCP protocol, so logs always go to stderr.
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING, stream=sys.stderr,
                        format="%(levelname)s %(name)s: %(message)s")
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
