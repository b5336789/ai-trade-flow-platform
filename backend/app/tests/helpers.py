"""Test helpers — synthetic candles so tests need no network/exchange."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

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


class StubBroker(Broker):
    """A deterministic data provider for tests — fixed prices, no network."""

    market = MarketKind.crypto
    mode = TradingMode.live

    def __init__(self, prices: dict[str, float], candles: list[Candle] | None = None) -> None:
        self._prices = prices
        self._candles = candles  # if set, get_ohlcv returns these verbatim

    @property
    def name(self) -> str:
        return "stub"

    def get_ticker(self, symbol: str) -> Ticker:
        if symbol not in self._prices:
            raise RuntimeError(f"no stub price for {symbol}")
        return Ticker(symbol=symbol, price=self._prices[symbol], timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc))

    def get_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> list[Candle]:
        if self._candles is not None:
            return self._candles
        return make_candles([self._prices[symbol]] * limit)

    def create_order(self, request: OrderRequest) -> OrderResult:  # pragma: no cover - unused
        raise NotImplementedError

    def get_balance(self) -> list[Balance]:
        return []

    def get_positions(self) -> list[Position]:
        return []

    def set_price(self, symbol: str, price: float) -> None:
        self._prices[symbol] = price


def make_candles(closes: list[float]) -> list[Candle]:
    """Build candles from a list of close prices (OHLC flattened to close, volume=1)."""
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    candles: list[Candle] = []
    for i, close in enumerate(closes):
        candles.append(
            Candle(
                timestamp=base + timedelta(hours=i),
                open=close,
                high=close,
                low=close,
                close=close,
                volume=1.0,
            )
        )
    return candles
