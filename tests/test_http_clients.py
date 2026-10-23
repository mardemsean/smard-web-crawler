"""HTTP-level tests for the Crawl4AI, Firecrawl and Decodo clients using httpx.MockTransport."""

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from smard_crawler.crawl4ai.client import Crawl4AIClient, _markdown_text
from smard_crawler.decodo.site_unblocker import SiteUnblockerClient
from smard_crawler.decodo.web_data_api import WebDataAPIClient
from smard_crawler.firecrawl.client import FirecrawlClient

_RealClient = httpx.AsyncClient


def mock_http(module: str, handler):
    """Patch httpx.AsyncClient inside `module` so every request goes to `handler`."""
    def factory(**kwargs):
        kwargs.pop("proxy", None)
        kwargs.pop("verify", None)
        return _RealClient(transport=httpx.MockTransport(handler), **kwargs)
    return patch(f"{module}.httpx.AsyncClient", factory)


NO_SLEEP = patch("asyncio.sleep", new=AsyncMock())


# --- Crawl4AI ---

def test_crawl4ai_payload_uses_only_untrusted_safe_fields():
    c = Crawl4AIClient(base_url="http://c4ai.test", api_token="")
    with patch("smard_crawler.crawl4ai.client.config") as cfg:
        cfg.stealth.enabled = True
        cfg.browser.headless = True
        cfg.browser.viewport_width = 1280
        cfg.browser.viewport_height = 720
        p = c.build_payload("https://example.com", strategy="pruning", wait_for="css:#main", timeout=120_000)
    assert p["urls"] == ["https://example.com"]
    b, r = p["browser_config"], p["crawler_config"]
    assert b["type"] == "BrowserConfig" and r["type"] == "CrawlerRunConfig"
    assert b["params"]["enable_stealth"] is True
    forbidden = {"proxy", "proxy_config", "magic", "simulate_user", "override_navigator", "js_code", "headers"}
    assert not forbidden & (set(b["params"]) | set(r["params"]))
    assert r["params"]["page_timeout"] == 60_000
    assert r["params"]["wait_for"] == "css:#main"
    assert r["params"]["markdown_generator"]["params"]["content_filter"]["type"] == "PruningContentFilter"


def test_crawl4ai_payload_without_stealth_or_filter():
    c = Crawl4AIClient(base_url="http://c4ai.test", api_token="")
    with patch("smard_crawler.crawl4ai.client.config") as cfg:
        cfg.stealth.enabled = True
        p = c.build_payload("https://example.com", strategy="none", stealth=False)
    assert p["browser_config"]["params"]["enable_stealth"] is False
    assert "markdown_generator" not in p["crawler_config"]["params"]


def test_crawl4ai_markdown_text_variants():
    assert _markdown_text({"raw_markdown": "raw", "fit_markdown": "fit"}) == "fit"
    assert _markdown_text({"raw_markdown": "raw", "fit_markdown": ""}) == "raw"
    assert _markdown_text("plain") == "plain"
    assert _markdown_text(None) == ""


@pytest.mark.asyncio
async def test_crawl4ai_400_is_not_retried():
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(400, json={"detail": "Rejected config: field 'magic' is not permitted"})

    with mock_http("smard_crawler.crawl4ai.client", handler):
        with pytest.raises(ValueError, match="rejected"):
            await Crawl4AIClient(base_url="http://c4ai.test", api_token="").scrape("https://example.com")
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_crawl4ai_401_is_not_retried():
    calls = []
    with mock_http("smard_crawler.crawl4ai.client", lambda r: calls.append(1) or httpx.Response(401)):
        with pytest.raises(httpx.HTTPStatusError):
            await Crawl4AIClient(base_url="http://c4ai.test", api_token="bad").scrape("https://example.com")
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_crawl4ai_scrape_parses_response_and_sends_token():
    seen = {}

    def handler(req):
        seen["auth"] = req.headers.get("authorization")
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json={"success": True, "results": [{
            "url": "https://example.com", "success": True, "status_code": 200,
            "markdown": {"raw_markdown": "# Raw", "fit_markdown": "# Fit"}, "metadata": {"title": "Ex"}}]})

    c = Crawl4AIClient(base_url="http://c4ai.test", api_token="tok")
    with mock_http("smard_crawler.crawl4ai.client", handler):
        r = await c.scrape("https://example.com")
    assert r["markdown"] == "# Fit" and r["status"] == 200 and r["metadata"]["title"] == "Ex"
    assert seen["auth"] == "Bearer tok"
    assert seen["body"]["crawler_config"]["type"] == "CrawlerRunConfig"


@pytest.mark.asyncio
async def test_crawl4ai_failed_result_raises_without_retry():
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(200, json={"results": [{"success": False, "error_message": "net::ERR_BLOCKED"}]})

    with mock_http("smard_crawler.crawl4ai.client", handler):
        with pytest.raises(RuntimeError, match="ERR_BLOCKED"):
            await Crawl4AIClient(base_url="http://c4ai.test", api_token="").scrape("https://example.com")
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_crawl4ai_http_error_retries_then_raises():
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(503)

    with mock_http("smard_crawler.crawl4ai.client", handler), NO_SLEEP:
        with pytest.raises(httpx.HTTPStatusError):
            await Crawl4AIClient(base_url="http://c4ai.test", api_token="").scrape("https://example.com")
    assert len(calls) == 3


@pytest.mark.asyncio
async def test_crawl4ai_empty_results():
    with mock_http("smard_crawler.crawl4ai.client", lambda r: httpx.Response(200, json={"results": []})):
        with pytest.raises(ValueError, match="No results"):
            await Crawl4AIClient(base_url="http://c4ai.test", api_token="").scrape("https://example.com")


@pytest.mark.asyncio
async def test_crawl4ai_health():
    with mock_http("smard_crawler.crawl4ai.client", lambda r: httpx.Response(200, json={"status": "ok"})):
        assert await Crawl4AIClient(base_url="http://c4ai.test").health() is True
    with mock_http("smard_crawler.crawl4ai.client", lambda r: (_ for _ in ()).throw(httpx.ConnectError("x"))):
        assert await Crawl4AIClient(base_url="http://c4ai.test").health() is False


# --- Firecrawl ---

@pytest.mark.asyncio
async def test_firecrawl_scrape():
    seen = {}

    def handler(req):
        seen["path"] = req.url.path
        seen["body"] = json.loads(req.content)
        seen["auth"] = req.headers.get("authorization")
        return httpx.Response(200, json={"success": True, "data": {
            "markdown": "# FC", "metadata": {"sourceURL": "https://example.com/final"}}})

    with mock_http("smard_crawler.firecrawl.client", handler):
        r = await FirecrawlClient(host="http://fc.test", api_key="fc-key").scrape("https://example.com", wait_for=500)
    assert r == {"url": "https://example.com/final", "markdown": "# FC", "html": "",
                 "metadata": {"sourceURL": "https://example.com/final"}, "success": True}
    assert seen["path"] == "/v1/scrape" and seen["body"]["waitFor"] == 500 and seen["auth"] == "Bearer fc-key"


@pytest.mark.asyncio
async def test_firecrawl_crawl_polls_until_completed():
    polls = []

    def handler(req):
        if req.method == "POST":
            return httpx.Response(200, json={"success": True, "id": "job-1"})
        polls.append(1)
        if len(polls) < 2:
            return httpx.Response(200, json={"status": "scraping"})
        return httpx.Response(200, json={"status": "completed", "total": 1, "data": [
            {"markdown": "# P", "metadata": {"sourceURL": "https://example.com/p"}}]})

    with mock_http("smard_crawler.firecrawl.client", handler), NO_SLEEP:
        r = await FirecrawlClient(host="http://fc.test").crawl("https://example.com", limit=5)
    assert r["job_id"] == "job-1" and r["pages"][0]["url"] == "https://example.com/p" and len(polls) == 2


@pytest.mark.asyncio
async def test_firecrawl_crawl_failed_status():
    def handler(req):
        if req.method == "POST":
            return httpx.Response(200, json={"id": "job-2"})
        return httpx.Response(200, json={"status": "failed"})

    with mock_http("smard_crawler.firecrawl.client", handler), NO_SLEEP:
        with pytest.raises(RuntimeError, match="Crawl failed"):
            await FirecrawlClient(host="http://fc.test")._poll_crawl("job-2", 10_000)


@pytest.mark.asyncio
async def test_firecrawl_health():
    with mock_http("smard_crawler.firecrawl.client", lambda r: httpx.Response(200, text="ok")):
        assert await FirecrawlClient(host="http://fc.test").health() is True
    with mock_http("smard_crawler.firecrawl.client", lambda r: httpx.Response(500)):
        assert await FirecrawlClient(host="http://fc.test").health() is False


# --- Decodo Site Unblocker ---

@pytest.mark.asyncio
async def test_site_unblocker_sends_su_headers_and_detects_markdown():
    seen = {}

    def handler(req):
        seen.update(req.headers)
        return httpx.Response(200, text="# Example Domain\n\ntext")

    c = SiteUnblockerClient(proxy_url="https://u:p@unblock.decodo.com:60000")
    with mock_http("smard_crawler.decodo.site_unblocker", handler):
        r = await c.scrape("https://example.com", geo="Brazil", session_id="s1")
    assert r["markdown"].startswith("# Example") and r["html"] == ""
    assert seen["x-su-headless"] == "html" and seen["x-su-markdown"] == "1"
    assert seen["x-su-geo"] == "Brazil" and seen["x-su-session"] == "s1"


@pytest.mark.asyncio
async def test_site_unblocker_html_response():
    c = SiteUnblockerClient(proxy_url="https://u:p@unblock.decodo.com:60000")
    with mock_http("smard_crawler.decodo.site_unblocker", lambda r: httpx.Response(200, text="<html>x</html>")):
        r = await c.scrape("https://example.com", js_render=False)
    assert r["markdown"] == "" and r["html"].startswith("<html>")


@pytest.mark.asyncio
async def test_site_unblocker_health_is_config_only_and_free():
    calls = []
    with mock_http("smard_crawler.decodo.site_unblocker", lambda r: calls.append(r) or httpx.Response(200)):
        assert await SiteUnblockerClient(proxy_url="https://u:p@unblock.decodo.com:60000").health() is True
    assert calls == []
    with patch("smard_crawler.decodo.site_unblocker.config") as cfg:
        cfg.site_unblocker_url = ""
        assert await SiteUnblockerClient().health() is False


# --- Decodo Web Data API ---

@pytest.mark.asyncio
async def test_web_data_api_scrape():
    seen = {}

    def handler(req):
        seen["url"] = str(req.url)
        seen["auth"] = req.headers.get("authorization")
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json={"results": [{"content": "# WDA", "status_code": 200, "task_id": "t1"}]})

    c = WebDataAPIClient(api_key="key", base_url="https://data.decodo.com/v1")
    with mock_http("smard_crawler.decodo.web_data_api", handler):
        r = await c.scrape("https://example.com", js_render=True, geo="Brazil")
    assert seen["url"] == "https://data.decodo.com/v1/scrape" and seen["auth"] == "Bearer key"
    assert seen["body"] == {"url": "https://example.com", "markdown": True, "headless": "html",
                            "proxy_pool": "standard", "geo": "Brazil"}
    assert r["markdown"] == "# WDA" and r["metadata"]["task_id"] == "t1"


@pytest.mark.asyncio
async def test_web_data_api_crawl_and_map():
    def handler(req):
        if req.url.path.endswith("/crawl") and req.method == "POST":
            return httpx.Response(200, json={"crawl_id": "c1"})
        if "/crawl/c1" in req.url.path:
            return httpx.Response(200, json={"status": "done", "completed": 1, "results": [{"url": "https://e.com/a", "content": "# A"}]})
        if req.url.path.endswith("/map"):
            return httpx.Response(200, json={"urls": ["https://e.com/a", "https://e.com/b"]})
        return httpx.Response(404)

    c = WebDataAPIClient(api_key="key", base_url="https://data.decodo.com/v1")
    with mock_http("smard_crawler.decodo.web_data_api", handler), NO_SLEEP:
        crawl = await c.crawl("https://e.com", limit=2)
        mapped = await c.map_site("https://e.com")
        pending = await c.crawl("https://e.com", callback_url="https://hook.test/cb")
    assert crawl["pages"] == [{"url": "https://e.com/a", "markdown": "# A", "metadata": {}}]
    assert mapped["total"] == 2
    assert pending == {"crawl_id": "c1", "status": "pending", "success": True}


@pytest.mark.asyncio
async def test_web_data_api_health_never_spends_a_request():
    calls = []
    with mock_http("smard_crawler.decodo.web_data_api", lambda r: calls.append(r) or httpx.Response(200)):
        assert await WebDataAPIClient(api_key="key").health() is True
    assert calls == []
    with patch("smard_crawler.decodo.web_data_api.config") as cfg:
        cfg.decodo_api_key = ""
        cfg.decodo_api_url = "https://data.decodo.com/v1"
        assert await WebDataAPIClient().health() is False
