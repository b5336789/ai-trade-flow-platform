# Docs Portal (Light) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `/docs` into a standalone light-themed reading portal (outside the App Shell), reachable from a top-bar entry point, and publish the development-history docs through the existing manifest.

**Architecture:** New `app/(handbook)/` route group with its own light shell (no `AppShell`); the existing docs pages move into it. Light theme is achieved by re-defining the DESIGN.md CSS tokens inside a `[data-surface="docs"]` scope, so the token-utility components (Markdown, SystemFeatures, pages) re-skin automatically. Dev-history docs are added to `lib/docs-manifest.ts`, which the sync script already derives from.

**Tech Stack:** Next.js 14 App Router, React 18, TypeScript, Tailwind CSS (token utilities mapped to CSS vars), react-markdown + remark-gfm.

## Global Constraints

- **No hardcoded hex in components** — colors come from CSS tokens (`bg-surface-1`, `text-muted`, `text-accent`, …). Light theme overrides tokens in scope; never inline hex. (DESIGN.md)
- **Light style is scoped to `[data-surface="docs"]` only** — the main App and every other room stay dark. This is a DESIGN.md deviation explicitly approved by the user for `/docs`; record it in DESIGN.md Decisions Log (Task 5).
- **`docs-manifest.ts` is the single source of truth** — `scripts/sync-docs.mjs` derives the file list from it via regex. Do NOT edit the sync script.
- **URLs stay `/docs` and `/docs/[slug]`** — route-group folders in parentheses do not change the path. Avoid declaring `/docs` in two route groups at once.
- **No frontend test runner exists.** Verification gates are `npm run build`, `npm run lint`, `npm run sync-docs` output, and grep/route checks. Use these as the test cycle. Report failures loudly; never claim a gate passed without running it.
- Work happens on branch `feature/docs-portal-light`. All commands run from `frontend/` unless noted.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `frontend/lib/docs-manifest.ts` | Doc catalog + category type (single source of truth) | Modify |
| `frontend/app/globals.css` | CSS tokens; add `[data-surface="docs"]` light scope | Modify |
| `frontend/app/(handbook)/layout.tsx` | Standalone light shell (no AppShell) + back-to-app link | Create |
| `frontend/app/(handbook)/docs/page.tsx` | Docs hub (moved, categories extended) | Create (moved) |
| `frontend/app/(handbook)/docs/[slug]/page.tsx` | Doc detail (moved, editorial measure) | Create (moved) |
| `frontend/app/(rooms)/docs/page.tsx` | old hub | Delete |
| `frontend/app/(rooms)/docs/[slug]/page.tsx` | old detail | Delete |
| `frontend/components/docs/Markdown.tsx` | Markdown renderer — bump base size/leading for reading | Modify (1 line) |
| `frontend/lib/nav.ts` | Sidebar nav — remove 文件 leaf | Modify |
| `frontend/components/shell/TopBar.tsx` | Add 文件中心 ↗ entry point | Modify |
| `DESIGN.md` | Decisions Log row for the light-docs deviation | Modify |

---

## Task 1: Publish dev-history docs via the manifest

**Files:**
- Modify: `frontend/lib/docs-manifest.ts`

**Interfaces:**
- Produces: three new `DocEntry` slugs — `overview` (README.md), `development-log` (development-log.md), `task-backlog` (task-backlog.md); new category literal `"開發歷程"`. Later tasks (hub `CATEGORIES`, `resolveHref`) rely on these slugs/files existing.

- [ ] **Step 1: Extend the category type**

In `frontend/lib/docs-manifest.ts`, change the `category` field type:

```ts
  category: "概覽" | "架構" | "功能" | "營運" | "開發歷程";
```

- [ ] **Step 2: Append the three entries**

Insert these objects at the end of the `DOCS` array, just before the closing `];`:

```ts
  {
    slug: "overview",
    title: "專案總覽",
    category: "概覽",
    file: "README.md",
    summary: "文件索引與快速導覽:從這裡開始。",
  },
  {
    slug: "development-log",
    title: "開發歷程",
    category: "開發歷程",
    file: "development-log.md",
    summary: "v1 16 個檢查點 + v2 各階段里程碑與完成驗證紀錄。",
  },
  {
    slug: "task-backlog",
    title: "任務清單／路線圖",
    category: "開發歷程",
    file: "task-backlog.md",
    summary: "v1+v2 全部任務、狀態(✅/⬜)、effort 與依賴分析。",
  },
```

- [ ] **Step 3: Sync and verify the count**

Run: `npm run sync-docs`
Expected output line: `[sync-docs] synced 12/12 docs into content/docs.`

- [ ] **Step 4: Verify the new files landed**

Run: `ls content/docs/README.md content/docs/development-log.md content/docs/task-backlog.md`
Expected: all three paths listed (no "No such file").

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/docs-manifest.ts frontend/content/docs/README.md frontend/content/docs/development-log.md frontend/content/docs/task-backlog.md
git commit -m "feat(docs): publish overview/development-log/task-backlog via manifest"
```

---

## Task 2: Add the light-theme token scope

**Files:**
- Modify: `frontend/app/globals.css`

**Interfaces:**
- Produces: a CSS rule `[data-surface="docs"]` that overrides `--bg`, `--surface-1..3`, `--border(-strong)`, `--text`, `--muted`, `--faint`, `--accent`, `--accent-dim` and sets `color-scheme: light`. Task 3's `(handbook)/layout.tsx` activates it via `data-surface="docs"`.

- [ ] **Step 1: Add the scope block**

In `frontend/app/globals.css`, insert this block immediately after the existing `[data-market="tw"] { ... }` line (before `body { ... }`):

```css
[data-surface="docs"] {
  color-scheme: light;
  --bg: #FBFBFA; --surface-1: #FFFFFF; --surface-2: #F4F5F6; --surface-3: #ECEEF0;
  --border: rgba(15,18,22,0.10); --border-strong: rgba(15,18,22,0.18);
  --text: #1A1D21; --muted: #5B616B; --faint: #8A9099;
  --accent: #0E8FA8; --accent-dim: rgba(14,143,168,0.12);
}
```

Note: keep `--up`/`--down`/`--live`/`--warning`/`--error` inherited — docs have no price semantics.

- [ ] **Step 2: Verify the scope compiles**

Run: `npm run build`
Expected: build completes with "Compiled successfully" (no CSS/PostCSS error). The scope is unused until Task 3, so no visual change yet.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/globals.css
git commit -m "feat(docs): add scoped light theme tokens for docs portal"
```

---

## Task 3: Standalone handbook shell + move docs pages

**Files:**
- Create: `frontend/app/(handbook)/layout.tsx`
- Create: `frontend/app/(handbook)/docs/page.tsx`
- Create: `frontend/app/(handbook)/docs/[slug]/page.tsx`
- Delete: `frontend/app/(rooms)/docs/page.tsx`
- Delete: `frontend/app/(rooms)/docs/[slug]/page.tsx`
- Modify: `frontend/components/docs/Markdown.tsx:22`

**Interfaces:**
- Consumes: `[data-surface="docs"]` (Task 2); `DOCS`, `getDoc` from `@/lib/docs-manifest` (Task 1); `readDocContent` from `@/lib/docs`; `Markdown`, `SystemFeatures` from `@/components/docs`.
- Produces: routes `/docs` and `/docs/[slug]` served by the light handbook layout (no `AppShell`).

- [ ] **Step 1: Remove the old docs pages from the rooms group**

Run:
```bash
git rm frontend/app/(rooms)/docs/page.tsx frontend/app/(rooms)/docs/[slug]/page.tsx
```
Expected: both files removed. (Deleting first prevents `/docs` being declared in two route groups.)

- [ ] **Step 2: Create the handbook layout**

Create `frontend/app/(handbook)/layout.tsx`:

```tsx
import Link from "next/link";

export default function HandbookLayout({ children }: { children: React.ReactNode }) {
  return (
    <div data-surface="docs" className="min-h-dvh bg-bg font-ui text-text">
      <header className="sticky top-0 z-20 border-b border-border bg-surface-1/90 backdrop-blur">
        <div className="mx-auto flex max-w-[1100px] items-center justify-between px-5 py-3">
          <Link href="/docs" className="font-display text-sm font-bold">
            AI Trade Flow<span className="text-accent">.</span>{" "}
            <span className="font-medium text-muted">文件中心</span>
          </Link>
          <Link href="/strategy-lab" className="text-[13px] text-muted hover:text-accent">
            ← 返回平台
          </Link>
        </div>
      </header>
      <main className="mx-auto max-w-[1100px] px-5 py-8">{children}</main>
    </div>
  );
}
```

- [ ] **Step 3: Create the hub page (categories extended)**

Create `frontend/app/(handbook)/docs/page.tsx`:

```tsx
import Link from "next/link";
import { DOCS, type DocEntry } from "@/lib/docs-manifest";
import { SystemFeatures } from "@/components/docs/SystemFeatures";

export const metadata = {
  title: "文件中心 · AI Trade Flow",
  description: "系統功能詳細說明與技術文件",
};

const CATEGORIES: DocEntry["category"][] = ["概覽", "架構", "功能", "營運", "開發歷程"];

export default function DocsHubPage() {
  return (
    <div className="space-y-8">
      <header>
        <h1 className="font-display text-2xl font-bold">文件中心 · Documentation</h1>
        <p className="mt-2 max-w-3xl text-[14px] leading-7 text-muted">
          AI Trade Flow 是一個給專業個人投資者的自動交易平台 — 在策略室用 AI 設計策略,於交易室回測與自動執行,
          背後是計入成本、杜絕前視偏差與過擬合的金融正確性地基。以下為系統功能詳細說明、完整技術文件與開發歷程。
        </p>
        <div className="mt-3 flex flex-wrap gap-2 text-[13px]">
          <Link
            href="/manual"
            className="rounded-md border border-border bg-surface-2 px-3 py-1.5 hover:border-accent"
          >
            圖文操作指南 /manual
          </Link>
          <a
            href="https://github.com/b5336789/ai-trade-flow-platform"
            target="_blank"
            rel="noreferrer"
            className="rounded-md border border-border bg-surface-2 px-3 py-1.5 hover:border-accent"
          >
            GitHub 原始碼
          </a>
        </div>
      </header>

      <section>
        <h2 className="mb-3 font-display text-lg font-semibold">系統功能詳細說明</h2>
        <SystemFeatures />
      </section>

      <section>
        <h2 className="mb-3 font-display text-lg font-semibold">技術文件</h2>
        <div className="space-y-5">
          {CATEGORIES.map((cat) => {
            const items = DOCS.filter((d) => d.category === cat);
            if (items.length === 0) return null;
            return (
              <div key={cat}>
                <h3 className="mb-2 text-[12px] uppercase tracking-wide text-faint">{cat}</h3>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {items.map((d) => (
                    <Link
                      key={d.slug}
                      href={`/docs/${d.slug}`}
                      className="group rounded-md border border-border bg-surface-1 p-4 transition-colors hover:border-accent"
                    >
                      <h4 className="font-display text-[14px] font-semibold group-hover:text-accent">
                        {d.title}
                      </h4>
                      <p className="mt-1 text-[12.5px] leading-relaxed text-muted">{d.summary}</p>
                    </Link>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
```

- [ ] **Step 4: Create the detail page (editorial measure, no dark card)**

Create `frontend/app/(handbook)/docs/[slug]/page.tsx`:

```tsx
import Link from "next/link";
import { notFound } from "next/navigation";
import { DOCS, getDoc } from "@/lib/docs-manifest";
import { readDocContent } from "@/lib/docs";
import { Markdown } from "@/components/docs/Markdown";

export function generateStaticParams() {
  return DOCS.map((d) => ({ slug: d.slug }));
}

export const dynamicParams = false;

export function generateMetadata({ params }: { params: { slug: string } }) {
  const doc = getDoc(params.slug);
  return { title: doc ? `${doc.title} · 文件` : "文件" };
}

export default function DocPage({ params }: { params: { slug: string } }) {
  const doc = getDoc(params.slug);
  if (!doc) notFound();
  const source = readDocContent(params.slug);

  return (
    <div className="grid grid-cols-1 gap-8 lg:grid-cols-[200px_1fr]">
      <aside className="lg:sticky lg:top-20 lg:self-start">
        <Link href="/docs" className="text-[12px] text-muted hover:text-accent">
          ← 文件中心
        </Link>
        <nav className="mt-3 space-y-0.5 text-[13px]">
          {DOCS.map((d) => (
            <Link
              key={d.slug}
              href={`/docs/${d.slug}`}
              className={`block rounded-md border-l-2 px-3 py-1.5 ${
                d.slug === doc.slug
                  ? "border-accent bg-accent-dim text-text"
                  : "border-transparent text-muted hover:bg-surface-2"
              }`}
            >
              {d.title}
            </Link>
          ))}
        </nav>
      </aside>

      <article className="min-w-0 max-w-[760px]">
        <Markdown source={source} />
      </article>
    </div>
  );
}
```

- [ ] **Step 5: Bump Markdown base size/leading for reading**

In `frontend/components/docs/Markdown.tsx`, change line 22 from:

```tsx
    <div className="max-w-none text-[14px] leading-relaxed text-text">
```

to:

```tsx
    <div className="max-w-none text-[15px] leading-7 text-text">
```

- [ ] **Step 6: Build and verify routes + standalone shell**

Run: `npm run build`
Expected: "Compiled successfully"; the route list shows `/docs` and `● /docs/[slug]` (SSG) including the new slugs. Confirm no error like "You cannot have two parallel pages that resolve to the same path".

- [ ] **Step 7: Verify the old rooms docs path is gone and no AppShell leaks in**

Run:
```bash
test ! -e "frontend/app/(rooms)/docs" && echo "rooms/docs removed"
grep -rl "AppShell" "frontend/app/(handbook)" || echo "no AppShell in handbook"
```
Expected: `rooms/docs removed` and `no AppShell in handbook`.

- [ ] **Step 8: Commit**

```bash
git add "frontend/app/(handbook)" frontend/components/docs/Markdown.tsx
git add -A "frontend/app/(rooms)/docs"
git commit -m "feat(docs): standalone light handbook shell; move /docs out of app shell"
```

---

## Task 4: Swap the entry point (sidebar leaf → top-bar link)

**Files:**
- Modify: `frontend/lib/nav.ts`
- Modify: `frontend/components/shell/TopBar.tsx`

**Interfaces:**
- Consumes: route `/docs` (Task 3).
- Produces: a persistent `文件中心 ↗` link in the App Shell top bar; the sidebar tree no longer lists 文件.

- [ ] **Step 1: Remove the 文件 leaf from the sidebar nav**

In `frontend/lib/nav.ts`, delete this line from the `NAV` array:

```ts
  { label: "文件", href: "/docs" },
```

- [ ] **Step 2: Add the top-bar entry point**

Replace the entire contents of `frontend/components/shell/TopBar.tsx` with:

```tsx
"use client";
import Link from "next/link";

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
      <span className="font-display text-sm font-bold md:hidden">
        AI Trade Flow<span className="text-accent">.</span>
      </span>
      <Link
        href="/docs"
        className="ml-auto rounded-md border border-border bg-surface-2 px-3 py-1.5 text-[13px] text-muted hover:border-accent hover:text-text"
      >
        文件中心 ↗
      </Link>
    </header>
  );
}
```

- [ ] **Step 3: Build and verify the entry-point swap**

Run:
```bash
npm run build
grep -q '文件' frontend/lib/nav.ts && echo "STILL IN NAV (fix)" || echo "nav leaf removed"
grep -q 'href="/docs"' frontend/components/shell/TopBar.tsx && echo "topbar link present"
```
Expected: build succeeds; `nav leaf removed`; `topbar link present`.

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/nav.ts frontend/components/shell/TopBar.tsx
git commit -m "feat(docs): move docs entry point from sidebar to top bar"
```

---

## Task 5: Record the design deviation + final verification

**Files:**
- Modify: `DESIGN.md` (Decisions Log table)

- [ ] **Step 1: Add a Decisions Log row**

In `DESIGN.md`, append this row to the bottom of the "Decisions Log" table:

```markdown
| 2026-06-20 | `/docs` 改為獨立亮色閱讀 Portal（`[data-surface="docs"]` scope） | 文件中心與交易終端機分流:長文閱讀需亮底/寬 measure;僅作用於 docs scope,主 App 維持深色終端機風。使用者核准的範圍內偏離。 |
```

- [ ] **Step 2: Final full verification (lint + build + sync count)**

Run from `frontend/`:
```bash
npm run sync-docs && npm run lint && npm run build
```
Expected: `synced 12/12 docs`; lint passes (no errors); build "Compiled successfully" with `/docs` and `/docs/[slug]` listed as static. Report any failure verbatim — do not proceed past a red gate.

- [ ] **Step 3: Commit**

```bash
git add DESIGN.md
git commit -m "docs: record light docs-portal deviation in DESIGN.md decisions log"
```

---

## Self-Review

**Spec coverage:**
- Standalone route group / out of AppShell → Task 3. ✓
- URL stays `/docs` → Tasks 3 (route-group move). ✓
- Light token scope (no hardcoded hex) → Task 2. ✓
- Editorial measure/leading → Task 3 (Steps 4–5). ✓
- Dev-history docs via manifest, sync 12/12 → Task 1. ✓
- Hub categories extended → Task 3 (Step 3). ✓
- Entry point: remove nav leaf + top-bar link → Task 4. ✓
- DESIGN.md deviation logged → Task 5. ✓
- Untouched: sync script, lib/docs.ts, other rooms → not modified by any task. ✓

**Placeholder scan:** No TBD/TODO; all code blocks complete; verification uses real commands (no fabricated unit tests, since no runner exists). ✓

**Type consistency:** `category` union includes `"開發歷程"` (Task 1) and the hub `CATEGORIES` array (Task 3) uses only members of that union. Slugs `overview`/`development-log`/`task-backlog` defined in Task 1 are the routes verified in Task 5. `DocEntry`, `getDoc`, `readDocContent`, `Markdown`, `SystemFeatures` signatures unchanged from current code. ✓
