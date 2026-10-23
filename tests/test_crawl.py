"""Tests for the native BFS crawler (smard_crawler/common/crawl.py)."""

import pytest

from smard_crawler.common.crawl import _norm, _same_site, bfs_crawl

SITE = {
    "https://site.test/": {"markdown": "# home", "title": "Home",
                            "links": ["https://site.test/a", "https://site.test/b", "https://other.test/x"]},
    "https://site.test/a": {"markdown": "# a", "links": ["https://site.test/a/deep", "https://site.test/"]},
    "https://site.test/b": {"markdown": "# b", "links": ["https://site.test/a"]},
    "https://site.test/a/deep": {"markdown": "# deep", "links": ["https://site.test/a/deeper"]},
    "https://site.test/a/deeper": {"markdown": "# deeper", "links": []},
    "https://other.test/x": {"markdown": "# other", "links": []},
}


def make_fetch(site=SITE, record=None):
    async def fetch(url):
        if record is not None:
            record.append(url)
        if url not in site:
            raise RuntimeError(f"404 {url}")
        return {"final_url": url, "success": True, **site[url]}
    return fetch


def test_norm_and_same_site():
    assert _norm("https://x.test/p#frag") == "https://x.test/p"
    assert _norm("https://x.test/p/") == "https://x.test/p"
    assert _norm("https://x.test/") == "https://x.test/"
    assert _same_site("https://x.test/a", "https://x.test/b")
    assert not _same_site("https://x.test/a", "https://y.test/a")
    assert not _same_site("ftp://x.test/a", "ftp://x.test/b")


@pytest.mark.asyncio
async def test_bfs_respects_same_domain_and_depth():
    visited = []
    result = await bfs_crawl(make_fetch(record=visited), "https://site.test/", limit=50, max_depth=2)
    urls = {p["url"] for p in result["pages"]}
    assert "https://other.test/x" not in urls  # cross-domain dropped
    assert "https://site.test/a/deeper" not in urls  # depth 3, beyond max_depth=2
    assert urls == {"https://site.test/", "https://site.test/a", "https://site.test/b", "https://site.test/a/deep"}
    assert result["total"] == 4 and result["success"]
    # Each page fetched exactly once despite back-links and shared links.
    assert len(visited) == len(set(visited)) == 4


@pytest.mark.asyncio
async def test_bfs_depth_zero_is_just_start():
    result = await bfs_crawl(make_fetch(), "https://site.test/", max_depth=0)
    assert [p["url"] for p in result["pages"]] == ["https://site.test/"]


@pytest.mark.asyncio
async def test_bfs_limit_caps_pages():
    result = await bfs_crawl(make_fetch(), "https://site.test/", limit=2, max_depth=5)
    assert result["total"] == 2


@pytest.mark.asyncio
async def test_bfs_dead_link_recorded_not_fatal():
    site = dict(SITE)
    site["https://site.test/"] = {"markdown": "# home", "links": ["https://site.test/missing", "https://site.test/a"]}
    result = await bfs_crawl(make_fetch(site), "https://site.test/", max_depth=1)
    by_url = {p["url"]: p for p in result["pages"]}
    assert by_url["https://site.test/missing"]["success"] is False
    assert "error" in by_url["https://site.test/missing"]
    assert by_url["https://site.test/a"]["success"] is True
    assert result["errors"] == 1 and result["success"]


@pytest.mark.asyncio
async def test_bfs_all_fail_is_unsuccessful():
    async def fetch(url):
        raise RuntimeError("down")
    result = await bfs_crawl(fetch, "https://site.test/", max_depth=1)
    assert result["success"] is False and result["total"] == 1


@pytest.mark.asyncio
async def test_bfs_cross_domain_allowed_when_flag_off():
    result = await bfs_crawl(make_fetch(), "https://site.test/", max_depth=1, same_domain=False)
    assert "https://other.test/x" in {p["url"] for p in result["pages"]}
