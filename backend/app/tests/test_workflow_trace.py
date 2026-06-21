"""run_workflow exposes raw per-node outputs via a caller-supplied RunContext."""

from __future__ import annotations

from app.schemas import Signal, SignalAction
from app.tests.helpers import StubBroker, make_candles
from app.workflow import nodes
from app.workflow.engine import run_workflow
from app.workflow.nodes import RunContext
from app.workflow.schema import Edge, NodeConfig, NodeType, WorkflowGraph


def _graph() -> WorkflowGraph:
    return WorkflowGraph(
        nodes=[
            NodeConfig(id="d", type=NodeType.data_source, params={"symbol": "BTC/USDT"}),
            NodeConfig(id="s", type=NodeType.strategy, params={"name": "ma_cross", "fast": 2, "slow": 4}),
        ],
        edges=[Edge(source="d", target="s")],
    )


def test_ctx_node_outputs_populated(monkeypatch):
    stub = StubBroker({"BTC/USDT": 9.0}, candles=make_candles([5, 5, 5, 5, 5, 5, 9]))
    monkeypatch.setattr(nodes, "get_data_broker", lambda market: stub)

    ctx = RunContext()
    result = run_workflow(_graph(), ctx=ctx)

    assert result.status == "ok", result.error
    # data_source output is the candle list; strategy output is a Signal
    assert isinstance(ctx.node_outputs["d"], list)
    assert isinstance(ctx.node_outputs["s"], Signal)
    assert ctx.node_outputs["s"].action in set(SignalAction)
