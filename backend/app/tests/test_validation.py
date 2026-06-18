"""Tests for walk-forward / out-of-sample validation (M0.4).

The whole point of M0.4: a parameter set that looks great in-sample must not be trusted on its
out-of-sample (OOS) performance. These tests use deterministic synthetic candles (no network).
"""

from __future__ import annotations

import pytest

from app.backtest.validation import walk_forward
from app.tests.helpers import make_candles

# A rise-then-fall shape repeated so MA-cross has signals in every window.
_SEG = [10, 10, 11, 13, 16, 20, 22, 20, 17, 14, 11, 10]
PRICES = _SEG * 6  # 72 candles — enough for several folds


def test_walk_forward_returns_per_fold_and_aggregate():
    report = walk_forward(
        make_candles(PRICES),
        "ma_cross",
        {"fast": [2, 3], "slow": [5, 6]},
        n_folds=3,
    )
    assert len(report.folds) == 3
    for fold in report.folds:
        # each fold selected its best params on the in-sample window
        assert fold.best_params.keys() == {"fast", "slow"}
        # and reports both the IS metric it was selected on and the OOS metric it achieved
        assert fold.is_metric is not None
        assert fold.oos_metric is not None
        assert fold.train_size > 0 and fold.test_size > 0
    # aggregate OOS metric is the mean of the per-fold OOS metrics
    expected = sum(f.oos_metric for f in report.folds) / len(report.folds)
    assert report.aggregate_oos_metric == pytest.approx(expected)


def test_walk_forward_folds_do_not_overlap_train_test():
    report = walk_forward(
        make_candles(PRICES),
        "ma_cross",
        {"fast": [2], "slow": [5]},
        n_folds=2,
    )
    for fold in report.folds:
        # test window starts at/after where the train window ends (no leakage)
        assert fold.test_start >= fold.train_end


def test_walk_forward_unknown_metric_fails_loud():
    with pytest.raises(ValueError):
        walk_forward(
            make_candles(PRICES),
            "ma_cross",
            {"fast": [2], "slow": [5]},
            n_folds=2,
            metric="bogus",
        )


def test_walk_forward_too_few_candles_fails_loud():
    with pytest.raises(ValueError):
        walk_forward(make_candles([10, 11, 12, 13]), "ma_cross", {"fast": [2], "slow": [3]}, n_folds=3)
