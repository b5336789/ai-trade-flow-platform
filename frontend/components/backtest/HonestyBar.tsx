import type { BacktestAssumptions } from "@/lib/api";

/** Surfaces the silent assumptions behind a backtest result. Warnings use --warning (never price tokens). */
export function HonestyBar({ assumptions }: { assumptions: BacktestAssumptions | null }) {
  if (!assumptions) return null;
  const a = assumptions;
  return (
    <div className="rounded-md border border-border bg-surface-2 px-3 py-2 text-[11px] text-muted">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
        <span>滑價 <span className="num text-text">{a.slippage_bps.toFixed(1)} bps</span></span>
        <span>成本 <span className="num text-text">{a.cost_taker_bps.toFixed(1)} bps</span></span>
        <span>K 線 <span className="num text-text">{a.bars}</span></span>
        <span>交易 <span className="num text-text">{a.num_trades}</span></span>
        <span>年化基準 <span className="text-text">{a.annualization_basis}</span></span>
      </div>
      {a.warnings.length > 0 && (
        <ul className="mt-1 space-y-0.5">
          {a.warnings.map((w) => (
            <li key={w} className="text-warning">⚠ {w}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
