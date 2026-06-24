# Dark / Light Mode — Design

> Spec for adding a user-controllable theme (system / light / dark) to the
> AI Trade Flow frontend. Read alongside [`DESIGN.md`](../../../DESIGN.md).

## Goal

Let users choose between **dark** (current default), **light**, and **system**
(follow OS `prefers-color-scheme`). The choice persists across visits and applies
to the whole app — both the two rooms (策略室 / 交易室) and the `/docs` handbook.

## Decisions (locked)

1. **First-visit default:** `system` — resolve via `prefers-color-scheme`. A manual
   choice overrides and persists.
2. **Control:** three-way `system / light / dark` (not a binary toggle).
3. **Docs follow the theme** — the handbook is no longer force-light.
4. **Dedicated app-light palette** — tuned for the dense terminal, not reused from
   the docs reading page. Documented in DESIGN.md.

## Current state (what exists today)

- `frontend/app/globals.css` defines the **dark** palette in `:root` and a one-off
  **light** palette under `[data-surface="docs"]` (docs only). `[data-market="tw"]`
  flips `--up`/`--down`.
- Components consume CSS-var-backed Tailwind tokens (`bg-bg`, `text-text`,
  `border-border`, …) — **no component reads a hardcoded hex**. So a theme switch is
  purely (a) defining a light palette and (b) flipping a root attribute.
- `app/providers.tsx` is the existing client wrapper (React Query) used by the root
  layout — the natural home for a theme context.
- DESIGN.md already reserves a "theme" slot in the top bar.

## Architecture

### 1. CSS: theme-keyed palettes (`globals.css`)

Restructure into a theme-keyed model. Dark stays the default so existing behavior is
unchanged when no attribute is set.

```
/* shared, theme-independent: fonts, radii, node-color hue intent */
:root { --font-ui: …; --font-mono: …; --r-sm/md/lg: …; }

/* DARK (default) */
:root,
[data-theme="dark"] {
  color-scheme: dark;
  --bg: #0A0B0D; --surface-1: #111317; --surface-2: #16181D; --surface-3: #1E2127;
  --border: rgba(255,255,255,.08); --border-strong: rgba(255,255,255,.14);
  --text: #E7E9EC; --muted: #8A9099; --faint: #5B616B;
  --accent: #22D3EE; --accent-dim: rgba(34,211,238,.14);
  --up: #34D399; --down: #F87171;
  --warning: #FBBF24; --error: #EF4444; --live: #FB7185;
  --c-data: #8A9099; --c-strat: #22D3EE; --c-logic: #FBBF24; --c-order: #34D399; --c-out: #A78BFA;
}

/* LIGHT (new dedicated app palette) */
[data-theme="light"] {
  color-scheme: light;
  --bg: #FBFBFA; --surface-1: #FFFFFF; --surface-2: #F4F5F6; --surface-3: #ECEEF0;
  --border: rgba(15,18,22,.10); --border-strong: rgba(15,18,22,.18);
  --text: #1A1D21; --muted: #5B616B; --faint: #8A9099;
  --accent: #0E8FA8; --accent-dim: rgba(14,143,168,.12);
  --up: #0E9F6E; --down: #E02424;
  --warning: #B45309; --error: #DC2626; --live: #E11D6E;
  --c-data: #5B616B; --c-strat: #0E8FA8; --c-logic: #B45309; --c-order: #0E9F6E; --c-out: #7C5CFF;
}

/* market inversion — per theme so contrast holds on each background */
[data-market="tw"]                     { --up: #F05252; --down: #31C48D; }
[data-theme="light"][data-market="tw"] { --up: #E02424; --down: #0E9F6E; }

/* docs surface: the forced-light palette is REMOVED so docs inherit data-theme.
   Today this selector holds only that palette, so the block is deleted entirely
   (re-add later only for genuine reading-surface tweaks, never a palette). */
```

The light hex values are chosen for **WCAG-AA-ish contrast on a light background**:
the accent darkens to `#0E8FA8` (the bright `#22D3EE` fails contrast on white), and
`--up`/`--down`/`--live` deepen so price + danger stay legible. The accent stays
**reserved for AI/automation** per DESIGN.md.

### 2. No-flash initial paint (`app/layout.tsx`)

App Router SSR can't know the client's stored preference, so without intervention the
page paints dark then jumps. Fix:

- Add `suppressHydrationWarning` to `<html>`.
- Inject a tiny **inline `<script>`** in `<head>` that runs before paint:

```js
(function () {
  try {
    var p = localStorage.getItem("theme");           // 'system' | 'light' | 'dark' | null
    var sys = matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
    document.documentElement.dataset.theme = (!p || p === "system") ? sys : p;
  } catch (e) { document.documentElement.dataset.theme = "dark"; }
})();
```

This sets `data-theme` synchronously → no FOUC. The script is the **single source of
truth for initial paint**; React state hydrates to match.

### 3. Theme state (`app/providers.tsx`)

Add a `ThemeProvider` + `useTheme()` alongside the existing React Query provider.

- **Stored preference:** `'system' | 'light' | 'dark'` in `localStorage["theme"]`.
- **Resolved theme:** `'light' | 'dark'` actually applied (preference resolved
  through `matchMedia` when `system`).
- On mount: read the attribute the inline script already set (avoids a second flip);
  sync React state to it.
- `setPreference(p)`: write `localStorage`, recompute resolved theme, set
  `document.documentElement.dataset.theme`.
- While preference is `system`: subscribe to `matchMedia` `change` and update the
  resolved theme live. Unsubscribe when preference becomes explicit.
- Context value: `{ preference, resolved, setPreference }`.

### 4. Control: `ThemeToggle` component

A small shared client component — a three-segment control: **monitor (system) /
sun (light) / moon (dark)**, active segment highlighted, each with an `aria-label`
and the group as a `role="radiogroup"`. Styled with existing tokens (`surface-2`,
`border`, `accent` for the active state — the accent here is acceptable as a
control affordance, consistent with focus rings).

Placement:
- **Rooms:** in `components/shell/TopBar.tsx` (left of the 文件中心 link).
- **Docs:** in `app/(handbook)/layout.tsx` header (right cluster). Because the docs
  layout is a server component, the toggle is its own `"use client"` component
  dropped in — no need to convert the layout.

### 5. Charts & canvas (the part that doesn't auto-switch)

CSS tokens cover all DOM, but two areas take colors in JavaScript:

- **`lightweight-charts`** (`PriceChart`, `CandleChart`, `EquityChart`,
  `WorkflowBacktestChart`): chart layout/grid/text colors are passed in JS at
  construction. They must read the **resolved theme** (from `useTheme()` or
  `getComputedStyle` on the token) and re-apply on theme change (effect keyed on
  `resolved`). Series up/down colors should pull from `--up`/`--down`.
- **React Flow canvas** (`components/workflow/`): the dotted-grid `Background`,
  edges, and node chrome — verify they read tokens; pass token-derived colors where
  React Flow needs explicit values.

This is the primary **manual-verification** area: run the app and confirm both themes
in the trading-room canvas and all charts (see Testing).

## DESIGN.md updates

Update the **Color** section to document the three-theme model:
- Note that the palette is keyed by `data-theme` (`dark` default, `light` override),
  system-followed on first load.
- Add the app-light palette table (the hex values above).
- Note that the accent darkens to `#0E8FA8` in light for contrast, still AI-reserved.
- Note `data-surface="docs"` no longer forces a palette — docs follow the theme.
- Update the Layout/top-bar note to point at the real `ThemeToggle`.

## Testing / verification

No frontend test runner exists (CI = `npm run build` only), so verification is:

1. **Build:** `npm run build` passes (catches type errors in the new hook/component).
2. **Manual, both themes × key surfaces** (via the `run-app` skill):
   - First load with OS light and OS dark → correct theme, **no flash**.
   - Cycle system → light → dark; reload → persists.
   - 策略室 chat + generated-strategy panel; 交易室 canvas (grid/edges/nodes,
     LIVE banner still unmistakable); backtest equity + KPIs; market candles;
     portfolio; /docs handbook.
   - 台股 (`data-market="tw"`) red=up reads correctly in **both** themes.
   - Accent stays cyan-family and AI-reserved in both themes.

## Out of scope

- Per-room or per-component theme overrides.
- Theme transition animations beyond the browser default.
- Server-side persistence of preference (localStorage only).

## Files touched

- `frontend/app/globals.css` — theme-keyed palettes (+ light values).
- `frontend/app/layout.tsx` — `suppressHydrationWarning` + inline no-flash script.
- `frontend/app/providers.tsx` — `ThemeProvider` + `useTheme`.
- `frontend/components/shell/ThemeToggle.tsx` — **new** three-way control.
- `frontend/components/shell/TopBar.tsx` — mount toggle.
- `frontend/app/(handbook)/layout.tsx` — mount toggle; drop forced-light surface.
- `frontend/components/PriceChart.tsx`, `CandleChart.tsx`, `EquityChart.tsx`,
  `WorkflowBacktestChart.tsx` — theme-aware chart colors.
- `frontend/components/workflow/*` — verify/patch canvas token usage.
- `DESIGN.md` — document the three-theme model + light palette.
