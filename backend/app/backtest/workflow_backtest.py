"""Drive a WorkflowGraph over history as a shared-cash multi-asset portfolio backtest.

Reuses run_workflow per bar via a BacktestContext (data_source slices history, order records
intent, risk_exit reads simulated positions). The per-bar order-node signals feed a PortfolioSim
with equal-weight rebalancing and next-bar-open fills, then metrics.py produces the report.
"""

from __future__ import annotations

from pydantic import Field

from app.backtest import metrics
from app.backtest.engine import BacktestResult, EquityPoint
from app.backtest.portfolio import PortfolioSim, _Pos
from app.config import settings
from app.schemas import Candle, MarketKind, SignalAction
from app.trading.costs import CostModel
from app.workflow.backtest_context import BacktestContext, SimPos
from app.workflow.engine import run_workflow
from app.workflow.nodes import RunContext
from app.workflow.run_store import build_trace, resolve_order_symbol
from app.workflow.schema import NodeType, WorkflowGraph


class WorkflowBacktestResult(BacktestResult):
    symbols: list[str] = Field(default_factory=list)
    signals: list[dict] = Field(default_factory=list)


def _aligned_timeline(histories: dict[str, list[Candle]]) -> list:
    """Timestamps present in EVERY symbol's history (intersection), sorted ascending."""
    common: set | None = None
    for hist in histories.values():
        ts = {c.timestamp for c in hist}
        common = ts if common is None else (common & ts)
    return sorted(common or set())


def run_workflow_backtest(
    graph: WorkflowGraph,
    histories: dict[str, list[Candle]],
    *,
    starting_cash: float = 100_000.0,
    market: MarketKind = MarketKind.crypto,
    timeframe: str = "1h",
    cost_model: CostModel | None = None,
    ai_bar_cap: int = 200,
    risk_free_rate: float | None = None,
) -> WorkflowBacktestResult:
    order_nodes = [n for n in graph.nodes if n.type == NodeType.order]
    if not order_nodes:
        raise ValueError("workflow backtest requires at least one order node")
    order_symbol = {n.id: resolve_order_symbol(graph, n.id) for n in order_nodes}
    symbols = sorted(set(order_symbol.values()))

    for sym in symbols:
        if sym not in histories or len(histories[sym]) < 2:
            raise ValueError(f"insufficient history for symbol {sym!r} (need >= 2 bars)")

    timeline = _aligned_timeline({s: histories[s] for s in symbols})
    if len(timeline) < 2:
        raise ValueError("aligned timeline across symbols has < 2 bars (timeframe mismatch?)")

    has_ai = any(n.type == NodeType.ai_signal for n in graph.nodes)
    if has_ai and len(timeline) > ai_bar_cap:
        raise ValueError(
            f"ai_signal backtest exceeds bar cap: {len(timeline)} bars > {ai_bar_cap}; "
            "shorten the range or remove the AI node"
        )

    costs = cost_model or CostModel.from_settings()
    rf = risk_free_rate if risk_free_rate is not None else settings.backtest_risk_free_rate

    # Index each symbol's candles by timestamp so a global bar maps to per-symbol indices.
    by_ts = {s: {c.timestamp: i for i, c in enumerate(histories[s])} for s in symbols}

    sim = PortfolioSim(starting_cash=starting_cash, market=market, cost_model=costs)
    bt = BacktestContext(histories=histories, positions={})
    for nid, sym in order_symbol.items():
        bt.set_order_symbol(nid, sym)

    equity_curve: list[EquityPoint] = []
    peak = starting_cash
    max_dd = 0.0
    bars_in_pos = 0
    signals: list[dict] = []
    desired_long: dict[str, bool] = {s: False for s in symbols}
    pending_targets: dict[str, float] | None = None

    # Bar 0 is the seed bar: no prior pending fill, no signal recorded. Decision bars start at 1.
    # This mirrors run_backtest's range(1, len(candles)) convention so signal count =
    # (len(timeline) - 1) * num_order_nodes and warmup failures are naturally avoided once
    # enough candles accumulate. Early bars that still lack enough candles for the strategy
    # are treated as all-hold (recoverable "not enough data", not a real error).
    for bar_i in range(1, len(timeline)):
        ts = timeline[bar_i]
        ts_iso = ts.isoformat()
        opens = {s: histories[s][by_ts[s][ts]].open for s in symbols}
        closes = {s: histories[s][by_ts[s][ts]].close for s in symbols}

        # 1) Execute the previous bar's decision at THIS bar's opens.
        if pending_targets is not None:
            sim.rebalance(pending_targets, opens, ts_iso)
            pending_targets = None

        # 2) Run the graph on data through close[bar_i]; collect order-node signals + traces.
        # Map the global bar to each symbol's local index for the window slice.
        bt.histories = {s: histories[s][: by_ts[s][ts] + 1] for s in symbols}
        bt.positions = {
            s: SimPos(quantity=sim.positions.get(s, _Pos()).quantity, avg_price=sim.positions.get(s, _Pos()).avg_price)
            for s in symbols
        }
        bt.orders_this_bar = []
        ctx = RunContext()
        ctx.backtest = bt
        # current_index now indexes the per-symbol sliced histories' last bar
        bt.current_index = max(len(v) - 1 for v in bt.histories.values())
        result = run_workflow(graph, ctx=ctx)
        # Warmup: strategy raises ValueError when not enough candles; treat as all-hold.
        # Real errors (cycle, unknown node, etc.) still fail loud.
        if result.status != "ok":
            # FRAGILE: matches on human-readable error strings from strategy.generate().
            # Deliberately a narrow allowlist of insufficient-data phrases only — do NOT
            # broaden to swallow other errors. Each entry corresponds to a specific built-in:
            #   "needs at least"  — ma_cross, rsi, bollinger (primary), spec
            #   "not enough"      — generic guard (future strategies)
            #   "insufficient"    — spec indicator warmup ("insufficient data for its window")
            #   "needs more candles" — macd ("macd needs more candles before signal/line are defined")
            #   "not yet defined" — bollinger secondary path ("bollinger bands not yet defined")
            # TODO(follow-up): strategies should raise a structured WarmupError preserved through
            # the engine so this string-matching guard can be replaced with isinstance checks.
            warmup_keywords = ("needs at least", "not enough", "insufficient", "needs more candles", "not yet defined")
            if result.error and any(kw in result.error for kw in warmup_keywords):
                pass  # treat early-bar strategy warmup as all-hold, continue
            else:
                raise ValueError(f"workflow failed during backtest at bar {bar_i}: {result.error}")

        # Record EVERY order node's signal this bar (incl. hold) with its ancestor trace.
        emitted = {oid: sig for (oid, _sym, sig) in bt.orders_this_bar}
        for nid in order_symbol:
            sig = emitted.get(nid)
            action = sig.action.value if sig else SignalAction.hold.value
            sym = order_symbol[nid]
            signals.append(
                {
                    "order_node_id": nid,
                    "symbol": sym,
                    "timestamp": ts_iso,
                    "bar_index": bar_i,
                    "action": action,
                    "confidence": sig.confidence if sig else 0.5,
                    "price": closes[sym],
                    "trace": build_trace(graph, nid, ctx.node_outputs),
                }
            )
            # Update desired state: buy -> long, sell -> flat, hold -> unchanged.
            if action == SignalAction.buy.value:
                desired_long[sym] = True
            elif action == SignalAction.sell.value:
                desired_long[sym] = False

        # 3) Equal-weight targets become the NEXT bar's pending fills (no look-ahead).
        # Final bar: decision is recorded above but cannot fill — there is no next-bar open.
        # Mirrors run_backtest's convention where the last bar signal is captured but not executed.
        if bar_i < len(timeline) - 1:
            longs = {s for s, on in desired_long.items() if on}
            pending_targets = sim.target_quantities(longs, closes)

        # 4) Mark-to-market at close[bar_i].
        eq = sim.equity(closes)
        equity_curve.append(EquityPoint(timestamp=ts_iso, equity=eq))
        if any(sim.positions.get(s, _Pos()).quantity > 0 for s in symbols):
            bars_in_pos += 1
        peak = max(peak, eq)
        if peak > 0:
            max_dd = max(max_dd, (peak - eq) / peak * 100)

    return _assemble_result(
        sim, equity_curve, starting_cash, timeframe, rf, bars_in_pos, max_dd, symbols, signals, histories
    )


def _assemble_result(
    sim, equity_curve, starting_cash, timeframe, rf, bars_in_pos, max_dd, symbols, signals, histories
) -> WorkflowBacktestResult:
    final_equity = equity_curve[-1].equity if equity_curve else starting_cash
    pnls = [t.pnl for t in sim.trades]
    win_pnls = [p for p in pnls if p > 0]
    loss_pnls = [p for p in pnls if p < 0]
    equities = [starting_cash] + [p.equity for p in equity_curve]
    returns = [equities[k] / equities[k - 1] - 1 for k in range(1, len(equities)) if equities[k - 1] > 0]
    ppy = metrics.periods_per_year(timeframe)
    cagr = metrics.cagr(starting_cash, final_equity, len(returns), ppy)
    # buy & hold of an equal-weight basket of all symbols, first->last close
    bh = 0.0
    for s in symbols:
        first, last = histories[s][0].close, histories[s][-1].close
        if first > 0:
            bh += (last / first - 1) / len(symbols)
    return WorkflowBacktestResult(
        starting_cash=starting_cash,
        final_equity=final_equity,
        total_return_pct=(final_equity / starting_cash - 1) * 100,
        buy_hold_return_pct=bh * 100,
        num_trades=len(sim.trades),
        wins=len(win_pnls),
        win_rate=(len(win_pnls) / len(sim.trades) * 100) if sim.trades else 0.0,
        max_drawdown_pct=max_dd,
        cagr=cagr,
        annualized_volatility=metrics.annualized_volatility(returns, ppy),
        sharpe=metrics.sharpe_ratio(returns, ppy, rf),
        sortino=metrics.sortino_ratio(returns, ppy, rf),
        calmar=metrics.calmar_ratio(cagr, max_dd),
        profit_factor=metrics.profit_factor(pnls),
        avg_win=(sum(win_pnls) / len(win_pnls)) if win_pnls else 0.0,
        avg_loss=(sum(loss_pnls) / len(loss_pnls)) if loss_pnls else 0.0,
        exposure_pct=(bars_in_pos / len(equity_curve) * 100) if equity_curve else 0.0,
        max_consecutive_losses=metrics.max_consecutive_losses(pnls),
        turnover=(sim.traded_value / starting_cash) if starting_cash > 0 else 0.0,
        trades=sim.trades,
        equity_curve=equity_curve,
        symbols=symbols,
        signals=signals,
    )
