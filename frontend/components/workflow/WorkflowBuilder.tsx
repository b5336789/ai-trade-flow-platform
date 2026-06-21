"use client";

import { ReactFlowProvider, type ReactFlowInstance } from "@xyflow/react";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { api, type RunResult, type WorkflowRunDTO, type WorkflowSignalDTO } from "@/lib/api";
import { SignalTraceDrawer } from "@/components/SignalTraceDrawer";
import { WorkflowBacktestChart } from "@/components/WorkflowBacktestChart";
import { WorkflowRunHistory } from "@/components/WorkflowRunHistory";
import { Canvas } from "./Canvas";
import { Inspector } from "./Inspector";
import { Palette } from "./Palette";
import { Toolbar } from "./Toolbar";
import { useWorkflowState } from "./useWorkflowState";
import { validateGraph } from "./validateGraph";

function BuilderInner() {
  const wf = useWorkflowState();
  const config = useQuery({ queryKey: ["config"], queryFn: api.config, retry: false });
  const [rf, setRf] = useState<ReactFlowInstance | null>(null);
  const [name, setName] = useState("My workflow");
  const [result, setResult] = useState<RunResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [btRun, setBtRun] = useState<WorkflowRunDTO | null>(null);
  const [btSignals, setBtSignals] = useState<WorkflowSignalDTO[]>([]);
  const [selected, setSelected] = useState<WorkflowSignalDTO | null>(null);
  const [backtesting, setBacktesting] = useState(false);
  const [historyRefresh, setHistoryRefresh] = useState(0);

  const valid = useMemo(() => validateGraph(wf.buildGraph()), [wf.nodes, wf.edges]);
  const selectedNode = wf.nodes.find((n) => n.id === wf.selectedId) ?? null;
  const mode = config.data?.trading_mode ?? "paper";

  async function save() {
    setSavedMsg(null); setError(null);
    try {
      const w = await api.createWorkflow(name, wf.buildGraph());
      setSavedMsg(`Saved as #${w.id} — schedule it to run automatically.`);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function run() {
    setRunning(true); setError(null); setResult(null);
    try {
      setResult(await api.runWorkflow(wf.buildGraph()));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRunning(false);
    }
  }

  async function handleBacktest() {
    setBacktesting(true); setError(null); setBtRun(null); setBtSignals([]);
    try {
      const res = await api.runWorkflowBacktest({ graph: wf.buildGraph(), limit: 500 });
      const run = await api.getWorkflowRun(res.run_id);
      setBtRun(run);
      setBtSignals(res.signals);
      setHistoryRefresh((n) => n + 1);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBacktesting(false);
    }
  }

  async function openRun(runId: number) {
    setError(null);
    try {
      const [run, sigs] = await Promise.all([api.getWorkflowRun(runId), api.getWorkflowRunSignals(runId)]);
      setBtRun(run);
      setBtSignals(sigs);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <section className="rounded-lg border border-border bg-surface-1">
      <Toolbar
        mode={mode}
        valid={valid}
        nodeCount={wf.nodes.length}
        edgeCount={wf.edges.length}
        canUndo={wf.canUndo}
        canRedo={wf.canRedo}
        onUndo={wf.undo}
        onRedo={wf.redo}
        onZoomIn={() => rf?.zoomIn()}
        onZoomOut={() => rf?.zoomOut()}
        onFit={() => rf?.fitView()}
        name={name}
        onName={setName}
        onSave={save}
        onRun={run}
        running={running}
        onBacktest={handleBacktest}
        backtesting={backtesting}
      />
      {savedMsg && <p className="px-3 py-1 text-sm text-up">{savedMsg}</p>}
      <div className="relative flex h-[520px]">
        {/* Palette: full on xl, icon strip on md, hidden on mobile */}
        {/* Full palette: desktop only */}
        <div className="hidden xl:block">
          <Palette />
        </div>
        {/* Compact icon-strip palette: tablet only */}
        <div className="hidden md:block xl:hidden">
          <Palette compact />
        </div>
        <div className="relative flex-1">
          <Canvas wf={wf} onInit={setRf} />
        </div>
        {/* Inspector: inline on xl; slide-over on md/sm when a node is selected */}
        {selectedNode && (
          <div className="absolute inset-y-0 right-0 z-10 xl:static xl:z-auto">
            <Inspector node={selectedNode} setParam={wf.setParam} onDelete={wf.deleteNode} onDuplicate={wf.duplicateNode} onClose={() => wf.setSelectedId(null)} />
          </div>
        )}
        {!selectedNode && (
          <div className="hidden xl:block">
            <Inspector node={null} setParam={wf.setParam} onDelete={wf.deleteNode} onDuplicate={wf.duplicateNode} />
          </div>
        )}
      </div>
      {error && <p className="px-3 py-2 text-sm text-error">Error: {error}</p>}
      {result && (
        <div className="m-3 rounded-lg border border-border bg-surface-2 p-3 text-xs">
          <div className="mb-1">
            Status: <span className={result.status === "ok" ? "text-up" : "text-error"}>{result.status}</span>
            {result.error && <span className="text-error"> — {result.error}</span>}
          </div>
          <ol className="space-y-0.5">
            {result.steps.map((s) => (
              <li key={s.node_id} className="text-text">
                <span className="text-faint">{s.type}</span> [{s.node_id}]: {JSON.stringify(s.summary)}
              </li>
            ))}
          </ol>
        </div>
      )}
      {btRun && (
        <div className="m-3 rounded-lg border border-border bg-surface-2 p-3">
          <div className="mb-2 flex items-center gap-3 text-xs">
            <span className="font-display font-semibold text-text">Backtest · {btRun.symbols.join(", ")}</span>
            {btRun.metrics_json && (
              <>
                <span className={btRun.metrics_json.total_return_pct >= 0 ? "text-up" : "text-down"}>
                  return {btRun.metrics_json.total_return_pct?.toFixed(2)}%
                </span>
                {btRun.metrics_json.sharpe_ratio != null && (
                  <span className="text-muted">sharpe {btRun.metrics_json.sharpe_ratio.toFixed(2)}</span>
                )}
                {btRun.metrics_json.max_drawdown_pct != null && (
                  <span className="text-muted">drawdown {btRun.metrics_json.max_drawdown_pct.toFixed(2)}%</span>
                )}
              </>
            )}
          </div>
          <WorkflowBacktestChart run={btRun} signals={btSignals} onSelectSignal={setSelected} />
        </div>
      )}
      <WorkflowRunHistory kind="backtest" onOpen={openRun} refreshKey={historyRefresh} />
      <SignalTraceDrawer signal={selected} onClose={() => setSelected(null)} />
    </section>
  );
}

export function WorkflowBuilder() {
  return (
    <ReactFlowProvider>
      <BuilderInner />
    </ReactFlowProvider>
  );
}
