"""Data-only broker backed by imported CSV history (see market_data.py).

Serves get_ticker/get_ohlcv for any symbol that has been imported for its market. Used as the
data provider behind a PaperBroker so 台股/美股 can be paper-traded and backtested offline.
"""

from __future__ import annotations

from datetime import datetime

from app.brokers import market_data
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


class CsvDataBroker(Broker):
    mode = TradingMode.paper

    def __init__(self, market: MarketKind) -> None:
        self.market = market

    @property
    def name(self) -> str:
        return f"csv:{self.market.value}"

    def _candles(self, symbol: str) -> list[Candle]:
        candles = market_data.get_candles(self.market, symbol)
        if not candles:
            raise RuntimeError(
                f"no imported data for {self.market.value}:{symbol} — "
                "POST /api/markets/import to add CSV history"
            )
        return candles

    def get_ticker(self, symbol: str) -> Ticker:
        last = self._candles(symbol)[-1]
        return Ticker(symbol=symbol, price=last.close, timestamp=last.timestamp)

    def get_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> list[Candle]:
        return self._candles(symbol)[-limit:]

    def get_ohlcv_range(
        self, symbol: str, timeframe: str = "1h", start: datetime | None = None, end: datetime | None = None
    ) -> list[Candle]:
        if start is None or end is None:
            raise ValueError("get_ohlcv_range requires both start and end")
        if start > end:
            raise ValueError(f"start {start.isoformat()} must be before end {end.isoformat()}")
        # parse_csv produces tz-naive datetimes (datetime.fromisoformat on bare dates like "2024-01-01").
        # Normalise start/end to tz-naive UTC so the comparison is consistent.
        _start = start.replace(tzinfo=None) if start.tzinfo is not None else start
        _end = end.replace(tzinfo=None) if end.tzinfo is not None else end
        return [c for c in self._candles(symbol) if _start <= c.timestamp <= _end]

    def create_order(self, request: OrderRequest) -> OrderResult:  # data-only
        raise NotImplementedError("CsvDataBroker is data-only; wrap it in a PaperBroker to trade")

    def get_balance(self) -> list[Balance]:
        return []

    def get_positions(self) -> list[Position]:
        return []
