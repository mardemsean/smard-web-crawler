"""Shared fixtures for smard-web-crawler tests."""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("PROXY_URL", "")
os.environ.setdefault("SITE_UNBLOCKER_URL", "")
os.environ.setdefault("DECODO_API_KEY", "")
os.environ.setdefault("OUTPUT_DIR", "/tmp/test-output")


@pytest.fixture
def mock_crawl4ai():
    client = AsyncMock()
    client.health = AsyncMock(return_value=True)
    client.scrape = AsyncMock(return_value={
        "url": "https://example.com",
        "markdown": "# Example\n\nHello world",
        "success": True,
    })
    return client


@pytest.fixture
def mock_firecrawl():
    client = AsyncMock()
    client.health = AsyncMock(return_value=True)
    client.scrape = AsyncMock(return_value={
        "url": "https://example.com",
        "markdown": "# Firecrawl Result",
        "success": True,
    })
    client.crawl = AsyncMock(return_value={
        "job_id": "fc-123",
        "total": 2,
        "pages": [
            {"url": "https://example.com", "markdown": "# Page 1"},
            {"url": "https://example.com/about", "markdown": "# Page 2"},
        ],
        "success": True,
    })
    return client


@pytest.fixture
def mock_site_unblocker():
    client = AsyncMock()
    client.health = AsyncMock(return_value=False)
    client.scrape = AsyncMock(return_value={
        "url": "https://example.com",
        "markdown": "# Site Unblocker Result",
        "success": True,
    })
    return client


@pytest.fixture
def mock_web_data_api():
    client = AsyncMock()
    client.health = AsyncMock(return_value=False)
    client.enabled = False
    client.scrape = AsyncMock(return_value={
        "url": "https://example.com",
        "markdown": "# Web Data API Result",
        "success": True,
    })
    client.crawl = AsyncMock(return_value={
        "crawl_id": "wda-456",
        "total": 1,
        "pages": [{"url": "https://example.com", "markdown": "# WDA Page"}],
        "success": True,
    })
    client.map_site = AsyncMock(return_value={
        "url": "https://example.com",
        "urls": ["https://example.com", "https://example.com/about"],
        "total": 2,
        "success": True,
    })
    return client
