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


# ---------------------------------------------------------------------------
# New render coverage tests
# ---------------------------------------------------------------------------

def _between_spec() -> StrategySpec:
    return StrategySpec.model_validate({
        "indicators": [{"id": "r", "kind": "rsi", "args": {"window": 14}}],
        "entry": {
            "kind": "cmp",
            "left": {"type": "indicator", "ref": "r"},
            "op": "between",
            "right": {"type": "literal", "value": 30},
            "right2": {"type": "literal", "value": 70},
        },
        "exit": {
            "kind": "cmp",
            "left": {"type": "indicator", "ref": "r"},
            "op": "gt",
            "right": {"type": "literal", "value": 80},
        },
        "params": [],
    })


def _cross_above_spec() -> StrategySpec:
    return StrategySpec.model_validate({
        "indicators": [
            {"id": "fast", "kind": "sma", "args": {"window": 5}},
            {"id": "slow", "kind": "sma", "args": {"window": 20}},
        ],
        "entry": {
            "kind": "cmp",
            "left": {"type": "indicator", "ref": "fast"},
            "op": "cross_above",
            "right": {"type": "indicator", "ref": "slow"},
        },
        "exit": {
            "kind": "cmp",
            "left": {"type": "indicator", "ref": "fast"},
            "op": "lt",
            "right": {"type": "literal", "value": 0},
        },
        "params": [],
    })


def _and_spec() -> StrategySpec:
    return StrategySpec.model_validate({
        "indicators": [{"id": "r", "kind": "rsi", "args": {"window": 14}}],
        "entry": {
            "kind": "bool",
            "op": "and",
            "children": [
                {"kind": "cmp", "left": {"type": "indicator", "ref": "r"},
                 "op": "gt", "right": {"type": "literal", "value": 30}},
                {"kind": "cmp", "left": {"type": "indicator", "ref": "r"},
                 "op": "lt", "right": {"type": "literal", "value": 70}},
            ],
        },
        "exit": {
            "kind": "cmp",
            "left": {"type": "indicator", "ref": "r"},
            "op": "gt",
            "right": {"type": "literal", "value": 80},
        },
        "params": [],
    })


def _or_spec() -> StrategySpec:
    return StrategySpec.model_validate({
        "indicators": [{"id": "r", "kind": "rsi", "args": {"window": 14}}],
        "entry": {
            "kind": "bool",
            "op": "or",
            "children": [
                {"kind": "cmp", "left": {"type": "indicator", "ref": "r"},
                 "op": "lt", "right": {"type": "literal", "value": 30}},
                {"kind": "cmp", "left": {"type": "indicator", "ref": "r"},
                 "op": "gt", "right": {"type": "literal", "value": 70}},
            ],
        },
        "exit": {
            "kind": "cmp",
            "left": {"type": "indicator", "ref": "r"},
            "op": "gt",
            "right": {"type": "literal", "value": 80},
        },
        "params": [],
    })


def _not_spec() -> StrategySpec:
    return StrategySpec.model_validate({
        "indicators": [{"id": "r", "kind": "rsi", "args": {"window": 14}}],
        "entry": {
            "kind": "bool",
            "op": "not",
            "children": [
                {"kind": "cmp", "left": {"type": "indicator", "ref": "r"},
                 "op": "gt", "right": {"type": "literal", "value": 80}},
            ],
        },
        "exit": {
            "kind": "cmp",
            "left": {"type": "indicator", "ref": "r"},
            "op": "gt",
            "right": {"type": "literal", "value": 80},
        },
        "params": [],
    })


def test_render_between_contains_range():
    code = render_python(_between_spec())
    assert "<=" in code


def test_render_cross_above_contains_call():
    code = render_python(_cross_above_spec())
    assert "cross_above(" in code


def test_render_and_combinator_contains_and():
    code = render_python(_and_spec())
    assert " and " in code


def test_render_or_combinator_contains_or():
    code = render_python(_or_spec())
    assert " or " in code


def test_render_not_combinator_contains_not():
    code = render_python(_not_spec())
    assert "not (" in code
