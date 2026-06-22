// Curated set of repo docs published to the website under /docs.
// Source of truth is repo-root docs/*.md; scripts/sync-docs.mjs copies them into
// content/docs/ (committed) so the Docker frontend build — whose context is
// frontend/ only — can render them without reaching outside the build context.
export interface DocEntry {
  slug: string;
  title: string;
  category: "概覽" | "架構" | "功能" | "營運" | "開發歷程";
  file: string;
  summary: string;
}

export const DOCS: DocEntry[] = [
  {
    slug: "architecture",
    title: "系統架構",
    category: "架構",
    file: "architecture.md",
    summary: "後端/前端分層、Broker 抽象接縫、工作流引擎與資料模型。",
  },
  {
    slug: "backend",
    title: "後端模組",
    category: "架構",
    file: "backend.md",
    summary: "FastAPI 路由、SQLModel 資料表、交易執行與風控模組導覽。",
  },
  {
    slug: "api-reference",
    title: "API 參考",
    category: "架構",
    file: "api-reference.md",
    summary: "所有 REST 端點:行情、AI 訊號、回測、工作流、排程、通知、帳本。",
  },
  {
    slug: "frontend",
    title: "前端 / UI",
    category: "架構",
    file: "frontend.md",
    summary: "兩室 IA、共用即時線圖 PriceChart、市場看盤、回測介面、策略室→回測→工作流串接、語言層。",
  },
  {
    slug: "strategies",
    title: "策略與指標",
    category: "功能",
    file: "strategies.md",
    summary: "內建技術指標策略、宣告式策略 spec,以及 AI 策略設計。",
  },
  {
    slug: "backtesting",
    title: "回測引擎",
    category: "功能",
    file: "backtesting.md",
    summary: "成本模型、next-bar 成交、風險指標、樣本外 / Walk-forward 驗證。",
  },
  {
    slug: "workflow",
    title: "工作流引擎",
    category: "功能",
    file: "workflow.md",
    summary: "節點式工作流:資料 → 策略/AI → 邏輯 → 下單 → 輸出,拓撲執行。",
  },
  {
    slug: "configuration",
    title: "設定與安全",
    category: "營運",
    file: "configuration.md",
    summary: "環境變數、API token、CORS、交易模式與交易所金鑰權限指引。",
  },
  {
    slug: "testing",
    title: "測試策略",
    category: "營運",
    file: "testing.md",
    summary: "業務邏輯導向的 pytest 套件:正常路徑、fail-loud、邊界與回歸。",
  },
  {
    slug: "go-live-checklist",
    title: "上線檢查清單",
    category: "營運",
    file: "go-live-checklist.md",
    summary: "切換真實交易前必須逐項確認的金融正確性與風控閘門。",
  },
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
];

export function getDoc(slug: string): DocEntry | undefined {
  return DOCS.find((d) => d.slug === slug);
}
