// frontend/components/Term.tsx
"use client";
import { GLOSSARY } from "@/lib/labels";

// 顯示一個術語標籤;若有對應白話解讀,附一個可 hover/focus 的「?」氣泡。
// 純 CSS group-hover,不引入 tooltip 套件(YAGNI)。
export function Term({ k, children }: { k: string; children: React.ReactNode }) {
  const def = GLOSSARY[k];
  if (!def) return <>{children}</>;
  return (
    <span className="group relative inline-flex items-center gap-1">
      <span>{children}</span>
      <button
        type="button"
        aria-label={`${typeof children === "string" ? children : k} 說明`}
        className="grid h-3.5 w-3.5 place-items-center rounded-full border border-border-strong text-[9px] leading-none text-muted hover:text-text focus:outline-none focus-visible:ring-1 focus-visible:ring-accent"
      >
        ?
      </button>
      <span
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-0 z-30 mb-1 hidden w-56 rounded-md border border-border bg-surface-3 p-2 text-[11px] font-normal leading-snug text-text shadow-lg group-hover:block group-focus-within:block"
      >
        {def}
      </span>
    </span>
  );
}
