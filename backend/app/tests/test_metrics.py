"""M0.3 — risk/return metrics, asserted against hand-computed values."""

from __future__ import annotations

import math

import pytest

from app.backtest import metrics


def test_periods_per_year_from_timeframe():
    assert metrics.periods_per_year("1h") == pytest.approx(8766.0)  # 365.25*24
    assert metrics.periods_per_year("1d") == pytest.approx(365.25)
    assert metrics.periods_per_year("15m") == pytest.approx(35064.0)
    assert metrics.periods_per_year("1w") == pytest.approx(52.178571, rel=1e-5)


def test_unsupported_timeframe_fails_loud():
    with pytest.raises(ValueError):
        metrics.periods_per_year("1y")


def test_sharpe_hand_computed():
    # returns [0.1,0.2,0.3]: mean 0.2, sample std (ddof=1) = 0.1 -> Sharpe 2.0 at ppy=1.
    assert metrics.sharpe_ratio([0.1, 0.2, 0.3], ppy=1.0) == pytest.approx(2.0)


def test_annualized_volatility_hand_computed():
    # sample std 0.1, annualised by sqrt(ppy). ppy=4 -> 0.2.
    assert metrics.annualized_volatility([0.1, 0.2, 0.3], ppy=4.0) == pytest.approx(0.2)


def test_sortino_hand_computed():
    # returns [0.3,-0.1,0.2,-0.1] mean 0.075; downside rms = sqrt((0.1^2+0.1^2)/4)=sqrt(0.005).
    expected = 0.075 / math.sqrt(0.005)
    assert metrics.sortino_ratio([0.3, -0.1, 0.2, -0.1], ppy=1.0) == pytest.approx(expected)


def test_sharpe_and_sortino_zero_dispersion():
    assert metrics.sharpe_ratio([0.05, 0.05, 0.05], ppy=1.0) == 0.0  # std 0
    assert metrics.sortino_ratio([0.05, 0.05, 0.05], ppy=1.0) == 0.0  # no downside


def test_profit_factor_hand_computed():
    assert metrics.profit_factor([100, -50, 200, -50]) == pytest.approx(3.0)  # 300 / 100
    assert metrics.profit_factor([100, 200]) is None  # no losses -> undefined
    assert metrics.profit_factor([-100, -50]) == pytest.approx(0.0)  # no gains


def test_max_consecutive_losses():
    assert metrics.max_consecutive_losses([10, -1, -2, -3, 5, -1]) == 3
    assert metrics.max_consecutive_losses([1, 2, 3]) == 0


def test_cagr_and_calmar_hand_computed():
    # double the money over exactly one year -> 100% CAGR.
    assert metrics.cagr(100.0, 200.0, n_periods=12, ppy=12.0) == pytest.approx(1.0)
    # CAGR 100% with 25% max drawdown -> Calmar 4.0.
    assert metrics.calmar_ratio(1.0, 25.0) == pytest.approx(4.0)
    assert metrics.calmar_ratio(1.0, 0.0) == 0.0  # no drawdown -> guarded
