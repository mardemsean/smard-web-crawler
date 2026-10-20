# Web Scraper Toolkit

Self-hosted web scraping infrastructure using Crawl4AI and Firecrawl for HTML-to-Markdown conversion with anti-bot bypass capabilities.

## Project Structure

```
web-scraper-toolkit/
├── docker-compose.yml      # Firecrawl + Crawl4AI containers
├── .env.example            # Environment variable template
├── scripts/
│   ├── setup.sh            # Cloud environment setup script
│   └── demo.py             # Quick demo of unified scraper
├── src/
│   ├── common/
│   │   ├── config.py       # Centralized config from env vars
│   │   ├── scraper.py      # Unified scraper (auto-routes to best engine)
│   │   └── stealth.py      # Anti-bot utilities
│   ├── crawl4ai/
│   │   └── client.py       # Crawl4AI server + direct library client
│   └── firecrawl/
│       └── client.py       # Firecrawl self-hosted API client
├── data/output/            # Scraped markdown output
└── tests/
```

## Quick Start

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with proxy credentials if needed

# 2. Start containers
docker compose up -d

# 3. Test
python3 scripts/demo.py https://example.com
```

## Conventions

- Python 3.12+, async/await throughout
- All config via environment variables (never hardcoded secrets)
- Type hints on all public APIs
- Use `tenacity` for retry logic, `httpx` for async HTTP
- Output markdown files include YAML frontmatter metadata
- Proxy URL format: `http://user:pass@host:port`

## Key Environment Variables

- `PROXY_URL` — residential proxy for anti-bot bypass
- `FIRECRAWL_HOST` — Firecrawl API endpoint (default: localhost:3002)
- `CRAWL4AI_BASE_URL` — Crawl4AI endpoint (default: localhost:11235)
- `STEALTH_ENABLED` — enable playwright-stealth patches
- `BROWSER_HEADLESS` — headless browser mode (true/false)
