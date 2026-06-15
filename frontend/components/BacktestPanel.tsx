"use client";

import { useState } from "react";
import { api, type BacktestResult, type EquityPoint } from "@/lib/api";

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
  const up = values[values.length - 1] >= values[0];
  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="h-16 w-full">
      <path d={path} fill="none" stroke={up ? "#22c55e" : "#ef4444"} strokeWidth={1} />
    </svg>
  );
}

export function BacktestPanel() {
  const [symbol, setSymbol] = useState("BTC/USDT");
  const [strategy, setStrategy] = useState("ma_cross");
  const [fast, setFast] = useState(10);
  const [slow, setSlow] = useState(20);
  const [window, setWindow] = useState(14);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function run() {
    setLoading(true);
    setError(null);
    setResult(null);
    const params = strategy === "rsi" ? { window } : { fast, slow };
    try {
      setResult(await api.backtest({ symbol, strategy, params, timeframe: "1h", limit: 500 }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const pct = (n: number) => `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;

  return (
    <section className="rounded-lg border border-neutral-800 bg-neutral-900/40 p-4">
      <h2 className="mb-3 text-lg font-semibold">Backtest</h2>
      <div className="mb-3 flex flex-wrap items-end gap-2">
        <input
          value={symbol}
          onChange={(e) => setSymbol(e.target.value.toUpperCase())}
          className="rounded bg-neutral-800 px-2 py-1 text-sm"
          placeholder="BTC/USDT"
        />
        <select
          value={strategy}
          onChange={(e) => setStrategy(e.target.value)}
          className="rounded bg-neutral-800 px-2 py-1 text-sm"
        >
          <option value="ma_cross">ma_cross</option>
          <option value="rsi">rsi</option>
        </select>
        {strategy === "rsi" ? (
          <NumInput label="window" value={window} onChange={setWindow} />
        ) : (
          <>
            <NumInput label="fast" value={fast} onChange={setFast} />
            <NumInput label="slow" value={slow} onChange={setSlow} />
          </>
        )}
        <button
          onClick={run}
          disabled={loading}
          className="rounded bg-indigo-600 px-3 py-1 text-sm font-medium hover:bg-indigo-500 disabled:opacity-50"
        >
          {loading ? "Running…" : "Run backtest"}
        </button>
      </div>

      {error && <p className="text-sm text-red-400">Backtest error: {error}</p>}
      {result && (
        <div className="space-y-3">
          <Sparkline points={result.equity_curve} />
          <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
            <Metric
              label="Return"
              value={pct(result.total_return_pct)}
              good={result.total_return_pct >= 0}
            />
            <Metric label="Buy & Hold" value={pct(result.buy_hold_return_pct)} good={result.buy_hold_return_pct >= 0} />
            <Metric label="Max DD" value={pct(-result.max_drawdown_pct)} good={false} />
            <Metric label="Trades" value={`${result.num_trades} (${result.win_rate.toFixed(0)}% win)`} />
          </div>
        </div>
      )}
    </section>
  );
}

function NumInput({ label, value, onChange }: { label: string; value: number; onChange: (n: number) => void }) {
  return (
    <label className="text-xs text-neutral-400">
      {label}
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="ml-1 w-16 rounded bg-neutral-800 px-1 py-1 text-sm text-neutral-100"
      />
    </label>
  );
}

function Metric({ label, value, good }: { label: string; value: string; good?: boolean }) {
  const color = good === undefined ? "text-neutral-100" : good ? "text-green-400" : "text-red-400";
  return (
    <div className="rounded bg-neutral-800/60 p-2">
      <div className="text-xs text-neutral-500">{label}</div>
      <div className={`font-semibold ${color}`}>{value}</div>
    </div>
  );
}
