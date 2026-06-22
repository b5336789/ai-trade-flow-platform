"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV, type NavItem } from "@/lib/nav";
import { StrategyLibraryTree } from "./StrategyLibraryTree";

function isActive(pathname: string, href?: string) {
  return !!href && (pathname === href || pathname.startsWith(href + "/"));
}

export function TreeNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav className="flex-1 overflow-y-auto p-2 text-sm">
      {NAV.map((item) => (
        <TreeRow key={item.label} item={item} pathname={pathname} onNavigate={onNavigate} />
      ))}
    </nav>
  );
}

function TreeRow({ item, pathname, onNavigate }: { item: NavItem; pathname: string; onNavigate?: () => void }) {
  const active = isActive(pathname, item.href);
  const Icon = item.icon;
  return (
    <div>
      <Link
        href={item.href ?? "#"}
        onClick={onNavigate}
        className={`flex items-center gap-2.5 rounded-md border-l-2 px-3 py-2 ${
          active ? "border-accent bg-accent-dim text-text" : "border-transparent text-muted hover:bg-surface-2"
        }`}
      >
        {Icon && <Icon size={16} strokeWidth={1.75} className={item.ai ? "text-accent" : "text-faint"} aria-hidden />}
        <span className="nav-label font-display font-semibold leading-tight">{item.label}</span>
      </Link>
      {item.children && (
        <div className="ml-3 border-l border-border pl-1">
          {item.children.map((leaf) => {
            const la = isActive(pathname, leaf.href);
            const isLibrary = leaf.href === "/strategy-lab#library";
            const LeafIcon = leaf.icon;
            return (
              <div key={leaf.href}>
                <Link
                  href={leaf.href}
                  onClick={onNavigate}
                  className={`flex items-center gap-2.5 rounded-md border-l-2 px-3 py-2 text-[13px] ${
                    la ? `${leaf.live ? "border-live text-live" : "border-accent text-text"} bg-accent-dim`
                       : "border-transparent text-muted hover:bg-surface-2"
                  }`}
                >
                  {LeafIcon && <LeafIcon size={15} strokeWidth={1.75} className={leaf.live ? "text-live" : "text-faint"} aria-hidden />}
                  <span className="nav-label leading-tight">{leaf.label}</span>
                </Link>
                {isLibrary && <StrategyLibraryTree onNavigate={onNavigate} />}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
