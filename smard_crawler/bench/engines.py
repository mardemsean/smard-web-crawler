"""Engine adapters. Each yields a Playwright Browser so one battery runs against all engines."""

from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator

from playwright.async_api import Browser, Playwright


@dataclass
class EngineHandle:
    name: str
    browser: Browser
    start_ms: float
    context_kwargs: dict[str, Any] = field(default_factory=dict)
    init_scripts: list[str] = field(default_factory=list)
    info: dict[str, Any] = field(default_factory=dict)


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def _wait_port(port: int, timeout: float, proc: subprocess.Popen | None = None) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc is not None and proc.poll() is not None:
            raise RuntimeError(f"engine process exited with code {proc.returncode}")
        try:
            _, w = await asyncio.open_connection("127.0.0.1", port)
            w.close()
            await w.wait_closed()
            return
        except OSError:
            await asyncio.sleep(0.1)
    raise TimeoutError(f"port {port} not ready after {timeout}s")


@asynccontextmanager
async def chromium(pw: Playwright, headless: bool = True, use_stealth_py: bool = False) -> AsyncIterator[EngineHandle]:
    t0 = time.perf_counter()
    browser = await pw.chromium.launch(headless=headless, executable_path=os.getenv("BENCH_CHROMIUM_PATH") or None)
    handle = EngineHandle(
        name="chromium+stealth.py" if use_stealth_py else "chromium",
        browser=browser,
        start_ms=(time.perf_counter() - t0) * 1000,
        info={"version": browser.version},
    )
    if use_stealth_py:
        from smard_crawler.common.stealth import SessionFingerprint, navigator_stealth_script

        fp = SessionFingerprint(seed=int(os.getenv("BENCH_STEALTH_SEED", "42")))
        handle.context_kwargs = {
            "user_agent": fp.profile.ua,
            "viewport": {"width": fp.profile.viewport_width, "height": fp.profile.viewport_height},
        }
        handle.init_scripts = [navigator_stealth_script(fp)]
        handle.info["profile"] = fp.profile.name
    try:
        yield handle
    finally:
        await browser.close()


@asynccontextmanager
async def obscura(pw: Playwright, binary: str | None = None, cdp_url: str | None = None, stealth: bool = True) -> AsyncIterator[EngineHandle]:
    """Spawn `obscura serve` (or attach to an existing CDP endpoint) and connect over CDP."""
    proc: subprocess.Popen | None = None
    log_file = None
    t0 = time.perf_counter()
    try:
        if cdp_url is None:
            binary = binary or os.getenv("OBSCURA_BIN") or "obscura"
            port = _free_port()
            args = [binary, "serve", "--port", str(port), "--allow-private-network"]
            if stealth:
                args.append("--stealth")
            log_path = Path(os.getenv("BENCH_LOG_DIR", "data/bench")) / f"obscura-{port}.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_file = log_path.open("wb")
            proc = subprocess.Popen(args, stdout=log_file, stderr=subprocess.STDOUT)
            await _wait_port(port, 30, proc)
            cdp_url = f"ws://127.0.0.1:{port}"
        browser = await pw.chromium.connect_over_cdp(cdp_url, timeout=30_000)
        handle = EngineHandle(
            name="obscura+stealth" if stealth else "obscura",
            browser=browser,
            start_ms=(time.perf_counter() - t0) * 1000,
            info={"version": browser.version, "cdp_url": cdp_url},
        )
        try:
            yield handle
        finally:
            try:
                await browser.close()
            except Exception:
                pass
    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        if log_file is not None:
            log_file.close()


@asynccontextmanager
async def cloakbrowser(pw: Playwright, headless: bool = True) -> AsyncIterator[EngineHandle]:
    """CloakBrowser via its own launcher; requires `pip install cloakbrowser` and an activated license."""
    from cloakbrowser import launch_async

    t0 = time.perf_counter()
    browser = await launch_async(headless=headless, proxy=os.getenv("BENCH_PROXY") or None)
    handle = EngineHandle(name="cloakbrowser", browser=browser, start_ms=(time.perf_counter() - t0) * 1000, info={"version": browser.version})
    try:
        yield handle
    finally:
        await browser.close()


@asynccontextmanager
async def cdp(pw: Playwright, url: str) -> AsyncIterator[EngineHandle]:
    t0 = time.perf_counter()
    browser = await pw.chromium.connect_over_cdp(url, timeout=30_000)
    handle = EngineHandle(name=f"cdp:{url}", browser=browser, start_ms=(time.perf_counter() - t0) * 1000, info={"version": browser.version})
    try:
        yield handle
    finally:
        await browser.close()


def resolve(spec: str, pw: Playwright, headless: bool = True):
    """Map an engine spec string to an adapter context manager."""
    if spec == "chromium":
        return chromium(pw, headless)
    if spec == "chromium-stealthpy":
        return chromium(pw, headless, use_stealth_py=True)
    if spec == "obscura":
        return obscura(pw, stealth=False)
    if spec == "obscura-stealth":
        return obscura(pw, stealth=True)
    if spec == "cloakbrowser":
        return cloakbrowser(pw, headless)
    if spec.startswith("cdp:"):
        return cdp(pw, spec[4:])
    raise ValueError(f"unknown engine: {spec}")


ENGINE_SPECS = ["chromium", "chromium-stealthpy", "obscura", "obscura-stealth", "cloakbrowser", "cdp:<url>"]
