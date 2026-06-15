"""Tests for MACD and Bollinger strategies + the strategy registry."""

from __future__ import annotations

import math

import pytest

from app.backtest.engine import run_backtest
from app.schemas import SignalAction
from app.strategies.bollinger import BollingerStrategy
from app.strategies.macd import MacdStrategy
from app.strategies.registry import STRATEGIES, build_strategy
from app.tests.helpers import make_candles


def test_registry_has_all_strategies():
    assert set(STRATEGIES) == {"ma_cross", "rsi", "macd", "bollinger"}
    assert build_strategy("bollinger").name == "bollinger"
    with pytest.raises(ValueError):
        build_strategy("does_not_exist")


class TestBollinger:
    strat = BollingerStrategy(window=10, window_dev=2.0)

    def test_buy_below_lower_band(self):
        prices = [10.0, 10.1] * 5 + [9.5]  # tiny volatility, last point dips below band
        assert self.strat.generate(make_candles(prices)).action == SignalAction.buy

    def test_sell_above_upper_band(self):
        prices = [10.0, 10.1] * 5 + [10.6]
        assert self.strat.generate(make_candles(prices)).action == SignalAction.sell

    def test_hold_within_bands(self):
        assert self.strat.generate(make_candles([10.0] * 12)).action == SignalAction.hold

    def test_insufficient_data_fails_loud(self):
        with pytest.raises(ValueError):
            self.strat.generate(make_candles([10.0, 10.1]))


class TestMacd:
    def test_trades_on_oscillating_series(self):
        # MACD needs ~35 bars; an oscillation produces multiple crossovers.
        prices = [100 + 10 * math.sin(i / 3) for i in range(120)]
        result = run_backtest(make_candles(prices), MacdStrategy())
        assert result.num_trades > 0

    def test_insufficient_data_fails_loud(self):
        with pytest.raises(ValueError):
            MacdStrategy().generate(make_candles([1.0, 2.0, 3.0]))

    def test_rejects_bad_windows(self):
        with pytest.raises(ValueError):
            MacdStrategy(window_fast=26, window_slow=12)
