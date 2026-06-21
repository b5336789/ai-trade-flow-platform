# app/tests/test_workflow_backtest_api.py
from __future__ import annotations

from fastapi.testclient import TestClient

from app.brokers import registry
from app.main import app
from app.schemas import MarketKind
from app.tests.helpers import StubBroker, make_candles
from app.workflow import nodes


def _patch_data(monkeypatch, closes):
    stub = StubBroker({"BTC/USDT": closes[-1]}, candles=make_candles(closes))
    monkeypatch.setattr("app.api.backtest.get_data_broker", lambda market: stub)


def test_workflow_backtest_endpoint_persists_and_reads(monkeypatch):
    _patch_data(monkeypatch, [5, 5, 5, 5, 5, 9, 9, 9])
    client = TestClient(app)
    graph = {
        "nodes": [
            {"id": "d", "type": "data_source", "params": {"symbol": "BTC/USDT"}},
            {"id": "s", "type": "strategy", "params": {"name": "ma_cross", "fast": 2, "slow": 4}},
            {"id": "o", "type": "order", "params": {}},
        ],
        "edges": [{"source": "d", "target": "s"}, {"source": "s", "target": "o"}],
    }
    resp = client.post("/api/backtest/workflow", json={"graph": graph, "limit": 50})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "run_id" in body and body["symbols"] == ["BTC/USDT"]
    rid = body["run_id"]

    runs = client.get("/api/workflows/runs?kind=backtest").json()
    assert any(r["id"] == rid for r in runs)
    sigs = client.get(f"/api/workflows/runs/{rid}/signals").json()
    assert sigs and all("trace_json" in s for s in sigs)
