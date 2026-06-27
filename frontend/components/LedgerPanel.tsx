"use client";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

function money(n: number) {
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export function LedgerPanel() {
  const ledger = useQuery({ queryKey: ["realized-ledger"], queryFn: () => api.realizedLedger(), retry: false });

  if (ledger.isError) {
    return <p className="text-sm text-error">損益帳本載入失敗：{(ledger.error as Error).message}</p>;
  }
  if (!ledger.data) return <p className="text-sm text-faint">載入中…</p>;
  const r = ledger.data;

  return (
    <section className="space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="font-display text-xl font-semibold">損益帳本（已實現）</h1>
        <span className="text-xs text-faint">{r.count} 筆處分 · 計價 {r.base_currency}</span>
        <button
          onClick={() => api.downloadLedgerCsv()}
          className="ml-auto rounded-md border border-border bg-surface-2 px-3 py-1.5 text-[13px] text-muted hover:text-text"
        >
          匯出 CSV（報稅）
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Kpi label={`已實現淨損益（${r.base_currency}）`} value={r.total_realized_net_base} colored />
        <Kpi label={`毛損益（${r.base_currency}）`} value={r.total_gross_pnl_base} colored />
        <Kpi label="總手續費（native sum）" value={r.total_fee} />
        <Kpi label="總證交稅（native sum）" value={r.total_tax} />
      </div>

      {r.disposals.length === 0 ? (
        <p className="text-sm text-faint">尚無已實現損益 — 平倉後會在此列出。</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="text-faint">
              <tr>
                <th className="py-1">平倉時間</th><th>市場</th><th>代號</th><th>數量</th>
                <th>賣出金額</th><th>成本</th><th>費用</th><th>稅</th><th>淨損益</th>
              </tr>
            </thead>
            <tbody>
              {r.disposals.map((d) => (
                <tr key={d.id} className="border-t border-border">
                  <td className="py-1">{new Date(d.closed_at).toLocaleString()}</td>
                  <td>{d.market}</td>
                  <td>{d.symbol}</td>
                  <td className="num">{d.quantity}</td>
                  <td className="num">{money(d.proceeds)}</td>
                  <td className="num">{money(d.cost_basis)}</td>
                  <td className="num">{money(d.fee)}</td>
                  <td className="num">{money(d.tax)}</td>
                  <td className={`num ${d.realized_net >= 0 ? "text-up" : "text-down"}`}>{money(d.realized_net)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function Kpi({ label, value, colored }: { label: string; value: number; colored?: boolean }) {
  const cls = colored ? (value >= 0 ? "text-up" : "text-down") : "text-text";
  return (
    <div className="rounded-md border border-border bg-surface-1 p-3">
      <div className="text-xs text-faint">{label}</div>
      <div className={`num text-lg font-semibold ${cls}`}>{money(value)}</div>
    </div>
  );
}
