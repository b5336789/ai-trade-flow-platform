"use client";

import { createChart, ColorType, LineStyle, type UTCTimestamp } from "lightweight-charts";
import { useEffect, useRef } from "react";
import type { EquityPoint } from "@/lib/api";

export function EquityChart({ points, height = 280 }: { points: EquityPoint[]; height?: number }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || points.length < 2) return;
    const css = getComputedStyle(document.documentElement);
    const v = (n: string, f: string) => css.getPropertyValue(n).trim() || f;
    const up = v("--up", "#34D399");
    const down = v("--down", "#F87171");
    const bg = v("--bg", "#0A0B0D");
    const gridColor = v("--border", "#1f1f1f");
    const textColor = v("--muted", "#8A9099");

    const isUp = points[points.length - 1].equity >= points[0].equity;

    const chart = createChart(containerRef.current, {
      layout: { background: { type: ColorType.Solid, color: bg }, textColor },
      grid: { vertLines: { color: gridColor }, horzLines: { color: gridColor } },
      width: containerRef.current.clientWidth,
      height,
      timeScale: { timeVisible: true },
    });
    const series = chart.addLineSeries({
      color: isUp ? up : down,
      lineWidth: 2,
      lineStyle: LineStyle.Solid,
      priceLineVisible: false,
    });
    series.setData(
      points.map((p) => ({
        time: (new Date(p.timestamp).getTime() / 1000) as UTCTimestamp,
        value: p.equity,
      })),
    );
    chart.timeScale().fitContent();

    const onResize = () => chart.applyOptions({ width: containerRef.current!.clientWidth });
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.remove();
    };
  }, [points, height]);

  if (points.length < 2) return null;
  return <div ref={containerRef} className="w-full" />;
}
