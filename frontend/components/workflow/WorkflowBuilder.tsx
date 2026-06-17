"use client";

import {
  addEdge,
  Background,
  Controls,
  ReactFlow,
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
  type Node,
} from "@xyflow/react";
import { useCallback, useMemo, useRef, useState } from "react";
import { api, type NodeType, type RunResult, type WorkflowGraph } from "@/lib/api";
import { TradeNode, type TradeNodeData } from "./TradeNode";

const DEFAULTS: Record<NodeType, Record<string, unknown>> = {
  data_source: { symbol: "BTC/USDT", timeframe: "1h", limit: 100 },
  strategy: { name: "ma_cross", fast: 10, slow: 20 },
  ai_signal: {},
  risk_exit: { stop_loss_pct: 5, take_profit_pct: 10 },
  order: { quantity: 0.01 },
  logger: {},
};

function starterNodes(setParam: TradeNodeData["setParam"]): Node[] {
  const mk = (id: string, type: NodeType, x: number, y: number): Node => ({
    id,
    type: "trade",
    position: { x, y },
    data: { nodeType: type, params: { ...DEFAULTS[type] }, setParam },
  });
  return [
    mk("data", "data_source", 0, 40),
    mk("strat", "strategy", 230, 40),
    mk("order", "order", 460, 40),
    mk("log", "logger", 690, 40),
  ];
}

const starterEdges: Edge[] = [
  { id: "e1", source: "data", target: "strat" },
  { id: "e2", source: "strat", target: "order" },
  { id: "e3", source: "order", target: "log" },
];

export function WorkflowBuilder() {
  const nodeTypes = useMemo(() => ({ trade: TradeNode }), []);
  const idCounter = useRef(100);

  const setParam = useCallback<TradeNodeData["setParam"]>((id, key, value) => {
    setNodes((nds) =>
      nds.map((n) =>
        n.id === id
          ? { ...n, data: { ...n.data, params: { ...(n.data as TradeNodeData).params, [key]: value } } }
          : n,
      ),
    );
  }, []);

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>(starterNodes(setParam));
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>(starterEdges);
  const [result, setResult] = useState<RunResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [name, setName] = useState("My workflow");
  const [savedMsg, setSavedMsg] = useState<string | null>(null);

  const onConnect = useCallback((c: Connection) => setEdges((eds) => addEdge(c, eds)), [setEdges]);

  function buildGraph(): WorkflowGraph {
    return {
      nodes: nodes.map((n) => ({
        id: n.id,
        type: (n.data as TradeNodeData).nodeType,
        params: (n.data as TradeNodeData).params,
      })),
      edges: edges.map((e) => ({ source: e.source, target: e.target })),
    };
  }

  async function save() {
    setSavedMsg(null);
    setError(null);
    try {
      const wf = await api.createWorkflow(name, buildGraph());
      setSavedMsg(`Saved as #${wf.id} — schedule it below to run automatically.`);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  function addNode(type: NodeType) {
    const id = `n${idCounter.current++}`;
    setNodes((nds) => [
      ...nds,
      {
        id,
        type: "trade",
        position: { x: 80 + Math.random() * 200, y: 200 + Math.random() * 120 },
        data: { nodeType: type, params: { ...DEFAULTS[type] }, setParam },
      },
    ]);
  }

  async function run() {
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      setResult(await api.runWorkflow(buildGraph()));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRunning(false);
    }
  }

  const NODE_BUTTONS: NodeType[] = ["data_source", "strategy", "ai_signal", "risk_exit", "order", "logger"];

  return (
    <section className="rounded-lg border border-neutral-800 bg-neutral-900/40 p-4">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <h2 className="mr-2 text-lg font-semibold">Workflow Builder</h2>
        {NODE_BUTTONS.map((t) => (
          <button
            key={t}
            onClick={() => addNode(t)}
            className="rounded bg-neutral-800 px-2 py-1 text-xs hover:bg-neutral-700"
          >
            + {t}
          </button>
        ))}
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="ml-auto rounded bg-neutral-800 px-2 py-1 text-sm"
          placeholder="workflow name"
        />
        <button
          onClick={save}
          className="rounded bg-blue-600 px-3 py-1 text-sm font-medium hover:bg-blue-500"
        >
          Save
        </button>
        <button
          onClick={run}
          disabled={running}
          className="rounded bg-green-600 px-3 py-1 text-sm font-medium hover:bg-green-500 disabled:opacity-50"
        >
          {running ? "Running…" : "Run"}
        </button>
      </div>
      {savedMsg && <p className="mb-2 text-sm text-green-400">{savedMsg}</p>}

      <div className="h-[360px] rounded border border-neutral-800">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          fitView
        >
          <Background />
          <Controls />
        </ReactFlow>
      </div>

      {error && <p className="mt-3 text-sm text-red-400">Run error: {error}</p>}
      {result && (
        <div className="mt-3 rounded border border-neutral-800 bg-neutral-900 p-3 text-xs">
          <div className="mb-1">
            Status:{" "}
            <span className={result.status === "ok" ? "text-green-400" : "text-red-400"}>
              {result.status}
            </span>
            {result.error && <span className="text-red-400"> — {result.error}</span>}
          </div>
          <ol className="space-y-0.5">
            {result.steps.map((s) => (
              <li key={s.node_id} className="text-neutral-300">
                <span className="text-neutral-500">{s.type}</span> [{s.node_id}]:{" "}
                {JSON.stringify(s.summary)}
              </li>
            ))}
          </ol>
        </div>
      )}
    </section>
  );
}
