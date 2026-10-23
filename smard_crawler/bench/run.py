"""Engine comparison battery: same functional, stealth and performance tests against every engine.

Usage:
    smard-crawler bench --engines chromium,chromium-stealthpy,obscura-stealth --rounds 5
    smard-crawler bench --engines cloakbrowser --rounds 5 --online      # on SMardSERVER
    smard-crawler bench --merge data/bench/a/results.json data/bench/b/results.json
"""

from __future__ import annotations

import argparse
import asyncio
import functools
import http.server
import json
import os
import platform
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable

from playwright.async_api import BrowserContext, Page, async_playwright

from smard_crawler.bench import engines
from smard_crawler.bench.scoring import PROBE_RULES, aggregate, score_probes

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures"
PROBES_JS = (ROOT / "probes.js").read_text()

ONLINE_TARGETS = {
    "headers": "https://httpbin.org/headers",
    "tls": "https://tls.peet.ws/api/all",
    "sannysoft": "https://bot.sannysoft.com/",
}


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args: Any) -> None:
        pass


def start_fixture_server() -> tuple[http.server.ThreadingHTTPServer, str]:
    handler = functools.partial(_QuietHandler, directory=str(FIXTURES))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def engine_rss_mb() -> float | None:
    """RSS of all descendant processes except the Playwright node driver."""
    try:
        import psutil
    except ImportError:
        return None
    total = 0
    for child in psutil.Process().children(recursive=True):
        try:
            if child.name().lower().startswith("node"):
                continue
            total += child.memory_info().rss
        except psutil.Error:
            continue
    return round(total / 1024 / 1024, 1)


async def _new_context(handle: engines.EngineHandle) -> tuple[BrowserContext, bool]:
    try:
        ctx = await handle.browser.new_context(**handle.context_kwargs)
        isolated = True
    except Exception:
        if not handle.browser.contexts:
            raise
        ctx = handle.browser.contexts[0]
        isolated = False
    for script in handle.init_scripts:
        await ctx.add_init_script(script)
    return ctx, isolated


# --- functional tests: each returns (ok, detail) ---

async def f_static(page: Page, base: str) -> tuple[bool, Any]:
    await page.goto(f"{base}/static.html", wait_until="load")
    text = await page.inner_text("body")
    return "SMARD-STATIC-MARKER" in text and "Row 3 Col 2" in text, len(text)


async def f_links(page: Page, base: str) -> tuple[bool, Any]:
    await page.goto(f"{base}/static.html", wait_until="load")
    n = await page.eval_on_selector_all("a", "els => els.length")
    return n == 4, n


async def f_js_render(page: Page, base: str) -> tuple[bool, Any]:
    await page.goto(f"{base}/dynamic.html", wait_until="load")
    el = await page.wait_for_selector("#rendered", timeout=3000)
    return (await el.inner_text()) == "SMARD-JS-MARKER", None


async def f_delayed(page: Page, base: str) -> tuple[bool, Any]:
    await page.goto(f"{base}/dynamic.html", wait_until="load")
    el = await page.wait_for_selector("#delayed", timeout=6000)
    return (await el.inner_text()) == "SMARD-DELAYED-MARKER", None


async def f_fetch(page: Page, base: str) -> tuple[bool, Any]:
    await page.goto(f"{base}/dynamic.html", wait_until="load")
    el = await page.wait_for_selector("#fetch-ok", timeout=5000)
    return (await el.inner_text()) == "SMARD-FETCH-MARKER", None


async def f_click(page: Page, base: str) -> tuple[bool, Any]:
    await page.goto(f"{base}/interaction.html", wait_until="load")
    await page.click("#reveal")
    await page.wait_for_selector("#revealed", state="visible", timeout=3000)
    return True, None


async def f_form(page: Page, base: str) -> tuple[bool, Any]:
    await page.goto(f"{base}/interaction.html", wait_until="load")
    await page.fill("#name", "smard")
    await page.click("#submit")
    await page.wait_for_function("document.getElementById('echo').textContent === 'hello smard'", timeout=3000)
    return True, None


async def f_cookie(page: Page, base: str) -> tuple[bool, Any]:
    await page.goto(f"{base}/interaction.html", wait_until="load")
    await page.reload(wait_until="load")
    state = await page.inner_text("#state")
    return state == "returning", state


async def f_spa(page: Page, base: str) -> tuple[bool, Any]:
    await page.goto(f"{base}/interaction.html", wait_until="load")
    await page.click("#go")
    await page.wait_for_function("location.pathname === '/spa/page2'", timeout=3000)
    return (await page.inner_text("#view")) == "SMARD-SPA-MARKER", None


async def f_screenshot(page: Page, base: str) -> tuple[bool, Any]:
    await page.goto(f"{base}/static.html", wait_until="load")
    png = await page.screenshot()
    return len(png) > 1000, len(png)


FUNCTIONAL: dict[str, Callable[[Page, str], Awaitable[tuple[bool, Any]]]] = {
    "static_text": f_static,
    "links": f_links,
    "js_render": f_js_render,
    "delayed_render": f_delayed,
    "js_fetch": f_fetch,
    "click": f_click,
    "form_fill": f_form,
    "cookie_persist": f_cookie,
    "spa_navigation": f_spa,
    "screenshot": f_screenshot,
}


async def _timed(coro: Awaitable[tuple[bool, Any]], timeout: float) -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        ok, detail = await asyncio.wait_for(coro, timeout)
        return {"ok": ok, "detail": detail, "ms": round((time.perf_counter() - t0) * 1000, 1)}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}", "ms": None}


async def run_concurrency(ctx: BrowserContext, base: str, n: int) -> dict[str, Any]:
    async def one() -> bool:
        page = await ctx.new_page()
        try:
            await page.goto(f"{base}/static.html", wait_until="load", timeout=15_000)
            return "SMARD-STATIC-MARKER" in await page.inner_text("body")
        finally:
            await page.close()

    t0 = time.perf_counter()
    results = await asyncio.gather(*(one() for _ in range(n)), return_exceptions=True)
    ms = (time.perf_counter() - t0) * 1000
    ok = sum(1 for r in results if r is True)
    return {"pages": n, "ok": ok, "ms": round(ms, 1), "pages_per_s": round(ok / (ms / 1000), 2) if ms else None}


async def run_online(page: Page) -> dict[str, Any]:
    out: dict[str, Any] = {}

    async def body_json(url: str) -> Any:
        await page.goto(url, wait_until="load", timeout=30_000)
        return json.loads(await page.inner_text("body"))

    try:
        out["headers"] = (await body_json(ONLINE_TARGETS["headers"])).get("headers")
    except Exception as e:
        out["headers"] = f"ERR: {e}"[:200]
    try:
        tls = await body_json(ONLINE_TARGETS["tls"])
        out["tls"] = {
            "ja3_hash": tls.get("tls", {}).get("ja3_hash"),
            "ja4": tls.get("tls", {}).get("ja4"),
            "http2_akamai": tls.get("http2", {}).get("akamai_fingerprint_hash"),
            "http_version": tls.get("http_version"),
            "user_agent": tls.get("user_agent"),
        }
    except Exception as e:
        out["tls"] = f"ERR: {e}"[:200]
    try:
        await page.goto(ONLINE_TARGETS["sannysoft"], wait_until="load", timeout=30_000)
        await page.wait_for_timeout(3000)
        out["sannysoft"] = {
            "failed": await page.locator("td.failed").count(),
            "warn": await page.locator("td.warn").count(),
            "passed": await page.locator("td.passed").count(),
        }
    except Exception as e:
        out["sannysoft"] = f"ERR: {e}"[:200]
    return out


async def run_round(handle: engines.EngineHandle, base: str, online: bool, concurrency: int) -> dict[str, Any]:
    rnd: dict[str, Any] = {"timing": {"cold_start": round(handle.start_ms, 1)}, "functional": {}}
    ctx, isolated = await _new_context(handle)
    rnd["isolated_context"] = isolated
    try:
        page = await ctx.new_page()
        for name, fn in FUNCTIONAL.items():
            rnd["functional"][name] = await _timed(fn(page, base), 20)

        t0 = time.perf_counter()
        try:
            await page.goto(f"{base}/probe.html", wait_until="load")
            rnd["probes"] = await asyncio.wait_for(page.evaluate(PROBES_JS), 20)
            rnd["timing"]["probe_eval"] = round((time.perf_counter() - t0) * 1000, 1)
        except Exception as e:
            rnd["probes"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
        rnd["probe_scores"] = score_probes(rnd["probes"])

        rnd["concurrency"] = await run_concurrency(ctx, base, concurrency)
        rnd["timing"]["concurrency_total"] = rnd["concurrency"]["ms"]
        rnd["rss_mb"] = engine_rss_mb()

        if online:
            rnd["online"] = await run_online(page)
        await page.close()
    finally:
        if isolated:
            await ctx.close()
    return rnd


async def run_engine(spec: str, rounds: int, base: str, online: bool, concurrency: int, headless: bool) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    info: dict[str, Any] = {}
    name = spec
    async with async_playwright() as pw:
        for i in range(rounds):
            try:
                async with engines.resolve(spec, pw, headless) as handle:
                    name, info = handle.name, handle.info
                    rnd = await run_round(handle, base, online, concurrency)
            except Exception as e:
                rnd = {"fatal": f"{type(e).__name__}: {str(e)[:300]}"}
            rnd["round"] = i + 1
            results.append(rnd)
            print(f"  [{spec}] round {i + 1}/{rounds}: " + (rnd.get("fatal") or
                  f"functional {sum(r['ok'] for r in rnd['functional'].values())}/{len(FUNCTIONAL)}, "
                  f"stealth {sum(rnd['probe_scores'].values())}/{len(PROBE_RULES)}"), flush=True)
    return {"engine": name, "spec": spec, "info": info, "summary": aggregate(results), "rounds": results}


def host_info() -> dict[str, Any]:
    return {"node": platform.node(), "system": platform.system(), "release": platform.release(),
            "machine": platform.machine(), "python": platform.python_version(), "cpus": os.cpu_count()}


def _fmt_pct(x: float | None) -> str:
    return "—" if x is None else f"{x * 100:.0f}%"


def _fmt_ms(t: dict[str, Any], key: str) -> str:
    v = t.get(key, {}).get("p50")
    return "—" if v is None else f"{v:.0f}"


def render_report(runs: list[dict[str, Any]]) -> str:
    lines = ["# Engine comparison", ""]
    hosts = {r["host"]["node"]: r["host"] for r in runs}
    lines.append("Hosts: " + "; ".join(f"{n} ({h['system']} {h['machine']}, {h['cpus']} CPUs)" for n, h in hosts.items()))
    lines += ["", "## Summary", "",
              "| Engine | Host | Version | Rounds (failed) | Functional | Stealth | Cold start ms p50 | Static load ms p50 | Concurrency ms p50 | RSS MB (last) |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for r in runs:
        s, t = r["summary"], r["summary"]["timing"]
        rss = next((x.get("rss_mb") for x in reversed(r["rounds"]) if x.get("rss_mb") is not None), None)
        lines.append(f"| {r['engine']} | {r['host']['node']} | {r['info'].get('version', '—')} | {s['rounds']} ({s['rounds_failed']}) "
                     f"| {_fmt_pct(s['functional_score'])} | {_fmt_pct(s['stealth_score'])} | {_fmt_ms(t, 'cold_start')} "
                     f"| {_fmt_ms(t, 'functional.static_text')} | {_fmt_ms(t, 'concurrency_total')} | {rss if rss is not None else '—'} |")

    names = [r["engine"] for r in runs]
    lines += ["", "## Functional pass rate", "", "| Test | " + " | ".join(names) + " |", "|---" * (len(names) + 1) + "|"]
    for test in FUNCTIONAL:
        lines.append(f"| {test} | " + " | ".join(_fmt_pct(r["summary"]["functional"].get(test)) for r in runs) + " |")

    lines += ["", "## Stealth probe pass rate", "", "| Probe | " + " | ".join(names) + " |", "|---" * (len(names) + 1) + "|"]
    for probe in PROBE_RULES:
        lines.append(f"| {probe} | " + " | ".join(_fmt_pct(r["summary"]["probes"].get(probe)) for r in runs) + " |")

    lines += ["", "## Raw fingerprint (first successful round)", ""]
    keys = ["ua", "platform", "uad_brands", "uad_platform", "webgl", "plugins", "languages", "hw_concurrency",
            "getters_native", "worker_ua", "worker_platform", "timezone", "screen"]
    lines += ["| Field | " + " | ".join(names) + " |", "|---" * (len(names) + 1) + "|"]
    firsts = [next((x.get("probes", {}) for x in r["rounds"] if "probes" in x), {}) for r in runs]
    for k in keys:
        cells = [str(f.get(k, "—")).replace("|", "\\|")[:90] for f in firsts]
        lines.append(f"| {k} | " + " | ".join(cells) + " |")

    errors = [(r["engine"], x["round"], x["fatal"]) for r in runs for x in r["rounds"] if x.get("fatal")]
    func_errors = sorted({(r["engine"], n, v["error"]) for r in runs for x in r["rounds"]
                          for n, v in x.get("functional", {}).items() if v.get("error")})
    if errors or func_errors:
        lines += ["", "## Errors", ""]
        lines += [f"- **{e}** round {n}: `{m}`" for e, n, m in errors]
        lines += [f"- **{e}** `{n}`: `{m}`" for e, n, m in func_errors]

    online = [(r["engine"], x["online"]) for r in runs for x in r["rounds"][:1] if x.get("online")]
    if online:
        lines += ["", "## Online (first round)", ""]
        for e, o in online:
            lines.append(f"- **{e}**: tls=`{json.dumps(o.get('tls'))[:300]}` sannysoft=`{o.get('sannysoft')}`")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="smard-crawler bench", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engines", default="chromium,chromium-stealthpy", help=f"comma list from: {', '.join(engines.ENGINE_SPECS)}")
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--online", action="store_true", help="also hit httpbin, tls.peet.ws and bot.sannysoft.com")
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--merge", nargs="+", help="merge results.json files from several hosts into one report")
    args = ap.parse_args(argv)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out or f"data/bench/{stamp}")
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.merge:
        runs = [run for path in args.merge for run in json.loads(Path(path).read_text())["runs"]]
    else:
        server, base = start_fixture_server()
        runs = []
        try:
            for spec in [s.strip() for s in args.engines.split(",") if s.strip()]:
                print(f"engine {spec}:", flush=True)
                run = asyncio.run(run_engine(spec, args.rounds, base, args.online, args.concurrency, not args.headed))
                run["host"] = host_info()
                runs.append(run)
        finally:
            server.shutdown()
        (out_dir / "results.json").write_text(json.dumps({"generated_at": stamp, "runs": runs}, indent=2, default=str))

    report = render_report(runs)
    (out_dir / "report.md").write_text(report)
    print(f"\nreport: {out_dir / 'report.md'}")


if __name__ == "__main__":
    main()
