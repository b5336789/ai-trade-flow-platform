"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, type Signal } from "@/lib/api";
import { setMarket } from "@/lib/useMarket";
import { CandleChart } from "./CandleChart";
import { Onboarding } from "./Onboarding";

const DEFAULT_SYMBOL: Record<string, string> = {
  crypto: "BTC/USDT",
  tw_stock: "2330",
  us_stock: "AAPL",
};

const TIMEFRAMES = ["15m", "1h", "4h", "1d"];

const SIGNAL_COLOR: Record<string, string> = {
  buy: "text-up",
  sell: "text-down",
  hold: "text-warning",
};

const SIGNAL_LABEL: Record<string, string> = {
  buy: "買進",
  sell: "賣出",
  hold: "觀望",
};

function money(n: number) {
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function price(n: number) {
  // Crypto can run to 5 decimals on small caps; round sensibly by magnitude.
  const dp = n >= 1000 ? 2 : n >= 1 ? 2 : 5;
  return n.toLocaleString(undefined, { minimumFractionDigits: dp, maximumFractionDigits: dp });
}

export function HomeDashboard() {
  const [market, setMarketState] = useState("crypto");
  const [symbol, setSymbol] = useState("BTC/USDT");
  const [timeframe, setTimeframe] = useState("1h");
  const [aiSignal, setAiSignal] = useState<Signal | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);
  const [aiLoading, setAiLoading] = useState(false);

  useEffect(() => {
    setMarket(market);
  }, [market]);

  const config = useQuery({ queryKey: ["config"], queryFn: api.config, retry: false });
  const candles = useQuery({
    queryKey: ["home-ohlcv", symbol, timeframe, market],
    queryFn: () => api.ohlcv(symbol, timeframe, 150, market),
    refetchInterval: 30_000,
    retry: false,
  });
  const portfolio = useQuery({
    queryKey: ["home-portfolio", market],
    queryFn: () => api.portfolio(market),
    refetchInterval: 5_000,
    retry: false,
  });
  const orders = useQuery({
    queryKey: ["home-orders"],
    queryFn: api.orders,
    refetchInterval: 5_000,
    retry: false,
  });

  function switchMarket(next: string) {
    setMarketState(next);
    setSymbol(DEFAULT_SYMBOL[next] ?? "");
    setAiSignal(null);
    setAiError(null);
  }

  async function askAi() {
    setAiLoading(true);
    setAiError(null);
    setAiSignal(null);
    try {
      setAiSignal(await api.aiSignal(symbol, market, timeframe, 150));
    } catch (e) {
      setAiError((e as Error).message);
    } finally {
      setAiLoading(false);
    }
  }

  const rows = candles.data ?? [];
  const last = rows.length ? rows[rows.length - 1].close : null;
  const first = rows.length ? rows[0].open : null;
  const change = last !== null && first !== null ? last - first : null;
  const changePct = change !== null && first ? (change / first) * 100 : null;
  const up = (change ?? 0) >= 0;
  const live = config.data?.trading_mode === "live";
  const positions = portfolio.data?.positions ?? [];
  const uPnl = positions.reduce((s, p) => s + p.unrealized_pnl, 0);

  return (
    <div className="space-y-4">
      <Onboarding />
      {/* Header band — context + controls. The big number lives on the chart, not here. */}
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-faint">交易總覽</p>
          <h1 className="font-display text-2xl font-bold tracking-tight">
            首頁<span className="text-accent">.</span>
          </h1>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select
            aria-label="市場"
            value={market}
            onChange={(e) => switchMarket(e.target.value)}
            className="rounded-md border border-border bg-surface-2 px-2.5 py-1.5 text-[13px]"
          >
            <option value="crypto">加密貨幣</option>
            <option value="tw_stock">台股</option>
            <option value="us_stock">美股</option>
          </select>
          <input
            aria-label="代號"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
            className="w-28 rounded-md border border-border bg-surface-2 px-2.5 py-1.5 text-[13px]"
            placeholder="BTC/USDT"
          />
          <div className="flex overflow-hidden rounded-md border border-border">
            {TIMEFRAMES.map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-2.5 py-1.5 text-[13px] ${
                  tf === timeframe ? "bg-surface-3 text-text" : "bg-surface-2 text-muted hover:text-text"
                }`}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Hero: big chart + KPI rail */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.7fr_1fr]">
        <section className="min-w-0 rounded-lg border border-border bg-surface-1 p-4">
          <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-display text-lg font-semibold">{symbol || "—"}</h2>
                <span className="rounded-sm bg-surface-3 px-1.5 py-0.5 text-[11px] text-muted">
                  {timeframe} · 近 {rows.length} 根
                </span>
              </div>
              <p className="mt-0.5 text-xs text-faint">即時收盤價（紙上行情，每 30 秒更新）</p>
            </div>
            <div className="text-right">
              <div className={`num text-3xl font-semibold leading-none sm:text-4xl ${last === null ? "text-faint" : ""}`}>
                {last === null ? "—" : price(last)}
              </div>
              {change !== null && changePct !== null && (
                <div
                  className={`num mt-1.5 inline-flex items-center gap-1 rounded-sm px-1.5 py-0.5 text-sm font-medium ${
                    up ? "bg-up/10 text-up" : "bg-down/10 text-down"
                  }`}
                >
                  <span>{up ? "▲" : "▼"}</span>
                  <span>{up ? "+" : ""}{price(change)}</span>
                  <span className="opacity-70">
                    ({up ? "+" : ""}
                    {changePct.toFixed(2)}%)
                  </span>
                </div>
              )}
            </div>
          </div>

          {candles.isError ? (
            <div className="flex h-[440px] items-center justify-center rounded-md border border-dashed border-border text-sm text-error">
              行情載入失敗:{(candles.error as Error).message}
            </div>
          ) : rows.length > 0 ? (
            <CandleChart candles={rows} height={440} />
          ) : (
            <div className="flex h-[440px] items-center justify-center text-sm text-faint">載入行情中…</div>
          )}
        </section>

        <div className="min-w-0 space-y-4">
          {/* Portfolio snapshot */}
          <section className="rounded-lg border border-border bg-surface-1 p-4">
            <div className="mb-2 flex items-center justify-between">
              <h2 className="font-display text-sm font-semibold text-muted">投組權益</h2>
              <span
                className={`rounded-sm px-2 py-0.5 text-[11px] font-medium ${
                  live ? "bg-live/15 text-live" : "bg-surface-3 text-muted"
                }`}
              >
                {(config.data?.trading_mode ?? "paper").toUpperCase()}
              </span>
            </div>
            {portfolio.isError ? (
              <p className="text-sm text-error">投組載入失敗:{(portfolio.error as Error).message}</p>
            ) : portfolio.data ? (
              <>
                <div className="num text-3xl font-semibold leading-none">{money(portfolio.data.equity)}</div>
                <div className="mt-3 grid grid-cols-3 gap-2">
                  <Kpi label="現金" value={money(portfolio.data.cash)} />
                  <Kpi label="部位市值" value={money(portfolio.data.positions_value)} />
                  <Kpi
                    label="未實現損益"
                    value={`${uPnl >= 0 ? "+" : ""}${money(uPnl)}`}
                    tone={uPnl >= 0 ? "up" : "down"}
                  />
                </div>
              </>
            ) : (
              <p className="text-sm text-faint">載入中…</p>
            )}
          </section>

          {/* AI signal — cyan marks the AI/automation identity */}
          <section className="rounded-lg border border-accent/40 bg-surface-1 p-4">
            <div className="mb-2 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-sm bg-accent" />
                <h2 className="font-display text-sm font-semibold">AI 訊號</h2>
              </div>
              <button
                onClick={askAi}
                disabled={aiLoading || !symbol}
                className="rounded-md bg-accent px-3 py-1 text-[13px] font-medium text-bg hover:brightness-110 disabled:opacity-50"
              >
                {aiLoading ? "分析中…" : "詢問 AI"}
              </button>
            </div>
            {aiError ? (
              <p className="text-sm text-error">AI 失敗:{aiError}</p>
            ) : aiSignal ? (
              <div>
                <div className="flex items-baseline gap-2">
                  <span className={`font-display text-2xl font-bold ${SIGNAL_COLOR[aiSignal.action]}`}>
                    {SIGNAL_LABEL[aiSignal.action] ?? aiSignal.action}
                  </span>
                  <span className="num text-sm text-muted">
                    信心 {(aiSignal.confidence * 100).toFixed(0)}% · {aiSignal.source}
                  </span>
                </div>
                <p className="mt-1.5 text-[13px] leading-relaxed text-text">{aiSignal.reason}</p>
              </div>
            ) : (
              <p className="text-[13px] text-faint">
                對 {symbol || "選定標的"} 詢問 AI，取得買 / 賣 / 觀望建議與理由。
              </p>
            )}
          </section>

          {/* Quick actions */}
          <section className="rounded-lg border border-border bg-surface-1 p-2">
            {QUICK_LINKS.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className="flex items-center justify-between rounded-md px-2.5 py-2 text-[13px] text-muted hover:bg-surface-2 hover:text-text"
              >
                <span>
                  {l.ai && <span className="mr-2 inline-block h-1.5 w-1.5 rounded-sm bg-accent align-middle" />}
                  {l.label}
                </span>
                <span className="text-faint">↗</span>
              </Link>
            ))}
          </section>
        </div>
      </div>

      {/* Bottom: positions + recent orders */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <section className="min-w-0 rounded-lg border border-border bg-surface-1 p-4">
          <h2 className="mb-2 font-display text-sm font-semibold text-muted">持有部位</h2>
          {positions.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="text-faint">
                  <tr>
                    <th className="py-1 pr-2">代號</th>
                    <th className="pr-2 text-right">數量</th>
                    <th className="pr-2 text-right">均價</th>
                    <th className="pr-2 text-right">現價</th>
                    <th className="text-right">未實現</th>
                  </tr>
                </thead>
                <tbody>
                  {positions.map((p) => (
                    <tr key={p.symbol} className="border-t border-border">
                      <td className="py-1.5 pr-2">{p.symbol}</td>
                      <td className="num pr-2 text-right">{p.quantity}</td>
                      <td className="num pr-2 text-right">{money(p.avg_price)}</td>
                      <td className="num pr-2 text-right">{money(p.current_price)}</td>
                      <td className={`num text-right ${p.unrealized_pnl >= 0 ? "text-up" : "text-down"}`}>
                        {p.unrealized_pnl >= 0 ? "+" : ""}
                        {money(p.unrealized_pnl)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-xs text-faint">尚無部位。到交易室執行策略後會顯示在這裡。</p>
          )}
        </section>

        <section className="min-w-0 rounded-lg border border-border bg-surface-1 p-4">
          <h2 className="mb-2 font-display text-sm font-semibold text-muted">近期訂單</h2>
          {orders.data && orders.data.length > 0 ? (
            <ul className="divide-y divide-border text-xs">
              {orders.data.slice(0, 8).map((o) => (
                <li key={o.id} className="flex items-center justify-between gap-2 py-1.5">
                  <span
                    className={`rounded-sm px-1.5 py-0.5 font-medium ${
                      o.side === "buy" ? "bg-up/15 text-up" : "bg-down/15 text-down"
                    }`}
                  >
                    {o.side === "buy" ? "買" : "賣"}
                  </span>
                  <span className="flex-1 truncate">
                    <span className="num">{o.quantity}</span> {o.symbol}
                  </span>
                  <span className="num text-muted">@ {money(o.price)}</span>
                  <span className="text-faint">{o.mode}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-faint">尚無訂單紀錄。</p>
          )}
        </section>
      </div>
    </div>
  );
}

const QUICK_LINKS = [
  { label: "與 AI 設計策略", href: "/strategy-lab", ai: true },
  { label: "模擬回測", href: "/trading-room/backtest", ai: false },
  { label: "工作流", href: "/trading-room/workflow", ai: false },
  { label: "市場行情", href: "/market", ai: false },
];

function Kpi({ label, value, tone }: { label: string; value: string; tone?: "up" | "down" }) {
  return (
    <div className="rounded-md bg-surface-2 p-2">
      <div className="text-[11px] text-faint">{label}</div>
      <div className={`num text-sm font-semibold ${tone === "up" ? "text-up" : tone === "down" ? "text-down" : ""}`}>
        {value}
      </div>
    </div>
  );
}
