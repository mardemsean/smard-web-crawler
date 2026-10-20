# Component Exploration

Evaluated components and external tools for potential integration with the smard-web-crawler three-level fallback architecture.

---

## Evaluation Summary

| Component | Verdict | Category | Integration Path |
|---|---|---|---|
| rota | **Extract patterns** | Proxy manager | Design patterns adopted (retry, liveness, cascade) |
| CloakBrowser | **Reverse-engineer concepts** | Stealth browser | Fingerprint techniques → stealth.py (v155 Pro installed locally) |
| Obscura | **Extract stealth patterns** | Headless browser engine | GREASE, _fpRand noise, navigator prototype chain → stealth.py |
| AutomatiQ | **Fork for integration** | MCP reverse-engineering | CDP-to-HTTP extraction for scraper agents |
| WebClaw | **Monitor** | Self-hosted scraper | Reference architecture, no direct use |
| mubeng | **Skip** | Proxy rotator | Go binary, our proxy layer handles rotation |
| spoofdpi | **Skip** | DPI circumvention | Solves a different problem (censorship, not scraping) |
| Proxy-Scraper-2026-GUI | **Skip** | Free proxy scraper | Free proxies too unreliable for production |
| VPSLab-Free-Proxy-List | **Skip** | Free proxy list | Same as above — unreliable for production |

---

## Detailed Evaluations

### rota (alpkeskin/rota)

**Category:** Proxy management and rotation framework (Go)
**Stars:** ~1.2k | **License:** MIT

**What it does:**
Dual-path proxy pool manager with intelligent health tracking, rotation strategies, and fallback chains. Written in Go with a clean architecture (docs/diagrams available).

**Design patterns extracted and adopted:**

1. **Retry intra-engine** — Try variant parameters within the same engine before escalating to the next. Example: Crawl4AI tries pruning → bm25 → semantic strategies before falling back to Firecrawl. *Implemented in `UnifiedScraper.scrape()`.*

2. **Periodic liveness** — Don't just check engines at startup. Recheck on failure and on a configurable timer (`LIVENESS_INTERVAL = 300s`). Stale health data causes unnecessary escalation. *Implemented via `_maybe_refresh_health()` and `_recheck_failed_engines()`.*

3. **Pool cascade with recheck** — During long batch operations, periodically re-verify previously-failed engines. If they recover, promote them back into the fallback order. Prevents a transient outage from permanently degrading batch throughput. *Implemented in `scrape_batch()` with `BATCH_RECHECK_INTERVAL`.*

4. **Dual-path entry** (future) — Route requests through two parallel paths simultaneously and take the first success. Useful for high-value scrapes where latency matters more than cost. *Not yet implemented — candidate for v2.*

**Verdict:** Patterns extracted and implemented. No code dependency needed.

---

### CloakBrowser

**Category:** Stealth Chromium fork with source-level fingerprint patches
**Stars:** ~32k | **License:** MIT wrappers, proprietary binary core

**What it does:**
87 C++ Chromium source-level patches that defeat fingerprinting at the browser engine level — not JS injection like playwright-stealth. Covers: canvas, WebGL, audio context, TLS JA3/JA4 fingerprints, CDP detection evasion, font enumeration, WebRTC leak prevention, navigator property consistency.

**Key differentiator:** Patches are compiled into the Chromium binary, making them invisible to JavaScript-based detection. Playwright-stealth injects JS that anti-bot systems can detect; CloakBrowser's modifications are below the JS layer.

**Playwright compatibility:** Exposes standard CDP protocol, usable as a Playwright browser binary via `executablePath`.

**Free edition:** Available. User has confirmed intent to use for testing.

**Installation status:** CloakBrowser v155 Pro (Chrome/155) installed and tested headless on local Windows development environment. License key stored in DPAPI at `~\.smard\secrets\cloakbrowser.key.dpapi`. Launch via `launch-agent-browser.ps1` (loads DPAPI key automatically). Limit: 1 concurrent session. Not present in cloud container — local-only.

**Reverse engineering plan:**
The goal is not to use CloakBrowser as a dependency but to extract concepts, techniques, and architectural decisions applicable to our stealth layer:

1. **Install free edition** — Obtain and install the CloakBrowser binary in the development environment
2. **Identify patch categories** — Catalog the 87 patches by anti-detection domain (canvas, WebGL, TLS, CDP, etc.)
3. **Map to our stealth.py** — Determine which techniques can be implemented via Playwright CDP commands or browser args without Chromium source modification
4. **Benchmark against DataDome tiers** — Test CloakBrowser vs playwright-stealth vs bare Chromium against known protection levels
5. **Document findings** — Add technique catalog to this RESEARCH folder

**Relevant techniques to investigate:**
- Canvas fingerprint noise injection (can be done via CDP `Runtime.evaluate`)
- WebGL renderer/vendor string spoofing (browser launch args)
- TLS fingerprint randomization (requires binary-level or proxy-level changes)
- CDP detection evasion (some achievable via Playwright stealth patches)
- Navigator consistency (user-agent, platform, hardware concurrency alignment)

**Verdict:** High-value for concept extraction. Install and reverse-engineer.

---

### AutomatiQ (AstroTechLab/AutomatiQ)

**Category:** MCP-first browser session recorder and HTTP reverse-engineering
**Stars:** Growing | **License:** Open source
**Fork:** `mardemsean/AutomatiQ-web-reverse-engineering-for-agents`

**What it does:**
Records browser sessions via CDP, captures all network traffic, then uses AI to reverse-engineer the underlying HTTP requests — extracting the minimal request sequence needed to replicate what the browser did. Exposes this via MCP protocol for LLM agent consumption.

**Why it matters for us:**
- Converts browser-dependent scraping workflows into lightweight HTTP-only requests
- Reduces cost by eliminating unnecessary browser rendering when the data is available via direct API calls
- DataDome tier analysis (from their research): ~60% of sites have no bot protection, ~25-35% light, ~10-15% medium → most scraping doesn't need heavy stealth

**Integration path:**
1. Use AutomatiQ to profile target sites before choosing engine
2. Sites with extractable HTTP APIs → direct httpx requests (cheapest)
3. Sites requiring JS rendering → Crawl4AI/Firecrawl
4. Sites with heavy protection → Site Unblocker / Web Data API

**Verdict:** Fork maintained. Integrate as pre-scrape reconnaissance tool.

---

### WebClaw

**Category:** Self-hosted web scraping platform
**Stars:** Moderate | **License:** Open source

**What it does:**
Full-featured self-hosted scraping platform with queue management, scheduling, proxy rotation, and result storage. Designed for team use with a web UI.

**Evaluation:**
- Overlap with our architecture: significant — we already have Crawl4AI + Firecrawl for self-hosted scraping
- Queue/scheduling: we don't need it at the scraper level (handled by the agent layer above)
- Proxy rotation: our Decodo residential proxy handles this
- No unique capability that our three-level fallback doesn't cover

**Verdict:** Monitor for ideas. No integration needed — our stack already covers this space.

---

### mubeng (kitabisa/mubeng)

**Category:** Proxy rotator and IP checker (Go binary)
**Stars:** ~3k | **License:** Apache-2.0

**What it does:**
Takes a list of proxy URLs, rotates them per-request or per-IP, checks proxy liveness, supports HTTP/SOCKS5. Designed as a standalone proxy rotation layer.

**Evaluation:**
- Our proxy rotation is handled by Decodo residential proxy (built-in rotation via `gate.decodo.com:7000`)
- mubeng is useful for free proxy lists but we deliberately avoid free proxies for reliability
- Would add a Go binary dependency for functionality we already have
- If we ever need to manage multiple paid proxy providers, mubeng's rotation logic could be relevant

**Verdict:** Skip. Decodo handles rotation natively.

---

### spoofdpi (xvzc/spoofdpi)

**Category:** DPI (Deep Packet Inspection) circumvention tool (Go)
**Stars:** ~4k | **License:** Apache-2.0

**What it does:**
Fragments TLS ClientHello packets to evade DPI-based censorship. Works as a local proxy that splits the SNI field across TCP segments.

**Evaluation:**
- Solves internet censorship, not bot detection — different problem domain
- Our scraping targets are commercial websites with anti-bot protection, not government firewalls
- Could theoretically help if scraping from restricted network environments, but our infrastructure runs from cloud VPS
- Decodo residential proxies already route through residential IPs that bypass geographic restrictions

**Verdict:** Skip. Solves a different problem.

---

### Proxy-Scraper-2026-GUI

**Category:** GUI tool for scraping free proxy lists
**Stars:** Low | **License:** Open source

**What it does:**
Scrapes free proxy lists from public sources, tests them, exports working proxies. Has a Qt GUI.

**Evaluation:**
- Free proxies are unreliable: high latency, frequent downtime, shared abuse, often blocked by anti-bot systems
- Our architecture pays for quality (Decodo residential at $3/GB) specifically to avoid free proxy problems
- Detection rates on free proxies are very high because they're shared across thousands of users
- No production use case in our stack

**Verdict:** Skip. Free proxies incompatible with our reliability requirements.

---

### VPSLab-Free-Proxy-List

**Category:** Curated free proxy list
**Stars:** Low | **License:** Open source

**What it does:**
Maintains a regularly-updated list of free HTTP/SOCKS proxies from various sources.

**Evaluation:**
Same issues as Proxy-Scraper-2026-GUI above. Free proxies are not viable for production scraping against sites with any bot protection.

**Verdict:** Skip. Same rationale as above.

---

### Obscura (mardemsean/obscura-headless-web-scrapinr-agent)

**Category:** Rust headless browser engine with stealth transport
**License:** Apache 2.0 | **Binary:** ~70MiB | **Memory:** ~30MB per page

**What it does:**
Full headless browser engine in Rust: V8 via deno_core, own DOM/layout/paint pipeline, CDP-compatible (Puppeteer/Playwright drop-in). Stealth mode operates at three layers:

1. **TLS fingerprint** (wreq/BoringSSL): Chrome 145/Windows ClientHello, cipher order, ALPN
2. **HTTP headers**: Chrome client hints with GREASE brand shuffling algorithm, Sec-Fetch-* metadata, referrer policy
3. **JS runtime**: 16K-line bootstrap.js with 200+ non-enumerable internal globals, prototype-chain navigator getters, seeded per-session fingerprint noise (canvas, audio, battery, geolocation)

**Key stealth techniques extractable for stealth.py:**

1. **GREASE sec-ch-ua algorithm** (bootstrap.js:8032-8047) — Generates browser brand lists with correct permutation order and GREASE tokens based on Chrome major version. Our stealth.py sends no client hints at all.

2. **`_fpRand` seeded noise model** (bootstrap.js:705-785) — One seed per session generates deterministic noise for canvas, audio context, battery, screen, GPU renderer. Produces consistent-but-unique fingerprints. Our stealth.py has zero fingerprint surface coverage.

3. **Prototype-chain navigator placement** (bootstrap.js:8148-8203) — Navigator getters on a thin prototype above `Navigator.prototype`, not as own properties. Own accessors are a bot tell detectable by `Object.getOwnPropertyDescriptor(navigator, 'userAgent')`. Our stealth.py doesn't touch navigator properties.

4. **Cross-surface consistency** (profiles.rs) — UA string, `navigator.platform`, `navigator.userAgentData.platform`, `platformVersion` all derive from a single `BrowserProfile`. Our stealth.py has 5 random UAs with no cross-surface consistency.

5. **Connection-reset retry** (wreq_client.rs) — Automatic retry on TCP reset, maps directly to our intra-engine retry pattern.

6. **Tracker blocklist** (blocklist.rs) — 3520+ domains from PGL list with subdomain matching. Could serve as resource filter in our pipeline.

**Stealth limitations (documented honestly by upstream):**
- No Cloudflare challenges, Datadome, Akamai active challenges, CAPTCHAs
- No passive TCP/IP stack fingerprinting (Linux SYN ≠ Windows/macOS — kernel-level, unsolvable in userspace)
- WebGL returns null (no GPU renderer)
- Profile rotation without matching TLS/timezone is a bot signal

**Full analysis:** See `Obscura-Decipher.md` and `Obscura-SmardAgentFlow-Analyze.md` in this directory.

**Verdict:** Extract stealth patterns 1-4 for stealth.py. Do not adopt as runtime dependency (Rust binary, different architecture).

---

## Architecture Decisions Log

### 2024-10 — Three-level fallback adopted

**Decision:** Route all scraping through a three-level escalation chain.
**Rationale:** Cost optimization with reliability guarantee. Level 1 (self-hosted + residential proxy) covers ~85% of scrapes at $3/GB. Level 2 (Site Unblocker) handles anti-bot sites at $5.50/GB. Level 3 (Web Data API) is the guaranteed fallback at $0.40-1.25/1K requests.

### 2024-10 — rota patterns adopted

**Decision:** Implement retry intra-engine, periodic liveness, and pool cascade with recheck.
**Rationale:** Reduces unnecessary escalation. Without intra-engine retry, a single Crawl4AI strategy failure immediately escalates to a more expensive engine. Without liveness rechecks, a transient container restart causes permanent degradation until manual intervention.

### 2024-10 — CloakBrowser reverse engineering planned

**Decision:** Extract stealth techniques from CloakBrowser rather than adopt it as a dependency.
**Rationale:** Proprietary binary core creates vendor lock-in risk. The techniques (fingerprint patching, CDP evasion) can be partially replicated via Playwright CDP commands and browser args. Understanding what CloakBrowser patches reveals what anti-bot systems detect.

### 2024-10 — Obscura stealth patterns extraction planned

**Decision:** Extract GREASE, _fpRand noise model, prototype-chain navigator placement, and cross-surface consistency patterns from Obscura for stealth.py.
**Rationale:** Obscura implements the most complete open-source stealth at three layers (TLS, HTTP headers, JS runtime). The Rust binary itself is not usable as a Python dependency, but the techniques documented in bootstrap.js (16K lines, fully readable) and wreq_client.rs are directly translatable. Current stealth.py has 5 random UAs with no fingerprint surface coverage — these patterns close the gap without adding a binary dependency.

### 2024-10 — AutomatiQ fork maintained

**Decision:** Maintain fork at `mardemsean/AutomatiQ-web-reverse-engineering-for-agents`.
**Rationale:** MCP-based HTTP reverse engineering enables a "level 0" optimization: bypass browser rendering entirely for sites where direct HTTP requests work. Reduces cost and latency for the ~60% of sites with no meaningful bot protection.
