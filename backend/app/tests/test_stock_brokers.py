"""Tests for stock broker scaffolds + CSV-backed offline data for 台股/美股."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.brokers import market_data, registry
from app.brokers.csv_data import CsvDataBroker
from app.brokers.firstrade import FirstradeBroker
from app.brokers.yuanta import YuantaBroker
from app.main import app
from app.schemas import MarketKind, OrderRequest, OrderSide

CSV = """timestamp,open,high,low,close,volume
2024-01-01,100,105,99,104,1000
2024-01-02,104,110,103,109,1200
2024-01-03,109,109,100,101,1500
"""


def test_parse_csv_ok_and_sorted():
    candles = market_data.parse_csv(CSV)
    assert len(candles) == 3
    assert candles[0].close == 104
    assert candles[-1].close == 101


def test_parse_csv_missing_columns_fails_loud():
    with pytest.raises(ValueError):
        market_data.parse_csv("timestamp,open\n2024-01-01,100")


def test_live_stock_brokers_fail_loud():
    with pytest.raises(NotImplementedError):
        YuantaBroker().create_order(OrderRequest(symbol="2330", side=OrderSide.buy, quantity=1))
    with pytest.raises(NotImplementedError):
        FirstradeBroker().get_ticker("AAPL")


def test_data_broker_requires_import_then_serves():
    market_data.clear()
    with pytest.raises(NotImplementedError):
        registry.get_data_broker(MarketKind.tw_stock)

    market_data.set_candles(MarketKind.tw_stock, "2330", market_data.parse_csv(CSV))
    broker = registry.get_data_broker(MarketKind.tw_stock)
    assert isinstance(broker, CsvDataBroker)
    assert broker.get_ticker("2330").price == 101
    assert len(broker.get_ohlcv("2330", limit=2)) == 2
    market_data.clear()


def test_import_then_backtest_tw_stock_offline():
    market_data.clear()
    registry.reset_paper_brokers()
    with TestClient(app) as client:
        imp = client.post(
            "/api/markets/import",
            json={"market": "tw_stock", "symbol": "2330", "csv": CSV},
        )
        assert imp.status_code == 200, imp.text
        assert imp.json()["imported"] == 3

        bt = client.post(
            "/api/backtest",
            json={"symbol": "2330", "market": "tw_stock", "strategy": "ma_cross",
                  "params": {"fast": 2, "slow": 3}},
        )
        assert bt.status_code == 200, bt.text
        assert "total_return_pct" in bt.json()
    market_data.clear()
    registry.reset_paper_brokers()
