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


# --- M0.4: train/test split mode (out-of-sample ranking) ---------------------------------------

# Train regime (first half): a clean single rise+fall — a TIGHT MA cross (fast=2,slow=3) rides it for
# a big in-sample gain. Test regime (second half): repeated choppy whipsaws — the tight combo buys
# highs and sells lows (huge OOS loss), while the slower combo (fast=2,slow=8) sits out the noise and
# even profits. So fast=2/slow=3 is GREAT in-sample but FAILS out-of-sample: it must NOT rank #1.
_TRAIN = [10, 10, 10, 11, 12, 14, 17, 20, 23, 26, 28, 29, 29, 28, 25, 21, 16, 12, 10, 10]
_CHOP = [10, 14, 9, 15, 8, 15, 9, 14, 8, 15, 9, 14, 8, 15, 9, 14, 8, 15, 9, 10]
SPLIT_PRICES = _TRAIN + _CHOP
SPLIT_GRID = {"fast": [2], "slow": [3, 8]}


def test_split_mode_reports_is_oos_and_gap():
    rows = grid_search(
        make_candles(SPLIT_PRICES),
        "ma_cross",
        SPLIT_GRID,
        split=True,
        oos_fraction=0.5,
    )
    scored = [r for r in rows if r.error is None]
    assert scored, "expected at least one scored combo"
    for r in scored:
        # split mode exposes IS vs OOS and their gap explicitly (we don't hide overfitting)
        assert r.is_return_pct is not None
        assert r.oos_return_pct is not None
        assert r.oos_sharpe is not None
        assert r.is_oos_gap_pct == pytest.approx(r.is_return_pct - r.oos_return_pct)


def test_split_mode_ranks_by_oos_not_raw_return():
    rows = grid_search(
        make_candles(SPLIT_PRICES),
        "ma_cross",
        SPLIT_GRID,
        split=True,
        oos_fraction=0.5,
        rank_metric="oos_sharpe",
    )
    scored = [r for r in rows if r.error is None]
    # ranking is by OOS sharpe, best-first — NOT raw IS return
    oos = [r.oos_sharpe for r in scored]
    assert oos == sorted(oos, reverse=True)


def test_overfit_combo_does_not_rank_first():
    """Acceptance test: a combo great in-sample but failing out-of-sample must not be #1."""
    rows = grid_search(
        make_candles(SPLIT_PRICES),
        "ma_cross",
        SPLIT_GRID,
        split=True,
        oos_fraction=0.5,
        rank_metric="oos_sharpe",
    )
    scored = [r for r in rows if r.error is None]
    by_is = sorted(scored, key=lambda r: r.is_return_pct, reverse=True)
    overfit = by_is[0]
    # sanity: the IS-best combo really is the tight one and it loses OOS
    assert overfit.params == {"fast": 2, "slow": 3}
    assert overfit.oos_return_pct < overfit.is_return_pct
    # the overfit combo must NOT be ranked #1 under OOS ranking
    assert rows[0].params != overfit.params


def test_split_mode_alt_rank_metric_return_over_maxdd():
    rows = grid_search(
        make_candles(SPLIT_PRICES),
        "ma_cross",
        SPLIT_GRID,
        split=True,
        oos_fraction=0.5,
        rank_metric="oos_return_over_maxdd",
    )
    scored = [r for r in rows if r.error is None]
    scores = [r.oos_return_over_maxdd for r in scored]
    assert scores == sorted(scores, reverse=True)


def test_split_mode_unknown_rank_metric_fails_loud():
    with pytest.raises(ValueError):
        grid_search(
            make_candles(SPLIT_PRICES),
            "ma_cross",
            {"fast": [2], "slow": [3]},
            split=True,
            rank_metric="raw_return",
        )


def test_optimize_endpoint_split_mode_returns_oos_selected_best():
    """/api/backtest/optimize in split mode: rows[0] is the OOS-selected combo with the IS↔OOS gap."""
    from fastapi.testclient import TestClient

    from app.api import backtest as backtest_api
    from app.main import app
    from app.tests.helpers import StubBroker

    stub = StubBroker({"BTC/USDT": 0.0}, candles=make_candles(SPLIT_PRICES))
    orig = backtest_api.get_data_broker
    backtest_api.get_data_broker = lambda market: stub
    try:
        with TestClient(app) as c:
            resp = c.post(
                "/api/backtest/optimize",
                json={
                    "symbol": "BTC/USDT",
                    "strategy": "ma_cross",
                    "param_grid": SPLIT_GRID,
                    "split": True,
                    "oos_fraction": 0.5,
                    "rank_metric": "oos_sharpe",
                },
            )
    finally:
        backtest_api.get_data_broker = orig

    assert resp.status_code == 200, resp.text
    rows = resp.json()
    best = rows[0]
    # OOS-selected best is the robust combo, not the in-sample overfit one
    assert best["params"] == {"fast": 2, "slow": 8}
    # the IS↔OOS gap is surfaced for the frontend to display
    assert best["is_return_pct"] is not None
    assert best["oos_return_pct"] is not None
    assert best["is_oos_gap_pct"] == pytest.approx(best["is_return_pct"] - best["oos_return_pct"])
