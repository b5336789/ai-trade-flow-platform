# P5 策略室→回測→實盤 串接 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire 策略室 → 回測 → 工作流(實盤) into a one-click chain using only URL query params + existing APIs, so a saved strategy can be carried into backtest pre-selected and a backtest result can pre-seed a runnable workflow graph.

**Architecture:** URL query params carry intent across pages (`?strategy=saved:<id>&symbol=&timeframe=` into backtest; `?workflow=<id>` into the workflow builder); there is **no global store** (YAGNI). The seed graph is built by a pure helper and persisted through the existing `api.createWorkflow`, then loaded by `WorkflowBuilder` via a new `api.getWorkflow(id)` (backend `GET /api/workflows/{id}` already exists). Live-trading safety is unchanged — the builder's existing `--live` Toolbar conventions are simply not bypassed.

**Tech Stack:** Next 14 App Router (useSearchParams/useRouter) · React 18 · TypeScript

## Global Constraints
- **DESIGN.md is authority** for all visual/UI decisions — read it before any styling change. Electric-cyan `--accent` is **AI/automation only**; price up/down via `--up`/`--down` tokens (台股 inverts via `data-market="tw"`); use existing tokens (`--surface-*`, `--border`, `--muted`, `--accent-dim`, `--live`), never hardcode colors. **Live safety:** the `--live`/`bg-live` Toolbar banner + "▶ 送出真實訂單" button conventions in `components/workflow/Toolbar.tsx` are the live guardrail — do **not** add or bypass live-order code in this phase.
- **No frontend unit runner.** Verify every task with: `cd frontend && npx tsc --noEmit && npm run build` (must pass), plus a **run-app visual verify** of the actual click-through. Pure helpers ship with a `node --input-type=module` self-check assertion.
- **Surgical changes only** — touch only what each task names; do not "clean up" adjacent code.
- All frontend client components use `"use client"`; import `useRouter`/`useSearchParams` from `next/navigation`.
- Always work in the frontend dir (`cd frontend`). **Never commit to `main`** — branch, PR, merge (see CLAUDE.md git flow).

## Dependency / Coupling Notes (READ FIRST)
- **`lib/labels.ts` (`L`) is a P1 deliverable.** If P1 has merged, add an `L.linking` section (Task 1) and consume `L.linking.*` everywhere. If P1 has **not** merged when P5 starts, define the same Traditional-Chinese string literals inline and leave a `// TODO(P1): move to L.linking` marker — do **not** block on P1.
- **`components/BacktestPanel.tsx` is touched by P2, P3 and P5.** P2 (回測重做: tabs/charts/metrics) and P3 (date-range) restructure the panel body and request types; **P5 only touches the top-of-component state initialization (mount-time query read) and adds no new request fields.** Execution ordering: **P5 should land after P2/P3 if they are in flight**; if P5 lands first, the query-read `useEffect` added here is isolated to the state block and will survive P2/P3 body rewrites. Re-verify the mount effect still references the live `saved`/`changeStrategy`/`setSymbol`/`setTimeframe`/`setMarketState` symbols after any P2/P3 merge. The `SAVED_PREFIX = "saved:"` constant and `saved:<id>` strategy value convention are stable across all three phases — coordinate on it, do not redefine it.
- **P4 already links library tree leaves to `/trading-room/backtest?strategy=saved:<id>`.** Task 1 (BacktestPanel reading that param) is what makes P4's links functional — they are currently dead until this task lands.

---

## File Structure

```
frontend/
  lib/
    labels.ts            (Task 1 — add L.linking section; P1-owned file)
    workflow-seed.ts     (Task 3 — NEW pure helper: seedGraphFromStrategy)
    api.ts               (Task 4 — add api.getWorkflow(id))
  components/
    BacktestPanel.tsx                 (Task 1 — read query params on mount)
    strategy/StrategyLibrary.tsx      (Task 2 — 拿去回測 button on saved cards)
    strategy/GeneratedStrategy.tsx    (Task 2 — 拿去回測 after save / disabled hint)
    workflow/WorkflowBuilder.tsx      (Task 5 — load ?workflow=<id> on mount)
  components/BacktestResultActions.tsx (Task 4 — NEW 建立工作流 entry; or inline in BacktestPanel)
```

---

### Task 1: BacktestPanel reads `?strategy=&symbol=&timeframe=` on mount

**Files:** `frontend/components/BacktestPanel.tsx` (state block ~L23-48; saved fetch effect ~L43-45), `frontend/lib/labels.ts` (add `L.linking`)
**Interfaces:**
- Consumes: URL query `?strategy=saved:<id>&symbol=&timeframe=` (produced by P4 tree leaves + Task 2 buttons)
- Produces: a BacktestPanel that pre-selects the saved strategy / symbol / timeframe from the URL

**Background:** `useSearchParams()` is available because BacktestPanel is already `"use client"`. The saved list arrives async (`api.listSavedStrategies().then(setSaved)`), so a `saved:<id>` strategy value can be applied immediately (the `<select>` shows it once `saved` resolves), but we must guard so we only auto-apply **once** and don't fight the user's later manual changes.

- [ ] **Step 1: Add `L.linking` to `lib/labels.ts`.** Append inside the existing `L` object (create the file's section if P1 has landed; otherwise inline-literal per the coupling note):
  ```ts
  // inside export const L = { ... }
  linking: {
    sendToBacktest: "拿去回測",
    sendToBacktestHint: "先存入策略庫才能拿去回測",
    buildWorkflow: "建立工作流",
    buildingWorkflow: "建立中…",
    buildWorkflowHint: "用此策略 + 下單節點預生成工作流",
  },
  ```

- [ ] **Step 2: Read query params on mount in `BacktestPanel`.** Add `useSearchParams` to the existing `next/navigation`-free import (it currently imports only React hooks). At top of `BacktestPanel`, after the existing `useState` declarations and the `saved` state, add the import and a one-shot apply effect. Use the existing `changeStrategy`, `setSymbol`, `setTimeframe`, `setMarketState` setters so params/strategy-kind stay consistent:
  ```tsx
  // add to imports
  import { useSearchParams } from "next/navigation";

  // ...inside BacktestPanel, after existing useState lines (keep all existing state):
  const searchParams = useSearchParams();
  const appliedQuery = useRef(false);

  // Carry intent from 策略室 / nav tree: ?strategy=saved:<id>&symbol=&timeframe=.
  // Apply ONCE. The saved-strategy select needs `saved` loaded to render its option,
  // so re-run until either applied or there is no saved-strategy intent to wait for.
  useEffect(() => {
    if (appliedQuery.current) return;
    const qSymbol = searchParams.get("symbol");
    const qTimeframe = searchParams.get("timeframe");
    const qMarket = searchParams.get("market");
    const qStrategy = searchParams.get("strategy"); // e.g. "saved:12" or "ma_cross"

    if (qSymbol) setSymbol(qSymbol.toUpperCase());
    if (qTimeframe && TIMEFRAMES.includes(qTimeframe)) setTimeframe(qTimeframe);
    if (qMarket && MARKETS.some((m) => m.value === qMarket)) setMarketState(qMarket);

    if (qStrategy?.startsWith(SAVED_PREFIX)) {
      // Wait for the saved list so the <select> can show the option; bail once loaded.
      const id = Number(qStrategy.slice(SAVED_PREFIX.length));
      if (saved.length === 0) return; // try again after listSavedStrategies resolves
      if (saved.some((s) => s.id === id)) changeStrategy(qStrategy);
      appliedQuery.current = true;
    } else if (qStrategy && STRATEGY_NAMES.includes(qStrategy)) {
      changeStrategy(qStrategy);
      appliedQuery.current = true;
    } else if (qSymbol || qTimeframe || qMarket) {
      appliedQuery.current = true; // params present but no strategy intent
    }
  }, [searchParams, saved]);
  ```
  Add `useRef` to the React import (`import { useEffect, useRef, useState } from "react";`). `STRATEGY_NAMES` is already imported from `@/lib/strategies`; `MARKETS`, `SAVED_PREFIX`, `TIMEFRAMES` already exist in this file.

- [ ] **Step 3: `cd frontend && npx tsc --noEmit && npm run build`** — Expected: pass.
- [ ] **Step 4: run-app visual verify.** Use the `run-app` skill. Navigate to `/trading-room/backtest?strategy=saved:<existing-id>&symbol=ETH/USDT&timeframe=4h`. Confirm: market/symbol/timeframe inputs reflect the query, and the strategy `<select>` shows the saved strategy selected (the `策略庫 · 預設參數` badge appears). Then change the strategy manually and reload **without** query → it must not re-apply (no flicker back).
- [ ] **Step 5: Commit** (`feat(p5): BacktestPanel reads strategy/symbol/timeframe from URL query`).

---

### Task 2: 策略室 「拿去回測」 buttons

**Files:** `frontend/components/strategy/StrategyLibrary.tsx` (card action row ~L100-122), `frontend/components/strategy/GeneratedStrategy.tsx` (save footer ~L102-128)
**Interfaces:**
- Consumes: a saved strategy `id` (only saved strategies have one)
- Produces: `router.push('/trading-room/backtest?strategy=saved:'+id)` navigation (consumed by Task 1)

**Decision (generated-but-unsaved):** A generated strategy has **no id** until saved. In `GeneratedStrategy`, the 「拿去回測」 button is **disabled with a hint until saved**, because `onSaved()` does not currently return the new id and auto-save-then-navigate would need an id round-trip the component doesn't have. The reliable id source is the **策略庫 card** (`StrategyLibrary`), which always has `s.id`. So: primary entry = library card; secondary = a post-save hint in GeneratedStrategy pointing the user to the library card.

- [ ] **Step 1: Add 「拿去回測」 to each `StrategyLibrary` card.** `StrategyLibrary` is `"use client"`. Add `import { useRouter } from "next/navigation";` and `import { L } from "@/lib/labels";`, then `const router = useRouter();` inside the component. In the card action row (the `<div className="mt-3 flex gap-1.5 ...">` containing 載入/回測/刪), insert a full-width 「拿去回測」 button **above** that row so it reads as the forward action. It carries the same `symbol`/`market` already chosen on this panel:
  ```tsx
  <button
    onClick={() =>
      router.push(
        `/trading-room/backtest?strategy=saved:${s.id}` +
          `&symbol=${encodeURIComponent(symbol)}&market=${encodeURIComponent(market)}`,
      )
    }
    className="mt-3 w-full rounded-sm border border-accent/40 bg-accent-dim px-2 py-1 text-[12px] text-accent hover:border-accent"
  >
    {L.linking.sendToBacktest} →
  </button>
  ```
  (`symbol` and `market` are existing state in this component; `accent`/`accent-dim` are valid here because navigating into the AI-designed-strategy flow is automation-adjacent and matches the existing 回測 button styling on the same card.)

- [ ] **Step 2: Add a disabled 「拿去回測」 hint in `GeneratedStrategy`.** In the save footer, after the save button, the strategy is unsaved until `onSaved` fires. Add a disabled button with a `title` hint so the affordance is discoverable but honest (no fake id):
  ```tsx
  // in the footer button row, after the 存入策略庫 button:
  <button
    type="button"
    disabled
    title={L.linking.sendToBacktestHint}
    className="rounded-md border border-border bg-surface-2 px-4 py-2 text-[13px] text-faint opacity-50"
  >
    {L.linking.sendToBacktest} →
  </button>
  ```
  Add `import { L } from "@/lib/labels";` to `GeneratedStrategy.tsx`. Also add one line of guidance under the success message: when `save.isSuccess`, append `· 到下方策略庫點「拿去回測」` to the existing `✓ 已存入策略庫` text (surgical: extend the existing `<p>` string only).

- [ ] **Step 3: `cd frontend && npx tsc --noEmit && npm run build`** — Expected: pass.
- [ ] **Step 4: run-app visual verify.** Open `/strategy-lab`. In 策略庫 click 「拿去回測」 on a saved card → lands on `/trading-room/backtest` with that strategy preselected (verifies the Task 1 handoff end-to-end). Confirm the GeneratedStrategy button is disabled with the hint tooltip before saving.
- [ ] **Step 5: Commit** (`feat(p5): 拿去回測 buttons in strategy lab navigate to backtest preselected`).

---

### Task 3: `lib/workflow-seed.ts` — pure seed-graph helper

**Files:** `frontend/lib/workflow-seed.ts` (NEW)
**Interfaces:**
- Consumes: `{ strategyId, strategySource, symbol, market, timeframe, quantity? }`
- Produces: a `WorkflowGraph` (typed from `@/lib/api`) of `data_source → strategy → order`

**Node params (must match backend `app/workflow/schema.py` + `app/workflow/nodes.py`):**
- `data_source.params`: `{ symbol, market, timeframe, limit }` — `nodes.py:_run_data_source` requires `symbol`, reads `market` (default crypto), `timeframe` (default "1h"), `limit` (default 100).
- `strategy.params`: for a **saved** strategy use `{ strategy_id: <number> }` — `nodes.py:_run_strategy` branches on `params.strategy_id`. For a **built-in** strategy use `{ name: <string> }`. Do **not** set both.
- `order.params`: `{ quantity }` — `nodeCatalog.ts` default `0.01`; `_run_order` consumes the upstream Signal.
- Edges: `data→strat`, `strat→order` (matches `WorkflowGraph.edges: {source, target}` and the engine's topological sort).

- [ ] **Step 1: Write `frontend/lib/workflow-seed.ts`** (COMPLETE):
  ```ts
  import type { WorkflowGraph } from "@/lib/api";

  export interface SeedStrategyInput {
    /** Saved-library strategy id, or null/undefined for a built-in by name. */
    strategyId?: number | null;
    /** Built-in strategy name (e.g. "ma_cross") when strategyId is absent. */
    strategyName?: string;
    symbol: string;
    market: string;
    timeframe: string;
    /** Order size; defaults to the order node's catalog default. */
    quantity?: number;
  }

  /**
   * Build a minimal runnable workflow: data_source -> strategy -> order.
   * Node `type`/`params` mirror backend app/workflow/schema.py + nodes.py so the
   * persisted graph runs without further editing. No global store: the caller
   * persists this via api.createWorkflow and navigates with the returned id.
   */
  export function seedGraphFromStrategy(input: SeedStrategyInput): WorkflowGraph {
    const { strategyId, strategyName, symbol, market, timeframe, quantity } = input;

    const strategyParams: Record<string, unknown> =
      strategyId != null
        ? { strategy_id: strategyId }
        : { name: strategyName ?? "ma_cross" };

    return {
      nodes: [
        {
          id: "data",
          type: "data_source",
          params: { symbol, market, timeframe, limit: 500 },
        },
        { id: "strat", type: "strategy", params: strategyParams },
        { id: "order", type: "order", params: { quantity: quantity ?? 0.01 } },
      ],
      edges: [
        { source: "data", target: "strat" },
        { source: "strat", target: "order" },
      ],
    };
  }
  ```

- [ ] **Step 2: Self-check (no unit runner).** Run an inline assertion via node (mirrors the P1 chart-helpers self-check). From `frontend/`:
  ```bash
  node --input-type=module -e '
  import { seedGraphFromStrategy } from "./lib/workflow-seed.ts";
  ' 2>/dev/null || true
  ```
  Because Node cannot import `.ts` with the `@/` alias directly, instead assert against a transpiled inline copy. Concretely, run:
  ```bash
  node --input-type=module -e '
  function seedGraphFromStrategy({ strategyId, strategyName, symbol, market, timeframe, quantity }) {
    const strategyParams = strategyId != null ? { strategy_id: strategyId } : { name: strategyName ?? "ma_cross" };
    return { nodes: [
      { id: "data", type: "data_source", params: { symbol, market, timeframe, limit: 500 } },
      { id: "strat", type: "strategy", params: strategyParams },
      { id: "order", type: "order", params: { quantity: quantity ?? 0.01 } },
    ], edges: [ { source: "data", target: "strat" }, { source: "strat", target: "order" } ] };
  }
  const saved = seedGraphFromStrategy({ strategyId: 7, symbol: "BTC/USDT", market: "crypto", timeframe: "1h" });
  const builtin = seedGraphFromStrategy({ strategyName: "rsi", symbol: "ETH/USDT", market: "crypto", timeframe: "4h" });
  const assert = (c, m) => { if (!c) { console.error("FAIL: " + m); process.exit(1); } };
  assert(saved.nodes.length === 3, "3 nodes");
  assert(saved.edges.length === 2, "2 edges");
  assert(saved.nodes[1].params.strategy_id === 7, "saved -> strategy_id");
  assert(saved.nodes[1].params.name === undefined, "saved has no name");
  assert(builtin.nodes[1].params.name === "rsi", "builtin -> name");
  assert(builtin.nodes[1].params.strategy_id === undefined, "builtin has no strategy_id");
  assert(saved.nodes[0].type === "data_source" && saved.nodes[2].type === "order", "endpoints");
  console.log("workflow-seed self-check OK");
  '
  ```
  Expected stdout: `workflow-seed self-check OK`. Keep this exact assertion block as the verification record (the literal must stay in sync with the `.ts` body).

- [ ] **Step 3: `cd frontend && npx tsc --noEmit && npm run build`** — Expected: pass (helper is referenced after Task 4; this step confirms it type-checks standalone).
- [ ] **Step 4: Commit** (`feat(p5): add seedGraphFromStrategy workflow seed helper`).

---

### Task 4: 「建立工作流」 entry on a backtest result + `api.getWorkflow`

**Files:** `frontend/lib/api.ts` (add `getWorkflow` near `createWorkflow` ~L408), `frontend/components/BacktestPanel.tsx` (add the button in the result overview area ~L269-294)
**Interfaces:**
- Consumes: current backtest selection (`symbol`, `market`, `timeframe`, the saved/built-in strategy) + `result` (only show after a successful run)
- Produces: a persisted workflow via `api.createWorkflow`, then `router.push('/trading-room/workflow?workflow=' + id)` (consumed by Task 5)

**Handoff decision:** persist-then-navigate-by-id (createWorkflow → `?workflow=<id>`). Rationale: no global store, survives reload, and the seeded graph is durable. Backend `GET /api/workflows/{id}` already exists; we add the missing client method.

- [ ] **Step 1: Add `api.getWorkflow(id)` to `lib/api.ts`** right after `createWorkflow`:
  ```ts
  getWorkflow: (id: number) => request<Workflow>(`/api/workflows/${id}`),
  ```
  (`Workflow` type with `.graph: WorkflowGraph` already exists at L98-104.)

- [ ] **Step 2: Add the 「建立工作流」 button to the backtest result.** In `BacktestPanel`, add `import { useRouter } from "next/navigation";`, `import { seedGraphFromStrategy } from "@/lib/workflow-seed";`, `import { L } from "@/lib/labels";` and `const router = useRouter();`. Add local state `const [seeding, setSeeding] = useState(false);` and a handler that reuses the existing `isSaved`/`savedId`/`strategy`/`symbol`/`market`/`timeframe` state:
  ```tsx
  async function buildWorkflow() {
    setSeeding(true);
    setError(null);
    try {
      const graph = seedGraphFromStrategy({
        strategyId: isSaved ? savedId : null,
        strategyName: isSaved ? undefined : strategy,
        symbol,
        market,
        timeframe,
      });
      const name = `${isSaved ? saved.find((s) => s.id === savedId)?.name ?? "策略" : strategy} · ${symbol}`;
      const wf = await api.createWorkflow(name, graph);
      router.push(`/trading-room/workflow?workflow=${wf.id}`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSeeding(false);
    }
  }
  ```
  Render the button at the top of the `tab === "overview"` block (so it appears with results). Use a neutral/automation style — it leads toward live, so keep it secondary to avoid implying it places orders:
  ```tsx
  <div className="flex justify-end">
    <button
      onClick={buildWorkflow}
      disabled={seeding}
      title={L.linking.buildWorkflowHint}
      className="rounded-md border border-accent/40 bg-accent-dim px-3 py-1 text-sm font-medium text-accent hover:border-accent disabled:opacity-50"
    >
      {seeding ? L.linking.buildingWorkflow : `${L.linking.buildWorkflow} →`}
    </button>
  </div>
  ```
  (Note: if P2 has rewritten the overview tab, place this `<div>` as the first child of the overview container; the handler is independent of the tab body.)

- [ ] **Step 3: `cd frontend && npx tsc --noEmit && npm run build`** — Expected: pass.
- [ ] **Step 4: run-app visual verify.** Run a backtest in `/trading-room/backtest` (use a saved strategy via the Task 1 deep-link), click 「建立工作流」 → it should create a workflow and navigate to `/trading-room/workflow?workflow=<id>` (verified visually together with Task 5). Confirm a built-in strategy (`name`) and a saved strategy (`strategy_id`) both produce a valid graph.
- [ ] **Step 5: Commit** (`feat(p5): 建立工作流 from backtest result persists seed graph and navigates`).

---

### Task 5: WorkflowBuilder loads `?workflow=<id>` on mount

**Files:** `frontend/components/workflow/WorkflowBuilder.tsx` (`BuilderInner` ~L17-44)
**Interfaces:**
- Consumes: URL `?workflow=<id>` (produced by Task 4)
- Produces: the builder canvas seeded from the persisted graph via the existing `wf.setGraph`

**Background:** `useWorkflowState` already exposes `setGraph(g: WorkflowGraph)` (L148-156) which lays nodes out in a grid and sets edges — exactly what a loaded graph needs. `BuilderInner` is inside `"use client"`. We fetch the workflow once on mount and seed the canvas + name.

- [ ] **Step 1: Load the workflow on mount.** In `BuilderInner`, add `import { useSearchParams } from "next/navigation";` and `import { useEffect, useRef } from "react";` (merge with the existing `react` import). After the existing hooks:
  ```tsx
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
      })
      .catch((e) => setError((e as Error).message));
  }, [searchParams]);
  ```
  (`wf`, `setName`, `setError` already exist in `BuilderInner`; `api` is already imported.)

- [ ] **Step 2: `cd frontend && npx tsc --noEmit && npm run build`** — Expected: pass.
- [ ] **Step 3: run-app visual verify (full chain).** 策略室 → 拿去回測 (saved card) → backtest preselected → Run → 建立工作流 → workflow page shows the seeded `data_source → strategy → order` graph with the correct name; the strategy node Inspector shows `已存策略 #<id>` for a saved strategy. **Live-safety checkpoint:** confirm the Toolbar still renders the mode badge and that in `paper` mode the run button reads 「▶ 執行回測」 (cyan), and that we added **no** live-order code — the existing `--live`/`bg-live` "▶ 送出真實訂單" path is untouched.
- [ ] **Step 4: Commit** (`feat(p5): WorkflowBuilder seeds canvas from ?workflow=<id> deep-link`).

---

## Self-Review

**Spec §8 (Area E) requirement → task mapping**
- §8 第二層 1 「策略室 →『拿去回測』」 → **Task 2** (library card button) + **Task 1** (panel reads the param). 第三層「回測頁讀 URL query `?strategy=saved:<id>&symbol=&timeframe=`,進頁自動選定」 → **Task 1**. 第三層「`router.push('/trading-room/backtest?strategy=saved:'+id)`」 → **Task 2**.
- §8 第二層 2 「回測 →『套用到工作流』」 / 第三層「往實盤『建立工作流』→ 預生成含該策略 + order node 的 graph,帶到 `/trading-room/workflow`(用既有 `api.createWorkflow`)」 → **Task 3** (seed helper) + **Task 4** (createWorkflow + navigate) + **Task 5** (load on the workflow page).
- §8 第三層「實盤安全態維持 DESIGN.md `--live` 規範」 → **Task 5 Step 3 live-safety checkpoint** (no new live code; existing Toolbar conventions untouched). §11.4(c) confirmed 「建立工作流」 is in scope.
- §8 第三層「不引入全域 store(YAGNI),靠 URL query + 既有 API 串接」 → satisfied: only `useSearchParams`/`useRouter` + `api.createWorkflow`/`getWorkflow`; no store added.

**Placeholder scan:** No `TBD`/`FIXME`/`???` in shipped code. The only `TODO` is the conditional `// TODO(P1): move to L.linking` marker, which is contingent on P1 merge ordering (documented in the coupling notes), not an unfinished feature.

**Type-consistency check (vs `lib/api.ts` + backend `schema.py`):**
- `seedGraphFromStrategy` returns `WorkflowGraph` = `{ nodes: GraphNode[]; edges: GraphEdge[] }` (api.ts L75-89). `GraphNode` = `{ id: string; type: NodeType; params: Record<string, unknown> }` — every seeded node sets exactly these; `type` values `"data_source" | "strategy" | "order"` are members of the `NodeType` union (api.ts L64-73) and of backend `NodeType` enum (schema.py L10-19). `GraphEdge` = `{ source; target }` — matches.
- Node `params` match backend consumers: `data_source` → `nodes.py:_run_data_source` (`symbol` required, `market`/`timeframe`/`limit` read); `strategy` saved → `params.strategy_id` branch (`nodes.py:_run_strategy` L97-106); `strategy` built-in → `params.name` (L107-109); `order` → `params.quantity` (`nodeCatalog` default 0.01). No node sets both `strategy_id` and `name`.
- `api.getWorkflow` returns `Workflow` (api.ts L98-104) whose `.graph` is `WorkflowGraph`, fed straight into `wf.setGraph(g: WorkflowGraph)` (useWorkflowState L148) — types align. Backend `GET /api/workflows/{id}` returns the `Workflow` model (`workflows.py:67-69`).
- `SAVED_PREFIX`/`saved:<id>` convention reused unchanged from `BacktestPanel.tsx:17` and `lib/api.ts` saved-strategy path — no parallel definition introduced.
