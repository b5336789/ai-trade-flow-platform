"use client";

import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { api, type NodeType } from "@/lib/api";
import { CATEGORY_COLOR, CATEGORY_LABEL, NODE_CATALOG, type NodeCategory } from "./nodeCatalog";

const CATEGORY_ORDER: NodeCategory[] = ["data", "strategy", "logic", "order", "output"];

type ChipPayload = { type: NodeType } | { type: "strategy"; savedStrategyId: number; name: string };

function onChipDragStart(e: React.DragEvent, payload: ChipPayload) {
  e.dataTransfer.setData("application/reactflow", JSON.stringify(payload));
  e.dataTransfer.effectAllowed = "move";
}

export function Palette({ compact = false }: { compact?: boolean }) {
  const [q, setQ] = useState("");
  const [openCat, setOpenCat] = useState<NodeCategory | null>(null);
  const saved = useQuery({ queryKey: ["savedStrategies"], queryFn: api.listSavedStrategies, retry: false });

  const byCategory = useMemo(() => {
    const groups: Record<NodeCategory, NodeType[]> = { data: [], strategy: [], logic: [], order: [], output: [] };
    (Object.keys(NODE_CATALOG) as NodeType[]).forEach((t) => groups[NODE_CATALOG[t].category].push(t));
    return groups;
  }, []);

  const match = (label: string) => label.toLowerCase().includes(q.toLowerCase());

  if (compact) {
    return (
      <aside className="relative flex h-full w-12 shrink-0 flex-col items-center gap-2 overflow-y-auto border-r border-border bg-surface-1 py-2">
        {CATEGORY_ORDER.map((cat) => {
          const items = byCategory[cat].filter((t) => match(NODE_CATALOG[t].title));
          const savedItems = cat === "strategy" ? (saved.data ?? []).filter((s) => match(s.name)) : [];
          if (items.length === 0 && savedItems.length === 0) return null;
          const isOpen = openCat === cat;
          return (
            <div key={cat} className="relative">
              <button
                title={CATEGORY_LABEL[cat]}
                onClick={() => setOpenCat(isOpen ? null : cat)}
                className="flex h-8 w-8 items-center justify-center rounded-md border border-border bg-surface-2 hover:bg-surface-3"
                style={{ borderLeft: `3px solid ${CATEGORY_COLOR[cat]}` }}
              >
                <span className="inline-block h-3 w-3 rounded-full" style={{ background: CATEGORY_COLOR[cat] }} />
              </button>
              {isOpen && (
                <div className="absolute left-10 top-0 z-20 flex min-w-[160px] flex-col gap-1 rounded-md border border-border bg-surface-1 p-2 shadow-lg">
                  <div className="mb-1 text-[10px] uppercase tracking-wide text-faint">{CATEGORY_LABEL[cat]}</div>
                  {items.map((t) => (
                    <button
                      key={t}
                      draggable
                      onDragStart={(e) => { onChipDragStart(e, { type: t }); setOpenCat(null); }}
                      className="cursor-grab rounded-md border border-border bg-surface-2 px-2 py-1 text-left text-xs hover:bg-surface-3"
                      style={{ borderLeft: `3px solid ${CATEGORY_COLOR[cat]}` }}
                    >
                      {NODE_CATALOG[t].title}
                    </button>
                  ))}
                  {cat === "strategy" && saved.isError && (
                    <div className="text-[10px] text-error">無法載入已存策略</div>
                  )}
                  {savedItems.map((s) => (
                    <button
                      key={`saved-${s.id}`}
                      draggable
                      onDragStart={(e) => { onChipDragStart(e, { type: "strategy", savedStrategyId: s.id, name: s.name }); setOpenCat(null); }}
                      className="cursor-grab rounded-md border border-border bg-surface-2 px-2 py-1 text-left text-xs hover:bg-surface-3"
                      style={{ borderLeft: `3px solid ${CATEGORY_COLOR.strategy}` }}
                      title={s.description}
                    >
                      ★ {s.name}
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </aside>
    );
  }

  return (
    <aside className="flex h-full w-[200px] shrink-0 flex-col gap-2 overflow-y-auto border-r border-border bg-surface-1 p-2">
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="搜尋節點…"
        className="rounded-md bg-surface-2 px-2 py-1 text-xs text-text"
      />
      {CATEGORY_ORDER.map((cat) => {
        const items = byCategory[cat].filter((t) => match(NODE_CATALOG[t].title));
        const savedItems = cat === "strategy" ? (saved.data ?? []).filter((s) => match(s.name)) : [];
        if (items.length === 0 && savedItems.length === 0) return null;
        return (
          <div key={cat}>
            <div className="mb-1 flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-faint">
              <span className="inline-block h-2 w-2 rounded-full" style={{ background: CATEGORY_COLOR[cat] }} />
              {CATEGORY_LABEL[cat]}
            </div>
            <div className="flex flex-col gap-1">
              {items.map((t) => (
                <button
                  key={t}
                  draggable
                  onDragStart={(e) => onChipDragStart(e, { type: t })}
                  className="cursor-grab rounded-md border border-border bg-surface-2 px-2 py-1 text-left text-xs hover:bg-surface-3"
                  style={{ borderLeft: `3px solid ${CATEGORY_COLOR[cat]}` }}
                >
                  {NODE_CATALOG[t].title}
                </button>
              ))}
              {cat === "strategy" && saved.isError && (
                <div className="text-[10px] text-error">無法載入已存策略</div>
              )}
              {savedItems.map((s) => (
                <button
                  key={`saved-${s.id}`}
                  draggable
                  onDragStart={(e) => onChipDragStart(e, { type: "strategy", savedStrategyId: s.id, name: s.name })}
                  className="cursor-grab rounded-md border border-border bg-surface-2 px-2 py-1 text-left text-xs hover:bg-surface-3"
                  style={{ borderLeft: `3px solid ${CATEGORY_COLOR.strategy}` }}
                  title={s.description}
                >
                  ★ {s.name}
                </button>
              ))}
            </div>
          </div>
        );
      })}
    </aside>
  );
}
