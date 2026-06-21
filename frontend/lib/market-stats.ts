// frontend/lib/market-stats.ts
// 從已抓到的 OHLCV 推導「24h 漲跌/高低/量」。後端 Ticker 只回現價,
// 為了不偽造不存在的後端欄位,這裡誠實地用最後 N 根 K 線估算(window 對應約 24h 的根數)。
import type { Candle } from "./api";

export interface MarketStats {
  last: number;
  first: number;
  changeAbs: number;
  changePct: number;
  high: number;
  low: number;
  volume: number;
}

// window = 對應約 24h 的根數(由 timeframe 推算,呼叫端傳入);取最後 window 根。
export function deriveStats(candles: Candle[], window: number): MarketStats | null {
  if (!candles.length) return null;
  const slice = candles.slice(-Math.max(1, window));
  const first = slice[0].open;
  const last = slice[slice.length - 1].close;
  const high = Math.max(...slice.map((c) => c.high));
  const low = Math.min(...slice.map((c) => c.low));
  const volume = slice.reduce((s, c) => s + c.volume, 0);
  const changeAbs = last - first;
  const changePct = first !== 0 ? (changeAbs / first) * 100 : 0;
  return { last, first, changeAbs, changePct, high, low, volume };
}

// 由 timeframe 估算「約 24h 需要幾根」。未知週期退回整段。
export function barsPer24h(timeframe: string): number {
  const map: Record<string, number> = {
    "1m": 1440, "5m": 288, "15m": 96, "30m": 48,
    "1h": 24, "4h": 6, "1d": 1,
  };
  return map[timeframe] ?? 24;
}
