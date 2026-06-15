"use client";

import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { NodeType } from "@/lib/api";

export interface TradeNodeData {
  nodeType: NodeType;
  params: Record<string, unknown>;
  setParam: (id: string, key: string, value: unknown) => void;
  [key: string]: unknown;
}

const TITLES: Record<NodeType, string> = {
  data_source: "Data Source",
  strategy: "Strategy",
  ai_signal: "AI Signal",
  order: "Order",
  logger: "Logger",
};

function Field({
  label,
  value,
  onChange,
  type = "text",
}: {
  label: string;
  value: unknown;
  onChange: (v: string) => void;
  type?: string;
}) {
  return (
    <label className="mb-1 block text-[10px] text-neutral-400">
      {label}
      <input
        type={type}
        value={String(value ?? "")}
        onChange={(e) => onChange(e.target.value)}
        className="mt-0.5 w-full rounded bg-neutral-800 px-1 py-0.5 text-xs text-neutral-100"
      />
    </label>
  );
}

export function TradeNode({ id, data }: NodeProps) {
  const d = data as TradeNodeData;
  const p = d.params;
  const set = (key: string, value: unknown) => d.setParam(id, key, value);
  const hasInput = d.nodeType !== "data_source";
  const hasOutput = d.nodeType !== "logger" && d.nodeType !== "order";

  return (
    <div className="min-w-[170px] rounded-md border border-neutral-700 bg-neutral-900 p-2 shadow">
      {hasInput && <Handle type="target" position={Position.Left} />}
      <div className="mb-1 text-xs font-semibold text-indigo-300">{TITLES[d.nodeType]}</div>

      {d.nodeType === "data_source" && (
        <>
          <Field label="symbol" value={p.symbol} onChange={(v) => set("symbol", v)} />
          <Field label="timeframe" value={p.timeframe} onChange={(v) => set("timeframe", v)} />
          <Field label="limit" type="number" value={p.limit} onChange={(v) => set("limit", Number(v))} />
        </>
      )}

      {d.nodeType === "strategy" && (
        <>
          <label className="mb-1 block text-[10px] text-neutral-400">
            name
            <select
              value={String(p.name ?? "ma_cross")}
              onChange={(e) => set("name", e.target.value)}
              className="mt-0.5 w-full rounded bg-neutral-800 px-1 py-0.5 text-xs"
            >
              <option value="ma_cross">ma_cross</option>
              <option value="rsi">rsi</option>
            </select>
          </label>
          {p.name === "rsi" ? (
            <Field label="window" type="number" value={p.window} onChange={(v) => set("window", Number(v))} />
          ) : (
            <>
              <Field label="fast" type="number" value={p.fast} onChange={(v) => set("fast", Number(v))} />
              <Field label="slow" type="number" value={p.slow} onChange={(v) => set("slow", Number(v))} />
            </>
          )}
        </>
      )}

      {d.nodeType === "ai_signal" && (
        <Field label="model (optional)" value={p.model} onChange={(v) => set("model", v || undefined)} />
      )}

      {d.nodeType === "order" && (
        <Field label="quantity" type="number" value={p.quantity} onChange={(v) => set("quantity", Number(v))} />
      )}

      {d.nodeType === "logger" && <div className="text-[10px] text-neutral-500">records run output</div>}

      {hasOutput && <Handle type="source" position={Position.Right} />}
    </div>
  );
}
