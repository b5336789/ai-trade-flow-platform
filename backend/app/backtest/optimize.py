"""Grid-search parameter optimization for a strategy over a fixed candle history.

Reuses ``run_backtest`` for every parameter combination and ranks the results. Pure/deterministic
and fully offline-testable.
"""

from __future__ import annotations

import itertools

from pydantic import BaseModel

from app.backtest.engine import run_backtest
from app.schemas import Candle, MarketKind
from app.strategies.registry import build_strategy

_METRICS = {"total_return_pct", "win_rate"}


class OptimizeRow(BaseModel):
    params: dict
    total_return_pct: float
    num_trades: int
    win_rate: float
    max_drawdown_pct: float
    error: str | None = None


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
) -> list[OptimizeRow]:
    if metric not in _METRICS:
        raise ValueError(f"metric must be one of {sorted(_METRICS)}")

    keys = list(param_grid)
    value_lists = [param_grid[k] for k in keys]
    combos = list(itertools.product(*value_lists)) if keys else [()]
    if len(combos) > max_combinations:
        raise ValueError(
            f"grid has {len(combos)} combinations, exceeding max_combinations={max_combinations}"
        )

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
