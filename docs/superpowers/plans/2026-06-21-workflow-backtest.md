# Workflow Historical Backtest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run any `WorkflowGraph` as a multi-asset shared-cash portfolio backtest over historical data, persist every workflow run (backtest + live/paper) with per-signal node-by-node traces, and surface signals as clickable chart markers with a run-history browser.

**Architecture:** Reuse `run_workflow` driven once per historical bar through a new `BacktestContext` threaded into `RunContext`. Only `data_source` (returns a history slice), `order` (records intent), and `risk_exit` (reads simulated position) branch on it; all other node logic is unchanged so backtest signals match live. A pure `PortfolioSim` applies equal-weight rebalancing with next-bar-open fills and transaction costs. A `run_store` persists runs + signal traces to two new SQLModel tables, consumed by a unified history API and frontend.

**Tech Stack:** Python 3.11 / FastAPI / SQLModel / pydantic (backend); Next.js 14 App Router / TypeScript / lightweight-charts / @xyflow/react (frontend). Tests: pytest (backend); `npm run build` + manual verification (frontend — no test runner).

## Global Constraints

- **Fail loud everywhere**: missing data, external errors, validation failures must raise/return an explicit error, never be silently skipped (mirror `workflow/engine.py` + `RiskGuard`).
- **Transaction costs ON by default**: every simulated fill goes through `CostModel.from_settings()`; `CostModel.zero()` only in explicit gross-vs-net tests.
- **No look-ahead**: a signal decided on `close[i]` fills at the next bar's `open[i+1]` (existing M0.2 convention).
- **Paper is the safe default**; the live order path must not change behavior — persistence is additive (write records after execution).
- **Indicators use the `ta` library** (already in deps); do not add `pandas-ta`.
- **Backend tests live in** `app/tests/`; run from `backend/` with the venv active (`pytest -q`).
- **AI bar cap default = 200** bars when a graph contains an `ai_signal` node.
- **Snake_case** Python, existing file/module conventions; surgical changes only.

---

## File Structure

**Backend (new):**
- `app/workflow/backtest_context.py` — `BacktestContext` (per-bar window, simulated position read, signal/order recorder).
- `app/backtest/portfolio.py` — `PortfolioSim` (cash + positions, equal-weight targets, fills with costs, equity, trades).
- `app/backtest/workflow_backtest.py` — orchestrator: validate graph, build timeline, bar loop, metrics, result.
- `app/workflow/run_store.py` — persist `WorkflowRun` + `WorkflowSignal` (+ ancestor trace) for backtest and live.

**Backend (modified):**
- `app/workflow/nodes.py` — `RunContext` gains `backtest` + `node_outputs`; `data_source`/`order`/`risk_exit` branch on `ctx.backtest`.
- `app/workflow/engine.py` — `run_workflow` accepts an optional `ctx` and records each node's raw output into `ctx.node_outputs`.
- `app/models.py` — `WorkflowRun`, `WorkflowSignal` tables.
- `app/api/backtest.py` — `POST /api/backtest/workflow`.
- `app/api/workflows.py` — live `run_ad_hoc`/`run_saved` persist via `run_store`; new run-history GET endpoints.

**Frontend (modified):**
- `frontend/lib/api.ts` — types + client methods for workflow backtest + run history.
- `frontend/components/` — signal-marker chart + trace drawer + run-history list (exact files in Task 11/12).
- workflow / backtest page under `frontend/app/(rooms)/trading-room/` — wire in the new UI.

---

## Task 1: Engine captures raw per-node outputs

**Files:**
- Modify: `app/workflow/nodes.py` (`RunContext.__init__`)
- Modify: `app/workflow/engine.py:58-100` (`run_workflow`)
- Test: `app/tests/test_workflow_trace.py` (create)

**Interfaces:**
- Consumes: existing `RunContext`, `run_workflow(graph, session=None, run_id=None)`.
- Produces: `RunContext.node_outputs: dict[str, Any]`; `RunContext.backtest: Any | None`; `run_workflow(graph, session=None, run_id=None, ctx: RunContext | None = None) -> RunResult` — when `ctx` is passed the engine uses it (and leaves `node_outputs` populated for the caller); otherwise behavior is unchanged.

- [ ] **Step 1: Write the failing test**

```python
# app/tests/test_workflow_trace.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest app/tests/test_workflow_trace.py -q`
Expected: FAIL — `run_workflow() got an unexpected keyword argument 'ctx'`.

- [ ] **Step 3: Implement**

In `app/workflow/nodes.py`, extend `RunContext.__init__` (after `self.scratch = {}`):

```python
        # Raw per-node outputs for this run (node_id -> value), for tracing/backtest.
        self.node_outputs: dict[str, Any] = {}
        # When set, data_source/order/risk_exit run in backtest mode (see BacktestContext).
        self.backtest: Any | None = None
```

In `app/workflow/engine.py`, change the signature and context creation:

```python
def run_workflow(
    graph: WorkflowGraph, session=None, run_id: str | None = None, ctx: RunContext | None = None
) -> RunResult:
```

Replace `ctx = RunContext(session=session, run_id=run_id)` with:

```python
    if ctx is None:
        ctx = RunContext(session=session, run_id=run_id)
```

After `outputs[node.id] = result` (line ~93) add:

```python
        ctx.node_outputs[node.id] = result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest app/tests/test_workflow_trace.py app/tests/test_workflow.py -q`
Expected: PASS (new test + existing workflow tests unaffected).

- [ ] **Step 5: Commit**

```bash
git add app/workflow/nodes.py app/workflow/engine.py app/tests/test_workflow_trace.py
git commit -m "feat(workflow): engine records raw per-node outputs via optional ctx

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Persistence tables (WorkflowRun, WorkflowSignal)

**Files:**
- Modify: `app/models.py` (append two tables)
- Test: `app/tests/test_workflow_run_models.py` (create)

**Interfaces:**
- Produces: `WorkflowRun(id, run_id, kind, workflow_id, graph_json, market, symbols, timeframe, starting_cash, params_json, metrics_json, equity_curve_json, trades_json, status, created_at)`; `WorkflowSignal(id, run_id, order_node_id, symbol, timestamp, bar_index, action, confidence, price, trace_json, created_at)`. JSON columns use `sa_column=Column(JSON)`.

- [ ] **Step 1: Write the failing test**

```python
# app/tests/test_workflow_run_models.py
"""WorkflowRun + WorkflowSignal persist and round-trip."""

from __future__ import annotations

from sqlmodel import Session, select

from app.db import engine
from app.models import WorkflowRun, WorkflowSignal


def test_workflow_run_and_signal_roundtrip():
    with Session(engine) as s:
        run = WorkflowRun(
            run_id="abc123",
            kind="backtest",
            graph_json={"nodes": [], "edges": []},
            market="crypto",
            symbols=["BTC/USDT", "ETH/USDT"],
            timeframe="1h",
            starting_cash=100_000.0,
            params_json={"limit": 500},
            metrics_json={"total_return_pct": 1.5},
            equity_curve_json=[{"timestamp": "t", "equity": 100.0}],
            trades_json=[],
            status="ok",
        )
        s.add(run)
        s.commit()
        s.refresh(run)
        s.add(
            WorkflowSignal(
                run_id=run.id,
                order_node_id="o",
                symbol="BTC/USDT",
                timestamp="2024-01-01T00:00:00+00:00",
                bar_index=3,
                action="buy",
                confidence=0.8,
                price=9.0,
                trace_json=[{"node_id": "s", "type": "strategy", "summary": {"signal": {"action": "buy"}}}],
            )
        )
        s.commit()

        got = s.exec(select(WorkflowSignal).where(WorkflowSignal.run_id == run.id)).all()
        assert len(got) == 1
        assert got[0].action == "buy"
        assert got[0].trace_json[0]["node_id"] == "s"
        assert run.symbols == ["BTC/USDT", "ETH/USDT"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest app/tests/test_workflow_run_models.py -q`
Expected: FAIL — `ImportError: cannot import name 'WorkflowRun'`.

- [ ] **Step 3: Implement**

Append to `app/models.py`:

```python
class WorkflowRun(SQLModel, table=True):
    """One workflow execution — backtest or live/paper (M-backtest).

    Unified run record. For backtests it carries the portfolio metrics/equity/trades as JSON; for
    live/paper triggers those stay null and only the per-signal rows matter.
    """

    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(index=True)  # the engine's logical run id (idempotency key)
    kind: str  # "backtest" | "live" | "paper"
    workflow_id: int | None = Field(default=None, index=True)
    graph_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    market: str = ""
    symbols: list = Field(default_factory=list, sa_column=Column(JSON))
    timeframe: str = ""
    starting_cash: float | None = Field(default=None)
    params_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    metrics_json: dict | None = Field(default=None, sa_column=Column(JSON))
    equity_curve_json: list | None = Field(default=None, sa_column=Column(JSON))
    trades_json: list | None = Field(default=None, sa_column=Column(JSON))
    status: str = "ok"  # "ok" | "error"
    created_at: datetime = Field(default_factory=_now, index=True)


class WorkflowSignal(SQLModel, table=True):
    """One emitted signal at an order node, with the node-by-node trace that produced it."""

    id: int | None = Field(default=None, primary_key=True)
    run_id: int = Field(index=True, foreign_key="workflowrun.id")
    order_node_id: str
    symbol: str = Field(index=True)
    timestamp: str  # bar timestamp ISO8601 (string keeps it portable across markets)
    bar_index: int | None = Field(default=None)
    action: str  # "buy" | "sell" | "hold"
    confidence: float = 0.5
    price: float = 0.0  # close at the signal bar
    trace_json: list = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_now)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest app/tests/test_workflow_run_models.py -q`
Expected: PASS (conftest drops+recreates the schema, so the new tables exist).

- [ ] **Step 5: Commit**

```bash
git add app/models.py app/tests/test_workflow_run_models.py
git commit -m "feat(models): WorkflowRun + WorkflowSignal tables for unified run history

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: run_store — build traces + persist runs/signals

**Files:**
- Create: `app/workflow/run_store.py`
- Test: `app/tests/test_run_store.py` (create)

**Interfaces:**
- Consumes: `RunContext.node_outputs`, `WorkflowGraph`, `WorkflowRun`/`WorkflowSignal`, engine `_summarize`.
- Produces:
  - `order_node_ancestors(graph: WorkflowGraph, order_node_id: str) -> list[str]` — ids of all transitive predecessors of an order node, in topological order.
  - `build_trace(graph, order_node_id, node_outputs) -> list[dict]` — `[{"node_id","type","summary"}]` for each ancestor, `summary` via engine `_summarize`.
  - `resolve_order_symbol(graph, order_node_id) -> str` — the unique `symbol` among the order node's ancestor `data_source` nodes (or the order node's own `params["symbol"]` if set); raises `ValueError` if zero or >1 distinct symbols.
  - `persist_workflow_run(session, *, run_id, kind, graph, market, symbols, timeframe, starting_cash, params, metrics, equity_curve, trades, status, signals) -> int` — writes one `WorkflowRun` + the given `signals` (list of dicts with keys order_node_id, symbol, timestamp, bar_index, action, confidence, price, trace) and returns the run's id.

- [ ] **Step 1: Write the failing test**

```python
# app/tests/test_run_store.py
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
                    "trace": [{"node_id": "s", "type": "strategy", "summary": {}}],
                }
            ],
        )
        rows = s.exec(select(WorkflowSignal).where(WorkflowSignal.run_id == run_id)).all()
        assert len(rows) == 1 and rows[0].action == "buy"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest app/tests/test_run_store.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.workflow.run_store'`.

- [ ] **Step 3: Implement**

```python
# app/workflow/run_store.py
"""Persist workflow runs + per-signal node traces (unified across backtest and live/paper)."""

from __future__ import annotations

from typing import Any

from sqlmodel import Session

from app.models import WorkflowRun, WorkflowSignal
from app.workflow.engine import _summarize
from app.workflow.schema import NodeType, WorkflowGraph


def _predecessors(graph: WorkflowGraph) -> dict[str, list[str]]:
    preds: dict[str, list[str]] = {n.id: [] for n in graph.nodes}
    for e in graph.edges:
        preds[e.target].append(e.source)
    return preds


def order_node_ancestors(graph: WorkflowGraph, order_node_id: str) -> list[str]:
    """All transitive predecessors of an order node, returned in topological (source-first) order."""
    preds = _predecessors(graph)
    seen: set[str] = set()
    stack = list(preds.get(order_node_id, []))
    while stack:
        nid = stack.pop()
        if nid in seen:
            continue
        seen.add(nid)
        stack.extend(preds.get(nid, []))
    # topological-ish: keep graph node declaration order among the ancestor set
    return [n.id for n in graph.nodes if n.id in seen]


def build_trace(graph: WorkflowGraph, order_node_id: str, node_outputs: dict[str, Any]) -> list[dict]:
    by_id = {n.id: n for n in graph.nodes}
    trace: list[dict] = []
    for nid in order_node_ancestors(graph, order_node_id):
        node = by_id[nid]
        trace.append(
            {"node_id": nid, "type": node.type.value, "summary": _summarize(node_outputs.get(nid))}
        )
    return trace


def resolve_order_symbol(graph: WorkflowGraph, order_node_id: str) -> str:
    by_id = {n.id: n for n in graph.nodes}
    own = by_id[order_node_id].params.get("symbol")
    if own:
        return str(own)
    symbols = {
        by_id[nid].params.get("symbol")
        for nid in order_node_ancestors(graph, order_node_id)
        if by_id[nid].type == NodeType.data_source and by_id[nid].params.get("symbol")
    }
    if len(symbols) != 1:
        raise ValueError(
            f"order node '{order_node_id}' must resolve to exactly one symbol "
            f"(found {sorted(s for s in symbols if s)}); set its 'symbol' param"
        )
    return str(next(iter(symbols)))


def persist_workflow_run(
    session: Session,
    *,
    run_id: str,
    kind: str,
    graph: WorkflowGraph,
    market: str,
    symbols: list[str],
    timeframe: str,
    starting_cash: float | None,
    params: dict,
    metrics: dict | None,
    equity_curve: list | None,
    trades: list | None,
    status: str,
    signals: list[dict],
) -> int:
    run = WorkflowRun(
        run_id=run_id,
        kind=kind,
        graph_json=graph.model_dump(mode="json"),
        market=market,
        symbols=symbols,
        timeframe=timeframe,
        starting_cash=starting_cash,
        params_json=params,
        metrics_json=metrics,
        equity_curve_json=equity_curve,
        trades_json=trades,
        status=status,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    for sig in signals:
        session.add(
            WorkflowSignal(
                run_id=run.id,
                order_node_id=sig["order_node_id"],
                symbol=sig["symbol"],
                timestamp=sig["timestamp"],
                bar_index=sig.get("bar_index"),
                action=sig["action"],
                confidence=sig.get("confidence", 0.5),
                price=sig.get("price", 0.0),
                trace_json=sig.get("trace", []),
            )
        )
    session.commit()
    return run.id
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest app/tests/test_run_store.py -q`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add app/workflow/run_store.py app/tests/test_run_store.py
git commit -m "feat(workflow): run_store — ancestor traces, symbol resolution, run persistence

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: PortfolioSim — equal-weight shared-cash simulation

**Files:**
- Create: `app/backtest/portfolio.py`
- Test: `app/tests/test_portfolio_sim.py` (create)

**Interfaces:**
- Consumes: `CostModel`, `MarketKind`, `OrderSide`, `backtest.engine.Trade`.
- Produces:
  - `PortfolioSim(starting_cash: float, market: MarketKind, cost_model: CostModel)`.
  - `.positions: dict[str, Position]` where `Position` is a small dataclass `(quantity: float, avg_price: float, entry_time: str, entry_fee: float)`.
  - `.equity(prices: dict[str, float]) -> float` — cash + Σ qty·price.
  - `.target_quantities(desired_long: set[str], prices: dict[str, float]) -> dict[str, float]` — equal-weight: each desired-long symbol targets `(equity/N)/price`; others target 0.
  - `.rebalance(targets: dict[str, float], prices: dict[str, float], ts: str) -> None` — trade the delta to each target at `prices[symbol]` through the cost model (buys raise cash outlay incl. fee; sells realize a `Trade`); never shorts (targets are ≥0). Appends to `.trades` and `.traded_value`.
  - `.trades: list[Trade]`.

- [ ] **Step 1: Write the failing test**

```python
# app/tests/test_portfolio_sim.py
from __future__ import annotations

from app.backtest.portfolio import PortfolioSim
from app.schemas import MarketKind
from app.trading.costs import CostModel


def _sim() -> PortfolioSim:
    return PortfolioSim(starting_cash=100_000.0, market=MarketKind.crypto, cost_model=CostModel.zero())


def test_equal_weight_two_symbols_split_5050():
    sim = _sim()
    prices = {"BTC/USDT": 100.0, "ETH/USDT": 50.0}
    targets = sim.target_quantities({"BTC/USDT", "ETH/USDT"}, prices)
    # 100k / 2 = 50k each -> 500 BTC, 1000 ETH
    assert round(targets["BTC/USDT"], 6) == 500.0
    assert round(targets["ETH/USDT"], 6) == 1000.0


def test_rebalance_buys_then_exit_to_cash():
    sim = _sim()
    prices = {"BTC/USDT": 100.0}
    sim.rebalance({"BTC/USDT": 500.0}, prices, ts="t0")  # deploy 50k? no — single symbol target=500
    assert round(sim.positions["BTC/USDT"].quantity, 6) == 500.0
    assert round(sim.equity(prices), 2) == 100_000.0  # zero-cost: equity unchanged
    sim.rebalance({"BTC/USDT": 0.0}, {"BTC/USDT": 120.0}, ts="t1")  # exit at higher price
    assert sim.positions["BTC/USDT"].quantity == 0.0
    assert len(sim.trades) == 1
    assert round(sim.trades[0].pnl, 2) == round((120.0 - 100.0) * 500.0, 2)


def test_single_active_long_targets_full_equity():
    sim = _sim()
    prices = {"BTC/USDT": 100.0, "ETH/USDT": 50.0}
    targets = sim.target_quantities({"BTC/USDT"}, prices)  # only BTC long -> 100% to BTC
    assert round(targets["BTC/USDT"], 6) == 1000.0
    assert targets["ETH/USDT"] == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest app/tests/test_portfolio_sim.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.backtest.portfolio'`.

- [ ] **Step 3: Implement**

```python
# app/backtest/portfolio.py
"""Shared-cash multi-asset portfolio simulation with equal-weight targets (M-backtest).

One cash pool, long/flat only. Equal-weight: every symbol currently desired-long targets an equal
fraction (1/N) of current portfolio equity; rebalancing trades the delta to each target through the
CostModel. Mirrors the single-asset engine's cost handling so net numbers stay honest.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.backtest.engine import Trade
from app.schemas import MarketKind, OrderSide
from app.trading.costs import CostModel

_QTY_EPS = 1e-9


@dataclass
class _Pos:
    quantity: float = 0.0
    avg_price: float = 0.0
    entry_time: str = ""
    entry_fee: float = 0.0


@dataclass
class PortfolioSim:
    starting_cash: float
    market: MarketKind
    cost_model: CostModel
    cash: float = field(init=False)
    positions: dict[str, _Pos] = field(default_factory=dict)
    trades: list[Trade] = field(default_factory=list)
    traded_value: float = 0.0

    def __post_init__(self) -> None:
        self.cash = self.starting_cash

    def equity(self, prices: dict[str, float]) -> float:
        held = sum(p.quantity * prices.get(sym, p.avg_price) for sym, p in self.positions.items())
        return self.cash + held

    def target_quantities(self, desired_long: set[str], prices: dict[str, float]) -> dict[str, float]:
        equity = self.equity(prices)
        longs = [s for s in desired_long if prices.get(s, 0.0) > 0]
        n = len(longs)
        targets: dict[str, float] = {sym: 0.0 for sym in prices}
        if n == 0:
            return targets
        per = equity / n
        for sym in longs:
            targets[sym] = per / prices[sym]
        return targets

    def rebalance(self, targets: dict[str, float], prices: dict[str, float], ts: str) -> None:
        # Sells first (free up cash), then buys, so capital recycles within the bar.
        for sym, target in sorted(targets.items(), key=lambda kv: kv[1]):
            price = prices.get(sym)
            if price is None or price <= 0:
                continue
            pos = self.positions.setdefault(sym, _Pos())
            delta = target - pos.quantity
            if abs(delta) <= _QTY_EPS:
                continue
            if delta > 0:
                self._buy(sym, pos, delta, price, ts)
            else:
                self._sell(sym, pos, -delta, price, ts)

    def _buy(self, sym: str, pos: _Pos, qty: float, price: float, ts: str) -> None:
        fill = self.cost_model.slippage_price(OrderSide.buy, price)
        fee = self.cost_model.fill_cost(self.market, OrderSide.buy, fill, qty).total
        outlay = qty * fill + fee
        if outlay > self.cash:  # never let cash go negative; scale the buy to fit
            scale = self.cash / outlay if outlay > 0 else 0.0
            qty *= scale
            fee = self.cost_model.fill_cost(self.market, OrderSide.buy, fill, qty).total
            outlay = qty * fill + fee
        if qty <= _QTY_EPS:
            return
        # weighted-average cost basis across the combined position
        new_qty = pos.quantity + qty
        pos.avg_price = (pos.avg_price * pos.quantity + fill * qty) / new_qty if new_qty > 0 else 0.0
        if pos.quantity <= _QTY_EPS:
            pos.entry_time = ts
            pos.entry_fee = fee
        else:
            pos.entry_fee += fee
        pos.quantity = new_qty
        self.cash -= outlay
        self.traded_value += qty * fill

    def _sell(self, sym: str, pos: _Pos, qty: float, price: float, ts: str) -> None:
        qty = min(qty, pos.quantity)
        if qty <= _QTY_EPS:
            return
        fill = self.cost_model.slippage_price(OrderSide.sell, price)
        sell_cost = self.cost_model.fill_cost(self.market, OrderSide.sell, fill, qty).total
        self.cash += qty * fill - sell_cost
        self.traded_value += qty * fill
        gross = (fill - pos.avg_price) * qty
        # apportion the entry fee by the fraction of the position being closed
        frac = qty / pos.quantity if pos.quantity > 0 else 1.0
        entry_fee_share = pos.entry_fee * frac
        self.trades.append(
            Trade(
                entry_time=pos.entry_time,
                exit_time=ts,
                entry_price=pos.avg_price,
                exit_price=fill,
                quantity=qty,
                pnl=gross - entry_fee_share - sell_cost,
                gross_pnl=gross,
                cost=entry_fee_share + sell_cost,
                return_pct=(fill / pos.avg_price - 1) * 100 if pos.avg_price else 0.0,
            )
        )
        pos.quantity -= qty
        pos.entry_fee -= entry_fee_share
        if pos.quantity <= _QTY_EPS:
            pos.quantity = 0.0
            pos.avg_price = 0.0
            pos.entry_fee = 0.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest app/tests/test_portfolio_sim.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add app/backtest/portfolio.py app/tests/test_portfolio_sim.py
git commit -m "feat(backtest): PortfolioSim — equal-weight shared-cash multi-asset simulation

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: BacktestContext + node backtest branches

**Files:**
- Create: `app/workflow/backtest_context.py`
- Modify: `app/workflow/nodes.py` (`_run_data_source`, `_run_order`, `_run_risk_exit`)
- Test: `app/tests/test_backtest_context.py` (create)

**Interfaces:**
- Consumes: `Candle`, `Signal`, `PortfolioSim._Pos` semantics (only needs `quantity`/`avg_price`), `RunContext.backtest`.
- Produces:
  - `BacktestContext(histories: dict[str, list[Candle]], positions: dict[str, _Pos])` with:
    - `current_index: int` and `current_ts` set by the orchestrator each bar.
    - `window_for(symbol) -> list[Candle]` — `histories[symbol][: current_index + 1]`.
    - `position_for(symbol) -> tuple[float, float]` — `(quantity, avg_price)` from `positions` (0,0 if flat).
    - `record(order_node_id, symbol, signal)` — appends `(order_node_id, symbol, signal)` to `.orders_this_bar`.
    - `.orders_this_bar: list[tuple[str, str, Signal]]` (cleared by orchestrator per bar).
  - In `nodes.py`: when `ctx.backtest` is set, `_run_data_source` returns `ctx.backtest.window_for(symbol)`; `_run_order` records the (resolved) symbol+signal and returns `None`; `_run_risk_exit` reads the simulated position via `ctx.backtest.position_for(symbol)` instead of the broker.

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest app/tests/test_backtest_context.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.workflow.backtest_context'`.

- [ ] **Step 3: Implement**

Create `app/workflow/backtest_context.py`:

```python
# app/workflow/backtest_context.py
"""Per-bar context that makes data_source/order/risk_exit nodes replay over history."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas import Candle, Signal


@dataclass
class SimPos:
    quantity: float = 0.0
    avg_price: float = 0.0


@dataclass
class BacktestContext:
    histories: dict[str, list[Candle]]
    positions: dict[str, "SimPos"]
    current_index: int = 0
    orders_this_bar: list[tuple[str, str, Signal]] = field(default_factory=list)
    _order_symbols: dict[str, str] = field(default_factory=dict)

    @property
    def current_ts(self) -> str:
        any_hist = next(iter(self.histories.values()))
        return any_hist[self.current_index].timestamp.isoformat()

    def window_for(self, symbol: str) -> list[Candle]:
        hist = self.histories.get(symbol)
        if hist is None:
            raise ValueError(f"no backtest history loaded for symbol {symbol!r}")
        return hist[: self.current_index + 1]

    def position_for(self, symbol: str) -> SimPos:
        return self.positions.get(symbol, SimPos())

    def set_order_symbol(self, order_node_id: str, symbol: str) -> None:
        self._order_symbols[order_node_id] = symbol

    def order_symbol(self, order_node_id: str, fallback: str | None) -> str:
        sym = self._order_symbols.get(order_node_id) or fallback
        if not sym:
            raise ValueError(f"order node '{order_node_id}' has no resolved symbol for backtest")
        return sym

    def record(self, order_node_id: str, symbol: str, signal: Signal) -> None:
        self.orders_this_bar.append((order_node_id, symbol, signal))
```

In `app/workflow/nodes.py`, branch the three runners. `_run_data_source` — at the top of the body, before fetching:

```python
    symbol = p["symbol"]
    market = MarketKind(p.get("market", "crypto"))
    ctx.scratch["symbol"] = symbol
    ctx.scratch["market"] = market
    if ctx.backtest is not None:
        return ctx.backtest.window_for(symbol)
    candles = get_data_broker(market).get_ohlcv(
        symbol, p.get("timeframe", "1h"), int(p.get("limit", 100))
    )
    return candles
```

(Keep the existing `if "symbol" not in p` guard above this.)

`_run_order` — after `signal = _only_signal(inputs)` and the `hold` early-return, before broker logic:

```python
    if ctx.backtest is not None:
        symbol = ctx.backtest.order_symbol(node.id, p.get("symbol") or ctx.scratch.get("symbol"))
        ctx.backtest.record(node.id, symbol, signal)
        return None
```

(Place this right after computing `p = node.params`; reuse the existing `symbol` resolution below for the live path.)

`_run_risk_exit` — replace the broker position lookup with a backtest branch. After computing `symbol`, `market`, `stop_loss_pct`, `take_profit_pct`:

```python
    if ctx.backtest is not None:
        sim = ctx.backtest.position_for(symbol)
        held_qty, avg_price = sim.quantity, sim.avg_price
    else:
        broker = get_broker(market)
        position = next((pos for pos in broker.get_positions() if pos.symbol == symbol), None)
        held_qty = position.quantity if position else 0.0
        avg_price = position.avg_price if position else 0.0
    if held_qty <= 0 or avg_price <= 0:
        return Signal(action=SignalAction.hold, reason="no open position", source="risk_exit")
    pnl_pct = (price / avg_price - 1) * 100
```

(Then keep the existing stop-loss / take-profit / within-thresholds branches, which already reference `pnl_pct`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest app/tests/test_backtest_context.py app/tests/test_workflow.py app/tests/test_risk_exit.py -q`
Expected: PASS — new tests pass and existing live-path workflow/risk_exit tests are unaffected (they never set `ctx.backtest`).

- [ ] **Step 5: Commit**

```bash
git add app/workflow/backtest_context.py app/workflow/nodes.py app/tests/test_backtest_context.py
git commit -m "feat(workflow): BacktestContext + data_source/order/risk_exit backtest branches

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Workflow backtest orchestrator

**Files:**
- Create: `app/backtest/workflow_backtest.py`
- Test: `app/tests/test_workflow_backtest.py` (create)

**Interfaces:**
- Consumes: `run_workflow`, `RunContext`, `BacktestContext`/`SimPos`, `PortfolioSim`, `run_store.resolve_order_symbol`/`build_trace`, `metrics`, `CostModel`, `BacktestResult`/`EquityPoint`.
- Produces:
  - `WorkflowBacktestResult(BacktestResult)` extended with `symbols: list[str]`, `signals: list[dict]` (the per-bar order-node records with traces, ready for `persist_workflow_run`).
  - `run_workflow_backtest(graph, histories: dict[str, list[Candle]], *, starting_cash=100_000.0, market=MarketKind.crypto, timeframe="1h", cost_model=None, ai_bar_cap=200, risk_free_rate=None) -> WorkflowBacktestResult`.
  - Validation (fail loud): graph has ≥1 order node; every order node resolves to one symbol (`resolve_order_symbol`); all histories share one timeframe (caller guarantees; orchestrator checks lengths/timeline ≥2); if any `ai_signal` node and `len(timeline) > ai_bar_cap` → `ValueError`.

- [ ] **Step 1: Write the failing test**

```python
# app/tests/test_workflow_backtest.py
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
    # at least one buy signal recorded for BTC with a non-empty trace
    btc_buys = [s for s in r1.signals if s["symbol"] == "BTC/USDT" and s["action"] == "buy"]
    assert btc_buys and btc_buys[0]["trace"]


def test_signals_recorded_every_bar_per_order_node():
    g, h = _two_symbol_graph(), _histories()
    r = run_workflow_backtest(g, h, cost_model=CostModel.zero())
    # 2 order nodes x (timeline-1) decision bars -> records for every bar incl. hold
    bars = len(next(iter(h.values()))) - 1
    assert len(r.signals) == 2 * bars
    assert {s["action"] for s in r.signals} <= {"buy", "sell", "hold"}


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest app/tests/test_workflow_backtest.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.backtest.workflow_backtest'`.

- [ ] **Step 3: Implement**

```python
# app/backtest/workflow_backtest.py
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

    for bar_i in range(len(timeline)):
        ts = timeline[bar_i]
        ts_iso = ts.isoformat()
        opens = {s: histories[s][by_ts[s][ts]].open for s in symbols}
        closes = {s: histories[s][by_ts[s][ts]].close for s in symbols}

        # 1) Execute the previous bar's decision at THIS bar's opens.
        if pending_targets is not None:
            sim.rebalance(pending_targets, opens, ts_iso)
            pending_targets = None

        # 2) Run the graph on data through close[bar_i]; collect order-node signals + traces.
        bt.current_index = bar_i  # window_for uses each symbol's own slice up to this ts
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
        if result.status != "ok":
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
```

> Note: `PortfolioSim` uses `_Pos` internally; the import `from app.backtest.portfolio import PortfolioSim, _Pos` is used only to read `quantity`/`avg_price` defensively. If `_Pos` is not exported cleanly, add `from app.backtest.portfolio import _Pos` — it is module-level in Task 4.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest app/tests/test_workflow_backtest.py -q`
Expected: PASS (3 tests). Then run the full suite: `pytest -q` — all green.

- [ ] **Step 5: Commit**

```bash
git add app/backtest/workflow_backtest.py app/tests/test_workflow_backtest.py
git commit -m "feat(backtest): workflow_backtest orchestrator — per-bar replay + portfolio sim

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: API — workflow backtest endpoint + run-history reads

**Files:**
- Modify: `app/api/backtest.py` (add `POST /api/backtest/workflow`)
- Modify: `app/api/workflows.py` (add run-history GET endpoints)
- Test: `app/tests/test_workflow_backtest_api.py` (create)

**Interfaces:**
- Consumes: `run_workflow_backtest`, `persist_workflow_run`, `get_data_broker`, `WorkflowRun`/`WorkflowSignal`.
- Produces:
  - `POST /api/backtest/workflow` body `WorkflowBacktestRequest{ graph?: WorkflowGraph, workflow_id?: int, market, timeframe, limit, starting_cash }` → `WorkflowBacktestResult` plus a `run_id` (DB id). Fetches each distinct symbol's history via `get_data_broker(market).get_ohlcv`, runs the backtest, persists via `persist_workflow_run(kind="backtest")`.
  - `GET /api/workflows/runs?kind=&limit=` → `list[WorkflowRun]` (newest first).
  - `GET /api/workflows/runs/{run_id}` → `WorkflowRun`.
  - `GET /api/workflows/runs/{run_id}/signals?symbol=` → `list[WorkflowSignal]`.

- [ ] **Step 1: Write the failing test**

```python
# app/tests/test_workflow_backtest_api.py
from __future__ import annotations

from fastapi.testclient import TestClient

from app.brokers import registry
from app.main import app
from app.schemas import MarketKind
from app.tests.helpers import StubBroker, make_candles
from app.workflow import nodes


def _patch_data(monkeypatch, closes):
    stub = StubBroker({"BTC/USDT": closes[-1]}, candles=make_candles(closes))
    monkeypatch.setattr("app.api.backtest.get_data_broker", lambda market: stub)


def test_workflow_backtest_endpoint_persists_and_reads(monkeypatch):
    _patch_data(monkeypatch, [5, 5, 5, 5, 5, 9, 9, 9])
    client = TestClient(app)
    graph = {
        "nodes": [
            {"id": "d", "type": "data_source", "params": {"symbol": "BTC/USDT"}},
            {"id": "s", "type": "strategy", "params": {"name": "ma_cross", "fast": 2, "slow": 4}},
            {"id": "o", "type": "order", "params": {}},
        ],
        "edges": [{"source": "d", "target": "s"}, {"source": "s", "target": "o"}],
    }
    resp = client.post("/api/backtest/workflow", json={"graph": graph, "limit": 50})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "run_id" in body and body["symbols"] == ["BTC/USDT"]
    rid = body["run_id"]

    runs = client.get("/api/workflows/runs?kind=backtest").json()
    assert any(r["id"] == rid for r in runs)
    sigs = client.get(f"/api/workflows/runs/{rid}/signals").json()
    assert sigs and all("trace_json" in s for s in sigs)
```

(Note: if global auth is enabled in the test env, follow the pattern in `app/tests/test_backtest_api.py` for headers; auth is disabled when `API_TOKEN` is empty.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest app/tests/test_workflow_backtest_api.py -q`
Expected: FAIL — 404 on `/api/backtest/workflow`.

- [ ] **Step 3: Implement**

In `app/api/backtest.py`, add imports and the endpoint:

```python
from fastapi import Depends
from sqlmodel import Session

from app.backtest.workflow_backtest import WorkflowBacktestResult, run_workflow_backtest
from app.db import get_session
from app.models import Workflow
from app.workflow.run_store import persist_workflow_run, resolve_order_symbol
from app.workflow.schema import NodeType, WorkflowGraph


class WorkflowBacktestRequest(BaseModel):
    graph: WorkflowGraph | None = None
    workflow_id: int | None = None
    market: MarketKind = MarketKind.crypto
    timeframe: str = "1h"
    limit: int = Field(default=500, ge=10, le=1000)
    starting_cash: float = 100_000.0


class WorkflowBacktestResponse(WorkflowBacktestResult):
    run_id: int


@router.post("/workflow", response_model=WorkflowBacktestResponse)
def workflow_backtest(req: WorkflowBacktestRequest, session: Session = Depends(get_session)) -> WorkflowBacktestResponse:
    if req.graph is None and req.workflow_id is None:
        raise HTTPException(status_code=422, detail="provide either 'graph' or 'workflow_id'")
    graph = req.graph
    if graph is None:
        wf = session.get(Workflow, req.workflow_id)
        if wf is None:
            raise HTTPException(status_code=404, detail="workflow not found")
        graph = WorkflowGraph.model_validate(wf.graph)
    try:
        order_nodes = [n for n in graph.nodes if n.type == NodeType.order]
        if not order_nodes:
            raise ValueError("workflow backtest requires at least one order node")
        symbols = sorted({resolve_order_symbol(graph, n.id) for n in order_nodes})
        broker = get_data_broker(req.market)
        histories = {s: broker.get_ohlcv(s, req.timeframe, req.limit) for s in symbols}
        result = run_workflow_backtest(
            graph,
            histories,
            starting_cash=req.starting_cash,
            market=req.market,
            timeframe=req.timeframe,
        )
        run_db_id = persist_workflow_run(
            session,
            run_id=f"bt-{req.workflow_id or 'adhoc'}",
            kind="backtest",
            graph=graph,
            market=req.market.value,
            symbols=result.symbols,
            timeframe=req.timeframe,
            starting_cash=req.starting_cash,
            params={"limit": req.limit},
            metrics=result.model_dump(mode="json", exclude={"signals", "equity_curve", "trades"}),
            equity_curve=[p.model_dump(mode="json") for p in result.equity_curve],
            trades=[t.model_dump(mode="json") for t in result.trades],
            status="ok",
            signals=result.signals,
        )
        return WorkflowBacktestResponse(**result.model_dump(), run_id=run_db_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"{type(exc).__name__}: {exc}")
```

In `app/api/workflows.py`, add the run-history reads (import `WorkflowRun, WorkflowSignal`):

```python
from app.models import RunLog, Workflow, WorkflowRun, WorkflowSignal


@router.get("/runs", response_model=list[WorkflowRun])
def list_runs(kind: str | None = None, limit: int = 50, session: Session = Depends(get_session)) -> list[WorkflowRun]:
    q = select(WorkflowRun).order_by(WorkflowRun.id.desc()).limit(limit)
    if kind:
        q = q.where(WorkflowRun.kind == kind)
    return list(session.exec(q).all())


@router.get("/runs/{run_id}", response_model=WorkflowRun)
def get_run(run_id: int, session: Session = Depends(get_session)) -> WorkflowRun:
    run = session.get(WorkflowRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@router.get("/runs/{run_id}/signals", response_model=list[WorkflowSignal])
def get_run_signals(run_id: int, symbol: str | None = None, session: Session = Depends(get_session)) -> list[WorkflowSignal]:
    q = select(WorkflowSignal).where(WorkflowSignal.run_id == run_id).order_by(WorkflowSignal.bar_index)
    if symbol:
        q = q.where(WorkflowSignal.symbol == symbol)
    return list(session.exec(q).all())
```

> Place the `/runs` routes BEFORE `/{workflow_id}` is not required since prefixes differ (`/runs` vs `/{workflow_id}`), but FastAPI matches `/runs` against `/{workflow_id}` (string) — to avoid `runs` being parsed as a workflow_id, declare the `/runs*` routes ABOVE the `/{workflow_id}` route in the file.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest app/tests/test_workflow_backtest_api.py -q`
Expected: PASS. Then `pytest -q` — full suite green.

- [ ] **Step 5: Commit**

```bash
git add app/api/backtest.py app/api/workflows.py app/tests/test_workflow_backtest_api.py
git commit -m "feat(api): POST /backtest/workflow + workflow run-history reads

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Persist live/paper workflow runs (unified history)

**Files:**
- Modify: `app/api/workflows.py` (`run_ad_hoc`, `run_saved`)
- Test: `app/tests/test_workflow_live_persist.py` (create)

**Interfaces:**
- Consumes: `run_workflow` (now records `ctx.node_outputs`), `persist_workflow_run`, `build_trace`, `resolve_order_symbol`, `settings.trading_mode`.
- Produces: each live/paper run writes one `WorkflowRun(kind=<mode>)` + one `WorkflowSignal` per order node that produced an order, with the ancestor trace. Order behavior is unchanged (records written AFTER execution); existing `RunLog` writes stay.

- [ ] **Step 1: Write the failing test**

```python
# app/tests/test_workflow_live_persist.py
from __future__ import annotations

from fastapi.testclient import TestClient

from app.brokers import registry
from app.brokers.paper import PaperBroker
from app.main import app
from app.schemas import MarketKind
from app.tests.helpers import StubBroker, make_candles
from app.workflow import nodes


def test_live_run_persists_workflow_run_and_signals(monkeypatch):
    buy_cross = make_candles([5, 5, 5, 5, 5, 9])
    monkeypatch.setattr(nodes, "get_data_broker", lambda market: StubBroker({"BTC/USDT": 9.0}, candles=buy_cross))
    registry.reset_paper_brokers()
    registry._paper_cache[MarketKind.crypto] = PaperBroker(
        data_provider=StubBroker({"BTC/USDT": 9.0}), starting_cash=10_000.0
    )
    client = TestClient(app)
    graph = {
        "nodes": [
            {"id": "d", "type": "data_source", "params": {"symbol": "BTC/USDT"}},
            {"id": "s", "type": "strategy", "params": {"name": "ma_cross", "fast": 2, "slow": 4}},
            {"id": "o", "type": "order", "params": {"quantity": 1}},
        ],
        "edges": [{"source": "d", "target": "s"}, {"source": "s", "target": "o"}],
    }
    r = client.post("/api/workflows/run", json=graph)
    assert r.status_code == 200, r.text
    runs = client.get("/api/workflows/runs?kind=paper").json()
    assert runs, "expected a persisted paper run"
    sigs = client.get(f"/api/workflows/runs/{runs[0]['id']}/signals").json()
    assert any(s["action"] == "buy" and s["symbol"] == "BTC/USDT" for s in sigs)
    registry.reset_paper_brokers()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest app/tests/test_workflow_live_persist.py -q`
Expected: FAIL — `kind=paper` run list is empty (live path doesn't persist `WorkflowRun` yet).

- [ ] **Step 3: Implement**

In `app/api/workflows.py`, add imports and a helper, then call it from both run endpoints:

```python
from app.config import settings
from app.schemas import MarketKind, SignalAction
from app.workflow.nodes import RunContext
from app.workflow.run_store import build_trace, persist_workflow_run, resolve_order_symbol
from app.workflow.schema import NodeType


def _persist_live_run(session, graph, workflow_id, ctx, result):
    """Record a live/paper workflow execution as a WorkflowRun + per-order-node signals."""
    order_nodes = [n for n in graph.nodes if n.type == NodeType.order]
    signals = []
    symbols = []
    for n in order_nodes:
        try:
            sym = resolve_order_symbol(graph, n.id)
        except ValueError:
            sym = n.params.get("symbol", "")
        symbols.append(sym)
        out = ctx.node_outputs.get(n.id)
        # out is an OrderResult when an order was placed, else None
        action = "hold"
        price = 0.0
        if out is not None and hasattr(out, "side"):
            action = SignalAction.buy.value if out.side.value == "buy" else SignalAction.sell.value
            price = out.price
        signals.append(
            {
                "order_node_id": n.id,
                "symbol": sym,
                "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
                "bar_index": None,
                "action": action,
                "confidence": 0.5,
                "price": price,
                "trace": build_trace(graph, n.id, ctx.node_outputs),
            }
        )
    persist_workflow_run(
        session,
        run_id=ctx.run_id,
        kind=settings.trading_mode.value if hasattr(settings.trading_mode, "value") else str(settings.trading_mode),
        graph=graph,
        market="crypto",
        symbols=sorted(set(s for s in symbols if s)),
        timeframe="",
        starting_cash=None,
        params={},
        metrics=None,
        equity_curve=None,
        trades=None,
        status=result.status,
        signals=signals,
    )
```

Change `run_ad_hoc` to build the ctx, persist, keep `RunLog`:

```python
@router.post("/run", response_model=RunResult)
def run_ad_hoc(graph: WorkflowGraph, session: Session = Depends(get_session)) -> RunResult:
    """Run a graph without persisting the workflow (handy for the editor's 'Run' button)."""
    ctx = RunContext(session=session)
    result = run_workflow(graph, session=session, ctx=ctx)
    session.add(RunLog(workflow_id=None, status=result.status, detail=result.model_dump(mode="json")))
    if result.status == "ok":
        _persist_live_run(session, graph, None, ctx, result)
    session.commit()
    return result
```

Apply the same pattern to `run_saved` (build `ctx`, pass `ctx=ctx`, call `_persist_live_run(session, graph, workflow_id, ctx, result)` on success).

> The `kind` uses `settings.trading_mode` (paper/live). Confirm the setting name by checking `app/config.py` for the trading-mode field; if it is named differently (e.g. `trading_mode`), use that exact attribute. The test asserts `kind=paper`, which is the default `TRADING_MODE`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest app/tests/test_workflow_live_persist.py app/tests/test_workflow.py -q`
Expected: PASS — live run persists; existing workflow order behavior unchanged. Then `pytest -q` full suite green.

- [ ] **Step 5: Commit**

```bash
git add app/api/workflows.py app/tests/test_workflow_live_persist.py
git commit -m "feat(api): persist live/paper workflow runs into unified history

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: Frontend API client — backtest + run history

**Files:**
- Modify: `frontend/lib/api.ts`
- Verify: `cd frontend && npm run build`

**Interfaces:**
- Produces typed methods on the existing api client:
  - `runWorkflowBacktest(body: { graph?: WorkflowGraphDTO; workflow_id?: number; market?: string; timeframe?: string; limit?: number; starting_cash?: number }): Promise<WorkflowBacktestResponse>`
  - `listWorkflowRuns(params?: { kind?: string; limit?: number }): Promise<WorkflowRunDTO[]>`
  - `getWorkflowRun(runId: number): Promise<WorkflowRunDTO>`
  - `getWorkflowRunSignals(runId: number, symbol?: string): Promise<WorkflowSignalDTO[]>`
  - Types `WorkflowRunDTO`, `WorkflowSignalDTO`, `WorkflowBacktestResponse` (extends the existing backtest result type with `symbols: string[]`, `signals: WorkflowSignalDTO[]`, `run_id: number`).

- [ ] **Step 1: Read the existing client to match conventions**

Run: `cd frontend && sed -n '1,80p' lib/api.ts` and locate the existing backtest result type + request helper (e.g. `apiFetch`/`request`). Match its style (fetch wrapper, base URL, bearer header).

- [ ] **Step 2: Add types + methods**

Add (adapting names to the file's existing `request`/`apiFetch` helper and result type — reuse the existing `BacktestResult` type for the metrics fields):

```typescript
export interface WorkflowSignalDTO {
  id: number;
  run_id: number;
  order_node_id: string;
  symbol: string;
  timestamp: string;
  bar_index: number | null;
  action: "buy" | "sell" | "hold";
  confidence: number;
  price: number;
  trace_json: { node_id: string; type: string; summary: Record<string, unknown> }[];
}

export interface WorkflowRunDTO {
  id: number;
  run_id: string;
  kind: "backtest" | "live" | "paper";
  workflow_id: number | null;
  market: string;
  symbols: string[];
  timeframe: string;
  starting_cash: number | null;
  metrics_json: Record<string, number> | null;
  equity_curve_json: { timestamp: string; equity: number }[] | null;
  trades_json: unknown[] | null;
  status: string;
  created_at: string;
}

export type WorkflowBacktestResponse = BacktestResult & {
  run_id: number;
  symbols: string[];
  signals: WorkflowSignalDTO[];
};

export const runWorkflowBacktest = (body: {
  graph?: unknown;
  workflow_id?: number;
  market?: string;
  timeframe?: string;
  limit?: number;
  starting_cash?: number;
}) => request<WorkflowBacktestResponse>("/api/backtest/workflow", { method: "POST", body: JSON.stringify(body) });

export const listWorkflowRuns = (params?: { kind?: string; limit?: number }) => {
  const q = new URLSearchParams();
  if (params?.kind) q.set("kind", params.kind);
  if (params?.limit) q.set("limit", String(params.limit));
  return request<WorkflowRunDTO[]>(`/api/workflows/runs?${q.toString()}`);
};

export const getWorkflowRun = (runId: number) => request<WorkflowRunDTO>(`/api/workflows/runs/${runId}`);

export const getWorkflowRunSignals = (runId: number, symbol?: string) =>
  request<WorkflowSignalDTO[]>(`/api/workflows/runs/${runId}/signals${symbol ? `?symbol=${encodeURIComponent(symbol)}` : ""}`);
```

> If the client uses a class/object with methods rather than free functions, attach these as methods following that pattern. Reuse the existing `request`/`apiFetch` wrapper — do NOT introduce a second fetch helper.

- [ ] **Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: build succeeds (types compile).

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/api.ts
git commit -m "feat(frontend): api client for workflow backtest + run history

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: Signal-marker chart + trace drawer component

**Files:**
- Create: `frontend/components/WorkflowBacktestChart.tsx`
- Create: `frontend/components/SignalTraceDrawer.tsx`
- Verify: `cd frontend && npm run build`

**Interfaces:**
- Consumes: `lightweight-charts`, `WorkflowSignalDTO`, `WorkflowRunDTO` (equity curve), DESIGN.md tokens (`--up`/`--down`/`--accent`).
- Produces:
  - `<WorkflowBacktestChart run={WorkflowRunDTO} signals={WorkflowSignalDTO[]} onSelectSignal={(s) => void} />` — renders the run's equity curve (or per-symbol price line) with **markers per signal**: buy = `--up` ▲ below bar, sell = `--down` ▼ above bar, hold = small neutral dot; clicking a marker calls `onSelectSignal`.
  - `<SignalTraceDrawer signal={WorkflowSignalDTO | null} onClose={() => void} />` — side drawer listing each `trace_json` entry (node_id, type, and a readable summary of the node's output) top-to-bottom, ending with the resulting action/confidence.

- [ ] **Step 1: Read DESIGN.md chart/marker guidance + an existing chart component**

Run: `cd frontend && sed -n '1,40p' components/BacktestPanel.tsx` and grep for existing `lightweight-charts` usage (`grep -rl "lightweight-charts" components`). Reuse the existing chart setup (theme colors, time formatting) so markers match house style. Confirm `--up`/`--down`/`--accent` token usage per DESIGN.md (never hardcode green-as-gain; respect `data-market="tw"`).

- [ ] **Step 2: Implement `SignalTraceDrawer.tsx`**

```tsx
"use client";
import type { WorkflowSignalDTO } from "@/lib/api";

export function SignalTraceDrawer({ signal, onClose }: { signal: WorkflowSignalDTO | null; onClose: () => void }) {
  if (!signal) return null;
  return (
    <aside className="signal-trace-drawer" role="dialog" aria-label="Signal derivation">
      <header>
        <strong>{signal.symbol}</strong> · {signal.action.toUpperCase()} · conf {signal.confidence.toFixed(2)}
        <button onClick={onClose} aria-label="Close">×</button>
      </header>
      <p className="muted">{new Date(signal.timestamp).toLocaleString()} · price {signal.price}</p>
      <ol className="trace-steps">
        {signal.trace_json.map((step) => (
          <li key={step.node_id}>
            <code>{step.type}</code> <span className="node-id">{step.node_id}</span>
            <pre>{JSON.stringify(step.summary, null, 2)}</pre>
          </li>
        ))}
      </ol>
    </aside>
  );
}
```

- [ ] **Step 3: Implement `WorkflowBacktestChart.tsx`**

Build on the existing lightweight-charts setup found in Step 1. Core requirements (adapt to the existing chart helper's API version):

```tsx
"use client";
import { useEffect, useRef } from "react";
import { createChart, type IChartApi } from "lightweight-charts";
import type { WorkflowRunDTO, WorkflowSignalDTO } from "@/lib/api";

export function WorkflowBacktestChart({
  run,
  signals,
  onSelectSignal,
}: {
  run: WorkflowRunDTO;
  signals: WorkflowSignalDTO[];
  onSelectSignal: (s: WorkflowSignalDTO) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = createChart(ref.current, { autoSize: true });
    chartRef.current = chart;
    const line = chart.addLineSeries();
    line.setData((run.equity_curve_json ?? []).map((p) => ({ time: (Date.parse(p.timestamp) / 1000) as never, value: p.equity })));
    const up = getComputedStyle(document.documentElement).getPropertyValue("--up").trim() || "#16a34a";
    const down = getComputedStyle(document.documentElement).getPropertyValue("--down").trim() || "#dc2626";
    line.setMarkers(
      signals
        .filter((s) => s.action !== "hold")
        .map((s) => ({
          time: (Date.parse(s.timestamp) / 1000) as never,
          position: s.action === "buy" ? "belowBar" : "aboveBar",
          color: s.action === "buy" ? up : down,
          shape: s.action === "buy" ? "arrowUp" : "arrowDown",
          text: s.action.toUpperCase(),
        })),
    );
    chart.subscribeClick((param) => {
      if (param.time == null) return;
      const t = (param.time as number) * 1000;
      const hit = signals.reduce<WorkflowSignalDTO | null>((best, s) => {
        const d = Math.abs(Date.parse(s.timestamp) - t);
        return best && Math.abs(Date.parse(best.timestamp) - t) <= d ? best : s;
      }, null);
      if (hit) onSelectSignal(hit);
    });
    return () => chart.remove();
  }, [run, signals, onSelectSignal]);

  return <div ref={ref} style={{ width: "100%", height: 360 }} />;
}
```

> Adjust `addLineSeries`/`setMarkers`/`subscribeClick` to the installed `lightweight-charts` major version (check `package.json`); v5 uses `addSeries(LineSeries, …)` and `createSeriesMarkers`. Match whatever the existing chart component in Step 1 uses.

- [ ] **Step 4: Verify build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/WorkflowBacktestChart.tsx frontend/components/SignalTraceDrawer.tsx
git commit -m "feat(frontend): workflow backtest chart with signal markers + trace drawer

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 11: Wire backtest action + run-history browser into the workflow page

**Files:**
- Modify: the workflow builder page/component under `frontend/app/(rooms)/trading-room/workflow/` (exact file: locate the "Run" button component in Step 1)
- Create: `frontend/components/WorkflowRunHistory.tsx`
- Verify: `cd frontend && npm run build`

**Interfaces:**
- Consumes: `runWorkflowBacktest`, `listWorkflowRuns`, `getWorkflowRun`, `getWorkflowRunSignals`, `WorkflowBacktestChart`, `SignalTraceDrawer`.
- Produces:
  - A "Backtest" button next to "Run" in the workflow builder that serializes the current React Flow graph to the `{nodes, edges}` DTO and calls `runWorkflowBacktest({ graph, limit })`, then shows `<WorkflowBacktestChart>` + metrics.
  - `<WorkflowRunHistory onOpen={(runId) => void} kind?: string />` — lists past runs (`listWorkflowRuns`), newest first, each row showing kind/symbols/return/date; clicking loads that run's chart + signals.

- [ ] **Step 1: Locate the builder's Run handler + graph serialization**

Run: `cd frontend && grep -rn "workflows/run\|runAdHoc\|toGraph\|nodes:.*edges" app/\(rooms\)/trading-room/workflow components | head`. Identify how the editor converts React Flow nodes/edges to the backend `{nodes:[{id,type,params}], edges:[{source,target}]}` shape (reuse it — do not re-implement).

- [ ] **Step 2: Implement `WorkflowRunHistory.tsx`**

```tsx
"use client";
import { useEffect, useState } from "react";
import { listWorkflowRuns, type WorkflowRunDTO } from "@/lib/api";

export function WorkflowRunHistory({ kind, onOpen }: { kind?: string; onOpen: (runId: number) => void }) {
  const [runs, setRuns] = useState<WorkflowRunDTO[]>([]);
  useEffect(() => {
    listWorkflowRuns({ kind, limit: 50 }).then(setRuns).catch(() => setRuns([]));
  }, [kind]);
  return (
    <ul className="run-history">
      {runs.map((r) => (
        <li key={r.id}>
          <button onClick={() => onOpen(r.id)}>
            <span className="kind">{r.kind}</span> {r.symbols.join(", ")}
            <span className="ret">{r.metrics_json?.total_return_pct?.toFixed(2) ?? "—"}%</span>
            <time>{new Date(r.created_at).toLocaleString()}</time>
          </button>
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **Step 3: Add the Backtest button + result panel to the builder**

In the builder component, next to the existing Run button, add a Backtest button using the existing graph serializer (call it `serializeGraph()` — use whatever the real helper is named from Step 1):

```tsx
const [btRun, setBtRun] = useState<WorkflowRunDTO | null>(null);
const [btSignals, setBtSignals] = useState<WorkflowSignalDTO[]>([]);
const [selected, setSelected] = useState<WorkflowSignalDTO | null>(null);

async function handleBacktest() {
  const graph = serializeGraph();           // reuse existing serializer
  const res = await runWorkflowBacktest({ graph, limit: 500 });
  const run = await getWorkflowRun(res.run_id);
  setBtRun(run);
  setBtSignals(res.signals);
}

async function openRun(runId: number) {
  const [run, sigs] = await Promise.all([getWorkflowRun(runId), getWorkflowRunSignals(runId)]);
  setBtRun(run);
  setBtSignals(sigs);
}
```

Render below the editor:

```tsx
<button onClick={handleBacktest}>Backtest</button>
<WorkflowRunHistory onOpen={openRun} />
{btRun && <WorkflowBacktestChart run={btRun} signals={btSignals} onSelectSignal={setSelected} />}
<SignalTraceDrawer signal={selected} onClose={() => setSelected(null)} />
```

- [ ] **Step 4: Verify build**

Run: `cd frontend && npm run build && npm run lint`
Expected: build + lint pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): backtest action + run-history browser in workflow builder

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 12: End-to-end manual verification + docs

**Files:**
- Verify: full stack via the `run-app` skill
- Modify: `docs/` workflow/backtest doc if one references workflow capabilities (check `lib/docs-manifest.ts`)

- [ ] **Step 1: Backend full suite**

Run: `cd backend && pytest -q`
Expected: all tests pass (including the new backtest/persistence/trace tests).

- [ ] **Step 2: Launch the stack and drive the UI**

Use the `run-app` skill (frontend/.claude/skills) to start backend + SQLite + frontend. In the trading-room workflow builder: build a 2-symbol `ma_cross` graph (BTC/USDT + ETH/USDT), click **Backtest**, confirm: equity curve renders, buy/sell markers appear, clicking a marker opens the trace drawer showing the node-by-node derivation, and the run appears in the run-history list. Reload a past run from history and confirm markers/trace reappear.

- [ ] **Step 3: Verify live-run persistence**

Trigger an ad-hoc run from the builder ("Run"), then confirm a `kind=paper` entry shows in run history with at least one signal + trace.

- [ ] **Step 4: Docs (if applicable)**

If a doc in `lib/docs-manifest.ts` describes workflow/backtest features, add a short paragraph describing workflow historical backtest + run history. Do not hand-edit synced copies under `frontend/content/docs/` (regenerated by sync-docs).

- [ ] **Step 5: Commit + open PR**

```bash
git add -A
git commit -m "docs: describe workflow historical backtest + run history

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
gh pr create --base main --head feature/workflow-backtest \
  --title "Workflow historical backtest + unified run history & per-signal traces" \
  --body "Implements docs/superpowers/specs/2026-06-21-workflow-backtest-design.md.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```

---

## Self-Review

**Spec coverage:**
- Per-bar Signal generator via `BacktestContext` → Tasks 1, 5, 6. ✓
- AI bar cap (200) → Task 6 (`ai_bar_cap`, fail-loud test). ✓
- New shared-portfolio multi-asset engine → Task 4 (`PortfolioSim`) + Task 6. ✓
- Equal-weight sizing → Task 4 (`target_quantities`) + Task 6. ✓
- Unified persistence (backtest + live/paper) → Task 2 (tables), 3 (run_store), 7 (backtest), 8 (live). ✓
- Per-signal chart markers + click-through trace → Tasks 10, 11. ✓
- Run-history browser → Tasks 9, 11. ✓
- Trace = order node's ancestor outputs → Task 3 (`build_trace`/`order_node_ancestors`) + tests. ✓
- Fail-loud validation (AI cap, timeframe/timeline, unresolvable symbol) → Task 6 + Task 3 (`resolve_order_symbol`). ✓
- Live order behavior unchanged → Task 8 (additive persist; `test_workflow.py` re-run asserts behavior). ✓
- Determinism + next-bar-open fills + costs → Task 4/6 tests. ✓

**Open items folded into tasks (no placeholders):**
- `settings.trading_mode` attribute name verified at implementation time in Task 8 (note included).
- `lightweight-charts` major-version API differences noted in Task 10 (adapt to installed version).
- React Flow graph serializer reused from existing builder, located in Task 11 Step 1.

**Type consistency:** `BacktestContext`/`SimPos`, `PortfolioSim`/`_Pos`, `resolve_order_symbol`/`build_trace`/`order_node_ancestors`, `run_workflow_backtest` return type `WorkflowBacktestResult` (extended to `WorkflowBacktestResponse` with `run_id` in the API) are consistent across producing and consuming tasks. The DTOs in Task 9 mirror the SQLModel fields from Task 2.
