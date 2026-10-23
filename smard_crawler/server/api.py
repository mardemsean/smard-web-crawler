"""HTTP API: /health, /scrape, /batch, /crawl, /map. Bearer auth via SMARD_API_TOKEN."""

from __future__ import annotations

import hmac
import os
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from ..common.budget import BudgetExceeded
from ..common.robots import RobotsDisallowed
from ..common.urlguard import UnsafeURL
from .service import MAX_BATCH, ScrapeService


class ScrapeRequest(BaseModel):
    url: str
    engine: str = "auto"
    save: bool = False
    max_chars: int = Field(200_000, ge=1, le=2_000_000)


class BatchRequest(BaseModel):
    urls: list[str] = Field(..., max_length=MAX_BATCH)
    engine: str = "auto"
    concurrency: int = Field(5, ge=1, le=20)
    save: bool = False
    max_chars: int = Field(20_000, ge=1, le=2_000_000)


class CrawlRequest(BaseModel):
    url: str
    limit: int = Field(20, ge=1, le=500)
    max_depth: int = Field(2, ge=1, le=5)


class MapRequest(BaseModel):
    url: str


def create_app(service: Optional[ScrapeService] = None, token: Optional[str] = None) -> FastAPI:
    svc = service or ScrapeService()
    api_token = token if token is not None else os.getenv("SMARD_API_TOKEN", "")

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        await svc.close()

    app = FastAPI(title="SMard Web Crawler", version="0.2.0", lifespan=lifespan)

    async def auth(authorization: str = Header(default="")) -> None:
        if not api_token:
            return
        scheme, _, value = authorization.partition(" ")
        if scheme.lower() != "bearer" or not hmac.compare_digest(value.encode(), api_token.encode()):
            raise HTTPException(status_code=401, detail="invalid or missing bearer token")

    async def run(coro) -> Any:
        try:
            return await coro
        except (UnsafeURL, ValueError) as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except RobotsDisallowed as e:
            raise HTTPException(status_code=403, detail=str(e)) from e
        except BudgetExceeded as e:
            raise HTTPException(status_code=429, detail=str(e)) from e
        except RuntimeError as e:
            raise HTTPException(status_code=502, detail=str(e)) from e

    @app.get("/health", dependencies=[Depends(auth)])
    async def health() -> dict:
        return await svc.health()

    @app.post("/scrape", dependencies=[Depends(auth)])
    async def scrape(req: ScrapeRequest) -> dict:
        return await run(svc.scrape(req.url, req.engine, req.save, req.max_chars))

    @app.post("/batch", dependencies=[Depends(auth)])
    async def batch(req: BatchRequest) -> list[dict]:
        return await run(svc.batch(req.urls, req.engine, req.concurrency, req.save, req.max_chars))

    @app.post("/crawl", dependencies=[Depends(auth)])
    async def crawl(req: CrawlRequest) -> dict:
        return await run(svc.crawl(req.url, req.limit, req.max_depth))

    @app.post("/map", dependencies=[Depends(auth)])
    async def map_site(req: MapRequest) -> dict:
        return await run(svc.map_site(req.url))

    return app


def serve(host: str = "127.0.0.1", port: int = 8787) -> None:
    import uvicorn

    if host not in ("127.0.0.1", "localhost", "::1") and len(os.getenv("SMARD_API_TOKEN", "")) < 32:
        raise SystemExit("Refusing non-loopback bind without SMARD_API_TOKEN (>= 32 chars). Generate: openssl rand -hex 32")
    uvicorn.run(create_app(), host=host, port=port)
