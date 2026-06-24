"use client";

import { createChart, ColorType, LineStyle, type UTCTimestamp, type MouseEventParams } from "lightweight-charts";
import { useEffect, useRef } from "react";
import type { WorkflowRunDTO, WorkflowSignalDTO } from "@/lib/api";
import { useTheme } from "@/app/providers";

export function WorkflowBacktestChart({
  run,
  signals,
  onSelectSignal,
}: {
  run: WorkflowRunDTO;
  signals: WorkflowSignalDTO[];
  onSelectSignal: (s: WorkflowSignalDTO) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  // Fix 2: store callback in a ref so chart effect doesn't re-mount on every parent render
  const onSelectRef = useRef(onSelectSignal);
  useEffect(() => { onSelectRef.current = onSelectSignal; }, [onSelectSignal]);
  const { resolved } = useTheme();

  useEffect(() => {
    if (!containerRef.current) return;
    const css = getComputedStyle(document.documentElement);
    const v = (n: string, f: string) => css.getPropertyValue(n).trim() || f;
    const up = v("--up", "#34D399");
    const down = v("--down", "#F87171");
    const neutral = v("--text-muted", "#8A9099");
    const bg = v("--bg", "#0A0B0D");
    const gridColor = v("--border", "#1f1f1f");
    const textColor = v("--text-muted", "#8A9099");

    const points = run.equity_curve_json ?? [];
    const isUp = points.length >= 2 ? points[points.length - 1].equity >= points[0].equity : true;

    const chart = createChart(containerRef.current, {
      layout: { background: { type: ColorType.Solid, color: bg }, textColor },
      grid: { vertLines: { color: gridColor }, horzLines: { color: gridColor } },
      width: containerRef.current.clientWidth,
      height: 360,
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

    // Build markers for buy/sell signals; hold signals get a small neutral circle.
    const markers = signals
      .filter((s) => s.action !== "hold")
      .map((s) => ({
        time: (new Date(s.timestamp).getTime() / 1000) as UTCTimestamp,
        position: (s.action === "buy" ? "belowBar" : "aboveBar") as "belowBar" | "aboveBar",
        color: s.action === "buy" ? up : down,
        shape: (s.action === "buy" ? "arrowUp" : "arrowDown") as "arrowUp" | "arrowDown",
        text: s.action.toUpperCase(),
      }));

    // Add hold markers as neutral dots
    const holdMarkers = signals
      .filter((s) => s.action === "hold")
      .map((s) => ({
        time: (new Date(s.timestamp).getTime() / 1000) as UTCTimestamp,
        position: "inBar" as const,
        color: neutral,
        shape: "circle" as const,
        text: "",
      }));

    const allMarkers = [...markers, ...holdMarkers].sort((a, b) =>
      (a.time as number) - (b.time as number),
    );

    series.setMarkers(allMarkers);
    chart.timeScale().fitContent();

    // Fix 1: derive bar interval from equity curve; only fire when click is within ~1.5 bars of a marker.
    // This prevents opening the drawer when clicking empty chart space far from any signal.
    const barIntervalMs = points.length >= 2
      ? Math.abs(
          new Date(points[1].timestamp).getTime() - new Date(points[0].timestamp).getTime()
        )
      : 0;
    // Use 1.5× the bar interval as the proximity threshold
    const proximityThresholdMs = barIntervalMs * 1.5;

    const clickHandler = (param: MouseEventParams) => {
      if (param.time == null) return;
      if (signals.length === 0) return;
      // Need at least a bar interval to define "near"; if curve has <2 points, skip
      if (barIntervalMs === 0) return;
      const clickMs = (param.time as UTCTimestamp) * 1000;
      const hit = signals.reduce<WorkflowSignalDTO | null>((best, s) => {
        const d = Math.abs(new Date(s.timestamp).getTime() - clickMs);
        if (!best) return s;
        return Math.abs(new Date(best.timestamp).getTime() - clickMs) <= d ? best : s;
      }, null);
      if (!hit) return;
      const hitMs = new Date(hit.timestamp).getTime();
      // Only select when click is within the proximity threshold of the nearest signal
      if (Math.abs(hitMs - clickMs) <= proximityThresholdMs) {
        onSelectRef.current(hit);
      }
    };

    chart.subscribeClick(clickHandler);

    const onResize = () => chart.applyOptions({ width: containerRef.current!.clientWidth });
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.unsubscribeClick(clickHandler as Parameters<typeof chart.unsubscribeClick>[0]);
      chart.remove();
    };
  }, [run, signals, resolved]);

  return <div ref={containerRef} className="w-full" />;
}
