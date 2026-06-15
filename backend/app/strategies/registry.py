"""Central strategy registry — reused by the workflow engine and the backtester."""

from __future__ import annotations

from app.strategies.base import Strategy
from app.strategies.ma_cross import MaCrossStrategy
from app.strategies.rsi import RsiStrategy

STRATEGIES: dict[str, type[Strategy]] = {
    MaCrossStrategy.name: MaCrossStrategy,
    RsiStrategy.name: RsiStrategy,
}


def build_strategy(name: str, params: dict | None = None) -> Strategy:
    if name not in STRATEGIES:
        raise ValueError(f"unknown strategy '{name}'. Available: {list(STRATEGIES)}")
    return STRATEGIES[name](**(params or {}))
