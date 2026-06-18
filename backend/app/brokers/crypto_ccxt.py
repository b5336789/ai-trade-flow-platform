"""Crypto broker backed by ccxt (Binance by default, with testnet support).

Market data (ticker/OHLCV) uses public endpoints and needs no keys. Live orders require
BINANCE_API_KEY/SECRET and fail loudly if missing (CLAUDE.md: never silently skip).
"""

from __future__ import annotations

from datetime import datetime, timezone

import ccxt

from app.brokers.base import Broker
from app.config import settings
from app.schemas import (
    Balance,
    Candle,
    MarketKind,
    OrderRequest,
    OrderResult,
    OrderType,
    Position,
    Ticker,
    TradingMode,
)


def _to_dt(ms: int | None) -> datetime:
    if ms is None:
        return datetime.now(timezone.utc)
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


class CcxtBroker(Broker):
    market = MarketKind.crypto
    mode = TradingMode.live

    def __init__(self, exchange_id: str = "binance") -> None:
        if not hasattr(ccxt, exchange_id):
            raise ValueError(f"Unknown ccxt exchange: {exchange_id}")
        params: dict = {"enableRateLimit": True}
        if settings.binance_api_key and settings.binance_api_secret:
            params["apiKey"] = settings.binance_api_key
            params["secret"] = settings.binance_api_secret
        self._exchange = getattr(ccxt, exchange_id)(params)
        self._exchange_id = exchange_id
        if settings.binance_testnet:
            # set_sandbox_mode raises on exchanges without a testnet; surface that loudly.
            self._exchange.set_sandbox_mode(True)

    @property
    def name(self) -> str:
        return f"ccxt:{self._exchange_id}"

    @property
    def has_credentials(self) -> bool:
        return bool(settings.binance_api_key and settings.binance_api_secret)

    def get_ticker(self, symbol: str) -> Ticker:
        t = self._exchange.fetch_ticker(symbol)
        price = t.get("last") or t.get("close")
        if price is None:
            raise RuntimeError(f"No price returned for {symbol}")
        return Ticker(symbol=symbol, price=float(price), timestamp=_to_dt(t.get("timestamp")))

    def get_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> list[Candle]:
        raw = self._exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        if not raw:
            raise RuntimeError(f"No OHLCV data returned for {symbol} {timeframe}")
        return [
            Candle(
                timestamp=_to_dt(r[0]),
                open=float(r[1]),
                high=float(r[2]),
                low=float(r[3]),
                close=float(r[4]),
                volume=float(r[5]),
            )
            for r in raw
        ]

    def create_order(self, request: OrderRequest) -> OrderResult:
        if not self.has_credentials:
            raise RuntimeError(
                "Live crypto order requires BINANCE_API_KEY/BINANCE_API_SECRET in the environment"
            )
        order = self._exchange.create_order(
            request.symbol,
            request.type.value,
            request.side.value,
            request.quantity,
            request.limit_price,
        )
        price = order.get("average") or order.get("price") or self.get_ticker(request.symbol).price
        return OrderResult(
            id=str(order.get("id", "")),
            symbol=request.symbol,
            side=request.side,
            quantity=request.quantity,
            price=float(price),
            status=order.get("status") or "open",
            mode=TradingMode.live,
            broker=self.name,
            timestamp=_to_dt(order.get("timestamp")),
            info=order if isinstance(order, dict) else {},
        )

    def get_balance(self) -> list[Balance]:
        if not self.has_credentials:
            return []
        bal = self._exchange.fetch_balance()
        free = bal.get("free", {})
        out: list[Balance] = []
        for asset, total in bal.get("total", {}).items():
            if total:
                out.append(Balance(asset=asset, free=float(free.get(asset, 0.0)), total=float(total)))
        return out

    def get_positions(self) -> list[Position]:
        """Synthesise spot positions from balances (M0.5).

        Spot holdings live in balances, not as derivative positions. Every non-quote asset with a
        non-zero total is materialised as a ``Position`` against the configured quote asset
        (``symbol = f"{asset}/{quote}"``) so the position-value risk cap is live for spot.

        Average entry cost is unknown from a balance snapshot, so ``avg_price`` is reported as 0;
        the risk guard judges the exposure cap by current market value, not by avg cost.
        """
        if not self.has_credentials:
            return []
        quote = settings.paper_quote_asset
        out: list[Position] = []
        for balance in self.get_balance():
            if balance.asset == quote or balance.total <= 0:
                continue
            out.append(
                Position(symbol=f"{balance.asset}/{quote}", quantity=balance.total, avg_price=0.0)
            )
        return out
