"use client";

import { useEffect, useState } from "react";
import {
  api,
  MARKETS,
  type BacktestResult,
  type CompareRow,
  type OptimizeRow,
  type StrategyListItem,
  type WalkForwardReport,
} from "@/lib/api";
import { OPTIMIZE_GRID, STRATEGY_NAMES, STRATEGY_PARAMS } from "@/lib/strategies";
import { EquityChart } from "@/components/EquityChart";
import { setMarket } from "@/lib/useMarket";
import { L } from "@/lib/labels";
import { Term } from "@/components/Term";
import { MetricCard } from "@/components/MetricCard";
import { PriceChart } from "@/components/PriceChart";
import { tradesToMarkers, type Overlay } from "@/lib/chart-helpers";
import type { Candle } from "@/lib/api";

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
  const [tab, setTab] = useState<"overview" | "trades" | "compare" | "optimize" | "walkforward">("overview");
  const [appliedHint, setAppliedHint] = useState(false);
  const [walkforward, setWalkforward] = useState<WalkForwardReport | null>(null);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [overviewCandles, setOverviewCandles] = useState<Candle[]>([]);
  const [moreMetrics, setMoreMetrics] = useState(false);

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
    setWalkforward(null);
    setError(null);
    setOverviewCandles([]);
    setAppliedHint(false);
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
      setTab("optimize");
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
      try {
        setOverviewCandles(await api.ohlcv(symbol, timeframe, limit, market));
      } catch {
        setOverviewCandles([]);
      }
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
      setTab("compare");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function runWalkForward() {
    if (isSaved) return;
    setLoading(true);
    resetOutputs();
    try {
      setWalkforward(
        await api.walkForward({
          symbol,
          market,
          strategy,
          param_grid: OPTIMIZE_GRID[strategy],
          timeframe,
          limit,
          n_folds: 4,
          metric: "sharpe",
        }),
      );
      setTab("walkforward");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const ovOverlays: Overlay[] =
    strategy === "ma_cross"
      ? [
          { id: "fast", type: "sma", period: Number(params.fast ?? 10), color: "--accent" },
          { id: "slow", type: "sma", period: Number(params.slow ?? 20), color: "--muted" },
        ]
      : [];

  return (
    <section className="rounded-lg border border-border bg-surface-1 p-4">
      <h2 className="font-display mb-3 text-lg font-semibold">{L.backtest.title}</h2>
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
          className="rounded-md bg-accent px-4 py-1.5 text-sm font-semibold text-bg hover:brightness-110 disabled:opacity-50"
        >
          {loading ? L.common.loading : L.backtest.run}
        </button>
        <button
          type="button"
          onClick={() => setAdvancedOpen((o) => !o)}
          className="rounded-md border border-border-strong bg-surface-2 px-3 py-1.5 text-sm text-text hover:bg-surface-3"
        >
          {L.common.advanced} {advancedOpen ? "▴" : "▾"}
        </button>
      </div>

      {advancedOpen && (
        <div className="mb-3 space-y-2 rounded-md border border-border bg-surface-2 p-3">
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={compare}
              disabled={loading}
              className="rounded-md border border-border-strong bg-surface-1 px-3 py-1 text-sm text-text hover:bg-surface-3 disabled:opacity-50"
            >
              {L.backtest.compare}
            </button>
            <span className="text-xs text-muted">{L.backtest.compareDesc}</span>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={optimize}
              disabled={loading || isSaved}
              className="rounded-md border border-border-strong bg-surface-1 px-3 py-1 text-sm text-text hover:bg-surface-3 disabled:opacity-50"
            >
              <Term k="optimize">{L.backtest.optimize}</Term>
            </button>
            <span className="text-xs text-muted">{L.backtest.optimizeDesc}</span>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={runWalkForward}
              disabled={loading || isSaved}
              className="rounded-md border border-border-strong bg-surface-1 px-3 py-1 text-sm text-text hover:bg-surface-3 disabled:opacity-50"
            >
              <Term k="walk_forward">{L.backtest.walkforward}</Term>
            </button>
            <span className="text-xs text-muted">{L.backtest.walkforwardDesc}</span>
          </div>
          {isSaved && (
            <p className="text-xs text-warning">{L.backtest.advancedOnlyBuiltin}</p>
          )}
        </div>
      )}

      {error && <p className="text-sm text-error">Backtest error: {error}</p>}

      {(result || comparison || optimization || walkforward) && (
        <div className="space-y-3">
          <div className="flex gap-2 border-b border-border text-sm">
            {result && (
              <>
                <TabBtn id="overview" tab={tab} setTab={setTab}>{L.backtest.overview}</TabBtn>
                <TabBtn id="trades" tab={tab} setTab={setTab}>{L.backtest.trades}</TabBtn>
              </>
            )}
            {comparison && <TabBtn id="compare" tab={tab} setTab={setTab}>{L.backtest.tabCompare}</TabBtn>}
            {optimization && <TabBtn id="optimize" tab={tab} setTab={setTab}>{L.backtest.tabOptimize}</TabBtn>}
            {walkforward && <TabBtn id="walkforward" tab={tab} setTab={setTab}>{L.backtest.tabWalkforward}</TabBtn>}
          </div>

          {appliedHint && tab === "overview" && (
            <p className="text-xs text-accent">{L.backtest.applied}</p>
          )}

          {result && tab === "overview" && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
                <MetricCard
                  termKey="total_return"
                  label={L.metrics.total_return}
                  value={pct(result.total_return_pct)}
                  health={result.total_return_pct >= 0 ? "up" : "down"}
                  sub={
                    <span className="text-muted">
                      {L.metrics.buy_hold} {pct(result.buy_hold_return_pct)} ·{" "}
                      <span className={result.total_return_pct - result.buy_hold_return_pct >= 0 ? "text-up" : "text-down"}>
                        {L.backtest.excess} {pct(result.total_return_pct - result.buy_hold_return_pct)}
                      </span>
                    </span>
                  }
                />
                <MetricCard
                  termKey="max_drawdown"
                  label={L.metrics.max_drawdown}
                  value={pct(-result.max_drawdown_pct)}
                  health="down"
                />
                <MetricCard
                  termKey="sharpe"
                  label={L.metrics.sharpe}
                  value={result.sharpe.toFixed(2)}
                  health={result.sharpe < 0 ? "down" : result.sharpe > 1 ? "up" : "neutral"}
                />
                <MetricCard
                  termKey="win_rate"
                  label={L.metrics.win_rate}
                  value={`${result.win_rate.toFixed(0)}%`}
                  health="neutral"
                />
              </div>
              {result.num_trades === 0 && (
                <p className="rounded-md border border-warning/40 bg-surface-2 px-3 py-2 text-sm text-warning">
                  {L.backtest.noTrades}
                </p>
              )}
              <div>
                <button
                  type="button"
                  onClick={() => setMoreMetrics((m) => !m)}
                  className="text-xs text-muted hover:text-text"
                >
                  {L.backtest.moreMetrics} {moreMetrics ? "▴" : "▾"}
                </button>
                {moreMetrics && (
                  <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
                    <span><Term k="cagr">{L.metrics.cagr}</Term> <span className="num">{pct(result.cagr)}</span></span>
                    <span><Term k="sortino">{L.metrics.sortino}</Term> <span className="num">{result.sortino.toFixed(2)}</span></span>
                    <span><Term k="calmar">{L.metrics.calmar}</Term> <span className="num">{result.calmar.toFixed(2)}</span></span>
                    <span><Term k="profit_factor">{L.metrics.profit_factor}</Term> <span className="num">{result.profit_factor == null ? "∞" : result.profit_factor.toFixed(2)}</span></span>
                    <span><Term k="annualized_volatility">{L.metrics.annualized_volatility}</Term> <span className="num">{pct(result.annualized_volatility * 100)}</span></span>
                    <span><Term k="exposure">{L.metrics.exposure}</Term> <span className="num">{result.exposure_pct.toFixed(0)}%</span></span>
                    <span><Term k="turnover">{L.metrics.turnover}</Term> <span className="num">{result.turnover.toFixed(2)}×</span></span>
                    <span><Term k="max_consecutive_losses">{L.metrics.max_consecutive_losses}</Term> <span className="num">{result.max_consecutive_losses}</span></span>
                    <span><Term k="num_trades">{L.metrics.num_trades}</Term> <span className="num">{result.num_trades}</span></span>
                  </div>
                )}
              </div>
              {overviewCandles.length > 0 && (
                <PriceChart
                  candles={overviewCandles}
                  markers={tradesToMarkers(result.trades)}
                  overlays={ovOverlays}
                  height={320}
                />
              )}
              <EquityChart points={result.equity_curve} />
            </div>
          )}

          {result && tab === "trades" && (
            <div className="max-h-80 overflow-y-auto">
              {result.trades.length === 0 ? (
                <p className="text-sm text-muted">{L.backtest.noTrades}</p>
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

          {tab === "compare" && comparison && (
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

          {tab === "optimize" && optimization && (
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
                              setAppliedHint(true);
                              setTab("overview");
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

          {tab === "walkforward" && walkforward && (
            <div className="space-y-2">
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
                <span className="text-muted">
                  {walkforward.strategy} · {walkforward.metric} · {walkforward.anchored ? "anchored" : "rolling"} ·{" "}
                  {walkforward.n_folds} folds
                </span>
                <span className={walkforward.aggregate_oos_return_pct >= 0 ? "text-up" : "text-down"}>
                  Agg OOS return {pct(walkforward.aggregate_oos_return_pct)}
                </span>
                <span className={walkforward.aggregate_oos_metric >= 0 ? "text-up" : "text-down"}>
                  Agg OOS {walkforward.metric} {walkforward.aggregate_oos_metric.toFixed(2)}
                </span>
              </div>
              <table className="w-full text-left text-xs">
                <thead className="text-faint">
                  <tr>
                    <th className="py-1">Fold</th>
                    <th>Best params</th>
                    <th className="num">IS {walkforward.metric}</th>
                    <th className="num">OOS {walkforward.metric}</th>
                    <th className="num">OOS Ret</th>
                    <th className="num">OOS Max DD</th>
                  </tr>
                </thead>
                <tbody>
                  {walkforward.folds.map((f) => (
                    <tr key={f.fold} className="border-t border-border">
                      <td className="py-1">{f.fold}</td>
                      {f.error ? (
                        <td colSpan={5} className="text-error">
                          {f.error}
                        </td>
                      ) : (
                        <>
                          <td className="font-mono">
                            {Object.entries(f.best_params)
                              .map(([k, v]) => `${k}=${v}`)
                              .join(", ")}
                          </td>
                          <td className="num">{f.is_metric.toFixed(2)}</td>
                          <td className={`num ${f.oos_metric >= 0 ? "text-up" : "text-down"}`}>{f.oos_metric.toFixed(2)}</td>
                          <td className={`num ${f.oos_return_pct >= 0 ? "text-up" : "text-down"}`}>{pct(f.oos_return_pct)}</td>
                          <td className="num text-down">{pct(-f.oos_max_drawdown_pct)}</td>
                        </>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
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

function TabBtn({
  id, tab, setTab, children,
}: {
  id: "overview" | "trades" | "compare" | "optimize" | "walkforward";
  tab: string;
  setTab: (t: "overview" | "trades" | "compare" | "optimize" | "walkforward") => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={() => setTab(id)}
      className={`px-3 py-1.5 ${tab === id ? "border-b-2 border-accent text-text" : "text-muted hover:text-text"}`}
    >
      {children}
    </button>
  );
}
