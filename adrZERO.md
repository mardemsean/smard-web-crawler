# ADR-0000 — Self-hosted scraping engines over paid APIs

**Status:** accepted (foundational decision).
**Date:** 2026-10-20 (implementation session).
**Scope:** this project's technical architecture.

## Context

Web scraping for autonomous agents (like Claude Code) requires converting
dynamic web pages to clean Markdown. Two approaches exist:

1. **Paid APIs** (Firecrawl cloud, ScrapingBee, etc.): managed infrastructure
   with proxy rotation and anti-bot bypass, but per-request costs and rate limits.
2. **Self-hosted engines** (Crawl4AI, Firecrawl self-hosted): identical
   algorithms running locally, with zero per-request cost and no rate limits, but
   requiring self-managed infrastructure for anti-bot bypass.

The technical analysis established that the code converting HTML to Markdown is
identical between paid and self-hosted versions. The rendering engine (Playwright
headless) is the same. The extraction algorithms (BM25, pruning, semantic blocks)
run locally in both cases. The only structural difference: who manages the
proxy rotation and anti-bot infrastructure.

## Decision

Build on **self-hosted engines** (Crawl4AI + Firecrawl) with a managed anti-bot
layer (residential proxy integration + playwright-stealth) to match the paid
API's bypass capabilities at zero per-request cost.

Concretely:

1. **Docker Compose** orchestrates Firecrawl API, Redis, and Crawl4AI server.
2. **Unified scraper interface** auto-routes to the best available engine.
3. **Proxy integration** via environment variable (`PROXY_URL`) for residential
   proxy rotation (BrightData, Oxylabs, Smartproxy).
4. **Stealth mode** via playwright-stealth patches and human behavior simulation.

## Alternatives considered

| Alternative | Why not |
| --- | --- |
| **Firecrawl paid API** | Per-request cost, rate limits, network latency; identical extraction quality to self-hosted |
| **Crawl4AI only** | Covers most cases but lacks Firecrawl's crawl-job orchestration for multi-page sites |
| **Firecrawl self-hosted only** | Missing Crawl4AI's advanced extraction strategies (BM25, pruning) |
| **Custom Playwright scripts** | Reinvents extraction algorithms already mature in both engines |

## Consequences

**Positive:**
- Zero per-request cost; unlimited volume.
- Localhost latency for agent ↔ scraper communication.
- Full control over proxy configuration and stealth behavior.
- Engine redundancy: if one is down, the other serves.

**Negative:**
- Requires Docker and adequate server resources (CPU, RAM).
- Proxy service subscription needed for anti-bot bypass at scale.
- Self-managed infrastructure: updates, monitoring, resource allocation.
