# app/tests/test_backtest_context.py
from __future__ import annotations

from app.schemas import MarketKind, Signal, SignalAction
from app.tests.helpers import make_candles
from app.workflow import nodes
from app.workflow.backtest_context import BacktestContext, SimPos
from app.workflow.nodes import RunContext
from app.workflow.schema import NodeConfig, NodeType


def test_data_source_returns_window_slice():
    hist = {"BTC/USDT": make_candles([1, 2, 3, 4, 5])}
    bt = BacktestContext(histories=hist, positions={})
    bt.current_index = 2
    ctx = RunContext()
    ctx.backtest = bt
    node = NodeConfig(id="d", type=NodeType.data_source, params={"symbol": "BTC/USDT"})
    out = nodes._run_data_source(node, [], ctx)
    assert [c.close for c in out] == [1, 2, 3]


def test_order_records_signal_instead_of_executing():
    bt = BacktestContext(histories={"BTC/USDT": make_candles([1])}, positions={})
    bt.current_index = 0
    bt.set_order_symbol("o", "BTC/USDT")  # orchestrator pre-resolves the symbol per order node
    ctx = RunContext()
    ctx.backtest = bt
    node = NodeConfig(id="o", type=NodeType.order, params={})
    sig = Signal(action=SignalAction.buy, confidence=0.7)
    assert nodes._run_order(node, [sig], ctx) is None
    assert bt.orders_this_bar == [("o", "BTC/USDT", sig)]


def test_risk_exit_reads_simulated_position():
    hist = {"BTC/USDT": make_candles([100, 100, 80])}  # -20% from avg 100
    bt = BacktestContext(histories=hist, positions={"BTC/USDT": SimPos(quantity=1.0, avg_price=100.0)})
    bt.current_index = 2
    ctx = RunContext()
    ctx.backtest = bt
    node = NodeConfig(
        id="r",
        type=NodeType.risk_exit,
        params={"symbol": "BTC/USDT", "market": "crypto", "stop_loss_pct": 10},
    )
    out = nodes._run_risk_exit(node, [bt.window_for("BTC/USDT")], ctx)
    assert out.action == SignalAction.sell
