"""Cross-market portfolio summary: per-market equity converted to base currency, then aggregated.

Read-only. Reuses build_portfolio + the FX seam (same pattern as api/risk.py). A market whose
broker isn't available (no live/imported data -> NotImplementedError) is reported available=false
with its error, never silently dropped.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.brokers.registry import get_broker
from app.marketdata.fx import FxConverter, quote_currency_for
from app.schemas import MarketKind
from app.trading.portfolio import build_portfolio

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


class MarketSummary(BaseModel):
    market: str
    available: bool
    quote_currency: str
    cash_native: float
    positions_value_native: float
    equity_native: float
    cash_base: float
    positions_value_base: float
    equity_base: float
    num_positions: int
    error: str | None = None


class PortfolioSummary(BaseModel):
    base_currency: str
    total_cash_base: float
    total_positions_value_base: float
    total_equity_base: float
    markets: list[MarketSummary]


@router.get("/summary", response_model=PortfolioSummary)
def portfolio_summary() -> PortfolioSummary:
    fx = FxConverter.from_settings()
    markets: list[MarketSummary] = []
    total_cash = total_pos = total_eq = 0.0

    for market in MarketKind:
        quote = quote_currency_for(market)
        try:
            view = build_portfolio(get_broker(market))
        except NotImplementedError as exc:
            markets.append(
                MarketSummary(
                    market=market.value, available=False, quote_currency=quote,
                    cash_native=0.0, positions_value_native=0.0, equity_native=0.0,
                    cash_base=0.0, positions_value_base=0.0, equity_base=0.0,
                    num_positions=0, error=str(exc),
                )
            )
            continue
        cash_base = fx.to_base(view.cash, quote)
        pos_base = fx.to_base(view.positions_value, quote)
        eq_base = fx.to_base(view.equity, quote)
        total_cash += cash_base
        total_pos += pos_base
        total_eq += eq_base
        markets.append(
            MarketSummary(
                market=market.value, available=True, quote_currency=quote,
                cash_native=view.cash, positions_value_native=view.positions_value,
                equity_native=view.equity, cash_base=cash_base,
                positions_value_base=pos_base, equity_base=eq_base,
                num_positions=len(view.positions),
            )
        )

    return PortfolioSummary(
        base_currency=fx.base_currency, total_cash_base=total_cash,
        total_positions_value_base=total_pos, total_equity_base=total_eq, markets=markets,
    )
