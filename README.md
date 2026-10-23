# smard-web-crawler — *self-hosted web search and scrape engine*

Turns web pages into clean Markdown through a chain of self-hosted engines, falling
back to managed Decodo services only when the free engines fail. Ships as a Python
package with a CLI, an HTTP API, an MCP server and a Claude Code plugin.

## Engines and fallback order

| # | Engine | Kind | Cost | Notes |
|---|---|---|---|---|
| 1 | **Obscura** (stealth build) | Rust/V8 headless browser over CDP | free | Chrome-identical TLS (JA3/JA4), ~110 MB RAM, no WebGL |
| 2 | **Crawl4AI** 0.9.5 | Chromium server (Docker) | free | `enable_stealth`, content filters |
| 3 | **Firecrawl** v2.11 | self-hosted stack (Docker) | free | preferred for `crawl` (native BFS fallback over a browser engine when it is not up) |
| 4 | **CloakBrowser** 0.6.3 | source-patched stealth Chromium | free tier, 1 session | hardest targets; needs a license |
| 5 | Decodo Site Unblocker | managed proxy | paid | rate-limited + daily cap |
| 6 | Decodo Web Data API | managed REST | paid | rate-limited + daily cap, `map` |

The order is configurable (`ENGINE_ORDER`). Engines that are down or unconfigured are
skipped, each engine retries with variant parameters before the chain escalates,
and failed engines are rechecked during long batches. Every scrape checks
`robots.txt` first (RFC 9309). The API and MCP refuse private and internal
addresses (SSRF guard).

Measured on SMardSERVER (Windows 11, direct egress, 5 rounds each, `smard-crawler bench --online`):

| Engine | Functional | Stealth probes | Static load | RSS | sannysoft failures | JA4 |
|---|---|---|---|---|---|---|
| CloakBrowser 155 | 100% | 100% | 45 ms | 465 MB | 0 | most common Chrome-on-Windows |
| Obscura `--stealth` | 100% | 90% | 27 ms | 80 MB | 3 | genuine Chrome (uTLS variant) |
| Chromium 156 headless | 100% | 70% | 30 ms | 259 MB | 12 | Chrome |

Obscura leads the chain for speed and density. Escalate to CloakBrowser
(`engine="cloakbrowser"`) for protected targets.
The rationale is in [docs/decisions/0001-obscura-engine.md](docs/decisions/0001-obscura-engine.md).

## Install (any machine, private repo)

You need Python 3.12+ and git access to this repository. Docker is optional.

```bash
git clone https://github.com/mardemsean/smard-web-crawler && cd smard-web-crawler
scripts/install.sh                     # Linux / macOS
#   --with-cloak       also install CloakBrowser (then: cloakbrowser login)
#   --with-docker      start Obscura + Crawl4AI + API containers
#   --with-firecrawl   start the Firecrawl self-hosted stack
#   --with-chromium    Playwright Chromium (benchmark baseline)
```

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 -WithCloak   # Windows
```

The installer creates `~/.smard-crawler/` with a venv, the checksum-verified Obscura
stealth binary and a `.env` with generated tokens, and puts `smard-crawler` and
`smard-crawler-mcp` on PATH. Add your proxy and Decodo credentials to
`~/.smard-crawler/.env`.

### Claude Code plugin

```
/plugin marketplace add mardemsean/smard-web-crawler
/plugin install smard-crawler@smard-labs
```

Private repositories authenticate with your existing git credentials (SSH key or
`gh auth setup-git`). The plugin starts `smard-crawler-mcp`, so run the installer
first. Without the plugin, register the server directly:
`claude mcp add --scope user smard-crawler -- smard-crawler-mcp`.

## Use

```bash
smard-crawler health                               # engines, order, paid budget
smard-crawler scrape https://example.com           # Markdown to stdout (+ saved to OUTPUT_DIR)
smard-crawler batch urls.txt --concurrency 8
smard-crawler crawl https://docs.example.com --limit 50
smard-crawler serve                                # HTTP API on 127.0.0.1:8787
smard-crawler bench --engines obscura-stealth,cloakbrowser,chromium --rounds 5 --online
```

HTTP API (Bearer `SMARD_API_TOKEN`): `GET /health`, `POST /scrape`, `/batch`,
`/crawl`, `/map`. MCP tools: `scrape`, `scrape_batch`, `crawl`, `map_site`,
`engines_health`.

Docker stack: `docker compose --env-file ~/.smard-crawler/.env up -d`. All ports
bind to loopback, and the containers refuse to start without their tokens.

## Development

```bash
pip install -e ".[all,dev]"
pytest -q                                          # unit tests
OBSCURA_BIN=~/.smard-crawler/bin/obscura pytest -q # + real-engine integration tests
```

## Structure

Governance: [AGENTS.md](AGENTS.md), [METHODOLOGY.md](METHODOLOGY.md),
[RULES.md](RULES.md), [INDEX.md](INDEX.md), [adrZERO.md](adrZERO.md).

| Path | Content |
|---|---|
| `smard_crawler/common/` | config, fallback scraper, robots, budget, URL guard, Markdown, stealth |
| `smard_crawler/browsers/` | Obscura and CloakBrowser engines (Playwright/CDP) |
| `smard_crawler/crawl4ai/`, `firecrawl/`, `decodo/` | HTTP engine clients |
| `smard_crawler/server/` | HTTP API, MCP server, shared service layer |
| `smard_crawler/bench/` | engine comparison battery and fixtures |
| `plugins/smard-crawler/`, `.claude-plugin/` | Claude Code plugin and marketplace |
| `docker/`, `Dockerfile`, `docker-compose.yml` | container stack |
| `scripts/` | installers, Firecrawl launcher, cloud setup, demo |
| `RESEARCH/` | Obscura analysis and the PONTE bridge document |
