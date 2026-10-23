# 0001 — Obscura as a crawler engine (decision D1)

**Status:** adopted 2026-10-22, revised 2026-10-23 with SMardSERVER evidence.
The operator delegated the call and made it conditional on complete tests
against Obscura. This record holds those results.
**Question:** adopt Obscura as a self-hosted engine in the fallback chain, or only
extract its stealth patterns into `stealth.py`?

## Evidence

Battery: `smard-crawler bench`. It runs 10 functional tests on local fixtures,
20 stealth probes, timing and RSS, plus online TLS, header and sannysoft checks.
5 rounds per engine.

### SMardSERVER: Windows 11, 16 CPUs, direct egress (authoritative)

Raw data: [docs/bench/smardserver/](../bench/smardserver/report.md).

| Engine | Functional | Stealth | Static load p50 | 8-page concurrency p50 | Cold start p50 | RSS | sannysoft failed |
|---|---|---|---|---|---|---|---|
| CloakBrowser 155 (pro) | 100% | **100%** | 45 ms | 293 ms | 770 ms | 465 MB | **0** |
| Obscura 0.2.5 `--stealth` | 100% | 90% | **27 ms** | 204 ms | 520 ms | **80 MB** | 3 |
| Obscura 0.2.5 (no stealth) | 100% | 90% | 27 ms | 204 ms | 524 ms | 78 MB | 3 |
| Chromium 156 headless | 100% | 70% | 30 ms | 178 ms | 68 ms | 259 MB | 12 |
| Chromium 156 + `stealth.py` | 100% | 75% | 28 ms | 166 ms | 67 ms | 261 MB | 6 |

| Engine | JA4 | HTTP |
|---|---|---|
| CloakBrowser | `t13d1517h2_8daaf6152771_cb7bf5808d99`, the most common Chrome-on-Windows JA4 (Chrome 153-156) | h2 |
| Obscura `--stealth` | `t13d1516h2_8daaf6152771_d8a2da3f94cd`, a genuine Chrome JA4 but the uTLS `HelloChrome_Auto` one, seen mostly on Linux and older Chrome | h2 |
| Obscura (no stealth) | `t13d1011h1_61a7ad8aa9b6_3fcd1a44f3e3`, non-Chrome | HTTP/1.1 |
| Chromium headless | `t13d1516h2_8daaf6152771_806a8c22fdea` | h2 |

All h2 engines share the Akamai HTTP/2 fingerprint `52d84b11737d980aef856699f885ca86`.

### Cloud VM: Linux, 4 CPUs, behind a TLS-intercepting proxy

Functional and stealth-probe results matched Windows: Obscura at 90%, Chromium
at 70%. Obscura used 107 MB against Chromium's 413 MB. The TLS numbers from that
host are invalid. Every engine reported the proxy's own ClientHello (`t13d911_...`)
over HTTP/1.1, so they are not used here.

### Remaining tells

- **Obscura:** no WebGL (`webgl_real_gpu` at 0%), and the `console.debug`
  Error-stack getter fires (`cdp_runtime_hidden` at 0%). Its JA4 is real Chrome,
  but it is less common for a Windows UA.
- **CloakBrowser:** none in this battery. It reports the host's real GPU through
  WebGL (RTX 5080, Direct3D11).
- **`stealth.py`:** its getters are not native functions. A platform mismatch
  (Linux profile UA on a Windows host) was found and fixed: the script now sets
  `navigator.platform`, and the bench selects the host OS profile so Web Workers
  agree.

## Decision

1. **Obscura stays engine #1** in the default `ENGINE_ORDER`. It is the fastest
   and lightest engine (27 ms static load, 80 MB, about 6x less memory than
   CloakBrowser), has full functional parity, and runs many sessions in parallel.
   Use only stealth builds: the `-stealth` release or `docker/obscura`. Without
   stealth it is detectable at the TLS and HTTP layer.
2. **CloakBrowser is the escalation engine for protected targets.** It has the
   best stealth on every axis (100% of probes, 0 sannysoft failures, the most
   common Windows Chrome JA4), but the free tier limits it to one session and it
   uses about 465 MB. For a single hard target, or a site known to check WebGL or
   CDP, call `engine="cloakbrowser"`, or put it first with
   `ENGINE_ORDER=cloakbrowser,obscura,...`.
3. Keep Crawl4AI and Firecrawl in the chain for heavy-JS pages and crawls.
4. `stealth.py` stays a library. Obscura and CloakBrowser patch below
   JavaScript, so it is not wired into them, and it is not wired into Crawl4AI,
   which has its own `enable_stealth`.

## Follow-ups

- Run the Decodo three-level smoke test with real credentials (pending operator credentials).
- Repeat `--online` through the residential proxy, and set `OBSCURA_TIMEZONE`
  and `OBSCURA_GEOLOCATION` to the proxy's exit region. The host reports
  America/Bahia; Obscura's own default is Europe/Berlin.
