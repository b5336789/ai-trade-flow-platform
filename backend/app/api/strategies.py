"""Strategy library: AI design, CRUD, and per-strategy backtest."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.ai.strategy_agent import design_strategy
from app.backtest.engine import BacktestResult, run_backtest
from app.brokers.registry import get_data_broker
from app.db import get_session
from app.schemas import MarketKind
from app.strategies import library
from app.strategies.spec import SpecStrategy, StrategySpec
from app.strategies.spec_render import render_python

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


class DesignRequest(BaseModel):
    message: str
    prior_spec: StrategySpec | None = None
    model: str | None = None


class SaveRequest(BaseModel):
    name: str
    description: str = ""
    spec: StrategySpec


class StrategyOut(BaseModel):
    id: int
    name: str
    description: str
    source: str
    spec: StrategySpec
    rendered_python: str


class StrategyListItem(BaseModel):
    id: int
    name: str
    description: str
    source: str
    num_params: int


def _to_out(row) -> StrategyOut:
    spec = StrategySpec.model_validate(row.spec_json)
    return StrategyOut(id=row.id, name=row.name, description=row.description,
                       source=row.source, spec=spec, rendered_python=render_python(spec))


@router.post("/design")
def design(req: DesignRequest) -> dict:
    try:
        out = design_strategy(req.message, prior_spec=req.prior_spec, model=req.model)
    except RuntimeError as exc:  # missing key / parse failure
        raise HTTPException(status_code=422, detail=str(exc))
    return {"spec": out["spec"], "rendered_python": out["rendered_python"],
            "explanation": out["explanation"]}


@router.get("", response_model=list[StrategyListItem])
def list_all(session: Session = Depends(get_session)) -> list[StrategyListItem]:
    items = []
    for row in library.list_strategies(session):
        spec = StrategySpec.model_validate(row.spec_json)
        items.append(StrategyListItem(id=row.id, name=row.name, description=row.description,
                                      source=row.source, num_params=len(spec.params)))
    return items


@router.post("", response_model=StrategyOut)
def create(req: SaveRequest, session: Session = Depends(get_session)) -> StrategyOut:
    row = library.save_strategy(session, req.name, req.spec, description=req.description, source="manual")
    return _to_out(row)


@router.get("/{sid}", response_model=StrategyOut)
def get_one(sid: int, session: Session = Depends(get_session)) -> StrategyOut:
    row = library.get_strategy(session, sid)
    if row is None:
        raise HTTPException(status_code=404, detail=f"strategy {sid} not found")
    return _to_out(row)


@router.put("/{sid}", response_model=StrategyOut)
def update(sid: int, req: SaveRequest, session: Session = Depends(get_session)) -> StrategyOut:
    try:
        row = library.update_strategy(session, sid, name=req.name,
                                      description=req.description, spec=req.spec)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _to_out(row)


@router.delete("/{sid}")
def remove(sid: int, session: Session = Depends(get_session)) -> dict:
    if not library.delete_strategy(session, sid):
        raise HTTPException(status_code=404, detail=f"strategy {sid} not found")
    return {"deleted": sid}


class StrategyBacktestRequest(BaseModel):
    symbol: str
    market: MarketKind = MarketKind.crypto
    timeframe: str = "1h"
    limit: int = Field(default=500, ge=10, le=1000)
    param_overrides: dict = Field(default_factory=dict)
    starting_cash: float = 100_000.0
    position_fraction: float = 1.0


@router.post("/{sid}/backtest", response_model=BacktestResult)
def backtest_one(sid: int, req: StrategyBacktestRequest,
                 session: Session = Depends(get_session)) -> BacktestResult:
    try:
        spec = library.load_spec(session, sid)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    try:
        strategy = SpecStrategy(spec, req.param_overrides)
        candles = get_data_broker(req.market).get_ohlcv(req.symbol, req.timeframe, req.limit)
        return run_backtest(candles, strategy, starting_cash=req.starting_cash,
                            position_fraction=req.position_fraction)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"{type(exc).__name__}: {exc}")
