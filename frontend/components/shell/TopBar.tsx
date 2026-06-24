"use client";
import Link from "next/link";
import { ThemeToggle } from "@/components/shell/ThemeToggle";

export function TopBar({ open, onMenu }: { open: boolean; onMenu: () => void }) {
  return (
    <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-border bg-bg/85 px-4 py-3 backdrop-blur">
      <button
        onClick={onMenu}
        aria-label="menu"
        aria-expanded={open}
        className="rounded-md border border-border-strong bg-surface-2 px-2.5 py-1.5 text-text md:hidden"
      >
        ☰
      </button>
      <Link href="/" aria-label="首頁" className="font-display text-sm font-bold md:hidden">
        AI Trade Flow<span className="text-accent">.</span>
      </Link>
      <div className="ml-auto flex items-center gap-3">
        <ThemeToggle />
        <Link
          href="/docs"
          className="rounded-md border border-border bg-surface-2 px-3 py-1.5 text-[13px] text-muted hover:border-accent hover:text-text"
        >
          文件中心 ↗
        </Link>
      </div>
    </header>
  );
}
