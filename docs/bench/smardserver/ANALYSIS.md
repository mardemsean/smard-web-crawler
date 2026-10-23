# SMardSERVER bench — reading of the results (2026-10-23)

Host: Windows 11 Pro for Workstations 10.0.26300, AMD Ryzen 7 8700G (16 threads), 47 GB RAM,
AMD Radeon 780M + Radeon RX 580, screen 2926x1646. Direct egress (no system proxy, Tailscale
without exit node, Windows Defender only). Files: `report.md`, `results.json` (5 rounds, online).

## Does Obscura `--stealth` / CloakBrowser carry the JA4 of Chrome outside the cloud proxy?

Measured by tls.peet.ws, compared against two independent sources: the Scrapfly JA4 observation
database (scrapfly.io/web-scraping-tools/ja4-fingerprint) and the FoxIO JA4+ README
(github.com/FoxIO-LLC/ja4), plus the measured uTLS table in github.com/North-web-dev/fingerprint-db.

| Engine | JA4 | What the databases say |
|---|---|---|
| cloakbrowser 155 | `t13d1517h2_8daaf6152771_cb7bf5808d99` | Most observed Chrome-on-Windows JA4 (Chrome 153–156, Windows and macOS); the canonical Chrome example in the FoxIO README. **Exact match with branded Chrome.** |
| obscura 0.2.5 `--stealth` | `t13d1516h2_8daaf6152771_d8a2da3f94cd` | A genuine Chrome JA4, but the one emitted by uTLS `HelloChrome_Auto`; observed mostly on Linux and older Chrome builds. Coherent with "a Chrome", not with the Chrome 145 on Windows that its User-Agent claims. |
| obscura 0.2.5 (no stealth) | `t13d1011h1_61a7ad8aa9b6_3fcd1a44f3e3`, HTTP/1.1 | Not a browser fingerprint. |
| Playwright chromium 156 | `t13d1516h2_8daaf6152771_806a8c22fdea` | Edge/Brave 154–156 on Windows, Chrome 155 on Android/Linux. Headless Chromium is not the right reference for "Chrome". |

Critical premise: the two databases label versions correctly. If they did not, only the version
detail would fall; the hash equality between CloakBrowser and the most common Chrome Windows
fingerprint would stand.

## Anomalies investigated

- **Obscura has no WebGL at all.** `canvas.getContext('webgl')` returns null in every round
  (`webgl: null`), so `webgl_real_gpu` fails for a structural reason, not a spoofing one.
  Obscura 0.2.5 is a V8-based renderer; its `--help` mentions render-enabled builds. Any anti-bot
  that scores WebGL will flag it. Not fixable in this package.
- **Obscura leaks CDP runtime use.** The probe that defines an `Error.stack` getter and passes the
  error to `console.debug` sees the getter touched in every round (`cdp_runtime_detected: true`),
  while CloakBrowser and plain Chromium do not. Upstream behaviour of Obscura's console
  serialisation; candidate for an issue at h4ckf0r0day/obscura.
- **CloakBrowser rotates a synthetic hardware profile per session.** The machine has AMD GPUs,
  16 threads and a 2926x1646 screen, yet CloakBrowser reported NVIDIA RTX 5080 / RTX 3080 /
  RTX 3090 / Intel UHD, 12–32 threads and 1920x1200–3440x1440 across the five rounds. Each
  profile is internally plausible, which is why every probe passes, but `webgl_real_gpu` cannot
  distinguish a spoofed GPU from a real one. Treat the 100% stealth score as "coherent", not "real".
- **Obscura `hardwareConcurrency` also varies** (6, 16, 8, 6, 6) with a fixed 1280x720 screen.
- **Timezone** is `America/Bahia` for every engine: the host clock, not a per-engine setting.
  Through a residential proxy this must be set with `OBSCURA_TIMEZONE` / `OBSCURA_GEOLOCATION`
  to match the exit region; that run is still pending (no Decodo credentials on this host).

## Paid-chain mechanics verified without Decodo credentials

- `ENGINE_ORDER=site_unblocker,web_data_api` with both unconfigured: clean refusal
  ("No scraping engine available").
- `SITE_UNBLOCKER_URL` pointing to an unreachable host, `ENGINE_ORDER=site_unblocker,cloakbrowser`:
  two `ConnectError` attempts (primary + `js_render: False` variant), then CloakBrowser answered.
- Budget: those two failed attempts were counted (`used_today` 2 → 4) although no request
  reached Decodo. Design question for the operator: charge on success/response only.

## Bugs fixed during this validation

- 8727155 — spawned `obscura serve` inherited `OBSCURA_CDP_TOKEN` and answered 401.
- faa39aa — cp1252 console broke `scrape --json`; stdout/stderr forced to UTF-8.
- b4bd978 — explicit `--engine` on an unconfigured paid level charged the budget before failing.
