"""Tests for the Obscura/CloakBrowser engines, robots.txt guard and paid-engine budget."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from smard_crawler.browsers.client import BrowserEngineClient, CloakBrowserClient, ObscuraClient, _http_base
from smard_crawler.common.budget import BudgetExceeded, DailyBudget, PaidGuard, RateLimiter
from smard_crawler.common.markdown import html_to_markdown
from smard_crawler.common.robots import RobotsChecker, RobotsDisallowed
from smard_crawler.common.scraper import UnifiedScraper


def _scraper(**clients):
    s = UnifiedScraper.__new__(UnifiedScraper)
    for name in ("obscura", "crawl4ai", "firecrawl", "cloakbrowser", "site_unblocker", "web_data_api"):
        c = clients.get(name)
        if c is None:
            c = AsyncMock()
            c.health = AsyncMock(return_value=False)
            c.scrape = AsyncMock(side_effect=RuntimeError(f"{name} down"))
        setattr(s, name, c)
    s.engine_order = ["obscura", "crawl4ai", "firecrawl", "cloakbrowser", "site_unblocker", "web_data_api"]
    s.robots = None
    s.paid_guard = None
    s._engine_health = {}
    s._last_health_check = 0
    s._failed_engines = set()
    return s


def _ok_client(markdown="# ok"):
    c = AsyncMock()
    c.health = AsyncMock(return_value=True)
    c.scrape = AsyncMock(return_value={"url": "https://example.com", "markdown": markdown, "success": True})
    return c


# --- markdown ---

def test_html_to_markdown_strips_scripts_and_collects_links():
    html = """<html><head><title> T </title><style>x{}</style></head><body>
    <h1>Head</h1><script>evil()</script><p>Body <a href="/a">a</a> <a href="#x">skip</a>
    <a href="javascript:void(0)">js</a><a href="/a">dup</a></p></body></html>"""
    out = html_to_markdown(html, "https://site.test/page")
    assert out["title"] == "T"
    assert "# Head" in out["markdown"]
    assert "evil" not in out["markdown"]
    assert out["links"] == ["https://site.test/a"]


def test_html_to_markdown_empty():
    assert html_to_markdown("")["markdown"] == ""


# --- budget ---

@pytest.mark.asyncio
async def test_daily_budget_enforces_limit(tmp_path):
    b = DailyBudget(2, tmp_path / "b.json")
    assert await b.consume() == 1
    assert await b.consume() == 2
    with pytest.raises(BudgetExceeded):
        await b.consume()
    assert b.used() == 2


@pytest.mark.asyncio
async def test_daily_budget_resets_on_new_day(tmp_path):
    f = tmp_path / "b.json"
    f.write_text('{"date": "2000-01-01", "count": 99}')
    assert await DailyBudget(5, f).consume() == 1


@pytest.mark.asyncio
async def test_daily_budget_unlimited(tmp_path):
    b = DailyBudget(0, tmp_path / "b.json")
    for _ in range(5):
        await b.consume()
    assert b.used() == 5


@pytest.mark.asyncio
async def test_daily_budget_survives_corrupt_state(tmp_path):
    f = tmp_path / "b.json"
    f.write_text("not json")
    assert await DailyBudget(1, f).consume() == 1


@pytest.mark.asyncio
async def test_rate_limiter_spaces_calls():
    rl = RateLimiter(20)
    with patch("smard_crawler.common.budget.asyncio.sleep", new=AsyncMock()) as sleep:
        await rl.acquire()
        await rl.acquire()
    assert sleep.await_count == 1
    assert 0 < sleep.await_args.args[0] <= 0.05


@pytest.mark.asyncio
async def test_rate_limiter_disabled():
    rl = RateLimiter(0)
    with patch("smard_crawler.common.budget.asyncio.sleep", new=AsyncMock()) as sleep:
        await rl.acquire()
        await rl.acquire()
    sleep.assert_not_awaited()


@pytest.mark.asyncio
async def test_paid_guard(tmp_path):
    g = PaidGuard(0, 1, tmp_path / "b.json")
    await g.acquire()
    with pytest.raises(BudgetExceeded):
        await g.acquire()


# --- robots ---

def _robots_transport(status: int, body: str = ""):
    return httpx.MockTransport(lambda req: httpx.Response(status, text=body))


@pytest.mark.asyncio
async def test_robots_disallow_path():
    checker = RobotsChecker("SMardCrawler")
    real = httpx.AsyncClient
    with patch("smard_crawler.common.robots.httpx.AsyncClient",
               lambda **kw: real(transport=_robots_transport(200, "User-agent: *\nDisallow: /private\n"), **kw)):
        assert await checker.allowed("https://site.test/public") is True
        assert await checker.allowed("https://site.test/private/x") is False


@pytest.mark.asyncio
async def test_robots_404_allows_and_5xx_disallows():
    real = httpx.AsyncClient
    with patch("smard_crawler.common.robots.httpx.AsyncClient", lambda **kw: real(transport=_robots_transport(404), **kw)):
        assert await RobotsChecker().allowed("https://a.test/x") is True
    with patch("smard_crawler.common.robots.httpx.AsyncClient", lambda **kw: real(transport=_robots_transport(503), **kw)):
        assert await RobotsChecker().allowed("https://b.test/x") is False


@pytest.mark.asyncio
async def test_robots_unreachable_disallows_and_caches():
    calls = []

    def handler(req):
        calls.append(req)
        raise httpx.ConnectError("down")

    real = httpx.AsyncClient
    checker = RobotsChecker()
    with patch("smard_crawler.common.robots.httpx.AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw)):
        assert await checker.allowed("https://c.test/1") is False
        assert await checker.allowed("https://c.test/2") is False
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_robots_non_http_scheme_allowed():
    assert await RobotsChecker().allowed("file:///etc/hosts") is True


# --- browser clients ---

def test_http_base():
    assert _http_base("ws://localhost:9222") == "http://localhost:9222"
    assert _http_base("wss://obscura.example:443/devtools") == "https://obscura.example:443"


@pytest.mark.asyncio
async def test_obscura_health_ok_sends_bearer():
    seen = {}

    def handler(req):
        seen["auth"] = req.headers.get("authorization")
        return httpx.Response(200, json={"Browser": "Obscura"})

    real = httpx.AsyncClient
    c = ObscuraClient(cdp_url="ws://obscura.test:9222", token="t" * 32)
    c.enabled = True
    with patch("smard_crawler.browsers.client.httpx.AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw)):
        assert await c.health() is True
    assert seen["auth"] == "Bearer " + "t" * 32


@pytest.mark.asyncio
async def test_obscura_health_disabled_or_down():
    c = ObscuraClient(cdp_url="ws://127.0.0.1:1", binary="")
    c.enabled = False
    assert await c.health() is False
    c.enabled = True
    assert await c.health() is False


@pytest.mark.asyncio
async def test_cloakbrowser_health():
    c = CloakBrowserClient()
    c.enabled = False
    assert await c.health() is False
    c.enabled = True
    with patch.dict("sys.modules", {"cloakbrowser": MagicMock()}):
        assert await c.health() is True
    with patch.dict("sys.modules", {"cloakbrowser": None}):
        assert await c.health() is False


def _fake_browser(html="<html><head><title>X</title></head><body><h1>Hi</h1><a href='/n'>n</a></body></html>",
                  status=200, new_context_fails=False):
    page = AsyncMock()
    page.url = "https://site.test/final"
    page.goto = AsyncMock(return_value=MagicMock(status=status))
    page.content = AsyncMock(return_value=html)
    ctx = AsyncMock()
    ctx.new_page = AsyncMock(return_value=page)
    browser = MagicMock()
    browser.is_connected = MagicMock(return_value=True)
    browser.new_context = AsyncMock(side_effect=RuntimeError("unsupported") if new_context_fails else None,
                                    return_value=ctx)
    browser.contexts = [ctx]
    browser.close = AsyncMock()
    return browser, ctx, page


class _FakeEngine(BrowserEngineClient):
    name = "fake"

    def __init__(self, browser):
        super().__init__(max_sessions=2, timeout_ms=1000)
        self.opened = 0
        self._fake = browser

    async def _open_browser(self):
        self.opened += 1
        return self._fake


@pytest.mark.asyncio
async def test_browser_engine_scrape_and_reuse():
    browser, ctx, page = _fake_browser()
    eng = _FakeEngine(browser)
    r1 = await eng.scrape("https://site.test/", wait_for=10)
    await eng.scrape("https://site.test/2")
    assert r1["success"] and r1["title"] == "X" and "# Hi" in r1["markdown"]
    assert r1["links"] == ["https://site.test/n"]
    assert eng.opened == 1
    page.wait_for_timeout.assert_awaited_once_with(10)
    assert ctx.close.await_count == 2
    await eng.close()
    browser.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_browser_engine_falls_back_to_default_context_and_flags_http_errors():
    browser, ctx, page = _fake_browser(status=403, new_context_fails=True)
    eng = _FakeEngine(browser)
    r = await eng.scrape("https://site.test/", wait_selector="h1")
    assert r["success"] is False and r["status"] == 403
    page.wait_for_selector.assert_awaited_once()
    ctx.close.assert_not_awaited()


# --- scraper integration of new engines and guards ---

@pytest.mark.asyncio
async def test_obscura_first_in_chain():
    s = _scraper(obscura=_ok_client("# from obscura"), crawl4ai=_ok_client())
    with patch("smard_crawler.common.scraper.config") as cfg:
        cfg.site_unblocker.enabled = False
        cfg.decodo_api.enabled = False
        r = await s.scrape("https://example.com", save=False)
    assert r["engine"] == "obscura"
    s.crawl4ai.scrape.assert_not_awaited()


@pytest.mark.asyncio
async def test_engine_order_is_configurable():
    s = _scraper(obscura=_ok_client(), cloakbrowser=_ok_client("# cloak"))
    s.engine_order = ["cloakbrowser", "obscura"]
    with patch("smard_crawler.common.scraper.config") as cfg:
        cfg.site_unblocker.enabled = False
        cfg.decodo_api.enabled = False
        r = await s.scrape("https://example.com", save=False)
    assert r["engine"] == "cloakbrowser"


@pytest.mark.asyncio
async def test_robots_block():
    s = _scraper(obscura=_ok_client())
    s.robots = MagicMock()
    s.robots.allowed = AsyncMock(return_value=False)
    with pytest.raises(RobotsDisallowed):
        await s.scrape("https://example.com/private", save=False)
    s.obscura.scrape.assert_not_awaited()


@pytest.mark.asyncio
async def test_paid_engine_guarded_and_skipped_when_budget_exhausted(tmp_path):
    su = _ok_client("# su")
    wda = _ok_client("# wda")
    s = _scraper(site_unblocker=su, web_data_api=wda)
    s.paid_guard = PaidGuard(0, 1, tmp_path / "b.json")
    with patch("smard_crawler.common.scraper.config") as cfg:
        cfg.site_unblocker.enabled = True
        cfg.decodo_api.enabled = True
        r1 = await s.scrape("https://example.com/1", save=False)
        assert r1["engine"] == "site_unblocker"
        with pytest.raises(RuntimeError, match="All engines failed"):
            await s.scrape("https://example.com/2", save=False)
    su.scrape.assert_awaited_once()
    wda.scrape.assert_not_awaited()


@pytest.mark.asyncio
async def test_check_engines_covers_all_and_tolerates_exceptions():
    bad = AsyncMock()
    bad.health = AsyncMock(side_effect=RuntimeError("boom"))
    s = _scraper(obscura=_ok_client(), crawl4ai=bad)
    health = await s.check_engines()
    assert health["obscura"] is True and health["crawl4ai"] is False
    assert set(health) == {"obscura", "crawl4ai", "firecrawl", "cloakbrowser", "site_unblocker", "web_data_api"}


@pytest.mark.asyncio
async def test_close_closes_browser_engines():
    s = _scraper()
    s.obscura.close = AsyncMock()
    s.cloakbrowser.close = AsyncMock()
    await s.close()
    s.obscura.close.assert_awaited_once()
    s.cloakbrowser.close.assert_awaited_once()


def test_real_constructor_wires_everything(tmp_path, monkeypatch):
    s = UnifiedScraper()
    assert s.engine_order[0] == "obscura"
    assert isinstance(s.obscura, ObscuraClient) and isinstance(s.cloakbrowser, CloakBrowserClient)
    assert s.paid_guard is not None


def test_obscura_can_spawn_only_local_existing_binary(tmp_path):
    exe = tmp_path / "obscura"
    exe.write_text("")
    assert ObscuraClient(cdp_url="ws://127.0.0.1:9222", binary=str(exe))._can_spawn() is True
    assert ObscuraClient(cdp_url="ws://remote.test:9222", binary=str(exe))._can_spawn() is False
    assert ObscuraClient(cdp_url="ws://127.0.0.1:9222", binary=str(tmp_path / "missing"))._can_spawn() is False
    assert ObscuraClient(cdp_url="ws://127.0.0.1:9222", binary="")._can_spawn() is False


@pytest.mark.asyncio
async def test_obscura_open_browser_raises_when_unreachable():
    c = ObscuraClient(cdp_url="ws://127.0.0.1:1", binary="")
    with pytest.raises(RuntimeError, match="not reachable"):
        await c._open_browser()


def test_config_treats_empty_values_as_unset(monkeypatch):
    import importlib
    cfgmod = importlib.import_module("smard_crawler.common.config")

    for k in ("BUDGET_STATE_FILE", "OBSCURA_CDP_URL", "OBSCURA_MAX_SESSIONS", "ENGINE_ORDER", "DECODO_MAX_RPS"):
        monkeypatch.setenv(k, "")
    cfg = cfgmod.AppConfig()
    assert cfg.budget.state_file == cfgmod.SMARD_HOME / "budget.json"
    assert cfg.obscura.cdp_url == "ws://localhost:9222"
    assert cfg.obscura.max_sessions == 8
    assert cfg.engine_order[0] == "obscura"
    assert cfg.budget.max_rps == 2.0


def test_load_env_files_precedence(tmp_path, monkeypatch):
    import importlib
    cfgmod = importlib.import_module("smard_crawler.common.config")

    explicit = tmp_path / "explicit.env"
    explicit.write_text("SMARD_TEST_KEY=explicit\n")
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    (cwd / ".env").write_text("SMARD_TEST_KEY=cwd\nSMARD_TEST_OTHER=cwd\n")
    monkeypatch.chdir(cwd)
    monkeypatch.setenv("SMARD_ENV_FILE", str(explicit))
    monkeypatch.delenv("SMARD_TEST_KEY", raising=False)
    monkeypatch.delenv("SMARD_TEST_OTHER", raising=False)
    loaded = cfgmod.load_env_files()
    import os
    assert loaded[:2] == [explicit, cwd / ".env"]
    assert os.environ["SMARD_TEST_KEY"] == "explicit" and os.environ["SMARD_TEST_OTHER"] == "cwd"
    monkeypatch.delenv("SMARD_TEST_KEY")
    monkeypatch.delenv("SMARD_TEST_OTHER")
