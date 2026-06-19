# 前端 A1:設計基礎 + 外殼 + 面板移入兩室 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the new two-room app shell (left tree nav + RWD) and DESIGN.md token foundation, and move the existing 8 panels into Next.js App Router routes — without changing what any panel does.

**Architecture:** A `(rooms)` route group shares an `AppShell` (sidebar tree + topbar + main); `/manual` stays outside it. DESIGN.md tokens land as CSS variables wired into Tailwind `theme.extend`; fonts via the `geist` package + `next/font/google`. Each panel moves into a thin route page, then is restyled to the tokens with market-aware up/down colors.

**Tech Stack:** Next.js 14 App Router, TypeScript, Tailwind CSS, @tanstack/react-query, @xyflow/react, lightweight-charts, `geist` font package.

**Spec:** [`docs/specs/2026-06-19-frontend-a1-shell-design.md`](../specs/2026-06-19-frontend-a1-shell-design.md)

## Global Constraints

- Work from `frontend/`. Verification gate per task = `npx tsc --noEmit` clean AND `npm run build` succeeds. No unit-test harness in A1 (per spec).
- Match existing code style: `"use client"` where hooks/interactivity used; Tailwind utility classes; `@/` path alias; functional components.
- Do NOT change panel data-fetching or `api` calls — only their location (route page) and styling.
- Accent cyan (`--accent`) is for AI / primary actions only. Financial figures use `.num`. Up/down via `--up`/`--down` tokens — never hardcode green=gain (台股 flips via `data-market="tw"`).
- Auth: `lib/api.ts` ALREADY sends `Authorization: Bearer` when `NEXT_PUBLIC_API_TOKEN` is set (came from the main merge) — verify, do not re-implement.
- Breakpoints: Tailwind defaults (md 768, xl 1280). Sidebar: ≥1280 pinned 240px, 768–1279 64px rail, <768 drawer.
- `/manual` route must remain working and unchanged.

---

## File Structure

- `frontend/tailwind.config.ts` — extend colors/fonts/radii (modify)
- `frontend/app/globals.css` — CSS variable tokens + `.num` + market flip (modify)
- `frontend/app/layout.tsx` — fonts + font CSS vars on `<html>` (modify)
- `frontend/app/page.tsx` — redirect → `/strategy-lab` (replace)
- `frontend/app/(rooms)/layout.tsx` — renders `<AppShell>` (create)
- `frontend/app/(rooms)/<route>/page.tsx` — 8 route pages + strategy-lab placeholder (create)
- `frontend/components/shell/{AppShell,Sidebar,TreeNav,TopBar}.tsx` — shell (create)
- `frontend/lib/nav.ts` — tree config (create)
- panel components + `CandleChart.tsx` — restyle (modify, Task 4)

---

## Task 1: Design-token foundation + fonts

**Files:**
- Modify: `frontend/tailwind.config.ts`, `frontend/app/globals.css`, `frontend/app/layout.tsx`
- Add dep: `geist`

**Interfaces:**
- Produces: Tailwind color names `bg, surface-1/2/3, border, border-strong, text, muted, faint, accent, accent-dim, up, down, warning, error, live`; font families `font-display/ui/mono/code`; radii `rounded-sm/md/lg`; a `.num` utility; `data-market` flip on `<html>`.

- [ ] **Step 1: Install the Geist font package**

```bash
cd frontend && npm install geist
```

- [ ] **Step 2: Write `app/globals.css` (tokens + utility)**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  color-scheme: dark;
  --bg: #0A0B0D; --surface-1: #111317; --surface-2: #16181D; --surface-3: #1E2127;
  --border: rgba(255,255,255,0.08); --border-strong: rgba(255,255,255,0.14);
  --text: #E7E9EC; --muted: #8A9099; --faint: #5B616B;
  --accent: #22D3EE; --accent-dim: rgba(34,211,238,0.14);
  --up: #34D399; --down: #F87171;
  --warning: #FBBF24; --error: #EF4444; --live: #FB7185;
  /* font CSS vars are bound to the geist package + next/font in layout.tsx */
  --font-ui: var(--font-geist-sans); --font-mono: var(--font-geist-mono);
}
[data-market="tw"] { --up: #F05252; --down: #31C48D; }

body { @apply bg-bg text-text font-ui; }

.num { font-family: var(--font-mono); font-variant-numeric: tabular-nums; }
```

- [ ] **Step 3: Write `tailwind.config.ts`**

```ts
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        "surface-1": "var(--surface-1)", "surface-2": "var(--surface-2)", "surface-3": "var(--surface-3)",
        border: "var(--border)", "border-strong": "var(--border-strong)",
        text: "var(--text)", muted: "var(--muted)", faint: "var(--faint)",
        accent: "var(--accent)", "accent-dim": "var(--accent-dim)",
        up: "var(--up)", down: "var(--down)",
        warning: "var(--warning)", error: "var(--error)", live: "var(--live)",
      },
      fontFamily: {
        display: ["var(--font-display)", "var(--font-ui)", "sans-serif"],
        ui: ["var(--font-ui)", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
        code: ["var(--font-code)", "monospace"],
      },
      borderRadius: { sm: "4px", md: "6px", lg: "8px" },
    },
  },
  plugins: [],
};
export default config;
```

- [ ] **Step 4: Wire fonts in `app/layout.tsx`**

```tsx
import type { Metadata } from "next";
import { Space_Grotesk, JetBrains_Mono } from "next/font/google";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import "./globals.css";
import "@xyflow/react/dist/style.css";
import { Providers } from "./providers";

const display = Space_Grotesk({ subsets: ["latin"], variable: "--font-display", display: "swap" });
const code = JetBrains_Mono({ subsets: ["latin"], variable: "--font-code", display: "swap" });

export const metadata: Metadata = {
  title: "AI Trade Flow",
  description: "AI-driven auto-trading platform — crypto / 台股 / 美股",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${GeistSans.variable} ${GeistMono.variable} ${display.variable} ${code.variable}`}
    >
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

- [ ] **Step 5: Verify**

```bash
cd frontend && npx tsc --noEmit && npm run build
```
Expected: typecheck clean; build succeeds (fonts resolve, no Tailwind errors). The existing `app/page.tsx` still builds (untouched this task).

- [ ] **Step 6: Commit**

```bash
git add frontend/tailwind.config.ts frontend/app/globals.css frontend/app/layout.tsx frontend/package.json frontend/package-lock.json
git commit -m "feat(fe): DESIGN.md design tokens + font foundation"
```

---

## Task 2: App shell + tree nav + RWD + first routes

**Files:**
- Create: `frontend/lib/nav.ts`, `frontend/components/shell/{AppShell,Sidebar,TreeNav,TopBar}.tsx`, `frontend/app/(rooms)/layout.tsx`, `frontend/app/(rooms)/strategy-lab/page.tsx`, `frontend/app/(rooms)/trading-room/page.tsx`, `frontend/app/(rooms)/trading-room/backtest/page.tsx`
- Replace: `frontend/app/page.tsx` (→ redirect)

**Interfaces:**
- Consumes: Task 1 tokens/fonts; existing `components/BacktestPanel`.
- Produces: `NAV` tree (`lib/nav.ts`), `<AppShell>` wrapping `{children}`, working tree nav with active state, RWD sidebar (pinned/rail/drawer).

- [ ] **Step 1: Write the nav config `lib/nav.ts`**

```ts
export interface NavLeaf { label: string; href: string; live?: boolean }
export interface NavItem { label: string; href?: string; ai?: boolean; children?: NavLeaf[] }

export const NAV: NavItem[] = [
  { label: "策略室", href: "/strategy-lab", ai: true },
  { label: "交易室", href: "/trading-room", children: [
    { label: "模擬回測", href: "/trading-room/backtest" },
    { label: "工作流", href: "/trading-room/workflow" },
  ]},
  { label: "市場", href: "/market" },
  { label: "投組", href: "/portfolio" },
  { label: "排程", href: "/schedules" },
  { label: "通知", href: "/notifications" },
  { label: "匯入", href: "/data-import" },
];
```

- [ ] **Step 2: Write `components/shell/TreeNav.tsx`**

```tsx
"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV, type NavItem } from "@/lib/nav";

function isActive(pathname: string, href?: string) {
  return !!href && (pathname === href || pathname.startsWith(href + "/"));
}

export function TreeNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav className="flex-1 overflow-y-auto p-2 text-sm">
      {NAV.map((item) => (
        <TreeRow key={item.label} item={item} pathname={pathname} onNavigate={onNavigate} />
      ))}
    </nav>
  );
}

function TreeRow({ item, pathname, onNavigate }: { item: NavItem; pathname: string; onNavigate?: () => void }) {
  const active = isActive(pathname, item.href);
  const dot = item.ai ? "bg-accent" : "bg-faint";
  return (
    <div>
      <Link
        href={item.href ?? "#"}
        onClick={onNavigate}
        className={`flex items-center gap-2 rounded-md border-l-2 px-3 py-2 ${
          active ? "border-accent bg-accent-dim text-text" : "border-transparent text-muted hover:bg-surface-2"
        }`}
      >
        <span className={`h-1.5 w-1.5 rounded-sm ${dot}`} />
        <span className="nav-label font-display font-semibold">{item.label}</span>
      </Link>
      {item.children && (
        <div className="ml-3 border-l border-border pl-1">
          {item.children.map((leaf) => {
            const la = isActive(pathname, leaf.href);
            return (
              <Link
                key={leaf.href}
                href={leaf.href}
                onClick={onNavigate}
                className={`flex items-center gap-2 rounded-md border-l-2 px-3 py-2 text-[13px] ${
                  la ? `${leaf.live ? "border-live text-live" : "border-accent text-text"} bg-accent-dim`
                     : "border-transparent text-muted hover:bg-surface-2"
                }`}
              >
                <span className="nav-label">{leaf.label}</span>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Write `components/shell/Sidebar.tsx` and `TopBar.tsx`**

```tsx
// components/shell/Sidebar.tsx
import { TreeNav } from "./TreeNav";

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <aside className="flex h-full flex-col bg-surface-1">
      <div className="flex items-center gap-2 border-b border-border px-4 py-4">
        <span className="font-display text-base font-bold">
          AI Trade Flow<span className="text-accent">.</span>
        </span>
      </div>
      <TreeNav onNavigate={onNavigate} />
    </aside>
  );
}
```

```tsx
// components/shell/TopBar.tsx
"use client";
export function TopBar({ onMenu }: { onMenu: () => void }) {
  return (
    <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-border bg-bg/85 px-4 py-3 backdrop-blur">
      <button
        onClick={onMenu}
        aria-label="menu"
        className="rounded-md border border-border-strong bg-surface-2 px-2.5 py-1.5 text-text md:hidden"
      >
        ☰
      </button>
      <span className="font-display text-sm font-bold md:hidden">
        AI Trade Flow<span className="text-accent">.</span>
      </span>
    </header>
  );
}
```

- [ ] **Step 4: Write `components/shell/AppShell.tsx` (RWD: pinned / rail / drawer)**

```tsx
"use client";
import { useState } from "react";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="min-h-dvh md:grid md:grid-cols-[64px_1fr] xl:grid-cols-[240px_1fr]">
      {/* desktop/tablet sidebar; labels hidden in rail (<xl) via .nav-label */}
      <div className="hidden md:block sticky top-0 h-dvh border-r border-border [&_.nav-label]:hidden xl:[&_.nav-label]:inline">
        <Sidebar />
      </div>
      {/* mobile drawer */}
      {open && <div className="fixed inset-0 z-30 bg-black/55 md:hidden" onClick={() => setOpen(false)} />}
      <div
        className={`fixed inset-y-0 left-0 z-40 w-[240px] transition-transform md:hidden ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <Sidebar onNavigate={() => setOpen(false)} />
      </div>
      <div className="min-w-0">
        <TopBar onMenu={() => setOpen(true)} />
        <main className="mx-auto max-w-[1440px] p-4">{children}</main>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Write `app/(rooms)/layout.tsx`, the redirect, and first routes**

```tsx
// app/(rooms)/layout.tsx
import { AppShell } from "@/components/shell/AppShell";
export default function RoomsLayout({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
```

```tsx
// app/page.tsx
import { redirect } from "next/navigation";
export default function Home() { redirect("/strategy-lab"); }
```

```tsx
// app/(rooms)/strategy-lab/page.tsx
export default function StrategyLabPage() {
  return (
    <section className="rounded-lg border border-border bg-surface-1 p-6">
      <h1 className="font-display text-xl font-bold">策略室 · Strategy Lab</h1>
      <p className="mt-2 text-muted">AI 策略設計與策略庫 — 即將推出 (A2)。</p>
    </section>
  );
}
```

```tsx
// app/(rooms)/trading-room/page.tsx
import { redirect } from "next/navigation";
export default function TradingRoom() { redirect("/trading-room/backtest"); }
```

```tsx
// app/(rooms)/trading-room/backtest/page.tsx
import { BacktestPanel } from "@/components/BacktestPanel";
export default function BacktestPage() { return <BacktestPanel />; }
```

- [ ] **Step 6: Verify (build + dogfood)**

```bash
cd frontend && npx tsc --noEmit && npm run build
```
Expected: clean. Then dogfood with the gstack browse binary (`~/.claude/skills/gstack/browse/dist/browse`) against `npm run dev`:
```bash
npm run dev &   # wait for :3000
B=~/.claude/skills/gstack/browse/dist/browse
$B goto http://localhost:3000/        # redirects to /strategy-lab; shell + tree visible
$B screenshot /tmp/a1-desktop.png
$B viewport 1024 800 && $B screenshot /tmp/a1-rail.png    # 64px icon rail (labels hidden)
$B viewport 390 844 && $B screenshot /tmp/a1-mobile.png   # hamburger; click → drawer
$B goto http://localhost:3000/trading-room/backtest       # BacktestPanel renders in shell
```
Expected: active tree item highlighted; rail hides labels at 1024; drawer opens on mobile; backtest route renders the panel.

- [ ] **Step 7: Commit**

```bash
git add frontend/lib/nav.ts frontend/components/shell frontend/app/\(rooms\) frontend/app/page.tsx
git commit -m "feat(fe): app shell — left tree nav, RWD rail/drawer, room routing"
```

---

## Task 3: Remaining route pages + remove old stacked page

**Files:**
- Create: `frontend/app/(rooms)/{trading-room/workflow,market,portfolio,schedules,notifications,data-import}/page.tsx`

**Interfaces:**
- Consumes: existing panels (`WorkflowBuilder`, `MarketPanel`, `PortfolioPanel`, `SchedulesPanel`, `NotificationsPanel`, `DataImportPanel`); the `(rooms)` layout from Task 2.

- [ ] **Step 1: Create the six route pages**

```tsx
// app/(rooms)/trading-room/workflow/page.tsx
import { WorkflowBuilder } from "@/components/workflow/WorkflowBuilder";
export default function WorkflowPage() { return <WorkflowBuilder />; }
```
```tsx
// app/(rooms)/market/page.tsx
import { MarketPanel } from "@/components/MarketPanel";
export default function MarketPage() { return <MarketPanel />; }
```
```tsx
// app/(rooms)/portfolio/page.tsx
import { PortfolioPanel } from "@/components/PortfolioPanel";
export default function PortfolioPage() { return <PortfolioPanel />; }
```
```tsx
// app/(rooms)/schedules/page.tsx
import { SchedulesPanel } from "@/components/SchedulesPanel";
export default function SchedulesPage() { return <SchedulesPanel />; }
```
```tsx
// app/(rooms)/notifications/page.tsx
import { NotificationsPanel } from "@/components/NotificationsPanel";
export default function NotificationsPage() { return <NotificationsPanel />; }
```
```tsx
// app/(rooms)/data-import/page.tsx
import { DataImportPanel } from "@/components/DataImportPanel";
export default function DataImportPage() { return <DataImportPanel />; }
```

- [ ] **Step 2: Confirm the old stacked page is gone**

`app/page.tsx` was replaced by the redirect in Task 2. Verify no other file imports the panels as a single stacked page (grep): `grep -rn "MarketPanel\|PortfolioPanel" app | grep -v "(rooms)"` → only the route pages.

- [ ] **Step 3: Verify (build + dogfood)**

```bash
cd frontend && npx tsc --noEmit && npm run build
```
Then with `npm run dev` + browse, visit each route and confirm the panel renders inside the shell:
`/trading-room/workflow`, `/market`, `/portfolio`, `/schedules`, `/notifications`, `/data-import`, and `/manual` (must still work, no shell). Screenshot `/portfolio` and `/market` for the record.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/\(rooms\)
git commit -m "feat(fe): route pages for workflow, market, portfolio, schedules, notifications, import"
```

---

## Task 4: Restyle panels to tokens + market-aware up/down

**Files:**
- Create: `frontend/lib/useMarket.ts` (sets `data-market` on `<html>`)
- Modify: `frontend/components/{MarketPanel,PortfolioPanel,BacktestPanel,SchedulesPanel,NotificationsPanel,DataImportPanel}.tsx`, `frontend/components/CandleChart.tsx`, `frontend/components/workflow/{WorkflowBuilder,TradeNode}.tsx`

**Interfaces:**
- Consumes: Task 1 token classes (`bg-surface-1`, `border-border`, `text-up`, `text-down`, `.num`, `text-accent`).
- Produces: `setMarket(market: string)` helper that sets `document.documentElement.dataset.market` (`"tw"` for `tw_stock`, else removed).

- [ ] **Step 1: Write `lib/useMarket.ts`**

```ts
// Sets data-market on <html> so --up/--down flip for 台股 (red-up). Call when the active market changes.
export function setMarket(market: string) {
  if (typeof document === "undefined") return;
  if (market === "tw_stock") document.documentElement.dataset.market = "tw";
  else delete document.documentElement.dataset.market;
}
```

- [ ] **Step 2: Restyle the panels — token swap (apply across all listed panels)**

Replace the legacy neutral/red/green Tailwind classes with tokens. The mechanical mapping to apply in every panel:
- `border-neutral-800` → `border-border`; `bg-neutral-900/40` / `bg-neutral-900` → `bg-surface-1`; `bg-neutral-800` → `bg-surface-2`; `hover:bg-neutral-700` → `hover:bg-surface-3`
- `text-neutral-500` → `text-faint`; `text-neutral-400` → `text-muted`
- price/PnL gains: `text-green-*` → `text-up`; losses/errors on prices: `text-red-*` → `text-down`; **system** errors (e.g. `Portfolio error:`) stay `text-error`
- buy badges `bg-green-700` → `bg-up/15 text-up`; sell `bg-red-600` → `bg-down/15 text-down`; **live mode** badge → `bg-live/15 text-live`
- headings: add `font-display`; section cards use `rounded-lg`
- wrap every numeric/price/qty/PnL cell value in the `.num` class (add `className="num"`), e.g. `<td className="num">{money(x)}</td>`

Concrete example — `PortfolioPanel.tsx` header + a figure:
```tsx
<section className="rounded-lg border border-border bg-surface-1 p-4">
  <div className="mb-3 flex items-center gap-2">
    <h2 className="font-display text-lg font-semibold">Portfolio</h2>
    {config.data && (
      <span className={`rounded-sm px-2 py-0.5 text-xs font-medium ${
        config.data.trading_mode === "live" ? "bg-live/15 text-live" : "bg-surface-3 text-muted"
      }`}>{config.data.trading_mode.toUpperCase()}</span>
    )}
    {/* …Reset button → bg-surface-2 hover:bg-surface-3… */}
  </div>
  {/* unrealized pnl cell: */}
  <td className={`num ${pos.unrealized_pnl >= 0 ? "text-up" : "text-down"}`}>{money(pos.unrealized_pnl)}</td>
</section>
```
Apply the same token mapping to `MarketPanel`, `BacktestPanel`, `SchedulesPanel`, `NotificationsPanel`, `DataImportPanel`, and `workflow/{WorkflowBuilder,TradeNode}` (cards/borders/text only — do NOT change builder behavior; A3 rebuilds it).

- [ ] **Step 3: Wire `setMarket` where the market changes**

In `MarketPanel.tsx` (and `BacktestPanel.tsx`) where the user picks a market, call `setMarket(market)` in an effect on the selected market value:
```tsx
import { useEffect } from "react";
import { setMarket } from "@/lib/useMarket";
// inside component, with `market` state:
useEffect(() => { setMarket(market); }, [market]);
```

- [ ] **Step 4: CandleChart token colors**

In `components/CandleChart.tsx`, read the up/down colors from CSS vars so the chart honors the market flip:
```tsx
const css = getComputedStyle(document.documentElement);
const up = css.getPropertyValue("--up").trim() || "#34D399";
const down = css.getPropertyValue("--down").trim() || "#F87171";
// pass up/down to series options (upColor/borderUpColor/wickUpColor = up; down equivalents = down)
```

- [ ] **Step 5: Verify (build + dogfood before/after)**

```bash
cd frontend && npx tsc --noEmit && npm run build
```
Then with `npm run dev` + browse: screenshot `/portfolio`, `/market`, `/trading-room/backtest` (terminal-dark, mono figures, cyan accent only on primary/AI). On `/market`, switch the symbol to a 台股 market and confirm gains turn **red** and losses **green** (the `data-market="tw"` flip); capture before/after.

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/useMarket.ts frontend/components
git commit -m "feat(fe): restyle panels to design tokens + market-aware up/down colors"
```

---

## Self-Review

**Spec coverage:**
- Tokens/fonts/.num/market flip → Task 1. Shell + tree + RWD + routing + redirect → Task 2. Remaining routes + old-page removal → Task 3. Panel restyle + market-aware up/down + CandleChart + `data-market` → Task 4. Auth → already present (Global Constraints, verify-only). 策略室 placeholder → Task 2. `/manual` untouched → verified Task 3.
- All spec sections covered.

**Placeholder scan:** none — every step has concrete code/commands. Task 4's per-panel restyle gives the exact class mapping + a worked example rather than re-printing all six files (mechanical, same mapping); this is a deliberate DRY instruction, not a vague placeholder.

**Type consistency:** `NAV`/`NavItem`/`NavLeaf` (lib/nav.ts) consumed by TreeNav; `AppShell`/`Sidebar`/`TopBar`/`TreeNav` prop shapes (`onNavigate?`, `onMenu`) consistent; `setMarket(market: string)` defined Task 4 Step 1, used Steps 3. Tailwind token names match Task 1's config exactly.

**Verification note:** per the approved spec there is NO unit-test harness; each task's gate is `tsc --noEmit` + `npm run build` + browser dogfood. This replaces the TDD red/green rhythm intentionally for a layout/shell increment.

## Out of scope (later increments)
- **A2** 策略室 AI chat + library (wired to `/api/strategies`).
- **A3** rebuild workflow builder (palette/canvas/inspector, node categories, backtest/live modes).
- Vitest/RTL harness; reconciliation with main's merged logic nodes.
