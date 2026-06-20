import Link from "next/link";
import { notFound } from "next/navigation";
import { DOCS, getDoc } from "@/lib/docs-manifest";
import { readDocContent } from "@/lib/docs";
import { Markdown } from "@/components/docs/Markdown";

export function generateStaticParams() {
  return DOCS.map((d) => ({ slug: d.slug }));
}

export const dynamicParams = false;

export function generateMetadata({ params }: { params: { slug: string } }) {
  const doc = getDoc(params.slug);
  return { title: doc ? `${doc.title} · 文件` : "文件" };
}

export default function DocPage({ params }: { params: { slug: string } }) {
  const doc = getDoc(params.slug);
  if (!doc) notFound();
  const source = readDocContent(params.slug);

  return (
    <div className="grid grid-cols-1 gap-8 lg:grid-cols-[200px_1fr]">
      <aside className="lg:sticky lg:top-20 lg:self-start">
        <Link href="/docs" className="text-[12px] text-muted hover:text-accent">
          ← 文件中心
        </Link>
        <nav className="mt-3 space-y-0.5 text-[13px]">
          {DOCS.map((d) => (
            <Link
              key={d.slug}
              href={`/docs/${d.slug}`}
              className={`block rounded-md border-l-2 px-3 py-1.5 ${
                d.slug === doc.slug
                  ? "border-accent bg-accent-dim text-text"
                  : "border-transparent text-muted hover:bg-surface-2"
              }`}
            >
              {d.title}
            </Link>
          ))}
        </nav>
      </aside>

      <article className="min-w-0 max-w-[760px]">
        <Markdown source={source} />
      </article>
    </div>
  );
}
