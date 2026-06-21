# app/workflow/backtest_context.py
"""Per-bar context that makes data_source/order/risk_exit nodes replay over history."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas import Candle, Signal


@dataclass
class SimPos:
    quantity: float = 0.0
    avg_price: float = 0.0


@dataclass
class BacktestContext:
    histories: dict[str, list[Candle]]
    positions: dict[str, "SimPos"]
    current_index: int = 0
    orders_this_bar: list[tuple[str, str, Signal]] = field(default_factory=list)
    _order_symbols: dict[str, str] = field(default_factory=dict)

    @property
    def current_ts(self) -> str:
        any_hist = next(iter(self.histories.values()))
        return any_hist[self.current_index].timestamp.isoformat()

    def window_for(self, symbol: str) -> list[Candle]:
        hist = self.histories.get(symbol)
        if hist is None:
            raise ValueError(f"no backtest history loaded for symbol {symbol!r}")
        return hist[: self.current_index + 1]

    def position_for(self, symbol: str) -> SimPos:
        return self.positions.get(symbol, SimPos())

    def set_order_symbol(self, order_node_id: str, symbol: str) -> None:
        self._order_symbols[order_node_id] = symbol

    def order_symbol(self, order_node_id: str, fallback: str | None) -> str:
        sym = self._order_symbols.get(order_node_id) or fallback
        if not sym:
            raise ValueError(f"order node '{order_node_id}' has no resolved symbol for backtest")
        return sym

    def record(self, order_node_id: str, symbol: str, signal: Signal) -> None:
        self.orders_this_bar.append((order_node_id, symbol, signal))
