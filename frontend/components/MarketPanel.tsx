"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, type Signal } from "@/lib/api";
import { setMarket } from "@/lib/useMarket";
import { CandleChart } from "./CandleChart";

const SIGNAL_COLORS: Record<string, string> = {
  buy: "text-up",
  sell: "text-down",
  hold: "text-warning",
};

export function MarketPanel() {
  const [symbol, setSymbol] = useState("BTC/USDT");
  const [timeframe, setTimeframe] = useState("1h");
  const [market, setMarketState] = useState("crypto");
  const [aiSignal, setAiSignal] = useState<Signal | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);
  const [aiLoading, setAiLoading] = useState(false);

  useEffect(() => { setMarket(market); }, [market]);

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
      setAiSignal(await api.aiSignal(symbol, market, timeframe, 120));
    } catch (e) {
      setAiError((e as Error).message);
    } finally {
      setAiLoading(false);
    }
  }

  return (
    <section className="rounded-lg border border-border bg-surface-1 p-4">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <h2 className="font-display mr-2 text-lg font-semibold">Market</h2>
        <input
          value={symbol}
          onChange={(e) => setSymbol(e.target.value.toUpperCase())}
          className="rounded-md bg-surface-2 px-2 py-1 text-sm"
          placeholder="BTC/USDT"
        />
        <select
          value={market}
          onChange={(e) => setMarketState(e.target.value)}
          className="rounded-md bg-surface-2 px-2 py-1 text-sm"
        >
          <option value="crypto">Crypto</option>
          <option value="tw_stock">台股</option>
          <option value="us_stock">美股</option>
        </select>
        <select
          value={timeframe}
          onChange={(e) => setTimeframe(e.target.value)}
          className="rounded-md bg-surface-2 px-2 py-1 text-sm"
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
          className="rounded-md bg-accent px-3 py-1 text-sm font-medium hover:bg-accent-dim disabled:opacity-50"
        >
          {aiLoading ? "Asking AI…" : "AI Signal"}
        </button>
      </div>

      {candles.isError && (
        <p className="mb-2 text-sm text-error">Chart error: {(candles.error as Error).message}</p>
      )}
      {candles.data && candles.data.length > 0 ? (
        <CandleChart candles={candles.data} />
      ) : (
        !candles.isError && <p className="text-sm text-faint">Loading candles…</p>
      )}

      {aiError && <p className="mt-3 text-sm text-error">AI error: {aiError}</p>}
      {aiSignal && (
        <div className="mt-3 rounded-lg border border-border bg-surface-2 p-3 text-sm">
          <span className={`font-bold uppercase ${SIGNAL_COLORS[aiSignal.action]}`}>
            {aiSignal.action}
          </span>{" "}
          <span className="text-muted">
            (confidence <span className="num">{(aiSignal.confidence * 100).toFixed(0)}</span>% · {aiSignal.source})
          </span>
          <p className="mt-1 text-text">{aiSignal.reason}</p>
        </div>
      )}
    </section>
  );
}
