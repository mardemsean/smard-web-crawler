---
name: engine-bench
description: Run the SMard engine comparison battery (functional, stealth-fingerprint and performance tests) against Obscura, CloakBrowser, Chromium and other CDP engines, and merge results from several machines. Use when the user wants to compare scraping engines, re-test stealth after an upgrade, or decide the fallback order.
---

# Engine comparison battery

`smard-crawler bench` runs the same tests against each engine, for N rounds each:

- **Functional (10 tests)**: static text, links, JS render, delayed render, JS fetch, click, form fill, cookie persistence, SPA navigation, screenshot. Runs against local fixture pages, so it needs no network.
- **Stealth (20 probes)**: webdriver, headless UA, plugins/PluginArray, `window.chrome`, userAgentData versus UA, platform consistency, native getters, WebGL GPU, canvas stability, CDP Runtime detection, notification permissions, iframe and Worker consistency.
- **Performance**: cold start, page load, 8-page concurrency, engine RSS.
- **Online (`--online`)**: TLS JA3/JA4 via tls.peet.ws, request headers via httpbin, bot.sannysoft.com failures.

## Commands

```bash
# Engines: chromium, chromium-stealthpy, obscura, obscura-stealth, cloakbrowser, cdp:<ws-url>
smard-crawler bench --engines obscura-stealth,cloakbrowser,chromium --rounds 5 --online

# Obscura is started from OBSCURA_BIN (the installer sets it in ~/.smard-crawler/.env)
# CloakBrowser needs the [cloak] extra and an activated license (cloakbrowser login)
# chromium needs: python -m playwright install chromium

# Merge runs from several hosts (e.g. cloud VM + SMardSERVER) into one report
smard-crawler bench --merge host-a/results.json host-b/results.json --out data/bench/merged
```

Each run writes `data/bench/<timestamp>/results.json` and `report.md`.

## Reading the report

- A stealth probe at 0% is a deterministic tell for that engine. Fix it, or route sensitive targets elsewhere.
- Compare `ja4` across engines: an engine whose JA4 differs from real Chrome's is detectable at the TLS layer, whatever its JavaScript fingerprint looks like.
- Use the summary table (functional %, stealth %, RSS, latency) to set `ENGINE_ORDER`.
- Measurements taken behind a TLS-intercepting proxy reflect the proxy's TLS, not the engine's. Repeat `--online` on a direct-egress host before drawing TLS conclusions.
