"use client";

import { useEffect, useState } from "react";

// Client-only Mermaid renderer for the /docs handbook. `mermaid` is dynamically
// imported inside the effect so (a) it never runs during SSG (it needs the DOM)
// and (b) the ~heavy bundle is code-split and only loads on docs pages that
// actually contain a diagram. On failure it falls back to the raw source so the
// content is never lost.
let counter = 0;

export function MermaidDiagram({ chart }: { chart: string }) {
  const [svg, setSvg] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({
          startOnLoad: false,
          theme: "dark",
          securityLevel: "loose", // repo-authored docs only; needed for <br/> labels
          fontFamily: "var(--font-geist), ui-sans-serif, sans-serif",
        });
        const { svg } = await mermaid.render(`mmd-${counter++}`, chart);
        if (!cancelled) setSvg(svg);
      } catch {
        if (!cancelled) setFailed(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [chart]);

  if (failed) {
    return (
      <pre className="my-4 overflow-x-auto rounded-md border border-border bg-bg p-3 font-code text-[12.5px] leading-relaxed">
        {chart}
      </pre>
    );
  }
  if (!svg) {
    return (
      <div className="my-4 grid place-items-center rounded-md border border-border bg-surface-1 p-6 text-xs text-faint">
        繪製圖表中…
      </div>
    );
  }
  return (
    <div
      className="my-4 flex justify-center overflow-x-auto rounded-md border border-border bg-surface-1 p-3 [&_svg]:max-w-full"
      // eslint-disable-next-line react/no-danger -- SVG produced by mermaid from trusted repo docs
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
