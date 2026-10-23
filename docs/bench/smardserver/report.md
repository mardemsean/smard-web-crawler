# Engine comparison

Hosts: SMardSERVER-8700G (Windows AMD64, 16 CPUs)

## Summary

| Engine | Host | Version | Rounds (failed) | Functional | Stealth | Cold start ms p50 | Static load ms p50 | Concurrency ms p50 | RSS MB (last) |
|---|---|---|---|---|---|---|---|---|---|
| cloakbrowser | SMardSERVER-8700G | 155.0.8059.39 | 5 (0) | 100% | 100% | 770 | 45 | 293 | 464.8 |
| obscura+stealth | SMardSERVER-8700G | 145.0.0.0 | 5 (0) | 100% | 90% | 520 | 27 | 204 | 80.2 |
| obscura | SMardSERVER-8700G | 145.0.0.0 | 5 (0) | 100% | 90% | 524 | 27 | 204 | 78.2 |
| chromium | SMardSERVER-8700G | 156.0.8078.4 | 5 (0) | 100% | 70% | 68 | 30 | 178 | 258.8 |
| chromium+stealth.py | SMardSERVER-8700G | 156.0.8078.4 | 5 (0) | 100% | 75% | 67 | 28 | 166 | 260.7 |

## Functional pass rate

| Test | cloakbrowser | obscura+stealth | obscura | chromium | chromium+stealth.py |
|---|---|---|---|---|---|
| static_text | 100% | 100% | 100% | 100% | 100% |
| links | 100% | 100% | 100% | 100% | 100% |
| js_render | 100% | 100% | 100% | 100% | 100% |
| delayed_render | 100% | 100% | 100% | 100% | 100% |
| js_fetch | 100% | 100% | 100% | 100% | 100% |
| click | 100% | 100% | 100% | 100% | 100% |
| form_fill | 100% | 100% | 100% | 100% | 100% |
| cookie_persist | 100% | 100% | 100% | 100% | 100% |
| spa_navigation | 100% | 100% | 100% | 100% | 100% |
| screenshot | 100% | 100% | 100% | 100% | 100% |

## Stealth probe pass rate

| Probe | cloakbrowser | obscura+stealth | obscura | chromium | chromium+stealth.py |
|---|---|---|---|---|---|
| webdriver_false | 100% | 100% | 100% | 0% | 100% |
| webdriver_not_own_prop | 100% | 100% | 100% | 100% | 100% |
| ua_not_headless | 100% | 100% | 100% | 0% | 100% |
| plugins_present | 100% | 100% | 100% | 0% | 100% |
| plugins_is_pluginarray | 100% | 100% | 100% | 100% | 100% |
| languages_present | 100% | 100% | 100% | 100% | 100% |
| window_chrome | 100% | 100% | 100% | 0% | 0% |
| uad_present | 100% | 100% | 100% | 100% | 100% |
| uad_matches_ua | 100% | 100% | 100% | 100% | 100% |
| platform_matches_ua | 100% | 100% | 100% | 100% | 0% |
| getters_native | 100% | 100% | 100% | 100% | 0% |
| tostring_native | 100% | 100% | 100% | 100% | 100% |
| outer_window_nonzero | 100% | 100% | 100% | 100% | 100% |
| hw_concurrency_plausible | 100% | 100% | 100% | 100% | 100% |
| webgl_real_gpu | 100% | 0% | 0% | 0% | 0% |
| canvas_stable | 100% | 100% | 100% | 100% | 100% |
| cdp_runtime_hidden | 100% | 0% | 0% | 100% | 100% |
| notification_consistent | 100% | 100% | 100% | 0% | 0% |
| iframe_consistent | 100% | 100% | 100% | 100% | 100% |
| worker_consistent | 100% | 100% | 100% | 100% | 100% |

## Raw fingerprint (first successful round)

| Field | cloakbrowser | obscura+stealth | obscura | chromium | chromium+stealth.py |
|---|---|---|---|---|---|
| ua | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/15 | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/14 | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/14 | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessC | Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Sa |
| platform | Win32 | Win32 | Win32 | Win32 | Win32 |
| uad_brands | Google Chrome/155\|Chromium/155\|Not(A:Brand/24 | Not:A-Brand/99\|Google Chrome/145\|Chromium/145 | Google Chrome/143\|Chromium/143\|Not A(Brand/24 | Not:A-Brand/8\|Chromium/156\|HeadlessChrome/156 | Chromium/129\|Not_A_Brand/24\|Google Chrome/129 |
| uad_platform | Windows | Windows | Windows | Windows | Linux |
| webgl | Google Inc. (NVIDIA) \| ANGLE (NVIDIA, NVIDIA GeForce RTX 5080 (0x00002C02) Direct3D11 vs_ | None | None | Google Inc. (Google) \| ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero) (0x0000C | Google Inc. (Google) \| ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero) (0x0000C |
| plugins | 5 | 5 | 5 | 0 | 5 |
| languages | en-US,en | en-US,en | en-US,en | pt-BR | en-US,en |
| hw_concurrency | 32 | 6 | 12 | 16 | 5 |
| getters_native | True | True | True | True | webdriver,hardwareConcurrency,languages,plugins |
| worker_ua | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/15 | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/14 | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/14 | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessC | Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Sa |
| worker_platform | Win32 | Win32 | Win32 | Win32 | Win32 |
| timezone | America/Bahia | America/Bahia | America/Bahia | America/Bahia | America/Bahia |
| screen | 3440x1440x24 | 1280x720x24 | 1280x720x24 | 1280x720x24 | 1920x1080x24 |

## Online (first round)

- **cloakbrowser**: tls=`{"ja3_hash": "81c502ed84afccae0b1830c8a76cdf09", "ja4": "t13d1517h2_8daaf6152771_cb7bf5808d99", "http2_akamai": "52d84b11737d980aef856699f885ca86", "http_version": "h2", "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"}` sannysoft=`{'failed': 0, 'warn': 0, 'passed': 31}`
- **obscura+stealth**: tls=`{"ja3_hash": "21347b30460204a9f28012bbb2293f8d", "ja4": "t13d1516h2_8daaf6152771_d8a2da3f94cd", "http2_akamai": "52d84b11737d980aef856699f885ca86", "http_version": "h2", "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"}` sannysoft=`{'failed': 3, 'warn': 1, 'passed': 27}`
- **obscura**: tls=`{"ja3_hash": "b6ede60bd5fb819a6ad7257bce3387c2", "ja4": "t13d1011h1_61a7ad8aa9b6_3fcd1a44f3e3", "http2_akamai": null, "http_version": "HTTP/1.1", "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"}` sannysoft=`{'failed': 3, 'warn': 1, 'passed': 27}`
- **chromium**: tls=`{"ja3_hash": "bba0a0246f0612c0f59342599a3a262c", "ja4": "t13d1516h2_8daaf6152771_806a8c22fdea", "http2_akamai": "52d84b11737d980aef856699f885ca86", "http_version": "h2", "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/156.0.8078.4 Safari` sannysoft=`{'failed': 12, 'warn': 1, 'passed': 18}`
- **chromium+stealth.py**: tls=`{"ja3_hash": "07b92e02d187bfb4bfe9d1ef3feea2c8", "ja4": "t13d1516h2_8daaf6152771_806a8c22fdea", "http2_akamai": "52d84b11737d980aef856699f885ca86", "http_version": "h2", "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"}` sannysoft=`{'failed': 6, 'warn': 0, 'passed': 25}`
