"""In-process paper-trading broker.

Pulls real prices from a wrapped data-provider broker (e.g. ``CcxtBroker``) and simulates fills,
tracking cash + positions in memory. This is the default, safe execution path. Persistence and
richer risk handling are layered on in later checkpoints (trading/portfolio.py, trading/risk.py).
"""

from __future__ import annotations

import itertools
from datetime import datetime, timezone

from app.brokers.base import Broker
from app.config import settings
from app.trading.costs import CostModel
from app.schemas import (
    Balance,
    Candle,
    OrderRequest,
    OrderResult,
    OrderSide,
    OrderType,
    Position,
    Ticker,
    TradingMode,
)


class PaperBroker(Broker):
    mode = TradingMode.paper

    def __init__(
        self,
        data_provider: Broker,
        starting_cash: float | None = None,
        quote_asset: str | None = None,
        store=None,
        cost_model: CostModel | None = None,
    ) -> None:
        self._data = data_provider
        self.market = data_provider.market
        self._cash = starting_cash if starting_cash is not None else settings.paper_starting_cash
        self._quote = quote_asset or settings.paper_quote_asset
        self._cost = cost_model or CostModel.from_settings()
        self._positions: dict[str, Position] = {}
        self._ids = itertools.count(1)
        self._store = store
        if store is not None:
            cash, positions = store.load()
            if cash is not None:  # hydrate from persisted state
                self._cash = cash
                self._positions = positions
            else:  # first run: persist the opening balance
                store.save(self._cash, self._quote, self._positions)

    def _persist(self) -> None:
        if self._store is not None:
            self._store.save(self._cash, self._quote, self._positions)

    @property
    def name(self) -> str:
        return f"paper:{self._data.name}"

    @property
    def cash(self) -> float:
        return self._cash

    # --- market data delegates to the real provider ---
    def get_ticker(self, symbol: str) -> Ticker:
        return self._data.get_ticker(symbol)

    def get_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> list[Candle]:
        return self._data.get_ohlcv(symbol, timeframe, limit)

    # --- simulated execution ---
    def create_order(self, request: OrderRequest) -> OrderResult:
        if request.type == OrderType.limit and request.limit_price:
            base_price = request.limit_price
        else:
            base_price = self._data.get_ticker(request.symbol).price

        # Slippage moves the fill price against us; fees/tax are deducted from cash (M0.1).
        fill_price = self._cost.slippage_price(request.side, base_price)
        fill_cost = self._cost.fill_cost(self.market, request.side, fill_price, request.quantity)

        if request.side == OrderSide.buy:
            need = fill_price * request.quantity + fill_cost.total
            if need > self._cash + 1e-9:
                raise RuntimeError(
                    f"Insufficient paper cash: need {need:.2f} {self._quote} "
                    f"(incl. fees {fill_cost.total:.2f}), have {self._cash:.2f}"
                )
            self._cash -= need
            self._apply_position(request.symbol, request.quantity, fill_price)
        else:  # sell
            pos = self._positions.get(request.symbol)
            held = pos.quantity if pos else 0.0
            if request.quantity > held + 1e-9:
                raise RuntimeError(
                    f"Insufficient position to sell {request.symbol}: "
                    f"have {held}, requested {request.quantity}"
                )
            self._cash += fill_price * request.quantity - fill_cost.total
            self._apply_position(request.symbol, -request.quantity, fill_price)

        self._persist()
        return OrderResult(
            id=f"paper-{next(self._ids)}",
            symbol=request.symbol,
            side=request.side,
            quantity=request.quantity,
            price=fill_price,
            status="filled",
            mode=TradingMode.paper,
            broker=self.name,
            timestamp=datetime.now(timezone.utc),
            info={"fee": fill_cost.fee, "tax": fill_cost.tax},
        )

    def _apply_position(self, symbol: str, delta_qty: float, price: float) -> None:
        pos = self._positions.get(symbol)
        if pos is None:
            if delta_qty <= 0:
                return
            self._positions[symbol] = Position(symbol=symbol, quantity=delta_qty, avg_price=price)
            return
        new_qty = pos.quantity + delta_qty
        if new_qty <= 1e-9:
            self._positions.pop(symbol, None)
        elif delta_qty > 0:
            # weighted-average cost basis on buys
            total_cost = pos.avg_price * pos.quantity + price * delta_qty
            pos.quantity = new_qty
            pos.avg_price = total_cost / new_qty
        else:
            # sells reduce quantity, cost basis unchanged
            pos.quantity = new_qty

    def get_balance(self) -> list[Balance]:
        return [Balance(asset=self._quote, free=self._cash, total=self._cash)]

    def get_positions(self) -> list[Position]:
        return list(self._positions.values())
