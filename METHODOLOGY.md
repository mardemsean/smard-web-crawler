# Methodology — from discomfort to production

**State:** implementation authorized; operational details remain proposed
wherever no explicit decision exists.
**Scope:** this repository implements a self-hosted web scraping toolkit; the
method governs its documentary lifecycle per smard-agent-flow.
**Origin:** session of 2026-10-20 on self-hosted web scraping infrastructure
with Crawl4AI and Firecrawl.

## Intent

To provide autonomous agents with high-quality web data extraction at zero
per-request cost, using self-hosted open-source engines that match or exceed the
efficiency of paid APIs. The four technical pillars: identical rendering engine
(Playwright headless), local extraction algorithms (BM25, pruning, semantic
blocks), zero-latency localhost communication, and managed anti-bot bypass
(proxy rotation + stealth mode).

## Cycle and entry points

Intent synthesis → architectural decision (self-hosted over paid) →
implementation → Docker orchestration → unified scraper interface → anti-bot
layer → testing → delivery → observation and iteration.

This project entered the cycle at implementation, with mature intent and a clear
architectural decision. The exploration phase was conducted in prior dialogue;
its conclusions informed the technical choices directly.

## Documents that accompany maturation

Documents are created when their triggers occur, per R5. The foundational
decision is recorded in `adrZERO.md`. Requirements, specifications, and
delivery records will be created when their respective triggers arise.

## Infrastructure and executors

The method's rules, prompts, and templates are incorporated from
smard-agent-flow-git. Specific tools receive adapters, not competing versions
of the policy.
