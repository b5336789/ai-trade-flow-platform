import type { ComponentPropsWithoutRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { DOCS } from "@/lib/docs-manifest";

// Map a relative ./foo.md link in the source docs to its published /docs route,
// falling back to the GitHub source when the target isn't published.
const REPO_BLOB = "https://github.com/b5336789/ai-trade-flow-platform/blob/main/docs/";

function resolveHref(href: string): { href: string; external: boolean } {
  if (/^https?:\/\//.test(href)) return { href, external: true };
  if (href.startsWith("#")) return { href, external: false };
  const file = href.replace(/^\.\//, "").replace(/^\.\.\//, "").split("/").pop() ?? href;
  const match = DOCS.find((d) => d.file === file);
  if (match) return { href: `/docs/${match.slug}`, external: false };
  if (file.endsWith(".md")) return { href: `${REPO_BLOB}${file}`, external: true };
  return { href, external: true };
}

export function Markdown({ source }: { source: string }) {
  return (
    <div className="max-w-none text-[15px] leading-7 text-text">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: (p) => <h1 className="mb-4 mt-2 font-display text-2xl font-bold" {...p} />,
          h2: (p) => (
            <h2 className="mb-3 mt-8 border-b border-border pb-1.5 font-display text-xl font-semibold" {...p} />
          ),
          h3: (p) => <h3 className="mb-2 mt-6 font-display text-base font-semibold" {...p} />,
          h4: (p) => <h4 className="mb-1.5 mt-4 font-display text-sm font-semibold text-muted" {...p} />,
          p: (p) => <p className="my-3 text-text/90" {...p} />,
          ul: (p) => <ul className="my-3 ml-5 list-disc space-y-1.5 marker:text-faint" {...p} />,
          ol: (p) => <ol className="my-3 ml-5 list-decimal space-y-1.5 marker:text-faint" {...p} />,
          li: (p) => <li className="text-text/90" {...p} />,
          a: ({ href, ...rest }) => {
            const r = resolveHref(href ?? "#");
            return (
              <a
                href={r.href}
                {...(r.external ? { target: "_blank", rel: "noreferrer" } : {})}
                className="text-accent underline decoration-accent/40 underline-offset-2 hover:decoration-accent"
                {...rest}
              />
            );
          },
          strong: (p) => <strong className="font-semibold text-text" {...p} />,
          blockquote: (p) => (
            <blockquote
              className="my-4 border-l-2 border-accent/50 bg-surface-2 px-4 py-2 text-muted [&>p]:my-1"
              {...p}
            />
          ),
          hr: () => <hr className="my-6 border-border" />,
          code: ({ className, children, ...rest }: ComponentPropsWithoutRef<"code">) => {
            const isBlock = (className ?? "").includes("language-");
            if (isBlock) {
              return (
                <code className={`font-code text-[12.5px] ${className ?? ""}`} {...rest}>
                  {children}
                </code>
              );
            }
            return (
              <code className="rounded-sm bg-surface-3 px-1.5 py-0.5 font-code text-[12.5px] text-accent" {...rest}>
                {children}
              </code>
            );
          },
          pre: (p) => (
            <pre
              className="my-4 overflow-x-auto rounded-md border border-border bg-bg p-3 font-code text-[12.5px] leading-relaxed"
              {...p}
            />
          ),
          table: (p) => (
            <div className="my-4 overflow-x-auto">
              <table className="w-full border-collapse text-[13px]" {...p} />
            </div>
          ),
          thead: (p) => <thead className="text-faint" {...p} />,
          th: (p) => <th className="border-b border-border px-3 py-1.5 text-left font-medium" {...p} />,
          td: (p) => <td className="border-b border-border px-3 py-1.5 align-top text-text/90" {...p} />,
        }}
      >
        {source}
      </ReactMarkdown>
    </div>
  );
}
