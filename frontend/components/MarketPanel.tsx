"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api, type Signal } from "@/lib/api";
import { CandleChart } from "./CandleChart";

const SIGNAL_STYLES: Record<string, { text: string; bar: string; chip: string; label: string }> = {
  buy: { text: "text-emerald-400", bar: "bg-emerald-400", chip: "border-emerald-500/40 bg-emerald-500/15 text-emerald-300", label: "買進" },
  sell: { text: "text-red-400", bar: "bg-red-400", chip: "border-red-500/40 bg-red-500/15 text-red-300", label: "賣出" },
  hold: { text: "text-amber-400", bar: "bg-amber-400", chip: "border-amber-500/40 bg-amber-500/15 text-amber-300", label: "觀望" },
};

export function MarketPanel() {
  const [symbol, setSymbol] = useState("BTC/USDT");
  const [timeframe, setTimeframe] = useState("1h");
  const [aiSignal, setAiSignal] = useState<Signal | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);
  const [aiLoading, setAiLoading] = useState(false);

  const candles = useQuery({
    queryKey: ["ohlcv", symbol, timeframe],
    queryFn: () => api.ohlcv(symbol, timeframe, 120),
    retry: false,
  });

  async function askAi() {
    setAiLoading(true);
    setAiError(null);
    setAiSignal(null);
    try {
      setAiSignal(await api.aiSignal(symbol, "crypto", timeframe, 120));
    } catch (e) {
      setAiError((e as Error).message);
    } finally {
      setAiLoading(false);
    }
  }

  const sig = aiSignal ? SIGNAL_STYLES[aiSignal.action] : null;

  return (
    <section className="card">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <h2 className="panel-title mr-1">📈 行情 Market</h2>
        <input
          value={symbol}
          onChange={(e) => setSymbol(e.target.value.toUpperCase())}
          className="input w-32"
          placeholder="BTC/USDT"
        />
        <div className="flex rounded-lg border border-white/5 bg-neutral-800/80 p-0.5">
          {["15m", "1h", "4h", "1d"].map((tf) => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                timeframe === tf ? "bg-brand-600 text-white" : "text-neutral-400 hover:text-neutral-200"
              }`}
            >
              {tf}
            </button>
          ))}
        </div>
        <button onClick={askAi} disabled={aiLoading} className="btn btn-primary ml-auto">
          {aiLoading ? (
            <>
              <Spinner /> 詢問 AI…
            </>
          ) : (
            <>✨ AI 訊號</>
          )}
        </button>
      </div>

      {candles.isError && (
        <p className="mb-2 text-sm text-red-400">行情載入失敗:{(candles.error as Error).message}</p>
      )}
      {candles.data && candles.data.length > 0 ? (
        <CandleChart candles={candles.data} />
      ) : (
        !candles.isError && <div className="skeleton h-[320px] w-full" />
      )}

      {aiError && <p className="mt-3 text-sm text-red-400">AI 錯誤:{aiError}</p>}
      {aiSignal && sig && (
        <div className="mt-3 animate-fade-in rounded-lg border border-white/5 bg-neutral-900/80 p-3 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`badge border ${sig.chip}`}>
              {sig.label} · {aiSignal.action.toUpperCase()}
            </span>
            <span className="text-xs text-neutral-500">來源 {aiSignal.source}</span>
            <div className="ml-auto flex items-center gap-2">
              <div className="h-1.5 w-24 overflow-hidden rounded-full bg-neutral-800">
                <div
                  className={`h-full rounded-full ${sig.bar}`}
                  style={{ width: `${Math.round(aiSignal.confidence * 100)}%` }}
                />
              </div>
              <span className={`text-xs font-semibold ${sig.text}`}>
                {(aiSignal.confidence * 100).toFixed(0)}%
              </span>
            </div>
          </div>
          <p className="mt-2 leading-relaxed text-neutral-300">{aiSignal.reason}</p>
        </div>
      )}
    </section>
  );
}

function Spinner() {
  return (
    <svg className="h-3.5 w-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-90" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
    </svg>
  );
}
