# Web Scraper Toolkit

Self-hosted web scraping infrastructure using Crawl4AI and Firecrawl for HTML-to-Markdown conversion with anti-bot bypass capabilities. Three-level fallback through Decodo (ex-Smartproxy) services.

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
│   │   ├── scraper.py      # Unified scraper with 3-level fallback
│   │   └── stealth.py      # Anti-bot utilities
│   ├── crawl4ai/
│   │   └── client.py       # Crawl4AI server + direct library client
│   ├── firecrawl/
│   │   └── client.py       # Firecrawl self-hosted API client
│   └── decodo/
│       ├── site_unblocker.py  # Decodo Site Unblocker (fallback level 2)
│       └── web_data_api.py    # Decodo Web Data API (fallback level 3)
├── data/output/            # Scraped markdown output
└── tests/
```

## Fallback Architecture

```
Request → [1] Self-hosted (Crawl4AI/Firecrawl + Residential Proxy)  — $3/GB
              ↓ fail
          [2] Decodo Site Unblocker (proxy-like, managed anti-bot)   — $5.50/GB
              ↓ fail
          [3] Decodo Web Data API /scrape (REST, fully managed)      — $0.40-1.25/1K req
```

## Quick Start

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with proxy credentials

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

### Level 1 — Self-hosted engines + Residential Proxy
- `PROXY_URL` — Decodo residential proxy (`http://user:pass@gate.decodo.com:7000`)
- `FIRECRAWL_HOST` — Firecrawl API endpoint (default: localhost:3002)
- `CRAWL4AI_BASE_URL` — Crawl4AI endpoint (default: localhost:11235)
- `STEALTH_ENABLED` — enable playwright-stealth patches
- `BROWSER_HEADLESS` — headless browser mode (true/false)

### Level 2 — Decodo Site Unblocker
- `SITE_UNBLOCKER_URL` — Site Unblocker proxy (`http://user:pass@unblock.decodo.com:60000`)
- `SITE_UNBLOCKER_FALLBACK` — enable as automatic fallback (default: true)

### Level 3 — Decodo Web Data API
- `DECODO_API_KEY` — Bearer token for Web Data API
- `DECODO_API_URL` — API base URL (default: https://data.decodo.com/v1)
- `DECODO_API_FALLBACK` — enable as last-resort fallback (default: true)
