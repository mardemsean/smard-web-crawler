"""Tests for src/common/scraper.py — UnifiedScraper fallback chain, batch, and resilience."""

import asyncio
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.common.scraper import (
    BATCH_RECHECK_INTERVAL,
    FALLBACK_ORDER,
    LIVENESS_INTERVAL,
    UnifiedScraper,
    _INTRA_ENGINE_VARIANTS,
)


@pytest.fixture
def scraper(mock_crawl4ai, mock_firecrawl, mock_site_unblocker, mock_web_data_api):
    s = UnifiedScraper.__new__(UnifiedScraper)
    s.crawl4ai = mock_crawl4ai
    s.firecrawl = mock_firecrawl
    s.site_unblocker = mock_site_unblocker
    s.web_data_api = mock_web_data_api
    s._engine_health = {}
    s._last_health_check = 0
    s._failed_engines = set()
    return s


class TestConstants:
    def test_fallback_order(self):
        assert FALLBACK_ORDER == ["crawl4ai", "firecrawl", "site_unblocker", "web_data_api"]

    def test_liveness_interval(self):
        assert LIVENESS_INTERVAL == 300

    def test_batch_recheck_interval(self):
        assert BATCH_RECHECK_INTERVAL == 10

    def test_intra_engine_variants_exist(self):
        assert "crawl4ai" in _INTRA_ENGINE_VARIANTS
        assert "firecrawl" in _INTRA_ENGINE_VARIANTS
        assert "site_unblocker" in _INTRA_ENGINE_VARIANTS
        assert "web_data_api" in _INTRA_ENGINE_VARIANTS


class TestCheckEngines:
    @pytest.mark.asyncio
    async def test_check_engines_returns_health(self, scraper):
        health = await scraper.check_engines()
        assert health["crawl4ai"] is True
        assert health["firecrawl"] is True
        assert health["site_unblocker"] is False
        assert health["web_data_api"] is False

    @pytest.mark.asyncio
    async def test_check_engines_updates_failed_set(self, scraper):
        await scraper.check_engines()
        assert "site_unblocker" in scraper._failed_engines
        assert "web_data_api" in scraper._failed_engines
        assert "crawl4ai" not in scraper._failed_engines

    @pytest.mark.asyncio
    async def test_check_engines_updates_timestamp(self, scraper):
        before = time.monotonic()
        await scraper.check_engines()
        assert scraper._last_health_check >= before


class TestMaybeRefreshHealth:
    @pytest.mark.asyncio
    async def test_refresh_when_no_health_data(self, scraper):
        assert scraper._engine_health == {}
        await scraper._maybe_refresh_health()
        assert scraper._engine_health != {}

    @pytest.mark.asyncio
    async def test_no_refresh_when_recent(self, scraper):
        await scraper.check_engines()
        call_count = scraper.crawl4ai.health.call_count
        await scraper._maybe_refresh_health()
        assert scraper.crawl4ai.health.call_count == call_count

    @pytest.mark.asyncio
    async def test_refresh_when_forced(self, scraper):
        await scraper.check_engines()
        call_count = scraper.crawl4ai.health.call_count
        await scraper._maybe_refresh_health(force=True)
        assert scraper.crawl4ai.health.call_count > call_count

    @pytest.mark.asyncio
    async def test_refresh_when_stale(self, scraper):
        await scraper.check_engines()
        scraper._last_health_check = time.monotonic() - LIVENESS_INTERVAL - 1
        call_count = scraper.crawl4ai.health.call_count
        await scraper._maybe_refresh_health()
        assert scraper.crawl4ai.health.call_count > call_count


class TestRecheckFailedEngines:
    @pytest.mark.asyncio
    async def test_no_failed_returns_empty(self, scraper):
        scraper._failed_engines = set()
        recovered = await scraper._recheck_failed_engines()
        assert recovered == []

    @pytest.mark.asyncio
    async def test_recovery_detected(self, scraper):
        scraper._failed_engines = {"crawl4ai"}
        scraper._engine_health = {"crawl4ai": False}
        scraper.crawl4ai.health = AsyncMock(return_value=True)
        recovered = await scraper._recheck_failed_engines()
        assert "crawl4ai" in recovered
        assert "crawl4ai" not in scraper._failed_engines
        assert scraper._engine_health["crawl4ai"] is True

    @pytest.mark.asyncio
    async def test_still_failed_not_recovered(self, scraper):
        scraper._failed_engines = {"site_unblocker"}
        scraper._engine_health = {"site_unblocker": False}
        scraper.site_unblocker.health = AsyncMock(return_value=False)
        recovered = await scraper._recheck_failed_engines()
        assert recovered == []
        assert "site_unblocker" in scraper._failed_engines

    @pytest.mark.asyncio
    async def test_health_exception_treated_as_still_failed(self, scraper):
        scraper._failed_engines = {"crawl4ai"}
        scraper._engine_health = {"crawl4ai": False}
        scraper.crawl4ai.health = AsyncMock(side_effect=ConnectionError("down"))
        recovered = await scraper._recheck_failed_engines()
        assert recovered == []


class TestFallbackOrder:
    @pytest.mark.asyncio
    async def test_healthy_engines_included(self, scraper):
        scraper._engine_health = {
            "crawl4ai": True,
            "firecrawl": True,
            "site_unblocker": False,
            "web_data_api": False,
        }
        with patch("src.common.scraper.config") as mock_config:
            mock_config.site_unblocker.enabled = False
            mock_config.decodo_api.enabled = False
            order = await scraper._fallback_order()
        assert order == ["crawl4ai", "firecrawl"]

    @pytest.mark.asyncio
    async def test_site_unblocker_included_when_configured(self, scraper):
        scraper._engine_health = {
            "crawl4ai": True,
            "firecrawl": False,
            "site_unblocker": False,
            "web_data_api": False,
        }
        with patch("src.common.scraper.config") as mock_config:
            mock_config.site_unblocker.enabled = True
            mock_config.decodo_api.enabled = False
            order = await scraper._fallback_order()
        assert "site_unblocker" in order

    @pytest.mark.asyncio
    async def test_web_data_api_included_when_configured(self, scraper):
        scraper._engine_health = {
            "crawl4ai": True,
            "firecrawl": False,
            "site_unblocker": False,
            "web_data_api": False,
        }
        with patch("src.common.scraper.config") as mock_config:
            mock_config.site_unblocker.enabled = False
            mock_config.decodo_api.enabled = True
            order = await scraper._fallback_order()
        assert "web_data_api" in order

    @pytest.mark.asyncio
    async def test_no_engines_raises(self, scraper):
        scraper._engine_health = {
            "crawl4ai": False,
            "firecrawl": False,
            "site_unblocker": False,
            "web_data_api": False,
        }
        with patch("src.common.scraper.config") as mock_config:
            mock_config.site_unblocker.enabled = False
            mock_config.decodo_api.enabled = False
            with pytest.raises(RuntimeError, match="No scraping engine available"):
                await scraper._fallback_order()


class TestScrapeWithEngine:
    @pytest.mark.asyncio
    async def test_scrape_with_crawl4ai(self, scraper):
        with patch("src.common.scraper.config") as mock_config:
            mock_config.output.dir = Path("/tmp/test-output")
            mock_config.output.include_meta = False
            result = await scraper._scrape_with("crawl4ai", "https://example.com", save=False)
        assert result["success"]
        assert result["engine"] == "crawl4ai"
        assert "elapsed_ms" in result

    @pytest.mark.asyncio
    async def test_scrape_with_firecrawl(self, scraper):
        result = await scraper._scrape_with("firecrawl", "https://example.com", save=False)
        assert result["engine"] == "firecrawl"

    @pytest.mark.asyncio
    async def test_scrape_with_site_unblocker(self, scraper):
        result = await scraper._scrape_with("site_unblocker", "https://example.com", save=False)
        assert result["engine"] == "site_unblocker"

    @pytest.mark.asyncio
    async def test_scrape_with_web_data_api(self, scraper):
        result = await scraper._scrape_with("web_data_api", "https://example.com", save=False)
        assert result["engine"] == "web_data_api"

    @pytest.mark.asyncio
    async def test_scrape_with_unknown_engine_raises(self, scraper):
        with pytest.raises(ValueError, match="Unknown engine"):
            await scraper._scrape_with("unknown", "https://example.com", save=False)

    @pytest.mark.asyncio
    async def test_scrape_with_records_elapsed(self, scraper):
        result = await scraper._scrape_with("crawl4ai", "https://example.com", save=False)
        assert isinstance(result["elapsed_ms"], int)
        assert result["elapsed_ms"] >= 0


class TestScrapeAuto:
    @pytest.mark.asyncio
    async def test_scrape_auto_uses_first_healthy(self, scraper):
        scraper._engine_health = {"crawl4ai": True, "firecrawl": True}
        scraper._last_health_check = time.monotonic()
        with patch("src.common.scraper.config") as mock_config:
            mock_config.site_unblocker.enabled = False
            mock_config.decodo_api.enabled = False
            result = await scraper.scrape("https://example.com", save=False)
        assert result["success"]
        assert result["engine"] == "crawl4ai"

    @pytest.mark.asyncio
    async def test_scrape_specific_engine(self, scraper):
        result = await scraper.scrape("https://example.com", engine="firecrawl", save=False)
        assert result["engine"] == "firecrawl"

    @pytest.mark.asyncio
    async def test_scrape_fallback_on_failure(self, scraper):
        scraper.crawl4ai.scrape = AsyncMock(side_effect=ConnectionError("down"))
        scraper._engine_health = {"crawl4ai": True, "firecrawl": True}
        scraper._last_health_check = time.monotonic()
        with patch("src.common.scraper.config") as mock_config:
            mock_config.site_unblocker.enabled = False
            mock_config.decodo_api.enabled = False
            result = await scraper.scrape(
                "https://example.com", save=False, intra_retry=False,
            )
        assert result["engine"] == "firecrawl"

    @pytest.mark.asyncio
    async def test_scrape_fallback_on_empty_result(self, scraper):
        scraper.crawl4ai.scrape = AsyncMock(return_value={
            "url": "https://example.com",
            "markdown": "",
            "success": True,
        })
        scraper._engine_health = {"crawl4ai": True, "firecrawl": True}
        scraper._last_health_check = time.monotonic()
        with patch("src.common.scraper.config") as mock_config:
            mock_config.site_unblocker.enabled = False
            mock_config.decodo_api.enabled = False
            result = await scraper.scrape(
                "https://example.com", save=False, intra_retry=False,
            )
        assert result["engine"] == "firecrawl"

    @pytest.mark.asyncio
    async def test_scrape_all_fail_raises(self, scraper):
        scraper.crawl4ai.scrape = AsyncMock(side_effect=ConnectionError("down"))
        scraper.firecrawl.scrape = AsyncMock(side_effect=ConnectionError("down"))
        scraper._engine_health = {"crawl4ai": True, "firecrawl": True}
        scraper._last_health_check = time.monotonic()
        with patch("src.common.scraper.config") as mock_config:
            mock_config.site_unblocker.enabled = False
            mock_config.decodo_api.enabled = False
            with pytest.raises(RuntimeError, match="All engines failed"):
                await scraper.scrape(
                    "https://example.com", save=False, intra_retry=False,
                )

    @pytest.mark.asyncio
    async def test_scrape_no_fallback_raises_immediately(self, scraper):
        scraper.crawl4ai.scrape = AsyncMock(side_effect=ConnectionError("down"))
        scraper._engine_health = {"crawl4ai": True, "firecrawl": True}
        scraper._last_health_check = time.monotonic()
        with patch("src.common.scraper.config") as mock_config:
            mock_config.site_unblocker.enabled = False
            mock_config.decodo_api.enabled = False
            with pytest.raises(ConnectionError):
                await scraper.scrape(
                    "https://example.com",
                    engine="crawl4ai",
                    save=False,
                    fallback=False,
                )

    @pytest.mark.asyncio
    async def test_scrape_marks_failed_engine(self, scraper):
        scraper.crawl4ai.scrape = AsyncMock(side_effect=ConnectionError("down"))
        scraper._engine_health = {"crawl4ai": True, "firecrawl": True}
        scraper._last_health_check = time.monotonic()
        with patch("src.common.scraper.config") as mock_config:
            mock_config.site_unblocker.enabled = False
            mock_config.decodo_api.enabled = False
            await scraper.scrape(
                "https://example.com", save=False, intra_retry=False,
            )
        assert "crawl4ai" in scraper._failed_engines


class TestIntraEngineRetry:
    @pytest.mark.asyncio
    async def test_intra_retry_tries_variants(self, scraper):
        call_count = 0

        async def flaky_scrape(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"url": "https://example.com", "markdown": "", "success": True}
            return {"url": "https://example.com", "markdown": "# Got it", "success": True}

        scraper.crawl4ai.scrape = AsyncMock(side_effect=flaky_scrape)
        scraper._engine_health = {"crawl4ai": True}
        scraper._last_health_check = time.monotonic()
        with patch("src.common.scraper.config") as mock_config:
            mock_config.site_unblocker.enabled = False
            mock_config.decodo_api.enabled = False
            mock_config.output.dir = Path("/tmp/test-output")
            mock_config.output.include_meta = False
            result = await scraper.scrape("https://example.com", save=False)
        assert result["markdown"] == "# Got it"
        assert call_count >= 2


class TestSave:
    @pytest.mark.asyncio
    async def test_save_writes_file(self, scraper, tmp_path):
        with patch("src.common.scraper.config") as mock_config:
            mock_config.output.dir = tmp_path
            mock_config.output.include_meta = True
            result = {
                "markdown": "# Test Content",
                "engine": "crawl4ai",
                "elapsed_ms": 150,
            }
            path = await scraper._save("https://example.com/page", result)
        saved = Path(path)
        assert saved.exists()
        content = saved.read_text()
        assert "# Test Content" in content
        assert "source: https://example.com/page" in content
        assert "engine: crawl4ai" in content

    @pytest.mark.asyncio
    async def test_save_without_meta(self, scraper, tmp_path):
        with patch("src.common.scraper.config") as mock_config:
            mock_config.output.dir = tmp_path
            mock_config.output.include_meta = False
            result = {"markdown": "# Raw Content", "engine": "test", "elapsed_ms": 0}
            path = await scraper._save("https://example.com", result)
        content = Path(path).read_text()
        assert content == "# Raw Content"
        assert "---" not in content

    @pytest.mark.asyncio
    async def test_save_creates_output_dir(self, scraper, tmp_path):
        output_dir = tmp_path / "new" / "nested"
        with patch("src.common.scraper.config") as mock_config:
            mock_config.output.dir = output_dir
            mock_config.output.include_meta = False
            result = {"markdown": "content", "engine": "test", "elapsed_ms": 0}
            await scraper._save("https://example.com", result)
        assert output_dir.exists()

    @pytest.mark.asyncio
    async def test_save_filename_sanitization(self, scraper, tmp_path):
        with patch("src.common.scraper.config") as mock_config:
            mock_config.output.dir = tmp_path
            mock_config.output.include_meta = False
            result = {"markdown": "ok", "engine": "test", "elapsed_ms": 0}
            path = await scraper._save("https://ex.com/path?q=1&a=2", result)
        filename = Path(path).name
        assert "?" not in filename
        assert "/" not in filename


class TestScrapeBatch:
    @pytest.mark.asyncio
    async def test_batch_returns_all_results(self, scraper):
        scraper._engine_health = {"crawl4ai": True, "firecrawl": True}
        scraper._last_health_check = time.monotonic()
        urls = ["https://example.com/1", "https://example.com/2", "https://example.com/3"]
        with patch("src.common.scraper.config") as mock_config:
            mock_config.site_unblocker.enabled = False
            mock_config.decodo_api.enabled = False
            mock_config.output.dir = Path("/tmp/test-output")
            mock_config.output.include_meta = False
            results = await scraper.scrape_batch(urls, concurrency=2)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_batch_handles_individual_failures(self, scraper):
        call_count = 0

        async def sometimes_fail(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if "fail" in url:
                raise ConnectionError("boom")
            return {"url": url, "markdown": "ok", "success": True}

        scraper.crawl4ai.scrape = AsyncMock(side_effect=sometimes_fail)
        scraper.firecrawl.scrape = AsyncMock(side_effect=sometimes_fail)
        scraper._engine_health = {"crawl4ai": True, "firecrawl": True}
        scraper._last_health_check = time.monotonic()

        urls = ["https://example.com/ok", "https://example.com/fail"]
        with patch("src.common.scraper.config") as mock_config:
            mock_config.site_unblocker.enabled = False
            mock_config.decodo_api.enabled = False
            results = await scraper.scrape_batch(urls, concurrency=1)
        assert len(results) == 2
        successes = [r for r in results if r.get("success")]
        failures = [r for r in results if r.get("error")]
        assert len(successes) >= 1


class TestCrawl:
    @pytest.mark.asyncio
    async def test_crawl_uses_firecrawl_when_healthy(self, scraper):
        scraper._engine_health = {"firecrawl": True}
        result = await scraper.crawl("https://example.com")
        assert result["success"]
        scraper.firecrawl.crawl.assert_called_once()

    @pytest.mark.asyncio
    async def test_crawl_falls_back_to_web_data_api(self, scraper):
        scraper._engine_health = {"firecrawl": True}
        scraper.firecrawl.crawl = AsyncMock(side_effect=ConnectionError("down"))
        scraper.web_data_api.enabled = True
        result = await scraper.crawl("https://example.com")
        assert result["success"]
        scraper.web_data_api.crawl.assert_called_once()

    @pytest.mark.asyncio
    async def test_crawl_no_engine_raises(self, scraper):
        scraper._engine_health = {"firecrawl": False}
        scraper.web_data_api.enabled = False
        with pytest.raises(RuntimeError, match="No crawl engine available"):
            await scraper.crawl("https://example.com")


class TestMapSite:
    @pytest.mark.asyncio
    async def test_map_site_returns_urls(self, scraper):
        scraper.web_data_api.enabled = True
        result = await scraper.map_site("https://example.com")
        assert result["total"] == 2

    @pytest.mark.asyncio
    async def test_map_site_disabled_raises(self, scraper):
        scraper.web_data_api.enabled = False
        with pytest.raises(RuntimeError, match="Web Data API not configured"):
            await scraper.map_site("https://example.com")
