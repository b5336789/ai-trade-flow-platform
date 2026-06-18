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


def test_target_position_idempotent_across_repeated_buy_ticks(seeded):
    """Already holding the target, the same buy signal across 5 ticks => at most 1 fill, not 5.

    Target-position semantics (M0.5): buy => hold `quantity`; once held, delta==0 so no order.
    """
    graph = _graph()
    fills = 0
    for _ in range(5):
        result = run_workflow(graph)
        assert result.status == "ok", result.error
        fills += len(result.orders)
    assert fills <= 1, f"expected at most 1 fill across repeated ticks, got {fills}"
    pos = registry.get_broker(MarketKind.crypto).get_positions()
    assert pos[0].symbol == "BTC/USDT" and pos[0].quantity == 10  # at target, not 50


def test_same_run_id_reruns_persist_one_order(seeded):
    """Re-running the SAME run_id => exactly 1 OrderRecord persisted.

    Here the second run is even short-circuited by the target-position no-op (already holding the
    target), so it never reaches execute_order. The deterministic client_order_id is the backstop
    when position state is missing/stale; the direct skip path is covered in test_orders_api.py.
    """
    import uuid

    from sqlmodel import Session, select

    from app.db import engine
    from app.models import OrderRecord

    run_id = f"run-{uuid.uuid4().hex}"
    graph = _graph()
    with Session(engine) as session:
        before = len(session.exec(select(OrderRecord)).all())
        r1 = run_workflow(graph, session=session, run_id=run_id)
        r2 = run_workflow(graph, session=session, run_id=run_id)
        after = session.exec(select(OrderRecord)).all()

    assert len(r1.orders) == 1
    assert len(r2.orders) == 0  # already at target -> no-op
    assert len(after) - before == 1, "the same run_id must persist exactly one OrderRecord"


def test_same_run_id_skips_even_if_position_reset(seeded):
    """The client_order_id is the backstop: same run_id reruns skip even with position wiped.

    Resetting the paper position between runs makes target-position want to re-buy; the matching
    client_order_id (same run_id + node) forces an idempotent skip, so no second fill is placed.
    """
    import uuid

    from sqlmodel import Session, select

    from app.db import engine
    from app.models import OrderRecord

    run_id = f"run-{uuid.uuid4().hex}"
    graph = _graph()
    with Session(engine) as session:
        before = len(session.exec(select(OrderRecord)).all())
        r1 = run_workflow(graph, session=session, run_id=run_id)

        # Wipe the in-memory position so the target-position no-op would NOT fire on rerun.
        registry.get_broker(MarketKind.crypto)._positions.clear()

        r2 = run_workflow(graph, session=session, run_id=run_id)
        after = session.exec(select(OrderRecord)).all()

    assert len(r1.orders) == 1
    assert len(r2.orders) == 1  # returned, but it is the idempotent skip (no new fill)
    assert r2.orders[0]["info"].get("idempotent_skip") is True
    assert len(after) - before == 1, "client_order_id must persist exactly one OrderRecord"


def test_sell_signal_targets_flat(monkeypatch):
    """A sell signal means TARGET=flat: sell exactly the held quantity, not a fixed param."""
    sell_cross = make_candles([9, 9, 9, 9, 9, 9, 5])  # fast SMA crosses below slow -> sell
    monkeypatch.setattr(
        nodes, "get_data_broker", lambda market: StubBroker({"BTC/USDT": 5.0}, candles=sell_cross)
    )
    registry.reset_paper_brokers()
    broker = PaperBroker(data_provider=StubBroker({"BTC/USDT": 5.0}), starting_cash=10_000.0)
    from app.schemas import OrderRequest, OrderSide

    broker.create_order(OrderRequest(symbol="BTC/USDT", side=OrderSide.buy, quantity=7))
    registry._paper_cache[MarketKind.crypto] = broker

    result = run_workflow(_graph())
    assert result.status == "ok", result.error
    assert len(result.orders) == 1
    assert result.orders[0]["side"] == "sell"
    assert result.orders[0]["quantity"] == 7  # the full holding, reaching flat
    assert broker.get_positions() == []
    registry.reset_paper_brokers()


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
