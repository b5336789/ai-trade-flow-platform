// frontend/components/MetricCard.tsx
"use client";
import { Term } from "@/components/Term";

type Health = "up" | "down" | "neutral";

// 放大的主指標卡;標題用 <Term> 帶白話解讀,值依 health 上色。
export function MetricCard({
  termKey, label, value, sub, health = "neutral",
}: {
  termKey: string;
  label: string;
  value: string;
  sub?: React.ReactNode;
  health?: Health;
}) {
  const color = health === "up" ? "text-up" : health === "down" ? "text-down" : "text-text";
  return (
    <div className="rounded-md border border-border bg-surface-2 p-3">
      <div className="text-xs text-faint">
        <Term k={termKey}>{label}</Term>
      </div>
      <div className={`num text-xl font-semibold ${color}`}>{value}</div>
      {sub != null && <div className="mt-0.5 text-xs">{sub}</div>}
    </div>
  );
}
