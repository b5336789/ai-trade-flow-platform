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
