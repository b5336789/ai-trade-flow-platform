"""Bar-by-bar backtester.

Walks the candle history, asks the strategy for a signal on the data seen so far, and simulates
long-only fills (buy goes in with ``position_fraction`` of cash, sell exits fully). Reports
performance metrics + an equity curve. Pure/deterministic — no network, fully unit-testable.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas import Candle, MarketKind, OrderSide, SignalAction
from app.strategies.base import Strategy
from app.trading.costs import CostModel


class Trade(BaseModel):
    entry_time: str
    exit_time: str
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float  # net of transaction costs
    gross_pnl: float  # (exit_price - entry_price) * quantity, before costs
    cost: float  # total buy + sell fees + sell tax
    return_pct: float  # gross price return of the round trip


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
    market: MarketKind = MarketKind.crypto,
    cost_model: CostModel | None = None,
) -> BacktestResult:
    """Bar-by-bar long-only backtest with transaction costs applied to every fill (M0.1 + M0.2).

    Fill convention (M0.2 — no look-ahead bias): a signal is decided on data **up to and including
    ``close[i]``**, and the resulting order fills at the **next bar's open ``open[i+1]``** — never at
    the decision bar's own close. A signal on the final bar has no next bar to fill at, so it opens
    no position (recorded as no trade). Equity is marked-to-market at each ``close[i]`` reflecting the
    position established by fills up to that bar's open.

    Costs default to the configured :class:`CostModel`; pass ``CostModel.zero()`` to measure gross
    performance. ``Trade.pnl`` is net of costs; ``Trade.gross_pnl`` / ``Trade.cost`` expose the breakdown.
    """
    if len(candles) < 2:
        raise ValueError("backtest requires at least 2 candles")
    if not 0 < position_fraction <= 1:
        raise ValueError("position_fraction must be in (0, 1]")

    costs = cost_model or CostModel.from_settings()
    cash = starting_cash
    qty = 0.0
    entry_price = 0.0
    entry_time = ""
    entry_fee = 0.0
    pending: SignalAction | None = None  # action decided at the previous close, fills at this open
    trades: list[Trade] = []
    equity_curve: list[EquityPoint] = []
    peak_equity = starting_cash
    max_drawdown = 0.0

    for i in range(1, len(candles)):
        bar = candles[i]
        ts = bar.timestamp.isoformat()

        # 1) Execute the action decided at the previous bar's close, at THIS bar's open.
        if pending == SignalAction.buy and qty == 0.0 and cash > 0:
            fill_price = costs.slippage_price(OrderSide.buy, bar.open)
            spend = cash * position_fraction
            qty = spend / fill_price
            buy_fee = costs.fill_cost(market, OrderSide.buy, fill_price, qty).total
            outlay = qty * fill_price + buy_fee
            if outlay > cash:  # leave room for the fee so cash never goes negative
                qty *= cash / outlay
                buy_fee = costs.fill_cost(market, OrderSide.buy, fill_price, qty).total
                outlay = qty * fill_price + buy_fee
            cash -= outlay
            entry_price = fill_price
            entry_fee = buy_fee
            entry_time = ts
        elif pending == SignalAction.sell and qty > 0.0:
            fill_price = costs.slippage_price(OrderSide.sell, bar.open)
            sell_cost = costs.fill_cost(market, OrderSide.sell, fill_price, qty)
            cash += qty * fill_price - sell_cost.total
            gross_pnl = (fill_price - entry_price) * qty
            total_cost = entry_fee + sell_cost.total
            trades.append(
                Trade(
                    entry_time=entry_time,
                    exit_time=ts,
                    entry_price=entry_price,
                    exit_price=fill_price,
                    quantity=qty,
                    pnl=gross_pnl - total_cost,
                    gross_pnl=gross_pnl,
                    cost=total_cost,
                    return_pct=(fill_price / entry_price - 1) * 100 if entry_price else 0.0,
                )
            )
            qty = 0.0
        pending = None

        # 2) Decide on data through close[i]; the order (if any) fills at the next bar's open.
        window = candles[: i + 1]
        try:
            action = strategy.generate(window).action
        except ValueError:
            action = SignalAction.hold  # not enough data yet for this strategy
        if action in (SignalAction.buy, SignalAction.sell):
            pending = action

        # 3) Mark-to-market at close[i].
        equity = cash + qty * bar.close
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
