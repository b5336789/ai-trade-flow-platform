"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, MARKETS, type BacktestResult } from "@/lib/api";
import { L } from "@/lib/labels";

interface StrategyLibraryProps {
  onLoad: (id: number) => void;
}

function pct(n: number) {
  return `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
}

export function StrategyLibrary({ onLoad }: StrategyLibraryProps) {
  const qc = useQueryClient();
  const router = useRouter();
  const [symbol, setSymbol] = useState("BTC/USDT");
  const [market, setMarket] = useState("crypto");
  const [results, setResults] = useState<Record<number, BacktestResult>>({});

  const list = useQuery({ queryKey: ["savedStrategies"], queryFn: api.listSavedStrategies, retry: false });

  const backtest = useMutation({
    mutationFn: (id: number) =>
      api.backtestSavedStrategy(id, { symbol, market, timeframe: "1h", limit: 300 }),
    onSuccess: (data, id) => setResults((prev) => ({ ...prev, [id]: data })),
  });

  const remove = useMutation({
    mutationFn: (id: number) => api.deleteStrategy(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["savedStrategies"] }),
  });

  return (
    <section className="rounded-lg border border-border bg-surface-1 p-4">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <h2 className="font-display text-[15px] font-semibold">策略庫</h2>
        <span className="text-[12px] text-faint">{list.data?.length ?? 0} 支策略</span>
        <div className="ml-auto flex items-center gap-2 text-[12px]">
          <span className="text-faint">回測標的</span>
          <input
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="num w-28 rounded-sm border border-border bg-surface-2 px-2 py-1 outline-none focus:border-accent"
          />
          <select
            value={market}
            onChange={(e) => setMarket(e.target.value)}
            className="rounded-sm border border-border bg-surface-2 px-2 py-1 outline-none focus:border-accent"
          >
            {MARKETS.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {list.isError && (
        <p className="text-[13px] text-error">⚠ 無法載入策略庫:{(list.error as Error).message}</p>
      )}
      {list.data && list.data.length === 0 && (
        <p className="text-[13px] text-faint">尚無已儲存的策略。在上方用 AI 設計一支並存入策略庫。</p>
      )}

      <div className="grid grid-cols-[repeat(auto-fill,minmax(210px,1fr))] gap-3">
        {list.data?.map((s) => {
          const r = results[s.id];
          const busy = backtest.isPending && backtest.variables === s.id;
          return (
            <div key={s.id} className="flex flex-col rounded-md border border-border bg-surface-2 p-3">
              <div className="flex items-start gap-2">
                <h3 className="flex-1 font-display text-[14px] font-semibold leading-tight">{s.name}</h3>
                <span
                  className={`rounded-sm px-1.5 py-0.5 text-[10px] font-medium ${
                    s.source === "ai" ? "bg-accent-dim text-accent" : "bg-surface-3 text-muted"
                  }`}
                >
                  {s.source === "ai" ? "AI" : s.source}
                </span>
              </div>
              <p className="mt-1 line-clamp-2 min-h-[2.4em] text-[12px] text-muted">
                {s.description || "—"}
              </p>
              <p className="mt-1 text-[11px] text-faint">{s.num_params} 個可調參數</p>

              {r && (
                <div className="mt-2 grid grid-cols-2 gap-1 rounded-sm bg-bg p-2 text-[11px]">
                  <Metric label="報酬" value={pct(r.total_return_pct)} positive={r.total_return_pct >= 0} />
                  <Metric label="B&H" value={pct(r.buy_hold_return_pct)} positive={r.buy_hold_return_pct >= 0} />
                  <Metric label="回撤" value={pct(-r.max_drawdown_pct)} positive={false} />
                  <Metric label="勝率" value={`${r.win_rate.toFixed(0)}%`} muted />
                </div>
              )}
              {backtest.isError && backtest.variables === s.id && (
                <p className="mt-2 text-[11px] text-error">⚠ {(backtest.error as Error).message}</p>
              )}

              <button
                onClick={() =>
                  router.push(
                    `/trading-room/backtest?strategy=saved:${s.id}` +
                      `&symbol=${encodeURIComponent(symbol)}&market=${encodeURIComponent(market)}`,
                  )
                }
                className="mt-3 w-full rounded-sm border border-accent/40 bg-accent-dim px-2 py-1 text-[12px] text-accent hover:border-accent"
              >
                {L.linking.sendToBacktest} →
              </button>
              <div className="mt-3 flex gap-1.5 text-[12px]">
                <button
                  onClick={() => onLoad(s.id)}
                  className="flex-1 rounded-sm border border-border bg-surface-3 px-2 py-1 hover:border-accent"
                >
                  載入
                </button>
                <button
                  onClick={() => backtest.mutate(s.id)}
                  disabled={busy}
                  className="flex-1 rounded-sm border border-accent/40 bg-accent-dim px-2 py-1 text-accent hover:border-accent disabled:opacity-40"
                >
                  {busy ? "…" : "回測"}
                </button>
                <button
                  onClick={() => {
                    if (confirm(`刪除策略「${s.name}」?`)) remove.mutate(s.id);
                  }}
                  className="rounded-sm border border-border px-2 py-1 text-down hover:border-down"
                >
                  刪
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function Metric({
  label,
  value,
  positive,
  muted,
}: {
  label: string;
  value: string;
  positive?: boolean;
  muted?: boolean;
}) {
  const color = muted ? "text-text" : positive ? "text-up" : "text-down";
  return (
    <div className="flex items-center justify-between">
      <span className="text-faint">{label}</span>
      <span className={`num ${color}`}>{value}</span>
    </div>
  );
}
