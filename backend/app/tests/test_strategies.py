"""Business-logic tests for indicator strategies (CLAUDE.md: validate intent, not coverage)."""

from __future__ import annotations

import pytest

from app.schemas import SignalAction
from app.strategies.ma_cross import MaCrossStrategy
from app.strategies.rsi import RsiStrategy
from app.tests.helpers import make_candles


class TestMaCross:
    strat = MaCrossStrategy(fast=2, slow=4)

    def test_buy_on_upward_cross(self):
        # flat then jump up -> fast SMA crosses above slow SMA on the last bar
        signal = self.strat.generate(make_candles([5, 5, 5, 5, 5, 5, 9]))
        assert signal.action == SignalAction.buy

    def test_sell_on_downward_cross(self):
        signal = self.strat.generate(make_candles([9, 9, 9, 9, 9, 9, 5]))
        assert signal.action == SignalAction.sell

    def test_hold_when_flat(self):
        signal = self.strat.generate(make_candles([5, 5, 5, 5, 5, 5, 5]))
        assert signal.action == SignalAction.hold

    def test_fails_loud_on_insufficient_data(self):
        with pytest.raises(ValueError):
            self.strat.generate(make_candles([5, 5]))

    def test_rejects_invalid_windows(self):
        with pytest.raises(ValueError):
            MaCrossStrategy(fast=10, slow=10)


class TestRsi:
    strat = RsiStrategy(window=14)

    def test_sell_when_overbought(self):
        # strictly increasing -> RSI ~100 -> overbought -> sell
        signal = self.strat.generate(make_candles([float(i) for i in range(1, 25)]))
        assert signal.action == SignalAction.sell

    def test_buy_when_oversold(self):
        # strictly decreasing -> RSI ~0 -> oversold -> buy
        signal = self.strat.generate(make_candles([float(i) for i in range(25, 1, -1)]))
        assert signal.action == SignalAction.buy

    def test_fails_loud_on_insufficient_data(self):
        with pytest.raises(ValueError):
            self.strat.generate(make_candles([1, 2, 3]))
