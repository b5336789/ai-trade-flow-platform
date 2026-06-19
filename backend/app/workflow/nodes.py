"""Node implementations + a registry mapping NodeType -> runner.

Each runner takes (node, upstream_inputs, context) and returns the value passed downstream.
Candle lists, Signals and OrderResults flow between nodes; indicator and AI nodes are
interchangeable because both emit a Signal.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any, Callable

from app.ai.signal_agent import generate_ai_signal
from app.brokers.registry import get_broker, get_data_broker
from app.schemas import (
    Candle,
    MarketKind,
    OrderRequest,
    OrderSide,
    Signal,
    SignalAction,
)
from app.strategies.registry import build_strategy
from app.trading.execution import execute_order
from app.workflow.schema import NodeConfig, NodeType

# Treat sub-unit quantity drift as "already at target" so float noise doesn't trigger churn.
_QTY_EPS = 1e-9


class RunContext:
    def __init__(self, session=None, run_id: str | None = None) -> None:
        self.session = session
        # Stable identity for this logical run; the order node folds it into a deterministic
        # client_order_id so re-running the SAME run (same run_id) is idempotent (M0.5).
        self.run_id = run_id or uuid.uuid4().hex
        self.scratch: dict[str, Any] = {}


def _client_order_id(run_id: str, node_id: str) -> str:
    """Deterministic idempotency key per (scheduled-run × order node)."""
    return hashlib.sha1(f"{run_id}:{node_id}".encode()).hexdigest()


def _first_candles(inputs: list[Any]) -> list[Candle]:
    for value in inputs:
        if isinstance(value, list) and value and isinstance(value[0], Candle):
            return value
    raise ValueError("node requires candle data from an upstream data_source")


def _signals(inputs: list[Any]) -> list[Signal]:
    return [value for value in inputs if isinstance(value, Signal)]


def _only_signal(inputs: list[Any]) -> Signal:
    """Return the single upstream Signal — fail loud if there are several.

    Unlike the old ``_first_signal`` (M2.1 bug), this never silently drops extra Signals: a node
    that expects ONE Signal must receive exactly one. To merge multiple Signals, wire them through
    a ``combine`` node first.
    """
    found = _signals(inputs)
    if not found:
        raise ValueError("node requires a Signal from an upstream strategy/ai_signal node")
    if len(found) > 1:
        raise ValueError(
            f"node received {len(found)} Signals but accepts one; "
            "route multiple Signals through a 'combine' node"
        )
    return found[0]


def _run_data_source(node: NodeConfig, inputs: list[Any], ctx: RunContext) -> list[Candle]:
    p = node.params
    if "symbol" not in p:
        raise ValueError("data_source node requires 'symbol'")
    symbol = p["symbol"]
    market = MarketKind(p.get("market", "crypto"))
    candles = get_data_broker(market).get_ohlcv(
        symbol, p.get("timeframe", "1h"), int(p.get("limit", 100))
    )
    ctx.scratch["symbol"] = symbol
    ctx.scratch["market"] = market
    return candles


def _run_strategy(node: NodeConfig, inputs: list[Any], ctx: RunContext) -> Signal:
    candles = _first_candles(inputs)
    name = node.params.get("name", "ma_cross")
    kwargs = {k: v for k, v in node.params.items() if k != "name"}
    return build_strategy(name, kwargs).generate(candles)


def _run_ai_signal(node: NodeConfig, inputs: list[Any], ctx: RunContext) -> Signal:
    candles = _first_candles(inputs)
    symbol = node.params.get("symbol") or ctx.scratch.get("symbol", "")
    return generate_ai_signal(symbol, candles, model=node.params.get("model"))


def _run_risk_exit(node: NodeConfig, inputs: list[Any], ctx: RunContext) -> Signal:
    """Emit a sell when the held position breaches stop-loss or take-profit, else hold.

    A threshold of 0 (or absent) disables that side. Needs candles upstream for the current price
    and reads the position's average cost from the (paper/live) broker.
    """
    candles = _first_candles(inputs)
    price = candles[-1].close
    p = node.params
    symbol = p.get("symbol") or ctx.scratch.get("symbol")
    if not symbol:
        raise ValueError("risk_exit node requires 'symbol' (or an upstream data_source)")
    market = MarketKind(p["market"]) if p.get("market") else ctx.scratch.get("market", MarketKind.crypto)
    stop_loss_pct = float(p.get("stop_loss_pct", 0) or 0)
    take_profit_pct = float(p.get("take_profit_pct", 0) or 0)

    broker = get_broker(market)
    position = next((pos for pos in broker.get_positions() if pos.symbol == symbol), None)
    if position is None or position.quantity <= 0 or position.avg_price <= 0:
        return Signal(action=SignalAction.hold, reason="no open position", source="risk_exit")

    pnl_pct = (price / position.avg_price - 1) * 100
    if stop_loss_pct > 0 and pnl_pct <= -stop_loss_pct:
        return Signal(
            action=SignalAction.sell,
            confidence=1.0,
            reason=f"stop-loss hit: {pnl_pct:.2f}% <= -{stop_loss_pct:.2f}%",
            source="risk_exit",
        )
    if take_profit_pct > 0 and pnl_pct >= take_profit_pct:
        return Signal(
            action=SignalAction.sell,
            confidence=1.0,
            reason=f"take-profit hit: {pnl_pct:.2f}% >= {take_profit_pct:.2f}%",
            source="risk_exit",
        )
    return Signal(
        action=SignalAction.hold,
        reason=f"within thresholds (P&L {pnl_pct:.2f}%)",
        source="risk_exit",
    )


def _run_order(node: NodeConfig, inputs: list[Any], ctx: RunContext):
    """Target-position semantics (M0.5).

    A Signal names a TARGET, not an action: buy => hold ``quantity`` units, sell => flat (0),
    hold => no-op. We read the current holding and trade only the delta to reach the target
    (long/flat only — never short). Already at target => no order, so repeated identical ticks
    are naturally idempotent.
    """
    signal = _only_signal(inputs)
    if signal.action == SignalAction.hold:
        return None
    p = node.params
    symbol = p.get("symbol") or ctx.scratch.get("symbol")
    if not symbol:
        raise ValueError("order node requires 'symbol' (or an upstream data_source)")
    market = MarketKind(p["market"]) if p.get("market") else ctx.scratch.get("market", MarketKind.crypto)

    target_qty = float(p.get("quantity", 1)) if signal.action == SignalAction.buy else 0.0

    broker = get_broker(market)
    held = next((pos.quantity for pos in broker.get_positions() if pos.symbol == symbol), 0.0)
    delta = target_qty - held
    if abs(delta) <= _QTY_EPS:
        return None  # already at target -> no-op (idempotent)

    side = OrderSide.buy if delta > 0 else OrderSide.sell
    request = OrderRequest(symbol=symbol, side=side, quantity=abs(delta))
    return execute_order(
        request,
        market=market,
        session=ctx.session,
        client_order_id=_client_order_id(ctx.run_id, node.id),
    )


def _run_combine(node: NodeConfig, inputs: list[Any], ctx: RunContext) -> Signal:
    """Reduce MULTIPLE upstream Signals into ONE (M2.1). Never silently drops a Signal.

    Modes (param ``mode``, default ``AND``); only buy/sell are "actionable", hold is neutral:

    - ``AND`` — consensus. Emit the shared direction only if EVERY signal agrees on the same
      actionable action; any disagreement or any hold present => hold. Confidence = min of the
      agreeing signals (the weakest link).
    - ``OR`` — any actionable signal wins over hold. On a buy-vs-sell conflict the configurable
      ``bias`` (default ``buy``) decides which side wins; absent a conflict the present action
      wins. Confidence = max confidence among signals on the winning side.
    - ``weighted`` — confidence-weighted vote. buy adds ``+confidence*weight``, sell adds
      ``-confidence*weight`` (hold contributes 0). Per-signal ``weight`` comes from the
      ``weights`` param keyed by the signal's ``source`` (fallback 1.0). Net > ``epsilon`` => buy,
      net < ``-epsilon`` => sell, else hold. Confidence = clamped |net| / total weight.
    """
    signals = _signals(inputs)
    if not signals:
        raise ValueError("combine node requires at least one upstream Signal")

    p = node.params
    mode = str(p.get("mode", "AND")).upper()

    if mode == "AND":
        actions = {s.action for s in signals}
        if actions == {SignalAction.buy} or actions == {SignalAction.sell}:
            action = signals[0].action
            confidence = min(s.confidence for s in signals)
            return Signal(action=action, confidence=confidence, reason="AND consensus", source="combine")
        return Signal(action=SignalAction.hold, reason="AND: signals disagree", source="combine")

    if mode == "OR":
        bias = SignalAction(str(p.get("bias", "buy")))
        has_buy = any(s.action == SignalAction.buy for s in signals)
        has_sell = any(s.action == SignalAction.sell for s in signals)
        if has_buy and has_sell:
            action = bias
            reason = f"OR conflict resolved by bias={bias.value}"
        elif has_buy:
            action = SignalAction.buy
            reason = "OR: a buy present"
        elif has_sell:
            action = SignalAction.sell
            reason = "OR: a sell present"
        else:
            return Signal(action=SignalAction.hold, reason="OR: all hold", source="combine")
        confidence = max((s.confidence for s in signals if s.action == action), default=0.5)
        return Signal(action=action, confidence=confidence, reason=reason, source="combine")

    if mode == "WEIGHTED":
        weights = p.get("weights") or {}
        epsilon = float(p.get("epsilon", 1e-9))
        net = 0.0
        total = 0.0
        for s in signals:
            w = float(weights.get(s.source, 1.0))
            total += w
            if s.action == SignalAction.buy:
                net += s.confidence * w
            elif s.action == SignalAction.sell:
                net -= s.confidence * w
        confidence = min(1.0, abs(net) / total) if total > 0 else 0.0
        if net > epsilon:
            action = SignalAction.buy
        elif net < -epsilon:
            action = SignalAction.sell
        else:
            return Signal(action=SignalAction.hold, reason="weighted vote tied", source="combine")
        return Signal(action=action, confidence=confidence, reason=f"weighted vote net={net:.4f}", source="combine")

    raise ValueError(f"combine node has unknown mode '{p.get('mode')}' (use AND/OR/weighted)")


_CONDITION_OPS: dict[str, Callable[[float, float], bool]] = {
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


def _condition_holds(node: NodeConfig, candles: list[Candle]) -> bool:
    """Evaluate ``<source> <operator> <value>`` against the LAST candle (price field)."""
    p = node.params
    source = str(p.get("source", "close"))
    operator = str(p.get("operator", ">"))
    if "value" not in p:
        raise ValueError("condition node requires 'value'")
    if operator not in _CONDITION_OPS:
        raise ValueError(f"condition node has unknown operator '{operator}'")
    last = candles[-1]
    if not hasattr(last, source):
        raise ValueError(f"condition source '{source}' is not a candle field")
    return _CONDITION_OPS[operator](float(getattr(last, source)), float(p["value"]))


def _run_condition(node: NodeConfig, inputs: list[Any], ctx: RunContext) -> Signal:
    """Threshold on upstream candles -> an actionable buy Signal (pass) or hold (block).

    params: ``source`` (candle field, default ``close``), ``operator`` (>, >=, <, <=, ==, !=),
    ``value``. When the threshold holds the node "passes" (emits a buy Signal); otherwise it
    "blocks" (emits hold). Wire it before an order node to gate entries.
    """
    candles = _first_candles(inputs)
    p = node.params
    met = _condition_holds(node, candles)
    detail = f"{p.get('source', 'close')} {p.get('operator', '>')} {p.get('value')}"
    if met:
        return Signal(action=SignalAction.buy, confidence=1.0, reason=f"condition met: {detail}", source="condition")
    return Signal(action=SignalAction.hold, reason=f"condition blocked: {detail}", source="condition")


def _run_branch(node: NodeConfig, inputs: list[Any], ctx: RunContext) -> Signal:
    """Gate one upstream Signal by a condition on upstream candles (M2.1).

    Routing within the topological engine's single-output constraint: a branch has ONE outgoing
    edge and acts as a conditional gate. When the condition holds the upstream Signal passes
    through unchanged; otherwise it is replaced with hold (the downstream branch is "not taken").
    Requires exactly one upstream Signal (fail loud on multiple) plus candles for the condition.
    """
    signal = _only_signal(inputs)
    candles = _first_candles(inputs)
    if _condition_holds(node, candles):
        return signal
    return Signal(action=SignalAction.hold, reason="branch not taken", source="branch")


def _run_logger(node: NodeConfig, inputs: list[Any], ctx: RunContext) -> Any:
    # Pass-through: the engine records every node's output anyway.
    return inputs[0] if inputs else None


NODE_RUNNERS: dict[NodeType, Callable[[NodeConfig, list[Any], RunContext], Any]] = {
    NodeType.data_source: _run_data_source,
    NodeType.strategy: _run_strategy,
    NodeType.ai_signal: _run_ai_signal,
    NodeType.risk_exit: _run_risk_exit,
    NodeType.order: _run_order,
    NodeType.logger: _run_logger,
    NodeType.combine: _run_combine,
    NodeType.condition: _run_condition,
    NodeType.branch: _run_branch,
}


def get_runner(node_type: NodeType) -> Callable[[NodeConfig, list[Any], RunContext], Any]:
    if node_type not in NODE_RUNNERS:
        raise ValueError(f"no runner for node type {node_type}")
    return NODE_RUNNERS[node_type]
