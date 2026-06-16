"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

function money(n: number) {
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export function PortfolioPanel() {
  const qc = useQueryClient();
  const config = useQuery({ queryKey: ["config"], queryFn: api.config, retry: false });
  const portfolio = useQuery({
    queryKey: ["portfolio"],
    queryFn: () => api.portfolio("crypto"),
    refetchInterval: 5000,
    retry: false,
  });
  const orders = useQuery({ queryKey: ["orders"], queryFn: api.orders, refetchInterval: 5000, retry: false });

  return (
    <section className="rounded-lg border border-neutral-800 bg-neutral-900/40 p-4">
      <div className="mb-3 flex items-center gap-2">
        <h2 className="text-lg font-semibold">Portfolio</h2>
        {config.data && (
          <span
            className={`rounded px-2 py-0.5 text-xs font-medium ${
              config.data.trading_mode === "live" ? "bg-red-600" : "bg-green-700"
            }`}
          >
            {config.data.trading_mode.toUpperCase()}
          </span>
        )}
        <button
          onClick={async () => {
            if (!confirm("重置紙上交易帳戶(現金與部位)?")) return;
            await api.resetPaper("crypto");
            qc.invalidateQueries({ queryKey: ["portfolio"] });
          }}
          className="ml-auto rounded bg-neutral-800 px-2 py-1 text-xs hover:bg-neutral-700"
        >
          Reset paper
        </button>
      </div>

      {portfolio.isError ? (
        <p className="text-sm text-red-400">Portfolio error: {(portfolio.error as Error).message}</p>
      ) : portfolio.data ? (
        <>
          <div className="mb-3 grid grid-cols-3 gap-2 text-sm">
            <Stat label="Cash" value={money(portfolio.data.cash)} />
            <Stat label="Positions" value={money(portfolio.data.positions_value)} />
            <Stat label="Equity" value={money(portfolio.data.equity)} />
          </div>
          {portfolio.data.positions.length > 0 && (
            <table className="w-full text-left text-xs">
              <thead className="text-neutral-500">
                <tr>
                  <th className="py-1">Symbol</th>
                  <th>Qty</th>
                  <th>Avg</th>
                  <th>Price</th>
                  <th>uPnL</th>
                </tr>
              </thead>
              <tbody>
                {portfolio.data.positions.map((p) => (
                  <tr key={p.symbol} className="border-t border-neutral-800">
                    <td className="py-1">{p.symbol}</td>
                    <td>{p.quantity}</td>
                    <td>{money(p.avg_price)}</td>
                    <td>{money(p.current_price)}</td>
                    <td className={p.unrealized_pnl >= 0 ? "text-green-400" : "text-red-400"}>
                      {money(p.unrealized_pnl)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      ) : (
        <p className="text-sm text-neutral-500">Loading…</p>
      )}

      <h3 className="mb-1 mt-4 text-sm font-semibold text-neutral-400">Recent orders</h3>
      {orders.data && orders.data.length > 0 ? (
        <ul className="space-y-1 text-xs">
          {orders.data.slice(0, 8).map((o) => (
            <li key={o.id} className="flex justify-between border-b border-neutral-800 py-1">
              <span className={o.side === "buy" ? "text-green-400" : "text-red-400"}>
                {o.side.toUpperCase()} {o.quantity} {o.symbol}
              </span>
              <span className="text-neutral-400">@ {money(o.price)}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-neutral-500">No orders yet.</p>
      )}
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded bg-neutral-800/60 p-2">
      <div className="text-xs text-neutral-500">{label}</div>
      <div className="font-semibold">{value}</div>
    </div>
  );
}
