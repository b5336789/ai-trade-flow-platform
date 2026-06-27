"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useActiveMarket } from "@/lib/market-context";
import { L } from "@/lib/labels";

function money(n: number) {
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export function PortfolioPanel() {
  const qc = useQueryClient();
  const { market } = useActiveMarket();
  const config = useQuery({ queryKey: ["config"], queryFn: api.config, retry: false });
  const portfolio = useQuery({
    queryKey: ["portfolio", market],
    queryFn: () => api.portfolio(market),
    refetchInterval: 5000,
    retry: false,
  });
  const orders = useQuery({ queryKey: ["orders"], queryFn: api.orders, refetchInterval: 5000, retry: false });
  const summary = useQuery({ queryKey: ["portfolio-summary"], queryFn: api.portfolioSummary, refetchInterval: 5000, retry: false });

  return (
    <section className="rounded-lg border border-border bg-surface-1 p-4">
      <div className="mb-3 flex items-center gap-2">
        <h2 className="font-display text-lg font-semibold">{L.portfolio.title}</h2>
        {config.data && (
          <span
            className={`rounded-sm px-2 py-0.5 text-xs font-medium ${
              config.data.trading_mode === "live" ? "bg-live/15 text-live" : "bg-surface-3 text-muted"
            }`}
          >
            {config.data.trading_mode.toUpperCase()}
          </span>
        )}
        <button
          onClick={async () => {
            if (!confirm("重置紙上交易帳戶(現金與部位)?")) return;
            await api.resetPaper(market);
            qc.invalidateQueries({ queryKey: ["portfolio", market] });
          }}
          className="ml-auto rounded-md bg-surface-2 px-2 py-1 text-xs hover:bg-surface-3"
        >
          {L.portfolio.resetPaper}
        </button>
      </div>

      {summary.data && (
        <div className="mb-3 rounded-md border border-border bg-surface-2 p-3">
          <div className="flex items-baseline justify-between">
            <span className="text-xs text-faint">跨市場總權益（{summary.data.base_currency}）</span>
            <span className="num text-lg font-semibold">{money(summary.data.total_equity_base)}</span>
          </div>
          <div className="mt-2 space-y-1">
            {summary.data.markets.filter((m) => m.available).map((m) => {
              const w = summary.data.total_equity_base > 0 ? (m.equity_base / summary.data.total_equity_base) * 100 : 0;
              return (
                <div key={m.market} className="flex items-center gap-2 text-xs">
                  <span className="w-20 text-muted">{m.market}</span>
                  <div className="h-1.5 flex-1 overflow-hidden rounded-sm bg-surface-3">
                    <div className="h-full bg-text/40" style={{ width: `${w}%` }} />
                  </div>
                  <span className="num w-28 text-right text-text">{money(m.equity_base)}</span>
                  <span className="num w-12 text-right text-faint">{w.toFixed(0)}%</span>
                </div>
              );
            })}
            {summary.data.markets.filter((m) => !m.available).length > 0 && (
              <p className="text-[11px] text-faint">
                未連線市場：{summary.data.markets.filter((m) => !m.available).map((m) => m.market).join("、")}（無資料 / 尚未實作）
              </p>
            )}
          </div>
        </div>
      )}

      {portfolio.isError ? (
        <p className="text-sm text-error">{L.portfolio.error}：{(portfolio.error as Error).message}</p>
      ) : portfolio.data ? (
        <>
          <div className="mb-3 grid grid-cols-3 gap-2 text-sm">
            <Stat label={L.portfolio.cash} value={money(portfolio.data.cash)} />
            <Stat label={L.portfolio.positions} value={money(portfolio.data.positions_value)} />
            <Stat label={L.portfolio.equity} value={money(portfolio.data.equity)} />
          </div>
          {portfolio.data.positions.length > 0 && (
            <table className="w-full text-left text-xs">
              <thead className="text-faint">
                <tr>
                  <th className="py-1">{L.portfolio.colSymbol}</th>
                  <th>{L.portfolio.colQty}</th>
                  <th>{L.portfolio.colAvg}</th>
                  <th>{L.portfolio.colPrice}</th>
                  <th>{L.portfolio.colUpnl}</th>
                </tr>
              </thead>
              <tbody>
                {portfolio.data.positions.map((p) => (
                  <tr key={p.symbol} className="border-t border-border">
                    <td className="py-1">{p.symbol}</td>
                    <td className="num">{p.quantity}</td>
                    <td className="num">{money(p.avg_price)}</td>
                    <td className="num">
                      {money(p.current_price)}
                      {p.price_source === "avg_fallback" && <span className="ml-1 text-warning" title="現價不可得，退回成本價">⚠</span>}
                    </td>
                    <td className={`num ${p.unrealized_pnl >= 0 ? "text-up" : "text-down"}`}>
                      {money(p.unrealized_pnl)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      ) : (
        <p className="text-sm text-faint">{L.portfolio.loading}</p>
      )}

      <h3 className="mb-1 mt-4 text-sm font-semibold text-muted">{L.portfolio.recentOrders}</h3>
      {orders.data && orders.data.length > 0 ? (
        <ul className="space-y-1 text-xs">
          {orders.data.slice(0, 8).map((o) => (
            <li key={o.id} className="flex justify-between border-b border-border py-1">
              <span
                className={`rounded-sm px-1.5 py-0.5 text-xs font-medium ${
                  o.side === "buy" ? "bg-up/15 text-up" : "bg-down/15 text-down"
                }`}
              >
                {o.side.toUpperCase()}
              </span>{" "}
              <span>
                <span className="num">{o.quantity}</span> {o.symbol}
              </span>
              <span className="text-muted">
                @ <span className="num">{money(o.price)}</span>
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-faint">{L.portfolio.noOrders}</p>
      )}
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-surface-2 p-2">
      <div className="text-xs text-faint">{label}</div>
      <div className="num font-semibold">{value}</div>
    </div>
  );
}
