"use client";

import { ReactFlowProvider, type ReactFlowInstance } from "@xyflow/react";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { api, type RunResult } from "@/lib/api";
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
      />
      {savedMsg && <p className="px-3 py-1 text-sm text-up">{savedMsg}</p>}
      <div className="flex h-[520px]">
        <Palette />
        <div className="relative flex-1">
          <Canvas wf={wf} onInit={setRf} />
        </div>
        <Inspector node={selectedNode} setParam={wf.setParam} onDelete={wf.deleteNode} onDuplicate={wf.duplicateNode} />
      </div>
      {error && <p className="px-3 py-2 text-sm text-error">Run error: {error}</p>}
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
