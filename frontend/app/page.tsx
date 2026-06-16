import { AppHeader } from "@/components/AppHeader";
import { BacktestPanel } from "@/components/BacktestPanel";
import { DataImportPanel } from "@/components/DataImportPanel";
import { MarketPanel } from "@/components/MarketPanel";
import { NotificationsPanel } from "@/components/NotificationsPanel";
import { PortfolioPanel } from "@/components/PortfolioPanel";
import { SchedulesPanel } from "@/components/SchedulesPanel";
import { WorkflowBuilder } from "@/components/workflow/WorkflowBuilder";

export default function Home() {
  return (
    <div className="min-h-screen">
      <AppHeader />
      <main className="mx-auto max-w-7xl animate-fade-in space-y-4 p-4">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div className="space-y-4 lg:col-span-2">
            <MarketPanel />
            <WorkflowBuilder />
            <SchedulesPanel />
            <BacktestPanel />
            <DataImportPanel />
          </div>
          <div className="space-y-4 lg:sticky lg:top-[4.5rem] lg:self-start">
            <PortfolioPanel />
            <NotificationsPanel />
          </div>
        </div>
      </main>
    </div>
  );
}
