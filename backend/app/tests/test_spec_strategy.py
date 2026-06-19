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
    prices = [100.0 if i % 2 == 0 else 101.0 for i in range(40)]
    sig = SpecStrategy(spec, overrides={"os": 1, "ob": 99}).generate(make_candles(prices))
    assert sig.action == SignalAction.hold
    assert sig.confidence == 0.0


def test_insufficient_candles_fails_loud():
    with pytest.raises(ValueError):
        SpecStrategy(_rsi_reversion()).generate(make_candles([100.0, 101.0]))


# ---------------------------------------------------------------------------
# cross_above / cross_below
# ---------------------------------------------------------------------------

def _sma_cross_spec(fast_win: int, slow_win: int, op: str) -> StrategySpec:
    """Spec with two SMA indicators; entry uses cross_above/cross_below."""
    return StrategySpec.model_validate({
        "indicators": [
            {"id": "fast", "kind": "sma", "args": {"window": fast_win}},
            {"id": "slow", "kind": "sma", "args": {"window": slow_win}},
        ],
        "entry": {
            "kind": "cmp",
            "left": {"type": "indicator", "ref": "fast"},
            "op": op,
            "right": {"type": "indicator", "ref": "slow"},
        },
        # exit uses a condition that never fires for isolation
        "exit": {
            "kind": "cmp",
            "left": {"type": "indicator", "ref": "fast"},
            "op": "lt",
            "right": {"type": "literal", "value": 0},
        },
        "params": [],
    })


def test_cross_above_entry_fires_on_cross():
    # 15 bars: first 13 stable at 10.0, bar 13 still 10.0, bar 14 spikes to 30.0.
    # SMA3 prev=10, SMA8 prev=10  -> fast(prev) <= slow(prev)  ✓
    # SMA3 curr=mean(10,10,30)=16.67, SMA8 curr=mean(10,10,10,10,10,10,10,30)=12.5
    # -> fast(curr) > slow(curr)  ✓  => cross_above fires => buy
    prices = [10.0] * 13 + [10.0, 30.0]
    sig = SpecStrategy(_sma_cross_spec(3, 8, "cross_above")).generate(make_candles(prices))
    assert sig.action == SignalAction.buy


def test_cross_below_exit_fires_on_cross():
    # 15 bars: first 13 stable at 30.0, bar 13 still 30.0, bar 14 drops to 10.0.
    # SMA3 prev=30, SMA8 prev=30  -> fast(prev) >= slow(prev)  ✓
    # SMA3 curr=mean(30,30,10)=23.33, SMA8 curr=mean(30*7,10)=27.5
    # -> fast(curr) < slow(curr)  ✓  => cross_below fires
    # The cross_below is in the ENTRY condition so action is "buy"
    prices = [30.0] * 13 + [30.0, 10.0]
    spec = _sma_cross_spec(3, 8, "cross_below")
    sig = SpecStrategy(spec).generate(make_candles(prices))
    assert sig.action == SignalAction.buy


# ---------------------------------------------------------------------------
# between
# ---------------------------------------------------------------------------

def _between_spec(lo: float, ub: float) -> StrategySpec:
    """Spec with RSI entry = between(rsi, lo, ub); exit never fires."""
    return StrategySpec.model_validate({
        "indicators": [{"id": "r", "kind": "rsi", "args": {"window": 14}}],
        "entry": {
            "kind": "cmp",
            "left": {"type": "indicator", "ref": "r"},
            "op": "between",
            "right": {"type": "literal", "value": lo},
            "right2": {"type": "literal", "value": ub},
        },
        "exit": {
            "kind": "cmp",
            "left": {"type": "indicator", "ref": "r"},
            "op": "lt",
            "right": {"type": "literal", "value": 0},
        },
        "params": [],
    })


def test_between_entry_inside_band():
    # Alternating 100/101 → RSI ≈ 50, clearly inside [30, 70].
    prices = [100.0 if i % 2 == 0 else 101.0 for i in range(40)]
    sig = SpecStrategy(_between_spec(30, 70)).generate(make_candles(prices))
    assert sig.action == SignalAction.buy


def test_between_entry_outside_band():
    # Monotonically rising prices → RSI near 100, outside [30, 70].
    prices = [float(60 + i) for i in range(30)]
    sig = SpecStrategy(_between_spec(30, 70)).generate(make_candles(prices))
    assert sig.action != SignalAction.buy


# ---------------------------------------------------------------------------
# combinators: and / or / not
# ---------------------------------------------------------------------------

def _combinator_spec(op: str, left_lit: float, right_lit: float) -> StrategySpec:
    """Spec whose entry is a Combinator wrapping two literal comparisons.

    Both children are: close_ref >= literal  (using a 'close' indicator).
    We vary the literals so we can make each child true or false.
    """
    return StrategySpec.model_validate({
        "indicators": [{"id": "c", "kind": "close", "args": {}}],
        "entry": {
            "kind": "bool",
            "op": op,
            "children": [
                {
                    "kind": "cmp",
                    "left": {"type": "indicator", "ref": "c"},
                    "op": "gt",
                    "right": {"type": "literal", "value": left_lit},
                },
                {
                    "kind": "cmp",
                    "left": {"type": "indicator", "ref": "c"},
                    "op": "gt",
                    "right": {"type": "literal", "value": right_lit},
                },
            ],
        },
        "exit": {
            "kind": "cmp",
            "left": {"type": "indicator", "ref": "c"},
            "op": "lt",
            "right": {"type": "literal", "value": 0},
        },
        "params": [],
    })


def test_and_combinator():
    # close=50; both children: 50 > 10 (T) and 50 > 20 (T) -> AND fires -> buy
    prices = [50.0] * 10
    sig = SpecStrategy(_combinator_spec("and", 10, 20)).generate(make_candles(prices))
    assert sig.action == SignalAction.buy


def test_or_combinator():
    # close=50; children: 50 > 10 (T) and 50 > 60 (F) -> OR fires -> buy
    prices = [50.0] * 10
    sig = SpecStrategy(_combinator_spec("or", 10, 60)).generate(make_candles(prices))
    assert sig.action == SignalAction.buy


def test_not_combinator():
    # NOT wraps a single child that is FALSE -> fires -> buy.
    # We use a spec where the inner cmp is "close > 999" (false at close=50).
    spec = StrategySpec.model_validate({
        "indicators": [{"id": "c", "kind": "close", "args": {}}],
        "entry": {
            "kind": "bool",
            "op": "not",
            "children": [
                {
                    "kind": "cmp",
                    "left": {"type": "indicator", "ref": "c"},
                    "op": "gt",
                    "right": {"type": "literal", "value": 999},
                }
            ],
        },
        "exit": {
            "kind": "cmp",
            "left": {"type": "indicator", "ref": "c"},
            "op": "lt",
            "right": {"type": "literal", "value": 0},
        },
        "params": [],
    })
    prices = [50.0] * 10
    sig = SpecStrategy(spec).generate(make_candles(prices))
    assert sig.action == SignalAction.buy
