import { TreeNav } from "./TreeNav";

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <aside className="flex h-full flex-col bg-surface-1">
      <div className="flex items-center gap-2 border-b border-border px-4 py-4">
        <span className="font-display text-base font-bold">
          AI Trade Flow<span className="text-accent">.</span>
        </span>
      </div>
      <TreeNav onNavigate={onNavigate} />
    </aside>
  );
}
