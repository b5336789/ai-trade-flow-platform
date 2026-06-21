"use client";
import { createChart, ColorType, type IChartApi, type ISeriesApi, type UTCTimestamp } from "lightweight-charts";
import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type Candle } from "@/lib/api";
import {
  toCandlestickData, toVolumeData, markerToSeries,
  type ChartMarker, type Overlay, type LiveConfig, type OHLCV,
} from "@/lib/chart-helpers";

export interface PriceChartProps {
  candles: Candle[];
  height?: number;
  markers?: ChartMarker[];
  overlays?: Overlay[];
  volume?: boolean;
  live?: LiveConfig | null;
  onCrosshairMove?: (p: OHLCV | null) => void;
}

function cssVar(name: string, fallback: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

// 簡單均線(用收盤價算 SMA);overlays 疊加用。
function sma(values: number[], period: number): (number | null)[] {
  const out: (number | null)[] = [];
  let sum = 0;
  for (let i = 0; i < values.length; i++) {
    sum += values[i];
    if (i >= period) sum -= values[i - period];
    out.push(i >= period - 1 ? sum / period : null);
  }
  return out;
}

export function PriceChart({
  candles, height = 360, markers, overlays, volume = true, live, onCrosshairMove,
}: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);

  // 建圖一次。candles 變動只 setData,不重建(避免閃爍/丟縮放)。
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const up = cssVar("--up", "#34D399");
    const down = cssVar("--down", "#F87171");
    const bg = cssVar("--bg", "#0A0B0D");
    const grid = cssVar("--border", "#1f1f1f");
    const text = cssVar("--muted", "#8A9099");

    const chart = createChart(el, {
      layout: { background: { type: ColorType.Solid, color: bg }, textColor: text },
      grid: { vertLines: { color: grid }, horzLines: { color: grid } },
      width: el.clientWidth, height,
      timeScale: { timeVisible: true },
      crosshair: { mode: 1 },
    });
    const candleSeries = chart.addCandlestickSeries({
      upColor: up, downColor: down, borderVisible: false, wickUpColor: up, wickDownColor: down,
    });
    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;

    if (volume) {
      const vol = chart.addHistogramSeries({ priceFormat: { type: "volume" }, priceScaleId: "" });
      vol.priceScale().applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
      volumeSeriesRef.current = vol;
    }

    // 十字準星 → 回拋當前根 OHLCV
    if (onCrosshairMove) {
      chart.subscribeCrosshairMove((param) => {
        const bar = param.seriesData.get(candleSeries) as
          | { open: number; high: number; low: number; close: number } | undefined;
        const v = volumeSeriesRef.current
          ? (param.seriesData.get(volumeSeriesRef.current) as { value: number } | undefined)
          : undefined;
        if (!bar || param.time == null) { onCrosshairMove(null); return; }
        onCrosshairMove({ time: param.time as number, ...bar, volume: v?.value ?? 0 });
      });
    }

    const ro = new ResizeObserver(() => chart.applyOptions({ width: el.clientWidth }));
    ro.observe(el);
    return () => { ro.disconnect(); chart.remove(); chartRef.current = null; candleSeriesRef.current = null; volumeSeriesRef.current = null; };
  // 僅在 height/volume/crosshair 身份改變時重建;candles 不在依賴內。
  }, [height, volume, onCrosshairMove]);

  // 資料更新:setData(整段)。增量 update 由 live 模式負責(Task 5)。
  useEffect(() => {
    const cs = candleSeriesRef.current, chart = chartRef.current;
    if (!cs || !chart) return;
    const up = cssVar("--up", "#34D399"), down = cssVar("--down", "#F87171");
    cs.setData(toCandlestickData(candles));
    if (volumeSeriesRef.current) volumeSeriesRef.current.setData(toVolumeData(candles, up, down));
    chart.timeScale().fitContent();
  }, [candles]);

  // 標記
  useEffect(() => {
    const cs = candleSeriesRef.current;
    if (!cs) return;
    const up = cssVar("--up", "#34D399"), down = cssVar("--down", "#F87171");
    cs.setMarkers((markers ?? []).map((m) => markerToSeries(m, up, down)));
  }, [markers]);

  // 疊加均線
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || !overlays?.length) return;
    const closes = candles.map((c) => c.close);
    const times = candles.map((c) => Math.floor(new Date(c.timestamp).getTime() / 1000) as UTCTimestamp);
    const lines = overlays.map((ov) => {
      const line = chart.addLineSeries({ color: ov.color ?? cssVar("--accent", "#22D3EE"), lineWidth: 1 });
      const series = sma(closes, ov.period);
      line.setData(times.map((t, i) => (series[i] == null ? null : { time: t, value: series[i]! })).filter(Boolean) as { time: UTCTimestamp; value: number }[]);
      return line;
    });
    return () => { lines.forEach((l) => chart.removeSeries(l)); };
  }, [overlays, candles]);

  // ── Live 輪詢(live 非 null 時啟用)──────────────────────────────
  const [lastPrice, setLastPrice] = useState<number | null>(null);
  const [flash, setFlash] = useState<"up" | "down" | null>(null);

  const liveQuery = useQuery({
    queryKey: ["price-live", live?.symbol, live?.timeframe, live?.market],
    queryFn: () => api.ohlcv(live!.symbol, live!.timeframe, 2, live!.market ?? "crypto"),
    enabled: !!live,
    refetchInterval: live ? Math.max(1000, live.intervalMs ?? 3000) : false,
    refetchIntervalInBackground: false, // 分頁失焦自動停
  });

  useEffect(() => {
    const cs = candleSeriesRef.current;
    const rows = liveQuery.data;
    if (!cs || !rows || !rows.length) return;
    const up = cssVar("--up", "#34D399"), down = cssVar("--down", "#F87171");
    for (const c of rows) {
      const t = Math.floor(new Date(c.timestamp).getTime() / 1000) as UTCTimestamp;
      cs.update({ time: t, open: c.open, high: c.high, low: c.low, close: c.close });
      if (volumeSeriesRef.current) {
        volumeSeriesRef.current.update({ time: t, value: c.volume, color: c.close >= c.open ? up : down });
      }
    }
    const newClose = rows[rows.length - 1].close;
    setLastPrice((prev) => {
      if (prev != null && newClose !== prev) setFlash(newClose > prev ? "up" : "down");
      return newClose;
    });
  }, [liveQuery.data]);

  useEffect(() => {
    if (!flash) return;
    const id = setTimeout(() => setFlash(null), 200);
    return () => clearTimeout(id);
  }, [flash]);

  if (!candles.length) {
    return (
      <div className="grid w-full place-items-center rounded-md border border-border bg-surface-1 text-sm text-muted" style={{ height }}>
        無資料
      </div>
    );
  }
  return (
    <div className="relative w-full">
      {live && lastPrice != null && (
        <div
          className={`num absolute right-2 top-2 z-10 rounded-md border border-border bg-surface-2 px-2 py-0.5 text-xs transition-colors ${
            flash === "up" ? "text-up" : flash === "down" ? "text-down" : "text-text"
          }`}
        >
          {lastPrice.toFixed(2)}
        </div>
      )}
      <div ref={containerRef} className="w-full" />
    </div>
  );
}
