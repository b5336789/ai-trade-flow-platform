"""HTTP-level test for the orders flow (paper mode, offline via stub-backed broker)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.brokers import registry
from app.brokers.paper import PaperBroker
from app.main import app
from app.schemas import MarketKind
from app.tests.helpers import StubBroker


@pytest.fixture()
def client():
    # Seed the paper-broker cache so the API uses a deterministic, offline broker.
    registry.reset_paper_brokers()
    registry._paper_cache[MarketKind.crypto] = PaperBroker(
        data_provider=StubBroker({"BTC/USDT": 100.0}), starting_cash=10_000.0
    )
    with TestClient(app) as c:
        yield c
    registry.reset_paper_brokers()


def test_place_order_then_list_and_portfolio(client):
    resp = client.post(
        "/api/orders",
        params={"market": "crypto"},
        json={"symbol": "BTC/USDT", "side": "buy", "quantity": 5},
    )
    assert resp.status_code == 200, resp.text
    order = resp.json()
    assert order["status"] == "filled"
    assert order["price"] == 100.0
    assert order["mode"] == "paper"

    listed = client.get("/api/orders").json()
    assert any(o["broker_order_id"] == order["id"] for o in listed)

    portfolio = client.get("/api/orders/portfolio", params={"market": "crypto"}).json()
    assert portfolio["cash"] == pytest.approx(9_500.0)  # 10000 - 5*100
    assert portfolio["positions"][0]["symbol"] == "BTC/USDT"


def test_risk_rejection_returns_422(client):
    # Default RiskGuard max_order_value=50_000; 600 * 100 = 60_000 exceeds it.
    resp = client.post(
        "/api/orders",
        params={"market": "crypto"},
        json={"symbol": "BTC/USDT", "side": "buy", "quantity": 600},
    )
    assert resp.status_code == 422
    assert "Risk check failed" in resp.json()["detail"]
