"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

/** Sticky top bar: brand mark, live trading-mode pill, and the manual link. */
export function AppHeader() {
  const config = useQuery({ queryKey: ["config"], queryFn: api.config, retry: false });
  const mode = config.data?.trading_mode;
  const live = mode === "live";

  return (
    <header className="sticky top-0 z-30 border-b border-white/5 bg-neutral-950/70 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-3 gap-y-2 px-4 py-3">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="grid h-9 w-9 place-items-center rounded-lg bg-gradient-to-br from-brand-500 to-violet-500 shadow-glow">
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 17l5-5 4 4 8-9" />
              <path d="M21 7v5h-5" />
            </svg>
          </span>
          <span className="leading-tight">
            <span className="block bg-gradient-to-r from-white to-neutral-400 bg-clip-text text-lg font-bold tracking-tight text-transparent">
              AI Trade Flow
            </span>
            <span className="block text-[11px] text-neutral-500">crypto · 台股 · 美股</span>
          </span>
        </Link>

        <div className="ml-auto flex items-center gap-2">
          {mode && (
            <span
              className={`badge border ${
                live
                  ? "animate-pulse-ring border-red-500/40 bg-red-500/15 text-red-300"
                  : "border-emerald-500/40 bg-emerald-500/15 text-emerald-300"
              }`}
              title={live ? "真實下單模式" : "紙上交易(安全)"}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${live ? "bg-red-400" : "bg-emerald-400"}`} />
              {live ? "LIVE" : "PAPER"}
            </span>
          )}
          <Link href="/manual" className="btn btn-primary">
            📖 使用說明書
          </Link>
        </div>
      </div>
    </header>
  );
}
