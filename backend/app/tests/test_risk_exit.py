"""Tests for the stop-loss / take-profit risk_exit workflow node."""

from __future__ import annotations

import pytest

from app.brokers import registry
from app.brokers.paper import PaperBroker
from app.schemas import MarketKind, OrderRequest, OrderSide
from app.tests.helpers import StubBroker, make_candles
from app.workflow import nodes
from app.workflow.engine import run_workflow
from app.workflow.schema import Edge, NodeConfig, NodeType, WorkflowGraph


def _seed_position(entry_price: float, qty: float = 10.0) -> PaperBroker:
    """Seed the crypto paper broker with an open position bought at entry_price."""
    registry.reset_paper_brokers()
    broker = PaperBroker(data_provider=StubBroker({"BTC/USDT": entry_price}), starting_cash=10_000.0)
    broker.create_order(OrderRequest(symbol="BTC/USDT", side=OrderSide.buy, quantity=qty))
    registry._paper_cache[MarketKind.crypto] = broker
    return broker


def _graph() -> WorkflowGraph:
    return WorkflowGraph(
        nodes=[
            NodeConfig(id="d", type=NodeType.data_source, params={"symbol": "BTC/USDT"}),
            NodeConfig(
                id="r",
                type=NodeType.risk_exit,
                params={"stop_loss_pct": 5, "take_profit_pct": 10},
            ),
            NodeConfig(id="o", type=NodeType.order, params={"quantity": 10}),
        ],
        edges=[Edge(source="d", target="r"), Edge(source="r", target="o")],
    )


def _run_with_price(monkeypatch, current_price: float):
    candles = make_candles([current_price])
    monkeypatch.setattr(
        nodes, "get_data_broker", lambda market: StubBroker({"BTC/USDT": current_price}, candles=candles)
    )
    return run_workflow(_graph())


def test_stop_loss_triggers_sell(monkeypatch):
    _seed_position(entry_price=100.0)
    result = _run_with_price(monkeypatch, current_price=94.0)  # -6% <= -5%
    assert result.status == "ok", result.error
    assert len(result.orders) == 1 and result.orders[0]["side"] == "sell"
    registry.reset_paper_brokers()


def test_take_profit_triggers_sell(monkeypatch):
    _seed_position(entry_price=100.0)
    result = _run_with_price(monkeypatch, current_price=111.0)  # +11% >= +10%
    assert len(result.orders) == 1 and result.orders[0]["side"] == "sell"
    registry.reset_paper_brokers()


def test_within_thresholds_holds(monkeypatch):
    _seed_position(entry_price=100.0)
    result = _run_with_price(monkeypatch, current_price=103.0)  # +3%, no exit
    assert result.orders == []
    registry.reset_paper_brokers()


def test_no_position_holds(monkeypatch):
    registry.reset_paper_brokers()
    registry._paper_cache[MarketKind.crypto] = PaperBroker(
        data_provider=StubBroker({"BTC/USDT": 100.0}), starting_cash=10_000.0
    )
    result = _run_with_price(monkeypatch, current_price=80.0)
    assert result.orders == []
    registry.reset_paper_brokers()
