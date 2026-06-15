"""Node implementations + a registry mapping NodeType -> runner.

Each runner takes (node, upstream_inputs, context) and returns the value passed downstream.
Candle lists, Signals and OrderResults flow between nodes; indicator and AI nodes are
interchangeable because both emit a Signal.
"""

from __future__ import annotations

from typing import Any, Callable

from app.ai.signal_agent import generate_ai_signal
from app.brokers.registry import get_data_broker
from app.schemas import (
    Candle,
    MarketKind,
    OrderRequest,
    OrderSide,
    Signal,
    SignalAction,
)
from app.strategies.base import Strategy
from app.strategies.ma_cross import MaCrossStrategy
from app.strategies.rsi import RsiStrategy
from app.trading.execution import execute_order
from app.workflow.schema import NodeConfig, NodeType

_STRATEGIES: dict[str, type[Strategy]] = {
    MaCrossStrategy.name: MaCrossStrategy,
    RsiStrategy.name: RsiStrategy,
}


class RunContext:
    def __init__(self, session=None) -> None:
        self.session = session
        self.scratch: dict[str, Any] = {}


def _first_candles(inputs: list[Any]) -> list[Candle]:
    for value in inputs:
        if isinstance(value, list) and value and isinstance(value[0], Candle):
            return value
    raise ValueError("node requires candle data from an upstream data_source")


def _first_signal(inputs: list[Any]) -> Signal:
    for value in inputs:
        if isinstance(value, Signal):
            return value
    raise ValueError("node requires a Signal from an upstream strategy/ai_signal node")


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
    if name not in _STRATEGIES:
        raise ValueError(f"unknown strategy '{name}'. Available: {list(_STRATEGIES)}")
    kwargs = {k: v for k, v in node.params.items() if k != "name"}
    return _STRATEGIES[name](**kwargs).generate(candles)


def _run_ai_signal(node: NodeConfig, inputs: list[Any], ctx: RunContext) -> Signal:
    candles = _first_candles(inputs)
    symbol = node.params.get("symbol") or ctx.scratch.get("symbol", "")
    return generate_ai_signal(symbol, candles, model=node.params.get("model"))


def _run_order(node: NodeConfig, inputs: list[Any], ctx: RunContext):
    signal = _first_signal(inputs)
    if signal.action == SignalAction.hold:
        return None
    p = node.params
    symbol = p.get("symbol") or ctx.scratch.get("symbol")
    if not symbol:
        raise ValueError("order node requires 'symbol' (or an upstream data_source)")
    market = MarketKind(p["market"]) if p.get("market") else ctx.scratch.get("market", MarketKind.crypto)
    side = OrderSide.buy if signal.action == SignalAction.buy else OrderSide.sell
    request = OrderRequest(symbol=symbol, side=side, quantity=float(p.get("quantity", 1)))
    return execute_order(request, market=market, session=ctx.session)


def _run_logger(node: NodeConfig, inputs: list[Any], ctx: RunContext) -> Any:
    # Pass-through: the engine records every node's output anyway.
    return inputs[0] if inputs else None


NODE_RUNNERS: dict[NodeType, Callable[[NodeConfig, list[Any], RunContext], Any]] = {
    NodeType.data_source: _run_data_source,
    NodeType.strategy: _run_strategy,
    NodeType.ai_signal: _run_ai_signal,
    NodeType.order: _run_order,
    NodeType.logger: _run_logger,
}


def get_runner(node_type: NodeType) -> Callable[[NodeConfig, list[Any], RunContext], Any]:
    if node_type not in NODE_RUNNERS:
        raise ValueError(f"no runner for node type {node_type}")
    return NODE_RUNNERS[node_type]
