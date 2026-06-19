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
