"use client";

import { Handle, Position, type NodeProps } from "@xyflow/react";
import { CATEGORY_LABEL, NODE_CATALOG, summaryText } from "./nodeCatalog";
import type { TradeNodeData } from "./useWorkflowState";

export function TradeNode({ data, selected }: NodeProps) {
  const d = data as TradeNodeData;
  const meta = NODE_CATALOG[d.nodeType];
  const summary = summaryText(d.nodeType, d.params);
  const isAI = d.nodeType === "ai_signal";

  return (
    <div
      className="relative w-[158px] overflow-hidden rounded-md border bg-surface-1 text-text shadow"
      style={{
        borderColor: selected ? "var(--accent)" : "var(--border)",
        borderWidth: selected ? 2 : 1,
      }}
    >
      <div className="absolute left-0 top-0 h-full w-[3px]" style={{ background: meta.colorVar }} />
      {meta.hasInput && (
        <Handle type="target" position={Position.Left} style={{ borderColor: meta.colorVar, background: "var(--surface-1)" }} />
      )}
      <div className="pl-2 pr-2 pt-1.5">
        <div className="flex items-center gap-1.5">
          <span className="inline-block h-2 w-2 rounded-full" style={{ background: meta.colorVar }} />
          <span className={`truncate text-xs font-semibold ${isAI ? "text-accent" : "text-text"}`}>{meta.title}</span>
        </div>
        <div className="mt-0.5 text-[9px] uppercase tracking-wide text-faint">{CATEGORY_LABEL[meta.category]}</div>
      </div>
      <div className="px-2 pb-2 pt-1">
        {summary ? (
          <div className="num truncate rounded-sm bg-surface-2 px-1 py-0.5 text-[11px] text-muted">{summary}</div>
        ) : (
          <div className="text-[10px] text-faint">{isAI ? "AI signal" : "—"}</div>
        )}
      </div>
      {meta.hasOutput && (
        <Handle type="source" position={Position.Right} style={{ borderColor: meta.colorVar, background: "var(--surface-1)" }} />
      )}
    </div>
  );
}
