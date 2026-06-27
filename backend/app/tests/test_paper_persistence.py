"""Paper-trading state must survive a process restart (persisted via PaperStore)."""

from __future__ import annotations

import pytest

from app.brokers.paper import PaperBroker
from app.schemas import MarketKind, OrderRequest, OrderSide
from app.tests.helpers import StubBroker
from app.trading.paper_store import PaperStore

# us_stock is not used for paper trading by other tests -> isolated.
MARKET = MarketKind.us_stock


@pytest.fixture(autouse=True)
def _no_slippage(monkeypatch):
    """Mechanic tests assert fee-only fills; pin slippage off (default is now 5 bps)."""
    from app.config import settings
    monkeypatch.setattr(settings, "cost_slippage_bps", 0.0)


@pytest.fixture()
def store():
    s = PaperStore(MARKET)
    s.reset()
    yield s
    s.reset()


def test_state_persists_across_broker_instances(store):
    b1 = PaperBroker(StubBroker({"AAPL": 100.0}), starting_cash=10_000.0, store=store)
    b1.create_order(OrderRequest(symbol="AAPL", side=OrderSide.buy, quantity=5))

    # Simulate a restart: a fresh broker over the same store hydrates from the DB.
    b2 = PaperBroker(StubBroker({"AAPL": 100.0}), starting_cash=999_999.0, store=store)
    # 10000 - 5*100 - 0.375 fee (crypto 7.5 bps), persisted — not the new starting_cash
    assert b2.cash == pytest.approx(9_500.0 - 0.375)
    positions = b2.get_positions()
    assert len(positions) == 1
    assert positions[0].symbol == "AAPL" and positions[0].quantity == 5


def test_sell_then_reload_reflects_closed_position(store):
    b1 = PaperBroker(StubBroker({"AAPL": 100.0}), starting_cash=10_000.0, store=store)
    b1.create_order(OrderRequest(symbol="AAPL", side=OrderSide.buy, quantity=5))
    b1.create_order(OrderRequest(symbol="AAPL", side=OrderSide.sell, quantity=5))

    b2 = PaperBroker(StubBroker({"AAPL": 100.0}), store=store)
    assert b2.get_positions() == []
    # round trip at 100: -0.375 buy fee - 0.375 sell fee (crypto 7.5 bps)
    assert b2.cash == pytest.approx(10_000.0 - 0.75)


def test_reset_clears_persisted_state(store):
    b1 = PaperBroker(StubBroker({"AAPL": 100.0}), starting_cash=10_000.0, store=store)
    b1.create_order(OrderRequest(symbol="AAPL", side=OrderSide.buy, quantity=5))
    store.reset()

    cash, positions = store.load()
    assert cash is None and positions == {}
