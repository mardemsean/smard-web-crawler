"""robots.txt compliance with per-host caching (RFC 9309 semantics)."""

from __future__ import annotations

import logging
import time
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

logger = logging.getLogger(__name__)

CACHE_TTL = 3600


class RobotsDisallowed(Exception):
    pass


class RobotsChecker:
    def __init__(self, user_agent: str = "SMardCrawler", timeout: float = 10.0, ttl: float = CACHE_TTL):
        self.user_agent = user_agent
        self.timeout = timeout
        self.ttl = ttl
        self._cache: dict[str, tuple[RobotFileParser, float]] = {}

    async def _fetch(self, origin: str) -> RobotFileParser:
        parser = RobotFileParser()
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                resp = await client.get(f"{origin}/robots.txt", headers={"User-Agent": self.user_agent})
        except httpx.HTTPError as e:
            # RFC 9309 2.3.1.4: unreachable robots.txt means assume complete disallow.
            logger.warning(f"[robots] {origin}: unreachable ({e}); treating as disallow")
            parser.disallow_all = True
            return parser
        if resp.status_code >= 500:
            parser.disallow_all = True
        elif resp.status_code >= 400:
            parser.allow_all = True
        else:
            parser.parse(resp.text.splitlines())
        return parser

    async def allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https"):
            return True
        origin = f"{parts.scheme}://{parts.netloc}"
        cached = self._cache.get(origin)
        if cached is None or time.monotonic() - cached[1] > self.ttl:
            cached = (await self._fetch(origin), time.monotonic())
            self._cache[origin] = cached
        return cached[0].can_fetch(self.user_agent, url)
