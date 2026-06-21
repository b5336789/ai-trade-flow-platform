from __future__ import annotations

import pytest

from app.backtest.workflow_backtest import run_workflow_backtest
from app.schemas import MarketKind
from app.tests.helpers import make_candles
from app.trading.costs import CostModel
from app.workflow.schema import Edge, NodeConfig, NodeType, WorkflowGraph


def _two_symbol_graph() -> WorkflowGraph:
    return WorkflowGraph(
        nodes=[
            NodeConfig(id="db", type=NodeType.data_source, params={"symbol": "BTC/USDT"}),
            NodeConfig(id="sb", type=NodeType.strategy, params={"name": "ma_cross", "fast": 2, "slow": 4}),
            NodeConfig(id="ob", type=NodeType.order, params={}),
            NodeConfig(id="de", type=NodeType.data_source, params={"symbol": "ETH/USDT"}),
            NodeConfig(id="se", type=NodeType.strategy, params={"name": "ma_cross", "fast": 2, "slow": 4}),
            NodeConfig(id="oe", type=NodeType.order, params={}),
        ],
        edges=[
            Edge(source="db", target="sb"), Edge(source="sb", target="ob"),
            Edge(source="de", target="se"), Edge(source="se", target="oe"),
        ],
    )


def _histories():
    return {
        "BTC/USDT": make_candles([5, 5, 5, 5, 5, 9, 9, 9]),  # buy cross ~bar 5
        "ETH/USDT": make_candles([5, 5, 5, 5, 5, 5, 5, 5]),  # never crosses
    }


def test_two_symbol_backtest_runs_and_is_deterministic():
    g, h = _two_symbol_graph(), _histories()
    r1 = run_workflow_backtest(g, h, starting_cash=100_000.0, market=MarketKind.crypto, cost_model=CostModel.zero())
    r2 = run_workflow_backtest(g, _histories(), starting_cash=100_000.0, market=MarketKind.crypto, cost_model=CostModel.zero())
    assert r1.symbols == ["BTC/USDT", "ETH/USDT"]
    assert len(r1.equity_curve) >= 2
    assert r1.final_equity == r2.final_equity  # deterministic
    # at least one buy signal recorded for BTC with a non-empty trace.
    # The key MUST be `trace_json` — the same name the DB column, the GET /runs/{id}/signals
    # endpoint, and the frontend WorkflowSignalDTO use — so the POST response and the persisted
    # rows are one consistent shape (a mismatch crashed the trace drawer on a fresh backtest).
    btc_buys = [s for s in r1.signals if s["symbol"] == "BTC/USDT" and s["action"] == "buy"]
    assert btc_buys and btc_buys[0]["trace_json"]
    assert "trace" not in btc_buys[0]


def test_signals_recorded_every_bar_per_order_node():
    g, h = _two_symbol_graph(), _histories()
    r = run_workflow_backtest(g, h, cost_model=CostModel.zero())
    # 2 order nodes x (timeline-1) decision bars -> records for every bar incl. hold
    bars = len(next(iter(h.values()))) - 1
    assert len(r.signals) == 2 * bars
    assert {s["action"] for s in r.signals} <= {"buy", "sell", "hold"}


def test_genuine_node_error_fails_loud():
    # Uses an unknown strategy so the error message is "unknown strategy 'nonexistent_strategy'..."
    # which does NOT contain any warmup keyword — proving real errors still raise (fail loud).
    g = WorkflowGraph(
        nodes=[
            NodeConfig(id="d", type=NodeType.data_source, params={"symbol": "BTC/USDT"}),
            NodeConfig(id="s", type=NodeType.strategy, params={"name": "nonexistent_strategy"}),
            NodeConfig(id="o", type=NodeType.order, params={}),
        ],
        edges=[Edge(source="d", target="s"), Edge(source="s", target="o")],
    )
    h = {"BTC/USDT": make_candles([1, 2, 3, 4, 5])}
    with pytest.raises(ValueError, match="workflow failed"):
        run_workflow_backtest(g, h, cost_model=CostModel.zero())


def test_ai_bar_cap_fails_loud():
    g = WorkflowGraph(
        nodes=[
            NodeConfig(id="d", type=NodeType.data_source, params={"symbol": "BTC/USDT"}),
            NodeConfig(id="a", type=NodeType.ai_signal, params={}),
            NodeConfig(id="o", type=NodeType.order, params={}),
        ],
        edges=[Edge(source="d", target="a"), Edge(source="a", target="o")],
    )
    h = {"BTC/USDT": make_candles(list(range(1, 12)))}  # 11 bars
    with pytest.raises(ValueError, match="ai_signal"):
        run_workflow_backtest(g, h, ai_bar_cap=5, cost_model=CostModel.zero())
