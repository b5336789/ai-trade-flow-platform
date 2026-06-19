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
