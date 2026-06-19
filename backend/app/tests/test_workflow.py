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


# --- M2.1: logic / combine nodes ---------------------------------------------

from app.schemas import Signal, SignalAction  # noqa: E402
from app.workflow.nodes import RunContext, _run_combine, _run_condition  # noqa: E402


def _sig(action: str, confidence: float = 1.0, source: str = "") -> Signal:
    return Signal(action=SignalAction(action), confidence=confidence, source=source)


def _combine(mode: str, signals, **params) -> Signal:
    node = NodeConfig(id="c", type=NodeType.combine, params={"mode": mode, **params})
    return _run_combine(node, list(signals), RunContext())


def test_combine_and_conflicting_signals_holds():
    """buy + sell into combine(AND) -> hold (no consensus)."""
    out = _combine("AND", [_sig("buy"), _sig("sell")])
    assert out.action == SignalAction.hold


def test_combine_and_all_agree_passes_through():
    out = _combine("AND", [_sig("buy", 0.9), _sig("buy", 0.6)])
    assert out.action == SignalAction.buy
    assert out.confidence == 0.6  # AND uses the weakest (min) agreeing confidence


def test_combine_and_any_hold_blocks():
    out = _combine("AND", [_sig("buy"), _sig("hold")])
    assert out.action == SignalAction.hold


def test_combine_or_conflict_uses_documented_bias():
    """buy + sell into combine(OR): the configured bias wins (default buy)."""
    buy_biased = _combine("OR", [_sig("buy", 0.5), _sig("sell", 0.9)])
    assert buy_biased.action == SignalAction.buy

    sell_biased = _combine("OR", [_sig("buy", 0.5), _sig("sell", 0.9)], bias="sell")
    assert sell_biased.action == SignalAction.sell


def test_combine_or_picks_actionable_over_hold():
    out = _combine("OR", [_sig("hold"), _sig("sell", 0.7)])
    assert out.action == SignalAction.sell
    assert out.confidence == 0.7


def test_combine_weighted_vote():
    """Weighted confidence vote: heavier/confident sell beats weaker buy."""
    out = _combine(
        "weighted",
        [_sig("buy", 0.4, source="a"), _sig("sell", 0.9, source="b")],
        weights={"a": 1.0, "b": 2.0},
    )
    assert out.action == SignalAction.sell

    # Balanced opposing votes net to ~0 -> hold.
    tie = _combine("weighted", [_sig("buy", 0.5), _sig("sell", 0.5)])
    assert tie.action == SignalAction.hold


def test_combine_does_not_silently_keep_first_signal():
    """combine must reduce ALL inputs, not return the first one."""
    out = _combine("AND", [_sig("sell"), _sig("buy"), _sig("buy")])
    assert out.action == SignalAction.hold  # not 'sell' (the first)


def test_order_node_rejects_multiple_signals_no_silent_drop(seeded):
    """Two strategy Signals fanning into one order node fail loud (no _first_signal drop)."""
    graph = WorkflowGraph(
        nodes=[
            NodeConfig(id="d", type=NodeType.data_source, params={"symbol": "BTC/USDT"}),
            NodeConfig(id="s1", type=NodeType.strategy, params={"name": "ma_cross", "fast": 2, "slow": 4}),
            NodeConfig(id="s2", type=NodeType.strategy, params={"name": "ma_cross", "fast": 2, "slow": 4}),
            NodeConfig(id="o", type=NodeType.order, params={"quantity": 10}),
        ],
        edges=[
            Edge(source="d", target="s1"),
            Edge(source="d", target="s2"),
            Edge(source="s1", target="o"),
            Edge(source="s2", target="o"),
        ],
    )
    result = run_workflow(graph)
    assert result.status == "error"
    assert "o" in result.error
    assert "combine" in result.error.lower()


def test_combine_node_merges_two_strategies_then_orders(seeded):
    """End-to-end: two strategies -> combine(AND) -> order. Both buy -> order placed."""
    graph = WorkflowGraph(
        nodes=[
            NodeConfig(id="d", type=NodeType.data_source, params={"symbol": "BTC/USDT"}),
            NodeConfig(id="s1", type=NodeType.strategy, params={"name": "ma_cross", "fast": 2, "slow": 4}),
            NodeConfig(id="s2", type=NodeType.strategy, params={"name": "ma_cross", "fast": 2, "slow": 4}),
            NodeConfig(id="c", type=NodeType.combine, params={"mode": "AND"}),
            NodeConfig(id="o", type=NodeType.order, params={"quantity": 10}),
        ],
        edges=[
            Edge(source="d", target="s1"),
            Edge(source="d", target="s2"),
            Edge(source="s1", target="c"),
            Edge(source="s2", target="c"),
            Edge(source="c", target="o"),
        ],
    )
    result = run_workflow(graph)
    assert result.status == "ok", result.error
    assert len(result.orders) == 1
    assert result.orders[0]["side"] == "buy"


def test_condition_threshold_passes_and_blocks():
    candles = make_candles([1, 2, 3, 4, 10])
    ctx = RunContext()
    passes = _run_condition(
        NodeConfig(id="x", type=NodeType.condition, params={"source": "close", "operator": ">", "value": 5}),
        [candles],
        ctx,
    )
    assert passes.action == SignalAction.buy  # condition met -> pass (actionable)

    blocked = _run_condition(
        NodeConfig(id="x", type=NodeType.condition, params={"source": "close", "operator": ">", "value": 50}),
        [candles],
        ctx,
    )
    assert blocked.action == SignalAction.hold  # condition not met -> block
