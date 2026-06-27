"use client";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useActiveMarket } from "@/lib/market-context";

function money(n: number) {
  return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

function Bar({ label, used, max, unit }: { label: string; used: number; max: number; unit: string }) {
  const pct = max > 0 ? Math.min(100, (Math.max(0, used) / max) * 100) : 0;
  const tone = pct >= 90 ? "bg-error" : pct >= 70 ? "bg-warning" : "bg-surface-3";
  return (
    <div className="rounded-md border border-border bg-surface-1 p-3">
      <div className="mb-1 flex items-baseline justify-between text-xs">
        <span className="text-muted">{label}</span>
        <span className="num text-text">
          {money(used)} / {money(max)} {unit}
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-sm bg-surface-2">
        <div className={`h-full ${tone}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function RiskPage() {
  const { market } = useActiveMarket();
  const qc = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const status = useQuery({
    queryKey: ["risk-status", market],
    queryFn: () => api.riskStatus(market),
    refetchInterval: 5000,
    retry: false,
  });

  if (status.isError) {
    return <p className="text-sm text-error">風控狀態載入失敗：{(status.error as Error).message}</p>;
  }
  if (!status.data) return <p className="text-sm text-faint">載入中…</p>;
  const s = status.data;
  const todayPnl = s.equity_base - s.day_start_equity_base;
  const dailyLossUsed = Math.max(0, s.day_start_equity_base - s.equity_base);

  const toggleKill = async () => {
    const next = !s.kill_switch_runtime;
    if (next && !confirm("確定要啟動 kill switch?所有新進場單將被擋下(平倉仍允許)。")) return;
    setBusy(true);
    setActionError(null);
    try {
      await api.setKillSwitch(next);
      qc.invalidateQueries({ queryKey: ["risk-status"] });
    } catch (e) {
      setActionError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const resume = async () => {
    if (!confirm("確定要解除 halted、恢復進場?")) return;
    setBusy(true);
    setActionError(null);
    try {
      await api.resumeRisk();
      qc.invalidateQueries({ queryKey: ["risk-status"] });
    } catch (e) {
      setActionError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="font-display text-xl font-semibold">風控中心</h1>
        <span className="text-xs text-faint">市場 {market} · 計價 {s.base_currency}</span>
      </div>

      {(s.kill_switch || s.halted) && (
        <div className="rounded-md border border-error/40 bg-error/15 px-4 py-3 text-sm text-error">
          {s.kill_switch && <div>● Kill switch 已啟動 — 所有新進場單被擋下。</div>}
          {s.halted && <div>● 已 halted(單日虧損達上限)— 進場暫停,平倉仍允許。</div>}
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <div className="rounded-md border border-border bg-surface-1 p-3">
          <div className="text-xs text-faint">權益(base)</div>
          <div className="num text-lg font-semibold">{money(s.equity_base)}</div>
        </div>
        <div className="rounded-md border border-border bg-surface-1 p-3">
          <div className="text-xs text-faint">今日損益</div>
          <div className={`num text-lg font-semibold ${todayPnl >= 0 ? "text-up" : "text-down"}`}>
            {todayPnl >= 0 ? "+" : "−"}{money(Math.abs(todayPnl))}
          </div>
        </div>
        <div className="rounded-md border border-border bg-surface-1 p-3">
          <div className="text-xs text-faint">日初權益</div>
          <div className="num text-lg font-semibold">{money(s.day_start_equity_base)}</div>
        </div>
        <div className="rounded-md border border-border bg-surface-1 p-3">
          <div className="text-xs text-faint">狀態</div>
          <div className={`text-lg font-semibold ${s.kill_switch || s.halted ? "text-error" : "text-text"}`}>
            {s.kill_switch ? "KILL" : s.halted ? "HALTED" : "OK"}
          </div>
        </div>
      </div>

      <div className="grid gap-3 lg:grid-cols-3">
        <Bar label="總曝險" used={s.exposure_base} max={s.max_total_exposure_value} unit={s.base_currency} />
        <Bar label="單日虧損" used={dailyLossUsed} max={s.max_daily_loss} unit={s.base_currency} />
        <Bar label="今日下單數" used={s.orders_today} max={s.max_orders_per_day} unit="筆" />
      </div>

      <div className="flex flex-wrap gap-3">
        <button
          onClick={toggleKill}
          disabled={busy}
          className={`rounded-md border px-4 py-2 text-sm font-medium disabled:opacity-50 ${
            s.kill_switch_runtime
              ? "border-border bg-surface-2 text-text hover:bg-surface-3"
              : "border-error/40 bg-error/15 text-error hover:bg-error/25"
          }`}
        >
          {s.kill_switch_runtime ? "解除 Kill Switch" : "啟動 Kill Switch"}
        </button>
        {s.halted && (
          <button
            onClick={resume}
            disabled={busy}
            className="rounded-md border border-warning/40 bg-warning/15 px-4 py-2 text-sm font-medium text-warning hover:bg-warning/25 disabled:opacity-50"
          >
            恢復進場(清除 halted)
          </button>
        )}
        {s.kill_switch_config && (
          <span className="self-center text-xs text-faint">
            註:設定檔層級 kill switch(KILL_SWITCH=true)為開,UI 僅能切換 runtime 旗標。
          </span>
        )}
      </div>
      {actionError && <p className="text-sm text-error">操作失敗：{actionError}</p>}
    </section>
  );
}
