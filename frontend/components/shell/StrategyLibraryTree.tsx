"use client";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Suspense } from "react";
import { api } from "@/lib/api";
import { L } from "@/lib/labels";

function StrategyLibraryTreeInner({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const params = useSearchParams();
  const activeStrategy = params.get("strategy");
  const q = useQuery({
    queryKey: ["nav-saved-strategies"],
    queryFn: api.listSavedStrategies,
    retry: false,
    staleTime: 60_000,
  });

  if (q.isError) {
    return <p className="px-3 py-1 text-[12px] text-faint">{L.nav.libraryError}</p>;
  }
  const items = q.data ?? [];
  if (items.length === 0) {
    return <p className="px-3 py-1 text-[12px] text-faint">{L.nav.libraryEmpty}</p>;
  }

  return (
    <div className="ml-3 border-l border-border pl-1">
      {items.map((s) => {
        const href = `/trading-room/backtest?strategy=saved:${s.id}`;
        const active =
          pathname.startsWith("/trading-room/backtest") && activeStrategy === `saved:${s.id}`;
        return (
          <Link
            key={s.id}
            href={href}
            onClick={onNavigate}
            title={s.description || s.name}
            className={`nav-label flex items-center gap-2 truncate rounded-md border-l-2 px-3 py-1.5 text-[12px] ${
              active
                ? "border-accent bg-accent-dim text-text"
                : "border-transparent text-muted hover:bg-surface-2"
            }`}
          >
            <span className="truncate">{s.name}</span>
          </Link>
        );
      })}
    </div>
  );
}

export function StrategyLibraryTree({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <Suspense fallback={null}>
      <StrategyLibraryTreeInner onNavigate={onNavigate} />
    </Suspense>
  );
}
