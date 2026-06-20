import Link from "next/link";
import { DOCS, type DocEntry } from "@/lib/docs-manifest";
import { SystemFeatures } from "@/components/docs/SystemFeatures";

export const metadata = {
  title: "文件中心 · AI Trade Flow",
  description: "系統功能詳細說明與技術文件",
};

const CATEGORIES: DocEntry["category"][] = ["概覽", "架構", "功能", "營運", "開發歷程"];

export default function DocsHubPage() {
  return (
    <div className="space-y-8">
      <header>
        <h1 className="font-display text-2xl font-bold">文件中心 · Documentation</h1>
        <p className="mt-2 max-w-3xl text-[14px] leading-7 text-muted">
          AI Trade Flow 是一個給專業個人投資者的自動交易平台 — 在策略室用 AI 設計策略,於交易室回測與自動執行,
          背後是計入成本、杜絕前視偏差與過擬合的金融正確性地基。以下為系統功能詳細說明、完整技術文件與開發歷程。
        </p>
        <div className="mt-3 flex flex-wrap gap-2 text-[13px]">
          <Link
            href="/manual"
            className="rounded-md border border-border bg-surface-2 px-3 py-1.5 hover:border-accent"
          >
            圖文操作指南 /manual
          </Link>
          <a
            href="https://github.com/b5336789/ai-trade-flow-platform"
            target="_blank"
            rel="noreferrer"
            className="rounded-md border border-border bg-surface-2 px-3 py-1.5 hover:border-accent"
          >
            GitHub 原始碼
          </a>
        </div>
      </header>

      <section>
        <h2 className="mb-3 font-display text-lg font-semibold">系統功能詳細說明</h2>
        <SystemFeatures />
      </section>

      <section>
        <h2 className="mb-3 font-display text-lg font-semibold">技術文件</h2>
        <div className="space-y-5">
          {CATEGORIES.map((cat) => {
            const items = DOCS.filter((d) => d.category === cat);
            if (items.length === 0) return null;
            return (
              <div key={cat}>
                <h3 className="mb-2 text-[12px] uppercase tracking-wide text-faint">{cat}</h3>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {items.map((d) => (
                    <Link
                      key={d.slug}
                      href={`/docs/${d.slug}`}
                      className="group rounded-md border border-border bg-surface-1 p-4 transition-colors hover:border-accent"
                    >
                      <h4 className="font-display text-[14px] font-semibold group-hover:text-accent">
                        {d.title}
                      </h4>
                      <p className="mt-1 text-[12.5px] leading-relaxed text-muted">{d.summary}</p>
                    </Link>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
