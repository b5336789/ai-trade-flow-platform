"""元大證券 (Yuanta) broker — live integration scaffold.

Implements the Broker interface for 台股 (and US 複委託) but every live method fails loud:
real trading requires Yuanta API credentials and their official trading SDK, which are not
wired up here. This documents the integration contract so the implementation slots in cleanly.

To paper-trade or backtest 台股 today, import CSV history (POST /api/markets/import) and use
TRADING_MODE=paper — the PaperBroker + CsvDataBroker path works fully offline.
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
    "元大證券 live integration is not implemented. Requires YUANTA_API_KEY/YUANTA_API_SECRET and "
    "Yuanta's official trading SDK. Use TRADING_MODE=paper with imported CSV data for now."
)


class YuantaBroker(Broker):
    """台股 元大證券 (and 美股 元大複委託 — pass market=us_stock)."""

    mode = TradingMode.live

    def __init__(self, market: MarketKind = MarketKind.tw_stock) -> None:
        self.market = market

    @property
    def name(self) -> str:
        return f"yuanta:{self.market.value}"

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
