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
