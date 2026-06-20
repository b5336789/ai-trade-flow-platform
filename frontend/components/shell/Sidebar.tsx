import Link from "next/link";
import { TreeNav } from "./TreeNav";

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <aside className="flex h-full flex-col bg-surface-1">
      <div className="border-b border-border px-4 py-4">
        <Link
          href="/"
          onClick={onNavigate}
          aria-label="首頁"
          className="font-display text-base font-bold hover:text-accent"
        >
          AI Trade Flow<span className="text-accent">.</span>
        </Link>
      </div>
      <TreeNav onNavigate={onNavigate} />
    </aside>
  );
}
