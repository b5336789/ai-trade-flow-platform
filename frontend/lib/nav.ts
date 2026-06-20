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
