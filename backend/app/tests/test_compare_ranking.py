"""compare endpoint must rank by risk-adjusted Sharpe and expose it."""
from __future__ import annotations

from datetime import datetime, timedelta

import app.api.backtest as bt
from app.api.backtest import CompareRequest, compare
from app.schemas import Candle


def _candles(closes):
    t0 = datetime(2024, 1, 1)
    out = []
    for i, c in enumerate(closes):
        out.append(Candle(timestamp=t0 + timedelta(hours=i), open=c, high=c, low=c, close=c, volume=1.0))
    return out


class _FakeBroker:
    def __init__(self, candles):
        self._candles = candles

    def get_ohlcv(self, symbol, timeframe, limit):
        return self._candles[:limit]

    def get_ohlcv_range(self, symbol, timeframe, start, end):
        return self._candles


def test_compare_sorts_by_sharpe_and_exposes_it(monkeypatch):
    # Trending series so multiple built-ins actually trade.
    candles = _candles([100 + (i % 7) - 3 + i * 0.5 for i in range(120)])
    monkeypatch.setattr(bt, "get_data_broker", lambda market: _FakeBroker(candles))
    rows = compare(CompareRequest(symbol="BTC/USDT", limit=120, strategies=["ma_cross", "rsi"]))
    assert all(hasattr(r, "sharpe") for r in rows)
    sharpes = [r.sharpe for r in rows if r.error is None]
    assert sharpes == sorted(sharpes, reverse=True)
