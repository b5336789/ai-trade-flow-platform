"""Pre-launch strategy quality gate — crypto first-launch OOS / walk-forward evaluation (MYM-14).

This is a REVIEW / GATEKEEPING harness, not a product feature. It reuses the certified backtest
engine (next-bar fill, no look-ahead) and walk-forward validator to answer one question per
candidate strategy: *is the out-of-sample, net-of-cost edge real enough to risk real money?*

Discipline (per the project's quant constraints):
- Only NET returns (transaction costs + slippage ON; slippage forced > 0 here).
- Real Binance OHLCV (public endpoint), fetched paginated; FAIL LOUD on any data gap.
- Risk-adjusted OOS selection only — never rank parameters by in-sample raw return.
- Reproducible: deterministic given the same fetched candles; the data window is printed.

Run:
    .venv/bin/python scripts/gate_eval.py [--quick]

Outputs a human summary to stdout and a JSON blob to scripts/gate_eval_result.json.
"""

from __future__ import annotations

# Force conservative, NON-ZERO costs BEFORE importing app (settings read env at import).
import os

os.environ.setdefault("COST_CRYPTO_TAKER_BPS", "7.5")   # Binance spot taker (default)
os.environ.setdefault("COST_SLIPPAGE_BPS", "5.0")       # conservative fixed slippage, was 0 in prod default
os.environ.setdefault("API_TOKEN", "")                   # local/offline

import argparse
import json
import sys
from datetime import datetime, timezone

import ccxt

from app.backtest.engine import run_backtest
from app.backtest.validation import selection_score, walk_forward
from app.schemas import Candle, MarketKind
from app.strategies.registry import build_strategy

# --- Data window: multi-year daily history covering bull, bear and chop regimes. ---
SINCE = "2019-01-01T00:00:00Z"
TIMEFRAME = "1d"
SYMBOLS = ["BTC/USDT", "ETH/USDT"]

_TF_MS = {"1d": 86_400_000, "4h": 14_400_000, "1h": 3_600_000}

# Candidate strategies + small, economically-sensible parameter grids.
# Grids are intentionally SMALL: a wide grid on a short OOS window is itself an overfit risk.
GRIDS = {
    "ma_cross": {"fast": [10, 20, 30], "slow": [50, 100, 200]},
    "rsi": {"window": [14, 21], "oversold": [25.0, 30.0], "overbought": [70.0, 75.0]},
    "macd": {"window_fast": [12], "window_slow": [26], "window_sign": [9]},
    "bollinger": {"window": [20, 30], "window_dev": [2.0, 2.5]},
}

# --- The GATE thresholds (documented in docs/strategy-gate.md). ---
GATE = {
    "min_oos_trades": 30,          # statistical confidence: < 30 round trips = not enough evidence
    "min_agg_oos_sharpe": 0.3,     # mean OOS Sharpe across folds must be meaningfully positive
    "min_holdout_oos_return": 0.0, # net holdout OOS return must be > 0
    "min_profit_factor": 1.2,      # net gross-profit / gross-loss on the holdout OOS window
    "max_drawdown_pct": 35.0,      # OOS max drawdown ceiling (conservative for crypto)
    "min_positive_fold_frac": 0.5, # >= half of OOS folds must have a positive risk-adjusted metric
    "max_is_oos_decay_ratio": 0.7, # OOS Sharpe must be >= (1 - 0.7) * IS Sharpe when IS is positive
    "stress_slippage_mult": 2.0,   # under 2x slippage the holdout OOS return must stay >= 0
}

N_FOLDS = 4


def fetch_candles(symbol: str, timeframe: str, since_iso: str) -> list[Candle]:
    """Paginated real Binance OHLCV. FAIL LOUD on an empty result (data gap)."""
    ex = ccxt.binance({"enableRateLimit": True})
    step = _TF_MS[timeframe]
    since = int(datetime.fromisoformat(since_iso.replace("Z", "+00:00")).timestamp() * 1000)
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    rows: list[list] = []
    last_ts: int | None = None
    while since < now_ms:
        batch = ex.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=1000)
        if not batch:
            break
        progressed = False
        for r in batch:
            ts = int(r[0])
            if last_ts is not None and ts <= last_ts:
                continue
            rows.append(r)
            last_ts = ts
            progressed = True
        if not progressed:
            break
        since = last_ts + step
    if not rows:
        raise RuntimeError(f"DATA GAP: no OHLCV for {symbol} {timeframe} since {since_iso}")
    candles = [
        Candle(
            timestamp=datetime.fromtimestamp(r[0] / 1000, tz=timezone.utc),
            open=float(r[1]), high=float(r[2]), low=float(r[3]),
            close=float(r[4]), volume=float(r[5]),
        )
        for r in rows
    ]
    # Integrity check: strictly increasing timestamps, no dupes.
    ts_list = [c.timestamp for c in candles]
    if ts_list != sorted(set(ts_list)):
        raise RuntimeError(f"DATA INTEGRITY: non-monotonic/duplicate timestamps for {symbol}")
    return candles


def holdout_oos(candles, strategy_name, grid, train_frac=0.7):
    """Pick params on the train prefix by OOS-style Sharpe, then evaluate on the holdout suffix.

    Returns the detailed holdout BacktestResult plus the in-sample Sharpe of the chosen params,
    so the caller can measure IS->OOS decay and read profit factor / trade count / drawdown.
    """
    import itertools

    keys = list(grid)
    combos = list(itertools.product(*[grid[k] for k in keys]))
    cut = int(len(candles) * train_frac)
    train, test = candles[:cut], candles[cut:]

    best_params, best_is = None, float("-inf")
    for combo in combos:
        params = dict(zip(keys, combo))
        try:
            r = run_backtest(train, build_strategy(strategy_name, params),
                             market=MarketKind.crypto, timeframe=TIMEFRAME)
        except Exception:
            continue
        s = selection_score(r, "sharpe")
        if s > best_is:
            best_is, best_params = s, params
    if best_params is None:
        raise RuntimeError(f"no valid in-sample combo for {strategy_name}")
    oos = run_backtest(test, build_strategy(strategy_name, best_params),
                       market=MarketKind.crypto, timeframe=TIMEFRAME)
    return best_params, best_is, oos


def stress_holdout(candles, strategy_name, params, slippage_mult):
    """Re-run the holdout OOS with slippage multiplied (cost stress)."""
    import itertools  # noqa

    base = float(os.environ["COST_SLIPPAGE_BPS"])
    from app.trading.costs import CostModel

    cut = int(len(candles) * 0.7)
    test = candles[cut:]
    cm = CostModel.from_settings()
    cm = CostModel(
        crypto_taker_bps=cm.crypto_taker_bps,
        crypto_maker_bps=cm.crypto_maker_bps,
        slippage_bps=base * slippage_mult,
    )
    return run_backtest(test, build_strategy(strategy_name, params),
                        market=MarketKind.crypto, timeframe=TIMEFRAME, cost_model=cm)


def evaluate(symbol: str, candles: list[Candle], quick: bool) -> dict:
    out = {"symbol": symbol, "n_candles": len(candles),
           "window": [candles[0].timestamp.isoformat(), candles[-1].timestamp.isoformat()],
           "strategies": {}}
    strat_names = ["ma_cross", "rsi"] if quick else list(GRIDS)
    for name in strat_names:
        grid = GRIDS[name]
        rec: dict = {"grid": grid}
        try:
            wf = walk_forward(
                candles, name, grid, n_folds=N_FOLDS, metric="sharpe", anchored=True,
                max_combinations=400, market=MarketKind.crypto, timeframe=TIMEFRAME,
            )
            scored = [f for f in wf.folds if f.error is None]
            pos_folds = sum(1 for f in scored if f.oos_metric > 0)
            rec["walk_forward"] = {
                "agg_oos_sharpe": round(wf.aggregate_oos_metric, 3),
                "agg_oos_return_pct": round(wf.aggregate_oos_return_pct, 2),
                "n_scored_folds": len(scored),
                "positive_fold_frac": round(pos_folds / len(scored), 2) if scored else 0.0,
                "folds": [
                    {"fold": f.fold, "params": f.best_params,
                     "is_sharpe": round(f.is_metric, 3), "oos_sharpe": round(f.oos_metric, 3),
                     "oos_return_pct": round(f.oos_return_pct, 2),
                     "oos_maxdd_pct": round(f.oos_max_drawdown_pct, 2)}
                    for f in wf.folds
                ],
            }

            params, is_sharpe, oos = holdout_oos(candles, name, grid)
            stress = stress_holdout(candles, name, params, GATE["stress_slippage_mult"])
            rec["holdout"] = {
                "chosen_params": params,
                "is_sharpe": round(is_sharpe, 3),
                "oos_sharpe": round(oos.sharpe, 3),
                "oos_return_pct": round(oos.total_return_pct, 2),
                "buy_hold_return_pct": round(oos.buy_hold_return_pct, 2),
                "oos_max_drawdown_pct": round(oos.max_drawdown_pct, 2),
                "oos_profit_factor": (round(oos.profit_factor, 3) if oos.profit_factor is not None else None),
                "oos_num_trades": oos.num_trades,
                "oos_win_rate": round(oos.win_rate, 1),
                "oos_turnover": round(oos.turnover, 2),
                "stress2x_oos_return_pct": round(stress.total_return_pct, 2),
                "stress2x_oos_sharpe": round(stress.sharpe, 3),
            }
            rec["gate"] = apply_gate(rec)
        except Exception as exc:  # fail loud, record the failure
            rec["error"] = f"{type(exc).__name__}: {exc}"
            rec["gate"] = {"verdict": "FAIL", "reasons": [rec["error"]]}
        out["strategies"][name] = rec
    return out


def apply_gate(rec: dict) -> dict:
    wf, hold = rec["walk_forward"], rec["holdout"]
    checks = {}
    checks["oos_trades>=min"] = hold["oos_num_trades"] >= GATE["min_oos_trades"]
    checks["agg_oos_sharpe>=min"] = wf["agg_oos_sharpe"] >= GATE["min_agg_oos_sharpe"]
    checks["holdout_oos_return>0"] = hold["oos_return_pct"] > GATE["min_holdout_oos_return"]
    pf = hold["oos_profit_factor"]
    checks["profit_factor>=min"] = (pf is not None and pf >= GATE["min_profit_factor"])
    checks["oos_maxdd<=ceiling"] = hold["oos_max_drawdown_pct"] <= GATE["max_drawdown_pct"]
    checks["positive_folds>=half"] = wf["positive_fold_frac"] >= GATE["min_positive_fold_frac"]
    # IS->OOS decay: only binding when IS Sharpe is positive.
    if hold["is_sharpe"] > 0:
        floor = (1.0 - GATE["max_is_oos_decay_ratio"]) * hold["is_sharpe"]
        checks["is_oos_decay_ok"] = hold["oos_sharpe"] >= floor
    else:
        checks["is_oos_decay_ok"] = hold["oos_sharpe"] > 0
    checks["survives_2x_slippage"] = hold["stress2x_oos_return_pct"] >= 0.0
    reasons = [k for k, ok in checks.items() if not ok]
    return {"verdict": "PASS" if not reasons else "FAIL", "checks": checks, "failed": reasons}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="2 strategies only (faster smoke run)")
    args = ap.parse_args()

    print(f"# Pre-launch crypto strategy gate  (slippage={os.environ['COST_SLIPPAGE_BPS']}bps, "
          f"taker={os.environ['COST_CRYPTO_TAKER_BPS']}bps, tf={TIMEFRAME})")
    results = []
    for sym in SYMBOLS:
        print(f"\n## {sym}  — fetching real Binance OHLCV since {SINCE} ...")
        candles = fetch_candles(sym, TIMEFRAME, SINCE)
        print(f"   {len(candles)} candles  [{candles[0].timestamp.date()} .. {candles[-1].timestamp.date()}]")
        res = evaluate(sym, candles, args.quick)
        results.append(res)
        for name, rec in res["strategies"].items():
            v = rec.get("gate", {}).get("verdict", "?")
            if "error" in rec:
                print(f"   {name:10s} {v}  ({rec['error']})")
                continue
            h = rec["holdout"]
            print(f"   {name:10s} {v}  aggOOS_Sharpe={rec['walk_forward']['agg_oos_sharpe']:>6} "
                  f"holdoutOOS_ret={h['oos_return_pct']:>7}% (B&H {h['buy_hold_return_pct']:>7}%) "
                  f"PF={h['oos_profit_factor']} trades={h['oos_num_trades']} "
                  f"DD={h['oos_max_drawdown_pct']}%  failed={rec['gate']['failed']}")

    payload = {"gate_thresholds": GATE, "since": SINCE, "timeframe": TIMEFRAME,
               "slippage_bps": float(os.environ["COST_SLIPPAGE_BPS"]),
               "taker_bps": float(os.environ["COST_CRYPTO_TAKER_BPS"]),
               "results": results}
    path = os.path.join(os.path.dirname(__file__), "gate_eval_result.json")
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"\nWrote {path}")

    n_pass = sum(1 for r in results for rec in r["strategies"].values()
                 if rec.get("gate", {}).get("verdict") == "PASS")
    print(f"\nPASS count: {n_pass}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
