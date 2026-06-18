"""Pre-trade risk guards. Every order passes through here before reaching a broker."""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas import OrderRequest, OrderSide


class RiskError(Exception):
    """Raised when an order violates a risk limit (CLAUDE.md: fail loud)."""


@dataclass
class RiskGuard:
    max_order_value: float = 50_000.0
    max_position_value: float = 100_000.0

    def check(
        self,
        request: OrderRequest,
        fill_price: float,
        current_position_qty: float = 0.0,
        current_price: float | None = None,
    ) -> None:
        if fill_price <= 0:
            raise RiskError(f"non-positive fill price {fill_price}")
        order_value = fill_price * request.quantity
        if order_value > self.max_order_value:
            raise RiskError(
                f"order value {order_value:.2f} exceeds max_order_value {self.max_order_value:.2f}"
            )
        if request.side == OrderSide.buy:
            # Judge the position cap by CURRENT MARKET VALUE (M0.5): the existing holding is marked
            # at the live price (spot avg_price is often unknown / synthesised as 0), and the new
            # slice at its fill price. Falls back to fill_price when no separate mark is supplied.
            mark_price = current_price if current_price is not None else fill_price
            projected_value = current_position_qty * mark_price + request.quantity * fill_price
            if projected_value > self.max_position_value:
                raise RiskError(
                    f"projected position value {projected_value:.2f} exceeds "
                    f"max_position_value {self.max_position_value:.2f}"
                )
