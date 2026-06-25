"use client";
import { createChart, ColorType, PriceScaleMode, type IChartApi, type ISeriesApi, type UTCTimestamp } from "lightweight-charts";
import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Maximize2 } from "lucide-react";
import { api, type Candle } from "@/lib/api";
import {
  toCandlestickData, toVolumeData, markerToSeries,
  sma, ema, bollinger, rsi, macd,
  type ChartMarker, type Overlay, type LiveConfig, type OHLCV, type IndicatorConfig, type OscillatorConfig,
} from "@/lib/chart-helpers";
import { useTheme } from "@/app/providers";

export interface PriceChartProps {
  candles: Candle[];
  height?: number;
  markers?: ChartMarker[];
  overlays?: Overlay[];
  indicators?: IndicatorConfig[];
  oscillators?: OscillatorConfig[];
  volume?: boolean;
  live?: LiveConfig | null;
  onCrosshairMove?: (p: OHLCV | null) => void;
  chartType?: "candles" | "line" | "area";
  logScale?: boolean;
  showLegend?: boolean;
}

function cssVar(name: string, fallback: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

export function PriceChart({
  candles, height = 360, markers, overlays, indicators, oscillators = [], volume = true, live, onCrosshairMove,
  chartType = "candles", logScale = false, showLegend = true,
}: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  // 主序列 ref(可能是 candlestick / line / area)
  const mainSeriesRef = useRef<ISeriesApi<"Candlestick" | "Line" | "Area"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const oscRefs = useRef<Record<string, HTMLDivElement | null>>({});
  // live update() 的高水位:已套用的最新一根時間。低於此值的 live 列要跳過,
  // 否則 lightweight-charts 會 throw「Cannot update oldest data」→ Application error。
  const lastBarTimeRef = useRef<number>(0);
  const [legend, setLegend] = useState<OHLCV | null>(null);
  const { resolved } = useTheme();

  const toggleFullscreen = () => {
    const el = wrapRef.current;
    if (!el) return;
    if (document.fullscreenElement) document.exitFullscreen();
    else el.requestFullscreen?.();
  };

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
      rightPriceScale: { mode: logScale ? PriceScaleMode.Logarithmic : PriceScaleMode.Normal },
    });
    let main: ISeriesApi<"Candlestick" | "Line" | "Area">;
    if (chartType === "line") {
      main = chart.addLineSeries({ color: up, lineWidth: 2 });
    } else if (chartType === "area") {
      main = chart.addAreaSeries({ lineColor: up, topColor: up, bottomColor: "rgba(0,0,0,0)", lineWidth: 2 });
    } else {
      main = chart.addCandlestickSeries({
        upColor: up, downColor: down, borderVisible: false, wickUpColor: up, wickDownColor: down,
      });
    }
    mainSeriesRef.current = main;
    chartRef.current = chart;

    if (volume) {
      const vol = chart.addHistogramSeries({ priceFormat: { type: "volume" }, priceScaleId: "" });
      vol.priceScale().applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
      volumeSeriesRef.current = vol;
    }

    // 十字準星 → 更新內部 legend 並回拋 OHLCV(即使外部沒給 onCrosshairMove 也訂閱)
    chart.subscribeCrosshairMove((param) => {
      const bar = param.seriesData.get(main) as
        | { open: number; high: number; low: number; close: number; value?: number } | undefined;
      const v = volumeSeriesRef.current
        ? (param.seriesData.get(volumeSeriesRef.current) as { value: number } | undefined)
        : undefined;
      if (!bar || param.time == null) { setLegend(null); onCrosshairMove?.(null); return; }
      const ohlcv: OHLCV = {
        time: param.time as number,
        open: bar.open ?? bar.value ?? 0, high: bar.high ?? bar.value ?? 0,
        low: bar.low ?? bar.value ?? 0, close: bar.close ?? bar.value ?? 0,
        volume: v?.value ?? 0,
      };
      setLegend(ohlcv);
      onCrosshairMove?.(ohlcv);
    });

    const ro = new ResizeObserver(() => chart.applyOptions({ width: el.clientWidth }));
    ro.observe(el);
    return () => { ro.disconnect(); chart.remove(); chartRef.current = null; mainSeriesRef.current = null; volumeSeriesRef.current = null; };
  // 類型/座標改變需重建;candles 不在依賴內。
  }, [height, volume, onCrosshairMove, chartType, logScale, resolved]);

  // 資料更新:setData(整段)。增量 update 由 live 模式負責(Task 5)。
  useEffect(() => {
    const cs = mainSeriesRef.current, chart = chartRef.current;
    if (!cs || !chart) return;
    const up = cssVar("--up", "#34D399"), down = cssVar("--down", "#F87171");
    if (chartType === "candles") {
      (cs as ISeriesApi<"Candlestick">).setData(toCandlestickData(candles));
    } else {
      const line = candles.map((c) => ({
        time: Math.floor(new Date(c.timestamp).getTime() / 1000) as UTCTimestamp,
        value: c.close,
      }));
      (cs as ISeriesApi<"Line" | "Area">).setData(line);
    }
    if (volumeSeriesRef.current) volumeSeriesRef.current.setData(toVolumeData(candles, up, down));
    chart.timeScale().fitContent();
    // setData 重設序列基準 → live 高水位也跟著重設到「目前最後一根」。
    lastBarTimeRef.current = candles.length
      ? Math.floor(new Date(candles[candles.length - 1].timestamp).getTime() / 1000)
      : 0;
  }, [candles, chartType, resolved]);

  // 標記
  useEffect(() => {
    const cs = mainSeriesRef.current;
    if (!cs) return;
    const up = cssVar("--up", "#34D399"), down = cssVar("--down", "#F87171");
    cs.setMarkers((markers ?? []).map((m) => markerToSeries(m, up, down)));
  }, [markers, resolved]);

  // 疊加均線(含 Bollinger);同時涵蓋舊 overlays → 轉等效 indicator(DRY)。
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    const times = candles.map((c) => Math.floor(new Date(c.timestamp).getTime() / 1000) as UTCTimestamp);
    const closes = candles.map((c) => c.close);
    const toLine = (vals: (number | null)[]) =>
      times.map((t, i) => (vals[i] == null ? null : { time: t, value: vals[i]! }))
           .filter(Boolean) as { time: UTCTimestamp; value: number }[];

    // 舊 overlays(sma/ema)轉成 IndicatorConfig,維持向下相容。
    const legacy: IndicatorConfig[] = (overlays ?? []).map((o) => ({
      id: o.id, type: o.type, period: o.period, color: o.color,
    }));
    const all = [...legacy, ...(indicators ?? [])];

    const series = all.flatMap((cfg) => {
      const color = cfg.color
        ? (cfg.color.startsWith("--") ? cssVar(cfg.color, "#8A9099") : cfg.color)
        : cssVar("--muted", "#8A9099");
      if (cfg.type === "bollinger") {
        const bb = bollinger(closes, cfg.period, 2);
        const mid = chart.addLineSeries({ color, lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
        const upper = chart.addLineSeries({ color, lineWidth: 1, lineStyle: 2, priceLineVisible: false, lastValueVisible: false });
        const lower = chart.addLineSeries({ color, lineWidth: 1, lineStyle: 2, priceLineVisible: false, lastValueVisible: false });
        mid.setData(toLine(bb.mid)); upper.setData(toLine(bb.upper)); lower.setData(toLine(bb.lower));
        return [mid, upper, lower];
      }
      const vals = cfg.type === "ema" ? ema(closes, cfg.period) : sma(closes, cfg.period);
      const line = chart.addLineSeries({ color, lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
      line.setData(toLine(vals));
      return [line];
    });

    return () => {
      if (chartRef.current !== chart) return; // chart 已 dispose 時不可 removeSeries
      series.forEach((s) => chart.removeSeries(s));
    };
  }, [overlays, indicators, candles, resolved]);

  // ── 副圖:RSI / MACD(獨立 chart 實例,時間軸雙向同步)──────────────
  useEffect(() => {
    const mainChart = chartRef.current;
    if (!mainChart || !oscillators?.length) return;
    const grid = cssVar("--border", "#1f1f1f");
    const text = cssVar("--muted", "#8A9099");
    const bg = cssVar("--bg", "#0A0B0D");
    const accent = cssVar("--accent", "#22D3EE");
    const upC = cssVar("--up", "#34D399"), downC = cssVar("--down", "#F87171");
    const times = candles.map((c) => Math.floor(new Date(c.timestamp).getTime() / 1000) as UTCTimestamp);
    const closes = candles.map((c) => c.close);
    const toLine = (vals: (number | null)[]) =>
      times.map((t, i) => (vals[i] == null ? null : { time: t, value: vals[i]! }))
           .filter(Boolean) as { time: UTCTimestamp; value: number }[];

    const charts: IChartApi[] = [];
    let syncing = false; // 防雙向遞迴

    for (const o of oscillators) {
      const el = oscRefs.current[o.id];
      if (!el) continue;
      const h = o.type === "rsi" ? 110 : 120;
      const c = createChart(el, {
        layout: { background: { type: ColorType.Solid, color: bg }, textColor: text },
        grid: { vertLines: { color: grid }, horzLines: { color: grid } },
        width: el.clientWidth, height: h,
        timeScale: { timeVisible: true, visible: false },
        crosshair: { mode: 1 },
      });
      if (o.type === "rsi") {
        const line = c.addLineSeries({ color: accent, lineWidth: 1 });
        line.setData(toLine(rsi(closes, o.period ?? 14)));
        // 30/70 參考線
        line.createPriceLine({ price: 70, color: grid, lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: "70" });
        line.createPriceLine({ price: 30, color: grid, lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: "30" });
      } else {
        const m = macd(closes);
        const hist = c.addHistogramSeries({ priceLineVisible: false });
        hist.setData(times.map((t, i) => (m.hist[i] == null ? null : {
          time: t, value: m.hist[i]!, color: (m.hist[i] as number) >= 0 ? upC : downC,
        })).filter(Boolean) as { time: UTCTimestamp; value: number; color: string }[]);
        const macdLine = c.addLineSeries({ color: accent, lineWidth: 1 });
        const sigLine = c.addLineSeries({ color: text, lineWidth: 1 });
        macdLine.setData(toLine(m.macd));
        sigLine.setData(toLine(m.signal));
      }
      const ro = new ResizeObserver(() => c.applyOptions({ width: el.clientWidth }));
      ro.observe(el);
      (c as unknown as { _ro?: ResizeObserver })._ro = ro;
      charts.push(c);
    }

    // 雙向同步:主圖 ↔ 每張副圖
    const allCharts = [mainChart, ...charts];
    const unsub: Array<() => void> = [];
    for (const src of allCharts) {
      const handler = (range: unknown) => {
        if (syncing || range == null) return;
        syncing = true;
        for (const dst of allCharts) {
          if (dst !== src) dst.timeScale().setVisibleLogicalRange(range as never);
        }
        syncing = false;
      };
      src.timeScale().subscribeVisibleLogicalRangeChange(handler);
      unsub.push(() => src.timeScale().unsubscribeVisibleLogicalRangeChange(handler));
    }

    return () => {
      unsub.forEach((u) => u());
      charts.forEach((c) => {
        const ro = (c as unknown as { _ro?: ResizeObserver })._ro;
        ro?.disconnect();
        c.remove();
      });
    };
  }, [oscillators, candles, resolved]);

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
    const cs = mainSeriesRef.current;
    const rows = liveQuery.data;
    if (!cs || !rows || !rows.length) return;
    const up = cssVar("--up", "#34D399"), down = cssVar("--down", "#F87171");
    // line/area 序列的 update({open,high,low,close}) 無效;live 僅 crypto 且預設 candles。
    if (chartType !== "candles") return;
    // update() 不能套用比「序列目前最新一根」更舊的根(否則 throw "Cannot update oldest data")。
    // 比對動態高水位(會隨 live 新根前進),而非靜態的初始最後一根——後者在跨週期換根後會失準。
    for (const c of rows) {
      const t = Math.floor(new Date(c.timestamp).getTime() / 1000) as UTCTimestamp;
      if (t < lastBarTimeRef.current) continue; // 跳過比目前最新一根更舊的列
      cs.update({ time: t, open: c.open, high: c.high, low: c.low, close: c.close });
      if (volumeSeriesRef.current) {
        volumeSeriesRef.current.update({ time: t, value: c.volume, color: c.close >= c.open ? up : down });
      }
      lastBarTimeRef.current = t;
    }
    const newClose = rows[rows.length - 1].close;
    setLastPrice((prev) => {
      if (prev != null && newClose !== prev) setFlash(newClose > prev ? "up" : "down");
      return newClose;
    });
  }, [liveQuery.data, candles, chartType]);

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
    <div ref={wrapRef} className="relative w-full bg-bg">
      {showLegend && legend && (
        <div className="num pointer-events-none absolute left-2 top-2 z-10 flex gap-2 rounded-md border border-border bg-surface-2/90 px-2 py-1 text-[11px]">
          <span className="text-faint">O <span className="text-text">{legend.open}</span></span>
          <span className="text-faint">H <span className="text-text">{legend.high}</span></span>
          <span className="text-faint">L <span className="text-text">{legend.low}</span></span>
          <span className="text-faint">C <span className={legend.close >= legend.open ? "text-up" : "text-down"}>{legend.close}</span></span>
          <span className="text-faint">Vol <span className="text-text">{legend.volume.toLocaleString()}</span></span>
        </div>
      )}
      {live && lastPrice != null && (
        <div
          className={`num absolute right-10 top-2 z-10 rounded-md border border-border bg-surface-2 px-2 py-0.5 text-xs transition-colors ${
            flash === "up" ? "text-up" : flash === "down" ? "text-down" : "text-text"
          }`}
        >
          {lastPrice.toFixed(2)}
        </div>
      )}
      <button
        onClick={toggleFullscreen}
        className="absolute right-2 top-2 z-20 rounded-md border border-border bg-surface-2 p-1 text-muted hover:text-text"
        aria-label="全螢幕"
      >
        <Maximize2 size={14} />
      </button>
      <div ref={containerRef} className="w-full" />
      {(oscillators ?? []).map((o) => (
        <div key={o.id} className="relative mt-1">
          <span className="absolute left-2 top-1 z-10 text-[10px] uppercase tracking-wide text-faint">
            {o.type === "rsi" ? `RSI ${o.period ?? 14}` : "MACD 12·26·9"}
          </span>
          <div ref={(el) => { oscRefs.current[o.id] = el; }} className="w-full" />
        </div>
      ))}
    </div>
  );
}
