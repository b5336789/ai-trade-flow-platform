"""Sanity tests for indicator wrappers."""

from __future__ import annotations

import pytest

from app.strategies.indicators import candles_to_df, rsi, sma
from app.tests.helpers import make_candles


def test_candles_to_df_empty_fails_loud():
    with pytest.raises(ValueError):
        candles_to_df([])


def test_sma_matches_manual_mean():
    df = candles_to_df(make_candles([1, 2, 3, 4, 5]))
    result = sma(df["close"], window=3)
    # last 3 closes are 3,4,5 -> mean 4
    assert result.iloc[-1] == pytest.approx(4.0)


def test_rsi_high_on_uptrend():
    df = candles_to_df(make_candles([float(i) for i in range(1, 30)]))
    assert rsi(df["close"], window=14).iloc[-1] > 70
