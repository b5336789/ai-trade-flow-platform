import {
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
  type Connection,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
} from "@xyflow/react";
import { useCallback, useMemo, useRef, useState } from "react";
import type { NodeType, WorkflowGraph } from "@/lib/api";
import { defaultParams } from "./nodeCatalog";
import {
  createWorkflowHistory,
  pushWorkflowSnapshot,
  redoWorkflowSnapshot,
  resetWorkflowHistory,
  undoWorkflowSnapshot,
} from "./workflowHistory";

export interface TradeNodeData {
  nodeType: NodeType;
  params: Record<string, unknown>;
  savedStrategyId?: number;
  [k: string]: unknown;
}

type Snapshot = { nodes: Node[]; edges: Edge[] };
const HISTORY_LIMIT = 50;

const STARTER: Snapshot = {
  nodes: [
    { id: "data", type: "trade", position: { x: 0, y: 80 }, data: { nodeType: "data_source", params: defaultParams("data_source") } },
    { id: "strat", type: "trade", position: { x: 240, y: 80 }, data: { nodeType: "strategy", params: defaultParams("strategy") } },
    { id: "order", type: "trade", position: { x: 480, y: 80 }, data: { nodeType: "order", params: defaultParams("order") } },
    { id: "log", type: "trade", position: { x: 720, y: 80 }, data: { nodeType: "logger", params: defaultParams("logger") } },
  ],
  edges: [
    { id: "e1", source: "data", target: "strat" },
    { id: "e2", source: "strat", target: "order" },
    { id: "e3", source: "order", target: "log" },
  ],
};

export function useWorkflowState() {
  const [nodes, setNodes] = useState<Node[]>(STARTER.nodes);
  const [edges, setEdges] = useState<Edge[]>(STARTER.edges);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const idCounter = useRef(100);

  // history
  const history = useRef(createWorkflowHistory<Snapshot>(HISTORY_LIMIT));
  const [histTick, setHistTick] = useState(0); // re-render canUndo/canRedo

  const snapshot = useCallback(() => {
    pushWorkflowSnapshot(history.current, { nodes, edges });
    setHistTick((t) => t + 1);
  }, [nodes, edges]);

  const onNodesChange = useCallback((changes: NodeChange[]) => {
    // snapshot once when a drag finishes or when any node is removed (keyboard delete)
    if (changes.some((c) => (c.type === "position" && c.dragging === false) || c.type === "remove")) snapshot();
    setNodes((nds) => applyNodeChanges(changes, nds));
  }, [snapshot]);

  const onEdgesChange = useCallback((changes: EdgeChange[]) => {
    // snapshot before applying when any edge is removed (keyboard delete)
    if (changes.some((c) => c.type === "remove")) snapshot();
    setEdges((eds) => applyEdgeChanges(changes, eds));
  }, [snapshot]);

  const onConnect = useCallback((c: Connection) => {
    snapshot();
    setEdges((eds) => addEdge(c, eds));
  }, [snapshot]);

  const addNode = useCallback(
    (type: NodeType, position: { x: number; y: number }, init?: { params?: Record<string, unknown>; savedStrategyId?: number }) => {
      snapshot();
      const id = `n${idCounter.current++}`;
      const data: TradeNodeData = {
        nodeType: type,
        params: { ...defaultParams(type), ...(init?.params ?? {}) },
        ...(init?.savedStrategyId !== undefined ? { savedStrategyId: init.savedStrategyId } : {}),
      };
      setNodes((nds) => [...nds, { id, type: "trade", position, data }]);
      setSelectedId(id);
    },
    [snapshot],
  );

  const setParam = useCallback((id: string, key: string, value: unknown) => {
    snapshot();
    setNodes((nds) =>
      nds.map((n) =>
        n.id === id ? { ...n, data: { ...n.data, params: { ...(n.data as TradeNodeData).params, [key]: value } } } : n,
      ),
    );
  }, [snapshot]);

  const deleteNode = useCallback((id: string) => {
    snapshot();
    setNodes((nds) => nds.filter((n) => n.id !== id));
    setEdges((eds) => eds.filter((e) => e.source !== id && e.target !== id));
    setSelectedId((cur) => (cur === id ? null : cur));
  }, [snapshot]);

  const deleteSelection = useCallback(() => {
    snapshot();
    setNodes((nds) => nds.filter((n) => !n.selected));
    setEdges((eds) => eds.filter((e) => !e.selected));
    setSelectedId(null);
  }, [snapshot]);

  const duplicateNode = useCallback((id: string) => {
    const src = nodes.find((n) => n.id === id);
    if (!src) return;
    snapshot();
    const newId = `n${idCounter.current++}`;
    const d = src.data as TradeNodeData;
    setNodes((nds) => [
      ...nds,
      { id: newId, type: "trade", position: { x: src.position.x + 40, y: src.position.y + 40 }, data: { ...d, params: { ...d.params } } },
    ]);
    setSelectedId(newId);
  }, [nodes, snapshot]);

  const undo = useCallback(() => {
    const prev = undoWorkflowSnapshot(history.current, { nodes, edges });
    if (!prev) return;
    setNodes(prev.nodes);
    setEdges(prev.edges);
    setHistTick((t) => t + 1);
  }, [nodes, edges]);

  const redo = useCallback(() => {
    const next = redoWorkflowSnapshot(history.current, { nodes, edges });
    if (!next) return;
    setNodes(next.nodes);
    setEdges(next.edges);
    setHistTick((t) => t + 1);
  }, [nodes, edges]);

  const buildGraph = useCallback((): WorkflowGraph => ({
    nodes: nodes.map((n) => ({
      id: n.id,
      type: (n.data as TradeNodeData).nodeType,
      params: (n.data as TradeNodeData).params,
      position: { x: n.position.x, y: n.position.y },
    })),
    edges: edges.map((e) => ({ source: e.source, target: e.target })),
  }), [nodes, edges]);

  const setGraph = useCallback((g: WorkflowGraph) => {
    resetWorkflowHistory(history.current);
    setHistTick((t) => t + 1);
    setNodes(g.nodes.map((n, i) => ({
      id: n.id,
      type: "trade",
      position: n.position ?? { x: (i % 4) * 240, y: Math.floor(i / 4) * 160 + 80 },
      data: { nodeType: n.type, params: n.params },
    })));
    setEdges(g.edges.map((e, i) => ({ id: `e${i}`, source: e.source, target: e.target })));
    setSelectedId(null);
  }, []);

  const canUndo = useMemo(() => { void histTick; return history.current.past.length > 0; }, [histTick]);
  const canRedo = useMemo(() => { void histTick; return history.current.future.length > 0; }, [histTick]);

  return {
    nodes, edges, onNodesChange, onEdgesChange, onConnect,
    addNode, setParam, deleteNode, deleteSelection, duplicateNode,
    selectedId, setSelectedId, undo, redo, canUndo, canRedo, buildGraph, setGraph,
  };
}
