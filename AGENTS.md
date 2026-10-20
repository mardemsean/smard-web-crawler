# Instructions for agents in this repository

Read [METHODOLOGY.md](METHODOLOGY.md) and [RULES.md](RULES.md) when starting
work on this project. Use [INDEX.md](INDEX.md) to locate canonical sources.
Respect instructions of narrower scope and the policies of the environment; a
material conflict must be made explicit, not resolved silently.

## Before acting, read the pertinent contract

| Action | Mandatory readings | Expected evidence |
| --- | --- | --- |
| Explore an intent | Workflow, rules and the existing exploration if any | Companionship and a visible synthesis, without forcing formalization |
| Create or alter a document | Visible elaboration protocol in the documentary contract and the current document | Proposal in the chat, substantive delta and open points per document |
| Found or change an intent | Current ZERO or requirement, pertinent exploration and the corresponding template | Traceable proposal; ratification before executing a new commitment |
| Constitute a repo or baseline | Baseline, documentary contract and existing policies | Contextual inventory and the external authorizations required |
| Take an architectural decision | Requirement, earlier decisions and the pertinent preflight | Alternatives, consequences and an identifiable decision |
| Specify or delegate | Ratified requirement, applicable ADRs and the execution bridge | Coverage, canonical tasks and a bounded mandate |
| Alter a prompt, skill, MCP or adapter | Baseline, pertinent inventory and the contracts of the adopted tool | Provenance, permissions, install/removal and compatibility verified |
| Alter deterministic execution | Technical contract, configuration and the area's existing tests | Positive and negative coverage; regression test for a bug |
| Open a PR, integrate or release | Existing review/release rules and the pertinent DEL record | Evidence and authorizations of the current revision |

## Execution in the repository

Technical stack: Python 3.12+, async/await, Docker Compose, Playwright headless.
Use `docker compose up -d` to start engines. Run `python3 scripts/demo.py <url>`
to verify. All configuration via environment variables (see `.env.example`).
Do not hardcode secrets, proxy credentials, or API keys.

## Boundaries

Do not fill in human approval, generate silent documentation or treat a merge as
generic ratification. Do not publish, grant access, install skills or MCPs, or
enable CI on the basis of a template alone. Do not scrape sites without
considering the target's robots.txt and terms of service.
