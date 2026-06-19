# Spec — 前端 A1:設計基礎 + 外殼 + 面板移入兩室

> Status: **approved design**, pre-implementation. First increment of front-end sub-project A
> (the new two-room design). Source of visual truth: [`DESIGN.md`](../../DESIGN.md).
> Build order within A: **A1 (this) → A2 策略室 → A3 交易室 builder**.
> Backend it integrates with: post-merge `main` (sub-project B `/api/strategies` + v2 wave:
> bearer-token auth, logic nodes, ledger, FX, risk).

## Goal

Stand up the new app shell and design-system foundation, and move the existing 8 panels into a
two-room, tree-navigated, responsive layout — without changing what any panel *does*. After A1
the product looks like DESIGN.md and navigates by the left tree; existing features keep working.
策略室's AI features (A2) and the rebuilt workflow builder (A3) are out of scope here.

## Decisions (locked in brainstorming)

1. **Navigation = Next.js App Router routes** (not in-page state). Rooms/sub-items are real URLs;
   the tree menu is `<Link>`s with active state from `usePathname()`. Deep-linkable, back/forward works.
2. **IA = flat top-level tree.** 策略室 and 交易室 are the two main rooms; Market / Portfolio /
   Schedules / Notifications / DataImport are top-level siblings (not nested under a room).
3. **Restyle depth = consistent design-system application, not pixel-perfect.** Tokens, fonts,
   `.num` tabular-mono figures, market-aware up/down, accent discipline across all migrated panels.
4. **Verification = build + typecheck + browser dogfood** (no new unit-test harness in A1).

## Design tokens (foundation)

Wire `DESIGN.md` into `tailwind.config.ts` `theme.extend` + `globals.css`:

- **Colors** as CSS variables on `:root` (dark): `--bg #0A0B0D`, `--surface-1/2/3`,
  `--border`, `--border-strong`, `--text/-muted/-faint`, `--accent #22D3EE` (+ `--accent-dim`),
  `--up`/`--down` (default green/red), `--warning`, `--error`, `--live #FB7185`. Exposed to Tailwind
  as `bg-surface-1`, `text-muted`, `border-accent`, etc.
- **Market-aware up/down:** `[data-market="tw"]` on `<html>` overrides `--up`/`--down` (台股 red-up).
  A small client helper sets `data-market` from the active symbol/market.
- **Radii:** `--r-sm 4`, `--r-md 6`, `--r-lg 8` → Tailwind `rounded-sm/md/lg` overrides.
- **Fonts** via `next/font/google`: Space Grotesk (display), Geist (ui/body), Geist Mono (data),
  JetBrains Mono (code); bound to CSS vars + Tailwind `font-display/ui/mono/code`. `Noto Sans TC`
  fallback for CJK.
- **`.num` utility:** `font-mono` + `tabular-nums` for every financial figure.

## App Router structure

```
frontend/app/
  layout.tsx                  fonts + <Providers> (existing react-query)
  page.tsx                    redirect → /strategy-lab
  (rooms)/
    layout.tsx                <AppShell>: Sidebar tree + TopBar + <main>{children}</main>
    strategy-lab/page.tsx     策略室 — A1 placeholder ("AI 策略設計 — 即將推出 (A2)")
    trading-room/
      backtest/page.tsx       ← BacktestPanel
      workflow/page.tsx       ← WorkflowBuilder (restyled only)
    market/page.tsx           ← MarketPanel (+ CandleChart)
    portfolio/page.tsx        ← PortfolioPanel
    schedules/page.tsx        ← SchedulesPanel
    notifications/page.tsx    ← NotificationsPanel
    data-import/page.tsx      ← DataImportPanel
  manual/                     unchanged
components/shell/
  AppShell.tsx                grid: sidebar | (topbar + main); owns drawer open state
  Sidebar.tsx + TreeNav.tsx   tree items as <Link>, active via usePathname()
  TopBar.tsx                  hamburger (mobile) + market/theme controls
```

`/trading-room` redirects to `/trading-room/backtest`.

### Tree (Sidebar)

```
策略室 Strategy Lab        /strategy-lab            (cyan dot — AI room)
交易室 Trading Room        /trading-room
  模擬回測 Backtest          /trading-room/backtest
  工作流 Workflow            /trading-room/workflow
市場 Market                /market
投組 Portfolio             /portfolio
排程 Schedules             /schedules
通知 Notifications         /notifications
匯入 Import                /data-import
```
Active leaf: cyan left-border + `--accent-dim` bg. Parent rows expand/collapse (chevron). Depth ≤ 3.

### Responsive (RWD)

Per DESIGN.md, sidebar drives the mode (Tailwind breakpoints):
- **≥1280 (xl):** pinned 240px tree.
- **768–1279 (md–lg):** 64px icon rail.
- **<768:** off-canvas drawer behind a hamburger; backdrop scrim; closes on nav select / Esc / scrim
  click; focus trapped while open; nav rows ≥44px touch. `AppShell` holds `drawerOpen` state.

## Auth wiring

`lib/api.ts` `request()` adds `Authorization: Bearer ${process.env.NEXT_PUBLIC_API_TOKEN}` **only when
the env var is non-empty** (local dev with backend auth disabled keeps working). `.env.example`
already documents `NEXT_PUBLIC_API_TOKEN`. No other api-client behavior changes.

## Panel migration

Each panel moves into its route page intact — same react-query hooks, same `api` calls, same logic.
Restyle each to the design system:
- token surfaces + fonts + sharp radii,
- **`.num` tabular-mono on all figures**, **market-aware `--up`/`--down`** on prices/PnL/order sides
  (replaces current hardcoded green/red — the visible headline change),
- cyan accent only on AI/primary actions,
- `data-market` set from the active market so 台股 flips up/down.
`CandleChart` reads up/down series colors from `--up`/`--down`.
The old stacked `app/page.tsx` is replaced by the redirect + per-route pages. `/manual` untouched.

## Out of scope (later increments)
- **A2** 策略室: AI chat → spec → rendered Python + adjustable params → strategy library
  (wired to `/api/strategies`). A1 leaves a placeholder page.
- **A3** 交易室: rebuild the workflow builder (palette/canvas/inspector, node categories,
  strategy nodes referencing the library, backtest/live modes). A1 only restyles the existing builder.
- No new unit-test harness (Vitest/RTL) — deferred to A2/A3 where there's logic worth unit-testing.
- Reconciling with main's already-merged logic nodes (sub-project C) — separate follow-up.

## Verification

- `npm run build` and `tsc` clean (the repo's existing frontend gate).
- Browser dogfood (gstack `browse`): every route renders; tree active-state correct; RWD at
  1440 / 1024 / 390 widths (pinned / rail / drawer); 台股 market flips up/down colors. Before/after
  screenshots captured.

## New / touched files
- New: `tailwind.config.ts` (extend), `globals.css` (tokens), `app/(rooms)/layout.tsx`,
  `app/(rooms)/**/page.tsx` (8 routes + strategy-lab placeholder), `app/page.tsx` (redirect),
  `components/shell/{AppShell,Sidebar,TreeNav,TopBar}.tsx`, a `useMarket`/`data-market` helper.
- Touch: `app/layout.tsx` (fonts), `lib/api.ts` (bearer header), each panel component (restyle),
  `components/CandleChart.tsx` (token colors), `components/workflow/{WorkflowBuilder,TradeNode}.tsx`
  (restyle only). Remove old `app/page.tsx` stacked layout.
