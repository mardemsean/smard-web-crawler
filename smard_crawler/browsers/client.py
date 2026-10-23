"""Browser-driven engines: Obscura (CDP server) and CloakBrowser (local stealth Chromium)."""

from __future__ import annotations

import asyncio
import os
import logging
import subprocess
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlsplit, urlunsplit

import httpx

from ..common.config import config
from ..common.markdown import html_to_markdown

logger = logging.getLogger(__name__)


class BrowserEngineClient:
    """Shared Playwright page workflow; subclasses provide the Browser."""

    name = "browser"

    def __init__(self, max_sessions: int = 4, timeout_ms: Optional[int] = None):
        self.timeout_ms = timeout_ms or config.browser.timeout
        self._sem = asyncio.Semaphore(max(1, max_sessions))
        self._browser: Any = None
        self._pw: Any = None
        self._lock = asyncio.Lock()

    async def _open_browser(self) -> Any:
        raise NotImplementedError

    async def _get_browser(self) -> Any:
        async with self._lock:
            if self._browser is None or not self._browser.is_connected():
                self._browser = await self._open_browser()
            return self._browser

    async def _new_context(self, browser: Any) -> tuple[Any, bool]:
        try:
            return await browser.new_context(), True
        except Exception:
            if browser.contexts:
                return browser.contexts[0], False
            raise

    async def scrape(self, url: str, *, wait_for: int = 0, wait_selector: Optional[str] = None) -> dict:
        async with self._sem:
            browser = await self._get_browser()
            ctx, owned = await self._new_context(browser)
            page = await ctx.new_page()
            try:
                t0 = time.monotonic()
                resp = await page.goto(url, wait_until="load", timeout=self.timeout_ms)
                if wait_selector:
                    await page.wait_for_selector(wait_selector, timeout=self.timeout_ms)
                if wait_for:
                    await page.wait_for_timeout(wait_for)
                html = await page.content()
                status = resp.status if resp else None
                extracted = html_to_markdown(html, page.url)
                return {
                    "url": url,
                    "final_url": page.url,
                    "status": status,
                    "title": extracted["title"],
                    "markdown": extracted["markdown"],
                    "links": extracted["links"],
                    "render_ms": round((time.monotonic() - t0) * 1000),
                    "success": status is None or status < 400,
                }
            finally:
                await page.close()
                if owned:
                    await ctx.close()

    async def close(self) -> None:
        if self._browser is not None:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._pw is not None:
            await self._pw.stop()
            self._pw = None


def _http_base(cdp_url: str) -> str:
    parts = urlsplit(cdp_url)
    scheme = {"ws": "http", "wss": "https"}.get(parts.scheme, parts.scheme)
    return urlunsplit((scheme, parts.netloc, "", "", ""))


def obscura_child_env(token: str) -> dict[str, str]:
    """Environment for a spawned `obscura serve`, coherent with the token the client will send.

    `obscura serve` enforces Bearer auth whenever OBSCURA_CDP_TOKEN is present in its environment.
    load_env_files() exports the installed .env into os.environ, so an inherited environment can
    make the child require a token the client never sends (401 on /json/version).
    """
    env = dict(os.environ)
    if token:
        env["OBSCURA_CDP_TOKEN"] = token
    else:
        env.pop("OBSCURA_CDP_TOKEN", None)
    return env


class ObscuraClient(BrowserEngineClient):
    """Connects to an `obscura serve --stealth` CDP endpoint.

    With OBSCURA_BIN set and a loopback OBSCURA_CDP_URL, the binary is started on demand
    and stopped on close(), so no separate daemon is needed.
    """

    name = "obscura"

    def __init__(self, cdp_url: Optional[str] = None, token: Optional[str] = None, max_sessions: Optional[int] = None,
                 binary: Optional[str] = None):
        super().__init__(max_sessions or config.obscura.max_sessions)
        self.cdp_url = cdp_url or config.obscura.cdp_url
        self.token = token if token is not None else config.obscura.token
        self.binary = binary if binary is not None else config.obscura.binary
        self.enabled = config.obscura.enabled
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._spawn_lock = asyncio.Lock()

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def _can_spawn(self) -> bool:
        host = urlsplit(self.cdp_url).hostname or ""
        return bool(self.binary) and Path(self.binary).is_file() and host in ("127.0.0.1", "localhost", "::1")

    async def _endpoint_up(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{_http_base(self.cdp_url)}/json/version", headers=self._headers())
                return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def _ensure_running(self) -> bool:
        if await self._endpoint_up():
            return True
        if not self._can_spawn():
            return False
        async with self._spawn_lock:
            if self._proc is None or self._proc.returncode is not None:
                port = urlsplit(self.cdp_url).port or 9222
                args = [self.binary, "serve", "--host", "127.0.0.1", "--port", str(port), "--stealth"]
                if config.proxy.enabled:
                    args += ["--proxy", config.proxy.url]
                logger.info(f"[obscura] starting local binary on port {port}")
                self._proc = await asyncio.create_subprocess_exec(
                    *args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=obscura_child_env(self.token),
                )
            for _ in range(150):
                if self._proc.returncode is not None:
                    logger.warning(f"[obscura] local binary exited with code {self._proc.returncode}")
                    return False
                if await self._endpoint_up():
                    return True
                await asyncio.sleep(0.1)
        return False

    async def _open_browser(self) -> Any:
        from playwright.async_api import async_playwright

        if not await self._ensure_running():
            raise RuntimeError(f"Obscura endpoint {self.cdp_url} is not reachable")

        if self._pw is None:
            self._pw = await async_playwright().start()
        kwargs: dict[str, Any] = {"timeout": self.timeout_ms}
        if self.token:
            kwargs["headers"] = self._headers()
        return await self._pw.chromium.connect_over_cdp(self.cdp_url, **kwargs)

    async def health(self) -> bool:
        return self.enabled and await self._ensure_running()

    async def close(self) -> None:
        await super().close()
        if self._proc is not None and self._proc.returncode is None:
            self._proc.terminate()
            try:
                await asyncio.wait_for(self._proc.wait(), 5)
            except asyncio.TimeoutError:
                self._proc.kill()
        self._proc = None


class CloakBrowserClient(BrowserEngineClient):
    """Launches CloakBrowser locally; requires `pip install cloakbrowser` and an activated license."""

    name = "cloakbrowser"

    def __init__(self, max_sessions: Optional[int] = None):
        super().__init__(max_sessions or config.cloakbrowser.max_sessions)
        self.enabled = config.cloakbrowser.enabled

    async def _open_browser(self) -> Any:
        from cloakbrowser import launch_async

        return await launch_async(
            headless=config.browser.headless,
            proxy=config.proxy.url or None,
            humanize=config.cloakbrowser.humanize,
        )

    async def health(self) -> bool:
        if not self.enabled:
            return False
        try:
            import cloakbrowser  # noqa: F401
        except ImportError:
            logger.warning("[cloakbrowser] enabled but package not installed (pip install 'smard-web-crawler[cloak]')")
            return False
        return True
