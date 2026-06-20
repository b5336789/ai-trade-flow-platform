"use client";

import { useEffect, useState } from "react";
import {
  api,
  MARKETS,
  type BacktestResult,
  type CompareRow,
  type OptimizeRow,
  type StrategyListItem,
} from "@/lib/api";
import { OPTIMIZE_GRID, STRATEGY_NAMES, STRATEGY_PARAMS } from "@/lib/strategies";
import { EquityChart } from "@/components/EquityChart";
import { setMarket } from "@/lib/useMarket";

const SAVED_PREFIX = "saved:";
const TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"];
const LIMITS = [200, 500, 1000];

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
  const [timeframe, setTimeframe] = useState("1h");
  const [limit, setLimit] = useState(500);
  const [tab, setTab] = useState<"overview" | "trades" | "walkforward">("overview");

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
          timeframe,
          limit,
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
          ? await api.backtestSavedStrategy(savedId, { symbol, market, timeframe, limit })
          : await api.backtest({ symbol, market, strategy, params, timeframe, limit });
      setResult(res);
      setTab("overview");
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
      setComparison(await api.compareStrategies({ symbol, market, timeframe, limit }));
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
          value={timeframe}
          onChange={(e) => setTimeframe(e.target.value)}
          className="rounded-md bg-surface-2 px-2 py-1 text-sm"
        >
          {TIMEFRAMES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <select
          value={limit}
          onChange={(e) => setLimit(Number(e.target.value))}
          className="rounded-md bg-surface-2 px-2 py-1 text-sm"
        >
          {LIMITS.map((n) => (
            <option key={n} value={n}>
              {n} bars
            </option>
          ))}
        </select>
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
          <div className="flex gap-2 border-b border-border text-sm">
            {(["overview", "trades", "walkforward"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-3 py-1.5 ${
                  tab === t ? "border-b-2 border-accent text-text" : "text-muted hover:text-text"
                }`}
              >
                {t === "overview" ? "概覽" : t === "trades" ? "交易" : "Walk-forward"}
              </button>
            ))}
          </div>

          {tab === "overview" && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
                <Metric label="Return" value={pct(result.total_return_pct)} good={result.total_return_pct >= 0} />
                <Metric label="Buy & Hold" value={pct(result.buy_hold_return_pct)} good={result.buy_hold_return_pct >= 0} />
                <Metric label="CAGR" value={pct(result.cagr)} good={result.cagr >= 0} />
                <Metric label="Max DD" value={pct(-result.max_drawdown_pct)} good={false} />
                <Metric label="Sharpe" value={result.sharpe.toFixed(2)} good={result.sharpe >= 0} />
                <Metric label="Sortino" value={result.sortino.toFixed(2)} good={result.sortino >= 0} />
                <Metric label="Win rate" value={`${result.win_rate.toFixed(0)}%`} />
                <Metric
                  label="Profit factor"
                  value={result.profit_factor == null ? "∞" : result.profit_factor.toFixed(2)}
                  good={result.profit_factor == null ? true : result.profit_factor >= 1}
                />
              </div>
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
                <span>Calmar {result.calmar.toFixed(2)}</span>
                <span>Vol {pct(result.annualized_volatility * 100)}</span>
                <span>Exposure {result.exposure_pct.toFixed(0)}%</span>
                <span>Turnover {result.turnover.toFixed(2)}×</span>
                <span>Max consec. losses {result.max_consecutive_losses}</span>
                <span>Trades {result.num_trades}</span>
              </div>
              <EquityChart points={result.equity_curve} />
            </div>
          )}

          {tab === "trades" && (
            <div className="max-h-80 overflow-y-auto">
              {result.trades.length === 0 ? (
                <p className="text-sm text-muted">No trades.</p>
              ) : (
                <table className="w-full text-left text-xs">
                  <thead className="text-faint">
                    <tr>
                      <th className="py-1">Entry</th>
                      <th>Exit</th>
                      <th className="num">Entry px</th>
                      <th className="num">Exit px</th>
                      <th className="num">Qty</th>
                      <th className="num">Return%</th>
                      <th className="num">Net PnL</th>
                      <th className="num">Cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.trades.map((t, i) => (
                      <tr key={i} className="border-t border-border">
                        <td className="py-1 font-mono">{t.entry_time.slice(0, 16).replace("T", " ")}</td>
                        <td className="font-mono">{t.exit_time.slice(0, 16).replace("T", " ")}</td>
                        <td className="num">{t.entry_price.toFixed(2)}</td>
                        <td className="num">{t.exit_price.toFixed(2)}</td>
                        <td className="num">{t.quantity.toFixed(4)}</td>
                        <td className={`num ${t.return_pct >= 0 ? "text-up" : "text-down"}`}>{pct(t.return_pct)}</td>
                        <td className={`num ${t.pnl >= 0 ? "text-up" : "text-down"}`}>{t.pnl.toFixed(2)}</td>
                        <td className="num text-muted">{t.cost.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {tab === "walkforward" && (
            <p className="text-sm text-muted">Walk-forward 將在下一步加入。</p>
          )}
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
