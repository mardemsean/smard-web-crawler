"""Rate limiting and daily request budget for paid engines."""

from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import date
from pathlib import Path


class BudgetExceeded(Exception):
    pass


class RateLimiter:
    """Spaces calls at least 1/max_rps seconds apart (max_rps <= 0 disables)."""

    def __init__(self, max_rps: float):
        self.interval = 1.0 / max_rps if max_rps > 0 else 0.0
        self._next = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        if not self.interval:
            return
        async with self._lock:
            now = time.monotonic()
            wait = self._next - now
            if wait > 0:
                await asyncio.sleep(wait)
                now = time.monotonic()
            self._next = now + self.interval


class DailyBudget:
    """Counts paid requests per local calendar day in a JSON file (limit <= 0 disables)."""

    def __init__(self, limit: int, state_file: Path):
        self.limit = limit
        self.state_file = Path(state_file)
        self._lock = asyncio.Lock()

    def _load(self) -> dict:
        try:
            state = json.loads(self.state_file.read_text())
        except (OSError, ValueError):
            state = {}
        today = date.today().isoformat()
        if state.get("date") != today:
            state = {"date": today, "count": 0}
        return state

    def _store(self, state: dict) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(state))
        os.replace(tmp, self.state_file)

    def used(self) -> int:
        return self._load()["count"]

    async def check(self, n: int = 1) -> int:
        """Raise if spending n more would exceed the cap, without incrementing."""
        async with self._lock:
            count = self._load()["count"]
            if self.limit > 0 and count + n > self.limit:
                raise BudgetExceeded(f"daily paid-request budget exhausted ({count}/{self.limit})")
            return count

    async def consume(self, n: int = 1) -> int:
        async with self._lock:
            state = self._load()
            if self.limit > 0 and state["count"] + n > self.limit:
                raise BudgetExceeded(f"daily paid-request budget exhausted ({state['count']}/{self.limit})")
            state["count"] += n
            self._store(state)
            return state["count"]


class PaidGuard:
    def __init__(self, max_rps: float, daily_limit: int, state_file: Path):
        self.limiter = RateLimiter(max_rps)
        self.budget = DailyBudget(daily_limit, state_file)

    async def before(self) -> None:
        """Gate a paid request: refuse if the daily cap is already reached, then rate-limit.
        Does not count the request — only a response does, via charge()."""
        await self.budget.check()
        await self.limiter.acquire()

    async def charge(self) -> int:
        """Count one paid request that actually reached the engine and returned."""
        return await self.budget.consume()

    async def acquire(self) -> None:
        """Count-then-limit in one step. Kept for callers that charge up front."""
        await self.budget.consume()
        await self.limiter.acquire()
