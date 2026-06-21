from __future__ import annotations

from fastapi.testclient import TestClient

from app.brokers import registry
from app.brokers.paper import PaperBroker
from app.main import app
from app.schemas import MarketKind
from app.tests.helpers import StubBroker, make_candles
from app.workflow import nodes


def test_live_run_persists_workflow_run_and_signals(monkeypatch):
    buy_cross = make_candles([5, 5, 5, 5, 5, 9])
    monkeypatch.setattr(nodes, "get_data_broker", lambda market: StubBroker({"BTC/USDT": 9.0}, candles=buy_cross))
    registry.reset_paper_brokers()
    registry._paper_cache[MarketKind.crypto] = PaperBroker(
        data_provider=StubBroker({"BTC/USDT": 9.0}), starting_cash=10_000.0
    )
    client = TestClient(app)
    graph = {
        "nodes": [
            {"id": "d", "type": "data_source", "params": {"symbol": "BTC/USDT"}},
            {"id": "s", "type": "strategy", "params": {"name": "ma_cross", "fast": 2, "slow": 4}},
            {"id": "o", "type": "order", "params": {"quantity": 1}},
        ],
        "edges": [{"source": "d", "target": "s"}, {"source": "s", "target": "o"}],
    }
    r = client.post("/api/workflows/run", json=graph)
    assert r.status_code == 200, r.text
    runs = client.get("/api/workflows/runs?kind=paper").json()
    assert runs, "expected a persisted paper run"
    sigs = client.get(f"/api/workflows/runs/{runs[0]['id']}/signals").json()
    assert any(s["action"] == "buy" and s["symbol"] == "BTC/USDT" for s in sigs)
    registry.reset_paper_brokers()
