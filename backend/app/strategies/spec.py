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
