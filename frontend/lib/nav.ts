import {
  FlaskConical, MessageSquareCode, Library,
  Network, History, Workflow,
  CandlestickChart, Wallet,
  Wrench, CalendarClock, Bell, Upload,
  type LucideIcon,
} from "lucide-react";

export interface NavLeaf { label: string; href: string; live?: boolean; icon?: LucideIcon }
export interface NavItem { label: string; href?: string; ai?: boolean; icon?: LucideIcon; children?: NavLeaf[] }

export const NAV: NavItem[] = [
  {
    label: "策略室",
    ai: true,
    icon: FlaskConical,
    children: [
      { label: "與 AI 設計策略", href: "/strategy-lab", icon: MessageSquareCode },
      // 策略庫 saved strategies are injected dynamically under this leaf (see StrategyLibraryTree).
      { label: "策略庫", href: "/strategy-lab#library", icon: Library },
    ],
  },
  {
    label: "交易室",
    icon: Network,
    children: [
      { label: "模擬回測", href: "/trading-room/backtest", icon: History },
      { label: "工作流", href: "/trading-room/workflow", icon: Workflow },
    ],
  },
  { label: "市場", href: "/market", icon: CandlestickChart },
  { label: "投組", href: "/portfolio", icon: Wallet },
  {
    label: "工具",
    icon: Wrench,
    children: [
      { label: "排程", href: "/schedules", icon: CalendarClock },
      { label: "通知", href: "/notifications", icon: Bell },
      { label: "匯入", href: "/data-import", icon: Upload },
    ],
  },
];
