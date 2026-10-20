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
| [docker-compose.yml](docker-compose.yml) | Container orchestration (Firecrawl + Crawl4AI + Redis) |
| [.env.example](.env.example) | Environment variable template |
| [src/common/config.py](src/common/config.py) | Centralized configuration from env vars |
| [src/common/scraper.py](src/common/scraper.py) | Unified scraper interface with auto-routing |
| [src/common/stealth.py](src/common/stealth.py) | Anti-bot stealth utilities |
| [src/crawl4ai/client.py](src/crawl4ai/client.py) | Crawl4AI server and direct library client |
| [src/firecrawl/client.py](src/firecrawl/client.py) | Firecrawl self-hosted API client |
| [scripts/setup.sh](scripts/setup.sh) | Environment setup script |
| [scripts/demo.py](scripts/demo.py) | Demo and verification script |

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
