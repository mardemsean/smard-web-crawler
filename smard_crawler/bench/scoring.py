"""Scoring rules: does a probe result look like a real desktop Chrome?"""

from __future__ import annotations

import re
import statistics
from typing import Any, Callable

Rule = Callable[[dict[str, Any]], bool]


def _chrome_major(ua: str | None) -> str | None:
    m = re.search(r"Chrome/(\d+)", ua or "")
    return m.group(1) if m else None


def _uad_consistent(p: dict[str, Any]) -> bool:
    major = _chrome_major(p.get("ua"))
    brands = p.get("uad_brands") or ""
    versions = dict(b.split("/", 1) for b in brands.split("|") if "/" in b)
    brand_major = versions.get("Google Chrome") or versions.get("Chromium")
    return major is not None and brand_major == major


def _platform_consistent(p: dict[str, Any]) -> bool:
    ua, plat = p.get("ua") or "", p.get("platform") or ""
    uad = p.get("uad_platform")
    if "Windows" in ua:
        expected, uad_expected = plat.startswith("Win"), "Windows"
    elif "Macintosh" in ua:
        expected, uad_expected = plat.startswith("Mac"), "macOS"
    elif "Linux" in ua:
        expected, uad_expected = plat.startswith("Linux"), "Linux"
    else:
        return False
    return expected and (uad is None or uad == uad_expected)


def _webgl_real(p: dict[str, Any]) -> bool:
    v = p.get("webgl")
    return bool(v) and v != "no-debug-ext" and "SwiftShader" not in v and not str(v).startswith("ERR")


def _notif_consistent(p: dict[str, Any]) -> bool:
    query = p.get("notification_query")
    if query not in ("granted", "denied", "prompt"):
        return False
    return not (p.get("notification_permission") == "denied" and query == "prompt")


def _same_as_main(p: dict[str, Any], key: str, main_key: str) -> bool:
    v = p.get(key)
    return isinstance(v, str) and not v.startswith(("ERR", "TIMEOUT")) and v == p.get(main_key)


PROBE_RULES: dict[str, Rule] = {
    "webdriver_false": lambda p: p.get("webdriver") is False,
    "webdriver_not_own_prop": lambda p: p.get("webdriver_own") is False,
    "ua_not_headless": lambda p: "Headless" not in (p.get("ua") or "Headless"),
    "plugins_present": lambda p: isinstance(p.get("plugins"), int) and p["plugins"] >= 1,
    "plugins_is_pluginarray": lambda p: p.get("plugins_is_pluginarray") is True,
    "languages_present": lambda p: bool(p.get("languages")) and not str(p["languages"]).startswith("ERR"),
    "window_chrome": lambda p: p.get("window_chrome") is True,
    "uad_present": lambda p: "Chrom" in (p.get("uad_brands") or ""),
    "uad_matches_ua": _uad_consistent,
    "platform_matches_ua": _platform_consistent,
    "getters_native": lambda p: p.get("getters_native") is True,
    "tostring_native": lambda p: p.get("tostring_native") is True,
    "outer_window_nonzero": lambda p: p.get("outer_zero") is False,
    "hw_concurrency_plausible": lambda p: isinstance(p.get("hw_concurrency"), int) and 2 <= p["hw_concurrency"] <= 64,
    "webgl_real_gpu": _webgl_real,
    "canvas_stable": lambda p: p.get("canvas_hash") not in (None, "UNSTABLE") and not str(p.get("canvas_hash")).startswith("ERR"),
    "cdp_runtime_hidden": lambda p: p.get("cdp_runtime_detected") is False,
    "notification_consistent": _notif_consistent,
    "iframe_consistent": lambda p: _same_as_main(p, "iframe_ua", "ua") and p.get("iframe_webdriver") == p.get("webdriver"),
    "worker_consistent": lambda p: _same_as_main(p, "worker_ua", "ua") and p.get("worker_platform") == p.get("platform"),
}


def score_probes(probes: dict[str, Any]) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for name, rule in PROBE_RULES.items():
        try:
            out[name] = bool(rule(probes))
        except Exception:
            out[name] = False
    return out


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    qs = statistics.quantiles(sorted(values), n=100, method="inclusive")
    return qs[int(pct) - 1]


def pass_rate(flags: list[bool]) -> float:
    return sum(flags) / len(flags) if flags else 0.0


def aggregate(rounds: list[dict[str, Any]]) -> dict[str, Any]:
    """Collapse per-round results of one engine into pass rates and latency percentiles."""
    functional: dict[str, list[bool]] = {}
    probes: dict[str, list[bool]] = {}
    timings: dict[str, list[float]] = {}
    for rnd in rounds:
        for name, res in rnd.get("functional", {}).items():
            functional.setdefault(name, []).append(bool(res.get("ok")))
            if res.get("ms") is not None:
                timings.setdefault(f"functional.{name}", []).append(res["ms"])
        for name, ok in rnd.get("probe_scores", {}).items():
            probes.setdefault(name, []).append(ok)
        for name, ms in rnd.get("timing", {}).items():
            if isinstance(ms, (int, float)):
                timings.setdefault(name, []).append(float(ms))

    func_rates = {k: pass_rate(v) for k, v in functional.items()}
    probe_rates = {k: pass_rate(v) for k, v in probes.items()}
    return {
        "rounds": len(rounds),
        "rounds_failed": sum(1 for r in rounds if r.get("fatal")),
        "functional": func_rates,
        "probes": probe_rates,
        "functional_score": pass_rate([x for v in functional.values() for x in v]),
        "stealth_score": pass_rate([x for v in probes.values() for x in v]),
        "timing": {k: {"p50": percentile(v, 50), "p95": percentile(v, 95), "n": len(v)} for k, v in timings.items()},
    }
