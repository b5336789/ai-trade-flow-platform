"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV, type NavItem } from "@/lib/nav";

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
  const dot = item.ai ? "bg-accent" : "bg-faint";
  return (
    <div>
      <Link
        href={item.href ?? "#"}
        onClick={onNavigate}
        className={`flex items-center gap-2 rounded-md border-l-2 px-3 py-2 ${
          active ? "border-accent bg-accent-dim text-text" : "border-transparent text-muted hover:bg-surface-2"
        }`}
      >
        <span className={`h-1.5 w-1.5 rounded-sm ${dot}`} />
        <span className="nav-label flex min-w-0 flex-col leading-tight">
          <span className="font-display font-semibold">{item.label}</span>
          {item.subtitle && (
            <span className="text-[11px] font-normal text-faint">{item.subtitle}</span>
          )}
        </span>
      </Link>
      {item.children && (
        <div className="ml-3 border-l border-border pl-1">
          {item.children.map((leaf) => {
            const la = isActive(pathname, leaf.href);
            return (
              <Link
                key={leaf.href}
                href={leaf.href}
                onClick={onNavigate}
                className={`flex items-center gap-2 rounded-md border-l-2 px-3 py-2 text-[13px] ${
                  la ? `${leaf.live ? "border-live text-live" : "border-accent text-text"} bg-accent-dim`
                     : "border-transparent text-muted hover:bg-surface-2"
                }`}
              >
                <span className="nav-label flex min-w-0 flex-col leading-tight">
                  <span>{leaf.label}</span>
                  {leaf.subtitle && (
                    <span className="text-[11px] text-faint">{leaf.subtitle}</span>
                  )}
                </span>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
