"""Backtest endpoint: fetch history for a symbol, run a strategy, return performance."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.backtest.engine import BacktestResult, run_backtest
from app.brokers.registry import get_data_broker
from app.schemas import MarketKind
from app.strategies.registry import STRATEGIES, build_strategy

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


class BacktestRequest(BaseModel):
    symbol: str
    market: MarketKind = MarketKind.crypto
    timeframe: str = "1h"
    limit: int = Field(default=500, ge=10, le=1000)
    strategy: str = "ma_cross"
    params: dict = Field(default_factory=dict)
    starting_cash: float = 100_000.0
    position_fraction: float = 1.0


@router.get("/strategies")
def list_strategies() -> dict[str, list[str]]:
    return {"strategies": list(STRATEGIES)}


@router.post("", response_model=BacktestResult)
def backtest(req: BacktestRequest) -> BacktestResult:
    try:
        strategy = build_strategy(req.strategy, req.params)
        candles = get_data_broker(req.market).get_ohlcv(req.symbol, req.timeframe, req.limit)
        return run_backtest(
            candles,
            strategy,
            starting_cash=req.starting_cash,
            position_fraction=req.position_fraction,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"{type(exc).__name__}: {exc}")
