# Workflow Historical Backtest + Unified Run History & Per-Signal Traces

**Date:** 2026-06-21
**Status:** Approved design — ready for implementation plan

## Problem

Node-based workflows (`WorkflowGraph`) can run live/paper but **cannot be replayed over
historical data**. `backtest/engine.py:run_backtest()` accepts only a single `Strategy` +
full candle history and walks bar-by-bar; `workflow/engine.py:run_workflow()` runs **one
topological pass on the latest snapshot** and places orders against the live/paper broker.
The `data_source` node always fetches the *current* latest bars, and there is no concept of
stepping through history. There is also no persisted, browsable record of past workflow
runs or of how each signal was derived.

## Goals

1. Run an arbitrary `WorkflowGraph` as a **multi-asset, shared-cash portfolio backtest** over
   historical data, reusing the existing workflow node logic so backtest signals are identical
   to live.
2. Persist **every** workflow execution (backtest **and** live/paper) as a run + per-signal
   records in the database — one unified, browsable history.
3. Show every emitted signal as a **clickable marker on the price chart**; clicking opens the
   **node-by-node derivation** ("how was this signal produced") for that bar.

## Decisions (locked during brainstorming)

| Decision | Choice |
|----------|--------|
| Workflow→backtest bridge | Workflow is a per-bar **Signal generator**; reuse `run_workflow` driven once per bar via a `BacktestContext`. Node logic unchanged. |
| `ai_signal` nodes in backtest | **Call the LLM per bar**, with a configurable **bar cap (default 200)**; fail loud if the timeline exceeds it. |
| Multi-symbol | **New shared-portfolio multi-asset engine** (one cash pool), not single-asset reuse. |
| Position sizing | **Equal-weight** across active-long symbols; rebalance toward `1/N × equity` each bar. |
| History persistence scope | **Unified**: backtest + live/paper runs both persisted. |
| Signal records / markers | **Every bar × symbol** (including `hold`), each with full trace. |

## Architecture

Bridge the two engines by **reusing `run_workflow` itself**, driven once per historical bar
through a new `BacktestContext` threaded into the engine. Only two node runners change
behavior when that context is present; every other runner is unchanged so backtest signal
logic is byte-for-byte identical to live.

- **`data_source`** (backtest ctx) → instead of fetching latest live candles, return the
  pre-loaded history for its symbol **sliced up to the current bar timestamp** (the lookback
  window the rest of the graph sees).
- **`order`** (backtest ctx) → instead of hitting the live/paper broker, **record
  `(symbol → Signal)`** into the context's per-bar sink.
- **Trace capture (new)** → the engine retains each node's *actual output* (Signal
  action/confidence, condition value, combine decision, …) per pass, not just a summary
  string. For each `order` node we persist a **signal record** whose trace = the order node's
  **ancestor nodes and their outputs at that bar** — exactly "how this signal was produced."

The recorded per-bar, per-symbol Signal matrix is fed to a **new multi-asset portfolio
engine** with one shared cash pool.

## Components

| # | File | Responsibility |
|---|------|----------------|
| 1 | `workflow/engine.py`, `workflow/nodes.py` (edit) | Add optional `BacktestContext`; `data_source`/`order` branch on it; retain per-node outputs for tracing. No change to other runners. |
| 2 | `workflow/run_store.py` (new) | Write `WorkflowRun` + `WorkflowSignal` rows; build each signal's ancestor trace. Called by both the live path and the backtest orchestrator. |
| 3 | `backtest/portfolio_engine.py` (new) | Shared-cash multi-asset simulation: equal-weight rebalance toward active-long targets, **next-bar-open fills** (matches existing M0.2 convention), cost model applied, mark-to-market → portfolio equity curve + trades. |
| 4 | `backtest/workflow_backtest.py` (new) | Orchestrator: pre-fetch each symbol's history, build aligned timeline, drive `run_workflow` per bar → Signal matrix + traces → portfolio_engine → persist via run_store. Owns all validation. |
| 5 | `api/backtest.py`, `api/workflows.py`, `api/schemas.py` (edit) | `POST /api/backtest/workflow` (ad-hoc graph or saved `workflow_id` + range/limit + `starting_cash`); new `GET /runs`, `GET /runs/{id}`, `GET /runs/{id}/signals[/{sig}]`; live `run_workflow` path persists too. |
| 6 | Frontend (edit) | Chart with per-signal markers (buy/sell prominent, hold inspectable) via `lightweight-charts`; click marker → drawer showing the node-by-node trace; run-history browser listing past runs (backtest + live/paper) → load equity/trades/markers. |

## Persistence model (SQLModel, `api/models.py`)

Unified across backtest + live/paper.

**`WorkflowRun`**: `id`, `run_id`, `kind` (`backtest`/`live`/`paper`), `workflow_id?`,
`graph_json` (graph snapshot for reproducibility), `market`, `symbols`, `timeframe`,
`starting_cash?`, `params_json`, `metrics_json?`, `equity_curve_json?`, `trades_json?`,
`status`, `created_at`.

**`WorkflowSignal`**: `id`, `run_id`→`WorkflowRun`, `order_node_id`, `symbol`, `timestamp`,
`bar_index?`, `action` (buy/sell/hold), `confidence/size`, `price`, `trace_json` (ancestor
node outputs at that bar), `created_at`.

Every bar × symbol (incl. hold) → one `WorkflowSignal`; a live trigger → one row per order
node. Equity/trades/metrics are stored as JSON on the run (queried as a unit); signals get
their own table (individually queried/clicked). The AI bar-cap bounds backtest row volume.

## Data flow

```
backtest: histories → per bar: run_workflow(ctx) → {Signal[t][symbol] + node trace}
                                    │
              portfolio_engine (equal-weight, t+1 open fill, costs) → equity/trades/metrics
                                    │
live/paper:  run_workflow(trigger) ─┤
                                    ▼
                          run_store → WorkflowRun + WorkflowSignal(trace) → DB
                                    ▼
        GET /runs, /runs/{id}, /runs/{id}/signals/{sig}
                                    ▼
   Frontend: chart markers ──click──▶ trace drawer ;  history browser ──▶ load run
```

## Equal-weight sizing rule

Each bar, symbols currently signalling **long** target `1/N × portfolio_equity` (N = count of
active longs that bar); the engine rebalances positions toward those targets. `hold` keeps the
current position; `sell`/flat exits to cash. As symbols enter/exit, N changes and remaining
symbols rebalance.

## Fail-loud validation (per CLAUDE.md)

- **AI bar cap**: if the graph has an `ai_signal` node and timeline bars > cap (default 200) →
  reject before running (bounds token cost).
- **Timeframe mismatch** across `data_source` nodes → reject (v1 requires one shared timeframe;
  align by timestamp).
- **Unresolvable order symbol**: an `order` node whose upstream cannot resolve to exactly one
  `data_source`/symbol → reject.
- **Insufficient history / warmup** → reject.
- **Persistence failures** fail loud (never silently drop a run/signal).
- The live order path change is **additive** (persist after execution) and must **not** alter
  order behavior.

## Testing (business-logic)

- Two-symbol (`ma_cross` on two symbols) backtest over fixed CSV/synthetic history → equity
  matches a hand-computed equal-weight portfolio (deterministic).
- Rebalance: both long ≈ 50/50; one exits → other rebalances to ~100%.
- Next-bar-open fill convention + transaction costs verified.
- Trace correctness: a signal's `trace_json` contains exactly its order node's ancestors with
  the correct per-bar outputs.
- Persistence round-trip: run → DB → `GET /runs/{id}` returns identical equity/trades/signals;
  a live trigger writes one run + the expected signal rows **without changing order behavior**.
- Determinism: same graph + same history → identical result.
- Fail-loud cases: AI cap exceeded, timeframe mismatch, unresolvable order symbol.

## Assumptions

- v1 requires all `data_source` nodes in a backtested graph share one timeframe; bars align by
  timestamp.
- The backtest date range is expressed via `limit`/range on the request (consistent with the
  existing backtest API).
- Results reuse the existing `BacktestResult` shape plus an optional per-symbol breakdown.

## Out of scope (v1)

- Cross-timeframe graphs (mixed timeframes across data_sources).
- Honoring per-order-node custom sizing params (equal-weight only).
- Backtesting graphs whose order-node symbol cannot be statically resolved.
