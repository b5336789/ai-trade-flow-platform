"""POST /api/backtest persists a BacktestRun retrievable via the runs endpoints."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, SQLModel, create_engine

import app.api.backtest as bt
from app.api.backtest import BacktestRequest, backtest, list_backtest_runs
from app.db import get_session
from app.schemas import Candle


@pytest.fixture()
def session():
    """Fresh isolated in-memory DB for this test file."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    import app.models  # noqa: F401  (register tables)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _candles(n):
    t0 = datetime(2024, 1, 1)
    return [
        Candle(timestamp=t0 + timedelta(hours=i), open=100 + i, high=100 + i,
               low=100 + i, close=100 + i, volume=1.0)
        for i in range(n)
    ]


class _FakeBroker:
    def __init__(self, candles):
        self._candles = candles

    def get_ohlcv(self, symbol, timeframe, limit):
        return self._candles[:limit]

    def get_ohlcv_range(self, symbol, timeframe, start, end):
        return self._candles


def test_backtest_persists_and_lists(monkeypatch, session):
    monkeypatch.setattr(bt, "get_data_broker", lambda market: _FakeBroker(_candles(60)))
    result = backtest(BacktestRequest(symbol="BTC/USDT", limit=60, strategy="ma_cross"), session=session)
    assert result.assumptions is not None
    runs = list_backtest_runs(limit=10, session=session)
    assert len(runs) == 1
    assert runs[0].symbol == "BTC/USDT"
    assert runs[0].strategy == "ma_cross"
    assert runs[0].metrics_json["total_return_pct"] == result.total_return_pct
