"use client";
import { useQuery } from "@tanstack/react-query";

import { api, type BacktestRunDTO } from "@/lib/api";

/** Past persisted backtests; click to inspect. Replaces transient single-result state. */
export function BacktestRunRegistry({ onSelect }: { onSelect?: (run: BacktestRunDTO) => void }) {
  const { data: runs = [] } = useQuery({
    queryKey: ["backtest-runs"],
    queryFn: () => api.listBacktestRuns(50),
    refetchInterval: 10_000,
  });
  if (runs.length === 0) {
    return <div className="text-[11px] text-faint">尚無回測紀錄 — 執行一次回測後會在此列出。</div>;
  }
  return (
    <div className="flex flex-col gap-1">
      {runs.map((r) => (
        <button
          key={r.id}
          onClick={() => onSelect?.(r)}
          className="flex items-center justify-between rounded-sm border border-border px-2 py-1 text-left text-[11px] hover:bg-surface-2"
        >
          <span className="text-text">{r.strategy} · {r.symbol}</span>
          <span className="num text-muted">
            {r.metrics_json ? `${r.metrics_json.total_return_pct?.toFixed(1)}% · Sharpe ${r.metrics_json.sharpe?.toFixed(2)}` : "—"}
          </span>
        </button>
      ))}
    </div>
  );
}
