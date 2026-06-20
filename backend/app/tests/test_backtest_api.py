"""API-level tests for the backtest router (walk-forward endpoint)."""

from __future__ import annotations

import math

from fastapi.testclient import TestClient

from app.main import app
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
