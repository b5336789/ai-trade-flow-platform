# 設計：獨立亮色文件 Portal（文件中心改入口 + 換風格 + 併入開發歷程）

- 日期：2026-06-20
- 狀態：已核准，待 review
- 分支：`feature/docs-portal-light`

## 目標

把現有 `/docs` 文件中心從「埋在交易終端機 App Shell 裡、共用深色密集風」改造成：

1. **另一個入口點** — 脫離左側樹狀導覽，成為一個獨立文件 Portal。
2. **另一個風格** — 亮色閱讀／文件風（編輯式排版），與深色交易終端機完全區隔。
3. **併入開發歷程** — 把 `development-log.md`、`task-backlog.md`、`README.md` 一併發布。

URL 維持 `/docs`、`/docs/[slug]`（沿用，舊連結不斷）。

## 現況（改造前）

- 文件頁在 `app/(rooms)/docs/`，被 `app/(rooms)/layout.tsx` 的 `<AppShell>` 包住，沿用深色終端機風與左側 `TreeNav`。
- 導覽 `lib/nav.ts` 的 `NAV` 有一個 `{ label: "文件", href: "/docs" }` leaf。
- 文件清單單一真實來源：`lib/docs-manifest.ts`（`DOCS: DocEntry[]`，目前 9 篇，category 型別 `"概覽" | "架構" | "功能" | "營運"`）。
- `scripts/sync-docs.mjs` 用 regex 從 manifest 抽 `file:` 清單，把 `docs/*.md` 複製進 `frontend/content/docs/`（committed，供 Docker build）。predev/prebuild 自動跑。
- `lib/docs.ts` 從 `content/docs/` 讀檔；頁面 SSG 靜態預渲染。
- `components/docs/Markdown.tsx` 用 react-markdown + remark-gfm，class 全是 token utility（`text-accent`、`bg-surface-3`…）；`resolveHref` 把相對 `.md` 連結對應到已發布 route，未發布者 fallback 到 GitHub blob。
- CSS token 定義在 `app/globals.css` 的 `:root`（深色）；`tailwind.config.ts` 把 token 映成 utility（`bg-bg`、`text-muted`、`font-display`…）。字體在 `app/layout.tsx` 用 next/font 綁 CSS 變數。

## 設計

### 1. 架構：獨立 route group，脫離 AppShell

- 新增 route group **`app/(handbook)/`**，含自己的 `layout.tsx`：**不包 `AppShell`**。改為亮色文件外殼：
  - 最外層 wrapper 帶 `data-surface="docs"`（觸發亮色 token scope）、`min-h-dvh bg-bg`（此 scope 內 `--bg` 已被覆寫成亮色）。
  - 亮色頂部 bar（sticky）：左側品牌 `AI Trade Flow · 文件中心`，右側「← 返回平台」連回 `/strategy-lab`。
- 把 `app/(rooms)/docs/page.tsx` 與 `app/(rooms)/docs/[slug]/page.tsx` **搬到** `app/(handbook)/docs/`，並從 `(rooms)` 移除（避免兩個 group 都宣告 `/docs` 造成路由衝突）。route group 名稱在括號內，不影響 URL，故路徑維持 `/docs`、`/docs/[slug]`。
- `lib/docs.ts`、`generateStaticParams`、`dynamicParams = false`、SSG 行為不變。

### 2. 亮色主題：token 覆寫（不寫死 hex）

在 `app/globals.css` 新增一段 scope（緊接 `:root` 之後）：

```css
[data-surface="docs"] {
  color-scheme: light;
  --bg: #FBFBFA; --surface-1: #FFFFFF; --surface-2: #F4F5F6; --surface-3: #ECEEF0;
  --border: rgba(15,18,22,0.10); --border-strong: rgba(15,18,22,0.18);
  --text: #1A1D21; --muted: #5B616B; --faint: #8A9099;
  --accent: #0E8FA8; --accent-dim: rgba(14,143,168,0.12);
}
```

- 因為文件相關元件（`docs/page.tsx`、`docs/[slug]/page.tsx`、`Markdown.tsx`、`SystemFeatures.tsx`）的 class 全是 token utility（`bg-surface-1`、`text-muted`、`border-border`、`text-accent`…），套上這個 scope 後**整批自動變亮色**，元件 class 幾乎不用改。
- 保留品牌字體（Space Grotesk 標題 / Geist 內文）與青色 DNA（`--accent` 採深一階的 `#0E8FA8`，亮底可讀）。
- `--up`/`--down`/`--live`/`--warning`/`--error` 不在文件 scope 覆寫（文件無價格語意需求；維持繼承值即可，且文件內不使用）。

#### 閱讀風微調

- 文章容器 measure 放寬至約 `72ch`、`leading-7`、內文字級 15px（目前 14px）。
- 調整點集中在 `app/(handbook)/docs/[slug]/page.tsx` 的 `<article>` 容器與 `Markdown.tsx` 最外層 wrapper 的字級/行距；**不改** Markdown 各元素的結構與 token class。

> **DESIGN.md 偏離聲明**：DESIGN.md 規定深色終端機密集風。本設計在 `/docs` 改為亮色閱讀風，屬經使用者明確核准的偏離，且僅作用於 `[data-surface="docs"]` scope，主 App 與其餘 room 完全不受影響。實作完成後於 DESIGN.md 的 Decisions Log 補一列記錄。

### 3. 開發歷程併入 manifest（不破壞單一真實來源）

`lib/docs-manifest.ts`：

- `DocEntry.category` 型別新增 `"開發歷程"` → `"概覽" | "架構" | "功能" | "營運" | "開發歷程"`。
- 新增三筆 entry：

  | slug | file | category | title | summary（範例，實作時定稿） |
  |---|---|---|---|---|
  | `overview` | `README.md` | 概覽 | 專案總覽 | 文件索引與快速導覽:從這裡開始。 |
  | `development-log` | `development-log.md` | 開發歷程 | 開發歷程 | v1 16 個檢查點 + v2 各階段里程碑與驗證紀錄。 |
  | `task-backlog` | `task-backlog.md` | 開發歷程 | 任務清單／路線圖 | v1+v2 全部任務、狀態與依賴分析。 |

- `scripts/sync-docs.mjs`：**零改動**。它從 manifest 抽 `file:` 清單，新增的三檔會自動被複製進 `content/docs/`。
- 交叉連結：新增三檔內部互連的 `.md`（如 task-backlog ↔ development-log ↔ README）會被 `resolveHref` 對應到已發布 route；未納入的 `PRD-v2.md` 維持既有的 GitHub blob fallback（已驗證無圖片引用，故不需處理 image 路徑）。

### 4. hub 頁分類擴充

`app/(handbook)/docs/page.tsx` 的 `CATEGORIES` 由 `["架構", "功能", "營運"]` 改為涵蓋 `["概覽", "架構", "功能", "營運", "開發歷程"]`，讓新分類與總覽顯示在卡片列表。其餘 hub 內容（intro、`<SystemFeatures />`、`/manual` 與 GitHub 連結）沿用。

### 5. 入口點（換位置）

- `lib/nav.ts`：**移除** `{ label: "文件", href: "/docs" }` leaf（文件不再是 in-shell room）。
- `components/shell/TopBar.tsx`：在右側加一個常駐「**文件中心 ↗**」連結（`<Link href="/docs">`），桌機與手機皆可見。這是新的、與 room 樹分離的入口點。

### 6. 明確不動的範圍

- 主 App 深色終端機風與其餘所有 room（策略室／交易室／市場／投組／排程／通知／匯入）。
- `scripts/sync-docs.mjs` 邏輯、`lib/docs.ts` 讀檔邏輯、SSG／standalone 產出方式。
- `Markdown.tsx` 與 `SystemFeatures.tsx` 的結構與 token class（僅繼承 scope 後的亮色變數，必要時只調最外層字級/measure）。

## 成功標準（可驗證）

1. 造訪 `/docs` 與 `/docs/[slug]`：呈現亮色閱讀風，**不出現** App Shell 左側樹狀導覽；有亮色頂部 bar 與「← 返回平台」。
2. 主 App 任一 room 的 TopBar 右側可見「文件中心 ↗」入口，點擊進入 Portal；左側樹狀導覽**不再**有「文件」項目。
3. `/docs/development-log`、`/docs/task-backlog`、`/docs/overview` 三條 route 可正常渲染對應 markdown（含表格／checkbox，remark-gfm）。
4. `npm run sync-docs` 報告同步 **12/12** 篇（原 9 + 新 3），`content/docs/` 含 `development-log.md`、`task-backlog.md`、`README.md`。
5. 主 App 其餘 room 視覺與行為不變（深色、左側 TreeNav 仍在）。
6. `npm run build` 成功，三條新 route 進入 `generateStaticParams` 並靜態預渲染。

## 風險與緩解

- **路由衝突**：必須把 `docs/` 從 `(rooms)` 移除後才在 `(handbook)` 建立，否則同一 `/docs` 路徑重複宣告會 build 失敗。→ 計畫中以「移動」而非「複製」處理。
- **亮色對比**：`--accent #0E8FA8` 與 `--text #1A1D21` 對亮底需達 AA。→ 實作後目視 + 必要時微調。
- **README 作為文件條目語意**：README 原為 repo 文件索引，作為 `/docs/overview` 呈現時內部連結需能解析（已由 `resolveHref` 涵蓋）。

## 不在範圍（YAGNI）

- 不另建獨立靜態站（Docusaurus 等）。
- 不發布 `PRD-v2.md`（維持 GitHub fallback）。
- 不從 git log 自動生成 commit 時間軸。
- 不做文件全文搜尋、版本切換、i18n。
