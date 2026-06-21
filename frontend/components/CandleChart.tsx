"use client";
import type { Candle } from "@/lib/api";
import { PriceChart } from "@/components/PriceChart";

// 薄包裝:歷史引用沿用此 API;實作改委派給 PriceChart(靜態模式)。
// 保留 volume=false 以貼近舊版單純 K 線外觀。
export function CandleChart({ candles, height = 320 }: { candles: Candle[]; height?: number }) {
  return <PriceChart candles={candles} height={height} volume={false} />;
}
