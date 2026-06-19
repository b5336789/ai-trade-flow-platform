# Spec — 策略庫 + AI 產生策略後端 (Sub-project B)

> Status: **approved design**, pre-implementation. Part of the new two-room redesign
> (see [`DESIGN.md`](../../DESIGN.md)). Build order: **B (this) → A frontend → C logic nodes**.
> Previous task history: [`development-log.md`](../development-log.md).

## Goal

Let users design trading strategies by talking to the AI in natural language, save them to
a reusable **strategy library** with adjustable parameters, and use them in the 交易室
workflow — backtested or live — exactly like the built-in strategies.

## Two locked decisions

1. **Execution model = declarative spec, not executed code.** An AI-generated strategy is
   stored as a validated JSON `StrategySpec`. A small interpreter turns it into the same
   `Signal` the engine already consumes. The Python shown to the user is *rendered from the
   spec* (read-only, for transparency/export) and is **never `eval`'d**. This is what makes
   AI strategies safe to run in live mode.
2. **Strategies are self-contained.** The spec carries its own entry/exit conditions and
   emits buy/sell/hold — matching the existing 4 strategies. Cross-strategy combination and
   confidence gating live in the canvas logic nodes (sub-project C), not in the strategy.

## Architecture

```
StrategySpec (JSON, validated)
   └─(interpreter)─▶ SpecStrategy  ──implements──▶ existing Strategy interface
                                                    ├─ workflow `strategy` node (unchanged)
                                                    └─ backtester (unchanged)
spec ──(pure renderer)──▶ Python string   # display/export only, never executed
```

`SpecStrategy` is an adapter implementing the current `Strategy` interface, so the workflow
engine and backtester treat AI strategies and built-ins identically. Built-ins stay as code;
the two coexist.

### Data model — one new table

```
StrategyDef(table=True):
  id: int (pk)
  name: str
  description: str = ""
  spec_json: str            # serialized StrategySpec
  source: str               # "ai" | "manual"
  created_at: datetime
  updated_at: datetime
```
Adjustable params live inside the spec, not as columns.

### Spec schema (whitelist — the safety boundary)

```
StrategySpec:
  indicators: [ { id: str, kind: IndicatorKind, args: dict } ]
  entry: ConditionTree          # true → buy
  exit:  ConditionTree          # true → sell
  params: [ ParamDef ]

IndicatorKind ∈ { rsi, sma, ema, macd, bollinger_hi, bollinger_lo, close, volume }

ConditionTree =
    Comparison { left: Operand, op: CmpOp, right: Operand }
  | Combinator { op: ("and"|"or"|"not"), children: [ConditionTree, ...] }

CmpOp ∈ { lt, le, gt, ge, cross_above, cross_below, between }
Operand = { indicator: id } | { param: name } | { literal: number }
ParamDef = { name, type: ("int"|"float"), default, min?, max?, step? }
```

Covers all 4 existing strategies (RSI / MA-cross / MACD / Bollinger) plus most retail TA.
Unknown `kind`/`op`, unresolved param-refs, over-depth trees, out-of-range literals → rejected.

### Interpreter (`SpecStrategy`)

On each candle window: compute the declared indicators (reusing the existing `ta`-based
indicator functions), evaluate `entry` → if true `buy`; else `exit` → if true `sell`; else
`hold`. Emits the existing `Signal` (action + `confidence` + rationale). **Confidence:** a
fired condition yields `confidence = 1.0`, `hold` yields `0.0` (simple, deterministic; a
richer distance-from-threshold score is future work). This keeps the canvas "IF 信心 ≥ x"
gate meaningful for spec strategies. Insufficient candles for a period → fail loud.

### Strategy node change (backward compatible)

The workflow `strategy` node `params` gains optional `strategy_id` + `param_overrides`
alongside the current built-in `name`. `build_strategy` path: a library id → load spec →
`SpecStrategy(param_overrides)`; a built-in name → unchanged.

## AI strategy agent (`ai/strategy_agent.py`)

Same pattern as `ai/signal_agent.py`:

- **Input** `(user_message, prior_spec?)`; **output** (Claude structured output) a
  `StrategySpec` + plain-language `explanation`.
- **Stateless backend conversation**: the frontend passes `prior_spec` back each turn;
  refine requests (“RSI 改 28、加停損 3%”) return the updated spec. The saved artifact is the
  strategy, not the chat.
- **Mechanical work stays out of the model**: Claude emits only the spec + explanation; the
  `spec → Python` render and all validation happen in code.
- **Strict validation**: model output parsed through the same pydantic schema; invalid → one
  bounded re-ask → surface the error. No silent fallback.
- **Offline/test mode**: deterministic mock mapping so tests run without `ANTHROPIC_API_KEY`.

## API (`api/strategies.py`) — return-the-model + fail-loud `HTTPException`, matching the codebase

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/strategies/design` | AI: `{message, prior_spec?}` → `{spec, rendered_python, explanation}`; 422 if no API key |
| GET | `/api/strategies` | List library |
| POST | `/api/strategies` | Save `{name, description?, spec}` (validated) |
| GET | `/api/strategies/{id}` | Fetch (full spec + rendered python) |
| PUT | `/api/strategies/{id}` | Rename / replace spec (re-validated) |
| DELETE | `/api/strategies/{id}` | Remove |
| POST | `/api/strategies/{id}/backtest` | Reuse backtest engine with `SpecStrategy` + `param_overrides` |

策略室 flow: chat → `design` → preview rendered Python + adjustable params → optional
`{id}/backtest` → `POST /api/strategies` to save → appears in library + as a draggable
strategy node in 交易室. Library CRUD + backtest work with no API key (only AI generation
needs the key).

## Error handling & safety

- Spec validation at the boundary (shared by API + agent); fail loud, no coercion.
- No `eval`/`exec`/`import` anywhere; rendered Python is display-only.
- Missing `ANTHROPIC_API_KEY` → `/design` 422; everything else still works.
- Param overrides validated against the spec's param defs (type + min/max).
- Live trading reuses the existing `trading/execution.py` → `RiskGuard` choke point; no
  special live path. (Future optional: warn if a strategy was never backtested before live.)
- Insufficient candles → fail loud. DB: 404 on missing id, 400 on invalid spec.

## Test plan (pytest, business-logic; adds to current 70, target ≥80%)

1. Spec validation — valid accepted; unknown indicator/op, unresolved param-ref, over-depth,
   out-of-range rejected.
2. Interpreter — every indicator + op (incl. `cross_above/below`), AND/OR/NOT,
   entry→buy / exit→sell / neither→hold, insufficient-data fail-loud.
3. Equivalence — a spec reproducing built-in RSI (and MA-cross) yields identical signals.
4. AI agent — offline mock → valid spec; refine with `prior_spec` updates correct field;
   invalid output → re-ask path.
5. Renderer — `spec → python` deterministic snapshot referencing spec indicators/params.
6. API — CRUD + 404/validation; `/design` no key → 422; `/{id}/backtest` returns
   equity+metrics; `param_overrides` applied.
7. Integration — `strategy` node with `strategy_id` + overrides → paper order end-to-end.
8. Backward-compat — built-in strategy path untouched; existing 70 tests stay green.

## Out of scope (separate specs)

- **A** — frontend shell: tree menu, two rooms, RWD, DESIGN.md token wiring, workflow-builder
  palette/canvas/inspector UI.
- **C** — workflow logic nodes (IF / AND / OR) in engine + builder.
- Multi-user/auth; real-broker live trading for 台股/美股.

## New files / touch points

- New: `models.py` (`StrategyDef`), `app/strategies/spec.py` (schema + `SpecStrategy` +
  renderer), `app/ai/strategy_agent.py`, `app/api/strategies.py`, tests under `app/tests/`.
- Touch: `app/strategies/registry.py` (build-from-library path), `app/workflow/nodes.py`
  (strategy node `strategy_id`/`param_overrides`), `app/main.py` (mount router), `db.py`
  (table create).
