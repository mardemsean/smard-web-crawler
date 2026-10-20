# smard-web-crawler — *advanced local self-hosted web search and scrape engine*

Self-hosted web scraping infrastructure using Crawl4AI and Firecrawl for
HTML-to-Markdown conversion with anti-bot bypass capabilities. Built for
autonomous agents that need high-quality, clean data from the web without
per-request API costs or rate limits.

## Why this exists

Paid scraping APIs charge per request and impose rate limits. Their open-source
counterparts — Crawl4AI and Firecrawl self-hosted — use identical algorithms for
HTML-to-Markdown conversion, the same Playwright headless rendering, and the same
semantic noise-removal strategies. The only real advantage of a paid API is
managed infrastructure: proxy rotation and anti-bot bypass.

This project closes that gap. It provides the infrastructure layer — proxy
integration, stealth mode, human simulation, and a unified scraper interface —
so that self-hosted engines deliver the same quality at zero per-request cost.

## What it actually does

- **Unified scraper** that auto-routes to the best available engine (Crawl4AI or
  Firecrawl) with health detection and fallback.
- **Docker Compose** stack: Firecrawl API + Redis + Crawl4AI server, one command.
- **Anti-bot bypass**: residential proxy integration, playwright-stealth patches,
  realistic HTTP headers, human behavior simulation.
- **Batch scraping** with concurrency control, per-domain rate limiting, and
  automatic retry with exponential backoff.
- **Markdown output** with YAML frontmatter metadata (source URL, engine,
  timestamp, extraction stats).

## Quick start

```bash
cp .env.example .env    # configure proxy credentials
docker compose up -d    # start engines
python3 scripts/demo.py https://example.com
```

## Honest about state

This repository was constituted from a working implementation session. The
technical code is operational. The methodological documentation follows the
smard-agent-flow baseline; documents are created when their triggers occur, not
preemptively.

## Structure

- [AGENTS.md](AGENTS.md) — operational routing for agents working in this repo.
- [METHODOLOGY.md](METHODOLOGY.md) — intent and articulation of the cycle.
- [RULES.md](RULES.md) — human–agent working rules.
- [INDEX.md](INDEX.md) — canonical index of responsibilities.
- [adrZERO.md](adrZERO.md) — foundational decision: self-hosted over paid APIs.

Technical:

- `src/` — Python source: unified scraper, Crawl4AI client, Firecrawl client,
  stealth utilities.
- `docker-compose.yml` — container orchestration.
- `scripts/` — setup and demo scripts.
- `.env.example` — environment variable template.
