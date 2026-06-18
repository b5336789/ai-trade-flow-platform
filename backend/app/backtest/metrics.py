"""Risk/return metrics for backtests (M0.3).

Pure, deterministic, fully unit-testable functions — no I/O, no globals. ``run_backtest`` composes
these into a :class:`BacktestResult`; ``walk_forward`` (M0.4) reuses them for OOS ranking.

Conventions:
- A "return" is a per-bar simple return ``equity_t / equity_{t-1} - 1``.
- Annualisation uses ``periods_per_year`` derived from the candle timeframe.
- Sharpe/Sortino use the sample standard deviation (ddof=1); Sortino's downside deviation is the
  root-mean-square of the negative excess returns over **all** periods (the common target-downside
  convention with target = risk-free).
"""

from __future__ import annotations

import math

_SECONDS_PER_YEAR = 365.25 * 24 * 3600
_UNIT_SECONDS = {"m": 60, "h": 3600, "d": 86400, "w": 604800}
_EPS = 1e-12  # dispersions below this are treated as zero (float noise, not real signal)


def periods_per_year(timeframe: str) -> float:
    """Bars per year for a ccxt-style timeframe (e.g. ``"1h"`` -> 8766.0, ``"1d"`` -> 365.25)."""
    tf = timeframe.strip().lower()
    num = ""
    i = 0
    while i < len(tf) and tf[i].isdigit():
        num += tf[i]
        i += 1
    unit = tf[i:]
    if not num or unit not in _UNIT_SECONDS:
        raise ValueError(f"unsupported timeframe for annualisation: {timeframe!r}")
    seconds = int(num) * _UNIT_SECONDS[unit]
    return _SECONDS_PER_YEAR / seconds


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _std(xs: list[float], ddof: int = 1) -> float:
    n = len(xs)
    if n <= ddof:
        return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (n - ddof))


def annualized_volatility(returns: list[float], ppy: float) -> float:
    return _std(returns) * math.sqrt(ppy)


def sharpe_ratio(returns: list[float], ppy: float, risk_free: float = 0.0) -> float:
    if not returns:
        return 0.0
    rf_per = risk_free / ppy
    excess = [r - rf_per for r in returns]
    sd = _std(excess)
    if sd < _EPS:
        return 0.0
    return _mean(excess) / sd * math.sqrt(ppy)


def sortino_ratio(returns: list[float], ppy: float, risk_free: float = 0.0) -> float:
    if not returns:
        return 0.0
    rf_per = risk_free / ppy
    excess = [r - rf_per for r in returns]
    downside = [min(0.0, e) for e in excess]
    dd = math.sqrt(sum(d * d for d in downside) / len(excess))
    if dd < _EPS:
        return 0.0
    return _mean(excess) / dd * math.sqrt(ppy)


def profit_factor(pnls: list[float]) -> float | None:
    """Gross profit / gross loss. ``None`` when there are no losing trades (undefined denominator)."""
    gains = sum(p for p in pnls if p > 0)
    losses = -sum(p for p in pnls if p < 0)
    if losses == 0:
        return None
    return gains / losses


def max_consecutive_losses(pnls: list[float]) -> int:
    longest = 0
    run = 0
    for p in pnls:
        if p < 0:
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    return longest


def cagr(starting_equity: float, final_equity: float, n_periods: int, ppy: float) -> float:
    if starting_equity <= 0 or final_equity <= 0 or n_periods <= 0 or ppy <= 0:
        return 0.0
    years = n_periods / ppy
    return (final_equity / starting_equity) ** (1 / years) - 1


def calmar_ratio(cagr_value: float, max_drawdown_pct: float) -> float:
    """CAGR / MaxDD. ``max_drawdown_pct`` is a percentage (e.g. 12.5 == 12.5%)."""
    if max_drawdown_pct <= 0:
        return 0.0
    return cagr_value / (max_drawdown_pct / 100.0)
