"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api, type Signal } from "@/lib/api";
import { CandleChart } from "./CandleChart";

const SIGNAL_COLORS: Record<string, string> = {
  buy: "text-green-400",
  sell: "text-red-400",
  hold: "text-yellow-400",
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

  return (
    <section className="rounded-lg border border-neutral-800 bg-neutral-900/40 p-4">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <h2 className="mr-2 text-lg font-semibold">Market</h2>
        <input
          value={symbol}
          onChange={(e) => setSymbol(e.target.value.toUpperCase())}
          className="rounded bg-neutral-800 px-2 py-1 text-sm"
          placeholder="BTC/USDT"
        />
        <select
          value={timeframe}
          onChange={(e) => setTimeframe(e.target.value)}
          className="rounded bg-neutral-800 px-2 py-1 text-sm"
        >
          {["15m", "1h", "4h", "1d"].map((tf) => (
            <option key={tf} value={tf}>
              {tf}
            </option>
          ))}
        </select>
        <button
          onClick={askAi}
          disabled={aiLoading}
          className="rounded bg-indigo-600 px-3 py-1 text-sm font-medium hover:bg-indigo-500 disabled:opacity-50"
        >
          {aiLoading ? "Asking AI…" : "AI Signal"}
        </button>
      </div>

      {candles.isError && (
        <p className="mb-2 text-sm text-red-400">Chart error: {(candles.error as Error).message}</p>
      )}
      {candles.data && candles.data.length > 0 ? (
        <CandleChart candles={candles.data} />
      ) : (
        !candles.isError && <p className="text-sm text-neutral-500">Loading candles…</p>
      )}

      {aiError && <p className="mt-3 text-sm text-red-400">AI error: {aiError}</p>}
      {aiSignal && (
        <div className="mt-3 rounded border border-neutral-800 bg-neutral-900 p-3 text-sm">
          <span className={`font-bold uppercase ${SIGNAL_COLORS[aiSignal.action]}`}>
            {aiSignal.action}
          </span>{" "}
          <span className="text-neutral-400">
            (confidence {(aiSignal.confidence * 100).toFixed(0)}% · {aiSignal.source})
          </span>
          <p className="mt-1 text-neutral-300">{aiSignal.reason}</p>
        </div>
      )}
    </section>
  );
}
