"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { api, type Signal } from "@/lib/api";
import { setMarket } from "@/lib/useMarket";
import { PriceChart } from "@/components/PriceChart";
import { deriveStats, barsPer24h } from "@/lib/market-stats";
import { L } from "@/lib/labels";
import type { ChartMarker } from "@/lib/chart-helpers";

const SIGNAL_COLORS: Record<string, string> = {
  buy: "text-up",
  sell: "text-down",
  hold: "text-warning",
};

// 內建常用標的;保留自由輸入(datalist)。
const COMMON_SYMBOLS: Record<string, string[]> = {
  crypto: ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "DOGE/USDT"],
  tw_stock: ["2330", "2317", "2454", "0050"],
  us_stock: ["AAPL", "MSFT", "NVDA", "TSLA", "SPY"],
};
const TIMEFRAMES = ["15m", "1h", "4h", "1d"];

const fmt = (n: number) => n.toLocaleString(undefined, { maximumFractionDigits: 4 });
const signed = (n: number) => `${n >= 0 ? "+" : ""}${n.toFixed(2)}`;

export function MarketPanel() {
  const router = useRouter();
  const pathname = usePathname();
  const sp = useSearchParams();
  const [symbol, setSymbol] = useState((sp.get("symbol") ?? "BTC/USDT").toUpperCase());
  const [timeframe, setTimeframe] = useState(sp.get("timeframe") ?? "1h");
  const [market, setMarketState] = useState(sp.get("market") ?? "crypto");
  const [paused, setPaused] = useState(false);
  const [aiSignal, setAiSignal] = useState<Signal | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);
  const [aiLoading, setAiLoading] = useState(false);

  useEffect(() => { setMarket(market); }, [market]);

  useEffect(() => {
    const q = new URLSearchParams({ symbol, timeframe, market });
    router.replace(`${pathname}?${q.toString()}`, { scroll: false });
  }, [symbol, timeframe, market, pathname, router]);

  const isCrypto = market === "crypto";

  // 歷史 K 線(給圖初始資料 + 推導 24h 統計)。
  const candles = useQuery({
    queryKey: ["ohlcv", symbol, timeframe, market],
    queryFn: () => api.ohlcv(symbol, timeframe, 200, market),
    retry: false,
  });

  // 現價(crypto 即時輪詢;台股/美股為離線 CSV,不偽裝即時)。
  const ticker = useQuery({
    queryKey: ["ticker", symbol, market],
    queryFn: () => api.ticker(symbol, market),
    retry: false,
    enabled: isCrypto && !paused,
    refetchInterval: isCrypto && !paused ? 3000 : false,
    refetchIntervalInBackground: false,
  });

  const stats = candles.data ? deriveStats(candles.data, barsPer24h(timeframe)) : null;
  const live = isCrypto && !paused ? { symbol, timeframe, market, intervalMs: 3000 } : null;

  // AI 訊號疊在最後一根 K(hold 不疊);text 帶信心度。
  const aiMarkers: ChartMarker[] = (() => {
    if (!aiSignal || aiSignal.action === "hold" || !candles.data?.length) return [];
    const lastIso = candles.data[candles.data.length - 1].timestamp;
    const time = Math.floor(new Date(lastIso).getTime() / 1000);
    const isBuy = aiSignal.action === "buy";
    return [{
      time,
      position: isBuy ? "belowBar" : "aboveBar",
      kind: isBuy ? "buy" : "sell",
      text: `AI ${aiSignal.action} ${(aiSignal.confidence * 100).toFixed(0)}%`,
    }];
  })();

  async function askAi() {
    setAiLoading(true);
    setAiError(null);
    setAiSignal(null);
    try {
      setAiSignal(await api.aiSignal(symbol, market, timeframe, 200));
    } catch (e) {
      setAiError((e as Error).message);
    } finally {
      setAiLoading(false);
    }
  }

  return (
    <section className="rounded-lg border border-border bg-surface-1 p-4">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <h2 className="font-display mr-2 text-lg font-semibold">{L.market.title}</h2>
        <input
          list="market-symbols"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value.toUpperCase())}
          className="rounded-md bg-surface-2 px-2 py-1 text-sm"
          placeholder={L.market.symbol}
        />
        <datalist id="market-symbols">
          {(COMMON_SYMBOLS[market] ?? []).map((s) => (
            <option key={s} value={s} />
          ))}
        </datalist>
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
          {TIMEFRAMES.map((tf) => (
            <option key={tf} value={tf}>{tf}</option>
          ))}
        </select>
        {isCrypto && (
          <button
            onClick={() => setPaused((p) => !p)}
            className="rounded-md border border-border-strong bg-surface-2 px-3 py-1 text-sm text-text hover:bg-surface-3"
          >
            {paused ? L.market.resume : L.market.pause}
          </button>
        )}
        <button
          onClick={askAi}
          disabled={aiLoading}
          className="rounded-md bg-accent px-3 py-1 text-sm font-medium text-bg hover:brightness-110 disabled:opacity-50"
        >
          {aiLoading ? L.market.askingAi : L.market.aiSignal}
        </button>
        {!isCrypto && (
          <span className="rounded-sm bg-surface-3 px-2 py-1 text-xs text-muted">
            {L.market.offlineCsv}
          </span>
        )}
      </div>

      {stats && (
        <div className="mb-3 flex flex-wrap items-baseline gap-x-5 gap-y-1 text-sm">
          <span className="num text-xl font-semibold text-text">
            {fmt(ticker.data?.price ?? stats.last)}
          </span>
          <span className={`num ${stats.changeAbs >= 0 ? "text-up" : "text-down"}`}>
            {L.market.change24h} {signed(stats.changeAbs)} ({signed(stats.changePct)}%)
          </span>
          <span className="num text-muted">{L.market.high24h} {fmt(stats.high)}</span>
          <span className="num text-muted">{L.market.low24h} {fmt(stats.low)}</span>
        </div>
      )}

      {candles.isError && (
        <p className="mb-2 text-sm text-error">{L.market.chartError}: {(candles.error as Error).message}</p>
      )}
      {candles.data && candles.data.length > 0 ? (
        <PriceChart candles={candles.data} live={live} markers={aiMarkers} height={360} />
      ) : (
        !candles.isError && <p className="text-sm text-faint">{L.market.loadingCandles}</p>
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
