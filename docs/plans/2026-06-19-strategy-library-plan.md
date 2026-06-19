# 策略庫 + AI 產生策略後端 Implementation Plan (Sub-project B)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users save AI-generated, parameterized trading strategies to a reusable library and run them in backtest/paper/live exactly like the built-in strategies — without ever executing model-written code.

**Architecture:** An AI strategy is a validated JSON `StrategySpec` (whitelisted indicators + condition trees). A `SpecStrategy` adapter interprets the spec and implements the existing `Strategy` interface, so the workflow engine and backtester are untouched. A pure renderer turns the spec into display-only Python. New `StrategyDef` table + `/api/strategies` CRUD + AI `design` endpoint.

**Tech Stack:** Python 3.13, FastAPI, SQLModel (SQLite), pydantic v2, pandas, `ta`, Anthropic SDK (structured outputs via `messages.parse(output_format=...)`), pytest.

**Spec:** [`docs/specs/2026-06-19-strategy-library-design.md`](../specs/2026-06-19-strategy-library-design.md)

## Global Constraints

- Backend Python ≥ 3.11 (runs on 3.13); snake_case; match existing module style.
- NO `eval`/`exec`/`import` of model output. The rendered Python is display-only and never run.
- Fail loud everywhere (CLAUDE.md): validate at boundaries, raise with clear messages, never silently degrade.
- Strategy/AI nodes emit the existing `app.schemas.Signal` (`action, confidence, reason, source`).
- All new tests are business-logic tests; the existing 70 tests must stay green. Run from `backend/` with `.venv/bin/python -m pytest -q`.
- AI features require `ANTHROPIC_API_KEY`; absence is a fail-loud 422 on `/design`, never a crash elsewhere.

---

## File Structure

- Create `app/strategies/spec.py` — `StrategySpec` schema + validation + `SpecStrategy` interpreter.
- Create `app/strategies/spec_render.py` — pure `render_python(spec) -> str`.
- Create `app/strategies/library.py` — persistence helpers over `StrategyDef`.
- Create `app/ai/strategy_agent.py` — `design_strategy(message, prior_spec)` (Claude structured output).
- Create `app/api/strategies.py` — `/api/strategies` router.
- Modify `app/models.py` — add `StrategyDef` table.
- Modify `app/strategies/indicators.py` — add `ema` helper.
- Modify `app/workflow/nodes.py` — strategy node accepts `strategy_id` + `param_overrides`.
- Modify `app/main.py` — mount the strategies router.
- Tests under `app/tests/`.

---

## Task 1: StrategySpec schema + validation

**Files:**
- Create: `backend/app/strategies/spec.py`
- Test: `backend/app/tests/test_strategy_spec.py`

**Interfaces:**
- Produces: `StrategySpec`, `IndicatorDef`, `IndicatorKind`, `CmpOp`, `BoolOp`, `ParamDef`,
  `Comparison`, `Combinator`, `ConditionTree`, and operand types `IndicatorRef`/`ParamRef`/`LiteralRef`.
  `StrategySpec.model_validate(dict)` raises `pydantic.ValidationError` on bad refs/depth.

- [ ] **Step 1: Write the failing test**

```python
# backend/app/tests/test_strategy_spec.py
"""Validation tests for the declarative StrategySpec."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.strategies.spec import StrategySpec


def _rsi_spec() -> dict:
    return {
        "indicators": [{"id": "r", "kind": "rsi", "args": {"window": {"type": "param", "ref": "win"}}}],
        "entry": {"kind": "cmp", "left": {"type": "indicator", "ref": "r"},
                  "op": "lt", "right": {"type": "param", "ref": "th"}},
        "exit": {"kind": "cmp", "left": {"type": "indicator", "ref": "r"},
                 "op": "gt", "right": {"type": "literal", "value": 70}},
        "params": [
            {"name": "win", "type": "int", "default": 14, "min": 2, "max": 100},
            {"name": "th", "type": "float", "default": 28, "min": 1, "max": 99},
        ],
    }


def test_valid_spec_accepted():
    spec = StrategySpec.model_validate(_rsi_spec())
    assert spec.indicators[0].kind.value == "rsi"


def test_unknown_indicator_kind_rejected():
    bad = _rsi_spec()
    bad["indicators"][0]["kind"] = "supertrend"
    with pytest.raises(ValidationError):
        StrategySpec.model_validate(bad)


def test_unresolved_indicator_ref_rejected():
    bad = _rsi_spec()
    bad["entry"]["left"] = {"type": "indicator", "ref": "missing"}
    with pytest.raises(ValidationError):
        StrategySpec.model_validate(bad)


def test_unresolved_param_ref_rejected():
    bad = _rsi_spec()
    bad["entry"]["right"] = {"type": "param", "ref": "nope"}
    with pytest.raises(ValidationError):
        StrategySpec.model_validate(bad)


def test_duplicate_indicator_ids_rejected():
    bad = _rsi_spec()
    bad["indicators"].append(bad["indicators"][0])
    with pytest.raises(ValidationError):
        StrategySpec.model_validate(bad)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest app/tests/test_strategy_spec.py -q`
Expected: FAIL with `ModuleNotFoundError: app.strategies.spec`.

- [ ] **Step 3: Write minimal implementation (schema only — interpreter comes in Task 2)**

```python
# backend/app/strategies/spec.py
"""Declarative strategy spec — the validated, never-executed representation of a strategy.

A StrategySpec is whitelisted indicators + boolean condition trees over comparisons.
The interpreter (SpecStrategy, below in Task 2) turns it into a Signal.
"""
from __future__ import annotations

import enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, model_validator

MAX_INDICATORS = 16
MAX_PARAMS = 16
MAX_TREE_DEPTH = 6


class IndicatorKind(str, enum.Enum):
    rsi = "rsi"
    sma = "sma"
    ema = "ema"
    macd = "macd"            # macd line
    bollinger_hi = "bollinger_hi"
    bollinger_lo = "bollinger_lo"
    close = "close"
    volume = "volume"


class CmpOp(str, enum.Enum):
    lt = "lt"
    le = "le"
    gt = "gt"
    ge = "ge"
    cross_above = "cross_above"
    cross_below = "cross_below"
    between = "between"


class BoolOp(str, enum.Enum):
    and_ = "and"
    or_ = "or"
    not_ = "not"


class IndicatorRef(BaseModel):
    type: Literal["indicator"] = "indicator"
    ref: str


class ParamRef(BaseModel):
    type: Literal["param"] = "param"
    ref: str


class LiteralRef(BaseModel):
    type: Literal["literal"] = "literal"
    value: float


Operand = Annotated[Union[IndicatorRef, ParamRef, LiteralRef], Field(discriminator="type")]


class ParamDef(BaseModel):
    name: str
    type: Literal["int", "float"]
    default: float
    min: float | None = None
    max: float | None = None
    step: float | None = None


class IndicatorDef(BaseModel):
    id: str
    kind: IndicatorKind
    args: dict[str, Union[float, ParamRef]] = Field(default_factory=dict)


class Comparison(BaseModel):
    kind: Literal["cmp"] = "cmp"
    left: Operand
    op: CmpOp
    right: Operand
    right2: Operand | None = None  # upper bound for 'between'


class Combinator(BaseModel):
    kind: Literal["bool"] = "bool"
    op: BoolOp
    children: list["ConditionTree"] = Field(min_length=1)


ConditionTree = Annotated[Union[Comparison, Combinator], Field(discriminator="kind")]


def _tree_depth(node: "ConditionTree", depth: int = 1) -> int:
    if isinstance(node, Combinator):
        return max((_tree_depth(c, depth + 1) for c in node.children), default=depth)
    return depth


def _operand_refs(op: Operand) -> tuple[set[str], set[str]]:
    """Return (indicator_refs, param_refs) used by an operand."""
    if isinstance(op, IndicatorRef):
        return {op.ref}, set()
    if isinstance(op, ParamRef):
        return set(), {op.ref}
    return set(), set()


def _collect_refs(node: "ConditionTree") -> tuple[set[str], set[str]]:
    inds: set[str] = set()
    params: set[str] = set()
    if isinstance(node, Comparison):
        for operand in (node.left, node.right, node.right2):
            if operand is not None:
                i, p = _operand_refs(operand)
                inds |= i
                params |= p
    else:
        for child in node.children:
            i, p = _collect_refs(child)
            inds |= i
            params |= p
    return inds, params


class StrategySpec(BaseModel):
    indicators: list[IndicatorDef] = Field(min_length=1, max_length=MAX_INDICATORS)
    entry: ConditionTree
    exit: ConditionTree
    params: list[ParamDef] = Field(default_factory=list, max_length=MAX_PARAMS)

    @model_validator(mode="after")
    def _validate_refs(self) -> "StrategySpec":
        ind_ids = [i.id for i in self.indicators]
        if len(ind_ids) != len(set(ind_ids)):
            raise ValueError("indicator ids must be unique")
        param_names = {p.name for p in self.params}
        if len(param_names) != len(self.params):
            raise ValueError("param names must be unique")

        known_inds = set(ind_ids)
        # indicator args may reference params
        for ind in self.indicators:
            for arg in ind.args.values():
                if isinstance(arg, ParamRef) and arg.ref not in param_names:
                    raise ValueError(f"indicator '{ind.id}' arg references unknown param '{arg.ref}'")

        for tree_name, tree in (("entry", self.entry), ("exit", self.exit)):
            if _tree_depth(tree) > MAX_TREE_DEPTH:
                raise ValueError(f"{tree_name} tree exceeds max depth {MAX_TREE_DEPTH}")
            inds, params = _collect_refs(tree)
            missing_i = inds - known_inds
            missing_p = params - param_names
            if missing_i:
                raise ValueError(f"{tree_name} references unknown indicators: {sorted(missing_i)}")
            if missing_p:
                raise ValueError(f"{tree_name} references unknown params: {sorted(missing_p)}")
        return self
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest app/tests/test_strategy_spec.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/strategies/spec.py backend/app/tests/test_strategy_spec.py
git commit -m "feat(strategy): declarative StrategySpec schema + validation"
```

---

## Task 2: SpecStrategy interpreter (+ `ema` indicator)

**Files:**
- Modify: `backend/app/strategies/indicators.py` (add `ema`)
- Modify: `backend/app/strategies/spec.py` (add `SpecStrategy`)
- Test: `backend/app/tests/test_spec_strategy.py`

**Interfaces:**
- Consumes: `StrategySpec` (Task 1), `app.strategies.indicators` (`rsi/sma/ema/macd/bollinger/candles_to_df`), `app.schemas.Signal/SignalAction/Candle`, `app.strategies.base.Strategy`.
- Produces: `SpecStrategy(spec: StrategySpec, overrides: dict | None = None)` implementing
  `Strategy.generate(candles) -> Signal`. Fired condition → `confidence 1.0`, hold → `0.0`.
  Invalid override (unknown name / out of min-max) → `ValueError`. Insufficient candles → `ValueError`.

- [ ] **Step 1: Write the failing test**

```python
# backend/app/tests/test_spec_strategy.py
"""Interpreter tests for SpecStrategy + equivalence to the built-in RSI strategy."""
from __future__ import annotations

import pytest

from app.schemas import SignalAction
from app.strategies.rsi import RsiStrategy
from app.strategies.spec import SpecStrategy, StrategySpec
from app.tests.helpers import make_candles


def _rsi_reversion() -> StrategySpec:
    return StrategySpec.model_validate({
        "indicators": [{"id": "r", "kind": "rsi", "args": {"window": {"type": "param", "ref": "win"}}}],
        "entry": {"kind": "cmp", "left": {"type": "indicator", "ref": "r"},
                  "op": "le", "right": {"type": "param", "ref": "os"}},
        "exit": {"kind": "cmp", "left": {"type": "indicator", "ref": "r"},
                 "op": "ge", "right": {"type": "param", "ref": "ob"}},
        "params": [
            {"name": "win", "type": "int", "default": 14},
            {"name": "os", "type": "float", "default": 30, "min": 1, "max": 99},
            {"name": "ob", "type": "float", "default": 70, "min": 1, "max": 99},
        ],
    })


def test_spec_matches_builtin_rsi():
    # falling then rising series exercises oversold buy + neutral/overbought
    prices = [float(p) for p in list(range(100, 60, -1)) + list(range(60, 100))]
    candles = make_candles(prices)
    spec_sig = SpecStrategy(_rsi_reversion()).generate(candles)
    builtin_sig = RsiStrategy(window=14, oversold=30.0, overbought=70.0).generate(candles)
    assert spec_sig.action == builtin_sig.action


def test_override_applies_and_validates():
    spec = _rsi_reversion()
    strat = SpecStrategy(spec, overrides={"os": 40})
    assert strat.params["os"] == 40
    with pytest.raises(ValueError):
        SpecStrategy(spec, overrides={"os": 999})   # out of [1, 99]
    with pytest.raises(ValueError):
        SpecStrategy(spec, overrides={"nope": 1})    # unknown param


def test_hold_has_zero_confidence():
    spec = _rsi_reversion()
    sig = SpecStrategy(spec, overrides={"os": 0.01, "ob": 99.99}).generate(make_candles([100.0] * 40))
    assert sig.action == SignalAction.hold
    assert sig.confidence == 0.0


def test_insufficient_candles_fails_loud():
    with pytest.raises(ValueError):
        SpecStrategy(_rsi_reversion()).generate(make_candles([100.0, 101.0]))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest app/tests/test_spec_strategy.py -q`
Expected: FAIL with `ImportError: cannot import name 'SpecStrategy'`.

- [ ] **Step 3a: Add the `ema` helper to indicators.py**

```python
# backend/app/strategies/indicators.py — add import + function
from ta.trend import EMAIndicator  # add to existing ta.trend import line

def ema(close: pd.Series, window: int) -> pd.Series:
    return EMAIndicator(close, window=window).ema_indicator()
```

- [ ] **Step 3b: Append `SpecStrategy` to spec.py**

```python
# backend/app/strategies/spec.py — append
import pandas as pd

from app.schemas import Candle, Signal, SignalAction
from app.strategies.base import Strategy
from app.strategies import indicators as ind


class SpecStrategy(Strategy):
    """Interprets a StrategySpec into a Signal. Never executes generated code."""

    def __init__(self, spec: StrategySpec, overrides: dict | None = None) -> None:
        self.spec = spec
        self.name = "spec"
        self.params: dict[str, float] = {p.name: p.default for p in spec.params}
        defs = {p.name: p for p in spec.params}
        for key, value in (overrides or {}).items():
            if key not in defs:
                raise ValueError(f"unknown param override '{key}'")
            d = defs[key]
            if d.min is not None and value < d.min:
                raise ValueError(f"param '{key}'={value} below min {d.min}")
            if d.max is not None and value > d.max:
                raise ValueError(f"param '{key}'={value} above max {d.max}")
            self.params[key] = int(value) if d.type == "int" else float(value)

    def _arg(self, value) -> float:
        return self.params[value.ref] if isinstance(value, ParamRef) else float(value)

    def _series(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        out: dict[str, pd.Series] = {}
        close = df["close"]
        for i in self.spec.indicators:
            a = {k: self._arg(v) for k, v in i.args.items()}
            if i.kind == IndicatorKind.rsi:
                out[i.id] = ind.rsi(close, int(a.get("window", 14)))
            elif i.kind == IndicatorKind.sma:
                out[i.id] = ind.sma(close, int(a.get("window", 20)))
            elif i.kind == IndicatorKind.ema:
                out[i.id] = ind.ema(close, int(a.get("window", 20)))
            elif i.kind == IndicatorKind.macd:
                out[i.id] = ind.macd(close)[0]
            elif i.kind == IndicatorKind.bollinger_hi:
                out[i.id] = ind.bollinger(close, int(a.get("window", 20)))[0]
            elif i.kind == IndicatorKind.bollinger_lo:
                out[i.id] = ind.bollinger(close, int(a.get("window", 20)))[2]
            elif i.kind == IndicatorKind.close:
                out[i.id] = close
            elif i.kind == IndicatorKind.volume:
                out[i.id] = df["volume"]
        return out

    def _val(self, operand: Operand, series: dict[str, pd.Series], df: pd.DataFrame, back: int) -> float:
        if isinstance(operand, IndicatorRef):
            return float(series[operand.ref].iloc[-1 - back])
        if isinstance(operand, ParamRef):
            return self.params[operand.ref]
        return float(operand.value)

    def _eval(self, node: ConditionTree, series: dict[str, pd.Series], df: pd.DataFrame) -> bool:
        if isinstance(node, Combinator):
            if node.op == BoolOp.not_:
                return not self._eval(node.children[0], series, df)
            results = [self._eval(c, series, df) for c in node.children]
            return all(results) if node.op == BoolOp.and_ else any(results)
        left = self._val(node.left, series, df, 0)
        right = self._val(node.right, series, df, 0)
        if node.op == CmpOp.lt:
            return left < right
        if node.op == CmpOp.le:
            return left <= right
        if node.op == CmpOp.gt:
            return left > right
        if node.op == CmpOp.ge:
            return left >= right
        if node.op == CmpOp.between:
            upper = self._val(node.right2, series, df, 0) if node.right2 else right
            return min(right, upper) <= left <= max(right, upper)
        # cross: compare previous vs current bar
        prev_left = self._val(node.left, series, df, 1)
        prev_right = self._val(node.right, series, df, 1)
        if node.op == CmpOp.cross_above:
            return prev_left <= prev_right and left > right
        return prev_left >= prev_right and left < right  # cross_below

    def generate(self, candles: list[Candle]) -> Signal:
        df = ind.candles_to_df(candles)
        if len(df) < 3:
            raise ValueError(f"spec strategy needs at least 3 candles, got {len(df)}")
        series = self._series(df)
        for sid, s in series.items():
            if s.iloc[-2:].isna().any():
                raise ValueError(f"indicator '{sid}' has insufficient data for its window")
        if self._eval(self.spec.entry, series, df):
            return Signal(action=SignalAction.buy, confidence=1.0, reason="entry condition met", source=self.name)
        if self._eval(self.spec.exit, series, df):
            return Signal(action=SignalAction.sell, confidence=1.0, reason="exit condition met", source=self.name)
        return Signal(action=SignalAction.hold, confidence=0.0, reason="no condition met", source=self.name)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest app/tests/test_spec_strategy.py -q`
Expected: PASS (4 passed). Then run the full suite to confirm no regressions:
`cd backend && .venv/bin/python -m pytest -q` → all prior + new pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/strategies/spec.py backend/app/strategies/indicators.py backend/app/tests/test_spec_strategy.py
git commit -m "feat(strategy): SpecStrategy interpreter + ema indicator"
```

---

## Task 3: spec → Python renderer (display-only)

**Files:**
- Create: `backend/app/strategies/spec_render.py`
- Test: `backend/app/tests/test_spec_render.py`

**Interfaces:**
- Consumes: `StrategySpec` and its node/operand types (Task 1).
- Produces: `render_python(spec: StrategySpec) -> str` — deterministic, references the spec's
  indicator ids and param names. Pure string; never executed.

- [ ] **Step 1: Write the failing test**

```python
# backend/app/tests/test_spec_render.py
from __future__ import annotations

from app.strategies.spec import StrategySpec
from app.strategies.spec_render import render_python


def _spec() -> StrategySpec:
    return StrategySpec.model_validate({
        "indicators": [{"id": "r", "kind": "rsi", "args": {"window": {"type": "param", "ref": "win"}}}],
        "entry": {"kind": "cmp", "left": {"type": "indicator", "ref": "r"},
                  "op": "lt", "right": {"type": "param", "ref": "th"}},
        "exit": {"kind": "cmp", "left": {"type": "indicator", "ref": "r"},
                 "op": "gt", "right": {"type": "literal", "value": 70}},
        "params": [{"name": "win", "type": "int", "default": 14},
                   {"name": "th", "type": "float", "default": 28}],
    })


def test_render_is_deterministic_and_references_spec():
    code = render_python(_spec())
    assert code == render_python(_spec())          # deterministic
    assert "def generate_signal" in code
    assert "win=14" in code and "th=28" in code     # params with defaults
    assert "rsi" in code and "return \"buy\"" in code
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest app/tests/test_spec_render.py -q`
Expected: FAIL with `ModuleNotFoundError: app.strategies.spec_render`.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/strategies/spec_render.py
"""Render a StrategySpec into human-readable Python. DISPLAY ONLY — never executed."""
from __future__ import annotations

from app.strategies.spec import (
    Combinator,
    Comparison,
    ConditionTree,
    IndicatorRef,
    LiteralRef,
    ParamRef,
    StrategySpec,
)

_OPS = {"lt": "<", "le": "<=", "gt": ">", "ge": ">="}


def _operand(op) -> str:
    if isinstance(op, IndicatorRef):
        return op.ref
    if isinstance(op, ParamRef):
        return op.ref
    return repr(op.value)


def _cond(node: ConditionTree) -> str:
    if isinstance(node, Comparison):
        if node.op.value in _OPS:
            return f"{_operand(node.left)} {_OPS[node.op.value]} {_operand(node.right)}"
        if node.op.value == "between":
            up = _operand(node.right2) if node.right2 else _operand(node.right)
            return f"{_operand(node.right)} <= {_operand(node.left)} <= {up}"
        return f"{node.op.value}({_operand(node.left)}, {_operand(node.right)})"
    if node.op.value == "not":
        return f"not ({_cond(node.children[0])})"
    joiner = f" {node.op.value} "
    return "(" + joiner.join(_cond(c) for c in node.children) + ")"


def render_python(spec: StrategySpec) -> str:
    args = ", ".join(f"{p.name}={int(p.default) if p.type == 'int' else p.default}" for p in spec.params)
    lines = [f"def generate_signal(df, {args}):" if args else "def generate_signal(df):"]
    for ind in spec.indicators:
        a = ", ".join(f"{k}={v.ref if isinstance(v, ParamRef) else v}" for k, v in ind.args.items())
        lines.append(f"    {ind.id} = {ind.kind.value}(df, {a})")
    lines.append(f"    if {_cond(spec.entry)}:")
    lines.append('        return "buy"')
    lines.append(f"    if {_cond(spec.exit)}:")
    lines.append('        return "sell"')
    lines.append('    return "hold"')
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest app/tests/test_spec_render.py -q`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/strategies/spec_render.py backend/app/tests/test_spec_render.py
git commit -m "feat(strategy): spec->python renderer (display only)"
```

---

## Task 4: StrategyDef model + library persistence

**Files:**
- Modify: `backend/app/models.py` (add `StrategyDef`)
- Create: `backend/app/strategies/library.py`
- Test: `backend/app/tests/test_strategy_library.py`

**Interfaces:**
- Consumes: `StrategySpec` (Task 1), `app.db` (`engine`, `get_session`), SQLModel `Session`.
- Produces (all take an explicit `Session`):
  `save_strategy(session, name, spec, description="", source="manual") -> StrategyDef`,
  `list_strategies(session) -> list[StrategyDef]`,
  `get_strategy(session, sid) -> StrategyDef | None`,
  `update_strategy(session, sid, *, name=None, description=None, spec=None) -> StrategyDef`,
  `delete_strategy(session, sid) -> bool`,
  `load_spec(session, sid) -> StrategySpec` (raises `ValueError` if missing).

- [ ] **Step 1: Write the failing test**

```python
# backend/app/tests/test_strategy_library.py
from __future__ import annotations

import pytest
from sqlmodel import Session

from app.db import engine, init_db
from app.strategies import library
from app.strategies.spec import StrategySpec


def _spec() -> StrategySpec:
    return StrategySpec.model_validate({
        "indicators": [{"id": "c", "kind": "close", "args": {}}],
        "entry": {"kind": "cmp", "left": {"type": "indicator", "ref": "c"},
                  "op": "gt", "right": {"type": "literal", "value": 0}},
        "exit": {"kind": "cmp", "left": {"type": "indicator", "ref": "c"},
                 "op": "lt", "right": {"type": "literal", "value": 0}},
        "params": [],
    })


def test_crud_round_trip():
    init_db()
    with Session(engine) as s:
        created = library.save_strategy(s, "t1", _spec(), description="d", source="manual")
        assert created.id is not None
        assert library.get_strategy(s, created.id).name == "t1"
        assert any(x.id == created.id for x in library.list_strategies(s))
        loaded = library.load_spec(s, created.id)
        assert loaded.indicators[0].kind.value == "close"
        library.update_strategy(s, created.id, name="t2")
        assert library.get_strategy(s, created.id).name == "t2"
        assert library.delete_strategy(s, created.id) is True
        assert library.get_strategy(s, created.id) is None


def test_load_missing_fails_loud():
    init_db()
    with Session(engine) as s:
        with pytest.raises(ValueError):
            library.load_spec(s, 999999)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest app/tests/test_strategy_library.py -q`
Expected: FAIL with `ModuleNotFoundError: app.strategies.library`.

- [ ] **Step 3a: Add the `StrategyDef` table to models.py**

```python
# backend/app/models.py — append (uses existing _now, Field, Column, JSON, SQLModel imports)
class StrategyDef(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    description: str = ""
    spec_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    source: str = "manual"  # "ai" | "manual"
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
```

- [ ] **Step 3b: Write library.py**

```python
# backend/app/strategies/library.py
"""Persistence for saved strategies (StrategyDef <-> StrategySpec)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session, select

from app.models import StrategyDef
from app.strategies.spec import StrategySpec


def save_strategy(session: Session, name: str, spec: StrategySpec,
                  description: str = "", source: str = "manual") -> StrategyDef:
    row = StrategyDef(name=name, description=description,
                      spec_json=spec.model_dump(mode="json"), source=source)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_strategies(session: Session) -> list[StrategyDef]:
    return list(session.exec(select(StrategyDef)).all())


def get_strategy(session: Session, sid: int) -> StrategyDef | None:
    return session.get(StrategyDef, sid)


def update_strategy(session: Session, sid: int, *, name: str | None = None,
                    description: str | None = None, spec: StrategySpec | None = None) -> StrategyDef:
    row = session.get(StrategyDef, sid)
    if row is None:
        raise ValueError(f"strategy {sid} not found")
    if name is not None:
        row.name = name
    if description is not None:
        row.description = description
    if spec is not None:
        row.spec_json = spec.model_dump(mode="json")
    row.updated_at = datetime.now(timezone.utc)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def delete_strategy(session: Session, sid: int) -> bool:
    row = session.get(StrategyDef, sid)
    if row is None:
        return False
    session.delete(row)
    session.commit()
    return True


def load_spec(session: Session, sid: int) -> StrategySpec:
    row = session.get(StrategyDef, sid)
    if row is None:
        raise ValueError(f"strategy {sid} not found")
    return StrategySpec.model_validate(row.spec_json)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest app/tests/test_strategy_library.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/models.py backend/app/strategies/library.py backend/app/tests/test_strategy_library.py
git commit -m "feat(strategy): StrategyDef table + library persistence"
```

---

## Task 5: AI strategy agent

**Files:**
- Create: `backend/app/ai/strategy_agent.py`
- Test: `backend/app/tests/test_strategy_agent.py`

**Interfaces:**
- Consumes: `app.ai.claude_client.get_claude_client`, `app.config.settings`, `StrategySpec` (Task 1), `render_python` (Task 3).
- Produces: `StrategyDesignResponse(BaseModel)` with `spec: StrategySpec`, `explanation: str`;
  `design_strategy(message: str, prior_spec: StrategySpec | None = None, model: str | None = None) -> dict`
  returning `{"spec": StrategySpec, "rendered_python": str, "explanation": str}`. Unparseable model
  output → `RuntimeError`.

- [ ] **Step 1: Write the failing test**

```python
# backend/app/tests/test_strategy_agent.py
"""AI strategy agent with a mocked Claude client (no key/network)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.ai import strategy_agent
from app.ai.strategy_agent import StrategyDesignResponse, design_strategy
from app.strategies.spec import StrategySpec

_SPEC_DICT = {
    "indicators": [{"id": "r", "kind": "rsi", "args": {"window": {"type": "param", "ref": "win"}}}],
    "entry": {"kind": "cmp", "left": {"type": "indicator", "ref": "r"},
              "op": "lt", "right": {"type": "param", "ref": "th"}},
    "exit": {"kind": "cmp", "left": {"type": "indicator", "ref": "r"},
             "op": "gt", "right": {"type": "literal", "value": 70}},
    "params": [{"name": "win", "type": "int", "default": 14},
               {"name": "th", "type": "float", "default": 28}],
}


class FakeMessages:
    def __init__(self, parsed):
        self._parsed = parsed
        self.last_kwargs = None

    def parse(self, **kwargs):
        self.last_kwargs = kwargs
        return SimpleNamespace(parsed_output=self._parsed)


class FakeClient:
    def __init__(self, parsed):
        self.messages = FakeMessages(parsed)


def test_design_returns_spec_python_and_explanation(monkeypatch):
    parsed = StrategyDesignResponse(spec=StrategySpec.model_validate(_SPEC_DICT), explanation="RSI reversion")
    monkeypatch.setattr(strategy_agent, "get_claude_client", lambda: FakeClient(parsed))
    out = design_strategy("make an RSI strategy")
    assert isinstance(out["spec"], StrategySpec)
    assert out["explanation"] == "RSI reversion"
    assert "def generate_signal" in out["rendered_python"]


def test_prior_spec_is_sent_to_model(monkeypatch):
    parsed = StrategyDesignResponse(spec=StrategySpec.model_validate(_SPEC_DICT), explanation="updated")
    fake = FakeClient(parsed)
    monkeypatch.setattr(strategy_agent, "get_claude_client", lambda: fake)
    prior = StrategySpec.model_validate(_SPEC_DICT)
    design_strategy("change threshold to 28", prior_spec=prior)
    content = fake.messages.last_kwargs["messages"][0]["content"]
    assert "change threshold" in content


def test_unparseable_output_fails_loud(monkeypatch):
    monkeypatch.setattr(strategy_agent, "get_claude_client", lambda: FakeClient(None))
    with pytest.raises(RuntimeError):
        design_strategy("anything")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest app/tests/test_strategy_agent.py -q`
Expected: FAIL with `ModuleNotFoundError: app.ai.strategy_agent`.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/ai/strategy_agent.py
"""LLM strategy designer: natural language -> validated StrategySpec (structured output).

Claude returns ONLY the spec + explanation. The spec->python render and all validation
happen in code (CLAUDE.md: keep mechanical work out of the model). The spec is never executed.
"""
from __future__ import annotations

from pydantic import BaseModel

from app.ai.claude_client import get_claude_client
from app.config import settings
from app.strategies.spec import StrategySpec
from app.strategies.spec_render import render_python

_SYSTEM_PROMPT = (
    "You design trading strategies as a STRICT declarative spec. Output only a StrategySpec "
    "(whitelisted indicators rsi/sma/ema/macd/bollinger_hi/bollinger_lo/close/volume; condition "
    "trees of comparisons and and/or/not) plus a one-paragraph explanation. Expose tunable numbers "
    "as params with sensible default/min/max. Do not write Python; do not invent indicators."
)


class StrategyDesignResponse(BaseModel):
    spec: StrategySpec
    explanation: str


def design_strategy(message: str, prior_spec: StrategySpec | None = None,
                    model: str | None = None) -> dict:
    model = model or settings.ai_model
    client = get_claude_client()
    content = message
    if prior_spec is not None:
        content = (
            f"Current strategy spec (JSON):\n{prior_spec.model_dump_json()}\n\n"
            f"Requested change: {message}"
        )
    response = client.messages.parse(
        model=model,
        max_tokens=2048,
        thinking={"type": "adaptive"},
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
        output_format=StrategyDesignResponse,
    )
    out = response.parsed_output
    if out is None:
        raise RuntimeError("AI strategy could not be parsed from the model response")
    return {
        "spec": out.spec,
        "rendered_python": render_python(out.spec),
        "explanation": out.explanation,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest app/tests/test_strategy_agent.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/ai/strategy_agent.py backend/app/tests/test_strategy_agent.py
git commit -m "feat(ai): strategy design agent (NL -> StrategySpec)"
```

---

## Task 6: Workflow strategy node accepts `strategy_id` + `param_overrides`

**Files:**
- Modify: `backend/app/workflow/nodes.py` (`_run_strategy`)
- Test: `backend/app/tests/test_workflow_spec_strategy.py`

**Interfaces:**
- Consumes: `library.load_spec` (Task 4), `SpecStrategy` (Task 2), existing `RunContext` (has `.session`), `build_strategy` (built-ins).
- Produces: `_run_strategy` behavior — if `node.params["strategy_id"]` present → load spec from DB
  (via `ctx.session`) + `SpecStrategy(spec, param_overrides)`; else unchanged built-in path.

- [ ] **Step 1: Write the failing test**

```python
# backend/app/tests/test_workflow_spec_strategy.py
from __future__ import annotations

from sqlmodel import Session

from app.db import engine, init_db
from app.strategies import library
from app.strategies.spec import StrategySpec
from app.workflow.nodes import RunContext, _run_strategy
from app.workflow.schema import NodeConfig, NodeType
from app.tests.helpers import make_candles


def _spec() -> StrategySpec:
    return StrategySpec.model_validate({
        "indicators": [{"id": "r", "kind": "rsi", "args": {"window": {"type": "literal", "value": 14}}}],
        "entry": {"kind": "cmp", "left": {"type": "indicator", "ref": "r"},
                  "op": "le", "right": {"type": "param", "ref": "os"}},
        "exit": {"kind": "cmp", "left": {"type": "indicator", "ref": "r"},
                 "op": "ge", "right": {"type": "literal", "value": 70}},
        "params": [{"name": "os", "type": "float", "default": 30, "min": 1, "max": 99}],
    })


def test_strategy_node_runs_library_spec_with_overrides():
    init_db()
    with Session(engine) as s:
        row = library.save_strategy(s, "lib-rsi", _spec(), source="ai")
        node = NodeConfig(id="n1", type=NodeType.strategy,
                          params={"strategy_id": row.id, "param_overrides": {"os": 35}})
        ctx = RunContext(session=s)
        prices = [float(p) for p in list(range(100, 60, -1)) + list(range(60, 100))]
        signal = _run_strategy(node, [make_candles(prices)], ctx)
        assert signal.source == "spec"


def test_builtin_strategy_path_unchanged():
    node = NodeConfig(id="n1", type=NodeType.strategy, params={"name": "rsi"})
    signal = _run_strategy(node, [make_candles([float(i) for i in range(1, 40)])], RunContext())
    assert signal.source == "rsi"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest app/tests/test_workflow_spec_strategy.py -q`
Expected: FAIL — library spec path not implemented (`source` != "spec" or KeyError).

- [ ] **Step 3: Update `_run_strategy` in nodes.py**

```python
# backend/app/workflow/nodes.py — replace _run_strategy with:
def _run_strategy(node: NodeConfig, inputs: list[Any], ctx: RunContext) -> Signal:
    candles = _first_candles(inputs)
    strategy_id = node.params.get("strategy_id")
    if strategy_id is not None:
        from app.strategies.library import load_spec
        from app.strategies.spec import SpecStrategy

        if ctx.session is None:
            raise ValueError("strategy node with strategy_id requires a DB session")
        spec = load_spec(ctx.session, int(strategy_id))
        overrides = node.params.get("param_overrides") or {}
        return SpecStrategy(spec, overrides).generate(candles)
    name = node.params.get("name", "ma_cross")
    kwargs = {k: v for k, v in node.params.items() if k != "name"}
    return build_strategy(name, kwargs).generate(candles)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest app/tests/test_workflow_spec_strategy.py -q`
Expected: PASS (2 passed). Then full suite: `cd backend && .venv/bin/python -m pytest -q`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/workflow/nodes.py backend/app/tests/test_workflow_spec_strategy.py
git commit -m "feat(workflow): strategy node supports library strategy_id + overrides"
```

---

## Task 7: `/api/strategies` router (CRUD + design + backtest) + mount

**Files:**
- Create: `backend/app/api/strategies.py`
- Modify: `backend/app/main.py` (import + `include_router`)
- Test: `backend/app/tests/test_strategies_api.py`

**Interfaces:**
- Consumes: `library` (Task 4), `design_strategy` (Task 5), `render_python` (Task 3), `SpecStrategy` (Task 2), `run_backtest` + `BacktestResult` (`app.backtest.engine`), `get_data_broker`, `get_session`, `StrategySpec`.
- Produces routes under `/api/strategies`: `GET ""`, `POST ""`, `GET /{sid}`, `PUT /{sid}`,
  `DELETE /{sid}`, `POST /design`, `POST /{sid}/backtest`.

- [ ] **Step 1: Write the failing test**

```python
# backend/app/tests/test_strategies_api.py
from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.ai import strategy_agent
from app.ai.strategy_agent import StrategyDesignResponse
from app.main import app
from app.strategies.spec import StrategySpec

client = TestClient(app)

_SPEC = {
    "indicators": [{"id": "r", "kind": "rsi", "args": {"window": {"type": "literal", "value": 14}}}],
    "entry": {"kind": "cmp", "left": {"type": "indicator", "ref": "r"},
              "op": "le", "right": {"type": "literal", "value": 30}},
    "exit": {"kind": "cmp", "left": {"type": "indicator", "ref": "r"},
             "op": "ge", "right": {"type": "literal", "value": 70}},
    "params": [],
}


def test_crud_and_validation():
    created = client.post("/api/strategies", json={"name": "rsi-lib", "spec": _SPEC})
    assert created.status_code == 200
    sid = created.json()["id"]
    assert any(s["id"] == sid for s in client.get("/api/strategies").json())
    assert client.get(f"/api/strategies/{sid}").json()["rendered_python"].startswith("def generate_signal")
    assert client.delete(f"/api/strategies/{sid}").status_code == 200
    assert client.get(f"/api/strategies/{sid}").status_code == 404
    # invalid spec rejected
    bad = {"name": "x", "spec": {**_SPEC, "indicators": [{"id": "r", "kind": "nope", "args": {}}]}}
    assert client.post("/api/strategies", json=bad).status_code == 422


def test_design_maps_agent_output(monkeypatch):
    parsed = StrategyDesignResponse(spec=StrategySpec.model_validate(_SPEC), explanation="ok")
    fake = SimpleNamespace(messages=SimpleNamespace(parse=lambda **k: SimpleNamespace(parsed_output=parsed)))
    monkeypatch.setattr(strategy_agent, "get_claude_client", lambda: fake)
    r = client.post("/api/strategies/design", json={"message": "rsi please"})
    assert r.status_code == 200
    assert r.json()["explanation"] == "ok"
    assert "rendered_python" in r.json()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest app/tests/test_strategies_api.py -q`
Expected: FAIL (404s — router not mounted).

- [ ] **Step 3a: Write the router**

```python
# backend/app/api/strategies.py
"""Strategy library: AI design, CRUD, and per-strategy backtest."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.ai.strategy_agent import design_strategy
from app.backtest.engine import BacktestResult, run_backtest
from app.brokers.registry import get_data_broker
from app.db import get_session
from app.schemas import MarketKind
from app.strategies import library
from app.strategies.spec import SpecStrategy, StrategySpec
from app.strategies.spec_render import render_python

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


class DesignRequest(BaseModel):
    message: str
    prior_spec: StrategySpec | None = None
    model: str | None = None


class SaveRequest(BaseModel):
    name: str
    description: str = ""
    spec: StrategySpec


class StrategyOut(BaseModel):
    id: int
    name: str
    description: str
    source: str
    spec: StrategySpec
    rendered_python: str


class StrategyListItem(BaseModel):
    id: int
    name: str
    description: str
    source: str
    num_params: int


def _to_out(row) -> StrategyOut:
    spec = StrategySpec.model_validate(row.spec_json)
    return StrategyOut(id=row.id, name=row.name, description=row.description,
                       source=row.source, spec=spec, rendered_python=render_python(spec))


@router.post("/design")
def design(req: DesignRequest) -> dict:
    try:
        out = design_strategy(req.message, prior_spec=req.prior_spec, model=req.model)
    except RuntimeError as exc:  # missing key / parse failure
        raise HTTPException(status_code=422, detail=str(exc))
    return {"spec": out["spec"], "rendered_python": out["rendered_python"],
            "explanation": out["explanation"]}


@router.get("", response_model=list[StrategyListItem])
def list_all(session: Session = Depends(get_session)) -> list[StrategyListItem]:
    items = []
    for row in library.list_strategies(session):
        spec = StrategySpec.model_validate(row.spec_json)
        items.append(StrategyListItem(id=row.id, name=row.name, description=row.description,
                                      source=row.source, num_params=len(spec.params)))
    return items


@router.post("", response_model=StrategyOut)
def create(req: SaveRequest, session: Session = Depends(get_session)) -> StrategyOut:
    row = library.save_strategy(session, req.name, req.spec, description=req.description, source="manual")
    return _to_out(row)


@router.get("/{sid}", response_model=StrategyOut)
def get_one(sid: int, session: Session = Depends(get_session)) -> StrategyOut:
    row = library.get_strategy(session, sid)
    if row is None:
        raise HTTPException(status_code=404, detail=f"strategy {sid} not found")
    return _to_out(row)


@router.put("/{sid}", response_model=StrategyOut)
def update(sid: int, req: SaveRequest, session: Session = Depends(get_session)) -> StrategyOut:
    try:
        row = library.update_strategy(session, sid, name=req.name,
                                      description=req.description, spec=req.spec)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _to_out(row)


@router.delete("/{sid}")
def remove(sid: int, session: Session = Depends(get_session)) -> dict:
    if not library.delete_strategy(session, sid):
        raise HTTPException(status_code=404, detail=f"strategy {sid} not found")
    return {"deleted": sid}


class StrategyBacktestRequest(BaseModel):
    symbol: str
    market: MarketKind = MarketKind.crypto
    timeframe: str = "1h"
    limit: int = Field(default=500, ge=10, le=1000)
    param_overrides: dict = Field(default_factory=dict)
    starting_cash: float = 100_000.0
    position_fraction: float = 1.0


@router.post("/{sid}/backtest", response_model=BacktestResult)
def backtest_one(sid: int, req: StrategyBacktestRequest,
                 session: Session = Depends(get_session)) -> BacktestResult:
    try:
        spec = library.load_spec(session, sid)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    try:
        strategy = SpecStrategy(spec, req.param_overrides)
        candles = get_data_broker(req.market).get_ohlcv(req.symbol, req.timeframe, req.limit)
        return run_backtest(candles, strategy, starting_cash=req.starting_cash,
                            position_fraction=req.position_fraction)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"{type(exc).__name__}: {exc}")
```

- [ ] **Step 3b: Mount the router in main.py**

```python
# backend/app/main.py
# 1) add `strategies` to the existing api import:
from app.api import ai, backtest, markets, notifications, orders, schedules, strategies, workflows
# 2) add after the other include_router calls:
app.include_router(strategies.router)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest app/tests/test_strategies_api.py -q`
Expected: PASS (2 passed). Then the full suite to confirm the whole sub-project is green:
`cd backend && .venv/bin/python -m pytest -q` (all prior 70 + new tests pass).

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/strategies.py backend/app/main.py backend/app/tests/test_strategies_api.py
git commit -m "feat(api): /api/strategies CRUD + AI design + per-strategy backtest"
```

---

## Self-Review

**Spec coverage:**
- Declarative spec + validation → Task 1. Interpreter + confidence + equivalence → Task 2.
- spec→python render → Task 3. `StrategyDef` + library → Task 4. AI agent (stateless, structured,
  offline mock) → Task 5. Strategy node `strategy_id`/`param_overrides` → Task 6.
  API (design/CRUD/backtest, fail-loud 422 no-key) → Task 7. All spec sections covered.
- Backward-compat: built-in path kept (Task 6 test `test_builtin_strategy_path_unchanged`); full
  suite re-run at Tasks 2, 6, 7.

**Deviations from spec (intentional, minor):** renderer split into `spec_render.py` and persistence
into `library.py` (the spec named a single `spec.py`) — keeps files focused per coding-style. Operands
use an explicit `type` tag (`{type:"indicator",ref:…}`) rather than the spec's `{indicator:id}`
shorthand, for robust pydantic discrimination.

**Placeholder scan:** none — every step has real code and exact commands.

**Type consistency:** `StrategySpec`, `SpecStrategy(spec, overrides)`, `design_strategy(...) -> dict`,
`library.load_spec(session, sid)`, `render_python(spec)` are used with identical signatures across tasks.

## Out of scope (separate plans)
- **A** frontend (tree menu, two rooms, RWD, DESIGN.md tokens, builder UI).
- **C** workflow logic nodes (IF/AND/OR).
