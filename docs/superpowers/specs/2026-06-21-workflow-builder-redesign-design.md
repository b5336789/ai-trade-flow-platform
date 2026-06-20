# Workflow Builder Redesign (Sub-project #1 of 2) — Design

Date: 2026-06-21
Branch (impl): `feature/workflow-builder-redesign`

## Context

The workflow editor (`frontend/components/workflow/WorkflowBuilder.tsx`, 207 lines +
`TradeNode.tsx`) is a prototype that does not match the already-specified three-pane
builder in `DESIGN.md` ("Workflow Builder (交易室 canvas)", lines 169–221). User pain
(all confirmed): editing params inside tiny node cards conflicts with dragging; nodes
added via buttons land at random overlapping positions; connecting/deleting is awkward;
no validation feedback before save/run.

This is **sub-project #1 of 2**. #2 (AI workflow generator: NL → `WorkflowGraph`) is a
separate later spec. The shared interface between them is the existing `WorkflowGraph`
type (`{nodes: GraphNode[], edges: GraphEdge[]}`); AI-generated graphs will render and be
edited in this builder.

## Goal

Rebuild the builder as the three-pane workspace DESIGN.md specifies, fixing all four pain
points, with full v1 scope: minimap + legend, palette with saved library strategies,
undo/redo, and responsive (desktop/tablet/mobile) behavior.

Non-goals: AI workflow generation (#2); backend changes (the workflow API + engine are
unchanged); adding a frontend test runner.

## Design authority

All visuals — three-pane layout, node category colors (`--c-data/--c-strat/--c-logic/
--c-order/--c-out`), node anatomy (158px card, left color bar, color chip, name, category
tag, 1–2 mono params, ringed ports, 2px cyan selected outline), edge/run states, toolbar
contents, and RWD breakpoints — follow `DESIGN.md` verbatim. The electric-cyan accent
stays reserved for AI/automation (Run button + AI Signal node only). Up/down semantics use
`--up`/`--down` tokens. This spec does not restate pixel values; it defers to DESIGN.md and
flags any deviation for approval (there are none).

## Architecture — file decomposition

Replace the monolith with focused files under `frontend/components/workflow/`:

| File | Responsibility | Depends on |
|------|----------------|-----------|
| `nodeCatalog.ts` | SINGLE source of node metadata: per `NodeType` → `{category, colorToken, title, defaults, paramSchema, hasInput, hasOutput}` | `lib/api` (NodeType), `lib/strategies` |
| `validateGraph.ts` | Pure `validateGraph(graph: WorkflowGraph) => {valid: boolean, errors: string[]}` (missing input, cycle, duplicate id) | `lib/api` types |
| `useWorkflowState.ts` | nodes/edges state + bounded undo/redo history + `addNode/onDrop/deleteSelection/duplicate/setParam/onConnect/onNodesChange/onEdgesChange` | React Flow hooks |
| `TradeNode.tsx` | Read-only node card per DESIGN.md anatomy (header + 1–2 key params in mono + ports) | `nodeCatalog` |
| `Palette.tsx` | Left pane: search + category-grouped draggable chips; Strategy group includes `api.listSavedStrategies()` | `nodeCatalog`, `lib/api` |
| `Canvas.tsx` | Center: `ReactFlow` + `Background` (dotted 22px) + `MiniMap` + color `Legend` + `Controls`; `onDrop`/`onDragOver` create nodes at cursor via `screenToFlowPosition` | `useWorkflowState`, `TradeNode`, `nodeCatalog` |
| `Inspector.tsx` | Right pane: selected node category label + title + editable fields (from `paramSchema`); footer 複製 / 刪除(`--down`) | `nodeCatalog`, `useWorkflowState` |
| `Toolbar.tsx` | Top: title · `交易室 · paper/LIVE` chip · undo/redo · zoom (−/100%/＋/fit) · live validation status · 💾 儲存 · ▶ 執行回測 (→ pink `--live` ▶ 送出真實訂單 in live mode) | `validateGraph` result, callbacks |
| `WorkflowBuilder.tsx` | Orchestrator: three-pane responsive layout, owns `selectedId`, wires the hook + panes, save/run + result panel (kept from current) | all of the above |

Rationale: the node card and inspector both render from `nodeCatalog`, so node metadata
lives in exactly one place (today it's split across `DEFAULTS` and `TradeNode`). `validateGraph`
is pure and isolated. `useWorkflowState` owns all mutation + history so panes stay thin.

## Param editing model (approved decision)

Params are edited **only** in the Inspector. Node cards are **read-only summaries** showing
the 1–2 key params in mono (e.g. `rsi ≤ 28`, `fast 10 / slow 20`). This removes the
input-vs-drag conflict that made in-node editing painful. `nodeCatalog.paramSchema` drives
both: which fields the inspector shows (type: number/text/select + options) and which 1–2
keys the card surfaces.

## Interactions / data flow

- **Add node:** drag a palette chip → `Canvas.onDrop` reads the dropped `NodeType` (or saved
  strategy id) from `dataTransfer` → `screenToFlowPosition(cursor)` → `useWorkflowState.addNode(type, pos)`
  with `nodeCatalog.defaults`. No random positions.
- **Select / edit:** click a node → `selectedId` set → Inspector renders its fields →
  `setParam(id, key, value)` updates state (pushes history).
- **Connect:** drag output port → input port → `onConnect` adds edge.
- **Delete:** Inspector 刪除 button, or Delete/Backspace on a selected node/edge →
  `deleteSelection()`.
- **Duplicate:** Inspector 複製 → clone node with offset position + new id.
- **Validate:** `WorkflowBuilder` computes `validateGraph(buildGraph())` via `useMemo`;
  Toolbar shows `✓ 有效 · N nodes · M edges` or the red error reason.
- **Save / Run:** `buildGraph()` → `api.createWorkflow(name, graph)` / `api.runWorkflow(graph)`
  (unchanged); result panel renders `RunResult.steps` as today.

### Validation rules (mirror backend `workflow/engine.py`)

`validateGraph` returns errors for: (1) a cycle in the graph; (2) duplicate node ids;
(3) any node that requires an input (`nodeCatalog.hasInput`, i.e. every type except
`data_source`) having zero incoming edges. These match what the engine fails loud on, so a
graph that is `✓ 有效` here will not be rejected by the engine for structure.

## Undo/redo

`useWorkflowState` keeps a bounded (e.g. 50-entry) history of `{nodes, edges}` snapshots.
Every mutating action (add, delete, duplicate, connect, setParam, node move on drag-stop)
pushes a snapshot; undo/redo restore. Exposed as `undo()/redo()/canUndo/canRedo` for the
Toolbar; keyboard ⌘Z / ⌘⇧Z.

## Palette saved strategies

The Strategy category lists built-ins (`STRATEGY_NAMES`) **and** saved library strategies
from `api.listSavedStrategies()` (loaded on mount; loading/empty states handled). Dragging a
saved strategy creates a `strategy` node whose params reference that saved def (carrying its
id/name) so it round-trips through save/run.

## Responsive (per DESIGN.md)

- **Desktop ≥1280:** full three-pane.
- **Tablet 768–1279:** palette collapses to an icon strip (category icons, click to pop a
  chip list); inspector becomes a slide-over opened on node selection; canvas takes freed width.
- **Mobile <768:** view/run-focused; palette and inspector become bottom sheets; heavy node
  editing is intentionally a desktop task (DESIGN.md-flagged scope call).

## Error handling / fail-loud

- `api.listSavedStrategies()` failure: palette shows an inline error in the Strategy group,
  built-ins still usable (do not crash the builder).
- Save/Run errors: existing inline error display retained.
- An invalid graph disables nothing destructive but the Toolbar shows the red reason; Run on
  an invalid graph still surfaces the backend's fail-loud error in the result panel.

## Testing / verification

No frontend test runner exists (CI = `npm run build` only); none is added (matches repo
convention). Verification gate:
1. `npx tsc --noEmit` — type-check clean.
2. `npm run build` — production build passes.
3. Manual drive in the running app (`npm run dev` + backend): drag each node category from
   palette → edits in inspector apply → connect ports → delete via key + footer → undo/redo →
   live validation flips red on a missing-input/cycle graph then green when fixed → save →
   run → result panel renders. RWD spot-check at desktop/tablet/mobile widths.

`validateGraph.ts` is kept pure so it *could* be unit-tested later if a runner is added.

## Out of scope / YAGNI

- AI workflow generation (sub-project #2).
- Any backend / workflow-engine change.
- A new frontend test runner (vitest etc.).
- Persisting canvas layout coordinates server-side (positions are client-only; the saved
  `WorkflowGraph` carries nodes/edges/params, as today).
