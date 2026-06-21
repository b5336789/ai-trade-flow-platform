// Pure functions + shared chart types. No React, directly testable.
import type {
  UTCTimestamp,
  Time,
  CandlestickData,
  HistogramData,
  SeriesMarker,
} from "lightweight-charts";
import type { Candle } from "./api";

export interface OHLCV {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}
export interface LiveConfig {
  symbol: string;
  timeframe: string;
  market?: string;
  intervalMs?: number;
}
export interface ChartMarker {
  time: number;
  position: "aboveBar" | "belowBar";
  kind: "buy" | "sell";
  text?: string;
}
export interface Overlay {
  id: string;
  type: "sma" | "ema";
  period: number;
  color?: string;
}
export interface TradeLike {
  entry_time: string;
  exit_time: string;
  return_pct: number;
}

const toUtc = (iso: string): UTCTimestamp =>
  Math.floor(new Date(iso).getTime() / 1000) as UTCTimestamp;

export const candleTime = (c: Candle): UTCTimestamp => toUtc(c.timestamp);

export function toCandlestickData(candles: Candle[]): CandlestickData[] {
  return candles.map((c) => ({
    time: candleTime(c),
    open: c.open,
    high: c.high,
    low: c.low,
    close: c.close,
  }));
}

export function toVolumeData(
  candles: Candle[],
  upColor: string,
  downColor: string
): HistogramData[] {
  return candles.map((c) => ({
    time: candleTime(c),
    value: c.volume,
    color: c.close >= c.open ? upColor : downColor,
  }));
}

// Each trade → entry (▲ buy) + exit (▼ sell, text with return %). Output sorted ascending by time (setMarkers requirement).
export function tradesToMarkers(trades: TradeLike[]): ChartMarker[] {
  const out: ChartMarker[] = [];
  for (const t of trades) {
    out.push({
      time: toUtc(t.entry_time),
      position: "belowBar",
      kind: "buy",
      text: "買",
    });
    const sign = t.return_pct >= 0 ? "+" : "";
    out.push({
      time: toUtc(t.exit_time),
      position: "aboveBar",
      kind: "sell",
      text: `賣 ${sign}${t.return_pct.toFixed(1)}%`,
    });
  }
  return out.sort((a, b) => a.time - b.time);
}

export function markerToSeries(
  m: ChartMarker,
  upColor: string,
  downColor: string
): SeriesMarker<Time> {
  return {
    time: m.time as UTCTimestamp,
    position: m.position,
    color: m.kind === "buy" ? upColor : downColor,
    shape: m.kind === "buy" ? "arrowUp" : "arrowDown",
    text: m.text,
  };
}
