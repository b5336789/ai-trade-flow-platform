"""Realized-P&L reporting and tax CSV export (M1.3).

Reads the :class:`~app.models.RealizedPnL` ledger written by ``execute_order``. Small and
fail-loud: invalid date filters raise; an empty period returns an empty report (not an error).
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.marketdata.fx import FxConverter, quote_currency_for
from app.models import RealizedPnL
from app.schemas import MarketKind

router = APIRouter(prefix="/api/ledger", tags=["ledger"])


class RealizedPnLReport(BaseModel):
    """Aggregated realized P&L over the filtered period, plus the underlying disposals."""

    count: int
    total_proceeds: float
    total_cost_basis: float
    total_fee: float
    total_tax: float
    total_gross_pnl: float
    total_realized_net: float
    base_currency: str
    total_realized_net_base: float
    total_gross_pnl_base: float
    disposals: list[RealizedPnL]


def _parse_day(value: str | None, *, end: bool) -> datetime | None:
    """Parse a YYYY-MM-DD (or full ISO) bound into a tz-aware UTC datetime. Fail loud on garbage."""
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"invalid date {value!r}: {exc}")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _query(
    session: Session,
    market: MarketKind | None,
    symbol: str | None,
    start: str | None,
    end: str | None,
) -> list[RealizedPnL]:
    stmt = select(RealizedPnL)
    if market is not None:
        stmt = stmt.where(RealizedPnL.market == market.value)
    if symbol is not None:
        stmt = stmt.where(RealizedPnL.symbol == symbol)
    start_dt = _parse_day(start, end=False)
    end_dt = _parse_day(end, end=True)
    if start_dt is not None:
        stmt = stmt.where(RealizedPnL.closed_at >= start_dt)
    if end_dt is not None:
        stmt = stmt.where(RealizedPnL.closed_at <= end_dt)
    return list(session.exec(stmt.order_by(RealizedPnL.closed_at, RealizedPnL.id)).all())


@router.get("/realized", response_model=RealizedPnLReport)
def realized_report(
    market: MarketKind | None = None,
    symbol: str | None = None,
    start: str | None = Query(None, description="inclusive ISO date/datetime lower bound"),
    end: str | None = Query(None, description="inclusive ISO date/datetime upper bound"),
    session: Session = Depends(get_session),
) -> RealizedPnLReport:
    rows = _query(session, market, symbol, start, end)

    fx = FxConverter.from_settings()

    def _to_base(attr: str) -> float:
        return sum(fx.to_base(getattr(r, attr), quote_currency_for(MarketKind(r.market))) for r in rows)

    return RealizedPnLReport(
        count=len(rows),
        total_proceeds=sum(r.proceeds for r in rows),
        total_cost_basis=sum(r.cost_basis for r in rows),
        total_fee=sum(r.fee for r in rows),
        total_tax=sum(r.tax for r in rows),
        total_gross_pnl=sum(r.gross_pnl for r in rows),
        total_realized_net=sum(r.realized_net for r in rows),
        base_currency=fx.base_currency,
        total_realized_net_base=_to_base("realized_net"),
        total_gross_pnl_base=_to_base("gross_pnl"),
        disposals=rows,
    )


@router.get("/realized.csv")
def realized_csv(
    market: MarketKind | None = None,
    symbol: str | None = None,
    start: str | None = Query(None, description="inclusive ISO date/datetime lower bound"),
    end: str | None = Query(None, description="inclusive ISO date/datetime upper bound"),
    session: Session = Depends(get_session),
) -> StreamingResponse:
    """CSV export of realized disposals for tax filing."""
    rows = _query(session, market, symbol, start, end)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "closed_at",
            "market",
            "symbol",
            "quantity",
            "proceeds",
            "cost_basis",
            "fee",
            "tax",
            "gross_pnl",
            "realized_net",
        ]
    )
    for r in rows:
        writer.writerow(
            [
                r.closed_at.isoformat(),
                r.market,
                r.symbol,
                r.quantity,
                r.proceeds,
                r.cost_basis,
                r.fee,
                r.tax,
                r.gross_pnl,
                r.realized_net,
            ]
        )
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=realized_pnl.csv"},
    )
