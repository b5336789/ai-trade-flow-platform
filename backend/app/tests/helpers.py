"""Test helpers — synthetic candles so tests need no network/exchange."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.schemas import Candle


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
