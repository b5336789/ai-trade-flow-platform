"""Tests for grid-search parameter optimization."""

from __future__ import annotations

import pytest

from app.backtest.optimize import grid_search
from app.tests.helpers import make_candles

# Rise -> plateau -> fall: profitable for a tuned MA cross.
PRICES = [10, 10, 10, 10, 12, 16, 20, 20, 20, 20, 20, 20, 18, 14, 10, 9, 8, 8, 9, 10]


def test_grid_search_ranks_best_first():
    rows = grid_search(make_candles(PRICES), "ma_cross", {"fast": [2, 3], "slow": [4, 5]})
    assert len(rows) == 4
    # sorted best-first by total_return_pct
    returns = [r.total_return_pct for r in rows if r.error is None]
    assert returns == sorted(returns, reverse=True)
    assert rows[0].params.keys() == {"fast", "slow"}


def test_invalid_combo_becomes_error_row_sorted_last():
    # fast == slow is rejected by MaCrossStrategy -> error row, ranked last.
    rows = grid_search(make_candles(PRICES), "ma_cross", {"fast": [4], "slow": [4]})
    assert len(rows) == 1
    assert rows[0].error is not None


def test_too_many_combinations_fails_loud():
    with pytest.raises(ValueError):
        grid_search(
            make_candles(PRICES),
            "ma_cross",
            {"fast": [1, 2, 3], "slow": [4, 5, 6]},
            max_combinations=4,
        )


def test_unknown_metric_fails_loud():
    with pytest.raises(ValueError):
        grid_search(make_candles(PRICES), "ma_cross", {"fast": [2]}, metric="sharpe")
