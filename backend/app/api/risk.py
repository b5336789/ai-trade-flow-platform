"""Risk status & kill-switch endpoints (M0.6).

Exposes the portfolio-level risk state and lets an operator engage/disengage the kill switch and
manually clear the ``halted`` flag (resume after a daily-loss breach). All values are reported in
the configured base currency (TWD).
"""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session

from app.brokers.registry import get_broker
from app.config import settings
from app.db import get_session
from app.marketdata.fx import FxConverter, quote_currency_for
from app.notifications.service import notify
from app.schemas import MarketKind
from app.trading import runtime_state
from app.trading.portfolio import build_portfolio

router = APIRouter(prefix="/api/risk", tags=["risk"])


class RiskStatus(BaseModel):
    kill_switch: bool  # effective: config flag OR persisted runtime flag
    kill_switch_config: bool
    kill_switch_runtime: bool
    halted: bool
    base_currency: str
    max_total_exposure_value: float
    max_daily_loss: float
    max_orders_per_day: int
    orders_today: int
    exposure_base: float
    equity_base: float
    day_start_equity_base: float


class KillSwitchRequest(BaseModel):
    engaged: bool


@router.get("/status", response_model=RiskStatus)
def risk_status(
    market: MarketKind = MarketKind.crypto, session: Session = Depends(get_session)
) -> RiskStatus:
    try:
        view = build_portfolio(get_broker(market))
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    fx = FxConverter.from_settings()
    quote_ccy = quote_currency_for(market)
    equity_base = fx.to_base(view.equity, quote_ccy)
    exposure_base = fx.to_base(view.positions_value, quote_ccy)
    runtime_kill = runtime_state.get_kill_switch(session)
    return RiskStatus(
        kill_switch=settings.kill_switch or runtime_kill,
        kill_switch_config=settings.kill_switch,
        kill_switch_runtime=runtime_kill,
        halted=runtime_state.get_halted(session),
        base_currency=fx.base_currency,
        max_total_exposure_value=settings.max_total_exposure_value,
        max_daily_loss=settings.max_daily_loss,
        max_orders_per_day=settings.max_orders_per_day,
        orders_today=runtime_state.count_orders_today(session),
        exposure_base=exposure_base,
        equity_base=equity_base,
        day_start_equity_base=runtime_state.get_or_snapshot_day_start_equity(session, equity_base),
    )


@router.post("/kill-switch")
def set_kill_switch(
    payload: KillSwitchRequest | None = Body(default=None),
    engaged: bool | None = Query(default=None),
    session: Session = Depends(get_session),
) -> dict[str, bool]:
    """Engage/disengage the persisted runtime kill switch.

    Accepts the documented JSON body (``{"engaged": true}``) and keeps the old query-param
    shape for operator scripts that already use ``?engaged=true``.
    """
    if payload is None and engaged is None:
        raise HTTPException(status_code=422, detail="engaged is required")
    next_state = payload.engaged if payload is not None else bool(engaged)
    title = "Kill switch engaged" if next_state else "Kill switch released"
    runtime_state.set_kill_switch(session, next_state)
    notify(
        session,
        title=title,
        message=(
            "New entries are blocked; exits remain allowed."
            if next_state
            else "New entries may pass configured risk gates again."
        ),
        level="warning" if next_state else "info",
        meta={"gate": "kill_switch", "engaged": next_state},
    )
    return {"kill_switch": next_state}


@router.post("/resume")
def resume(session: Session = Depends(get_session)) -> dict[str, bool]:
    """Manually clear the ``halted`` flag to resume entries after a daily-loss breach."""
    runtime_state.set_halted(session, False)
    notify(
        session,
        title="Trading resumed after halt",
        message="The halted flag was cleared; new entries may pass configured risk gates again.",
        level="info",
        meta={"gate": "halted", "halted": False},
    )
    return {"halted": False}
