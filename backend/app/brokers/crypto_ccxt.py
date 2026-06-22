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


MAX_RANGE_BARS = 5000  # hard cap so a long range / small timeframe can't run away

_TIMEFRAME_MS = {
    "1m": 60_000, "3m": 180_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000,
    "1h": 3_600_000, "2h": 7_200_000, "4h": 14_400_000, "6h": 21_600_000,
    "12h": 43_200_000, "1d": 86_400_000, "1w": 604_800_000,
}


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

    def get_ohlcv_range(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> list[Candle]:
        _start = start if start.tzinfo else start.replace(tzinfo=timezone.utc)
        _end = end if end.tzinfo else end.replace(tzinfo=timezone.utc)
        start_ms = int(_start.timestamp() * 1000)
        end_ms = int(_end.timestamp() * 1000)
        step = _TIMEFRAME_MS.get(timeframe, 3_600_000)
        out: list[Candle] = []
        since = start_ms
        last_ts: int | None = None
        while since <= end_ms and len(out) < MAX_RANGE_BARS:
            raw = self._exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since)
            if not raw:
                break
            advanced = False
            for r in raw:
                ts = int(r[0])
                if ts > end_ms:
                    advanced = False
                    break
                if last_ts is not None and ts <= last_ts:
                    continue  # de-dupe overlap across pages
                out.append(
                    Candle(
                        timestamp=_to_dt(ts),
                        open=float(r[1]),
                        high=float(r[2]),
                        low=float(r[3]),
                        close=float(r[4]),
                        volume=float(r[5]),
                    )
                )
                last_ts = ts
                advanced = True
                if len(out) >= MAX_RANGE_BARS:
                    break
            if not advanced:
                break  # no progress (range exhausted or exchange ignored since) → stop, don't spin
            since = last_ts + step  # next page starts after the last bar we kept
        if not out:
            raise RuntimeError(
                f"No OHLCV data for {symbol} {timeframe} in range {start.isoformat()}..{end.isoformat()}"
            )
        return out[:MAX_RANGE_BARS]

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
