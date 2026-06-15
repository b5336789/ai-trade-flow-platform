"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ai, backtest, markets, orders, workflows
from app.db import init_db
from app.schemas import MarketKind


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="ai-trade-flow-platform", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(markets.router)
app.include_router(orders.router)
app.include_router(ai.router)
app.include_router(workflows.router)
app.include_router(backtest.router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/config", tags=["meta"])
def config() -> dict:
    from app.config import settings

    return {
        "trading_mode": settings.trading_mode.value,
        "markets": [m.value for m in MarketKind],
        "implemented_markets": ["crypto"],
        "ai_model": settings.ai_model,
    }
