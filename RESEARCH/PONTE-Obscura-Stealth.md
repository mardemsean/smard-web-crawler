# PONTE — Obscura Stealth Patterns → smard-web-crawler stealth.py

**Bridge document** linking Obscura headless engine stealth capabilities
to their Python reimplementation in `src/common/stealth.py`.

**Source**: `mardemsean/obscura-headless-web-scrapinr-agent` (study fork)
**Target**: `mardemsean/smard-web-crawler` `src/common/stealth.py`
**Date**: 2026-10-21

---

## Concepts that transfer

### 1. GREASE sec-ch-ua brand shuffling

**Obscura source**: `bootstrap.js` lines 8032–8047
**Pattern**: Chrome randomizes three entries in the `sec-ch-ua` header — one
real Chrome brand, one Chromium brand, and one GREASE decoy with
non-alphanumeric characters. The order is shuffled per session.

**Why it matters**: Bot detectors fingerprint the static order of `sec-ch-ua`
brands. Headless Chrome and naive scrapers emit a fixed order that differs
from real browsers, which rotate the GREASE entry and shuffle positions.

**Python implementation**: `grease_sec_ch_ua(fp)` generates the header from a
`SessionFingerprint` seed. The GREASE brand uses the same character set as
Chrome's algorithm (`" ( : - . / ) ; = ? _"`). The shuffle is
deterministic per session seed, so repeated requests within a session
produce the same order.

**Verification**: Check that:
- Output contains exactly three quoted brand entries
- One entry contains a non-alphanumeric GREASE character
- Order varies across different seeds
- Order is stable within the same seed

### 2. Per-session seeded fingerprint noise (`_fpRand`)

**Obscura source**: `bootstrap.js` `_fpSeed` / `_fpRand(salt)` pattern
**Pattern**: A single per-session seed drives all fingerprint-surface noise
through a deterministic hash function. Canvas pixel noise, AudioContext
frequency values, battery level, screen dimensions, and hardware concurrency
all derive from `hash(seed + surface_name)`.

**Why it matters**: Random-per-request fingerprint values create a different
identity on every page load — itself a bot signal. Real browsers have
consistent hardware characteristics within a session. Seeded noise gives
each session a unique but internally stable identity.

**Python implementation**: `SessionFingerprint` class with `fp_rand(salt)`
producing deterministic floats via `SHA-256(seed:salt)`. Surface-specific
methods (`canvas_noise()`, `audio_context_noise()`, `battery_level()`,
`screen_color_depth()`) wrap `fp_rand` with appropriate ranges.

**Verification**: Check that:
- Same seed + salt always returns the same value
- Different salts produce different values
- Values fall within documented ranges
- The profile selection is deterministic per seed

### 3. Prototype-chain navigator property placement

**Obscura source**: `bootstrap.js` navigator override section
**Pattern**: Override `navigator.webdriver`, `navigator.plugins`,
`navigator.hardwareConcurrency`, `navigator.userAgentData` etc. by placing
getters on `Navigator.prototype` via `Object.defineProperty`, NOT as own
properties on the `navigator` instance.

**Why it matters**: Bot detectors call
`navigator.hasOwnProperty('webdriver')` — if it returns `true`, the property
was set by automation tooling (Playwright, Puppeteer) rather than inherited
from the prototype chain as in real browsers.

**Python implementation**: `navigator_stealth_script(fp)` generates a JS
snippet for injection via Playwright's `page.add_init_script()`. The script
places all overrides on `Object.getPrototypeOf(navigator)` and includes:
- `webdriver: false`
- `hardwareConcurrency` and `deviceMemory` from `_fpRand`
- `plugins` array with 5 PDF viewer entries (Chrome standard)
- `userAgentData` with GREASE brands matching the HTTP headers

**Verification**: After injection, `navigator.hasOwnProperty('webdriver')`
returns `false` and `navigator.webdriver` returns `false`.

### 4. Cross-surface profile consistency

**Obscura source**: `profiles.rs` `BrowserProfile` struct
**Pattern**: UA string, `navigator.platform`, `sec-ch-ua-platform`,
`platformVersion`, `architecture`, `bitness`, and browser version are all
derived from a single `BrowserProfile`. Inconsistency across these surfaces
is a detection vector.

**Python implementation**: `BrowserProfile` frozen dataclass binds all
identity surfaces. `SessionFingerprint` selects one profile per session.
`stealth_headers()` and `navigator_stealth_script()` both read from the
same profile, guaranteeing HTTP headers match JS-injected values.

---

## Concepts that do NOT transfer

### Rust wreq TLS fingerprint impersonation

**Obscura**: Uses BoringSSL via `wreq` to reproduce Chrome's exact TLS
ClientHello (cipher suite order, ALPN, extensions). This defeats JA3/JA4
fingerprinting at the TLS layer.

**Why it doesn't transfer**: Python's `httpx`/`aiohttp` use their own TLS
stacks (OpenSSL via `ssl` module). Matching Chrome's ClientHello requires
either a Rust/C library binding or routing through a proxy that handles TLS
impersonation. Our Level 1 residential proxy and Level 2 Site Unblocker
already handle TLS at the proxy layer, making this moot for our architecture.

### V8 bootstrap.js execution context

**Obscura**: 16K lines of JS that run in a V8 isolate before any page
script, capturing `deno_core` bridge in a closure and deleting the `Deno`
global. This is a Rust-native V8 embedding.

**Why it doesn't transfer**: We use Playwright (Chromium), which has its
own JS execution context. We inject stealth overrides via
`page.add_init_script()` instead — same effect, different mechanism.

### CDP server and MCP tools

**Obscura**: Exposes 32 JSON-RPC tools for browser automation via CDP.

**Why it doesn't transfer**: We use Playwright's API directly, which
already speaks CDP under the hood.

### Tracker domain blocklist

**Obscura**: 3520+ domains from the PGL ad blocklist with subdomain matching.

**Why it doesn't transfer directly**: We scrape for content, not for
browsing. Blocking tracker domains could break pages that gate content
behind analytics. However, the blocklist could be ported as an optional
resource filter in the future.

---

## Integration path

```
Obscura (Rust/V8)          smard-web-crawler (Python/Playwright)
─────────────────          ──────────────────────────────────────
profiles.rs BrowserProfile → BrowserProfile dataclass (stealth.py)
bootstrap.js GREASE algo   → grease_sec_ch_ua() function
bootstrap.js _fpRand       → SessionFingerprint class
bootstrap.js navigator     → navigator_stealth_script() JS template
wreq TLS impersonation     → Handled by proxy layer (Levels 1–3)
tracker blocklist           → Future: optional resource filter
```

**Implementation order**:
1. `BrowserProfile` dataclass with 3 pre-built profiles (win/mac/linux)
2. `SessionFingerprint` with seeded `fp_rand()` and profile selection
3. `grease_sec_ch_ua()` and updated `stealth_headers()` using profiles
4. `navigator_stealth_script()` JS template for Playwright injection
5. Updated `simulate_human()` using session-seeded timing

**Backward compatibility**: `random_user_agent()` remains as a convenience
function returning a profile's UA string. `stealth_headers()` gains an
optional `SessionFingerprint` parameter; without it, creates a one-shot
fingerprint (matching old behavior of random per-call).
