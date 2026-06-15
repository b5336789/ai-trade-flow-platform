import { BacktestPanel } from "@/components/BacktestPanel";
import { MarketPanel } from "@/components/MarketPanel";
import { PortfolioPanel } from "@/components/PortfolioPanel";
import { WorkflowBuilder } from "@/components/workflow/WorkflowBuilder";

export default function Home() {
  return (
    <main className="mx-auto max-w-7xl space-y-4 p-4">
      <header className="flex items-baseline gap-3">
        <h1 className="text-2xl font-bold">AI Trade Flow</h1>
        <span className="text-sm text-neutral-500">crypto · 台股 (元大) · 美股 (元大複委託 / Firstrade)</span>
      </header>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <MarketPanel />
          <WorkflowBuilder />
          <BacktestPanel />
        </div>
        <PortfolioPanel />
      </div>
    </main>
  );
}
