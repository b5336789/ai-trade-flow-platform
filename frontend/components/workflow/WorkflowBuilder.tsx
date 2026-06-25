"use client";

import { ReactFlowProvider, type ReactFlowInstance } from "@xyflow/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api, type RunResult, type Workflow, type WorkflowGraph, type WorkflowRunDTO, type WorkflowSignalDTO } from "@/lib/api";
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
  const qc = useQueryClient();
  const wf = useWorkflowState();
  const config = useQuery({ queryKey: ["config"], queryFn: api.config, retry: false });
  const workflows = useQuery({ queryKey: ["workflows"], queryFn: api.listWorkflows, retry: false });
  const [rf, setRf] = useState<ReactFlowInstance | null>(null);
  const [name, setName] = useState("My workflow");
  const [currentWorkflowId, setCurrentWorkflowId] = useState<number | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [result, setResult] = useState<RunResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [running, setRunning] = useState(false);
  const [btRun, setBtRun] = useState<WorkflowRunDTO | null>(null);
  const [btSignals, setBtSignals] = useState<WorkflowSignalDTO[]>([]);
  const [selected, setSelected] = useState<WorkflowSignalDTO | null>(null);
  const [backtesting, setBacktesting] = useState(false);
  const [historyRefresh, setHistoryRefresh] = useState(0);

  const searchParams = useSearchParams();
  const loadedWorkflow = useRef(false);

  // Deep-link from a backtest result: ?workflow=<id> seeds the canvas once.
  useEffect(() => {
    if (loadedWorkflow.current) return;
    const idStr = searchParams.get("workflow");
    if (!idStr) return;
    const id = Number(idStr);
    if (!Number.isFinite(id)) return;
    loadedWorkflow.current = true;
    api
      .getWorkflow(id)
      .then((w) => {
        wf.setGraph(w.graph);
        setName(w.name);
        setCurrentWorkflowId(w.id);
      })
      .catch((e) => setError((e as Error).message));
  }, [searchParams]);

  const valid = useMemo(() => validateGraph(wf.buildGraph()), [wf.nodes, wf.edges]);
  const selectedNode = wf.nodes.find((n) => n.id === wf.selectedId) ?? null;
  const mode = config.data?.trading_mode ?? "paper";

  function graphForSave(): WorkflowGraph | null {
    const graph = wf.buildGraph();
    const checked = validateGraph(graph);
    if (!checked.valid) {
      setError(`Workflow invalid: ${checked.errors[0]}`);
      return null;
    }
    return graph;
  }

  async function save() {
    setSavedMsg(null); setError(null);
    const graph = graphForSave();
    if (!graph) return;
    setSaving(true);
    try {
      const workflowName = name.trim() || "Untitled workflow";
      const w = currentWorkflowId
        ? await api.updateWorkflow(currentWorkflowId, workflowName, graph)
        : await api.createWorkflow(workflowName, graph);
      setName(w.name);
      setCurrentWorkflowId(w.id);
      setSavedMsg(`Saved #${w.id}.`);
      qc.invalidateQueries({ queryKey: ["workflows"] });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function saveAs() {
    setSavedMsg(null); setError(null);
    const graph = graphForSave();
    if (!graph) return;
    setSaving(true);
    try {
      const workflowName = name.trim() || "Untitled workflow";
      const w = await api.createWorkflow(workflowName, graph);
      setName(w.name);
      setCurrentWorkflowId(w.id);
      setSavedMsg(`Saved as new workflow #${w.id}.`);
      qc.invalidateQueries({ queryKey: ["workflows"] });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function openWorkflow(workflow: Workflow) {
    setSavedMsg(null); setError(null);
    try {
      const loaded = await api.getWorkflow(workflow.id);
      wf.setGraph(loaded.graph);
      setName(loaded.name);
      setCurrentWorkflowId(loaded.id);
      setPickerOpen(false);
      setSavedMsg(`Loaded #${loaded.id}.`);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function deleteWorkflow(id: number, workflowName?: string) {
    if (!window.confirm(`Delete workflow #${id}${workflowName ? ` ${workflowName}` : ""}?`)) return;
    setSavedMsg(null); setError(null); setDeletingId(id);
    try {
      await api.deleteWorkflow(id);
      if (currentWorkflowId === id) {
        setCurrentWorkflowId(null);
        setSavedMsg(`Deleted #${id}. Current canvas is now an unsaved draft.`);
      } else {
        setSavedMsg(`Deleted #${id}.`);
      }
      qc.invalidateQueries({ queryKey: ["workflows"] });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setDeletingId(null);
    }
  }

  async function deleteCurrentWorkflow() {
    if (!currentWorkflowId) return;
    await deleteWorkflow(currentWorkflowId, name);
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
        currentWorkflowId={currentWorkflowId}
        onOpen={() => setPickerOpen((open) => !open)}
        onSave={save}
        onSaveAs={saveAs}
        onDeleteCurrent={deleteCurrentWorkflow}
        saving={saving}
        onRun={run}
        running={running}
        onBacktest={handleBacktest}
        backtesting={backtesting}
      />
      {pickerOpen && (
        <div className="border-b border-border bg-surface-1 px-3 py-3">
          <div className="mb-2 flex items-center justify-between gap-2">
            <p className="text-xs font-medium text-muted">Saved workflows</p>
            <button
              onClick={() => workflows.refetch()}
              className="rounded-md bg-surface-2 px-2 py-1 text-xs hover:bg-surface-3"
            >
              Refresh
            </button>
          </div>
          {workflows.isLoading && <p className="text-xs text-faint">Loading workflows...</p>}
          {workflows.error && <p className="text-xs text-error">{(workflows.error as Error).message}</p>}
          {workflows.data && workflows.data.length > 0 ? (
            <div className="max-h-52 overflow-auto rounded-md border border-border">
              <table className="w-full text-left text-xs">
                <thead className="bg-surface-2 text-faint">
                  <tr>
                    <th className="px-2 py-1">ID</th>
                    <th className="px-2 py-1">Name</th>
                    <th className="px-2 py-1">Updated</th>
                    <th className="px-2 py-1" />
                  </tr>
                </thead>
                <tbody>
                  {workflows.data.map((w) => (
                    <tr key={w.id} className="border-t border-border">
                      <td className="px-2 py-1 text-muted">#{w.id}</td>
                      <td className="px-2 py-1 text-text">{w.name}</td>
                      <td className="px-2 py-1 text-faint">{new Date(w.updated_at).toLocaleString()}</td>
                      <td className="px-2 py-1 text-right">
                        <button
                          onClick={() => openWorkflow(w)}
                          className="mr-2 rounded-sm bg-accent px-2 py-0.5 font-medium text-bg hover:brightness-110"
                        >
                          Open
                        </button>
                        <button
                          onClick={() => deleteWorkflow(w.id, w.name)}
                          disabled={deletingId === w.id}
                          className="rounded-sm px-2 py-0.5 text-error hover:bg-error/10 disabled:opacity-40"
                        >
                          {deletingId === w.id ? "Deleting" : "Delete"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            !workflows.isLoading && <p className="text-xs text-faint">No saved workflows yet.</p>
          )}
        </div>
      )}
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
                {btRun.metrics_json.sharpe != null && (
                  <span className="text-muted">sharpe {btRun.metrics_json.sharpe.toFixed(2)}</span>
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
