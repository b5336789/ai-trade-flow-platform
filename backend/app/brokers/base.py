"""The single abstraction that every market/mode plugs into.

Adding a new market (台股 元大, 美股 元大複委託 / Firstrade) or switching paper<->live is done by
implementing this interface + registering in ``registry.py`` — no caller changes elsewhere.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

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

    # --- trading ---
    @abstractmethod
    def create_order(self, request: OrderRequest) -> OrderResult: ...

    @abstractmethod
    def get_balance(self) -> list[Balance]: ...

    @abstractmethod
    def get_positions(self) -> list[Position]: ...
