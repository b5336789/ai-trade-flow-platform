"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ai, backtest, markets, notifications, orders, schedules, workflows
from app.api.deps import require_api_token
from app.config import settings
from app.db import init_db
from app.schemas import MarketKind
from app.scheduler.service import shutdown_scheduler, start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="ai-trade-flow-platform", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# M0.7: bearer-token auth is applied GLOBALLY to every /api router here, so individual router
# files need no changes. ``GET /health`` (below) is intentionally left public.
_auth = [Depends(require_api_token)]
app.include_router(markets.router, dependencies=_auth)
app.include_router(orders.router, dependencies=_auth)
app.include_router(ai.router, dependencies=_auth)
app.include_router(workflows.router, dependencies=_auth)
app.include_router(backtest.router, dependencies=_auth)
app.include_router(schedules.router, dependencies=_auth)
app.include_router(notifications.router, dependencies=_auth)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/config", tags=["meta"], dependencies=[Depends(require_api_token)])
def config() -> dict:
    return {
        "trading_mode": settings.trading_mode.value,
        "markets": [m.value for m in MarketKind],
        "implemented_markets": ["crypto"],
        "ai_model": settings.ai_model,
    }
