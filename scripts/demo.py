#!/usr/bin/env python3
"""Demo: scrape a URL using the unified scraper interface."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.common.scraper import UnifiedScraper


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    engine = sys.argv[2] if len(sys.argv) > 2 else "auto"

    scraper = UnifiedScraper()

    print(f"Checking engine availability...")
    health = await scraper.check_engines()
    print(f"  Crawl4AI: {'UP' if health['crawl4ai'] else 'DOWN'}")
    print(f"  Firecrawl: {'UP' if health['firecrawl'] else 'DOWN'}")

    if not any(health.values()):
        print("\nNo engines running. Start them with:")
        print("  cd /home/user/web-scraper-toolkit && docker compose up -d")
        print("\nFalling back to direct Crawl4AI library mode...")
        from src.crawl4ai.client import Crawl4AIClient
        client = Crawl4AIClient()
        result = await client.scrape_direct(url)
    else:
        print(f"\nScraping {url} (engine={engine})...")
        result = await scraper.scrape(url, engine=engine)

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
