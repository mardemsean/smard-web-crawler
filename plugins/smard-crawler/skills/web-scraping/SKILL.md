---
name: web-scraping
description: Fetch web pages as clean Markdown with the SMard crawler MCP tools (scrape, scrape_batch, crawl, map_site, engines_health). Use when the user asks to read, scrape, extract, crawl or monitor a website, or when a plain web fetch is blocked by anti-bot protection.
---

# Web scraping with the SMard crawler

The `smard-crawler` MCP server exposes five tools. Prefer them over generic fetch tools when a page needs JavaScript rendering, anti-bot evasion, or many URLs.

| Tool | Use for |
|---|---|
| `scrape(url, engine="auto", max_chars=50000)` | One page to Markdown |
| `scrape_batch(urls, engine="auto", concurrency=5, max_chars=10000)` | Up to 100 pages; returns `{count, succeeded, results}` |
| `crawl(url, limit=20, max_depth=2)` | A site section (Firecrawl self-hosted, then Decodo Web Data API) |
| `map_site(url)` | List a site's URLs (needs `DECODO_API_KEY`) |
| `engines_health()` | Which engines are up, the fallback order, today's paid budget |

## How the fallback chain works

`engine="auto"` tries, in order (configurable with `ENGINE_ORDER`):

1. **obscura**: lightweight stealth browser with a Chrome-identical TLS fingerprint. Fast, about 110 MB RAM. No WebGL.
2. **crawl4ai**: full Chromium with `enable_stealth`, good for heavy JS sites.
3. **firecrawl**: self-hosted Firecrawl, also used by `crawl`.
4. **cloakbrowser**: source-patched stealth Chromium for the hardest targets. The free tier runs one session at a time.
5. **site_unblocker**: Decodo managed anti-bot. **Paid.**
6. **web_data_api**: Decodo fully managed API. **Paid.**

Paid engines are rate-limited (`DECODO_MAX_RPS`) and capped per day (`DECODO_DAILY_LIMIT`). Pass a specific `engine` only when you have a reason, for example forcing `cloakbrowser` after `auto` returned a challenge page.

## Rules

- robots.txt is enforced. A `robots_disallowed` error means the site forbids it: tell the user, do not retry with another engine.
- Private, loopback and cloud-metadata addresses are refused (`unsafe_url`).
- Tool errors come back as `{"success": false, "error": <kind>, "detail": ...}` with kind `unsafe_url`, `robots_disallowed`, `budget_exhausted`, `invalid_request` or `engines_failed`.
- Large pages are truncated to `max_chars` (`truncated: true`, `total_chars`). Raise `max_chars` only when the user needs the full text.
- Check `engines_health` first when every call fails; it usually means the services are not running.

## If the tools are missing

The plugin launches `smard-crawler-mcp`, which must be installed on this machine:

```bash
git clone https://github.com/mardemsean/smard-web-crawler && cd smard-web-crawler
scripts/install.sh                                      # Linux / macOS
powershell -ExecutionPolicy Bypass -File scripts\install.ps1   # Windows
```

If the command is not on PATH, set `SMARD_CRAWLER_MCP` to its absolute path (the installer prints it). Configuration lives in `~/.smard-crawler/.env`.
