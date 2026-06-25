"use client";

import { Copy, FolderOpen, Save, Trash2 } from "lucide-react";
import type { ValidationResult } from "./validateGraph";

export function Toolbar({
  mode, valid, nodeCount, edgeCount, canUndo, canRedo,
  onUndo, onRedo, onZoomIn, onZoomOut, onFit, name, onName, currentWorkflowId,
  onOpen, onSave, onSaveAs, onDeleteCurrent, saving, onRun, running,
  onBacktest, backtesting,
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
  currentWorkflowId: number | null;
  onOpen: () => void;
  onSave: () => void;
  onSaveAs: () => void;
  onDeleteCurrent: () => void;
  saving: boolean;
  onRun: () => void;
  running: boolean;
  onBacktest: () => void;
  backtesting: boolean;
}) {
  const live = mode === "live";
  const btn = "rounded-md bg-surface-2 px-2 py-1 text-xs hover:bg-surface-3 disabled:opacity-40";
  const actionBtn = "inline-flex items-center gap-1 rounded-md bg-surface-2 px-3 py-1 text-sm hover:bg-surface-3 disabled:opacity-40";
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
      <span className="rounded-sm bg-surface-3 px-2 py-1 text-xs text-muted">
        {currentWorkflowId ? `#${currentWorkflowId}` : "新檔"}
      </span>
      <button onClick={onOpen} className={actionBtn} title="開啟 workflow">
        <FolderOpen size={14} />
        開啟
      </button>
      <button onClick={onSave} disabled={saving} className={actionBtn} title="儲存目前 workflow">
        <Save size={14} />
        {saving ? "儲存中" : "儲存"}
      </button>
      <button onClick={onSaveAs} disabled={saving} className={actionBtn} title="另存新檔">
        <Copy size={14} />
        另存
      </button>
      <button
        onClick={onDeleteCurrent}
        disabled={!currentWorkflowId || saving}
        className="inline-flex items-center gap-1 rounded-md bg-surface-2 px-3 py-1 text-sm text-error hover:bg-surface-3 disabled:opacity-40"
        title="刪除目前 workflow"
      >
        <Trash2 size={14} />
        刪除
      </button>
      <button
        onClick={onRun}
        disabled={running}
        className={`rounded-md px-3 py-1 text-sm font-medium disabled:opacity-50 ${live ? "bg-live/20 text-live hover:bg-live/30" : "bg-accent text-bg hover:brightness-110"}`}
      >
        {running ? "Running…" : live ? "▶ 送出真實訂單" : "▶ 執行回測"}
      </button>
      <button
        onClick={onBacktest}
        disabled={backtesting || !valid.valid}
        className="rounded-md bg-surface-2 px-3 py-1 text-sm font-medium hover:bg-surface-3 disabled:opacity-50"
      >
        {backtesting ? "Backtesting…" : "📊 Backtest"}
      </button>
    </div>
  );
}
