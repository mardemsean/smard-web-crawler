# Obscura — /smard-agent-flow:analyze Audit Report

**Repo**: `mardemsean/obscura-headless-web-scrapinr-agent`
**Audit scope**: Read-only documentary chain audit per smard-agent-flow methodology
**Date**: 2026-10-20

---

## Documentary Chain Audit

### ZERO (Zero-State Assessment)
**Status**: ABSENT

No ZERO document exists. This is an external upstream project (forked from
the Obscura open-source headless browser), not an internally commissioned
deliverable. A zero-state assessment was never initiated because the fork
was acquired for study and integration, not for development under smard
methodology.

**Impact**: Low — appropriate for an external fork. If modifications are
planned (beyond study), a ZERO should be created before the first commit.

### PREFLIGHT-ADR (Architecture Decision Record)
**Status**: ABSENT (partial equivalent exists)

No formal PREFLIGHT-ADR. The `AGENTS.md` file serves as an informal
architecture guide covering:
- Build instructions with feature flags
- Test methodology (nextest, obstacle course 33/33)
- 10-crate architecture breakdown
- Stealth mode description
- Robustness invariants (panic=unwind, 20-redirect limit, SSRF guard)

**Divergence**: AGENTS.md is upstream-authored guidance for contributors,
not a decision record. It documents WHAT but not WHY decisions were made
(e.g., why V8 via deno_core instead of SpiderMonkey, why wreq over
reqwest for stealth, why BoringSSL instead of rustls for TLS impersonation).

### PONTE (Bridge Document)
**Status**: ABSENT

No bridge document linking upstream capability to smard-web-crawler
integration. The relationship between this fork and the consuming project
is implicit (referenced in `RESEARCH/Exploration.md` in the parent repo).

**Recommendation**: Create a PONTE documenting:
1. Which stealth concepts transfer (GREASE algorithm, _fpRand noise model,
   prototype-chain navigator placement)
2. Which do NOT transfer (Rust-only wreq transport, V8 bootstrap.js, CDP server)
3. Integration path (extract patterns, not code — Python reimplementation)

### Specs (Specification Documents)
**Status**: ABSENT (upstream docs serve as equivalent)

23 documentation files in `docs/` cover operational specifications:
- `Configure-stealth-and-proxies.md` — stealth capabilities and limitations
- `Environment-variables.md` — full configuration surface
- `Use-with-Playwright.md`, `Use-with-Puppeteer.md` — integration guides
- `Use-the-MCP-server.md` — agent integration

These are user-facing docs, not formal specs with acceptance criteria.

### Tasks
**Status**: ABSENT

No task tracking documents. Issues are on the upstream GitHub. The fork
has no `.github/ISSUE_TEMPLATE`, no project board, no task list.

### PR (Pull Request Chain)
**Status**: NOT APPLICABLE

This is a study fork. No PRs have been opened against it from the smard
side. The upstream commit history is intact at depth-1 clone.

### DEL (Deliverable / Deployment Record)
**Status**: ABSENT

No deployment record. The fork is not deployed — it exists for code study
and concept extraction.

---

## R3 Ratification Check

**R3**: "Every decision that changes scope, stack, or timeline must be
ratified in an ADR before implementation begins."

**Finding**: No scope/stack/timeline decisions have been made against this
fork. The decision to study Obscura is recorded in
`web-scraper-toolkit/RESEARCH/Exploration.md` (parent repo), which serves
as an informal ratification. However, the specific decision to extract
GREASE, _fpRand, and prototype-chain patterns for stealth.py has NOT been
formally ratified.

**Recommendation**: Add an ADR entry to Exploration.md or create a formal
PREFLIGHT-ADR before implementing extracted patterns in stealth.py.

## R5 Check (Files Created Only When Triggered)

**Finding**: COMPLIANT by absence. No smard-methodology files were created
in this repo. The repo contains only upstream content.

## R6 Duplication Check

**Finding**: No duplication detected. The fork is a clean depth-1 clone
with no added files, no parallel documentation, no copied-and-modified
variants of upstream code.

---

## Material Conflicts

1. **Typo in repo name**: `obscura-headless-web-scrapinr-agent` — "scrapinr"
   is missing the 'g'. This propagates into all GitHub URLs and clone paths.
   Non-blocking but creates confusion in documentation references.

2. **Stealth claims vs. reality gap**: The README and AGENTS.md describe stealth
   as handling "basic bot detection" but bootstrap.js implements sophisticated
   multi-surface fingerprint spoofing (canvas noise, audio context, battery,
   geolocation, navigator prototype chain, WebGL null, GREASE brands). The
   documentation undersells the capability, which could lead to underestimation
   during integration planning.

3. **Profile consistency warning underdocumented**: The critical constraint that
   profile rotation WITHOUT matching TLS fingerprint and timezone is a bot signal
   is buried in `Configure-stealth-and-proxies.md` but absent from AGENTS.md and
   README. An agent working from AGENTS.md alone would miss this constraint.

---

## Summary Verdict

| Chain Link | Status | Severity |
|---|---|---|
| ZERO | Absent | Low (external fork) |
| PREFLIGHT-ADR | Absent (AGENTS.md partial) | Medium |
| PONTE | Absent | **High** — needed before integration |
| Specs | Absent (docs/ partial) | Low |
| Tasks | Absent | Low (study fork) |
| PR | N/A | — |
| DEL | Absent | Low (not deployed) |

**Overall**: The fork is clean but undocumented from a smard methodology
perspective. The single high-severity gap is the missing PONTE document
that should bridge Obscura's stealth patterns to the smard-web-crawler
stealth.py implementation. Without it, the integration path is implicit
and unratified.
