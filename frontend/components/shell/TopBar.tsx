"use client";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ShieldAlert } from "lucide-react";

import { ThemeToggle } from "@/components/shell/ThemeToggle";
import { api, MARKETS } from "@/lib/api";
import { useActiveMarket } from "@/lib/market-context";

function money(n: number) {
  return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

export function TopBar({ open, onMenu }: { open: boolean; onMenu: () => void }) {
  const { market, setMarket } = useActiveMarket();
  const config = useQuery({ queryKey: ["config"], queryFn: api.config, retry: false });
  const risk = useQuery({
    queryKey: ["risk-status", market],
    queryFn: () => api.riskStatus(market),
    refetchInterval: 5000,
    retry: false,
  });

  const live = config.data?.trading_mode === "live";
  const s = risk.data;
  const todayPnl = s ? s.equity_base - s.day_start_equity_base : 0;
  const danger = !!s && (s.kill_switch || s.halted);
  // Risk state couldn't load (e.g. 501 on an unimplemented market). Kill/halt are GLOBAL flags;
  // never show a falsely-reassuring neutral chip when the true state is unknown.
  const unknown = risk.isError;

  return (
    <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-border bg-bg/85 px-4 py-2.5 backdrop-blur">
      <button
        onClick={onMenu}
        aria-label="menu"
        aria-expanded={open}
        className="rounded-md border border-border-strong bg-surface-2 px-2.5 py-1.5 text-text md:hidden"
      >
        ☰
      </button>
      <Link href="/" aria-label="首頁" className="font-display text-sm font-bold md:hidden">
        AI Trade Flow<span className="text-accent">.</span>
      </Link>

      {/* Global market selector — the single driver of data-market */}
      <label className="flex items-center gap-1.5 text-[13px] text-muted">
        <span className="hidden sm:inline text-faint">市場</span>
        <select
          value={market}
          onChange={(e) => setMarket(e.target.value)}
          aria-label="市場"
          className="rounded-md border border-border bg-surface-2 px-2 py-1 text-[13px] text-text"
        >
          {MARKETS.map((m) => (
            <option key={m.value} value={m.value}>{m.label}</option>
          ))}
        </select>
      </label>

      {/* Mode chip — paper neutral; LIVE = --live + pulse (the one deliberate animation) */}
      <span
        className={`rounded-sm px-2 py-0.5 text-xs font-medium ${
          live ? "bg-live/15 text-live animate-pulse" : "bg-surface-3 text-muted"
        }`}
        title={live ? "實際下單模式" : "紙上交易(安全預設)"}
      >
        {(config.data?.trading_mode ?? "paper").toUpperCase()}
      </span>

      {/* Active-market equity + today's PnL (base currency) */}
      {s && (
        <div className="hidden items-baseline gap-2 lg:flex">
          <span className="num text-[13px] text-text">{money(s.equity_base)} {s.base_currency}</span>
          <span className={`num text-xs ${todayPnl >= 0 ? "text-up" : "text-down"}`}>
            {todayPnl >= 0 ? "▴" : "▾"} {money(Math.abs(todayPnl))}
          </span>
        </div>
      )}

      <div className="ml-auto flex items-center gap-3">
        {/* Risk chip — always reachable; turns --error on kill/halt */}
        <Link
          href="/risk"
          title="風控中心"
          className={`flex items-center gap-1 rounded-md border px-2 py-1 text-xs ${
            danger
              ? "border-error/40 bg-error/15 text-error"
              : unknown
                ? "border-warning/40 bg-warning/15 text-warning"
                : "border-border bg-surface-2 text-muted hover:text-text"
          }`}
        >
          <ShieldAlert size={14} />
          <span className="hidden sm:inline">{danger ? (s.kill_switch ? "KILL" : "HALTED") : unknown ? "風控 ?" : "風控"}</span>
        </Link>
        <ThemeToggle />
        <Link
          href="/docs"
          className="rounded-md border border-border bg-surface-2 px-3 py-1.5 text-[13px] text-muted hover:border-accent hover:text-text"
        >
          文件中心 ↗
        </Link>
      </div>
    </header>
  );
}
