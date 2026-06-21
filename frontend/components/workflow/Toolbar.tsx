"use client";

import type { ValidationResult } from "./validateGraph";

export function Toolbar({
  mode, valid, nodeCount, edgeCount, canUndo, canRedo,
  onUndo, onRedo, onZoomIn, onZoomOut, onFit, name, onName, onSave, onRun, running,
}: {
  mode: string;
  valid: ValidationResult;
  nodeCount: number;
  edgeCount: number;
  canUndo: boolean;
  canRedo: boolean;
  onUndo: () => void;
  onRedo: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onFit: () => void;
  name: string;
  onName: (v: string) => void;
  onSave: () => void;
  onRun: () => void;
  running: boolean;
}) {
  const live = mode === "live";
  const btn = "rounded-md bg-surface-2 px-2 py-1 text-xs hover:bg-surface-3 disabled:opacity-40";
  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-border bg-surface-1 px-3 py-2">
      <h2 className="font-display text-sm font-semibold">Workflow Builder.</h2>
      <span className={`rounded-sm px-1.5 py-0.5 text-[10px] ${live ? "bg-live/15 text-live" : "bg-surface-3 text-muted"}`}>
        交易室 · {mode.toUpperCase()}
      </span>
      <div className="flex items-center gap-1">
        <button className={btn} onClick={onUndo} disabled={!canUndo} title="復原">↶</button>
        <button className={btn} onClick={onRedo} disabled={!canRedo} title="重做">↷</button>
      </div>
      <div className="flex items-center gap-1">
        <button className={btn} onClick={onZoomOut}>−</button>
        <button className={btn} onClick={onFit}>fit</button>
        <button className={btn} onClick={onZoomIn}>＋</button>
      </div>
      <span className={`text-xs ${valid.valid ? "text-up" : "text-error"}`}>
        {valid.valid ? `✓ 有效 · ${nodeCount} nodes · ${edgeCount} edges` : `✗ ${valid.errors[0]}`}
      </span>
      <input
        value={name}
        onChange={(e) => onName(e.target.value)}
        placeholder="workflow name"
        className="ml-auto rounded-md bg-surface-2 px-2 py-1 text-sm"
      />
      <button onClick={onSave} className="rounded-md bg-surface-2 px-3 py-1 text-sm hover:bg-surface-3">💾 儲存</button>
      <button
        onClick={onRun}
        disabled={running}
        className={`rounded-md px-3 py-1 text-sm font-medium disabled:opacity-50 ${live ? "bg-live/20 text-live hover:bg-live/30" : "bg-accent text-bg hover:brightness-110"}`}
      >
        {running ? "Running…" : live ? "▶ 送出真實訂單" : "▶ 執行回測"}
      </button>
    </div>
  );
}
