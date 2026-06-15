"""Order execution path shared by the orders API and the workflow engine.

Resolves a fill price, runs the risk guard, places the order via the selected broker, and
persists an OrderRecord. Keeping this in one place avoids divergence between manual and
workflow-driven trading.
"""

from __future__ import annotations

from sqlmodel import Session

from app.brokers.registry import get_broker
from app.models import OrderRecord
from app.notifications.service import notify
from app.schemas import MarketKind, OrderRequest, OrderResult, OrderType, TradingMode
from app.trading.risk import RiskGuard

_default_guard = RiskGuard()


def execute_order(
    request: OrderRequest,
    market: MarketKind = MarketKind.crypto,
    mode: TradingMode | None = None,
    guard: RiskGuard | None = None,
    session: Session | None = None,
) -> OrderResult:
    guard = guard or _default_guard
    broker = get_broker(market, mode)

    if request.type == OrderType.limit and request.limit_price:
        fill_price = request.limit_price
    else:
        fill_price = broker.get_ticker(request.symbol).price

    held = next(
        (p.quantity for p in broker.get_positions() if p.symbol == request.symbol), 0.0
    )
    guard.check(request, fill_price, current_position_qty=held)

    result = broker.create_order(request)

    if session is not None:
        session.add(
            OrderRecord(
                broker_order_id=result.id,
                symbol=result.symbol,
                side=result.side.value,
                quantity=result.quantity,
                price=result.price,
                status=result.status,
                mode=result.mode.value,
                broker=result.broker,
                market=market.value,
            )
        )
        session.commit()
        notify(
            session,
            title=f"Order {result.status}: {result.side.value} {result.quantity} {result.symbol}",
            message=f"{result.mode.value} @ {result.price} via {result.broker}",
            level="success",
            meta=result.model_dump(mode="json"),
        )

    return result
