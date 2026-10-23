#!/usr/bin/env python3
"""Demo: scrape a URL using the unified scraper with three-level fallback."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from smard_crawler.common.scraper import UnifiedScraper


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    engine = sys.argv[2] if len(sys.argv) > 2 else "auto"

    scraper = UnifiedScraper()

    print("Checking engine availability...")
    health = await scraper.check_engines()
    for name in scraper.engine_order:
        print(f"  {name:<15} {'UP' if health.get(name) else 'DOWN/NOT CONFIGURED'}")

    available = [k for k, v in health.items() if v]
    if not available:
        print("\nNo engines available. Options:")
        print("  - Start containers: docker compose up -d")
        print("  - Configure SITE_UNBLOCKER_URL in .env")
        print("  - Configure DECODO_API_KEY in .env")
        print("\nFalling back to direct Crawl4AI library mode...")
        from smard_crawler.crawl4ai.client import Crawl4AIClient
        client = Crawl4AIClient()
        result = await client.scrape_direct(url)
    else:
        print(f"\nScraping {url} (engine={engine})...")
        result = await scraper.scrape(url, engine=engine)
    await scraper.close()

    print(f"\n--- Result ---")
    print(f"URL: {result.get('url')}")
    print(f"Engine: {result.get('engine', 'direct')}")
    print(f"Success: {result.get('success')}")
    print(f"Markdown length: {len(result.get('markdown', ''))} chars")
    if result.get("saved_path"):
        print(f"Saved to: {result['saved_path']}")
    print(f"\n--- First 500 chars ---")
    print(result.get("markdown", "")[:500])


if __name__ == "__main__":
    asyncio.run(main())
