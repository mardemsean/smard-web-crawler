# Obscura — /decipher Analysis

## Gist

Rust headless browser engine. V8 via deno_core. Own DOM/layout/paint pipeline.
CDP-compatible drop-in for headless Chrome. 30MB memory, ~70MiB binary.
Stealth mode: wreq/BoringSSL TLS fingerprint impersonation (Chrome 145/Windows),
16K-line JS bootstrap with full navigator/canvas/audio/WebGL fingerprint spoofing,
3520+ tracker domain blocklist, 8 browser profiles with env-var rotation control.

## Bottom line

Obscura is the most complete open-source stealth headless engine available —
it operates at three layers (TLS fingerprint, HTTP headers with Chrome client hints
GREASE algorithm, and JS runtime fingerprint surfaces) that together defeat basic
and intermediate bot detection. It does NOT handle Cloudflare challenges, Datadome,
Akamai active challenges, CAPTCHAs, or passive TCP/IP stack fingerprinting (Linux
vs macOS SYN packet differences), which it documents honestly.

## Self-check

Verified: cloned repo, read 10+ source files totalling ~25K lines including
wreq_client.rs (942 lines), client.rs (2985 lines), bootstrap.js (16K+ lines),
profiles.rs, blocklist.rs, lib.rs, MCP server (lib.rs, 32 tools), CLI main.rs,
and stealth documentation. All claims cross-checked against source.

## Terms

- **wreq**: Rust HTTP client library with TLS fingerprint impersonation (BoringSSL)
- **GREASE**: Generate Random Extensions And Sustain Extensibility — Chrome's
  sec-ch-ua brand shuffling algorithm (line 8032-8047 of bootstrap.js)
- **SSRF guard**: Server-Side Request Forgery protection — blocks loopback,
  RFC1918, link-local, CGNAT, 6to4, NAT64, Teredo IPv6 translation bypasses
- **CDP**: Chrome DevTools Protocol — the wire protocol Puppeteer/Playwright use
- **obstacle course**: 33-stage behavioral test gate in companion repo

## Needs you

- **Stealth feature requires CMake**: BoringSSL builds through CMake;
  without it, `--features stealth` fails silently at link time
- **V8 first build is ~5 min + GB disk**: deno_core compiles V8 from source;
  incremental builds are seconds but initial is heavy
- **TCP/IP fingerprinting is unsolvable in userspace**: Linux SYN packets
  differ from Windows/macOS at kernel level — must run in matching VM/container
  or route through proxy with correct TCP stack
- **Profile rotation is opt-in and risky**: One IP cycling identities is a
  bot signal; rotation lacks matching TLS/timezone fingerprint per profile
- **nextest required, not cargo test**: V8 holds one isolate per process;
  `cargo test` puts all tests in one process and they fail

## How it works

1. **CLI parses args** (clap): `--stealth` flag propagates to BrowserContext
   which selects wreq transport + tracker blocklist + profile injection
2. **wreq_client.rs builds TLS session**: `Profile::Chrome145, Platform::Windows`,
   BoringSSL cipher order, ALPN, ClientHello match real Chrome — connection reset
   triggers automatic retry
3. **bootstrap.js (16K lines) executes in V8 context**: pre-declares ~200 internal
   globals as non-enumerable, captures deno_core bridge in closure, deletes
   `Deno` global before page script runs
4. **Navigator prototype chain spoofed**: webdriver=false, plugins (5 PDF viewers),
   mimeTypes, userAgentData with GREASE brands, hardwareConcurrency, deviceMemory
   — all on prototype hop (own accessors = bot tell, so they use defineProperty
   on prototype)
5. **Fingerprint surfaces per-session seeded**: `_fpRand(salt)` from `_fpSeed`
   generates deterministic-per-session canvas noise, audio context values,
   battery level, geolocation jitter, screen dimensions, GPU renderer string
6. **MCP server exposes 32 JSON-RPC tools**: browser_snapshot with element refs,
   click/type/select by ref, screenshot, tab management, cookie/storage access,
   console capture — agents use refs not CSS selectors

## What changes

- **For smard-web-crawler**: Extract three stealth concepts — (a) the GREASE
  sec-ch-ua algorithm for header consistency, (b) the `_fpRand` seeded
  per-session fingerprint noise model for canvas/audio, (c) the prototype-chain
  placement of navigator getters (own accessors are a bot tell)
- **wreq transport pattern**: Connection-reset retry with configurable attempts
  maps directly to our intra-engine retry pattern
- **Tracker blocklist**: 3520+ domains from PGL list with subdomain matching
  — can be ported as a resource filter in our pipeline
- **Profile consistency model**: UA string, platform, ua_platform,
  ua_platform_version must agree across all surfaces — our stealth.py
  currently has 5 random UAs with no cross-surface consistency

## Held back

WebGL returns null (no GPU renderer) — detectable by sites that expect a
renderer string. No iframe isolation for fingerprint surfaces (all frames
share one `_fpSeed`). Font enumeration is static (no system font probing).
`chrome.csi()` and `chrome.loadTimes()` use random timing rather than real
navigation timing. PerformanceObserver entries are synthetic. No Web
Bluetooth, Web USB, Web Serial, or WebXR stubs — absence itself is
fingerprintable on Chrome where these exist.
