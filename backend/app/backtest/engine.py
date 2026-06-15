"""Bar-by-bar backtester.

Walks the candle history, asks the strategy for a signal on the data seen so far, and simulates
long-only fills (buy goes in with ``position_fraction`` of cash, sell exits fully). Reports
performance metrics + an equity curve. Pure/deterministic — no network, fully unit-testable.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas import Candle, SignalAction
from app.strategies.base import Strategy


class Trade(BaseModel):
    entry_time: str
    exit_time: str
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    return_pct: float


class EquityPoint(BaseModel):
    timestamp: str
    equity: float


class BacktestResult(BaseModel):
    starting_cash: float
    final_equity: float
    total_return_pct: float
    buy_hold_return_pct: float
    num_trades: int
    wins: int
    win_rate: float
    max_drawdown_pct: float
    trades: list[Trade] = Field(default_factory=list)
    equity_curve: list[EquityPoint] = Field(default_factory=list)


def run_backtest(
    candles: list[Candle],
    strategy: Strategy,
    starting_cash: float = 100_000.0,
    position_fraction: float = 1.0,
) -> BacktestResult:
    if len(candles) < 2:
        raise ValueError("backtest requires at least 2 candles")
    if not 0 < position_fraction <= 1:
        raise ValueError("position_fraction must be in (0, 1]")

    cash = starting_cash
    qty = 0.0
    entry_price = 0.0
    entry_time = ""
    trades: list[Trade] = []
    equity_curve: list[EquityPoint] = []
    peak_equity = starting_cash
    max_drawdown = 0.0

    for i in range(1, len(candles)):
        window = candles[: i + 1]
        price = window[-1].close
        ts = window[-1].timestamp.isoformat()

        try:
            signal = strategy.generate(window)
            action = signal.action
        except ValueError:
            action = SignalAction.hold  # not enough data yet for this strategy

        if action == SignalAction.buy and qty == 0.0 and cash > 0:
            spend = cash * position_fraction
            qty = spend / price
            cash -= spend
            entry_price = price
            entry_time = ts
        elif action == SignalAction.sell and qty > 0.0:
            proceeds = qty * price
            cash += proceeds
            pnl = (price - entry_price) * qty
            trades.append(
                Trade(
                    entry_time=entry_time,
                    exit_time=ts,
                    entry_price=entry_price,
                    exit_price=price,
                    quantity=qty,
                    pnl=pnl,
                    return_pct=(price / entry_price - 1) * 100 if entry_price else 0.0,
                )
            )
            qty = 0.0

        equity = cash + qty * price
        equity_curve.append(EquityPoint(timestamp=ts, equity=equity))
        peak_equity = max(peak_equity, equity)
        if peak_equity > 0:
            max_drawdown = max(max_drawdown, (peak_equity - equity) / peak_equity * 100)

    final_equity = cash + qty * candles[-1].close
    wins = sum(1 for t in trades if t.pnl > 0)
    first_price = candles[0].close
    last_price = candles[-1].close

    return BacktestResult(
        starting_cash=starting_cash,
        final_equity=final_equity,
        total_return_pct=(final_equity / starting_cash - 1) * 100,
        buy_hold_return_pct=(last_price / first_price - 1) * 100 if first_price else 0.0,
        num_trades=len(trades),
        wins=wins,
        win_rate=(wins / len(trades) * 100) if trades else 0.0,
        max_drawdown_pct=max_drawdown,
        trades=trades,
        equity_curve=equity_curve,
    )
