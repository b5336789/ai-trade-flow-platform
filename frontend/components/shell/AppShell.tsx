"use client";
import { useEffect, useState } from "react";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <div className="min-h-dvh md:grid md:grid-cols-[64px_1fr] xl:grid-cols-[240px_1fr]">
      {/* desktop/tablet sidebar; labels hidden in rail (<xl) via .nav-label */}
      <div className="hidden md:block sticky top-0 h-dvh border-r border-border [&_.nav-label]:hidden xl:[&_.nav-label]:inline">
        <Sidebar />
      </div>
      {/* mobile drawer */}
      {open && <div className="fixed inset-0 z-30 bg-black/55 md:hidden" onClick={() => setOpen(false)} />}
      <div
        aria-hidden={!open}
        {...(!open && { inert: "" as unknown as boolean })}
        className={`fixed inset-y-0 left-0 z-40 w-[240px] transition-transform md:hidden ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <Sidebar onNavigate={() => setOpen(false)} />
      </div>
      <div className="min-w-0">
        <TopBar open={open} onMenu={() => setOpen(true)} />
        <main className="mx-auto max-w-[1440px] p-4">{children}</main>
      </div>
    </div>
  );
}
