import Link from "next/link";

export default function HandbookLayout({ children }: { children: React.ReactNode }) {
  return (
    <div data-surface="docs" className="min-h-dvh bg-bg font-ui text-text">
      <header className="sticky top-0 z-20 border-b border-border bg-surface-1/90 backdrop-blur">
        <div className="mx-auto flex max-w-[1100px] items-center justify-between px-5 py-3">
          <Link href="/docs" className="font-display text-sm font-bold">
            AI Trade Flow<span className="text-accent">.</span>{" "}
            <span className="font-medium text-muted">文件中心</span>
          </Link>
          <Link href="/strategy-lab" className="text-[13px] text-muted hover:text-accent">
            ← 返回平台
          </Link>
        </div>
      </header>
      <main className="mx-auto max-w-[1100px] px-5 py-8">{children}</main>
    </div>
  );
}
