# P4 導覽中文化 + 首次引導 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the left-tree sidebar self-explanatory (Chinese main label + English subtitle), mount the strategy library under 策略室, group tools under 工具, add a dismissible 3-step home onboarding card, and unify remaining English panel strings to Chinese via the labels layer — all conforming to DESIGN.md «Navigation — Left Tree Menu».

**Architecture:** This phase is frontend-only and consumes the P1 labels layer (`@/lib/labels` `L`, `@/components/Term` `<Term>`). It extends the static `NavItem`/`NavLeaf` data model with `subtitle`, renders subtitles in `TreeNav` (hidden in the `<xl` icon rail alongside `.nav-label`), injects the saved-strategy library as dynamic tree leaves from a client fetch, adds a self-contained onboarding card to `HomeDashboard`, and sweeps the four still-English panels (Portfolio / Schedules / Notifications / DataImport) to Chinese. No backend changes; no new routes.

**Tech Stack:** Next 14 App Router · React 18 · TypeScript · Tailwind (DESIGN.md tokens)

## Global Constraints
- **DESIGN.md is the authority** for all visual/UI decisions — the «Navigation — Left Tree Menu» and «Responsive (RWD)» sections govern this phase. Read it before touching any nav code. Flag any deviation for explicit approval.
- **Tokens only** — never hardcode colors. Use existing Tailwind token classes already present in the codebase (`border-accent`, `bg-accent-dim`, `text-text`, `text-muted`, `text-faint`, `border-border`, `bg-surface-1/2/3`, `border-live`, `text-live`, `font-display`, `num`, `text-up`, `text-down`). Drive price up/down via `--up`/`--down` tokens only.
- **cyan = AI / active only** — `--accent` is reserved for the active leaf and AI/automation leaves; `實際下單`-style live leaves use the `--live` dot, never cyan.
- **NO frontend unit runner** — there is no test framework. Verify every task with `cd frontend && npx tsc --noEmit && npm run build` (must pass) **plus** a run-app visual check for any visible change (sidebar subtitles render, library appears under 策略室, active state styling, onboarding card on home).
- **Surgical changes only** — touch only code relevant to Area D. Do not "clean up" adjacent code, styling, or comments. Match existing conventions exactly.
- **All frontend commands are `cd frontend`-prefixed** (agent cwd resets between bash calls; always run from `frontend/`).
- **Never commit to `main`** — branch first, open a PR, then merge (git flow). Use one branch for this whole phase (e.g. `feature/p4-nav-i18n-onboarding`).
- **Fail loud** — best-effort fetches (strategy library) must tolerate auth/empty gracefully and render nothing rather than crash; everything else surfaces errors.
- **Coordination note (overlap with P2):** P2 also edits `lib/labels.ts`. All P4 additions to `lib/labels.ts` are **purely additive** (a new `L.nav` block plus new keys under `L.common`/new `L.portfolio`/`L.schedules`/`L.notifications`/`L.dataImport` sections). Append; never reorder or rewrite P2's keys. Conflicts, if any, are trivial additive merges.

---

## File Structure

```
frontend/
  lib/
    nav.ts                    # MODIFY — add subtitle? to NavItem/NavLeaf; add 工具 group; subtitles
    labels.ts                 # MODIFY — add L.nav + panel label sections (additive; P1 owns the file)
  components/
    shell/
      TreeNav.tsx             # MODIFY — render subtitle; mount StrategyLibraryTree under 策略室
      StrategyLibraryTree.tsx # CREATE — client fetch of saved strategies → tree leaves
    HomeDashboard.tsx         # MODIFY — render <Onboarding/>
    Onboarding.tsx            # CREATE — dismissible 3-step card (localStorage)
    PortfolioPanel.tsx        # MODIFY — English → L.*
    SchedulesPanel.tsx        # MODIFY — English → L.*
    NotificationsPanel.tsx    # MODIFY — English → L.*
    DataImportPanel.tsx       # MODIFY — English placeholder note (mostly already 中文)
```

**Assumption (delivered by P1, consume — do not redefine):** `frontend/lib/labels.ts` exists and exports `L` with at least `L.market`, `L.backtest`, `L.metrics`, `L.common`, plus `GLOSSARY`; `frontend/components/Term.tsx` exports `<Term>`. If P1 has NOT yet landed when this phase starts, **fail loud** — do not stub these files here; they are P1's deliverable. (Tasks that only touch `nav.ts`/`TreeNav.tsx`/`Onboarding.tsx` without `L.*` can proceed; the i18n-sweep task hard-depends on P1.)

---

### Task 1: Extend nav data model — subtitles + 工具 group

**Files:** Modify `frontend/lib/nav.ts` (whole file, lines 1-16)
**Interfaces:**
- Produces: `NavLeaf { label; href; subtitle?; live? }`, `NavItem { label; href?; subtitle?; ai?; children? }`, new `NAV` shape with 策略室 children (與 AI 設計策略 / 策略庫) and a 工具 parent grouping 排程 / 通知 / 匯入.
- Consumes: nothing.

DESIGN.md tree to mirror: 策略室 → 與 AI 設計策略 + 策略庫(saved strategies injected at render time, Task 4); 交易室 → 模擬回測 + 工作流; 市場; 投組; 工具 → 排程 / 通知 / 匯入.

- [ ] **Step 1: Rewrite `frontend/lib/nav.ts`**

```ts
export interface NavLeaf { label: string; href: string; subtitle?: string; live?: boolean }
export interface NavItem { label: string; href?: string; subtitle?: string; ai?: boolean; children?: NavLeaf[] }

export const NAV: NavItem[] = [
  {
    label: "策略室",
    subtitle: "Strategy Lab",
    ai: true,
    children: [
      { label: "與 AI 設計策略", href: "/strategy-lab", subtitle: "Design with AI" },
      // 策略庫 saved strategies are injected dynamically under this leaf (see StrategyLibraryTree).
      { label: "策略庫", href: "/strategy-lab#library", subtitle: "Strategy Library" },
    ],
  },
  {
    label: "交易室",
    subtitle: "Trading Room",
    children: [
      { label: "模擬回測", href: "/trading-room/backtest", subtitle: "Backtest" },
      { label: "工作流", href: "/trading-room/workflow", subtitle: "Workflow" },
    ],
  },
  { label: "市場", href: "/market", subtitle: "Market" },
  { label: "投組", href: "/portfolio", subtitle: "Portfolio" },
  {
    label: "工具",
    subtitle: "Tools",
    children: [
      { label: "排程", href: "/schedules", subtitle: "Schedules" },
      { label: "通知", href: "/notifications", subtitle: "Notifications" },
      { label: "匯入", href: "/data-import", subtitle: "Data Import" },
    ],
  },
];
```

Notes: 策略室 loses its own `href` and becomes a parent (DESIGN.md shows it as an expandable parent). The 策略庫 leaf links to `/strategy-lab#library` as a stable anchor; the saved-strategy leaves under it are injected in Task 4. 工具 has no `href` (group-only). `ai: true` stays on 策略室 so its dot is cyan per DESIGN.md (AI room).

- [ ] **Step 2: `cd frontend && npx tsc --noEmit && npm run build`** — Expected: pass (the new optional `subtitle?` is unused by `TreeNav` until Task 3, but the data must compile and the existing `live?` consumer keeps working).
- [ ] **Step 3: Commit** — `feat(nav): add subtitle to NavItem/NavLeaf and group 排程/通知/匯入 under 工具`

---

### Task 2: Add `L.nav` and panel label sections to `lib/labels.ts`

**Files:** Modify `frontend/lib/labels.ts` (append a new `L.nav` block and panel sections inside the exported `L` object — additive only)
**Interfaces:**
- Consumes: existing `L` export from P1.
- Produces: `L.nav` (subtitles + group labels), `L.portfolio`, `L.schedules`, `L.notifications`, `L.dataImport`, and any missing `L.common` keys used by Tasks 4–8.

> **Coordination:** P2 also edits this file. Append these sections; do not touch P2's `L.market`/`L.backtest`/`L.metrics`. If a key already exists, reuse it instead of duplicating.

- [ ] **Step 1: Add the following sections inside the exported `L` object** (place after the existing sections; keep trailing comma discipline matching the file):

```ts
  nav: {
    strategyLab: "策略室",
    strategyLabSub: "Strategy Lab",
    tradingRoom: "交易室",
    tradingRoomSub: "Trading Room",
    tools: "工具",
    toolsSub: "Tools",
    library: "策略庫",
    librarySub: "Strategy Library",
    libraryEmpty: "尚無已存策略",
    libraryError: "策略庫載入失敗",
  },
  onboarding: {
    title: "三步上手",
    dismiss: "知道了",
    step1Title: "① 策略室設計",
    step1Body: "與 AI 對話,生成你的交易策略並存入策略庫。",
    step2Title: "② 交易室回測",
    step2Body: "把策略拿去回測,看 K 線買賣點與績效指標。",
    step3Title: "③ 排程 / 實盤",
    step3Body: "把驗證過的策略接上工作流,排程自動執行。",
  },
  portfolio: {
    title: "投組",
    cash: "現金",
    positions: "部位市值",
    equity: "權益",
    resetPaper: "重置紙上帳戶",
    error: "投組載入失敗",
    loading: "載入中…",
    recentOrders: "近期訂單",
    noOrders: "尚無訂單紀錄。",
    colSymbol: "代號",
    colQty: "數量",
    colAvg: "均價",
    colPrice: "現價",
    colUpnl: "未實現損益",
  },
  schedules: {
    title: "排程(自動執行)",
    selectWorkflow: "請先選擇已儲存的工作流(於上方建立器存檔)。",
    workflow: "工作流",
    selectPlaceholder: "— 選擇 —",
    everySeconds: "間隔(秒)",
    schedule: "建立排程",
    colInterval: "間隔",
    colState: "狀態",
    colLastRun: "上次執行",
    colLastStatus: "上次結果",
    running: "執行中",
    paused: "已暫停",
    delete: "刪除",
    empty: "尚無排程。先在建立器存檔工作流,再於此排程。",
  },
  notifications: {
    title: "通知",
    test: "測試",
    empty: "尚無通知。訂單與訊號會顯示在這裡。",
  },
  dataImport: {
    symbolPlaceholder: "代號(如 2330 / AAPL)",
  },
```

- [ ] **Step 2: `cd frontend && npx tsc --noEmit && npm run build`** — Expected: pass (sections compile even before consumers exist).
- [ ] **Step 3: Commit** — `feat(labels): add L.nav, onboarding, and panel label sections`

---

### Task 3: Render subtitles in `TreeNav` (parent + leaf), rail-safe

**Files:** Modify `frontend/components/shell/TreeNav.tsx` (lines 1-58)
**Interfaces:**
- Consumes: `NavItem.subtitle`, `NavLeaf.subtitle` from Task 1.
- Produces: parent rows and leaf rows render a small muted English subtitle under the main label; subtitle is wrapped in `.nav-label` so AppShell's `[&_.nav-label]:hidden` (`<xl` icon rail) hides it too.

DESIGN.md: active leaf = cyan 2px left border + `--accent-dim` bg + `--text`; hover `--surface-2`; live leaves use `--live` dot/border (keep the existing `leaf.live` branch). Subtitle is muted/faint English, smaller than the main label.

- [ ] **Step 1: Update parent row markup** (the `<span className="nav-label font-display font-semibold">{item.label}</span>` block) to render a subtitle line. Replace that span with:

```tsx
        <span className="nav-label flex min-w-0 flex-col leading-tight">
          <span className="font-display font-semibold">{item.label}</span>
          {item.subtitle && (
            <span className="text-[11px] font-normal text-faint">{item.subtitle}</span>
          )}
        </span>
```

- [ ] **Step 2: Update leaf row markup** (the `<span className="nav-label">{leaf.label}</span>`) similarly:

```tsx
                <span className="nav-label flex min-w-0 flex-col leading-tight">
                  <span>{leaf.label}</span>
                  {leaf.subtitle && (
                    <span className="text-[11px] text-faint">{leaf.subtitle}</span>
                  )}
                </span>
```

The wrapping `<span className="nav-label …">` keeps the whole label+subtitle block hidden in the icon rail (`<xl`) via AppShell's existing `[&_.nav-label]:hidden` rule. The leading dot (`<span className={...dot...}/>`) stays visible in the rail as before. Do not change the `border-l-2 border-accent bg-accent-dim` active classes or the `leaf.live` branch.

- [ ] **Step 3: `cd frontend && npx tsc --noEmit && npm run build`** — Expected: pass.
- [ ] **Step 4: run-app visual verify** — Use the `run-app` skill. At `xl` width: each parent (策略室 / 交易室 / 工具) and leaf shows Chinese main + small grey English subtitle; active leaf has cyan left border + dim bg. Resize to tablet (`md`–`lg`, `<xl`): sidebar collapses to icon rail and BOTH label and subtitle hide, only dots remain.
- [ ] **Step 5: Commit** — `feat(nav): render Chinese main + English subtitle in tree, rail-safe`

---

### Task 4: Mount the strategy library under 策略室 → 策略庫

**Files:** Create `frontend/components/shell/StrategyLibraryTree.tsx`; Modify `frontend/components/shell/TreeNav.tsx` (render the component beneath the 策略庫 leaf)
**Interfaces:**
- Consumes: `api.listSavedStrategies(): Promise<StrategyListItem[]>` where `StrategyListItem = { id: number; name: string; description: string; source: string; num_params: number }`; `L.nav`.
- Produces: saved strategies rendered as indented tree leaves linking to `/trading-room/backtest?strategy=saved:<id>` (the `strategy` query param is consumed in P5 — fine to link now).

Best-effort fetch (tolerate auth/empty like `BacktestPanel` does): on error or empty, render a single muted hint, never crash.

- [ ] **Step 1: Create `frontend/components/shell/StrategyLibraryTree.tsx`**

```tsx
"use client";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { L } from "@/lib/labels";

export function StrategyLibraryTree({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const params = useSearchParams();
  const activeStrategy = params.get("strategy");
  const q = useQuery({
    queryKey: ["nav-saved-strategies"],
    queryFn: api.listSavedStrategies,
    retry: false,
    staleTime: 60_000,
  });

  if (q.isError) {
    return <p className="px-3 py-1 text-[12px] text-faint">{L.nav.libraryError}</p>;
  }
  const items = q.data ?? [];
  if (items.length === 0) {
    return <p className="px-3 py-1 text-[12px] text-faint">{L.nav.libraryEmpty}</p>;
  }

  return (
    <div className="ml-3 border-l border-border pl-1">
      {items.map((s) => {
        const href = `/trading-room/backtest?strategy=saved:${s.id}`;
        const active =
          pathname.startsWith("/trading-room/backtest") && activeStrategy === `saved:${s.id}`;
        return (
          <Link
            key={s.id}
            href={href}
            onClick={onNavigate}
            title={s.description || s.name}
            className={`nav-label flex items-center gap-2 truncate rounded-md border-l-2 px-3 py-1.5 text-[12px] ${
              active
                ? "border-accent bg-accent-dim text-text"
                : "border-transparent text-muted hover:bg-surface-2"
            }`}
          >
            <span className="truncate">{s.name}</span>
          </Link>
        );
      })}
    </div>
  );
}
```

Notes: saved leaves are NOT live, so they use the standard cyan active style, never `--live`. Wrapping each in `.nav-label` hides them in the icon rail (consistent with the rest of the tree). The component is only mounted at `xl` since the rail hides labels — but it stays in DOM (cheap) and the mobile drawer shows it fully.

- [ ] **Step 2: Mount it under the 策略庫 leaf in `TreeNav.tsx`.** In the leaf `.map(...)`, after the closing `</Link>` of each leaf, conditionally render the library tree when the leaf is 策略庫. Wrap the leaf body in a fragment:

```tsx
          {item.children.map((leaf) => {
            const la = isActive(pathname, leaf.href);
            const isLibrary = leaf.href === "/strategy-lab#library";
            return (
              <div key={leaf.href}>
                <Link
                  href={leaf.href}
                  onClick={onNavigate}
                  className={`flex items-center gap-2 rounded-md border-l-2 px-3 py-2 text-[13px] ${
                    la ? `${leaf.live ? "border-live text-live" : "border-accent text-text"} bg-accent-dim`
                       : "border-transparent text-muted hover:bg-surface-2"
                  }`}
                >
                  <span className="nav-label flex min-w-0 flex-col leading-tight">
                    <span>{leaf.label}</span>
                    {leaf.subtitle && (
                      <span className="text-[11px] text-faint">{leaf.subtitle}</span>
                    )}
                  </span>
                </Link>
                {isLibrary && <StrategyLibraryTree onNavigate={onNavigate} />}
              </div>
            );
          })}
```

Add `import { StrategyLibraryTree } from "./StrategyLibraryTree";` at the top. (This replaces the `key={leaf.href}` on the `Link` with a wrapping `<div key>` and folds in the Task-3 subtitle markup — net result: subtitle + optional library subtree.)

- [ ] **Step 3: `cd frontend && npx tsc --noEmit && npm run build`** — Expected: pass.
- [ ] **Step 4: run-app visual verify** — Use `run-app`. Under 策略室 → 策略庫, saved strategies appear as a deeper-indented list (depth ≤ 3 — DESIGN.md cap: 策略室 → 策略庫 → strategy leaf). With no saved strategies or auth off, the muted "尚無已存策略" hint shows instead (no crash). Clicking a strategy navigates to `/trading-room/backtest?strategy=saved:<id>`.
- [ ] **Step 5: Commit** — `feat(nav): mount saved strategy library under 策略室 → 策略庫`

---

### Task 5: Home onboarding card (dismissible 3-step, localStorage)

**Files:** Create `frontend/components/Onboarding.tsx`; Modify `frontend/components/HomeDashboard.tsx` (render `<Onboarding/>` at top of the returned `<div className="space-y-4">`)
**Interfaces:**
- Consumes: `L.onboarding`.
- Produces: a dismissible card with three linked steps; dismissal persisted in `localStorage` under key `atf-onboarding-dismissed`.

DESIGN.md: cyan is AI-only — step ① (策略室, AI) may use a cyan dot; steps ②/③ use neutral tokens. Card uses `border-border bg-surface-1` like other home sections.

- [ ] **Step 1: Create `frontend/components/Onboarding.tsx`**

```tsx
"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { L } from "@/lib/labels";

const KEY = "atf-onboarding-dismissed";

const STEPS = [
  { href: "/strategy-lab", title: L.onboarding.step1Title, body: L.onboarding.step1Body, ai: true },
  { href: "/trading-room/backtest", title: L.onboarding.step2Title, body: L.onboarding.step2Body, ai: false },
  { href: "/schedules", title: L.onboarding.step3Title, body: L.onboarding.step3Body, ai: false },
];

export function Onboarding() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    // Read after mount to avoid SSR/client hydration mismatch.
    setShow(typeof window !== "undefined" && localStorage.getItem(KEY) !== "1");
  }, []);

  if (!show) return null;

  function dismiss() {
    try {
      localStorage.setItem(KEY, "1");
    } catch {
      /* private mode — best effort */
    }
    setShow(false);
  }

  return (
    <section className="rounded-lg border border-border bg-surface-1 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-display text-sm font-semibold text-muted">{L.onboarding.title}</h2>
        <button
          onClick={dismiss}
          className="rounded-md bg-surface-2 px-2 py-1 text-xs text-muted hover:bg-surface-3 hover:text-text"
        >
          {L.onboarding.dismiss}
        </button>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {STEPS.map((s) => (
          <Link
            key={s.href}
            href={s.href}
            className="group rounded-md border border-border bg-surface-2 p-3 hover:border-accent hover:bg-surface-3"
          >
            <div className="flex items-center gap-2">
              {s.ai && <span className="h-1.5 w-1.5 rounded-sm bg-accent" />}
              <span className="font-display text-sm font-semibold text-text">{s.title}</span>
            </div>
            <p className="mt-1 text-xs leading-relaxed text-muted">{s.body}</p>
          </Link>
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Render it in `HomeDashboard.tsx`.** Add `import { Onboarding } from "./Onboarding";` at the top (with the other imports). Then insert `<Onboarding />` as the first child of the outer `<div className="space-y-4">` (immediately before the `{/* Header band … */}` `<header>`):

```tsx
    <div className="space-y-4">
      <Onboarding />
      {/* Header band — context + controls. The big number lives on the chart, not here. */}
      <header className="flex flex-wrap items-end justify-between gap-3">
```

- [ ] **Step 3: `cd frontend && npx tsc --noEmit && npm run build`** — Expected: pass.
- [ ] **Step 4: run-app visual verify** — Use `run-app`. On the home page the 3-step card shows at top (① 策略室設計 / ② 交易室回測 / ③ 排程/實盤), step ① has a cyan dot, each card links to its route. Click 知道了 → card disappears; reload → still gone (localStorage). Clear `atf-onboarding-dismissed` in devtools → reappears.
- [ ] **Step 5: Commit** — `feat(home): add dismissible 3-step onboarding card`

---

### Task 6: i18n sweep — PortfolioPanel

**Files:** Modify `frontend/components/PortfolioPanel.tsx`
**Interfaces:** Consumes `L.portfolio`. Keep finance/value formatting; only swap visible English UI strings.

Exact English strings to convert (file → new value from `L.portfolio`):
- L24 `Portfolio` → `{L.portfolio.title}`
- L42 `Reset paper` → `{L.portfolio.resetPaper}`
- L47 `Portfolio error: {…}` → `{L.portfolio.error}：{(portfolio.error as Error).message}`
- L51 `Cash` → `label={L.portfolio.cash}`
- L52 `Positions` → `label={L.portfolio.positions}`
- L53 `Equity` → `label={L.portfolio.equity}`
- L59-63 table headers `Symbol/Qty/Avg/Price/uPnL` → `{L.portfolio.colSymbol}` / `colQty` / `colAvg` / `colPrice` / `colUpnl`
- L83 `Loading…` → `{L.portfolio.loading}`
- L86 `Recent orders` → `{L.portfolio.recentOrders}`
- L108 `No orders yet.` → `{L.portfolio.noOrders}`

Keep `o.side.toUpperCase()` (BUY/SELL chip — a state token, fine) and the `TRADING_MODE.toUpperCase()` chip (paper/live mode is a finance/system term). Add `import { L } from "@/lib/labels";`.

- [ ] **Step 1: Add the import and apply all the L24–L108 replacements above.**
- [ ] **Step 2: `cd frontend && npx tsc --noEmit && npm run build`** — Expected: pass.
- [ ] **Step 3: run-app visual verify** — Portfolio page header reads 投組, stats read 現金/部位市值/權益, table headers 中文, button 重置紙上帳戶.
- [ ] **Step 4: Commit** — `i18n(portfolio): convert visible English strings to L.portfolio`

---

### Task 7: i18n sweep — SchedulesPanel + NotificationsPanel

**Files:** Modify `frontend/components/SchedulesPanel.tsx`, `frontend/components/NotificationsPanel.tsx`
**Interfaces:** Consumes `L.schedules`, `L.notifications`.

**SchedulesPanel** — exact strings (file → `L.schedules`):
- L24 `Select a saved workflow first (…).` → `{L.schedules.selectWorkflow}`
- L49 `Schedules (auto-run)` → `{L.schedules.title}`
- L53 `workflow` label → `{L.schedules.workflow}`
- L59 `— select —` → `{L.schedules.selectPlaceholder}`
- L68 `every (s)` → `{L.schedules.everySeconds}`
- L82 `Schedule` → `{L.schedules.schedule}`
- L91-95 headers `Workflow/Interval/State/Last run/Last status` → `colWorkflow`(reuse `workflow`) / `colInterval` / `colState` / `colLastRun` / `colLastStatus`
- L111 `running`/`paused` → `{L.schedules.running}` / `{L.schedules.paused}`
- L122 `delete` → `{L.schedules.delete}`
- L130-132 `No schedules yet. …` → `{L.schedules.empty}`

(For the L91 `Workflow` header, reuse `{L.schedules.workflow}`.)

**NotificationsPanel** — exact strings (file → `L.notifications`):
- L30 `Notifications` → `{L.notifications.title}`
- L34 `Test` → `{L.notifications.test}`
- L57 `No notifications yet. Orders and signals appear here.` → `{L.notifications.empty}`

Add `import { L } from "@/lib/labels";` to both files.

- [ ] **Step 1: Apply SchedulesPanel replacements + import.**
- [ ] **Step 2: Apply NotificationsPanel replacements + import.**
- [ ] **Step 3: `cd frontend && npx tsc --noEmit && npm run build`** — Expected: pass.
- [ ] **Step 4: run-app visual verify** — Schedules page header 排程(自動執行), button 建立排程, state chips 執行中/已暫停, delete 刪除; Notifications header 通知, button 測試, empty hint 中文.
- [ ] **Step 5: Commit** — `i18n(schedules,notifications): convert visible English strings to L.*`

---

### Task 8: i18n sweep — DataImportPanel + final English grep

**Files:** Modify `frontend/components/DataImportPanel.tsx`; then grep the whole app
**Interfaces:** Consumes `L.dataImport`.

DataImportPanel is already mostly Chinese. The only remaining UI English is the symbol input placeholder (the CSV-format placeholder/sample is a literal data schema — **keep** as-is, it is not prose):
- L50 `placeholder="代號 (如 2330 / AAPL)"` → `placeholder={L.dataImport.symbolPlaceholder}` (normalizes spacing; value already 中文 but route it through labels for consistency)

Add `import { L } from "@/lib/labels";`.

- [ ] **Step 1: Apply the placeholder replacement + import.**
- [ ] **Step 2: Final English-UI grep** — run from `frontend/`:

```
cd frontend && grep -rnE '>[[:space:]]*(Run|Compare|Backtest|Portfolio|Schedule|Schedules|Notifications|Notification|Cash|Equity|Positions|Loading|Recent orders|Test|Symbol|Qty|Avg|Price|delete|running|paused|No [a-z])' components app | grep -v node_modules
```

Expected: no hits in panels owned by P4 (Portfolio/Schedules/Notifications/DataImport). Hits inside `MarketPanel`/`BacktestPanel` are **owned by P2** — do NOT touch them here (note them only). Finance tokens (Sharpe/RSI/CAGR/BUY/SELL/PAPER/LIVE) are intentionally retained per spec §F2 and are not flagged.

- [ ] **Step 3: `cd frontend && npx tsc --noEmit && npm run build`** — Expected: pass.
- [ ] **Step 4: run-app visual verify** — Data-import page unchanged visually except the symbol placeholder. Spot-check the whole app sidebar + the four tool panels render with no stray English UI verbs.
- [ ] **Step 5: Commit** — `i18n(data-import): route symbol placeholder through L; verify no stray English UI`

---

## Self-Review

**Spec §7 Area D requirement → task mapping**
| §7 D requirement | Task(s) |
|---|---|
| 側欄標籤補副標(`策略室 Strategy Lab` 中+英) | Task 1 (data) + Task 3 (render) |
| 策略庫掛入側欄(`api.listSavedStrategies`,client fetch) | Task 1 (anchor leaf) + Task 4 (StrategyLibraryTree) |
| 首頁三步引導(可點直達、可關、localStorage) | Task 5 (Onboarding) |
| 分組:排程/通知/匯入 歸「工具」 | Task 1 (工具 parent) |
| `NavItem` 增 `subtitle?` + 動態 children | Task 1 (subtitle) + Task 4 (dynamic library children) |
| 中文化掃描(非 P2 面板) | Task 6 (Portfolio) + Task 7 (Schedules/Notifications) + Task 8 (DataImport + grep) |
| active/live 規範沿用 DESIGN.md | Task 3 (cyan active, leaf.live branch kept) + Task 4 (saved leaves use cyan-active, never --live) |
| icon rail (<xl) 標籤隱藏含副標 | Task 3 (subtitle inside `.nav-label`) + Task 4 (library leaves inside `.nav-label`) |

**DESIGN.md «Navigation — Left Tree Menu» conformance check**
- Tree mirrors two-room IA (策略室 / 交易室) + grouped tools — ✅ Task 1 matches the documented tree (策略室 → 與 AI 設計策略 / 策略庫 → saved; 交易室 → 模擬回測 / 工作流).
- Depth ≤ 3 — ✅ deepest path is 策略室 → 策略庫 → strategy leaf (Task 4).
- Children indent 16px with 1px `--border` guide — ✅ reuse existing `ml-3 border-l border-border pl-1` (Task 4 mirrors TreeNav's existing child wrapper).
- Active leaf: cyan 2px left border + `--accent-dim` bg + `--text` — ✅ Tasks 3/4 reuse `border-accent bg-accent-dim text-text`.
- Hover `--surface-2` — ✅ `hover:bg-surface-2` reused.
- cyan = AI/active only; live leaves use `--live` dot — ✅ 策略室 keeps `ai:true` cyan dot; saved/library leaves never use `--live`; the `leaf.live` branch is preserved untouched for future 實際下單 leaves.
- Icon rail (`<xl`) hides labels via `.nav-label` — ✅ subtitles and library leaves wrapped in `.nav-label`; dots stay visible.
- Subtitle style = Chinese main + small muted English — ✅ `text-[11px] text-faint` under `font-display` main label.

**Placeholder / completeness scan**
- No `TODO`/`TBD`/placeholder code — all steps contain complete, compilable TSX.
- All `L.*` keys consumed by Tasks 4–8 are defined in Task 2 (`L.nav`, `L.onboarding`, `L.portfolio`, `L.schedules`, `L.notifications`, `L.dataImport`).
- Hard dependency on P1 (`@/lib/labels`, `@/components/Term`) is stated up front and fails loud if absent; `<Term>` is available but not required by this phase (nav subtitles are plain text, not glossary terms).
- P2 overlap on `lib/labels.ts` is additive and flagged in Global Constraints + Task 2.
- The `?strategy=saved:<id>` query param (Task 4) is intentionally a forward-link consumed by P5 — noted, not a gap.
- No backend changes; no new routes; no token hardcoding; every visible change has a run-app visual verify step.
