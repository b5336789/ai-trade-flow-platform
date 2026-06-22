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
export interface IndicatorConfig {
  id: string;
  type: "sma" | "ema" | "bollinger";
  period: number;
  color?: string; // CSS var (e.g. "--up") or hex; default neutral
}
export interface OscillatorConfig {
  id: string;
  type: "rsi" | "macd";
  period?: number; // rsi window (default 14)
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

// ── 技術指標(純函式,前端計算)。暖機期不足以計算時填 null(fail loud:不偽造數值)。──
export function sma(values: number[], period: number): (number | null)[] {
  const out: (number | null)[] = [];
  let sum = 0;
  for (let i = 0; i < values.length; i++) {
    sum += values[i];
    if (i >= period) sum -= values[i - period];
    out.push(i >= period - 1 ? sum / period : null);
  }
  return out;
}

// EMA:以前 period 根的 SMA 作種子,其後用遞迴 k=2/(period+1)。
export function ema(values: number[], period: number): (number | null)[] {
  const out: (number | null)[] = new Array(values.length).fill(null);
  if (period <= 0 || values.length < period) return out;
  const k = 2 / (period + 1);
  let prev = 0;
  for (let i = 0; i < period; i++) prev += values[i];
  prev /= period;
  out[period - 1] = prev;
  for (let i = period; i < values.length; i++) {
    prev = values[i] * k + prev * (1 - k);
    out[i] = prev;
  }
  return out;
}

// RSI:Wilder 平滑。第一個值落在索引 period。
export function rsi(values: number[], period = 14): (number | null)[] {
  const out: (number | null)[] = new Array(values.length).fill(null);
  if (values.length <= period) return out;
  let gain = 0, loss = 0;
  for (let i = 1; i <= period; i++) {
    const d = values[i] - values[i - 1];
    if (d >= 0) gain += d; else loss -= d;
  }
  let avgGain = gain / period, avgLoss = loss / period;
  out[period] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
  for (let i = period + 1; i < values.length; i++) {
    const d = values[i] - values[i - 1];
    const g = d >= 0 ? d : 0;
    const l = d < 0 ? -d : 0;
    avgGain = (avgGain * (period - 1) + g) / period;
    avgLoss = (avgLoss * (period - 1) + l) / period;
    out[i] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
  }
  return out;
}

// MACD:macd = ema(fast) − ema(slow);signal = macd 的 ema(signal);hist = macd − signal。
export function macd(
  values: number[], fast = 12, slow = 26, signalPeriod = 9
): { macd: (number | null)[]; signal: (number | null)[]; hist: (number | null)[] } {
  const emaFast = ema(values, fast);
  const emaSlow = ema(values, slow);
  const macdLine: (number | null)[] = values.map((_, i) =>
    emaFast[i] != null && emaSlow[i] != null ? emaFast[i]! - emaSlow[i]! : null
  );
  // 對「已定義的 macd 段」算 EMA,再映射回原索引。
  const defined: number[] = macdLine.filter((v): v is number => v != null);
  const sigDefined = ema(defined, signalPeriod);
  const signal: (number | null)[] = new Array(values.length).fill(null);
  let j = 0;
  for (let i = 0; i < values.length; i++) {
    if (macdLine[i] != null) { signal[i] = sigDefined[j]; j++; }
  }
  const hist: (number | null)[] = values.map((_, i) =>
    macdLine[i] != null && signal[i] != null ? (macdLine[i] as number) - (signal[i] as number) : null
  );
  return { macd: macdLine, signal, hist };
}

// 布林通道:mid = SMA(period);upper/lower = mid ± mult × 母體標準差。
export function bollinger(
  values: number[], period = 20, mult = 2
): { upper: (number | null)[]; mid: (number | null)[]; lower: (number | null)[] } {
  const mid = sma(values, period);
  const upper: (number | null)[] = new Array(values.length).fill(null);
  const lower: (number | null)[] = new Array(values.length).fill(null);
  for (let i = period - 1; i < values.length; i++) {
    let sum = 0;
    for (let k = i - period + 1; k <= i; k++) sum += values[k];
    const mean = sum / period;
    let varSum = 0;
    for (let k = i - period + 1; k <= i; k++) varSum += (values[k] - mean) ** 2;
    const sd = Math.sqrt(varSum / period);
    upper[i] = mean + mult * sd;
    lower[i] = mean - mult * sd;
  }
  return { upper, mid, lower };
}
