# 0001 — Obscura as a crawler engine (decision D1)

**Status:** adopted 2026-10-22. The operator delegated the call and made it
conditional on complete tests against Obscura. This record holds those results.
**Question:** adopt Obscura as a self-hosted engine in the fallback chain, or only
extract its stealth patterns into `stealth.py`?

## Evidence

Battery: `smard-crawler bench`. It runs 10 functional tests on local fixtures,
20 stealth probes, timing and RSS, plus online TLS, header and sannysoft checks.
All engines ran on the same host (Linux x86_64, 4 CPUs), 5 rounds each.

| Engine | Functional | Stealth | Cold start p50 | Static load p50 | 8-page concurrency p50 | RSS |
|---|---|---|---|---|---|---|
| Chromium 141 headless | 100% | 70% | 64 ms | 54 ms | 354 ms | 413 MB |
| Chromium 141 + `stealth.py` | 100% | 80% | 69 ms | 52 ms | 335 ms | 418 MB |
| Obscura (no stealth) | 100% | 90% | 112 ms | 52 ms | 400 ms | 106 MB |
| Obscura `--stealth` (built from fork f4085fa) | 100% | 90% | 113 ms | 60 ms | 490 ms | 118 MB |
| Obscura `--stealth` (release v0.2.5) | 100% | 90% | 116 ms | 69 ms | 482 ms | 107 MB |

Online, 1 round:

| Engine | JA4 | bot.sannysoft.com failed |
|---|---|---|
| Chromium headless | `t13d911_f91f431d341e_f50d94e863eb` | 12 |
| Obscura (no stealth) | `t13d1011h1_61a7ad8aa9b6_3fcd1a44f3e3` (distinct, detectable) | 3 |
| Obscura `--stealth` | `t13d911_f91f431d341e_f50d94e863eb` (same as Chromium) | 3 |

Caveat: this host egresses through a TLS-intercepting proxy. All engines report
HTTP/1.1, which is a sign the proxy shaped the connection. Repeat `--online` on a
direct-egress host such as SMardSERVER before relying on the TLS numbers.

Obscura's remaining tells: no WebGL (`webgl_real_gpu` at 0%), and the
`console.debug` Error-stack getter fires (`cdp_runtime_hidden` at 0%).
`stealth.py` on Chromium fixes `webdriver`, the headless UA and plugins. Its getters
are not native functions, so `getters_native` drops to 0%.

## Decision

1. Adopt Obscura as engine #1 (`ENGINE_ORDER` default). It matches functionality,
   has the best stealth score and uses a quarter of Chromium's memory.
2. Use only stealth builds: the `-stealth` release, or our `docker/obscura` image.
   The upstream Docker Hub image is built without the `stealth` feature.
3. Keep Crawl4AI and CloakBrowser in the chain. Sites that fingerprint WebGL or
   detect CDP fall through to them.
4. Keep `stealth.py` as a library. It is not wired into Crawl4AI, which has its
   own `enable_stealth`, nor into Obscura or CloakBrowser, which patch below
   JavaScript.

## Follow-ups

- Run the battery on SMardSERVER with `cloakbrowser` and `--online`, then merge
  the results with `smard-crawler bench --merge`.
- Set `OBSCURA_TIMEZONE` and `OBSCURA_GEOLOCATION` to match the proxy's exit
  region. The default reports Europe/Berlin.
