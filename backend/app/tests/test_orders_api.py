"""HTTP-level test for the orders flow (paper mode, offline via stub-backed broker)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from datetime import datetime, timezone

from app.brokers import registry
from app.brokers.crypto_ccxt import CcxtBroker
from app.brokers.paper import PaperBroker
from app.main import app
from app.schemas import Balance, MarketKind, OrderRequest, OrderSide, Ticker, TradingMode
from app.tests.helpers import StubBroker
from app.trading.execution import execute_order
from app.trading.risk import RiskError, RiskGuard


@pytest.fixture(autouse=True)
def _no_slippage(monkeypatch):
    """Mechanic tests assert fee-only fills; pin slippage off (default is now 5 bps)."""
    from app.config import settings
    monkeypatch.setattr(settings, "cost_slippage_bps", 0.0)


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
    # 10000 - 5*100 - 0.375 crypto taker fee (7.5 bps on 500 notional, M0.1)
    assert portfolio["cash"] == pytest.approx(9_500.0 - 0.375)
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


# --- M0.5: spot position synthesis + market-value cap + idempotency ---


def _live_spot_broker(monkeypatch, *, btc_balance: float, price: float) -> CcxtBroker:
    """A CcxtBroker whose balances/prices are stubbed (no network, no real keys)."""
    broker = CcxtBroker()
    monkeypatch.setattr(type(broker), "has_credentials", property(lambda self: True))
    monkeypatch.setattr(
        broker,
        "get_balance",
        lambda: [Balance(asset="BTC", free=btc_balance, total=btc_balance),
                 Balance(asset="USDT", free=1_000.0, total=1_000.0)],
    )
    monkeypatch.setattr(
        broker,
        "get_ticker",
        lambda symbol: Ticker(symbol=symbol, price=price, timestamp=datetime.now(timezone.utc)),
    )
    return broker


def test_ccxt_spot_positions_synthesised_from_balances(monkeypatch):
    """get_positions() materialises non-quote balances as Positions (avg_price unknown -> 0)."""
    broker = _live_spot_broker(monkeypatch, btc_balance=0.5, price=20_000.0)
    positions = broker.get_positions()
    assert len(positions) == 1
    pos = positions[0]
    assert pos.symbol == "BTC/USDT"
    assert pos.quantity == 0.5
    assert pos.avg_price == 0.0  # avg cost unknown from a balance snapshot


def test_live_spot_buy_over_position_cap_rejected(monkeypatch):
    """A live spot buy that pushes position MARKET VALUE over the cap is rejected (RiskError)."""
    # Held 4 BTC @ 20k (market value 80k). max_position_value=100k. Buying 2 more BTC (40k)
    # => projected 120k by market value -> reject. (Order value 40k is under max_order_value.)
    broker = _live_spot_broker(monkeypatch, btc_balance=4.0, price=20_000.0)
    monkeypatch.setattr("app.trading.execution.get_broker", lambda market, mode=None: broker)

    guard = RiskGuard(max_order_value=50_000.0, max_position_value=100_000.0)
    request = OrderRequest(symbol="BTC/USDT", side=OrderSide.buy, quantity=2.0)
    with pytest.raises(RiskError, match="position value"):
        execute_order(request, market=MarketKind.crypto, mode=TradingMode.live, guard=guard)


def test_execute_order_idempotent_by_client_order_id(client):
    """Same client_order_id => exactly 1 OrderRecord/fill; the rerun is a skip."""
    from sqlmodel import Session, select

    from app.db import engine
    from app.models import OrderRecord

    import uuid

    request = OrderRequest(symbol="BTC/USDT", side=OrderSide.buy, quantity=1.0)
    coid = f"test-coid-{uuid.uuid4().hex}"
    with Session(engine) as session:
        before = len(session.exec(select(OrderRecord).where(OrderRecord.client_order_id == coid)).all())
        r1 = execute_order(request, market=MarketKind.crypto, session=session, client_order_id=coid)
        r2 = execute_order(request, market=MarketKind.crypto, session=session, client_order_id=coid)
        after = session.exec(select(OrderRecord).where(OrderRecord.client_order_id == coid)).all()

    assert r1.info.get("idempotent_skip") is not True
    assert r2.info.get("idempotent_skip") is True
    assert r2.id == r1.id  # same broker order returned
    assert len(after) - before == 1
