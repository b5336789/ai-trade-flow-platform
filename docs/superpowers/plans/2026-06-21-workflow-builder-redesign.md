# Workflow Builder Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the workflow editor as the three-pane builder DESIGN.md specifies (palette → canvas → inspector), fixing in-node param editing, random node placement, awkward connect/delete, and missing validation.

**Architecture:** Replace the `WorkflowBuilder.tsx` monolith with focused files: a `nodeCatalog` single-source-of-truth for node metadata, a pure `validateGraph`, a `useWorkflowState` hook (state + undo/redo + mutations), and four panes (Toolbar, Palette, Canvas, Inspector) wired by a thin orchestrator. Params move to the Inspector; node cards become read-only summaries.

**Tech Stack:** Next.js 14 App Router, TypeScript, React, `@xyflow/react` (React Flow), `@tanstack/react-query` (config fetch), Tailwind (CSS-var tokens).

## Global Constraints

- **No frontend test runner** (CI = `npm run build` only). Per-task verification is `npx tsc --noEmit` and, for tasks touching components/JSX, `npm run build`. The final task adds a manual drive. Do NOT add a test runner.
- **DESIGN.md is the visual authority.** Three-pane layout, node category colors, node anatomy, edge/run states, toolbar contents, and RWD breakpoints follow DESIGN.md ("Workflow Builder (交易室 canvas)", lines 169–221) verbatim. Flag any deviation; there should be none.
- **Electric-cyan accent (`--accent` / `--c-strat`) is reserved for AI/automation only** — Run button + AI Signal node. Other categories use their own hue.
- **Directional color** uses `--up`/`--down` tokens; never hardcode green-as-gain.
- All work on branch `feature/workflow-builder-redesign`; never commit to `main`. Commit messages end with:
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- Run all commands from `frontend/`.
- Surgical: do not touch backend or unrelated frontend code.

## File map

| File | Created in | Responsibility |
|------|-----------|----------------|
| `app/globals.css`, `tailwind.config.ts` | Task 1 | add `--c-data/--c-strat/--c-logic/--c-order/--c-out` tokens + Tailwind color mappings |
| `components/workflow/nodeCatalog.ts` | Task 1 | per-`NodeType` metadata: category, colorVar, title, ports, param schema, summary |
| `components/workflow/validateGraph.ts` | Task 2 | pure `validateGraph(graph) => {valid, errors}` |
| `components/workflow/useWorkflowState.ts` | Task 3 | nodes/edges + undo/redo + add/drop/delete/duplicate/setParam/connect + buildGraph/setGraph |
| `components/workflow/TradeNode.tsx` | Task 4 | read-only node card (anatomy per DESIGN.md) |
| `components/workflow/Palette.tsx` | Task 5 | left pane: search + category groups + draggable chips + saved strategies |
| `components/workflow/Inspector.tsx` | Task 6 | right pane: selected node fields + 複製/刪除 |
| `components/workflow/Canvas.tsx` | Task 7 | center: ReactFlow + Background + MiniMap + Legend + Controls + drop |
| `components/workflow/Toolbar.tsx` | Task 8 | top bar: mode chip, undo/redo, zoom, validation, Save, Run |
| `components/workflow/WorkflowBuilder.tsx` | Task 8 | orchestrator (rewritten): provider + three-pane + result panel |
| (RWD in the above) | Task 9 | tablet slide-over + icon strip, mobile bottom sheets |

---

### Task 1: Tokens + `nodeCatalog.ts`

**Files:**
- Modify: `frontend/app/globals.css` (`:root` block, after the `--warning/--error/--live` line)
- Modify: `frontend/tailwind.config.ts` (`theme.extend.colors`)
- Create: `frontend/components/workflow/nodeCatalog.ts`

**Interfaces:**
- Produces:
  - CSS vars `--c-data #8A9099`, `--c-strat #22D3EE`, `--c-logic #FBBF24`, `--c-order #34D399`, `--c-out #A78BFA`; Tailwind colors `"c-data" … "c-out"`.
  - `type NodeCategory = "data" | "strategy" | "logic" | "order" | "output"`
  - `interface ParamField { key: string; label: string; kind: "number" | "text" | "select"; options?: string[]; default: unknown }`
  - `interface NodeMeta { category: NodeCategory; colorVar: string; title: string; hasInput: boolean; hasOutput: boolean; params: ParamField[]; summaryKeys: string[] }`
  - `const NODE_CATALOG: Record<NodeType, NodeMeta>`
  - `const CATEGORY_COLOR: Record<NodeCategory, string>` (maps to `var(--c-*)`)
  - `function defaultParams(t: NodeType): Record<string, unknown>`
  - `function summaryText(t: NodeType, params: Record<string, unknown>): string`

- [ ] **Step 1: Add the CSS tokens**

In `frontend/app/globals.css`, the `:root` block currently ends a line with:
```css
  --warning: #FBBF24; --error: #EF4444; --live: #FB7185;
```
Add immediately after it (inside `:root`):
```css
  --c-data: #8A9099; --c-strat: #22D3EE; --c-logic: #FBBF24; --c-order: #34D399; --c-out: #A78BFA;
```

- [ ] **Step 2: Map them in Tailwind**

In `frontend/tailwind.config.ts`, inside `theme.extend.colors`, after the `warning/error/live` line add:
```ts
        "c-data": "var(--c-data)", "c-strat": "var(--c-strat)", "c-logic": "var(--c-logic)",
        "c-order": "var(--c-order)", "c-out": "var(--c-out)",
```

- [ ] **Step 3: Write `nodeCatalog.ts`**

Create `frontend/components/workflow/nodeCatalog.ts`:
```ts
import type { NodeType } from "@/lib/api";

export type NodeCategory = "data" | "strategy" | "logic" | "order" | "output";

export interface ParamField {
  key: string;
  label: string;
  kind: "number" | "text" | "select";
  options?: string[];
  default: unknown;
}

export interface NodeMeta {
  category: NodeCategory;
  colorVar: string;
  title: string;
  hasInput: boolean;
  hasOutput: boolean;
  params: ParamField[];
  summaryKeys: string[];
}

export const CATEGORY_COLOR: Record<NodeCategory, string> = {
  data: "var(--c-data)",
  strategy: "var(--c-strat)",
  logic: "var(--c-logic)",
  order: "var(--c-order)",
  output: "var(--c-out)",
};

export const CATEGORY_LABEL: Record<NodeCategory, string> = {
  data: "資料 Data",
  strategy: "策略 Strategy",
  logic: "邏輯 Logic",
  order: "下單 Order",
  output: "輸出 Output",
};

const OPERATORS = [">", ">=", "<", "<=", "==", "!="];

export const NODE_CATALOG: Record<NodeType, NodeMeta> = {
  data_source: {
    category: "data", colorVar: CATEGORY_COLOR.data, title: "Data Source",
    hasInput: false, hasOutput: true,
    params: [
      { key: "symbol", label: "symbol", kind: "text", default: "BTC/USDT" },
      { key: "timeframe", label: "timeframe", kind: "text", default: "1h" },
      { key: "limit", label: "limit", kind: "number", default: 100 },
    ],
    summaryKeys: ["symbol", "timeframe"],
  },
  strategy: {
    category: "strategy", colorVar: CATEGORY_COLOR.strategy, title: "Strategy",
    hasInput: true, hasOutput: true,
    // strategy params beyond `name` are appended dynamically by the Inspector from STRATEGY_PARAMS[name].
    params: [{ key: "name", label: "name", kind: "select", options: [], default: "ma_cross" }],
    summaryKeys: ["name"],
  },
  ai_signal: {
    category: "strategy", colorVar: CATEGORY_COLOR.strategy, title: "AI Signal",
    hasInput: true, hasOutput: true,
    params: [{ key: "model", label: "model (optional)", kind: "text", default: "" }],
    summaryKeys: [],
  },
  risk_exit: {
    category: "order", colorVar: CATEGORY_COLOR.order, title: "Risk Exit (SL/TP)",
    hasInput: true, hasOutput: true,
    params: [
      { key: "stop_loss_pct", label: "stop_loss_pct", kind: "number", default: 5 },
      { key: "take_profit_pct", label: "take_profit_pct", kind: "number", default: 10 },
    ],
    summaryKeys: ["stop_loss_pct", "take_profit_pct"],
  },
  order: {
    category: "order", colorVar: CATEGORY_COLOR.order, title: "Order",
    hasInput: true, hasOutput: false,
    params: [{ key: "quantity", label: "quantity", kind: "number", default: 0.01 }],
    summaryKeys: ["quantity"],
  },
  logger: {
    category: "output", colorVar: CATEGORY_COLOR.output, title: "Logger",
    hasInput: true, hasOutput: false,
    params: [],
    summaryKeys: [],
  },
  condition: {
    category: "logic", colorVar: CATEGORY_COLOR.logic, title: "Condition",
    hasInput: true, hasOutput: true,
    params: [
      { key: "source", label: "source", kind: "text", default: "close" },
      { key: "operator", label: "operator", kind: "select", options: OPERATORS, default: ">" },
      { key: "value", label: "value", kind: "number", default: 0 },
    ],
    summaryKeys: ["source", "operator", "value"],
  },
  combine: {
    category: "logic", colorVar: CATEGORY_COLOR.logic, title: "Combine",
    hasInput: true, hasOutput: true,
    params: [{ key: "mode", label: "mode", kind: "select", options: ["AND", "OR", "weighted"], default: "AND" }],
    summaryKeys: ["mode"],
  },
  branch: {
    category: "logic", colorVar: CATEGORY_COLOR.logic, title: "Branch",
    hasInput: true, hasOutput: true,
    params: [
      { key: "source", label: "source", kind: "text", default: "close" },
      { key: "operator", label: "operator", kind: "select", options: OPERATORS, default: ">" },
      { key: "value", label: "value", kind: "number", default: 0 },
    ],
    summaryKeys: ["source", "operator", "value"],
  },
};

export function defaultParams(t: NodeType): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const f of NODE_CATALOG[t].params) out[f.key] = f.default;
  return out;
}

export function summaryText(t: NodeType, params: Record<string, unknown>): string {
  const keys = NODE_CATALOG[t].summaryKeys;
  if (keys.length === 0) return "";
  return keys.map((k) => params[k]).filter((v) => v !== undefined && v !== "").join(" ");
}
```

- [ ] **Step 4: Verify type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/app/globals.css frontend/tailwind.config.ts frontend/components/workflow/nodeCatalog.ts
git commit -m "feat(workflow): node category tokens + nodeCatalog single-source metadata

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `validateGraph.ts` (pure)

**Files:**
- Create: `frontend/components/workflow/validateGraph.ts`

**Interfaces:**
- Consumes: `WorkflowGraph` (`lib/api`), `NODE_CATALOG` (Task 1).
- Produces: `interface ValidationResult { valid: boolean; errors: string[] }`; `function validateGraph(graph: WorkflowGraph): ValidationResult`.

- [ ] **Step 1: Write `validateGraph.ts`**

Create `frontend/components/workflow/validateGraph.ts`:
```ts
import type { WorkflowGraph } from "@/lib/api";
import { NODE_CATALOG } from "./nodeCatalog";

export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

// Mirrors backend app/workflow/engine.py structural checks: duplicate ids, cycles,
// and required-input nodes with no incoming edge. A graph valid here will not be
// rejected by the engine for structure.
export function validateGraph(graph: WorkflowGraph): ValidationResult {
  const errors: string[] = [];
  const ids = graph.nodes.map((n) => n.id);

  // duplicate ids
  const dupes = ids.filter((id, i) => ids.indexOf(id) !== i);
  if (dupes.length) errors.push(`重複節點 id: ${[...new Set(dupes)].join(", ")}`);

  // required-input nodes with no incoming edge
  const incoming = new Map<string, number>();
  for (const id of ids) incoming.set(id, 0);
  for (const e of graph.edges) incoming.set(e.target, (incoming.get(e.target) ?? 0) + 1);
  for (const n of graph.nodes) {
    if (NODE_CATALOG[n.type].hasInput && (incoming.get(n.id) ?? 0) === 0) {
      errors.push(`節點 ${n.id} (${NODE_CATALOG[n.type].title}) 缺少輸入`);
    }
  }

  // cycle detection (DFS over adjacency)
  const adj = new Map<string, string[]>();
  for (const id of ids) adj.set(id, []);
  for (const e of graph.edges) adj.get(e.source)?.push(e.target);
  const state = new Map<string, 0 | 1 | 2>(); // 0=unseen,1=in-stack,2=done
  let hasCycle = false;
  const visit = (u: string) => {
    state.set(u, 1);
    for (const v of adj.get(u) ?? []) {
      const s = state.get(v) ?? 0;
      if (s === 1) hasCycle = true;
      else if (s === 0) visit(v);
    }
    state.set(u, 2);
  };
  for (const id of ids) if ((state.get(id) ?? 0) === 0) visit(id);
  if (hasCycle) errors.push("流程有循環 (cycle)");

  return { valid: errors.length === 0, errors };
}
```

- [ ] **Step 2: Verify type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/workflow/validateGraph.ts
git commit -m "feat(workflow): pure validateGraph (dupes, cycles, missing input)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: `useWorkflowState.ts`

**Files:**
- Create: `frontend/components/workflow/useWorkflowState.ts`

**Interfaces:**
- Consumes: `@xyflow/react` hooks/types, `NodeType`/`WorkflowGraph` (`lib/api`), `defaultParams` (Task 1).
- Produces:
  - `interface TradeNodeData { nodeType: NodeType; params: Record<string, unknown>; savedStrategyId?: number; [k: string]: unknown }`
  - `interface UseWorkflow { nodes; edges; onNodesChange; onEdgesChange; onConnect; addNode(type: NodeType, position: {x:number;y:number}, init?: {params?: Record<string,unknown>; savedStrategyId?: number}): void; setParam(id: string, key: string, value: unknown): void; deleteNode(id: string): void; deleteSelection(): void; duplicateNode(id: string): void; selectedId: string | null; setSelectedId(id: string | null): void; undo(): void; redo(): void; canUndo: boolean; canRedo: boolean; buildGraph(): WorkflowGraph; setGraph(g: WorkflowGraph): void }`
  - `function useWorkflowState(): UseWorkflow`

- [ ] **Step 1: Write `useWorkflowState.ts`**

Create `frontend/components/workflow/useWorkflowState.ts`:
```ts
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
  const past = useRef<Snapshot[]>([]);
  const future = useRef<Snapshot[]>([]);
  const [histTick, setHistTick] = useState(0); // re-render canUndo/canRedo

  const snapshot = useCallback(() => {
    past.current.push({ nodes, edges });
    if (past.current.length > HISTORY_LIMIT) past.current.shift();
    future.current = [];
    setHistTick((t) => t + 1);
  }, [nodes, edges]);

  const onNodesChange = useCallback((changes: NodeChange[]) => {
    // snapshot once when a drag finishes (position change with dragging=false)
    if (changes.some((c) => c.type === "position" && c.dragging === false)) snapshot();
    setNodes((nds) => applyNodeChanges(changes, nds));
  }, [snapshot]);

  const onEdgesChange = useCallback((changes: EdgeChange[]) => {
    setEdges((eds) => applyEdgeChanges(changes, eds));
  }, []);

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
    const prev = past.current.pop();
    if (!prev) return;
    future.current.push({ nodes, edges });
    setNodes(prev.nodes);
    setEdges(prev.edges);
    setHistTick((t) => t + 1);
  }, [nodes, edges]);

  const redo = useCallback(() => {
    const next = future.current.pop();
    if (!next) return;
    past.current.push({ nodes, edges });
    setNodes(next.nodes);
    setEdges(next.edges);
    setHistTick((t) => t + 1);
  }, [nodes, edges]);

  const buildGraph = useCallback((): WorkflowGraph => ({
    nodes: nodes.map((n) => ({ id: n.id, type: (n.data as TradeNodeData).nodeType, params: (n.data as TradeNodeData).params })),
    edges: edges.map((e) => ({ source: e.source, target: e.target })),
  }), [nodes, edges]);

  const setGraph = useCallback((g: WorkflowGraph) => {
    snapshot();
    setNodes(g.nodes.map((n, i) => ({
      id: n.id, type: "trade", position: { x: (i % 4) * 240, y: Math.floor(i / 4) * 160 + 80 },
      data: { nodeType: n.type, params: n.params },
    })));
    setEdges(g.edges.map((e, i) => ({ id: `e${i}`, source: e.source, target: e.target })));
    setSelectedId(null);
  }, [snapshot]);

  const canUndo = useMemo(() => { void histTick; return past.current.length > 0; }, [histTick]);
  const canRedo = useMemo(() => { void histTick; return future.current.length > 0; }, [histTick]);

  return {
    nodes, edges, onNodesChange, onEdgesChange, onConnect,
    addNode, setParam, deleteNode, deleteSelection, duplicateNode,
    selectedId, setSelectedId, undo, redo, canUndo, canRedo, buildGraph, setGraph,
  };
}
```

- [ ] **Step 2: Verify type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/workflow/useWorkflowState.ts
git commit -m "feat(workflow): useWorkflowState hook (state, mutations, undo/redo)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: `TradeNode.tsx` (read-only card)

**Files:**
- Modify (rewrite): `frontend/components/workflow/TradeNode.tsx`

**Interfaces:**
- Consumes: `NodeProps`/`Handle`/`Position` (`@xyflow/react`), `NODE_CATALOG`/`summaryText`/`CATEGORY_LABEL` (Task 1), `TradeNodeData` (Task 3).
- Produces: `export function TradeNode(props: NodeProps)` for `nodeTypes={{ trade: TradeNode }}`.

Visual anatomy per DESIGN.md §"Node anatomy": ~158px card; header = 3px category-colored left bar + color chip + name + tiny category tag; body = 1–2 key params in mono; round ports ringed in category color (input left, output right); selected node gets 2px cyan (`--accent`) outline.

- [ ] **Step 1: Rewrite `TradeNode.tsx`**

Replace the entire file with:
```tsx
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
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: type-check clean; build succeeds. (The old `WorkflowBuilder.tsx` still imports the old `TradeNodeData` shape — it imported it from `./TradeNode`. Since `TradeNodeData` now lives in `useWorkflowState`, update the import in `WorkflowBuilder.tsx` to `import type { TradeNodeData } from "./useWorkflowState"` so the build stays green; do not otherwise change `WorkflowBuilder.tsx` in this task.)

- [ ] **Step 3: Commit**

```bash
git add frontend/components/workflow/TradeNode.tsx frontend/components/workflow/WorkflowBuilder.tsx
git commit -m "feat(workflow): read-only TradeNode card per DESIGN.md anatomy

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: `Palette.tsx`

**Files:**
- Create: `frontend/components/workflow/Palette.tsx`

**Interfaces:**
- Consumes: `NODE_CATALOG`/`CATEGORY_COLOR`/`CATEGORY_LABEL`/`NodeCategory` (Task 1), `api`/`StrategyListItem`/`NodeType` (`lib/api`), `@tanstack/react-query`.
- Produces: `export function Palette()`. Chips are `draggable`; `onDragStart` sets `dataTransfer.setData("application/reactflow", JSON.stringify(payload))` where `payload` is `{ type: NodeType }` for catalog nodes or `{ type: "strategy", savedStrategyId: number, name: string }` for saved strategies. Canvas (Task 7) reads this key.

- [ ] **Step 1: Write `Palette.tsx`**

Create `frontend/components/workflow/Palette.tsx`:
```tsx
"use client";

import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { api, type NodeType } from "@/lib/api";
import { CATEGORY_COLOR, CATEGORY_LABEL, NODE_CATALOG, type NodeCategory } from "./nodeCatalog";

const CATEGORY_ORDER: NodeCategory[] = ["data", "strategy", "logic", "order", "output"];

type ChipPayload = { type: NodeType } | { type: "strategy"; savedStrategyId: number; name: string };

function onChipDragStart(e: React.DragEvent, payload: ChipPayload) {
  e.dataTransfer.setData("application/reactflow", JSON.stringify(payload));
  e.dataTransfer.effectAllowed = "move";
}

export function Palette() {
  const [q, setQ] = useState("");
  const saved = useQuery({ queryKey: ["savedStrategies"], queryFn: api.listSavedStrategies, retry: false });

  const byCategory = useMemo(() => {
    const groups: Record<NodeCategory, NodeType[]> = { data: [], strategy: [], logic: [], order: [], output: [] };
    (Object.keys(NODE_CATALOG) as NodeType[]).forEach((t) => groups[NODE_CATALOG[t].category].push(t));
    return groups;
  }, []);

  const match = (label: string) => label.toLowerCase().includes(q.toLowerCase());

  return (
    <aside className="flex h-full w-[200px] shrink-0 flex-col gap-2 overflow-y-auto border-r border-border bg-surface-1 p-2">
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="搜尋節點…"
        className="rounded-md bg-surface-2 px-2 py-1 text-xs text-text"
      />
      {CATEGORY_ORDER.map((cat) => {
        const items = byCategory[cat].filter((t) => match(NODE_CATALOG[t].title));
        const savedItems = cat === "strategy" ? (saved.data ?? []).filter((s) => match(s.name)) : [];
        if (items.length === 0 && savedItems.length === 0) return null;
        return (
          <div key={cat}>
            <div className="mb-1 flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-faint">
              <span className="inline-block h-2 w-2 rounded-full" style={{ background: CATEGORY_COLOR[cat] }} />
              {CATEGORY_LABEL[cat]}
            </div>
            <div className="flex flex-col gap-1">
              {items.map((t) => (
                <button
                  key={t}
                  draggable
                  onDragStart={(e) => onChipDragStart(e, { type: t })}
                  className="cursor-grab rounded-md border border-border bg-surface-2 px-2 py-1 text-left text-xs hover:bg-surface-3"
                  style={{ borderLeft: `3px solid ${CATEGORY_COLOR[cat]}` }}
                >
                  {NODE_CATALOG[t].title}
                </button>
              ))}
              {cat === "strategy" && saved.isError && (
                <div className="text-[10px] text-error">無法載入已存策略</div>
              )}
              {savedItems.map((s) => (
                <button
                  key={`saved-${s.id}`}
                  draggable
                  onDragStart={(e) => onChipDragStart(e, { type: "strategy", savedStrategyId: s.id, name: s.name })}
                  className="cursor-grab rounded-md border border-border bg-surface-2 px-2 py-1 text-left text-xs hover:bg-surface-3"
                  style={{ borderLeft: `3px solid ${CATEGORY_COLOR.strategy}` }}
                  title={s.description}
                >
                  ★ {s.name}
                </button>
              ))}
            </div>
          </div>
        );
      })}
    </aside>
  );
}
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/workflow/Palette.tsx
git commit -m "feat(workflow): draggable node palette with saved strategies

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: `Inspector.tsx`

**Files:**
- Create: `frontend/components/workflow/Inspector.tsx`

**Interfaces:**
- Consumes: `NODE_CATALOG`/`CATEGORY_LABEL`/`CATEGORY_COLOR`/`ParamField` (Task 1), `TradeNodeData` (Task 3), `STRATEGY_NAMES`/`STRATEGY_PARAMS` (`lib/strategies`), `Node` type (`@xyflow/react`).
- Produces: `export function Inspector(props: { node: Node | null; setParam: (id, key, value) => void; onDelete: (id) => void; onDuplicate: (id) => void })`.

Behavior: render the selected node's category label + title, then a field per `NODE_CATALOG[type].params`. Special cases: `strategy` appends a numeric field per `STRATEGY_PARAMS[name]` (defaulting from the schema) and the `name` select uses `STRATEGY_NAMES`; `combine` shows an extra `bias` text field only when `mode === "OR"`. Footer: 複製 / 刪除 (delete styled `--down`).

- [ ] **Step 1: Write `Inspector.tsx`**

Create `frontend/components/workflow/Inspector.tsx`:
```tsx
"use client";

import type { Node } from "@xyflow/react";
import { STRATEGY_NAMES, STRATEGY_PARAMS } from "@/lib/strategies";
import { CATEGORY_COLOR, CATEGORY_LABEL, NODE_CATALOG, type ParamField } from "./nodeCatalog";
import type { TradeNodeData } from "./useWorkflowState";

function FieldInput({ field, value, onChange }: { field: ParamField; value: unknown; onChange: (v: unknown) => void }) {
  if (field.kind === "select") {
    return (
      <select
        value={String(value ?? field.default)}
        onChange={(e) => onChange(e.target.value)}
        className="mt-0.5 w-full rounded-sm bg-surface-2 px-1.5 py-1 text-xs text-text"
      >
        {(field.options ?? []).map((o) => (
          <option key={o} value={o}>{o}</option>
        ))}
      </select>
    );
  }
  return (
    <input
      type={field.kind === "number" ? "number" : "text"}
      value={String(value ?? "")}
      onChange={(e) => onChange(field.kind === "number" ? Number(e.target.value) : e.target.value)}
      className="mt-0.5 w-full rounded-sm bg-surface-2 px-1.5 py-1 text-xs text-text"
    />
  );
}

export function Inspector({
  node,
  setParam,
  onDelete,
  onDuplicate,
}: {
  node: Node | null;
  setParam: (id: string, key: string, value: unknown) => void;
  onDelete: (id: string) => void;
  onDuplicate: (id: string) => void;
}) {
  if (!node) {
    return (
      <aside className="w-64 shrink-0 border-l border-border bg-surface-1 p-3 text-xs text-faint">
        選擇一個節點以編輯參數。
      </aside>
    );
  }
  const d = node.data as TradeNodeData;
  const meta = NODE_CATALOG[d.nodeType];
  const set = (key: string, value: unknown) => setParam(node.id, key, value);

  // strategy: name select (from STRATEGY_NAMES) + dynamic numeric params from STRATEGY_PARAMS[name]
  const strategyName = d.nodeType === "strategy" ? String(d.params.name ?? "ma_cross") : "";
  const strategyParamKeys = d.nodeType === "strategy" ? Object.keys(STRATEGY_PARAMS[strategyName] ?? {}) : [];

  return (
    <aside className="flex w-64 shrink-0 flex-col border-l border-border bg-surface-1">
      <div className="border-b border-border p-3">
        <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-faint">
          <span className="inline-block h-2 w-2 rounded-full" style={{ background: CATEGORY_COLOR[meta.category] }} />
          {CATEGORY_LABEL[meta.category]}
        </div>
        <div className="mt-0.5 font-display text-sm font-semibold">{meta.title}</div>
      </div>

      <div className="flex-1 space-y-2 overflow-y-auto p-3">
        {meta.params.map((f) => {
          if (d.nodeType === "strategy" && f.key === "name") {
            return (
              <label key="name" className="block text-[10px] text-muted">
                name
                <select
                  value={strategyName}
                  onChange={(e) => set("name", e.target.value)}
                  className="mt-0.5 w-full rounded-sm bg-surface-2 px-1.5 py-1 text-xs text-text"
                >
                  {STRATEGY_NAMES.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </label>
            );
          }
          return (
            <label key={f.key} className="block text-[10px] text-muted">
              {f.label}
              <FieldInput field={f} value={d.params[f.key]} onChange={(v) => set(f.key, v)} />
            </label>
          );
        })}

        {strategyParamKeys.map((key) => (
          <label key={key} className="block text-[10px] text-muted">
            {key}
            <input
              type="number"
              value={String(d.params[key] ?? STRATEGY_PARAMS[strategyName][key])}
              onChange={(e) => set(key, Number(e.target.value))}
              className="mt-0.5 w-full rounded-sm bg-surface-2 px-1.5 py-1 text-xs text-text"
            />
          </label>
        ))}

        {d.nodeType === "combine" && String(d.params.mode ?? "AND") === "OR" && (
          <label className="block text-[10px] text-muted">
            bias (buy/sell)
            <input
              value={String(d.params.bias ?? "")}
              onChange={(e) => set("bias", e.target.value)}
              className="mt-0.5 w-full rounded-sm bg-surface-2 px-1.5 py-1 text-xs text-text"
            />
          </label>
        )}
      </div>

      <div className="flex gap-2 border-t border-border p-3">
        <button onClick={() => onDuplicate(node.id)} className="flex-1 rounded-md bg-surface-2 px-2 py-1 text-xs hover:bg-surface-3">複製</button>
        <button onClick={() => onDelete(node.id)} className="flex-1 rounded-md bg-down/15 px-2 py-1 text-xs text-down hover:bg-down/25">刪除</button>
      </div>
    </aside>
  );
}
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/workflow/Inspector.tsx
git commit -m "feat(workflow): inspector pane for node param editing + delete/duplicate

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: `Canvas.tsx`

**Files:**
- Create: `frontend/components/workflow/Canvas.tsx`

**Interfaces:**
- Consumes: `@xyflow/react` (`ReactFlow`, `Background`, `BackgroundVariant`, `Controls`, `MiniMap`, `Panel`, `useReactFlow`), `TradeNode` (Task 4), `NODE_CATALOG`/`CATEGORY_COLOR`/`CATEGORY_LABEL` (Task 1), `useWorkflowState` return (Task 3), `NodeType` (`lib/api`).
- Produces: `export function Canvas(props: { wf: ReturnType<typeof useWorkflowState>; onInit?: (i: ReactFlowInstance) => void })`. Must be rendered inside a `ReactFlowProvider` (provided by Task 8). Reads the `"application/reactflow"` drag payload (Task 5) on drop and calls `wf.addNode`. Calls `wf.setSelectedId` on node click / pane click. Forwards `onInit` to `<ReactFlow>` so the Toolbar (Task 8) can drive zoom.

- [ ] **Step 1: Write `Canvas.tsx`**

Create `frontend/components/workflow/Canvas.tsx`:
```tsx
"use client";

import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  Panel,
  ReactFlow,
  useReactFlow,
  type Node,
  type ReactFlowInstance,
} from "@xyflow/react";
import { useCallback, useMemo } from "react";
import type { NodeType } from "@/lib/api";
import { CATEGORY_COLOR, CATEGORY_LABEL, NODE_CATALOG, type NodeCategory } from "./nodeCatalog";
import { TradeNode } from "./TradeNode";
import type { TradeNodeData, useWorkflowState } from "./useWorkflowState";

const CATS: NodeCategory[] = ["data", "strategy", "logic", "order", "output"];

export function Canvas({ wf, onInit }: { wf: ReturnType<typeof useWorkflowState>; onInit?: (i: ReactFlowInstance) => void }) {
  const nodeTypes = useMemo(() => ({ trade: TradeNode }), []);
  const { screenToFlowPosition } = useReactFlow();

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const raw = e.dataTransfer.getData("application/reactflow");
      if (!raw) return;
      const payload = JSON.parse(raw) as { type: NodeType; savedStrategyId?: number; name?: string };
      const position = screenToFlowPosition({ x: e.clientX, y: e.clientY });
      if (payload.savedStrategyId !== undefined) {
        wf.addNode("strategy", position, { savedStrategyId: payload.savedStrategyId, params: { name: payload.name } });
      } else {
        wf.addNode(payload.type, position);
      }
    },
    [screenToFlowPosition, wf],
  );

  const minimapColor = useCallback(
    (n: Node) => NODE_CATALOG[(n.data as TradeNodeData).nodeType].colorVar,
    [],
  );

  return (
    <div className="relative h-full w-full" onDrop={onDrop} onDragOver={onDragOver}>
      <ReactFlow
        nodes={wf.nodes}
        edges={wf.edges}
        nodeTypes={nodeTypes}
        onNodesChange={wf.onNodesChange}
        onEdgesChange={wf.onEdgesChange}
        onConnect={wf.onConnect}
        onNodeClick={(_, n) => wf.setSelectedId(n.id)}
        onPaneClick={() => wf.setSelectedId(null)}
        onInit={onInit}
        deleteKeyCode={["Backspace", "Delete"]}
        onNodesDelete={() => wf.setSelectedId(null)}
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={22} />
        <Controls />
        <MiniMap nodeColor={minimapColor} pannable zoomable className="!bg-surface-2" />
        <Panel position="bottom-left">
          <div className="flex flex-wrap gap-2 rounded-md border border-border bg-surface-1/90 px-2 py-1 text-[10px]">
            {CATS.map((c) => (
              <span key={c} className="flex items-center gap-1 text-muted">
                <span className="inline-block h-2 w-2 rounded-full" style={{ background: CATEGORY_COLOR[c] }} />
                {CATEGORY_LABEL[c]}
              </span>
            ))}
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
}
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: clean. (`useReactFlow` requires a provider at runtime; the build only type-checks, so it passes here. Provider is added in Task 8.)

- [ ] **Step 3: Commit**

```bash
git add frontend/components/workflow/Canvas.tsx
git commit -m "feat(workflow): canvas with minimap, legend, drop-to-create

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: `Toolbar.tsx` + `WorkflowBuilder.tsx` orchestrator (desktop)

**Files:**
- Create: `frontend/components/workflow/Toolbar.tsx`
- Modify (full rewrite): `frontend/components/workflow/WorkflowBuilder.tsx`

**Interfaces:**
- `Toolbar` consumes: `ValidationResult` (Task 2), callbacks. Produces: `export function Toolbar(props: { mode: string; valid: ValidationResult; nodeCount: number; edgeCount: number; canUndo: boolean; canRedo: boolean; onUndo: () => void; onRedo: () => void; onZoomIn: () => void; onZoomOut: () => void; onFit: () => void; name: string; onName: (v: string) => void; onSave: () => void; onRun: () => void; running: boolean })`.
- `WorkflowBuilder` wires `useWorkflowState`, `validateGraph` (useMemo), `api.config`, save/run, the `ReactFlowProvider`, and the three panes. Zoom handlers come from a `useReactFlow` instance obtained via `onInit` (stored in state) so the Toolbar (outside the flow) can drive zoom.

- [ ] **Step 1: Write `Toolbar.tsx`**

Create `frontend/components/workflow/Toolbar.tsx`:
```tsx
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
```

- [ ] **Step 2: Rewrite `WorkflowBuilder.tsx`**

Replace the entire file with:
```tsx
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

  const graph = wf.buildGraph();
  const valid = useMemo(() => validateGraph(graph), [graph]);
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
              <li key={s.node_id}>
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
```

Zoom is wired via the `onInit` prop added to `Canvas` in Task 7: `<Canvas wf={wf} onInit={setRf} />` stores the `ReactFlowInstance` so the Toolbar (rendered outside the flow) can call `rf.zoomIn()/zoomOut()/fitView()`. No extra wrapper component is needed.

- [ ] **Step 3: Update the page (no change needed) and verify build**

`app/(rooms)/trading-room/workflow/page.tsx` already renders `<WorkflowBuilder />` — no change.

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: clean.

- [ ] **Step 4: Manual drive (the real gate)**

Start backend (`cd backend && uvicorn app.main:app --port 8000`) and `cd frontend && npm run dev`; open `http://localhost:3000/trading-room/workflow` and confirm:
- Drag each category chip from the palette → node lands at the cursor (not random).
- Click a node → inspector shows its fields → edit a param → node card summary updates.
- Drag output→input ports to connect; select an edge/node and press Delete → removed; inspector 刪除/複製 work.
- Undo/redo buttons reflect history; zoom −/fit/＋ work; minimap + legend show; nodes colored by category; AI Signal + Run are the only cyan.
- Validation: delete the edge into `strategy` → toolbar turns red "缺少輸入"; reconnect → green "✓ 有效 · N nodes · M edges".
- Save → success message; Run → result panel renders steps.

Record the result (pass/fail per item) in the task report.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/workflow/Toolbar.tsx frontend/components/workflow/WorkflowBuilder.tsx frontend/components/workflow/Canvas.tsx
git commit -m "feat(workflow): toolbar + three-pane orchestrator (desktop)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: Responsive (tablet + mobile)

**Files:**
- Modify: `frontend/components/workflow/WorkflowBuilder.tsx` (layout), `frontend/components/workflow/Palette.tsx` (icon strip), `frontend/components/workflow/Inspector.tsx` (slide-over / sheet shell)

**Interfaces:**
- Consumes: existing pane components. No new exported types. Uses Tailwind responsive prefixes (`md:`, `xl:`) and a `selectedNode != null` trigger to reveal the inspector on tablet/mobile.

Behavior per DESIGN.md §RWD:
- **Desktop ≥1280 (`xl:`):** three panes side by side (current layout).
- **Tablet 768–1279 (`md:`):** palette becomes a narrow icon strip; inspector is hidden inline and shown as a right slide-over only when a node is selected (overlay with a close button).
- **Mobile <768:** palette and inspector become bottom sheets (toggled by buttons in the toolbar/canvas); canvas takes full width; node editing is desktop-focused (acceptable per DESIGN.md).

- [ ] **Step 1: Make the layout responsive in `WorkflowBuilder.tsx`**

Change the panes container so the palette and inspector collapse/overlay below `xl`. Replace the `<div className="flex h-[520px]">…</div>` block with:
```tsx
      <div className="relative flex h-[520px]">
        {/* Palette: full on xl, icon strip on md, bottom-sheet toggle on mobile */}
        <div className="hidden md:block">
          <Palette compact={typeof window !== "undefined" && window.innerWidth < 1280} />
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
```

- [ ] **Step 2: Add `compact` to `Palette.tsx`**

Add an optional `compact` prop. When `compact`, render the category groups as a vertical icon strip (the color swatch acts as the icon) that expands its chip list on click. Add to the `Palette` signature:
```tsx
export function Palette({ compact = false }: { compact?: boolean }) {
```
and when `compact` is true, render a `w-12` strip: one swatch button per category that toggles a popover listing that category's draggable chips (reuse the existing chip markup). Keep the full layout for `compact === false`. Both paths use the same `onChipDragStart`.

- [ ] **Step 3: Add `onClose` to `Inspector.tsx`**

Add an optional `onClose?: () => void` prop; when present, render a small `✕` button in the inspector header (top-right) that calls it. This is the slide-over close affordance on tablet/mobile; on `xl` `onClose` is omitted so no button shows.

- [ ] **Step 4: Verify build + responsive spot-check**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Then in the running dev app, use the browser device toolbar at ~1440px (three panes), ~1024px (icon-strip palette + inspector slide-over on select with ✕), and ~390px (canvas full width, inspector overlays on select). Record pass/fail.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/workflow/WorkflowBuilder.tsx frontend/components/workflow/Palette.tsx frontend/components/workflow/Inspector.tsx
git commit -m "feat(workflow): responsive palette icon strip + inspector slide-over

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage:**
- Three-pane layout, file decomposition → Tasks 1–8. ✓
- `nodeCatalog` single source → Task 1. ✓
- Params only in Inspector; cards read-only → Tasks 4, 6. ✓
- Drag-from-palette, drop at cursor → Tasks 5, 7. ✓
- Connect/delete (ports, key, footer) → Tasks 3, 6, 7. ✓
- Live validation mirroring engine.py → Tasks 2, 8. ✓
- Minimap + legend → Task 7. ✓
- Palette saved strategies → Task 5. ✓
- Undo/redo → Tasks 3, 8. ✓
- RWD → Task 9. ✓
- Category color tokens → Task 1. ✓
- Save/Run/result panel retained → Task 8. ✓
- Verify via tsc + build + manual; no test runner → all tasks + Global Constraints. ✓

**Placeholder scan:** none — every code step has complete code; the only intentionally-described (not fully-coded) parts are the Task 9 `compact` icon-strip and `onClose` button, which are bounded UI additions with explicit signatures and behavior. All exact values (tokens, defaults, params) are concrete.

**Type consistency:** `TradeNodeData` is defined once in `useWorkflowState.ts` (Task 3) and imported by `TradeNode`/`Canvas`/`Inspector`. `useWorkflowState`'s returned shape is consumed as `ReturnType<typeof useWorkflowState>` by `Canvas`. `ValidationResult`/`validateGraph` (Task 2) used by `Toolbar`/`WorkflowBuilder`. `NODE_CATALOG`/`CATEGORY_COLOR`/`CATEGORY_LABEL`/`defaultParams`/`summaryText`/`ParamField`/`NodeCategory` all defined in Task 1 and consumed consistently. The drag payload key `"application/reactflow"` is written in Task 5 and read in Task 7. Zoom is wired via the `onInit` prop on `Canvas` (defined in Task 7, consumed in Task 8) which stores a `ReactFlowInstance` the Toolbar drives.
