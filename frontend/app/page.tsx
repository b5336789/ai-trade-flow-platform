import Link from "next/link";
import { BacktestPanel } from "@/components/BacktestPanel";
import { MarketPanel } from "@/components/MarketPanel";
import { NotificationsPanel } from "@/components/NotificationsPanel";
import { PortfolioPanel } from "@/components/PortfolioPanel";
import { SchedulesPanel } from "@/components/SchedulesPanel";
import { WorkflowBuilder } from "@/components/workflow/WorkflowBuilder";

export default function Home() {
  return (
    <main className="mx-auto max-w-7xl space-y-4 p-4">
      <header className="flex flex-wrap items-baseline gap-3">
        <h1 className="text-2xl font-bold">AI Trade Flow</h1>
        <span className="text-sm text-neutral-500">crypto · 台股 (元大) · 美股 (元大複委託 / Firstrade)</span>
        <Link
          href="/manual"
          className="ml-auto rounded bg-indigo-600 px-3 py-1 text-sm font-medium hover:bg-indigo-500"
        >
          📖 使用說明書
        </Link>
      </header>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <MarketPanel />
          <WorkflowBuilder />
          <SchedulesPanel />
          <BacktestPanel />
        </div>
        <div className="space-y-4">
          <PortfolioPanel />
          <NotificationsPanel />
        </div>
      </div>
    </main>
  );
}
