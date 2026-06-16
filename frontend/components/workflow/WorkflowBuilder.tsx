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

  const NODE_BUTTONS: NodeType[] = ["data_source", "strategy", "ai_signal", "order", "logger"];

  return (
    <section className="card">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <h2 className="panel-title mr-1">🧩 工作流建立器 Workflow Builder</h2>
        {NODE_BUTTONS.map((t) => (
          <button key={t} onClick={() => addNode(t)} className="btn btn-ghost btn-xs">
            + {t}
          </button>
        ))}
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="input ml-auto w-40"
          placeholder="workflow name"
        />
        <button onClick={save} className="btn bg-sky-600 text-white hover:bg-sky-500">
          儲存
        </button>
        <button onClick={run} disabled={running} className="btn btn-success">
          {running ? (
            <>
              <Spinner /> 執行中…
            </>
          ) : (
            "▶ 執行"
          )}
        </button>
      </div>
      {savedMsg && <p className="mb-2 text-sm text-emerald-400">{savedMsg}</p>}

      <div className="h-[360px] overflow-hidden rounded-lg border border-white/5">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          fitView
          proOptions={{ hideAttribution: true }}
        >
          <Background gap={16} color="#27272a" />
          <Controls className="!border-white/10 !bg-neutral-800 [&_button]:!border-white/10 [&_button]:!bg-neutral-800 [&_button:hover]:!bg-neutral-700" />
        </ReactFlow>
      </div>

      {error && <p className="mt-3 text-sm text-red-400">執行錯誤:{error}</p>}
      {result && (
        <div className="mt-3 animate-fade-in rounded-lg border border-white/5 bg-neutral-900/80 p-3 text-xs">
          <div className="mb-1.5 flex items-center gap-2">
            <span className="text-neutral-500">狀態</span>
            <span
              className={`badge border ${
                result.status === "ok"
                  ? "border-emerald-500/40 bg-emerald-500/15 text-emerald-300"
                  : "border-red-500/40 bg-red-500/15 text-red-300"
              }`}
            >
              {result.status}
            </span>
            {result.error && <span className="text-red-400">— {result.error}</span>}
          </div>
          <ol className="space-y-0.5">
            {result.steps.map((s) => (
              <li key={s.node_id} className="font-mono text-neutral-300">
                <span className="text-brand-400">{s.type}</span>{" "}
                <span className="text-neutral-500">[{s.node_id}]</span>: {JSON.stringify(s.summary)}
              </li>
            ))}
          </ol>
        </div>
      )}
    </section>
  );
}

function Spinner() {
  return (
    <svg className="h-3.5 w-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-90" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
    </svg>
  );
}
