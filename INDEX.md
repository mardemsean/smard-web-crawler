# Canonical index

This index maps responsibilities; it does not prove reading or approval.

## Entry and governance

| Source | Responsibility |
| --- | --- |
| [README](README.md) | Entry orientation and state |
| [METHODOLOGY](METHODOLOGY.md) | Intent and articulation of the cycle |
| [RULES](RULES.md) | Human–agent working rules |
| [AGENTS](AGENTS.md) | Operational routing and readings per action |
| [adrZERO](adrZERO.md) | Foundational decision: self-hosted over paid APIs |

## Technical

| Source | Responsibility |
| --- | --- |
| [pyproject.toml](pyproject.toml) | Package metadata, extras and console scripts |
| [docker-compose.yml](docker-compose.yml) | Container stack (Obscura + Crawl4AI + API) |
| [.env.example](.env.example) | Environment variable template |
| [smard_crawler/common/config.py](smard_crawler/common/config.py) | Configuration from env vars and .env files |
| [smard_crawler/common/scraper.py](smard_crawler/common/scraper.py) | Fallback chain, intra-engine retry, liveness |
| [smard_crawler/common/robots.py](smard_crawler/common/robots.py) | robots.txt compliance |
| [smard_crawler/common/budget.py](smard_crawler/common/budget.py) | Rate limit and daily budget for paid engines |
| [smard_crawler/common/urlguard.py](smard_crawler/common/urlguard.py) | SSRF guard at the API/MCP boundary |
| [smard_crawler/common/stealth.py](smard_crawler/common/stealth.py) | Browser profiles, GREASE, navigator script |
| [smard_crawler/browsers/client.py](smard_crawler/browsers/client.py) | Obscura and CloakBrowser engines |
| [smard_crawler/crawl4ai/client.py](smard_crawler/crawl4ai/client.py) | Crawl4AI server client |
| [smard_crawler/firecrawl/client.py](smard_crawler/firecrawl/client.py) | Firecrawl self-hosted client |
| [smard_crawler/decodo/](smard_crawler/decodo/) | Decodo Site Unblocker and Web Data API clients |
| [smard_crawler/server/](smard_crawler/server/) | HTTP API and MCP server |
| [smard_crawler/bench/](smard_crawler/bench/) | Engine comparison battery |
| [smard_crawler/cli.py](smard_crawler/cli.py) | `smard-crawler` command line |
| [plugins/smard-crawler/](plugins/smard-crawler/) | Claude Code plugin (MCP + skills) |
| [.claude-plugin/marketplace.json](.claude-plugin/marketplace.json) | Plugin marketplace |
| [scripts/install.sh](scripts/install.sh), [scripts/install.ps1](scripts/install.ps1) | Installers |
| [scripts/firecrawl-up.sh](scripts/firecrawl-up.sh) | Firecrawl self-hosted stack at a pinned release |
| [scripts/setup.sh](scripts/setup.sh) | Cloud agent environment setup |
| [docs/decisions/0001-obscura-engine.md](docs/decisions/0001-obscura-engine.md) | Decision D1: Obscura as engine |
| [DEPLOY-CHECKLIST.md](DEPLOY-CHECKLIST.md) | Deployment checklist |

## Available templates (not filled-in documents)

| Template | Trigger |
| --- | --- |
| [Exploration](docs/production-workflow/templates/EXPLORATION.md) | Preserve selected learning |
| [ZERO](docs/production-workflow/templates/REQUIREMENT-ZERO.MD) | Elaborate the foundation of the product |
| [Numbered requirement](docs/production-workflow/templates/requirement-NNNN.md) | Change or expansion of the intent |
| [Preflight and ADR](docs/production-workflow/templates/PREFLIGHT-ADR.md) | Examine risk and a material decision |
| [Execution bridge](docs/production-workflow/templates/SPECS-TASKS-BRIDGE.md) | Connect specs/tasks and the mandate |
| [Delivery and learning](docs/production-workflow/templates/LEARNING-DELIVERY.md) | Review, release and observe |
| [Constitution](docs/production-workflow/templates/REPOSITORY-CONSTITUTION.md) | Concrete need for a repo or incorporation |
| [Handoff](docs/production-workflow/templates/PASSAGE-RECORD.md) | Preserve a relevant decision or transition |
| [Capabilities](docs/production-workflow/templates/CAPABILITIES-INTEGRATIONS.md) | Adopt or modify a prompt, skill, MCP, agent or executor |
| [Session checkpoint](docs/production-workflow/templates/SESSION-CHECKPOINT.md) | Preserve memory before compaction or handoff |
| [Ratification](docs/production-workflow/templates/DOCUMENTARY-RATIFICATION.md) | Relate content, human response and authorized revision |

## Limits of the inventory

The index covers the current state of this repository. The presence of a file or
directory does not demonstrate activation, authorization or compatibility.
