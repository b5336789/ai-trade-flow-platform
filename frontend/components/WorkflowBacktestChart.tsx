"use client";

import { createChart, ColorType, LineStyle, type UTCTimestamp, type MouseEventParams } from "lightweight-charts";
import { useEffect, useRef } from "react";
import type { WorkflowRunDTO, WorkflowSignalDTO } from "@/lib/api";

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

    const clickHandler = (param: MouseEventParams) => {
      if (param.time == null) return;
      const clickMs = (param.time as UTCTimestamp) * 1000;
      const hit = signals.reduce<WorkflowSignalDTO | null>((best, s) => {
        const d = Math.abs(new Date(s.timestamp).getTime() - clickMs);
        if (!best) return s;
        return Math.abs(new Date(best.timestamp).getTime() - clickMs) <= d ? best : s;
      }, null);
      if (hit) onSelectSignal(hit);
    };

    chart.subscribeClick(clickHandler);

    const onResize = () => chart.applyOptions({ width: containerRef.current!.clientWidth });
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.unsubscribeClick(clickHandler as Parameters<typeof chart.unsubscribeClick>[0]);
      chart.remove();
    };
  }, [run, signals, onSelectSignal]);

  return <div ref={containerRef} className="w-full" />;
}
