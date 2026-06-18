"""Order execution path shared by the orders API and the workflow engine.

Resolves a fill price, runs the risk guard, places the order via the selected broker, and
persists an OrderRecord. Keeping this in one place avoids divergence between manual and
workflow-driven trading.
"""

from __future__ import annotations

from sqlmodel import Session, select

from app.brokers.registry import get_broker
from app.models import OrderRecord
from app.notifications.service import notify
from app.schemas import MarketKind, OrderRequest, OrderResult, OrderSide, OrderType, TradingMode
from app.trading.risk import RiskGuard

_default_guard = RiskGuard()


def _record_to_result(record: OrderRecord) -> OrderResult:
    """Reconstruct the OrderResult of an already-persisted order (idempotent skip path)."""
    return OrderResult(
        id=record.broker_order_id,
        symbol=record.symbol,
        side=OrderSide(record.side),
        quantity=record.quantity,
        price=record.price,
        status=record.status,
        mode=TradingMode(record.mode),
        broker=record.broker,
        timestamp=record.created_at,
        info={"idempotent_skip": True, "client_order_id": record.client_order_id},
    )


def execute_order(
    request: OrderRequest,
    market: MarketKind = MarketKind.crypto,
    mode: TradingMode | None = None,
    guard: RiskGuard | None = None,
    session: Session | None = None,
    client_order_id: str | None = None,
) -> OrderResult:
    guard = guard or _default_guard
    broker = get_broker(market, mode)

    # Idempotency (M0.5): if this logical decision was already placed (same client_order_id),
    # SKIP rather than place a duplicate. Manual orders pass client_order_id=None -> never skip.
    if client_order_id is not None and session is not None:
        existing = session.exec(
            select(OrderRecord).where(OrderRecord.client_order_id == client_order_id)
        ).first()
        if existing is not None:
            notify(
                session,
                title=f"Order skipped (idempotent): {existing.side} {existing.quantity} {existing.symbol}",
                message=f"client_order_id={client_order_id} already placed as order #{existing.id}",
                level="info",
                meta={"client_order_id": client_order_id, "order_record_id": existing.id},
            )
            return _record_to_result(existing)

    current_price = broker.get_ticker(request.symbol).price
    if request.type == OrderType.limit and request.limit_price:
        fill_price = request.limit_price
    else:
        fill_price = current_price

    held = next(
        (p.quantity for p in broker.get_positions() if p.symbol == request.symbol), 0.0
    )
    guard.check(request, fill_price, current_position_qty=held, current_price=current_price)

    result = broker.create_order(request)

    if session is not None:
        session.add(
            OrderRecord(
                client_order_id=client_order_id,
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
