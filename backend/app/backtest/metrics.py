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

from app.schemas import MarketKind

_SECONDS_PER_YEAR = 365.25 * 24 * 3600
_UNIT_SECONDS = {"m": 60, "h": 3600, "d": 86400, "w": 604800}
_TRADING_DAYS_PER_YEAR = 252.0
_TRADING_WEEKS_PER_YEAR = 52.0
# Regular cash-session length per equity market (seconds): TW 09:00-13:30 = 4.5h; US 09:30-16:00 = 6.5h.
_STOCK_SESSION_SECONDS = {
    MarketKind.tw_stock: 4.5 * 3600,
    MarketKind.us_stock: 6.5 * 3600,
}
_EPS = 1e-12  # keep existing constant below this block


def periods_per_year(timeframe: str, market: MarketKind = MarketKind.crypto) -> float:
    """Bars per year for a ccxt-style timeframe.

    Crypto (24/7) uses the calendar-second basis (``"1h"`` -> 8766, ``"1d"`` -> 365.25).
    Equities use a TRADING calendar — 252 trading days/year, intraday scaled by the cash session
    length — so daily stock Sharpe/vol are not inflated ~1.2x by counting 365 days.
    """
    tf = timeframe.strip().lower()
    num = ""
    i = 0
    while i < len(tf) and tf[i].isdigit():
        num += tf[i]
        i += 1
    unit = tf[i:]
    if not num or unit not in _UNIT_SECONDS:
        raise ValueError(f"unsupported timeframe for annualisation: {timeframe!r}")
    n = int(num)
    session = _STOCK_SESSION_SECONDS.get(market)
    if session is None:  # crypto / 24-7 — unchanged calendar-second basis
        return _SECONDS_PER_YEAR / (n * _UNIT_SECONDS[unit])
    if unit == "d":
        return _TRADING_DAYS_PER_YEAR / n
    if unit == "w":
        return _TRADING_WEEKS_PER_YEAR / n
    bars_per_session = session / (n * _UNIT_SECONDS[unit])  # intraday
    return _TRADING_DAYS_PER_YEAR * bars_per_session


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
    # Compute in log space and clamp the exponent: annualising a very short sample (few bars, high
    # ppy) can otherwise overflow `**` with OverflowError. exp(±700) is near the float ceiling, so
    # we return a finite (if absurd) number rather than raising — such a CAGR is statistically
    # meaningless anyway and the caller still gets a usable result.
    exponent = math.log(final_equity / starting_equity) / years
    exponent = max(-700.0, min(700.0, exponent))
    return math.exp(exponent) - 1


def calmar_ratio(cagr_value: float, max_drawdown_pct: float) -> float:
    """CAGR / MaxDD. ``max_drawdown_pct`` is a percentage (e.g. 12.5 == 12.5%)."""
    if max_drawdown_pct <= 0:
        return 0.0
    return cagr_value / (max_drawdown_pct / 100.0)
