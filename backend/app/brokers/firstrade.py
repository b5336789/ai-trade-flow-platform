"""Firstrade (美股) broker — live integration scaffold.

⚠️ Firstrade has NO official public API. Any live integration relies on community/unofficial,
reverse-engineered libraries whose login/2FA flow is fragile and can break without notice. This
scaffold fails loud rather than pretend to trade. Use CSV import + paper mode for now.
"""

from __future__ import annotations

from app.brokers.base import Broker
from app.schemas import (
    Balance,
    Candle,
    MarketKind,
    OrderRequest,
    OrderResult,
    Position,
    Ticker,
    TradingMode,
)

_NOT_WIRED = (
    "Firstrade live integration is not implemented. Firstrade has no official public API; a live "
    "implementation would use an unofficial library with FIRSTRADE_USERNAME/PASSWORD (fragile, "
    "may break). Use TRADING_MODE=paper with imported CSV data for now."
)


class FirstradeBroker(Broker):
    market = MarketKind.us_stock
    mode = TradingMode.live

    @property
    def name(self) -> str:
        return "firstrade:us_stock"

    def get_ticker(self, symbol: str) -> Ticker:
        raise NotImplementedError(_NOT_WIRED)

    def get_ohlcv(self, symbol: str, timeframe: str = "1d", limit: int = 100) -> list[Candle]:
        raise NotImplementedError(_NOT_WIRED)

    def create_order(self, request: OrderRequest) -> OrderResult:
        raise NotImplementedError(_NOT_WIRED)

    def get_balance(self) -> list[Balance]:
        raise NotImplementedError(_NOT_WIRED)

    def get_positions(self) -> list[Position]:
        raise NotImplementedError(_NOT_WIRED)
