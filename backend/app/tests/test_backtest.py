"""Business-logic tests for the backtester (deterministic, offline)."""

from __future__ import annotations

import pytest

from app.backtest.engine import run_backtest
from app.strategies.ma_cross import MaCrossStrategy
from app.tests.helpers import make_candles


def test_profitable_round_trip_with_ma_cross():
    # Gentle rise -> buy cross at ~12; plateau at 20; decline -> sell cross at ~18 (profit).
    prices = [10, 10, 10, 10, 12, 16, 20, 20, 20, 20, 20, 20, 18, 14, 10]
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
