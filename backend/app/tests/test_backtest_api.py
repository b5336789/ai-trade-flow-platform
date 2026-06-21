"""API-level tests for the backtest router (walk-forward endpoint)."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.brokers.base import Broker
from app.main import app
from app.schemas import Balance, Candle, MarketKind, Position, Ticker, TradingMode
from app.tests.helpers import StubBroker, make_candles

client = TestClient(app)

# Oscillating closes so ma_cross actually crosses within each fold.
_CLOSES = [100 + 10 * math.sin(i / 5) for i in range(200)]


def _stub_data_broker(monkeypatch):
    """Make the walk-forward endpoint use deterministic offline candles."""
    monkeypatch.setattr(
        "app.api.backtest.get_data_broker",
        lambda market: StubBroker({"BTC/USDT": 100.0}, candles=make_candles(_CLOSES)),
    )


def test_walk_forward_returns_fold_structure(monkeypatch):
    _stub_data_broker(monkeypatch)
    resp = client.post(
        "/api/backtest/walk-forward",
        json={
            "symbol": "BTC/USDT",
            "strategy": "ma_cross",
            "param_grid": {"fast": [5, 10], "slow": [20, 30]},
            "n_folds": 3,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["strategy"] == "ma_cross"
    assert body["n_folds"] == 3
    assert len(body["folds"]) == 3
    assert "aggregate_oos_metric" in body
    assert "aggregate_oos_return_pct" in body
    # each fold carries the in-sample vs out-of-sample structure
    for fold in body["folds"]:
        assert "best_params" in fold
        assert "oos_metric" in fold
        assert "oos_return_pct" in fold


def test_walk_forward_bad_n_folds_is_422(monkeypatch):
    _stub_data_broker(monkeypatch)
    resp = client.post(
        "/api/backtest/walk-forward",
        json={
            "symbol": "BTC/USDT",
            "strategy": "ma_cross",
            "param_grid": {"fast": [5, 10], "slow": [20, 30]},
            "n_folds": 1,
        },
    )
    # n_folds must be >= 2; FastAPI request-validation (Field ge=2) returns 422.
    assert resp.status_code == 422, resp.text


class _RangeStubBroker(Broker):
    """Stub whose get_ohlcv_range returns only candles inside [start, end] from a fixed daily series."""

    market = MarketKind.crypto
    mode = TradingMode.live

    def __init__(self, closes: list[float]) -> None:
        base = datetime(2024, 1, 1, tzinfo=timezone.utc)
        self._series = [
            Candle(timestamp=base + timedelta(days=i), open=c, high=c, low=c, close=c, volume=1.0)
            for i, c in enumerate(closes)
        ]

    @property
    def name(self) -> str:
        return "range-stub"

    def get_ticker(self, symbol: str) -> Ticker:
        return Ticker(symbol=symbol, price=self._series[-1].close, timestamp=self._series[-1].timestamp)

    def get_ohlcv(self, symbol, timeframe="1h", limit=100):
        return self._series[-limit:]

    def get_ohlcv_range(self, symbol, timeframe, start, end):
        if start > end:
            raise ValueError("start must be before end")
        return [c for c in self._series if start <= c.timestamp <= end]

    def create_order(self, request):  # pragma: no cover
        raise NotImplementedError

    def get_balance(self) -> list[Balance]:
        return []

    def get_positions(self) -> list[Position]:
        return []


def _stub_range_broker(monkeypatch, closes):
    monkeypatch.setattr("app.api.backtest.get_data_broker", lambda market: _RangeStubBroker(closes))


def test_backtest_date_range_uses_range_fetch(monkeypatch):
    # 60 daily bars from 2024-01-01; request a 20-day window → only those bars feed the backtest.
    _stub_range_broker(monkeypatch, [100 + 5 * math.sin(i / 4) for i in range(60)])
    resp = client.post(
        "/api/backtest",
        json={
            "symbol": "BTC/USDT",
            "strategy": "ma_cross",
            "params": {"fast": 2, "slow": 5},
            "start": "2024-01-05T00:00:00Z",
            "end": "2024-01-25T00:00:00Z",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "total_return_pct" in body
    # 21 candles in [01-05, 01-25] → equity curve has len-1 points (engine convention).
    assert len(body["equity_curve"]) == 21 - 1


def test_backtest_reversed_range_is_422(monkeypatch):
    _stub_range_broker(monkeypatch, [100.0] * 60)
    resp = client.post(
        "/api/backtest",
        json={
            "symbol": "BTC/USDT",
            "strategy": "ma_cross",
            "start": "2024-02-01T00:00:00Z",
            "end": "2024-01-01T00:00:00Z",
        },
    )
    assert resp.status_code == 422, resp.text


def test_backtest_range_too_few_candles_is_422(monkeypatch):
    _stub_range_broker(monkeypatch, [100.0] * 60)
    # A 1-day window catches a single candle → run_backtest rejects (<2) → 422 fail-loud.
    resp = client.post(
        "/api/backtest",
        json={
            "symbol": "BTC/USDT",
            "strategy": "ma_cross",
            "start": "2024-01-10T00:00:00Z",
            "end": "2024-01-10T12:00:00Z",
        },
    )
    assert resp.status_code == 422, resp.text


def test_backtest_no_range_still_uses_limit(monkeypatch):
    # Backward-compat: omitting start/end keeps the limit path (no get_ohlcv_range call needed).
    _stub_range_broker(monkeypatch, [100 + 5 * math.sin(i / 4) for i in range(60)])
    resp = client.post(
        "/api/backtest",
        json={"symbol": "BTC/USDT", "strategy": "ma_cross", "params": {"fast": 2, "slow": 5}, "limit": 30},
    )
    assert resp.status_code == 200, resp.text
    assert len(resp.json()["equity_curve"]) == 30 - 1
