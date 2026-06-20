# backend/app/tests/test_strategy_agent.py
"""AI strategy agent with a mocked structured-completion boundary (no key/network)."""
from __future__ import annotations

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


def _patch(monkeypatch, parsed, captured=None):
    def fake(**kwargs):
        if captured is not None:
            captured.update(kwargs)
        return parsed
    monkeypatch.setattr(strategy_agent, "structured_completion", fake)


def test_design_returns_spec_python_and_explanation(monkeypatch):
    parsed = StrategyDesignResponse(spec=StrategySpec.model_validate(_SPEC_DICT), explanation="RSI reversion")
    _patch(monkeypatch, parsed)
    out = design_strategy("make an RSI strategy")
    assert isinstance(out["spec"], StrategySpec)
    assert out["explanation"] == "RSI reversion"
    assert "def generate_signal" in out["rendered_python"]


def test_prior_spec_is_sent_to_model(monkeypatch):
    parsed = StrategyDesignResponse(spec=StrategySpec.model_validate(_SPEC_DICT), explanation="updated")
    captured = {}
    _patch(monkeypatch, parsed, captured)
    prior = StrategySpec.model_validate(_SPEC_DICT)
    design_strategy("change threshold to 28", prior_spec=prior)
    assert "change threshold" in captured["content"]
    assert captured["output_model"] is StrategyDesignResponse
