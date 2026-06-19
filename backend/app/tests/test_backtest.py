"""Business-logic tests for the backtester (deterministic, offline)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.backtest.engine import run_backtest
from app.schemas import Candle, MarketKind, Signal, SignalAction
from app.strategies.base import Strategy
from app.strategies.ma_cross import MaCrossStrategy
from app.tests.helpers import make_candles
from app.trading.costs import CostModel


def _ohlc(opens: list[float], closes: list[float]) -> list[Candle]:
    """Candles with independent open/close (unlike make_candles which flattens O=H=L=C)."""
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [
        Candle(
            timestamp=base + timedelta(hours=i),
            open=o,
            high=max(o, c),
            low=min(o, c),
            close=c,
            volume=1.0,
        )
        for i, (o, c) in enumerate(zip(opens, closes))
    ]


class _BuyThenSellByLen(Strategy):
    """Deterministic strategy keyed on window length — buy at buy_len candles, sell at sell_len."""

    name = "buy_then_sell_by_len"

    def __init__(self, buy_len: int, sell_len: int) -> None:
        self.buy_len = buy_len
        self.sell_len = sell_len

    def generate(self, candles: list[Candle]) -> Signal:
        n = len(candles)
        if n == self.buy_len:
            return Signal(action=SignalAction.buy)
        if n == self.sell_len:
            return Signal(action=SignalAction.sell)
        return Signal(action=SignalAction.hold)



def test_profitable_round_trip_with_ma_cross():
    # Rise -> golden cross (buy fills next-bar open ~16); ride up to a high plateau; decline -> death
    # cross (sell fills next-bar open ~26). Profitable even with honest next-bar fills + costs (M0.2).
    prices = [10, 10, 10, 10, 12, 16, 20, 24, 28, 30, 30, 30, 30, 28, 26, 24, 22]
    result = run_backtest(make_candles(prices), MaCrossStrategy(fast=2, slow=4), starting_cash=10_000.0)
    assert result.num_trades >= 1
    # First completed trade bought below its exit price -> positive return.
    assert result.trades[0].return_pct > 0
    assert result.total_return_pct > 0
    assert result.wins >= 1


def test_buy_and_hold_reference_on_uptrend():
    prices = [float(i) for i in range(10, 30)]
    result = run_backtest(make_candles(prices), MaCrossStrategy(fast=2, slow=4))
    # buy & hold over 10 -> 29 is +190%
    assert result.buy_hold_return_pct == pytest.approx((29 / 10 - 1) * 100, rel=1e-6)


def test_equity_curve_and_drawdown_present():
    prices = [10, 11, 12, 9, 8, 13, 14]
    result = run_backtest(make_candles(prices), MaCrossStrategy(fast=2, slow=4))
    assert len(result.equity_curve) == len(prices) - 1
    assert result.max_drawdown_pct >= 0.0


def test_rejects_too_few_candles():
    with pytest.raises(ValueError):
        run_backtest(make_candles([10.0]), MaCrossStrategy(fast=2, slow=4))


def test_rejects_bad_position_fraction():
    with pytest.raises(ValueError):
        run_backtest(make_candles([1, 2, 3, 4, 5]), MaCrossStrategy(fast=2, slow=4), position_fraction=0)


# --- M0.2: fill at next-bar open (no look-ahead bias) ----------------------
def test_fills_at_next_bar_open_not_decision_close():
    # Signal decided on data through close[2]; the fill must be open[3], NOT close[2].
    opens = [10, 11, 12, 99, 14, 88]
    closes = [10, 11, 50, 13, 14, 15]
    candles = _ohlc(opens, closes)
    # buy decided when the window has 3 candles (i=2 → through close[2]); sell at 5 candles (i=4).
    strat = _BuyThenSellByLen(buy_len=3, sell_len=5)
    result = run_backtest(
        candles, strat, starting_cash=10_000.0, market=MarketKind.crypto, cost_model=CostModel.zero()
    )
    assert result.num_trades == 1
    t = result.trades[0]
    assert t.entry_price == 99.0  # open[3]
    assert t.entry_price != 50.0  # NOT close[2] (the decision bar's close)
    assert t.exit_price == 88.0  # open[5]


# --- M0.3: expanded risk/return metrics on the result --------------------
def test_backtest_populates_risk_metrics():
    prices = [10, 10, 10, 10, 12, 16, 20, 24, 28, 30, 30, 30, 30, 28, 26, 24, 22]
    result = run_backtest(
        make_candles(prices), MaCrossStrategy(fast=2, slow=4), starting_cash=10_000.0, timeframe="1d"
    )
    assert result.num_trades >= 1
    # All metrics are present and finite; profit_factor may be None only if there are no losses.
    for field in ("cagr", "annualized_volatility", "sharpe", "sortino", "calmar", "turnover", "exposure_pct"):
        assert isinstance(getattr(result, field), float)
    assert 0.0 <= result.exposure_pct <= 100.0
    assert result.turnover > 0.0  # at least one round trip moved notional
    assert result.max_consecutive_losses >= 0
    if result.wins == result.num_trades:  # no losses in this profitable fixture
        assert result.profit_factor is None


def test_last_bar_signal_opens_no_position():
    # A buy decided on the final bar has no next-bar open to fill at -> no position opened.
    candles = _ohlc([10, 11, 12, 13], [10, 11, 12, 13])
    strat = _BuyThenSellByLen(buy_len=4, sell_len=999)  # buy on the last bar (window len == 4)
    result = run_backtest(
        candles, strat, starting_cash=10_000.0, market=MarketKind.crypto, cost_model=CostModel.zero()
    )
    assert result.num_trades == 0
    assert result.final_equity == pytest.approx(10_000.0)
