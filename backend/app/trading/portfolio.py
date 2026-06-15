"""Portfolio valuation: positions enriched with current price + unrealized P&L, plus equity."""

from __future__ import annotations

from pydantic import BaseModel

from app.brokers.base import Broker


class PositionView(BaseModel):
    symbol: str
    quantity: float
    avg_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    price_source: str  # "live" or "avg_fallback" when a live price was unavailable


class PortfolioView(BaseModel):
    cash: float
    positions: list[PositionView]
    positions_value: float
    equity: float


def build_portfolio(broker: Broker) -> PortfolioView:
    balances = broker.get_balance()
    cash = sum(b.free for b in balances)

    positions: list[PositionView] = []
    positions_value = 0.0
    for pos in broker.get_positions():
        try:
            price = broker.get_ticker(pos.symbol).price
            source = "live"
        except Exception:
            # Price feed unavailable — fall back to cost basis but flag it (don't hide it).
            price = pos.avg_price
            source = "avg_fallback"
        market_value = price * pos.quantity
        positions_value += market_value
        positions.append(
            PositionView(
                symbol=pos.symbol,
                quantity=pos.quantity,
                avg_price=pos.avg_price,
                current_price=price,
                market_value=market_value,
                unrealized_pnl=(price - pos.avg_price) * pos.quantity,
                price_source=source,
            )
        )

    return PortfolioView(
        cash=cash,
        positions=positions,
        positions_value=positions_value,
        equity=cash + positions_value,
    )
