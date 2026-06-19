"""Walk-forward / out-of-sample validation for parameter selection (M0.4).

The optimizer must not pick parameters that only shine in-sample (overfitting / data-leakage).
``walk_forward`` splits the candle history into multiple sequential folds; for each fold it picks the
best parameters on the **in-sample (train)** window and then measures how those parameters actually
perform on the **out-of-sample (test)** window that immediately follows. It returns the per-fold OOS
performance plus an aggregate so the caller can judge robustness, not just peak in-sample numbers.

Pure/deterministic and fully offline-testable — reuses ``run_backtest`` and ``backtest.metrics``.
"""

from __future__ import annotations

import itertools

from pydantic import BaseModel, Field

from app.backtest.engine import BacktestResult, run_backtest
from app.schemas import Candle, MarketKind
from app.strategies.registry import build_strategy

# Risk-adjusted selection metrics. Raw return is deliberately excluded: ranking by raw return is the
# overfitting trap M0.4 exists to eliminate.
_SELECTION_METRICS = {"sharpe", "sortino", "calmar", "return_over_maxdd"}


def selection_score(result: BacktestResult, metric: str) -> float:
    """Risk-adjusted score for ranking/selecting parameters from a backtest result.

    ``return_over_maxdd`` is total return (%) divided by max drawdown (%); when there was no drawdown
    the ratio is undefined, so we fall back to the raw return so a flat-but-positive run still scores.
    """
    if metric == "sharpe":
        return result.sharpe
    if metric == "sortino":
        return result.sortino
    if metric == "calmar":
        return result.calmar
    if metric == "return_over_maxdd":
        if result.max_drawdown_pct <= 0:
            return result.total_return_pct
        return result.total_return_pct / result.max_drawdown_pct
    raise ValueError(f"metric must be one of {sorted(_SELECTION_METRICS)}, got {metric!r}")


class FoldResult(BaseModel):
    fold: int
    best_params: dict
    train_start: int
    train_end: int  # exclusive
    test_start: int
    test_end: int  # exclusive
    train_size: int
    test_size: int
    is_metric: float  # in-sample score of the selected params (the metric they were chosen on)
    oos_metric: float  # out-of-sample score of those same params (what we actually trust)
    is_return_pct: float
    oos_return_pct: float
    oos_max_drawdown_pct: float
    error: str | None = None


class WalkForwardReport(BaseModel):
    strategy: str
    metric: str
    n_folds: int
    anchored: bool
    folds: list[FoldResult] = Field(default_factory=list)
    aggregate_oos_metric: float = 0.0  # mean OOS metric across folds — the headline robustness number
    aggregate_oos_return_pct: float = 0.0


def _best_params_on(
    candles: list[Candle],
    strategy_name: str,
    combos: list[tuple],
    keys: list[str],
    metric: str,
    starting_cash: float,
    position_fraction: float,
    market: MarketKind,
    timeframe: str,
) -> tuple[dict, BacktestResult]:
    """Pick the combo with the highest in-sample ``metric`` on ``candles``. Fail loud if none run."""
    best: tuple[dict, BacktestResult] | None = None
    best_score = float("-inf")
    last_error: Exception | None = None
    for combo in combos:
        params = dict(zip(keys, combo))
        try:
            result = run_backtest(
                candles,
                build_strategy(strategy_name, params),
                starting_cash=starting_cash,
                position_fraction=position_fraction,
                market=market,
                timeframe=timeframe,
            )
        except Exception as exc:  # a single invalid combo shouldn't abort selection
            last_error = exc
            continue
        score = selection_score(result, metric)
        if score > best_score:
            best_score = score
            best = (params, result)
    if best is None:
        raise ValueError(
            f"no parameter combination produced a valid in-sample backtest "
            f"(last error: {type(last_error).__name__}: {last_error})"
        )
    return best


def walk_forward(
    candles: list[Candle],
    strategy_name: str,
    param_grid: dict[str, list],
    n_folds: int = 4,
    metric: str = "sharpe",
    anchored: bool = True,
    max_combinations: int = 200,
    starting_cash: float = 100_000.0,
    position_fraction: float = 1.0,
    market: MarketKind = MarketKind.crypto,
    timeframe: str = "1h",
) -> WalkForwardReport:
    """Anchored (default) or rolling walk-forward validation.

    The history is divided into ``n_folds`` consecutive equal test windows. For fold ``k`` the test
    window is the ``k``-th slice; the train window is everything before it (anchored: from the start;
    rolling: only the immediately preceding slice). Best params are chosen on the train window by the
    risk-adjusted ``metric`` and then scored on the test window. Per-fold OOS results and their mean
    are returned. Fails loud on bad inputs.
    """
    if metric not in _SELECTION_METRICS:
        raise ValueError(f"metric must be one of {sorted(_SELECTION_METRICS)}, got {metric!r}")
    if n_folds < 2:
        raise ValueError(f"n_folds must be >= 2, got {n_folds}")

    keys = list(param_grid)
    value_lists = [param_grid[k] for k in keys]
    combos = list(itertools.product(*value_lists)) if keys else [()]
    if len(combos) > max_combinations:
        raise ValueError(
            f"grid has {len(combos)} combinations, exceeding max_combinations={max_combinations}"
        )

    n = len(candles)
    # Each fold needs >= 2 candles in both train and test for run_backtest to work.
    fold_size = n // (n_folds + 1)  # +1 because fold 0's train must precede the first test window
    if fold_size < 2:
        raise ValueError(
            f"not enough candles ({n}) for {n_folds} folds; need >= {2 * (n_folds + 1)}"
        )

    folds: list[FoldResult] = []
    for k in range(n_folds):
        # Anchored: train = [0, test_start); rolling: train = the one preceding fold-sized slice.
        test_start = (k + 1) * fold_size
        test_end = (k + 2) * fold_size if k < n_folds - 1 else n
        train_start = 0 if anchored else max(0, test_start - fold_size)
        train_end = test_start

        train = candles[train_start:train_end]
        test = candles[test_start:test_end]
        if len(train) < 2 or len(test) < 2:
            raise ValueError(f"fold {k} produced a window with < 2 candles (train={len(train)}, test={len(test)})")

        try:
            best_params, is_result = _best_params_on(
                train, strategy_name, combos, keys, metric,
                starting_cash, position_fraction, market, timeframe,
            )
            oos_result = run_backtest(
                test,
                build_strategy(strategy_name, best_params),
                starting_cash=starting_cash,
                position_fraction=position_fraction,
                market=market,
                timeframe=timeframe,
            )
            folds.append(
                FoldResult(
                    fold=k,
                    best_params=best_params,
                    train_start=train_start,
                    train_end=train_end,
                    test_start=test_start,
                    test_end=test_end,
                    train_size=len(train),
                    test_size=len(test),
                    is_metric=selection_score(is_result, metric),
                    oos_metric=selection_score(oos_result, metric),
                    is_return_pct=is_result.total_return_pct,
                    oos_return_pct=oos_result.total_return_pct,
                    oos_max_drawdown_pct=oos_result.max_drawdown_pct,
                )
            )
        except Exception as exc:
            # Fail loud: a fold that cannot be evaluated is recorded with its error and a zero score.
            folds.append(
                FoldResult(
                    fold=k,
                    best_params={},
                    train_start=train_start,
                    train_end=train_end,
                    test_start=test_start,
                    test_end=test_end,
                    train_size=len(train),
                    test_size=len(test),
                    is_metric=0.0,
                    oos_metric=0.0,
                    is_return_pct=0.0,
                    oos_return_pct=0.0,
                    oos_max_drawdown_pct=0.0,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )

    scored = [f for f in folds if f.error is None]
    agg_metric = sum(f.oos_metric for f in scored) / len(scored) if scored else 0.0
    agg_return = sum(f.oos_return_pct for f in scored) / len(scored) if scored else 0.0
    return WalkForwardReport(
        strategy=strategy_name,
        metric=metric,
        n_folds=n_folds,
        anchored=anchored,
        folds=folds,
        aggregate_oos_metric=agg_metric,
        aggregate_oos_return_pct=agg_return,
    )
