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
