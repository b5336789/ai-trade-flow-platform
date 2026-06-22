"""Backtest endpoint: fetch history for a symbol, run a strategy, return performance."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.backtest.engine import BacktestResult, run_backtest
from app.backtest.optimize import OptimizeRow, grid_search
from app.backtest.validation import WalkForwardReport, walk_forward
from app.backtest.workflow_backtest import WorkflowBacktestResult, run_workflow_backtest
from app.brokers.registry import get_data_broker
from app.db import get_session
from app.models import Workflow
from app.schemas import MarketKind
from app.strategies.registry import STRATEGIES, build_strategy
from app.workflow.run_store import persist_workflow_run, resolve_order_symbol
from app.workflow.schema import NodeType, WorkflowGraph

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


def _fetch_candles(broker, symbol, timeframe, limit, start, end):
    """Range fetch when both start+end are given (C2), else the legacy limit path. Fails loud."""
    if start is not None and end is not None:
        if start >= end:
            raise ValueError("start must be before end")
        return broker.get_ohlcv_range(symbol, timeframe, start, end)
    return broker.get_ohlcv(symbol, timeframe, limit)


class WorkflowBacktestRequest(BaseModel):
    graph: WorkflowGraph | None = None
    workflow_id: int | None = None
    market: MarketKind = MarketKind.crypto
    timeframe: str = "1h"
    limit: int = Field(default=500, ge=10, le=1000)
    starting_cash: float = 100_000.0


class WorkflowBacktestResponse(WorkflowBacktestResult):
    run_id: int


@router.post("/workflow", response_model=WorkflowBacktestResponse)
def workflow_backtest(req: WorkflowBacktestRequest, session: Session = Depends(get_session)) -> WorkflowBacktestResponse:
    if req.graph is None and req.workflow_id is None:
        raise HTTPException(status_code=422, detail="provide either 'graph' or 'workflow_id'")
    graph = req.graph
    if graph is None:
        wf = session.get(Workflow, req.workflow_id)
        if wf is None:
            raise HTTPException(status_code=404, detail="workflow not found")
        graph = WorkflowGraph.model_validate(wf.graph)
    try:
        order_nodes = [n for n in graph.nodes if n.type == NodeType.order]
        if not order_nodes:
            raise ValueError("workflow backtest requires at least one order node")
        symbols = sorted({resolve_order_symbol(graph, n.id) for n in order_nodes})
        broker = get_data_broker(req.market)
        histories = {s: broker.get_ohlcv(s, req.timeframe, req.limit) for s in symbols}
        result = run_workflow_backtest(
            graph,
            histories,
            starting_cash=req.starting_cash,
            market=req.market,
            timeframe=req.timeframe,
        )
        run_db_id = persist_workflow_run(
            session,
            run_id=f"bt-{req.workflow_id or 'adhoc'}",
            kind="backtest",
            graph=graph,
            market=req.market.value,
            symbols=result.symbols,
            timeframe=req.timeframe,
            starting_cash=req.starting_cash,
            params={"limit": req.limit},
            metrics=result.model_dump(mode="json", exclude={"signals", "equity_curve", "trades"}),
            equity_curve=[p.model_dump(mode="json") for p in result.equity_curve],
            trades=[t.model_dump(mode="json") for t in result.trades],
            status="ok",
            signals=result.signals,
        )
        return WorkflowBacktestResponse(**result.model_dump(), run_id=run_db_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"{type(exc).__name__}: {exc}")


class BacktestRequest(BaseModel):
    symbol: str
    market: MarketKind = MarketKind.crypto
    timeframe: str = "1h"
    limit: int = Field(default=500, ge=10, le=1000)
    strategy: str = "ma_cross"
    params: dict = Field(default_factory=dict)
    starting_cash: float = 100_000.0
    position_fraction: float = 1.0
    start: datetime | None = None  # C2: when start+end both set, fetch by range instead of limit
    end: datetime | None = None


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
    start: datetime | None = None
    end: datetime | None = None


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
        candles = _fetch_candles(
            get_data_broker(req.market), req.symbol, req.timeframe, req.limit, req.start, req.end
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
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
    start: datetime | None = None
    end: datetime | None = None


@router.post("/optimize", response_model=list[OptimizeRow])
def optimize(req: OptimizeRequest) -> list[OptimizeRow]:
    """Grid-search a strategy's parameters over the symbol's history; ranked best-first.

    With ``split=True`` ranking is by the out-of-sample (OOS) risk-adjusted ``rank_metric`` — never raw
    return — and each row carries IS vs OOS values and their gap. "Apply best" applies ``rows[0]``,
    which is the OOS-selected combo.
    """
    try:
        candles = _fetch_candles(
            get_data_broker(req.market), req.symbol, req.timeframe, req.limit, req.start, req.end
        )
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


class WalkForwardRequest(BaseModel):
    symbol: str
    market: MarketKind = MarketKind.crypto
    timeframe: str = "1h"
    limit: int = Field(default=500, ge=10, le=1000)
    strategy: str = "ma_cross"
    param_grid: dict[str, list] = Field(default_factory=dict)
    n_folds: int = Field(default=4, ge=2, le=20)
    metric: str = "sharpe"
    anchored: bool = True
    max_combinations: int = Field(default=200, ge=1, le=500)
    start: datetime | None = None
    end: datetime | None = None


@router.post("/walk-forward", response_model=WalkForwardReport)
def walk_forward_endpoint(req: WalkForwardRequest) -> WalkForwardReport:
    """Walk-forward (anchored/rolling) out-of-sample validation of a strategy's parameters.

    Picks best params per fold on the in-sample window by a risk-adjusted ``metric`` and scores
    them on the following out-of-sample window; ranking by raw return is deliberately unavailable
    (the overfitting trap). Fails loud on bad inputs.
    """
    try:
        candles = _fetch_candles(
            get_data_broker(req.market), req.symbol, req.timeframe, req.limit, req.start, req.end
        )
        return walk_forward(
            candles,
            req.strategy,
            req.param_grid,
            n_folds=req.n_folds,
            metric=req.metric,
            anchored=req.anchored,
            max_combinations=req.max_combinations,
            starting_cash=100_000.0,
            position_fraction=1.0,
            market=req.market,
            timeframe=req.timeframe,
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
        candles = _fetch_candles(
            get_data_broker(req.market), req.symbol, req.timeframe, req.limit, req.start, req.end
        )
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
