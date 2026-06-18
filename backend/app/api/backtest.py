"""Backtest endpoint: fetch history for a symbol, run a strategy, return performance."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.backtest.engine import BacktestResult, run_backtest
from app.backtest.optimize import OptimizeRow, grid_search
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


class CompareRequest(BaseModel):
    symbol: str
    market: MarketKind = MarketKind.crypto
    timeframe: str = "1h"
    limit: int = Field(default=500, ge=10, le=1000)
    strategies: list[str] = Field(default_factory=lambda: list(STRATEGIES))
    starting_cash: float = 100_000.0
    position_fraction: float = 1.0


class CompareRow(BaseModel):
    strategy: str
    total_return_pct: float
    buy_hold_return_pct: float
    num_trades: int
    win_rate: float
    max_drawdown_pct: float
    error: str | None = None


@router.post("/compare", response_model=list[CompareRow])
def compare(req: CompareRequest) -> list[CompareRow]:
    """Run several strategies over the same history and rank them by return (fetch once)."""
    try:
        candles = get_data_broker(req.market).get_ohlcv(req.symbol, req.timeframe, req.limit)
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"{type(exc).__name__}: {exc}")

    rows: list[CompareRow] = []
    for name in req.strategies:
        try:
            result = run_backtest(
                candles,
                build_strategy(name),
                starting_cash=req.starting_cash,
                position_fraction=req.position_fraction,
                market=req.market,
                timeframe=req.timeframe,
            )
            rows.append(
                CompareRow(
                    strategy=name,
                    total_return_pct=result.total_return_pct,
                    buy_hold_return_pct=result.buy_hold_return_pct,
                    num_trades=result.num_trades,
                    win_rate=result.win_rate,
                    max_drawdown_pct=result.max_drawdown_pct,
                )
            )
        except Exception as exc:  # one bad strategy shouldn't sink the whole comparison
            rows.append(
                CompareRow(
                    strategy=name,
                    total_return_pct=0.0,
                    buy_hold_return_pct=0.0,
                    num_trades=0,
                    win_rate=0.0,
                    max_drawdown_pct=0.0,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
    rows.sort(key=lambda r: r.total_return_pct, reverse=True)
    return rows


class OptimizeRequest(BaseModel):
    symbol: str
    market: MarketKind = MarketKind.crypto
    timeframe: str = "1h"
    limit: int = Field(default=500, ge=10, le=1000)
    strategy: str = "ma_cross"
    param_grid: dict[str, list] = Field(default_factory=dict)
    metric: str = "total_return_pct"
    starting_cash: float = 100_000.0
    position_fraction: float = 1.0
    max_combinations: int = Field(default=200, ge=1, le=500)
    # M0.4 — out-of-sample ranking. With split=True the history is divided into an in-sample prefix
    # and an oos_fraction out-of-sample suffix; combos are ranked by the risk-adjusted OOS rank_metric
    # (default OOS Sharpe) and each row exposes the IS↔OOS gap so the frontend can show it.
    split: bool = False
    oos_fraction: float = Field(default=0.3, gt=0.0, lt=1.0)
    rank_metric: str = "oos_sharpe"


@router.post("/optimize", response_model=list[OptimizeRow])
def optimize(req: OptimizeRequest) -> list[OptimizeRow]:
    """Grid-search a strategy's parameters over the symbol's history; ranked best-first.

    With ``split=True`` ranking is by the out-of-sample (OOS) risk-adjusted ``rank_metric`` — never raw
    return — and each row carries IS vs OOS values and their gap. "Apply best" applies ``rows[0]``,
    which is the OOS-selected combo.
    """
    try:
        candles = get_data_broker(req.market).get_ohlcv(req.symbol, req.timeframe, req.limit)
        return grid_search(
            candles,
            req.strategy,
            req.param_grid,
            metric=req.metric,
            starting_cash=req.starting_cash,
            position_fraction=req.position_fraction,
            max_combinations=req.max_combinations,
            market=req.market,
            timeframe=req.timeframe,
            split=req.split,
            oos_fraction=req.oos_fraction,
            rank_metric=req.rank_metric,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"{type(exc).__name__}: {exc}")


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
            market=req.market,
            timeframe=req.timeframe,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"{type(exc).__name__}: {exc}")
