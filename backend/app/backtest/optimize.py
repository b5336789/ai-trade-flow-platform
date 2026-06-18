"""Grid-search parameter optimization for a strategy over a fixed candle history.

Reuses ``run_backtest`` for every parameter combination and ranks the results. Pure/deterministic
and fully offline-testable.

Two ranking modes:
- **Legacy (default):** runs each combo on the FULL dataset and ranks by a raw ``metric``
  (``total_return_pct`` or ``win_rate``). Kept for backward compatibility.
- **Split (M0.4):** ``split=True`` carves the history into an in-sample (train) prefix and an
  out-of-sample (test) suffix, scores every combo on BOTH, exposes the IS↔OOS gap, and ranks by a
  RISK-ADJUSTED **out-of-sample** metric (default OOS Sharpe). This eliminates the overfitting trap
  of ranking by in-sample raw return.
"""

from __future__ import annotations

import itertools

from pydantic import BaseModel

from app.backtest.engine import run_backtest
from app.backtest.validation import selection_score
from app.schemas import Candle, MarketKind
from app.strategies.registry import build_strategy

_METRICS = {"total_return_pct", "win_rate"}
# Risk-adjusted OOS ranking metrics for split mode (never raw return — that's the overfitting trap).
_RANK_METRICS = {"oos_sharpe", "oos_sortino", "oos_calmar", "oos_return_over_maxdd"}
_RANK_TO_SELECTION = {
    "oos_sharpe": "sharpe",
    "oos_sortino": "sortino",
    "oos_calmar": "calmar",
    "oos_return_over_maxdd": "return_over_maxdd",
}


class OptimizeRow(BaseModel):
    params: dict
    total_return_pct: float
    num_trades: int
    win_rate: float
    max_drawdown_pct: float
    error: str | None = None
    # --- Split mode (M0.4): in-sample vs out-of-sample, surfaced (never hidden) ---
    is_return_pct: float | None = None  # in-sample total return %
    oos_return_pct: float | None = None  # out-of-sample total return %
    is_oos_gap_pct: float | None = None  # is_return_pct - oos_return_pct (positive => OOS decay)
    oos_sharpe: float | None = None
    oos_sortino: float | None = None
    oos_calmar: float | None = None
    oos_max_drawdown_pct: float | None = None
    oos_return_over_maxdd: float | None = None
    rank_score: float | None = None  # the risk-adjusted OOS value this row was ranked on


def _legacy_grid_search(
    candles: list[Candle],
    strategy_name: str,
    combos: list[tuple],
    keys: list[str],
    metric: str,
    starting_cash: float,
    position_fraction: float,
    market: MarketKind,
    timeframe: str,
) -> list[OptimizeRow]:
    rows: list[OptimizeRow] = []
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
            rows.append(
                OptimizeRow(
                    params=params,
                    total_return_pct=result.total_return_pct,
                    num_trades=result.num_trades,
                    win_rate=result.win_rate,
                    max_drawdown_pct=result.max_drawdown_pct,
                )
            )
        except Exception as exc:  # one bad combo shouldn't sink the sweep — record it
            rows.append(
                OptimizeRow(
                    params=params,
                    total_return_pct=0.0,
                    num_trades=0,
                    win_rate=0.0,
                    max_drawdown_pct=0.0,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )

    rows.sort(
        key=lambda r: getattr(r, metric) if r.error is None else float("-inf"),
        reverse=True,
    )
    return rows


def _split_grid_search(
    candles: list[Candle],
    strategy_name: str,
    combos: list[tuple],
    keys: list[str],
    rank_metric: str,
    oos_fraction: float,
    starting_cash: float,
    position_fraction: float,
    market: MarketKind,
    timeframe: str,
) -> list[OptimizeRow]:
    if rank_metric not in _RANK_METRICS:
        raise ValueError(f"rank_metric must be one of {sorted(_RANK_METRICS)}, got {rank_metric!r}")
    if not 0 < oos_fraction < 1:
        raise ValueError(f"oos_fraction must be in (0, 1), got {oos_fraction}")

    n = len(candles)
    split = int(round(n * (1 - oos_fraction)))
    train = candles[:split]
    test = candles[split:]
    if len(train) < 2 or len(test) < 2:
        raise ValueError(
            f"split mode needs >= 2 candles in both windows (train={len(train)}, test={len(test)}); "
            f"provide more history or adjust oos_fraction"
        )

    selection = _RANK_TO_SELECTION[rank_metric]
    rows: list[OptimizeRow] = []
    for combo in combos:
        params = dict(zip(keys, combo))
        try:
            is_result = run_backtest(
                train,
                build_strategy(strategy_name, params),
                starting_cash=starting_cash,
                position_fraction=position_fraction,
                market=market,
                timeframe=timeframe,
            )
            oos_result = run_backtest(
                test,
                build_strategy(strategy_name, params),
                starting_cash=starting_cash,
                position_fraction=position_fraction,
                market=market,
                timeframe=timeframe,
            )
            oos_rom = selection_score(oos_result, "return_over_maxdd")
            rows.append(
                OptimizeRow(
                    params=params,
                    # Headline figures reflect the OOS window — that's what we trust to rank/apply.
                    total_return_pct=oos_result.total_return_pct,
                    num_trades=oos_result.num_trades,
                    win_rate=oos_result.win_rate,
                    max_drawdown_pct=oos_result.max_drawdown_pct,
                    is_return_pct=is_result.total_return_pct,
                    oos_return_pct=oos_result.total_return_pct,
                    is_oos_gap_pct=is_result.total_return_pct - oos_result.total_return_pct,
                    oos_sharpe=oos_result.sharpe,
                    oos_sortino=oos_result.sortino,
                    oos_calmar=oos_result.calmar,
                    oos_max_drawdown_pct=oos_result.max_drawdown_pct,
                    oos_return_over_maxdd=oos_rom,
                    rank_score=selection_score(oos_result, selection),
                )
            )
        except Exception as exc:  # one bad combo shouldn't sink the sweep — record it
            rows.append(
                OptimizeRow(
                    params=params,
                    total_return_pct=0.0,
                    num_trades=0,
                    win_rate=0.0,
                    max_drawdown_pct=0.0,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )

    # Rank by the risk-adjusted OOS metric — NEVER raw in-sample return.
    rows.sort(
        key=lambda r: r.rank_score if r.error is None and r.rank_score is not None else float("-inf"),
        reverse=True,
    )
    return rows


def grid_search(
    candles: list[Candle],
    strategy_name: str,
    param_grid: dict[str, list],
    metric: str = "total_return_pct",
    starting_cash: float = 100_000.0,
    position_fraction: float = 1.0,
    max_combinations: int = 200,
    market: MarketKind = MarketKind.crypto,
    timeframe: str = "1h",
    split: bool = False,
    oos_fraction: float = 0.3,
    rank_metric: str = "oos_sharpe",
) -> list[OptimizeRow]:
    """Sweep ``param_grid`` and rank the combos.

    Default (legacy) mode ranks by the raw ``metric`` over the full history. With ``split=True`` the
    history is divided into an in-sample prefix and a ``oos_fraction`` out-of-sample suffix; each combo
    is scored on both, the IS↔OOS gap is exposed, and ranking is by the risk-adjusted ``rank_metric``
    on the OOS window (default OOS Sharpe). ``metric`` is ignored in split mode.
    """
    if not split and metric not in _METRICS:
        raise ValueError(f"metric must be one of {sorted(_METRICS)}")

    keys = list(param_grid)
    value_lists = [param_grid[k] for k in keys]
    combos = list(itertools.product(*value_lists)) if keys else [()]
    if len(combos) > max_combinations:
        raise ValueError(
            f"grid has {len(combos)} combinations, exceeding max_combinations={max_combinations}"
        )

    if split:
        return _split_grid_search(
            candles, strategy_name, combos, keys, rank_metric, oos_fraction,
            starting_cash, position_fraction, market, timeframe,
        )
    return _legacy_grid_search(
        candles, strategy_name, combos, keys, metric,
        starting_cash, position_fraction, market, timeframe,
    )
