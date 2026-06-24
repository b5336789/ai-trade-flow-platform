# Dark / Light Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a user-controllable `system / light / dark` theme to the frontend, persisted and applied across both rooms and the docs handbook.

**Architecture:** Theming is already CSS-custom-property driven; components consume token classes (`bg-bg`, `text-text`, …) and never hardcode hex. We add a dedicated light palette keyed by `data-theme="light"` on `<html>` (dark stays the `:root` default), a no-flash inline script that sets the attribute before paint, a `ThemeProvider`/`useTheme` context for state + persistence, a three-way `ThemeToggle` control, and theme-awareness for the JS-colored charts and the React Flow canvas.

**Tech Stack:** Next.js 14 App Router, React 18, TypeScript, Tailwind (token colors via CSS vars), `lightweight-charts` v5-style API, `@xyflow/react` v12 (has `colorMode`), `lucide-react` icons.

## Global Constraints

- **Never hardcode hex in components** — drive all color through CSS-var tokens (DESIGN.md). New palette values live only in `globals.css` + DESIGN.md.
- **Accent reserved for AI/automation** — accent is `#22D3EE` (dark) / `#0E8FA8` (light); do not spend it on generic chrome. The toggle's active-segment accent is an acceptable control affordance (consistent with focus rings).
- **Price up/down are tokens, never constants** — drive through `--up`/`--down`; `data-market="tw"` inverts them, and the inversion must hold in both themes.
- **Fail loud** — no silent fallbacks that hide a broken theme; `useTheme` throws if used outside the provider.
- **No frontend test runner exists** (CI = `npm run build`). The per-task verification cycle is: type-safe build (`npm run build`) as the automated gate, plus targeted manual checks via the `run-app` skill where behavior is visual. This replaces TDD red/green for this UI work — stated honestly per project conventions.
- **Git flow:** work on branch `feat/dark-light-mode` (already created); commit per task; never commit to `main`.

## File Structure

| File | Responsibility | Action |
|------|----------------|--------|
| `frontend/app/globals.css` | Theme-keyed palettes (dark default + light) | Modify |
| `frontend/app/layout.tsx` | No-flash inline script + `suppressHydrationWarning` | Modify |
| `frontend/app/providers.tsx` | `ThemeProvider` + `useTheme` context | Modify |
| `frontend/components/shell/ThemeToggle.tsx` | Three-way system/light/dark control | Create |
| `frontend/components/shell/TopBar.tsx` | Mount toggle (rooms) | Modify |
| `frontend/app/(handbook)/layout.tsx` | Mount toggle (docs); stop forcing light | Modify |
| `frontend/components/PriceChart.tsx` | Rebuild chart on theme change | Modify |
| `frontend/components/EquityChart.tsx` | Rebuild chart on theme change | Modify |
| `frontend/components/WorkflowBacktestChart.tsx` | Rebuild chart on theme change | Modify |
| `frontend/components/workflow/Canvas.tsx` | React Flow `colorMode` | Modify |
| `DESIGN.md` | Document the three-theme model + light palette | Modify |

`CandleChart.tsx` delegates to `PriceChart` — no change needed.

---

### Task 1: Theme-keyed palettes in `globals.css` (+ DESIGN.md color section)

Restructure the stylesheet so dark is the default and light is a dedicated, contrast-tuned palette. Remove the old docs-only forced-light block so docs inherit `data-theme`.

**Files:**
- Modify: `frontend/app/globals.css` (full rewrite — 29 lines today)
- Modify: `DESIGN.md` (Color section)

**Interfaces:**
- Produces: CSS contract — `[data-theme="dark"]` (and bare `:root`) → dark tokens; `[data-theme="light"]` → light tokens. Tokens unchanged in name: `--bg --surface-1/2/3 --border --border-strong --text --muted --faint --accent --accent-dim --up --down --warning --error --live --c-data/-strat/-logic/-order/-out --font-ui --font-mono`.

- [ ] **Step 1: Rewrite `globals.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  /* font CSS vars are bound to the geist package + next/font in layout.tsx */
  --font-ui: var(--font-geist-sans); --font-mono: var(--font-geist-mono);
}

/* ── DARK (default) ─────────────────────────────────────────────── */
:root,
[data-theme="dark"] {
  color-scheme: dark;
  --bg: #0A0B0D; --surface-1: #111317; --surface-2: #16181D; --surface-3: #1E2127;
  --border: rgba(255,255,255,0.08); --border-strong: rgba(255,255,255,0.14);
  --text: #E7E9EC; --muted: #8A9099; --faint: #5B616B;
  --accent: #22D3EE; --accent-dim: rgba(34,211,238,0.14);
  --up: #34D399; --down: #F87171;
  --warning: #FBBF24; --error: #EF4444; --live: #FB7185;
  --c-data: #8A9099; --c-strat: #22D3EE; --c-logic: #FBBF24; --c-order: #34D399; --c-out: #A78BFA;
}

/* ── LIGHT (dedicated app palette, tuned for AA contrast on light) ── */
[data-theme="light"] {
  color-scheme: light;
  --bg: #FBFBFA; --surface-1: #FFFFFF; --surface-2: #F4F5F6; --surface-3: #ECEEF0;
  --border: rgba(15,18,22,0.10); --border-strong: rgba(15,18,22,0.18);
  --text: #1A1D21; --muted: #5B616B; --faint: #8A9099;
  --accent: #0E8FA8; --accent-dim: rgba(14,143,168,0.12);
  --up: #0E9F6E; --down: #E02424;
  --warning: #B45309; --error: #DC2626; --live: #E11D6E;
  --c-data: #5B616B; --c-strat: #0E8FA8; --c-logic: #B45309; --c-order: #0E9F6E; --c-out: #7C5CFF;
}

/* market inversion — per theme so red=up contrast holds on each background */
[data-market="tw"]                     { --up: #F05252; --down: #31C48D; }
[data-theme="light"][data-market="tw"] { --up: #E02424; --down: #0E9F6E; }

body { @apply bg-bg text-text font-ui; }

.num { font-family: var(--font-mono); font-variant-numeric: tabular-nums; }
```

Note what changed vs. today: dark values are identical (now also matched by `[data-theme="dark"]`); the `[data-surface="docs"]` forced-light block is **deleted** (docs now follow `data-theme`); a light palette + a light 台股 inversion are added.

- [ ] **Step 2: Update DESIGN.md Color section**

In `DESIGN.md`, under `## Color`, after the existing dark token list, add:

```markdown
### Theme modes (dark / light / system)

The palette is keyed by `data-theme` on `<html>`: dark is the default (`:root`),
light is an override (`[data-theme="light"]`). First visit follows the OS via
`prefers-color-scheme`; the user's choice (`system`/`light`/`dark`) persists in
`localStorage` and is set before paint by an inline script in `app/layout.tsx`.
The `/docs` handbook follows the theme (it no longer forces a light palette).

**App-light palette** (tuned for AA contrast on a light terminal):
- Backgrounds: `--bg #FBFBFA` → `--surface-1 #FFFFFF` → `--surface-2 #F4F5F6` → `--surface-3 #ECEEF0`.
- Borders: `--border rgba(15,18,22,.10)`, `--border-strong rgba(15,18,22,.18)`.
- Text: `--text #1A1D21`, `--muted #5B616B`, `--faint #8A9099`.
- Accent darkens to `--accent #0E8FA8` (bright `#22D3EE` fails contrast on white) — still AI-reserved.
- Price/status deepen for legibility: `--up #0E9F6E`, `--down #E02424`, `--warning #B45309`, `--error #DC2626`, `--live #E11D6E`.
- 台股 inversion in light: `--up #E02424` (red=up), `--down #0E9F6E`.
```

- [ ] **Step 3: Build to verify nothing broke**

Run: `cd frontend && npm run build`
Expected: build succeeds (dark theme output unchanged; no missing-token CSS).

- [ ] **Step 4: Commit**

```bash
git add frontend/app/globals.css DESIGN.md
git commit -m "feat(theme): add light palette keyed by data-theme; docs follow theme

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: No-flash inline script in `layout.tsx`

Set `data-theme` synchronously before paint so there is no dark→light flash, and silence the resulting hydration attribute warning.

**Files:**
- Modify: `frontend/app/layout.tsx`

**Interfaces:**
- Produces: on every page load, `document.documentElement.dataset.theme` is `'light'|'dark'` before first paint, derived from `localStorage["theme"]` (`'system'|'light'|'dark'|null`) and `prefers-color-scheme`.

- [ ] **Step 1: Add `suppressHydrationWarning` to `<html>` and inject the script**

In `frontend/app/layout.tsx`, change the `<html>` element to include `suppressHydrationWarning` and add a `<head>` containing the inline script. Replace the `return (...)` block of `RootLayout` with:

```tsx
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${GeistSans.variable} ${GeistMono.variable} ${display.variable} ${code.variable} ${cjk.variable}`}
    >
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html:
              "(function(){try{var p=localStorage.getItem('theme');var m=window.matchMedia('(prefers-color-scheme: light)').matches?'light':'dark';document.documentElement.dataset.theme=(!p||p==='system')?m:p;}catch(e){document.documentElement.dataset.theme='dark';}})();",
          }}
        />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
```

- [ ] **Step 2: Build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 3: Manual no-flash check (run-app skill)**

Start the app. With OS set to light, hard-reload `/strategy-lab`: page must paint light immediately (no dark flash). Set OS to dark, reload: paints dark. Confirm `<html>` has `data-theme` set in devtools before any React mount.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/layout.tsx
git commit -m "feat(theme): set data-theme before paint to prevent FOUC

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: `ThemeProvider` + `useTheme` in `providers.tsx`

Add theme state, persistence, and OS-follow to the existing client provider wrapper.

**Files:**
- Modify: `frontend/app/providers.tsx`

**Interfaces:**
- Produces:
  - `type ThemePreference = "system" | "light" | "dark"`
  - `type ResolvedTheme = "light" | "dark"`
  - `useTheme(): { preference: ThemePreference; resolved: ResolvedTheme; setPreference: (p: ThemePreference) => void }` — throws if used outside `<Providers>`.
- Consumes: existing `QueryClientProvider` / `QueryClient` from `@tanstack/react-query`.

- [ ] **Step 1: Replace `providers.tsx` with the theme-aware version**

```tsx
"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

export type ThemePreference = "system" | "light" | "dark";
export type ResolvedTheme = "light" | "dark";

interface ThemeContextValue {
  preference: ThemePreference;
  resolved: ResolvedTheme;
  setPreference: (p: ThemePreference) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);
const STORAGE_KEY = "theme";

function systemTheme(): ResolvedTheme {
  if (typeof window === "undefined") return "dark";
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

function resolve(pref: ThemePreference): ResolvedTheme {
  return pref === "system" ? systemTheme() : pref;
}

function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [preference, setPref] = useState<ThemePreference>("system");
  const [resolved, setResolved] = useState<ResolvedTheme>("dark");

  // Sync React state to whatever the no-flash inline script already applied.
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    const pref: ThemePreference =
      stored === "light" || stored === "dark" || stored === "system" ? stored : "system";
    setPref(pref);
    setResolved(resolve(pref));
  }, []);

  const setPreference = useCallback((p: ThemePreference) => {
    setPref(p);
    const r = resolve(p);
    setResolved(r);
    localStorage.setItem(STORAGE_KEY, p);
    document.documentElement.dataset.theme = r;
  }, []);

  // Follow OS changes only while preference is "system".
  useEffect(() => {
    if (preference !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: light)");
    const onChange = () => {
      const r = systemTheme();
      setResolved(r);
      document.documentElement.dataset.theme = r;
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [preference]);

  const value = useMemo(
    () => ({ preference, resolved, setPreference }),
    [preference, resolved, setPreference],
  );
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within Providers");
  return ctx;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(() => new QueryClient());
  return (
    <QueryClientProvider client={client}>
      <ThemeProvider>{children}</ThemeProvider>
    </QueryClientProvider>
  );
}
```

- [ ] **Step 2: Build**

Run: `cd frontend && npm run build`
Expected: build succeeds (no type errors; `useTheme` exported).

- [ ] **Step 3: Commit**

```bash
git add frontend/app/providers.tsx
git commit -m "feat(theme): add ThemeProvider + useTheme (system/light/dark, persisted)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: `ThemeToggle` three-way control

A compact `radiogroup` with monitor/sun/moon segments.

**Files:**
- Create: `frontend/components/shell/ThemeToggle.tsx`

**Interfaces:**
- Consumes: `useTheme` from `@/app/providers`.
- Produces: `export function ThemeToggle(): JSX.Element`.

- [ ] **Step 1: Create the component**

```tsx
"use client";
import { Monitor, Sun, Moon } from "lucide-react";
import { useTheme, type ThemePreference } from "@/app/providers";

const OPTS: { value: ThemePreference; label: string; Icon: typeof Monitor }[] = [
  { value: "system", label: "系統主題", Icon: Monitor },
  { value: "light", label: "亮色主題", Icon: Sun },
  { value: "dark", label: "暗色主題", Icon: Moon },
];

export function ThemeToggle() {
  const { preference, setPreference } = useTheme();
  return (
    <div
      role="radiogroup"
      aria-label="主題"
      className="flex items-center gap-0.5 rounded-md border border-border bg-surface-2 p-0.5"
    >
      {OPTS.map(({ value, label, Icon }) => {
        const active = preference === value;
        return (
          <button
            key={value}
            role="radio"
            aria-checked={active}
            aria-label={label}
            title={label}
            onClick={() => setPreference(value)}
            className={`rounded p-1.5 transition-colors ${
              active ? "bg-accent-dim text-accent" : "text-muted hover:text-text"
            }`}
          >
            <Icon size={14} />
          </button>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2: Build**

Run: `cd frontend && npm run build`
Expected: build succeeds (component compiles even though not yet mounted).

- [ ] **Step 3: Commit**

```bash
git add frontend/components/shell/ThemeToggle.tsx
git commit -m "feat(theme): add three-way ThemeToggle control

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Mount the toggle (TopBar + docs header) and update DESIGN.md nav note

**Files:**
- Modify: `frontend/components/shell/TopBar.tsx`
- Modify: `frontend/app/(handbook)/layout.tsx`
- Modify: `DESIGN.md` (Layout / top-bar note)

**Interfaces:**
- Consumes: `ThemeToggle` from `@/components/shell/ThemeToggle`.

- [ ] **Step 1: Add the toggle to `TopBar.tsx`**

Place it just before the 文件中心 link so it sits in the right cluster. Add the import and insert `<ThemeToggle />` with `ml-auto` moved onto it (it becomes the first right-aligned item). Replace the file body:

```tsx
"use client";
import Link from "next/link";
import { ThemeToggle } from "@/components/shell/ThemeToggle";

export function TopBar({ open, onMenu }: { open: boolean; onMenu: () => void }) {
  return (
    <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-border bg-bg/85 px-4 py-3 backdrop-blur">
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
      <div className="ml-auto flex items-center gap-3">
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

- [ ] **Step 2: Add the toggle to the docs header**

In `frontend/app/(handbook)/layout.tsx`, import the toggle and add it to the right cluster next to the 返回平台 link. Replace the file body:

```tsx
import Link from "next/link";
import { ThemeToggle } from "@/components/shell/ThemeToggle";

export default function HandbookLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-dvh bg-bg font-ui text-text">
      <header className="sticky top-0 z-20 border-b border-border bg-surface-1/90 backdrop-blur">
        <div className="mx-auto flex max-w-[1100px] items-center justify-between px-5 py-3">
          <Link href="/docs" className="font-display text-sm font-bold">
            AI Trade Flow<span className="text-accent">.</span>{" "}
            <span className="font-medium text-muted">文件中心</span>
          </Link>
          <div className="flex items-center gap-4">
            <ThemeToggle />
            <Link href="/strategy-lab" className="text-[13px] text-muted hover:text-accent">
              ← 返回平台
            </Link>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-[1100px] px-5 py-8">{children}</main>
    </div>
  );
}
```

Note: the `data-surface="docs"` attribute is **removed** from the wrapper `div` — its only effect was forcing the light palette (deleted in Task 1), so docs now follow the active theme.

- [ ] **Step 3: Update DESIGN.md top-bar note**

In `DESIGN.md`, in the `## Layout` → `**Shell:**` paragraph, the existing text mentions "A slim top bar stays for context controls (market color, theme, live/paper)." Append a sentence:

```markdown
The theme control is the `ThemeToggle` component (system/light/dark) in the top
bar and the docs header.
```

- [ ] **Step 4: Build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 5: Manual check (run-app skill)**

Toggle system→light→dark in a room: whole app re-themes; reload persists the choice. Open `/docs`: toggle present, docs re-theme with it (dark docs in dark mode). Re-confirm no-flash from Task 2 still holds.

- [ ] **Step 6: Commit**

```bash
git add frontend/components/shell/TopBar.tsx "frontend/app/(handbook)/layout.tsx" DESIGN.md
git commit -m "feat(theme): mount ThemeToggle in top bar + docs header; docs follow theme

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Theme-aware charts

`lightweight-charts` instances read CSS-var colors via `getComputedStyle` at construction inside a `useEffect`, but those effects don't re-run on theme change, so a switched theme leaves stale chart colors. Fix: add the resolved theme to each chart effect's dependency array so the chart fully rebuilds (re-reading the now-correct CSS vars).

**Files:**
- Modify: `frontend/components/PriceChart.tsx`
- Modify: `frontend/components/EquityChart.tsx`
- Modify: `frontend/components/WorkflowBacktestChart.tsx`

**Interfaces:**
- Consumes: `useTheme` from `@/app/providers` (`resolved`).

- [ ] **Step 1: PriceChart — import the hook and add `resolved` to all chart effects**

In `frontend/components/PriceChart.tsx`:

1. Add the import near the other imports:

```tsx
import { useTheme } from "@/app/providers";
```

2. Inside the component, after the `const [legend, setLegend] = useState<OHLCV | null>(null);` line, add:

```tsx
  const { resolved } = useTheme();
```

3. Append `resolved` to the dependency array of **each** chart effect so they re-run together and repopulate the rebuilt chart with correct colors:
   - Build effect (currently `}, [height, volume, onCrosshairMove, chartType, logScale]);`) → `}, [height, volume, onCrosshairMove, chartType, logScale, resolved]);`
   - Data effect (currently `}, [candles, chartType]);`) → `}, [candles, chartType, resolved]);`
   - Markers effect (currently `}, [markers]);`) → `}, [markers, resolved]);`
   - Overlays/indicators effect (currently `}, [overlays, indicators, candles]);`) → `}, [overlays, indicators, candles, resolved]);`
   - Oscillators effect (currently `}, [oscillators, candles]);`) → `}, [oscillators, candles, resolved]);`

   (Leave the live-polling effects untouched — they read up/down per run and don't construct the chart.)

- [ ] **Step 2: EquityChart — same pattern**

In `frontend/components/EquityChart.tsx`:

1. Add import:

```tsx
import { useTheme } from "@/app/providers";
```

2. At the top of the component body, before the effect:

```tsx
  const { resolved } = useTheme();
```

3. Change the effect deps from `}, [points, height]);` to `}, [points, height, resolved]);`.

- [ ] **Step 3: WorkflowBacktestChart — same pattern**

In `frontend/components/WorkflowBacktestChart.tsx`:

1. Add import:

```tsx
import { useTheme } from "@/app/providers";
```

2. After the `onSelectRef` setup, add:

```tsx
  const { resolved } = useTheme();
```

3. Change the chart effect deps from `}, [run, signals]);` to `}, [run, signals, resolved]);`.

- [ ] **Step 4: Build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 5: Manual check (run-app skill)**

Open market candles (PriceChart with volume + an oscillator), a backtest equity curve (EquityChart), and a workflow backtest result (WorkflowBacktestChart). Toggle light↔dark: chart background, grid, text, and up/down series colors all update to the active theme with no leftover dark panel on light (or vice versa). On a 台股 symbol, red=up holds in both themes.

- [ ] **Step 6: Commit**

```bash
git add frontend/components/PriceChart.tsx frontend/components/EquityChart.tsx frontend/components/WorkflowBacktestChart.tsx
git commit -m "feat(theme): rebuild lightweight-charts on theme change

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: React Flow canvas `colorMode`

React Flow v12 has built-in light/dark chrome (Controls, MiniMap, edges, handles, attribution) controlled by the `colorMode` prop. Wire it to the resolved theme so the canvas chrome matches. Node colors and the legend already use CSS-var tokens and adapt automatically.

**Files:**
- Modify: `frontend/components/workflow/Canvas.tsx`

**Interfaces:**
- Consumes: `useTheme` from `@/app/providers` (`resolved`, which is `"light" | "dark"` — a valid `ColorMode`).

- [ ] **Step 1: Add the hook and pass `colorMode`**

In `frontend/components/workflow/Canvas.tsx`:

1. Add import:

```tsx
import { useTheme } from "@/app/providers";
```

2. Inside `Canvas`, after `const { screenToFlowPosition } = useReactFlow();`, add:

```tsx
  const { resolved } = useTheme();
```

3. On the `<ReactFlow ...>` element, add the prop (e.g. right after `nodeTypes={nodeTypes}`):

```tsx
        colorMode={resolved}
```

- [ ] **Step 2: Build**

Run: `cd frontend && npm run build`
Expected: build succeeds (`colorMode` accepts `"light" | "dark"`).

- [ ] **Step 3: Manual check (run-app skill)**

Open the trading-room workflow canvas. Toggle light↔dark: the dotted-grid background, zoom Controls, MiniMap, and edges flip to match. Node category colors and the bottom-left legend stay correct (tokens). The LIVE mode banner remains unmistakable in both themes.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/workflow/Canvas.tsx
git commit -m "feat(theme): wire React Flow colorMode to active theme

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: Full-app verification pass

A final cross-surface sweep in both themes — the spec's verification checklist — to catch any surface still reading a hardcoded color or stale token.

**Files:** none (verification only; patch + amend the relevant prior commit if a defect is found).

- [ ] **Step 1: Build + lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: both pass.

- [ ] **Step 2: Manual sweep (run-app skill), each in light AND dark**

- First load with OS=light then OS=dark → correct theme, **no flash** (preference unset / `system`).
- Cycle system → light → dark; reload between each → choice persists.
- 策略室: chat panel, "AI 生成" badges, generated-strategy code + param table.
- 交易室: canvas (Task 7), backtest equity + KPI cards, run/LIVE controls — LIVE banner unmistakable in both themes.
- Market page: candles + volume + RSI/MACD (Task 6).
- Portfolio, schedules, notifications, data-import, home dashboard.
- `/docs` handbook: readable in both themes; toggle works.
- 台股 (`data-market="tw"`): red=up in both themes.
- Accent stays cyan-family and AI-reserved (not leaking onto generic chrome) in both themes.

- [ ] **Step 3: If a defect is found**

Fix the offending component to use the correct token (never hardcode hex), rebuild, re-verify, and commit with a descriptive message. If clean, no commit needed.

- [ ] **Step 4: Finish the branch**

Use the superpowers:finishing-a-development-branch skill to open a PR for `feat/dark-light-mode` into `main` (git flow: PR, then merge — never commit to main directly).

---

## Self-Review

**Spec coverage:**
- CSS theme-keyed palettes + light values → Task 1. ✓
- No-flash inline script + `suppressHydrationWarning` → Task 2. ✓
- `ThemeProvider`/`useTheme`, `system|light|dark`, persistence, OS-follow-while-system → Task 3. ✓
- Three-way `ThemeToggle` → Task 4; mounted in TopBar + docs header → Task 5. ✓
- Docs follow theme (drop forced-light) → Task 1 (CSS) + Task 5 (remove `data-surface`). ✓
- Charts theme-aware → Task 6. ✓
- React Flow canvas → Task 7 (`colorMode`). ✓
- DESIGN.md updates (color model + light palette + top-bar note) → Task 1 + Task 5. ✓
- Verification checklist → Task 8. ✓
- 台股 inversion in both themes → Task 1 (`[data-theme="light"][data-market="tw"]`), verified in Tasks 6 & 8. ✓

**Placeholder scan:** No TBD/TODO; every code step shows the exact change. ✓

**Type consistency:** `ThemePreference`/`ResolvedTheme`/`useTheme` defined in Task 3 (`providers.tsx`) and consumed verbatim in Tasks 4, 6, 7. `resolved` is `"light"|"dark"`, matching React Flow's `ColorMode` in Task 7. ✓
