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
    ) -> None:
        if fill_price <= 0:
            raise RiskError(f"non-positive fill price {fill_price}")
        order_value = fill_price * request.quantity
        if order_value > self.max_order_value:
            raise RiskError(
                f"order value {order_value:.2f} exceeds max_order_value {self.max_order_value:.2f}"
            )
        if request.side == OrderSide.buy:
            projected_value = (current_position_qty + request.quantity) * fill_price
            if projected_value > self.max_position_value:
                raise RiskError(
                    f"projected position value {projected_value:.2f} exceeds "
                    f"max_position_value {self.max_position_value:.2f}"
                )
