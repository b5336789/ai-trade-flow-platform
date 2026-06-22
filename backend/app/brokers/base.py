"""The single abstraction that every market/mode plugs into.

Adding a new market (台股 元大, 美股 元大複委託 / Firstrade) or switching paper<->live is done by
implementing this interface + registering in ``registry.py`` — no caller changes elsewhere.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

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


class Broker(ABC):
    market: MarketKind
    mode: TradingMode

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable identifier, e.g. ``ccxt:binance`` or ``paper:ccxt:binance``."""

    # --- market data ---
    @abstractmethod
    def get_ticker(self, symbol: str) -> Ticker: ...

    @abstractmethod
    def get_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> list[Candle]: ...

    def get_ohlcv_range(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> list[Candle]:
        """Fetch candles whose timestamp falls in [start, end]. Subclasses override; default fails loud."""
        raise NotImplementedError(
            f"{type(self).__name__} does not support date-range OHLCV; use get_ohlcv(limit=...)"
        )

    # --- trading ---
    @abstractmethod
    def create_order(self, request: OrderRequest) -> OrderResult: ...

    @abstractmethod
    def get_balance(self) -> list[Balance]: ...

    @abstractmethod
    def get_positions(self) -> list[Position]: ...
