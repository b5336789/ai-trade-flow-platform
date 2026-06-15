"""End-to-end workflow engine tests (offline: stub data + seeded paper broker)."""

from __future__ import annotations

import pytest

from app.brokers import registry
from app.brokers.paper import PaperBroker
from app.schemas import MarketKind
from app.tests.helpers import StubBroker, make_candles
from app.workflow import nodes
from app.workflow.engine import _topological_order, run_workflow
from app.workflow.schema import Edge, NodeConfig, NodeType, WorkflowGraph


@pytest.fixture()
def seeded(monkeypatch):
    """Wire data_source (stub candles that trigger a buy cross) + paper broker (offline)."""
    buy_cross = make_candles([5, 5, 5, 5, 5, 5, 9])  # fast SMA crosses above slow on last bar
    stub = StubBroker({"BTC/USDT": 9.0}, candles=buy_cross)
    monkeypatch.setattr(nodes, "get_data_broker", lambda market: stub)

    registry.reset_paper_brokers()
    registry._paper_cache[MarketKind.crypto] = PaperBroker(
        data_provider=StubBroker({"BTC/USDT": 9.0}), starting_cash=10_000.0
    )
    yield
    registry.reset_paper_brokers()


def _graph() -> WorkflowGraph:
    return WorkflowGraph(
        nodes=[
            NodeConfig(id="d", type=NodeType.data_source, params={"symbol": "BTC/USDT"}),
            NodeConfig(id="s", type=NodeType.strategy, params={"name": "ma_cross", "fast": 2, "slow": 4}),
            NodeConfig(id="o", type=NodeType.order, params={"quantity": 10}),
            NodeConfig(id="l", type=NodeType.logger, params={}),
        ],
        edges=[Edge(source="d", target="s"), Edge(source="s", target="o"), Edge(source="o", target="l")],
    )


def test_run_places_order_on_buy_signal(seeded):
    result = run_workflow(_graph())
    assert result.status == "ok", result.error
    assert len(result.orders) == 1
    order = result.orders[0]
    assert order["side"] == "buy"
    assert order["quantity"] == 10
    assert order["mode"] == "paper"
    # paper broker should now hold the position
    pos = registry.get_broker(MarketKind.crypto).get_positions()
    assert pos[0].symbol == "BTC/USDT" and pos[0].quantity == 10


def test_hold_signal_places_no_order(monkeypatch):
    flat = make_candles([5, 5, 5, 5, 5, 5, 5])  # no cross -> hold
    monkeypatch.setattr(nodes, "get_data_broker", lambda market: StubBroker({"BTC/USDT": 5.0}, candles=flat))
    graph = WorkflowGraph(
        nodes=[
            NodeConfig(id="d", type=NodeType.data_source, params={"symbol": "BTC/USDT"}),
            NodeConfig(id="s", type=NodeType.strategy, params={"name": "ma_cross", "fast": 2, "slow": 4}),
            NodeConfig(id="o", type=NodeType.order, params={"quantity": 10}),
        ],
        edges=[Edge(source="d", target="s"), Edge(source="s", target="o")],
    )
    result = run_workflow(graph)
    assert result.status == "ok"
    assert result.orders == []


def test_cycle_is_rejected():
    graph = WorkflowGraph(
        nodes=[
            NodeConfig(id="a", type=NodeType.logger),
            NodeConfig(id="b", type=NodeType.logger),
        ],
        edges=[Edge(source="a", target="b"), Edge(source="b", target="a")],
    )
    result = run_workflow(graph)
    assert result.status == "error"
    assert "cycle" in result.error


def test_topological_order_respects_dependencies():
    graph = _graph()
    order = [n.id for n in _topological_order(graph)]
    assert order.index("d") < order.index("s") < order.index("o") < order.index("l")


def test_node_failure_reports_which_node(monkeypatch):
    # strategy node with no upstream candles -> fails loud, engine names the node
    graph = WorkflowGraph(
        nodes=[NodeConfig(id="s", type=NodeType.strategy, params={"name": "ma_cross"})],
        edges=[],
    )
    result = run_workflow(graph)
    assert result.status == "error"
    assert "s" in result.error
