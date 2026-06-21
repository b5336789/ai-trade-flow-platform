from __future__ import annotations

import pytest
from sqlmodel import Session, select

from app.db import engine
from app.models import WorkflowSignal
from app.workflow.run_store import (
    build_trace,
    order_node_ancestors,
    persist_workflow_run,
    resolve_order_symbol,
)
from app.schemas import Signal, SignalAction
from app.tests.helpers import make_candles
from app.workflow.schema import Edge, NodeConfig, NodeType, WorkflowGraph


def _graph() -> WorkflowGraph:
    return WorkflowGraph(
        nodes=[
            NodeConfig(id="d", type=NodeType.data_source, params={"symbol": "BTC/USDT"}),
            NodeConfig(id="s", type=NodeType.strategy, params={"name": "ma_cross"}),
            NodeConfig(id="o", type=NodeType.order, params={"quantity": 1}),
            NodeConfig(id="l", type=NodeType.logger, params={}),
        ],
        edges=[Edge(source="d", target="s"), Edge(source="s", target="o"), Edge(source="o", target="l")],
    )


def test_ancestors_and_symbol_resolution():
    g = _graph()
    assert order_node_ancestors(g, "o") == ["d", "s"]
    assert resolve_order_symbol(g, "o") == "BTC/USDT"


def test_resolve_symbol_fails_loud_when_ambiguous():
    g = WorkflowGraph(
        nodes=[
            NodeConfig(id="d1", type=NodeType.data_source, params={"symbol": "BTC/USDT"}),
            NodeConfig(id="d2", type=NodeType.data_source, params={"symbol": "ETH/USDT"}),
            NodeConfig(id="c", type=NodeType.combine, params={}),
            NodeConfig(id="o", type=NodeType.order, params={}),
        ],
        edges=[Edge(source="d1", target="c"), Edge(source="d2", target="c"), Edge(source="c", target="o")],
    )
    with pytest.raises(ValueError):
        resolve_order_symbol(g, "o")


def test_build_trace_uses_ancestor_outputs():
    g = _graph()
    outputs = {
        "d": make_candles([1, 2, 3]),
        "s": Signal(action=SignalAction.buy, confidence=0.9, source="ma_cross"),
    }
    trace = build_trace(g, "o", outputs)
    ids = [t["node_id"] for t in trace]
    assert ids == ["d", "s"]
    assert trace[1]["summary"]["signal"]["action"] == "buy"


def test_persist_workflow_run_writes_signals():
    g = _graph()
    with Session(engine) as s:
        run_id = persist_workflow_run(
            s,
            run_id="r1",
            kind="backtest",
            graph=g,
            market="crypto",
            symbols=["BTC/USDT"],
            timeframe="1h",
            starting_cash=100_000.0,
            params={"limit": 100},
            metrics={"total_return_pct": 0.0},
            equity_curve=[],
            trades=[],
            status="ok",
            signals=[
                {
                    "order_node_id": "o",
                    "symbol": "BTC/USDT",
                    "timestamp": "2024-01-01T00:00:00+00:00",
                    "bar_index": 1,
                    "action": "buy",
                    "confidence": 0.9,
                    "price": 9.0,
                    "trace_json": [{"node_id": "s", "type": "strategy", "summary": {}}],
                }
            ],
        )
        rows = s.exec(select(WorkflowSignal).where(WorkflowSignal.run_id == run_id)).all()
        assert len(rows) == 1 and rows[0].action == "buy"
