"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

function money(n: number) {
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export function PortfolioPanel() {
  const config = useQuery({ queryKey: ["config"], queryFn: api.config, retry: false });
  const portfolio = useQuery({
    queryKey: ["portfolio"],
    queryFn: () => api.portfolio("crypto"),
    refetchInterval: 5000,
    retry: false,
  });
  const orders = useQuery({ queryKey: ["orders"], queryFn: api.orders, refetchInterval: 5000, retry: false });

  return (
    <section className="card">
      <div className="mb-3 flex items-center gap-2">
        <h2 className="panel-title">💼 投資組合 Portfolio</h2>
        {config.data && (
          <span
            className={`badge border ${
              config.data.trading_mode === "live"
                ? "border-red-500/40 bg-red-500/15 text-red-300"
                : "border-emerald-500/40 bg-emerald-500/15 text-emerald-300"
            }`}
          >
            {config.data.trading_mode.toUpperCase()}
          </span>
        )}
      </div>

      {portfolio.isError ? (
        <p className="text-sm text-red-400">投資組合載入失敗:{(portfolio.error as Error).message}</p>
      ) : portfolio.data ? (
        <>
          <div className="mb-3 grid grid-cols-3 gap-2 text-sm">
            <Stat label="現金 Cash" value={money(portfolio.data.cash)} />
            <Stat label="部位 Positions" value={money(portfolio.data.positions_value)} />
            <Stat label="總值 Equity" value={money(portfolio.data.equity)} accent />
          </div>
          {portfolio.data.positions.length > 0 ? (
            <table className="w-full text-left text-xs">
              <thead className="text-neutral-500">
                <tr>
                  <th className="py-1 font-medium">Symbol</th>
                  <th className="font-medium">Qty</th>
                  <th className="font-medium">Avg</th>
                  <th className="font-medium">Price</th>
                  <th className="text-right font-medium">uPnL</th>
                </tr>
              </thead>
              <tbody>
                {portfolio.data.positions.map((p) => (
                  <tr key={p.symbol} className="border-t border-white/5 transition-colors hover:bg-white/5">
                    <td className="py-1.5 font-medium">{p.symbol}</td>
                    <td>{p.quantity}</td>
                    <td>{money(p.avg_price)}</td>
                    <td>{money(p.current_price)}</td>
                    <td className={`text-right font-medium ${p.unrealized_pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                      {p.unrealized_pnl >= 0 ? "+" : ""}
                      {money(p.unrealized_pnl)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-xs text-neutral-500">尚無持倉部位。</p>
          )}
        </>
      ) : (
        <div className="mb-3 grid grid-cols-3 gap-2">
          <div className="skeleton h-12" />
          <div className="skeleton h-12" />
          <div className="skeleton h-12" />
        </div>
      )}

      <h3 className="mb-1.5 mt-4 text-xs font-semibold uppercase tracking-wide text-neutral-500">
        近期訂單 Recent orders
      </h3>
      {orders.data && orders.data.length > 0 ? (
        <ul className="space-y-1 text-xs">
          {orders.data.slice(0, 8).map((o) => (
            <li key={o.id} className="flex items-center justify-between border-b border-white/5 py-1">
              <span className="flex items-center gap-2">
                <span
                  className={`badge ${
                    o.side === "buy" ? "bg-emerald-500/15 text-emerald-300" : "bg-red-500/15 text-red-300"
                  }`}
                >
                  {o.side.toUpperCase()}
                </span>
                <span className="text-neutral-300">
                  {o.quantity} {o.symbol}
                </span>
              </span>
              <span className="text-neutral-400">@ {money(o.price)}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-neutral-500">尚無訂單。</p>
      )}
    </section>
  );
}

function Stat({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className={`rounded-lg border p-2 ${accent ? "border-brand-500/30 bg-brand-500/10" : "border-white/5 bg-neutral-800/50"}`}>
      <div className="text-[11px] text-neutral-500">{label}</div>
      <div className={`mt-0.5 font-semibold tabular ${accent ? "text-brand-200" : "text-neutral-100"}`}>{value}</div>
    </div>
  );
}
