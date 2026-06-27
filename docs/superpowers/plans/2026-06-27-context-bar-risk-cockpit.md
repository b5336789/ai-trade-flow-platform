# Global Context Bar + Risk Cockpit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the empty top bar into a cross-page **Global Context Bar** (single market selector → drives `data-market` globally; mode chip; active-market equity + today's PnL; risk chip), and surface the already-built-but-UI-less risk controls as a **Risk Cockpit** page (kill-switch / resume / limit usage), wiring the three `/api/risk/*` endpoints the frontend currently never calls.

**Architecture:** Frontend-only. A new `MarketProvider` becomes the single source of truth for the active market and the *only* place that sets `data-market` on `<html>` (fixing cross-page color residue + the `StrategyLibrary`/`DataImportPanel` no-`setMarket` bug). `TopBar` is rebuilt into the Context Bar consuming that context + `react-query` reads of `api.config` (mode) and a new `api.riskStatus` (equity/PnL/risk). A new `/risk` route renders the cockpit. The six panels migrate from their local `market` state to `useActiveMarket()`.

**Tech Stack:** Next.js 14 App Router + TypeScript + React (client components) + TanStack React Query (already in use) + Tailwind (design tokens) + lucide-react icons. No backend changes. **No frontend test runner** (CI does `npm ci` + `npm run build`).

## Global Constraints

- **Branch, never `main`.** Work on `feat/context-bar-risk-cockpit`; open a PR at the end.
- **DESIGN.md tokens (verbatim):** `--accent` (cyan) is **AI/automation only** — never for market/mode/risk UI. `--live` (`#FB7185`) marks **real-money / LIVE only**; the LIVE mode chip is the one place a pulse animation is allowed. Danger = `--warning` / `--error`. Price up/down via `--up`/`--down` (台股 inverts via `data-market="tw"`) — never hardcode green-as-gain; today's-PnL coloring goes through `--up`/`--down`. Numbers use the `.num` class (tabular). Tight radii.
- **`data-market` is set in exactly ONE place** after this work: the `MarketProvider`. No component calls the old `lib/useMarket.ts:setMarket` afterward.
- **Fail loud:** risk/config query errors render an explicit error state; never a silent blank.
- **No new dependencies.** lucide-react, react-query, next are already present.
- **Verify command (frontend):** `cd frontend && npx tsc --noEmit` (per-task typecheck) and `cd frontend && npm run build` (authoritative, run by the controller after each wave). There is no unit-test runner.

---

### Task 1: `MarketProvider` — global active-market context (single `data-market` owner)

**Files:**
- Create: `frontend/lib/market-context.tsx`
- Modify: `frontend/app/providers.tsx` (wrap children in `MarketProvider`)

**Interfaces:**
- Produces: `MarketProvider` (component) and `useActiveMarket(): { market: string; setMarket: (m: string) => void }`. `setMarket` updates state, sets/clears `document.documentElement.dataset.market` (`"tw"` for `tw_stock`, removed otherwise), and persists to `localStorage["active-market"]`. Consumed by Tasks 3, 4, 5.

- [ ] **Step 1: Create the context** — `frontend/lib/market-context.tsx`:

```tsx
"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";

const STORAGE_KEY = "active-market";
const DEFAULT_MARKET = "crypto";

/** The ONLY place that drives --up/--down inversion for 台股 (red-up). */
function applyDataMarket(market: string) {
  if (typeof document === "undefined") return;
  if (market === "tw_stock") document.documentElement.dataset.market = "tw";
  else delete document.documentElement.dataset.market;
}

interface MarketContextValue {
  market: string;
  setMarket: (m: string) => void;
}

const MarketContext = createContext<MarketContextValue | null>(null);

export function MarketProvider({ children }: { children: React.ReactNode }) {
  const [market, setMarketState] = useState<string>(DEFAULT_MARKET);

  // Hydrate from localStorage once, and apply data-market for the restored market.
  useEffect(() => {
    const stored = typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null;
    const m = stored || DEFAULT_MARKET;
    setMarketState(m);
    applyDataMarket(m);
  }, []);

  const setMarket = useCallback((m: string) => {
    setMarketState(m);
    applyDataMarket(m);
    if (typeof window !== "undefined") localStorage.setItem(STORAGE_KEY, m);
  }, []);

  return <MarketContext.Provider value={{ market, setMarket }}>{children}</MarketContext.Provider>;
}

export function useActiveMarket(): MarketContextValue {
  const ctx = useContext(MarketContext);
  if (!ctx) throw new Error("useActiveMarket must be used within MarketProvider");
  return ctx;
}
```

- [ ] **Step 2: Wire it into Providers** — in `frontend/app/providers.tsx`, add the import after line 11:

```tsx
import { MarketProvider } from "@/lib/market-context";
```

and wrap the children inside `ThemeProvider` (replace the `Providers` return, lines 85-89):

```tsx
  return (
    <QueryClientProvider client={client}>
      <ThemeProvider>
        <MarketProvider>{children}</MarketProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
```

- [ ] **Step 3: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit** — (controller handles git; if running solo: `git add frontend/lib/market-context.tsx frontend/app/providers.tsx && git commit -m "feat(shell): MarketProvider — global active-market context"`)

---

### Task 2: Risk API client methods

**Files:**
- Modify: `frontend/lib/api.ts` (add `RiskStatus` interface + 3 methods)

**Interfaces:**
- Produces: `RiskStatus` interface (mirrors backend `app/api/risk.py:RiskStatus`); `api.riskStatus(market?)`, `api.setKillSwitch(engaged)`, `api.resumeRisk()`. Consumed by Tasks 3, 4.

- [ ] **Step 1: Add the interface** — in `frontend/lib/api.ts`, after the `AppConfig` interface (after line 67):

```typescript
export interface RiskStatus {
  kill_switch: boolean; // effective: config OR runtime
  kill_switch_config: boolean;
  kill_switch_runtime: boolean;
  halted: boolean;
  base_currency: string;
  max_total_exposure_value: number;
  max_daily_loss: number;
  max_orders_per_day: number;
  orders_today: number;
  exposure_base: number;
  equity_base: number;
  day_start_equity_base: number;
}
```

- [ ] **Step 2: Add the client methods** — inside the `api` object, after the `resetPaper` method (after line 414):

```typescript
  riskStatus: (market = "crypto") =>
    request<RiskStatus>(`/api/risk/status?market=${market}`),
  setKillSwitch: (engaged: boolean) =>
    request<{ kill_switch: boolean }>(`/api/risk/kill-switch?engaged=${engaged}`, { method: "POST" }),
  resumeRisk: () => request<{ halted: boolean }>("/api/risk/resume", { method: "POST" }),
```

- [ ] **Step 3: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit** — `feat(api): risk status + kill-switch + resume client methods`

---

### Task 3: Global Context Bar (rebuild `TopBar`)

**Files:**
- Modify: `frontend/components/shell/TopBar.tsx` (full rewrite of the `ml-auto` content + add a market selector)

**Interfaces:**
- Consumes: `useActiveMarket` (T1), `api.config` + `api.riskStatus` (T2), `MARKETS` from `@/lib/api`.
- Produces: the persistent context bar. No new exports.

- [ ] **Step 1: Rewrite `TopBar.tsx`** — replace the whole file with:

```tsx
"use client";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ShieldAlert } from "lucide-react";

import { ThemeToggle } from "@/components/shell/ThemeToggle";
import { api, MARKETS } from "@/lib/api";
import { useActiveMarket } from "@/lib/market-context";

function money(n: number) {
  return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

export function TopBar({ open, onMenu }: { open: boolean; onMenu: () => void }) {
  const { market, setMarket } = useActiveMarket();
  const config = useQuery({ queryKey: ["config"], queryFn: api.config, retry: false });
  const risk = useQuery({
    queryKey: ["risk-status", market],
    queryFn: () => api.riskStatus(market),
    refetchInterval: 5000,
    retry: false,
  });

  const live = config.data?.trading_mode === "live";
  const s = risk.data;
  const todayPnl = s ? s.equity_base - s.day_start_equity_base : 0;
  const danger = !!s && (s.kill_switch || s.halted);

  return (
    <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-border bg-bg/85 px-4 py-2.5 backdrop-blur">
      <button
        onClick={onMenu}
        aria-label="menu"
        aria-expanded={open}
        className="rounded-md border border-border-strong bg-surface-2 px-2.5 py-1.5 text-text md:hidden"
      >
        ☰
      </button>
      <Link href="/" aria-label="首頁" className="font-display text-sm font-bold md:hidden">
        AI Trade Flow<span className="text-accent">.</span>
      </Link>

      {/* Global market selector — the single driver of data-market */}
      <label className="flex items-center gap-1.5 text-[13px] text-muted">
        <span className="hidden sm:inline text-faint">市場</span>
        <select
          value={market}
          onChange={(e) => setMarket(e.target.value)}
          aria-label="市場"
          className="rounded-md border border-border bg-surface-2 px-2 py-1 text-[13px] text-text"
        >
          {MARKETS.map((m) => (
            <option key={m.value} value={m.value}>{m.label}</option>
          ))}
        </select>
      </label>

      {/* Mode chip — paper neutral; LIVE = --live + pulse (the one deliberate animation) */}
      <span
        className={`rounded-sm px-2 py-0.5 text-xs font-medium ${
          live ? "bg-live/15 text-live animate-pulse" : "bg-surface-3 text-muted"
        }`}
        title={live ? "實際下單模式" : "紙上交易(安全預設)"}
      >
        {(config.data?.trading_mode ?? "paper").toUpperCase()}
      </span>

      {/* Active-market equity + today's PnL (base currency) */}
      {s && (
        <div className="hidden items-baseline gap-2 lg:flex">
          <span className="num text-[13px] text-text">{money(s.equity_base)} {s.base_currency}</span>
          <span className={`num text-xs ${todayPnl >= 0 ? "text-up" : "text-down"}`}>
            {todayPnl >= 0 ? "▴" : "▾"} {money(Math.abs(todayPnl))}
          </span>
        </div>
      )}

      <div className="ml-auto flex items-center gap-3">
        {/* Risk chip — always reachable; turns --error on kill/halt */}
        <Link
          href="/risk"
          title="風控中心"
          className={`flex items-center gap-1 rounded-md border px-2 py-1 text-xs ${
            danger
              ? "border-error/40 bg-error/15 text-error"
              : "border-border bg-surface-2 text-muted hover:text-text"
          }`}
        >
          <ShieldAlert size={14} />
          <span className="hidden sm:inline">{danger ? (s?.kill_switch ? "KILL" : "HALTED") : "風控"}</span>
        </Link>
        <ThemeToggle />
        <Link
          href="/docs"
          className="rounded-md border border-border bg-surface-2 px-3 py-1.5 text-[13px] text-muted hover:border-accent hover:text-text"
        >
          文件中心 ↗
        </Link>
      </div>
    </header>
  );
}
```

- [ ] **Step 2: Typecheck** — `cd frontend && npx tsc --noEmit` → no errors.
- [ ] **Step 3: Commit** — `feat(shell): Global Context Bar (market/mode/equity/risk)`

---

### Task 4: Risk Cockpit page + nav

**Files:**
- Create: `frontend/app/(rooms)/risk/page.tsx`
- Modify: `frontend/lib/nav.ts` (add a 監控室 group with a Risk Cockpit leaf)

**Interfaces:**
- Consumes: `useActiveMarket` (T1), `api.riskStatus`/`setKillSwitch`/`resumeRisk` (T2).

- [ ] **Step 1: Add nav entry** — in `frontend/lib/nav.ts`, add `Gauge` and `ShieldAlert` to the lucide import (line 1-7) and a 監控室 group. Update the import line to include them:

```tsx
import {
  FlaskConical, MessageSquareCode, Library,
  Network, History, Workflow,
  CandlestickChart, Wallet,
  Wrench, CalendarClock, Bell, Upload,
  Gauge, ShieldAlert,
  type LucideIcon,
} from "lucide-react";
```

and insert this NavItem into the `NAV` array immediately after the 交易室 block (after line 30, before `市場`):

```tsx
  {
    label: "監控室",
    icon: Gauge,
    children: [
      { label: "風控", href: "/risk", icon: ShieldAlert },
    ],
  },
```

- [ ] **Step 2: Create the cockpit page** — `frontend/app/(rooms)/risk/page.tsx`:

```tsx
"use client";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useActiveMarket } from "@/lib/market-context";

function money(n: number) {
  return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

function Bar({ label, used, max, unit }: { label: string; used: number; max: number; unit: string }) {
  const pct = max > 0 ? Math.min(100, (Math.max(0, used) / max) * 100) : 0;
  const tone = pct >= 90 ? "bg-error" : pct >= 70 ? "bg-warning" : "bg-surface-3";
  return (
    <div className="rounded-md border border-border bg-surface-1 p-3">
      <div className="mb-1 flex items-baseline justify-between text-xs">
        <span className="text-muted">{label}</span>
        <span className="num text-text">
          {money(used)} / {money(max)} {unit}
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-sm bg-surface-2">
        <div className={`h-full ${tone}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function RiskPage() {
  const { market } = useActiveMarket();
  const qc = useQueryClient();
  const status = useQuery({
    queryKey: ["risk-status", market],
    queryFn: () => api.riskStatus(market),
    refetchInterval: 5000,
    retry: false,
  });

  if (status.isError) {
    return <p className="text-sm text-error">風控狀態載入失敗：{(status.error as Error).message}</p>;
  }
  if (!status.data) return <p className="text-sm text-faint">載入中…</p>;
  const s = status.data;
  const todayPnl = s.equity_base - s.day_start_equity_base;
  const dailyLossUsed = Math.max(0, s.day_start_equity_base - s.equity_base);

  const toggleKill = async () => {
    const next = !s.kill_switch_runtime;
    if (next && !confirm("確定要啟動 kill switch?所有新進場單將被擋下(平倉仍允許)。")) return;
    await api.setKillSwitch(next);
    qc.invalidateQueries({ queryKey: ["risk-status"] });
  };
  const resume = async () => {
    if (!confirm("確定要解除 halted、恢復進場?")) return;
    await api.resumeRisk();
    qc.invalidateQueries({ queryKey: ["risk-status"] });
  };

  return (
    <section className="space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="font-display text-xl font-semibold">風控中心</h1>
        <span className="text-xs text-faint">市場 {market} · 計價 {s.base_currency}</span>
      </div>

      {(s.kill_switch || s.halted) && (
        <div className="rounded-md border border-error/40 bg-error/15 px-4 py-3 text-sm text-error">
          {s.kill_switch && <div>● Kill switch 已啟動 — 所有新進場單被擋下。</div>}
          {s.halted && <div>● 已 halted(單日虧損達上限)— 進場暫停,平倉仍允許。</div>}
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <div className="rounded-md border border-border bg-surface-1 p-3">
          <div className="text-xs text-faint">權益(base)</div>
          <div className="num text-lg font-semibold">{money(s.equity_base)}</div>
        </div>
        <div className="rounded-md border border-border bg-surface-1 p-3">
          <div className="text-xs text-faint">今日損益</div>
          <div className={`num text-lg font-semibold ${todayPnl >= 0 ? "text-up" : "text-down"}`}>
            {todayPnl >= 0 ? "+" : "−"}{money(Math.abs(todayPnl))}
          </div>
        </div>
        <div className="rounded-md border border-border bg-surface-1 p-3">
          <div className="text-xs text-faint">日初權益</div>
          <div className="num text-lg font-semibold">{money(s.day_start_equity_base)}</div>
        </div>
        <div className="rounded-md border border-border bg-surface-1 p-3">
          <div className="text-xs text-faint">狀態</div>
          <div className={`text-lg font-semibold ${s.kill_switch || s.halted ? "text-error" : "text-up"}`}>
            {s.kill_switch ? "KILL" : s.halted ? "HALTED" : "OK"}
          </div>
        </div>
      </div>

      <div className="grid gap-3 lg:grid-cols-3">
        <Bar label="總曝險" used={s.exposure_base} max={s.max_total_exposure_value} unit={s.base_currency} />
        <Bar label="單日虧損" used={dailyLossUsed} max={s.max_daily_loss} unit={s.base_currency} />
        <Bar label="今日下單數" used={s.orders_today} max={s.max_orders_per_day} unit="筆" />
      </div>

      <div className="flex flex-wrap gap-3">
        <button
          onClick={toggleKill}
          className={`rounded-md border px-4 py-2 text-sm font-medium ${
            s.kill_switch_runtime
              ? "border-border bg-surface-2 text-text hover:bg-surface-3"
              : "border-error/40 bg-error/15 text-error hover:bg-error/25"
          }`}
        >
          {s.kill_switch_runtime ? "解除 Kill Switch" : "啟動 Kill Switch"}
        </button>
        {s.halted && (
          <button
            onClick={resume}
            className="rounded-md border border-warning/40 bg-warning/15 px-4 py-2 text-sm font-medium text-warning hover:bg-warning/25"
          >
            恢復進場(清除 halted)
          </button>
        )}
        {s.kill_switch_config && (
          <span className="self-center text-xs text-faint">
            註:設定檔層級 kill switch(KILL_SWITCH=true)為開,UI 僅能切換 runtime 旗標。
          </span>
        )}
      </div>
    </section>
  );
}
```

- [ ] **Step 3: Typecheck** — `cd frontend && npx tsc --noEmit` → no errors.
- [ ] **Step 4: Commit** — `feat(risk): Risk Cockpit page + 監控室 nav`

---

### Task 5: Migrate panels to the shared active-market context

Replace each panel's local `market` state + old `lib/useMarket.ts:setMarket` calls with `useActiveMarket()`. This makes the Context Bar selector and each panel agree, and routes ALL `data-market` changes through the provider — fixing the residue bug and the `StrategyLibrary`/`DataImportPanel` no-`setMarket` bug. Then delete the now-unused `lib/useMarket.ts`.

**Files:**
- Modify: `frontend/components/MarketPanel.tsx`, `frontend/components/BacktestPanel.tsx`, `frontend/components/HomeDashboard.tsx`, `frontend/components/strategy/StrategyLibrary.tsx`, `frontend/components/DataImportPanel.tsx`, `frontend/components/PortfolioPanel.tsx`
- Delete: `frontend/lib/useMarket.ts`

**Interfaces:**
- Consumes: `useActiveMarket` (T1).

- [ ] **Step 1: Migration pattern (apply to each panel)**

For every panel that has `const [market, setMarketState] = useState(...)` (or `useState("crypto")` / from `sp.get("market")`) plus `import { setMarket } from "@/lib/useMarket"` and a `useEffect(() => setMarket(market), [market])`:

1. Add `import { useActiveMarket } from "@/lib/market-context";` and remove `import { setMarket } from "@/lib/useMarket";`.
2. Replace the local state with `const { market, setMarket } = useActiveMarket();`.
3. Delete the `useEffect(() => { setMarket(market); }, [market]);` (the provider now owns `data-market`).
4. Replace any `setMarketState(x)` call with `setMarket(x)`.
5. Keep the panel's `<select>` — just point its `onChange` at the context `setMarket` (it already reads `market`).

Per-file specifics:
- **`MarketPanel.tsx`** (`:37` `const [market, setMarketState] = useState(sp.get("market") ?? "crypto")`, `:7` import, plus its `setMarket` effect): apply pattern. The initial `sp.get("market")` URL seed is dropped in favor of the persisted global market (acceptable; the symbol/timeframe URL seeds stay). Point the market `<select>` onChange to `setMarket`.
- **`BacktestPanel.tsx`** (`:35` state, `:17` import, `:75` `if (qMarket ...) setMarketState(qMarket)`, `:91` effect, `:241` select onChange): apply pattern. At `:75`, replace `setMarketState(qMarket)` with `setMarket(qMarket)` (still honor the `?market=` deep-link by writing it into the context once on mount). Remove the `:91` effect.
- **`HomeDashboard.tsx`** (`:42` `const [market, setMarketState] = useState("crypto")`, `:7` import, `:50` `setMarket(market)` effect, `:74` `setMarketState(next)`): apply pattern; replace `setMarketState(next)` with the context `setMarket(next)`; remove the effect.
- **`StrategyLibrary.tsx`** (`:21` `const [market, setMarket] = useState("crypto")`, select `:51`): replace local state with `const { market, setMarket } = useActiveMarket();` (this FIXES the bug — 台股 colors now invert because the provider sets `data-market`). No `useMarket` import existed here.
- **`DataImportPanel.tsx`** (`:12` `const [market, setMarket] = useState("tw_stock")`, select `:38`): this panel's market is an *import target*, not the viewing market — but it should still drive `data-market` for consistency. Replace with `const { market, setMarket } = useActiveMarket();` and default-select `tw_stock` only if the active market is crypto is NOT required — simplest: use the shared market; if the user is on crypto, they can switch in the bar. (Acceptable: import targets tw/us; keep the shared selector.)
- **`PortfolioPanel.tsx`** (currently hardcodes `api.portfolio("crypto")` at `:18`, no market selector): add `const { market } = useActiveMarket();` and change the query to `queryFn: () => api.portfolio(market)` with `queryKey: ["portfolio", market]`; the reset button's `api.resetPaper("crypto")` → `api.resetPaper(market)`. (The standalone mode chip at `:26-34` stays for now; the Context Bar also shows mode — a future cleanup can dedupe, out of scope here.)

- [ ] **Step 2: Delete the dead module**

After all six panels no longer import it, delete `frontend/lib/useMarket.ts`. Verify no remaining importers:
Run: `cd frontend && grep -rn "lib/useMarket\|from \"@/lib/useMarket\"" components app` → expect no matches.

- [ ] **Step 3: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors (all `setMarketState` references removed; `useMarket` import gone everywhere).

- [ ] **Step 4: Commit** — `refactor(market): panels consume MarketProvider; drop scattered setMarket`

---

### Task 6: Build + visual verification + DESIGN.md compliance

**Files:** none (verification only).

- [ ] **Step 1: Authoritative build**

Run: `cd frontend && npm run build`
Expected: `✓ Compiled successfully`, 0 type errors, all pages generated (including the new `/risk`).

- [ ] **Step 2: Visual smoke (use the `run-app` skill)**

Launch the stack and confirm in a browser:
1. The Context Bar shows the market selector, a `PAPER` chip (neutral), active-market equity + today's PnL, and a 風控 chip on every room page.
2. Switching the market to **台股 (tw_stock)** in the bar flips `--up`/`--down` **globally** (portfolio uPnL, market chart, backtest returns all invert red/green) and **persists across navigation** (no residue when going back to a crypto view — switch back to crypto and confirm colors revert everywhere).
3. Open **/risk** (監控室 → 風控): equity / today-PnL / limit bars render; click **啟動 Kill Switch** → the page banner + the Context Bar 風控 chip turn `--error`/`KILL` on the next refetch; **解除** clears it.
4. If `TRADING_MODE=live`, the mode chip is `--live` + pulsing.

- [ ] **Step 3: DESIGN.md compliance self-check**

- `--accent` (cyan) appears in NONE of the new market/mode/risk UI (only theme/AI keep it). ✓
- LIVE mode chip is the only pulse; `--live` used only for live. ✓
- Risk danger uses `--error`/`--warning`, not price tokens or accent. ✓
- Today's-PnL color goes through `--up`/`--down` (inverts for 台股). ✓
- Numbers use `.num`. ✓

- [ ] **Step 4: Commit** (if any compliance fix was needed) — otherwise nothing to commit.

---

## Self-Review

**1. Spec coverage** (against blueprint §5 Global Context Bar + Risk Cockpit / roadmap Now-5 + Now-6):
- Context Bar: single global market selector → `data-market` ✔ (T1+T3+T5); mode chip (paper/LIVE + pulse) ✔ (T3); equity/today-PnL ✔ (T3, from riskStatus); risk chip reading `/api/risk/status`, turns `--error` on kill/halt ✔ (T3); persistent across pages ✔ (TopBar is in AppShell). Theme + docs retained ✔.
- Risk Cockpit: kill-switch toggle + resume + limit usage (exposure / daily-loss / orders) wired to the 3 `/api/risk/*` endpoints ✔ (T2+T4); nav leaf under a new 監控室 ✔ (T4, aligns with the approved three-room IA).
- Bug fixes: cross-page `data-market` residue + `StrategyLibrary`/`DataImportPanel` no-`setMarket` ✔ (T1+T5 centralize the single owner).

**2. Placeholder scan:** No "TBD"/"handle later". New components have full code; T5 gives a concrete per-file migration with line refs.

**3. Type consistency:** `useActiveMarket(): { market: string; setMarket: (m: string) => void }` is used identically in T3/T4/T5. `RiskStatus` fields match `api/risk.py:RiskStatus` exactly. `api.riskStatus/setKillSwitch/resumeRisk` signatures consistent between T2 (def) and T3/T4 (use).

**Deliberately deferred (noted, not silently dropped):**
- Global **alert bell** / Alert Center → roadmap X10 thread.
- **Cross-market** equity aggregation (Context Bar shows the *active* market's equity, not a TWD roll-up) → roadmap Now-7 (needs a new `/api/portfolio/summary`).
- **Per-run / per-deployment mode** (mode chip currently mirrors the global `trading_mode`) → roadmap Next thread (authoritative per-run mode + LIVE arming gate).
- Deduping the standalone mode chips still in `PortfolioPanel`/`HomeDashboard`/`WorkflowBuilder` now that the bar shows mode → minor follow-up.

---

## Execution Handoff

**Plan complete. Suggested execution: subagent-driven, conflict-safe waves (parallel where files are disjoint):**
- **Wave 1 (parallel):** T1 (`market-context` + providers), T2 (`api.ts`) — disjoint.
- **Wave 2 (parallel):** T3 (`TopBar`), T4 (`risk/page` + `nav`), T5 (6 panels + delete `useMarket`) — disjoint files, all depend on Wave 1.
- **Wave 3:** T6 (build + visual verification).

Frontend has no test runner: tasks self-verify with `npx tsc --noEmit`; the controller runs `npm run build` after each wave (concurrent builds share `.next`, so do NOT build inside parallel tasks).
