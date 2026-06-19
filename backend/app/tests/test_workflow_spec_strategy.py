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
        "indicators": [{"id": "r", "kind": "rsi", "args": {"window": 14}}],
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
