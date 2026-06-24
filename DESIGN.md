# Design System — AI Trade Flow

> Source of truth for all visual and UI decisions. Read this before touching anything
> in `frontend/`. Created by `/design-consultation`.

## Product Context

- **What this is:** An AI-driven auto-trading platform for crypto / 台股 / 美股. Users
  design strategies by talking to an AI, then run them — backtested or live — through a
  drag-and-drop workflow.
- **Who it's for:** Technically-minded retail traders and quant-curious builders.
- **Space/industry:** Fintech / trading terminals.
- **Project type:** Data-dense web app (single shell, two rooms).
- **Reference points:** TradingView (data density, green/red semantics), Linear
  (dark surfaces, restrained accent, craft).

## Information Architecture — Two Rooms

The product is split into two top-level rooms, switched from a global nav in the top bar.
Each room has a distinct layout but shares one visual system.

### 策略室 — Strategy Lab
Where strategies are born. Talk to the AI in natural language; it generates a strategy
as **Python code**, which is saved to the **Strategy Library** for reuse.

- **Layout:** conversation panel (left) + generated-strategy panel (right: code block +
  adjustable parameter table), with the Strategy Library as a draggable card grid below.
- **Each strategy** is Python with typed, **adjustable parameters** (name, type, default,
  editable value) tuned at use-time.
- **This is the AI-heavy room** — the electric accent leads here (chat, "AI 生成" badges,
  send button).

### 交易室 — Trading Room
Where strategies run. Two modes, one drag-and-drop canvas.

- **Modes:** `模擬回測` (backtest) and `實際下單` (live). A clearly-marked toggle.
- **Canvas:** wire **strategy nodes** (from the library) + **logic nodes** (conditions)
  + **order nodes** into a workflow. Dotted-grid canvas, node-to-node edges.
- **Backtest mode:** equity curve + metrics (報酬 / Buy&Hold / 最大回撤 / 勝率).
- **Live mode:** MUST show an unmistakable safety state — pink `LIVE` banner with a
  pulsing indicator, the run button flips to `btn-live` ("送出真實訂單"), portfolio chip
  reads `LIVE` not `paper`. The calm data field stays calm; danger is signaled by the
  live color only.

## Aesthetic Direction

- **Direction:** Refined terminal — Bloomberg-terminal seriousness, Linear-grade craft.
- **Decoration level:** minimal. Type, data, and one accent do all the work.
- **Mood:** a precision instrument. Dark, dense, sharp, fast. Not a friendly rounded SaaS.

## Typography

Loaded from Google Fonts. `Noto Sans TC` is the CJK fallback for 中文 in display/UI roles.

- **Display / Hero / panel titles:** **Space Grotesk** (600/700) — engineered, confident.
- **Body / UI:** **Geist** (400/500) — neutral, legible at small sizes for dense UI.
- **Data / all numbers:** **Geist Mono** with `tabular-nums` — the terminal signature;
  every financial figure aligns to the digit. Use `.num` utility everywhere numbers appear.
- **Code / strategy / workflow JSON:** **JetBrains Mono**.
- **CJK fallback:** **Noto Sans TC**.
- **Loading:** single `<link>` with `display=swap` (see `frontend/app/layout.tsx`).
- **Scale (px):** 11 (micro/labels) · 13 (body/UI) · 15 (panel title) · 19–20 (KPI) ·
  38–44 (poster). Letter-spacing −0.025em on display sizes.

## Color

Dark-first. CSS custom properties are the contract — never hardcode hex in components.

- **Backgrounds (layered):** `--bg #0A0B0D` → `--surface-1 #111317` →
  `--surface-2 #16181D` → `--surface-3 #1E2127`.
- **Borders:** `--border rgba(255,255,255,.08)`, `--border-strong rgba(255,255,255,.14)`.
- **Text:** `--text #E7E9EC`, `--text-muted #8A9099`, `--text-faint #5B616B`.
- **Accent — `--accent #22D3EE` (electric cyan):** RESERVED for AI / automation only —
  AI chat, "AI 生成" badges, Run, strategy nodes, focus rings. If everything is accent,
  nothing is. `--accent-dim rgba(34,211,238,.14)` for fills.
- **Status (distinct from price):** `--warning #FBBF24`, `--error #EF4444`,
  `--live #FB7185` (live-trading danger), info = accent.

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

### Market-aware directional color (key decision)

Price up/down are **tokens, not constants**, because conventions differ by market:

- **Default (crypto / 美股):** `--up #34D399` (green), `--down #F87171` (red).
- **台股 (Taiwan):** the convention is **inverted** — red = up, green = down. Set
  `data-market="tw"` on the root to flip: `--up #F05252`, `--down #31C48D`.

Drive up/down coloring through `--up` / `--down` only. Switching the market tab (or
loading a 台股 symbol) must set `data-market` so gains read correctly for the user.
Never hardcode green-as-gain.

## Spacing

- **Base unit:** 4px.
- **Density:** compact in data areas (tables, KPIs, canvas), comfortable in headers/marketing.
- **Scale:** 4 · 8 · 10 · 13 · 16 · 20 · 24 · 30 · 40.

## Layout

- **Shell:** left **tree-menu sidebar** (primary nav) + main content area. A slim top
  bar stays for context controls (market color, theme, live/paper). Content max-width
  `1440px`, 22px gutters. The theme control is the `ThemeToggle` component (system/light/dark) in the top
  bar and the docs header.
- **策略室 grid:** `1.1fr 1.2fr` (chat | generated strategy), library grid
  `repeat(auto-fill, minmax(210px, 1fr))`. Collapses to 1 column < 980px.
- **交易室 grid:** full-width canvas, then `2fr 1fr` (results | portfolio).
- **Border radius (tight):** `--r-sm 4px`, `--r-md 6px`, `--r-lg 8px`. Sharp reads
  "professional instrument". No bubbly uniform radius.

### Navigation — Left Tree Menu

Primary navigation is a collapsible tree in a left sidebar (the room switcher moves
here). The tree mirrors the two-room IA so users always see where they are.

```
AI Trade Flow.
├─ 🧪 策略室
│  ├─ 與 AI 設計策略
│  └─ 策略庫
│     └─ … (saved strategies)
├─ 🔀 交易室
│  ├─ 模擬回測
│  └─ 工作流
├─ 📈 市場
├─ 👛 投組
└─ 🔧 工具
   ├─ 排程
   ├─ 通知
   └─ 匯入
```

label 僅中文;每項以 lucide icon 前綴(策略室=FlaskConical、交易室=Network、市場=CandlestickChart、投組=Wallet、工具=Wrench;leaf 各有對應 icon)。AI leaf 的 icon 用 `--accent`,其餘用 `--text-faint`,active/live 色彩規則不變。

- **Sidebar width:** `--nav-w 240px` (expanded), `--nav-w-rail 64px` (icon rail).
- **Tree mechanics:** parent rows expand/collapse (chevron, 120ms); children indent
  by 16px with a 1px `--border` guide line; depth ≤ 3.
- **Active state:** the active leaf gets a cyan left-border (`--accent`, 2px) + tinted
  `--accent-dim` background + `--text` label. Hover = `--surface-2`.
- **Color discipline:** cyan marks the *active* item and AI/automation leaves only;
  `實際下單` (live) leaves use the `--live` dot so the danger room is legible in nav.
- **Sticky:** sidebar is `position: sticky; top: 0; height: 100dvh`; only the tree body
  scrolls. Brand sits pinned at the top of the sidebar.

### Responsive (RWD)

Breakpoints follow Tailwind defaults (the project's framework):
`sm 640 · md 768 · lg 1024 · xl 1280 · 2xl 1536`. The sidebar drives the layout mode.

| Range | Sidebar | Content | Tables |
|-------|---------|---------|--------|
| **Desktop ≥ 1280 (xl)** | pinned, 240px, expanded tree | full grids (`1.1fr 1.2fr`, `2fr 1fr`) | full |
| **Tablet 768–1279 (md–lg)** | 64px **icon rail**, labels on hover/flyout | grids collapse to 1 column; canvas scrolls-x | full, scroll-x if needed |
| **Mobile < 768 (<md)** | **off-canvas drawer** behind a hamburger; backdrop scrim; closes on select | everything stacks single-column; sticky top bar holds the hamburger + brand | horizontal scroll inside the panel (no layout break) |

Rules:
- **Mobile-first CSS:** base styles = mobile; layer complexity up at `md`/`xl` with
  `min-width` media queries. No desktop-only assumptions.
- **Drawer a11y:** trap focus when open, `Esc` closes, hamburger is a real
  `<button aria-expanded>`, scrim click closes.
- **Touch targets:** ≥ 44px tall nav rows on mobile (override the compact desktop density).
- **No clipped data:** financial tables never reflow into ambiguous wrapping — they
  scroll horizontally within their panel so columns stay aligned (tabular-nums intact).
- **Charts/canvas:** fluid width, fixed-ish height; the workflow canvas keeps its dotted
  grid and scrolls on small screens rather than shrinking nodes below readable size.
- **Units:** prefer `dvh`/`svh` for full-height nav so mobile browser chrome doesn't clip.

## Motion

- **Approach:** minimal-functional. Tools shouldn't bounce.
- **Easing / duration:** `ease` transitions, 120–200ms for hovers/state.
- **Meaningful motion only:** price ticks may flash up/down color on change; the `LIVE`
  indicator pulses (the one deliberate, attention-demanding animation).

## Workflow Builder (交易室 canvas)

The drag-and-drop builder is a three-pane workspace on top of React Flow
(`@xyflow/react`, already a project dependency). Preview: `/tmp/atf-workflow-preview.html`.

- **Top toolbar (full width):** `Workflow Builder.` title · `交易室 · paper/LIVE` chip ·
  undo/redo · zoom `−／100%／＋／fit` · right side live validation
  (`✓ 有效 · N nodes · M edges`, turns `--error` red on cycle / missing input) ·
  `💾 儲存` · `▶ 執行回測` (flips to the pink `--live` `▶ 送出真實訂單` in live mode).
- **Left — node palette (~200px):** search box + draggable node chips grouped by
  category, each with its category color swatch. Strategy group includes saved library
  strategies. Drag a chip onto the canvas to create a node.
- **Center — canvas:** dotted-grid background (22px), pan/zoom. Bottom-right **minimap**,
  bottom-left **color legend**.
- **Right — inspector (~256px):** selected node's category label + title, then editable
  fields (name, input source, and the node's params — e.g. logic = field/operator/threshold;
  strategy = its adjustable Python params). Footer: 複製 / 刪除 (delete in `--down` red).

### Node categories (one color each)

| Category | Token | Use |
|----------|-------|-----|
| 資料 Data | `--c-data #8A9099` (gray) | OHLCV, CSV import |
| 策略 Strategy | `--c-strat #22D3EE` (cyan) | library strategies + ⚡ AI Signal |
| 邏輯 Logic | `--c-logic #FBBF24` (amber) | IF, AND/OR, thresholds |
| 下單 Order | `--c-order #34D399` (green) | market/limit order, RiskGuard |
| 輸出 Output | `--c-out #A78BFA` (violet) | Notify, Logger |

Cyan stays tied to strategy/AI so "the AI is in this flow" reads at a glance. The
accent's AI-only rule still holds: the Run button and AI nodes are the only cyan;
other categories own their own hues.

### Node anatomy

158px card: header (category-colored 3px left bar + color chip + name + tiny category
tag) over a body showing the 1–2 key params in mono (`rsi ≤ 28`, `conf ≥ 0.70`). Round
**ports** sit on the card edges — input left, output right — ringed in the node's
category color. Selected node gets a 2px cyan outline.

### Edge & run states

- **Default edge:** `--border-strong` bezier, 2px.
- **Running edge:** animated dashed `--accent` flow (marks the active step during a run).
- **Error edge / invalid graph:** `--error` red; toolbar validation reflects it.

### RWD (builder)

- **Desktop ≥1280:** full three-pane.
- **Tablet 768–1279:** palette collapses to an icon strip; inspector becomes a slide-over
  triggered by node selection; canvas takes the freed width.
- **Mobile <768:** view/run-focused — palette and inspector become bottom sheets; heavy
  node editing is intentionally a desktop task (flagged scope call, not a gap).

## SAFE choices vs RISKS

**SAFE (category baseline):** dark theme; green/red price semantics; tabular monospace
numerals.

**RISKS (where the product gets its face):**
1. **Market-aware red/green** that flips for 台股 — most Western tools hardcode green-up;
   this respects each market's convention.
2. **Electric cyan reserved exclusively for AI/automation** — color-codes "the AI is
   acting", tying the palette to the product's core identity.
3. **Terminal-sharp density** (tight radii, mono numerals everywhere) instead of friendly
   rounded SaaS — signals "serious instrument".

## AI-slop guardrails (do NOT do)

No purple/violet default gradients · no 3-column icon-in-circle feature grids · no
centered-everything · no uniform bubbly radius · no gradient CTAs · no generic hero
stock imagery. Accent is cyan and earns its place; it is not decoration.

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-06-19 | Initial design system created | `/design-consultation` + visual research (TradingView, Linear). Refined-terminal aesthetic. |
| 2026-06-19 | Two-room IA: 策略室 + 交易室 | User restructure: AI-generated Python strategies → library → drag-drop backtest/live workflow. |
| 2026-06-19 | Market-aware up/down color tokens | 台股 inverts the green/red convention; hardcoding green-up misreads gains for Taiwanese users. |
| 2026-06-19 | Left tree-menu sidebar replaces top-bar room switcher | Two rooms + sub-items + saved strategies need persistent, hierarchical nav; a tree shows location and scales as the library grows. |
| 2026-06-19 | RWD: pinned tree → icon rail → off-canvas drawer | One layout can't serve desktop terminals and phones; sidebar drives the mode at xl/md breakpoints, tables scroll-x rather than reflow. |
| 2026-06-19 | Workflow builder: palette + canvas + inspector, color-per-category nodes | Maps to React Flow; category colors (data/strategy/logic/order/output) make graphs scannable; cyan reserved for strategy/AI keeps the AI-accent rule intact. |
| 2026-06-20 | `/docs` 改為獨立亮色閱讀 Portal（`[data-surface="docs"]` scope） | 文件中心與交易終端機分流:長文閱讀需亮底/寬 measure;僅作用於 docs scope,主 App 維持深色終端機風。使用者核准的範圍內偏離。 |
| 2026-06-22 | 選單改純中文 label + lucide icon(移除英文 subtitle) | 中英並陳視覺雜訊大;icon + 中文更貼近專業終端機。使用者核准的偏離。 |
