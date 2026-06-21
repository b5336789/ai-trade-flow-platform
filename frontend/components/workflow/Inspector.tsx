"use client";

import type { Node } from "@xyflow/react";
import { STRATEGY_NAMES, STRATEGY_PARAMS } from "@/lib/strategies";
import { CATEGORY_COLOR, CATEGORY_LABEL, NODE_CATALOG, type ParamField } from "./nodeCatalog";
import type { TradeNodeData } from "./useWorkflowState";

function FieldInput({ field, value, onChange }: { field: ParamField; value: unknown; onChange: (v: unknown) => void }) {
  if (field.kind === "select") {
    return (
      <select
        value={String(value ?? field.default)}
        onChange={(e) => onChange(e.target.value)}
        className="mt-0.5 w-full rounded-sm bg-surface-2 px-1.5 py-1 text-xs text-text"
      >
        {(field.options ?? []).map((o) => (
          <option key={o} value={o}>{o}</option>
        ))}
      </select>
    );
  }
  return (
    <input
      type={field.kind === "number" ? "number" : "text"}
      value={String(value ?? "")}
      onChange={(e) => onChange(field.kind === "number" ? Number(e.target.value) : e.target.value)}
      className="mt-0.5 w-full rounded-sm bg-surface-2 px-1.5 py-1 text-xs text-text"
    />
  );
}

export function Inspector({
  node,
  setParam,
  onDelete,
  onDuplicate,
  onClose,
}: {
  node: Node | null;
  setParam: (id: string, key: string, value: unknown) => void;
  onDelete: (id: string) => void;
  onDuplicate: (id: string) => void;
  onClose?: () => void;
}) {
  if (!node) {
    return (
      <aside className="w-64 shrink-0 border-l border-border bg-surface-1 p-3 text-xs text-faint">
        選擇一個節點以編輯參數。
      </aside>
    );
  }
  const d = node.data as TradeNodeData;
  const meta = NODE_CATALOG[d.nodeType];
  const set = (key: string, value: unknown) => setParam(node.id, key, value);

  // strategy: name select (from STRATEGY_NAMES) + dynamic numeric params from STRATEGY_PARAMS[name]
  const strategyName = d.nodeType === "strategy" ? String(d.params.name ?? "ma_cross") : "";
  const strategyParamKeys = d.nodeType === "strategy" ? Object.keys(STRATEGY_PARAMS[strategyName] ?? {}) : [];

  return (
    <aside className="flex w-64 shrink-0 flex-col border-l border-border bg-surface-1">
      <div className="border-b border-border p-3">
        <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-faint">
          <span className="inline-block h-2 w-2 rounded-full" style={{ background: CATEGORY_COLOR[meta.category] }} />
          {CATEGORY_LABEL[meta.category]}
          {onClose && (
            <button
              onClick={onClose}
              className="ml-auto text-faint hover:text-text xl:hidden"
              aria-label="關閉"
            >
              ✕
            </button>
          )}
        </div>
        <div className="mt-0.5 font-display text-sm font-semibold">{meta.title}</div>
      </div>

      <div className="flex-1 space-y-2 overflow-y-auto p-3">
        {d.nodeType === "strategy" && d.params.strategy_id ? (
          <div className="rounded-sm bg-surface-2 px-2 py-1.5 text-xs text-muted">
            已存策略 #{String(d.params.strategy_id)}
          </div>
        ) : (
          <>
            {meta.params.map((f) => {
              if (d.nodeType === "strategy" && f.key === "name") {
                return (
                  <label key="name" className="block text-[10px] text-muted">
                    name
                    <select
                      value={strategyName}
                      onChange={(e) => set("name", e.target.value)}
                      className="mt-0.5 w-full rounded-sm bg-surface-2 px-1.5 py-1 text-xs text-text"
                    >
                      {STRATEGY_NAMES.map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  </label>
                );
              }
              return (
                <label key={f.key} className="block text-[10px] text-muted">
                  {f.label}
                  <FieldInput field={f} value={d.params[f.key]} onChange={(v) => set(f.key, v)} />
                </label>
              );
            })}

            {strategyParamKeys.map((key) => (
              <label key={key} className="block text-[10px] text-muted">
                {key}
                <input
                  type="number"
                  value={String(d.params[key] ?? STRATEGY_PARAMS[strategyName][key])}
                  onChange={(e) => set(key, Number(e.target.value))}
                  className="mt-0.5 w-full rounded-sm bg-surface-2 px-1.5 py-1 text-xs text-text"
                />
              </label>
            ))}
          </>
        )}

        {d.nodeType === "combine" && String(d.params.mode ?? "AND") === "OR" && (
          <label className="block text-[10px] text-muted">
            bias (buy/sell)
            <input
              value={String(d.params.bias ?? "")}
              onChange={(e) => set("bias", e.target.value)}
              className="mt-0.5 w-full rounded-sm bg-surface-2 px-1.5 py-1 text-xs text-text"
            />
          </label>
        )}
      </div>

      <div className="flex gap-2 border-t border-border p-3">
        <button onClick={() => onDuplicate(node.id)} className="flex-1 rounded-md bg-surface-2 px-2 py-1 text-xs hover:bg-surface-3">複製</button>
        <button onClick={() => onDelete(node.id)} className="flex-1 rounded-md bg-down/15 px-2 py-1 text-xs text-down hover:bg-down/25">刪除</button>
      </div>
    </aside>
  );
}
