"""Render a StrategySpec into human-readable Python. DISPLAY ONLY — never executed."""
from __future__ import annotations

from app.strategies.spec import (
    Combinator,
    Comparison,
    ConditionTree,
    IndicatorRef,
    LiteralRef,
    ParamRef,
    StrategySpec,
)

_OPS = {"lt": "<", "le": "<=", "gt": ">", "ge": ">="}


def _operand(op) -> str:
    if isinstance(op, IndicatorRef):
        return op.ref
    if isinstance(op, ParamRef):
        return op.ref
    return repr(op.value)


def _cond(node: ConditionTree) -> str:
    if isinstance(node, Comparison):
        if node.op.value in _OPS:
            return f"{_operand(node.left)} {_OPS[node.op.value]} {_operand(node.right)}"
        if node.op.value == "between":
            up = _operand(node.right2) if node.right2 else _operand(node.right)
            return f"{_operand(node.right)} <= {_operand(node.left)} <= {up}"
        return f"{node.op.value}({_operand(node.left)}, {_operand(node.right)})"
    if node.op.value == "not":
        return f"not ({_cond(node.children[0])})"
    joiner = f" {node.op.value} "
    return "(" + joiner.join(_cond(c) for c in node.children) + ")"


def render_python(spec: StrategySpec) -> str:
    args = ", ".join(f"{p.name}={int(p.default) if p.type == 'int' else p.default}" for p in spec.params)
    lines = [f"def generate_signal(df, {args}):" if args else "def generate_signal(df):"]
    for ind in spec.indicators:
        a = ", ".join(f"{k}={v.ref if isinstance(v, ParamRef) else v}" for k, v in ind.args.items())
        lines.append(f"    {ind.id} = {ind.kind.value}(df, {a})")
    lines.append(f"    if {_cond(spec.entry)}:")
    lines.append('        return "buy"')
    lines.append(f"    if {_cond(spec.exit)}:")
    lines.append('        return "sell"')
    lines.append('    return "hold"')
    return "\n".join(lines)
