"use client";

import { useEffect, useState } from "react";
import {
  api,
  MARKETS,
  type BacktestResult,
  type CompareRow,
  type EquityPoint,
  type OptimizeRow,
  type StrategyListItem,
} from "@/lib/api";
import { OPTIMIZE_GRID, STRATEGY_NAMES, STRATEGY_PARAMS } from "@/lib/strategies";
import { setMarket } from "@/lib/useMarket";

const SAVED_PREFIX = "saved:";

function Sparkline({ points }: { points: EquityPoint[] }) {
  if (points.length < 2) return null;
  const values = points.map((p) => p.equity);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const w = 100;
  const h = 30;
  const path = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * w;
      const y = h - ((v - min) / range) * h;
      return `${i === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
  const isUp = values[values.length - 1] >= values[0];
  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="h-16 w-full">
      <path d={path} fill="none" stroke={isUp ? "var(--up)" : "var(--down)"} strokeWidth={1} />
    </svg>
  );
}

const pct = (n: number) => `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;

export function BacktestPanel() {
  const [symbol, setSymbol] = useState("BTC/USDT");
  const [market, setMarketState] = useState("crypto");
  const [strategy, setStrategy] = useState("ma_cross");
  const [params, setParams] = useState<Record<string, number>>({ ...STRATEGY_PARAMS.ma_cross });
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [comparison, setComparison] = useState<CompareRow[] | null>(null);
  const [optimization, setOptimization] = useState<OptimizeRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState<StrategyListItem[]>([]);

  useEffect(() => { setMarket(market); }, [market]);

  // Saved library strategies designed in 策略室 are selectable here too, closing
  // the 策略室 → 交易室 loop. Library fetch is best-effort (auth/empty tolerated).
  useEffect(() => {
    api.listSavedStrategies().then(setSaved).catch(() => setSaved([]));
  }, []);

  const isSaved = strategy.startsWith(SAVED_PREFIX);
  const savedId = isSaved ? Number(strategy.slice(SAVED_PREFIX.length)) : null;

  function changeStrategy(name: string) {
    setStrategy(name);
    setParams(name.startsWith(SAVED_PREFIX) ? {} : { ...STRATEGY_PARAMS[name] });
  }

  function resetOutputs() {
    setResult(null);
    setComparison(null);
    setOptimization(null);
    setError(null);
  }

  async function optimize() {
    setLoading(true);
    resetOutputs();
    try {
      setOptimization(
        // M0.4: split mode ranks by out-of-sample Sharpe (not raw in-sample return) to avoid overfitting.
        await api.optimize({
          symbol,
          market,
          strategy,
          param_grid: OPTIMIZE_GRID[strategy],
          timeframe: "1h",
          limit: 500,
          split: true,
          rank_metric: "oos_sharpe",
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function run() {
    setLoading(true);
    resetOutputs();
    try {
      const res =
        isSaved && savedId != null
          ? await api.backtestSavedStrategy(savedId, { symbol, market, timeframe: "1h", limit: 500 })
          : await api.backtest({ symbol, market, strategy, params, timeframe: "1h", limit: 500 });
      setResult(res);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function compare() {
    setLoading(true);
    resetOutputs();
    try {
      setComparison(await api.compareStrategies({ symbol, market, timeframe: "1h", limit: 500 }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="rounded-lg border border-border bg-surface-1 p-4">
      <h2 className="font-display mb-3 text-lg font-semibold">Backtest</h2>
      <div className="mb-3 flex flex-wrap items-end gap-2">
        <select
          value={market}
          onChange={(e) => setMarketState(e.target.value)}
          className="rounded-md bg-surface-2 px-2 py-1 text-sm"
        >
          {MARKETS.map((m) => (
            <option key={m.value} value={m.value}>
              {m.label}
            </option>
          ))}
        </select>
        <input
          value={symbol}
          onChange={(e) => setSymbol(e.target.value.toUpperCase())}
          className="rounded-md bg-surface-2 px-2 py-1 text-sm"
          placeholder="BTC/USDT"
        />
        <select
          value={strategy}
          onChange={(e) => changeStrategy(e.target.value)}
          className="rounded-md bg-surface-2 px-2 py-1 text-sm"
        >
          <optgroup label="內建策略">
            {STRATEGY_NAMES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </optgroup>
          {saved.length > 0 && (
            <optgroup label="策略庫 (策略室)">
              {saved.map((s) => (
                <option key={s.id} value={`${SAVED_PREFIX}${s.id}`}>
                  {s.name}
                </option>
              ))}
            </optgroup>
          )}
        </select>
        {isSaved && (
          <span className="rounded-sm bg-accent-dim px-2 py-1 text-xs text-accent">策略庫 · 預設參數</span>
        )}
        {Object.keys(params).map((key) => (
          <label key={key} className="text-xs text-muted">
            {key}
            <input
              type="number"
              value={params[key]}
              onChange={(e) => setParams((p) => ({ ...p, [key]: Number(e.target.value) }))}
              className="ml-1 w-16 rounded-md bg-surface-2 px-1 py-1 text-sm text-text"
            />
          </label>
        ))}
        <button
          onClick={run}
          disabled={loading}
          className="rounded-md bg-accent px-3 py-1 text-sm font-medium text-bg hover:brightness-110 disabled:opacity-50"
        >
          {loading ? "…" : "Run"}
        </button>
        <button
          onClick={compare}
          disabled={loading}
          className="rounded-md bg-surface-2 text-text border border-border-strong px-3 py-1 text-sm font-medium hover:bg-surface-3 disabled:opacity-50"
        >
          Compare all
        </button>
        <button
          onClick={optimize}
          disabled={loading || isSaved}
          title={isSaved ? "最佳化僅支援內建策略" : undefined}
          className="rounded-md bg-surface-2 text-text border border-border-strong px-3 py-1 text-sm font-medium hover:bg-surface-3 disabled:opacity-50"
        >
          Optimize
        </button>
      </div>

      {error && <p className="text-sm text-error">Backtest error: {error}</p>}

      {result && (
        <div className="space-y-3">
          <Sparkline points={result.equity_curve} />
          <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
            <Metric label="Return" value={pct(result.total_return_pct)} good={result.total_return_pct >= 0} />
            <Metric label="Buy & Hold" value={pct(result.buy_hold_return_pct)} good={result.buy_hold_return_pct >= 0} />
            <Metric label="Max DD" value={pct(-result.max_drawdown_pct)} good={false} />
            <Metric label="Trades" value={`${result.num_trades} (${result.win_rate.toFixed(0)}% win)`} />
          </div>
        </div>
      )}

      {optimization && (
        <table className="w-full text-left text-xs">
          <thead className="text-faint">
            <tr>
              <th className="py-1">Params</th>
              <th>OOS Ret</th>
              <th>IS→OOS Gap</th>
              <th>OOS Sharpe</th>
              <th>Max DD</th>
              <th>Trades</th>
              <th>Win%</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {optimization.slice(0, 10).map((r, i) => (
              <tr key={i} className="border-t border-border">
                <td className="py-1 font-mono">
                  {i === 0 && !r.error ? "🏆 " : ""}
                  {Object.entries(r.params)
                    .map(([k, v]) => `${k}=${v}`)
                    .join(", ")}
                </td>
                {r.error ? (
                  <td colSpan={7} className="text-error">
                    {r.error}
                  </td>
                ) : (
                  <>
                    {/* M0.4: headline is the out-of-sample return; IS→OOS gap exposes overfitting. */}
                    <td className={`num ${(r.oos_return_pct ?? r.total_return_pct) >= 0 ? "text-up" : "text-down"}`}>
                      {pct(r.oos_return_pct ?? r.total_return_pct)}
                    </td>
                    <td className={`num ${(r.is_oos_gap_pct ?? 0) > 0 ? "text-warning" : "text-muted"}`}>
                      {r.is_oos_gap_pct == null ? "—" : pct(r.is_oos_gap_pct)}
                    </td>
                    <td className={`num ${(r.oos_sharpe ?? 0) >= 0 ? "text-up" : "text-down"}`}>
                      {r.oos_sharpe == null ? "—" : r.oos_sharpe.toFixed(2)}
                    </td>
                    <td className="num text-down">{pct(-r.max_drawdown_pct)}</td>
                    <td className="num">{r.num_trades}</td>
                    <td className="num">{r.win_rate.toFixed(0)}%</td>
                    <td>
                      <button
                        onClick={() => {
                          setParams({ ...(r.params as Record<string, number>) });
                          setOptimization(null);
                        }}
                        className="text-accent hover:underline"
                      >
                        use
                      </button>
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {comparison && (
        <table className="w-full text-left text-xs">
          <thead className="text-faint">
            <tr>
              <th className="py-1">Strategy</th>
              <th>Return</th>
              <th>Max DD</th>
              <th>Trades</th>
              <th>Win%</th>
            </tr>
          </thead>
          <tbody>
            {comparison.map((r, i) => (
              <tr key={r.strategy} className="border-t border-border">
                <td className="py-1">
                  {i === 0 && !r.error ? "🏆 " : ""}
                  {r.strategy}
                </td>
                {r.error ? (
                  <td colSpan={4} className="text-error">
                    {r.error}
                  </td>
                ) : (
                  <>
                    <td className={`num ${r.total_return_pct >= 0 ? "text-up" : "text-down"}`}>
                      {pct(r.total_return_pct)}
                    </td>
                    <td className="num text-down">{pct(-r.max_drawdown_pct)}</td>
                    <td className="num">{r.num_trades}</td>
                    <td className="num">{r.win_rate.toFixed(0)}%</td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

function Metric({ label, value, good }: { label: string; value: string; good?: boolean }) {
  const color = good === undefined ? "text-text" : good ? "text-up" : "text-down";
  return (
    <div className="rounded-md bg-surface-2 p-2">
      <div className="text-xs text-faint">{label}</div>
      <div className={`num font-semibold ${color}`}>{value}</div>
    </div>
  );
}
