"""Tests for bench/scoring.py rules and aggregation."""

from smard_crawler.bench.scoring import PROBE_RULES, aggregate, percentile, score_probes

CHROME_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"

REAL_CHROME = {
    "webdriver": False, "webdriver_own": False, "ua": CHROME_UA, "platform": "Win32",
    "languages": "en-US,en", "plugins": 5, "plugins_is_pluginarray": True, "window_chrome": True,
    "uad_brands": "Google Chrome/141|Not?A_Brand/8|Chromium/141", "uad_platform": "Windows",
    "getters_native": True, "tostring_native": True, "outer_zero": False, "hw_concurrency": 8,
    "webgl": "Google Inc. (NVIDIA) | ANGLE (NVIDIA GeForce RTX 3060)", "canvas_hash": 12345,
    "cdp_runtime_detected": False, "notification_permission": "default", "notification_query": "prompt",
    "iframe_ua": CHROME_UA, "iframe_webdriver": False, "worker_ua": CHROME_UA, "worker_platform": "Win32",
}


def test_real_chrome_passes_every_rule():
    scores = score_probes(REAL_CHROME)
    assert set(scores) == set(PROBE_RULES)
    assert all(scores.values()), [k for k, v in scores.items() if not v]


def test_headless_tells_fail():
    p = dict(REAL_CHROME, ua=CHROME_UA.replace("Chrome/", "HeadlessChrome/"), webdriver=True,
             webgl="Google Inc. (Google) | ANGLE (SwiftShader Device)", notification_permission="denied")
    s = score_probes(p)
    assert not s["ua_not_headless"]
    assert not s["webdriver_false"]
    assert not s["webgl_real_gpu"]
    assert not s["notification_consistent"]


def test_uad_version_mismatch_fails():
    s = score_probes(dict(REAL_CHROME, uad_brands="Google Chrome/129|Chromium/129"))
    assert not s["uad_matches_ua"]


def test_platform_mismatch_fails():
    assert not score_probes(dict(REAL_CHROME, platform="Linux x86_64"))["platform_matches_ua"]


def test_worker_mismatch_fails():
    assert not score_probes(dict(REAL_CHROME, worker_ua="HeadlessChrome"))["worker_consistent"]


def test_unstable_canvas_and_errors_fail():
    s = score_probes(dict(REAL_CHROME, canvas_hash="UNSTABLE", languages="ERR:boom"))
    assert not s["canvas_stable"]
    assert not s["languages_present"]


def test_empty_probe_result_fails_everything():
    assert not any(score_probes({"error": "TimeoutError"}).values())


def test_percentile():
    assert percentile([], 50) is None
    assert percentile([7.0], 95) == 7.0
    assert percentile([1.0, 2.0, 3.0, 4.0, 5.0], 50) == 3.0


def test_aggregate():
    rounds = [
        {"functional": {"a": {"ok": True, "ms": 10.0}}, "probe_scores": {"x": True, "y": False}, "timing": {"cold_start": 100.0}},
        {"functional": {"a": {"ok": False, "ms": None}}, "probe_scores": {"x": True, "y": True}, "timing": {"cold_start": 200.0}},
        {"fatal": "RuntimeError: boom"},
    ]
    agg = aggregate(rounds)
    assert agg["rounds"] == 3
    assert agg["rounds_failed"] == 1
    assert agg["functional"]["a"] == 0.5
    assert agg["probes"] == {"x": 1.0, "y": 0.5}
    assert agg["stealth_score"] == 0.75
    assert agg["timing"]["cold_start"]["n"] == 2
    assert agg["timing"]["functional.a"]["n"] == 1
