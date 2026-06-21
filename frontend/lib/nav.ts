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
