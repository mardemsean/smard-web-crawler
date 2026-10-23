"""Tests for the URL guard, ScrapeService, HTTP API, MCP server and CLI."""

import json
import socket
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from smard_crawler.common.budget import BudgetExceeded
from smard_crawler.common.robots import RobotsDisallowed
from smard_crawler.common.urlguard import UnsafeURL, validate_url
from smard_crawler.server.service import MAX_BATCH, ScrapeService

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from smard_crawler.server.api import create_app  # noqa: E402


def _addrinfo(ip):
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    return AsyncMock(return_value=[(family, socket.SOCK_STREAM, 6, "", (ip, 443))])


def _public_dns():
    return patch("asyncio.BaseEventLoop.getaddrinfo", new=_addrinfo("93.184.215.14"))


# --- URL guard ---

@pytest.mark.asyncio
@pytest.mark.parametrize("ip", ["127.0.0.1", "10.0.0.5", "192.168.1.1", "169.254.169.254", "::1", "::ffff:10.0.0.1", "fd00::1"])
async def test_validate_url_blocks_internal(ip):
    with patch("asyncio.BaseEventLoop.getaddrinfo", new=_addrinfo(ip)):
        with pytest.raises(UnsafeURL):
            await validate_url("https://internal.test/")


@pytest.mark.asyncio
async def test_validate_url_allows_public():
    with _public_dns():
        assert await validate_url("https://example.com/x") == "https://example.com/x"


@pytest.mark.asyncio
@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://x.test/", "https:///nohost", "javascript:alert(1)"])
async def test_validate_url_rejects_bad_schemes(url):
    with pytest.raises(UnsafeURL):
        await validate_url(url)


@pytest.mark.asyncio
async def test_validate_url_private_opt_in(monkeypatch):
    monkeypatch.setenv("SMARD_ALLOW_PRIVATE", "true")
    assert await validate_url("http://127.0.0.1:8080/") == "http://127.0.0.1:8080/"


@pytest.mark.asyncio
async def test_validate_url_unresolvable():
    with patch("asyncio.BaseEventLoop.getaddrinfo", new=AsyncMock(side_effect=socket.gaierror("nx"))):
        with pytest.raises(UnsafeURL, match="cannot resolve"):
            await validate_url("https://nx.invalid/")


# --- service ---

def _service(markdown="# hello"):
    scraper = MagicMock()
    scraper.scrape = AsyncMock(return_value={"url": "https://example.com", "markdown": markdown, "success": True, "engine": "obscura"})
    scraper.scrape_batch = AsyncMock(side_effect=lambda urls, **kw: [{"url": u, "markdown": markdown, "success": True} for u in urls])
    scraper.crawl = AsyncMock(return_value={"pages": [], "success": True})
    scraper.map_site = AsyncMock(return_value={"urls": ["https://example.com/a"], "success": True})
    scraper.check_engines = AsyncMock(return_value={"obscura": True})
    scraper.engine_order = ["obscura"]
    scraper.robots = object()
    scraper.paid_guard = MagicMock()
    scraper.paid_guard.budget.used.return_value = 3
    scraper.paid_guard.budget.limit = 10
    scraper.close = AsyncMock()
    return ScrapeService(scraper), scraper


@pytest.mark.asyncio
async def test_service_scrape_truncates():
    svc, scraper = _service("x" * 100)
    with _public_dns():
        r = await svc.scrape("https://example.com", max_chars=10)
    assert r["markdown"] == "x" * 10 and r["truncated"] and r["total_chars"] == 100
    scraper.scrape.assert_awaited_once_with("https://example.com", engine="auto", save=False)


@pytest.mark.asyncio
async def test_service_rejects_unknown_engine():
    svc, _ = _service()
    with _public_dns(), pytest.raises(ValueError, match="unknown engine"):
        await svc.scrape("https://example.com", engine="nope")


@pytest.mark.asyncio
async def test_service_batch_limits():
    svc, scraper = _service()
    assert await svc.batch([]) == []
    with pytest.raises(ValueError, match="at most"):
        await svc.batch(["https://example.com"] * (MAX_BATCH + 1))
    with _public_dns():
        out = await svc.batch(["https://example.com/1", "https://example.com/2"], concurrency=999)
    assert len(out) == 2
    assert scraper.scrape_batch.await_args.kwargs["concurrency"] == 20


@pytest.mark.asyncio
async def test_service_health_crawl_map_close():
    svc, scraper = _service()
    h = await svc.health()
    assert h["engines"] == {"obscura": True} and h["paid_budget"] == {"used_today": 3, "daily_limit": 10}
    assert h["respect_robots"] is True
    with _public_dns():
        await svc.crawl("https://example.com", limit=10_000, max_depth=99)
        assert scraper.crawl.await_args.kwargs == {"limit": 500, "max_depth": 5}
        assert (await svc.map_site("https://example.com"))["urls"]
    await svc.close()
    scraper.close.assert_awaited_once()


# --- HTTP API ---

def test_api_auth_and_endpoints():
    svc, _ = _service()
    client = TestClient(create_app(svc, token="s" * 32))
    assert client.get("/health").status_code == 401
    assert client.get("/health", headers={"Authorization": "Bearer wrong"}).status_code == 401
    h = {"Authorization": "Bearer " + "s" * 32}
    assert client.get("/health", headers=h).json()["engines"] == {"obscura": True}
    with _public_dns():
        assert client.post("/scrape", json={"url": "https://example.com"}, headers=h).json()["markdown"] == "# hello"
        assert len(client.post("/batch", json={"urls": ["https://example.com"]}, headers=h).json()) == 1
        assert client.post("/crawl", json={"url": "https://example.com"}, headers=h).status_code == 200
        assert client.post("/map", json={"url": "https://example.com"}, headers=h).status_code == 200


@pytest.mark.parametrize("exc,status", [
    (RobotsDisallowed("no"), 403), (BudgetExceeded("cap"), 429), (RuntimeError("All engines failed"), 502), (ValueError("bad"), 400),
])
def test_api_error_mapping(exc, status):
    svc, scraper = _service()
    scraper.scrape.side_effect = exc
    client = TestClient(create_app(svc, token=""))
    with _public_dns():
        assert client.post("/scrape", json={"url": "https://example.com"}).status_code == status


def test_api_unsafe_url_is_400():
    svc, _ = _service()
    client = TestClient(create_app(svc, token=""))
    assert client.post("/scrape", json={"url": "file:///etc/passwd"}).status_code == 400


def test_api_validation():
    svc, _ = _service()
    client = TestClient(create_app(svc, token=""))
    assert client.post("/batch", json={"urls": ["https://e.com"] * (MAX_BATCH + 1)}).status_code == 422
    assert client.post("/crawl", json={"url": "https://e.com", "limit": 0}).status_code == 422


def test_serve_refuses_public_bind_without_token(monkeypatch):
    from smard_crawler.server import api

    monkeypatch.delenv("SMARD_API_TOKEN", raising=False)
    with pytest.raises(SystemExit, match="Refusing"):
        api.serve("0.0.0.0", 8787)


# --- MCP ---

mcp = pytest.importorskip("mcp")


def _tool_json(result):
    return json.loads(result.content[0].text)


@pytest.mark.asyncio
async def test_mcp_lists_tools_and_scrapes():
    from smard_crawler.server.mcp_server import build_server

    svc, _ = _service()
    server = build_server(svc)
    names = {t.name for t in await server.list_tools()}
    assert names == {"scrape", "scrape_batch", "crawl", "map_site", "engines_health"}
    with _public_dns():
        assert _tool_json(await server.call_tool("scrape", {"url": "https://example.com"}))["markdown"] == "# hello"
        batch = _tool_json(await server.call_tool("scrape_batch", {"urls": ["https://example.com"]}))
        assert batch["count"] == 1 and batch["succeeded"] == 1 and len(batch["results"]) == 1
        assert _tool_json(await server.call_tool("crawl", {"url": "https://example.com"}))["success"]
        assert _tool_json(await server.call_tool("map_site", {"url": "https://example.com"}))["urls"]
    assert _tool_json(await server.call_tool("engines_health", {}))["engines"] == {"obscura": True}


@pytest.mark.asyncio
@pytest.mark.parametrize("exc,kind", [
    (RobotsDisallowed("no"), "robots_disallowed"), (BudgetExceeded("cap"), "budget_exhausted"),
    (RuntimeError("down"), "engines_failed"), (ValueError("bad"), "invalid_request"),
])
async def test_mcp_errors_are_structured(exc, kind):
    from smard_crawler.server.mcp_server import build_server

    svc, scraper = _service()
    scraper.scrape.side_effect = exc
    with _public_dns():
        out = _tool_json(await build_server(svc).call_tool("scrape", {"url": "https://example.com"}))
    assert out == {"success": False, "error": kind, "detail": str(exc)}


@pytest.mark.asyncio
async def test_mcp_unsafe_url():
    from smard_crawler.server.mcp_server import build_server

    svc, _ = _service()
    out = _tool_json(await build_server(svc).call_tool("scrape", {"url": "file:///etc/passwd"}))
    assert out["error"] == "unsafe_url"


# --- CLI ---

def test_cli_parser_and_bench_dispatch():
    from smard_crawler import cli

    args = cli.build_parser().parse_args(["scrape", "https://example.com", "--engine", "obscura", "--no-save"])
    assert args.url == "https://example.com" and args.engine == "obscura" and args.no_save
    with patch("smard_crawler.bench.run.main") as bench:
        assert cli.main(["bench", "--rounds", "1"]) == 0
    bench.assert_called_once_with(["--rounds", "1"])


def test_cli_scrape_outputs_markdown(capsys):
    from smard_crawler import cli

    fake = MagicMock()
    fake.scrape = AsyncMock(return_value={"markdown": "# out", "success": True, "engine": "obscura"})
    fake.close = AsyncMock()
    with patch("smard_crawler.common.scraper.UnifiedScraper", return_value=fake):
        assert cli.main(["scrape", "https://example.com", "--no-save"]) == 0
    assert "# out" in capsys.readouterr().out
    fake.scrape.assert_awaited_once_with("https://example.com", engine="auto", save=False)
    fake.close.assert_awaited_once()


def test_cli_batch(tmp_path, capsys):
    from smard_crawler import cli

    f = tmp_path / "urls.txt"
    f.write_text("# comment\nhttps://a.test\n\nhttps://b.test\n")
    fake = MagicMock()
    fake.scrape_batch = AsyncMock(return_value=[{"url": "https://a.test", "success": True}, {"url": "https://b.test", "success": False}])
    fake.close = AsyncMock()
    with patch("smard_crawler.common.scraper.UnifiedScraper", return_value=fake):
        assert cli.main(["batch", str(f), "--no-save"]) == 1
    assert fake.scrape_batch.await_args.args[0] == ["https://a.test", "https://b.test"]
    assert json.loads(capsys.readouterr().out)[1]["success"] is False
