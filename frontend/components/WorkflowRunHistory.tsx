"use client";

import { useEffect, useState } from "react";
import { api, type WorkflowRunDTO } from "@/lib/api";

export function WorkflowRunHistory({
  kind,
  onOpen,
  refreshKey,
}: {
  kind?: string;
  onOpen: (runId: number) => void;
  refreshKey?: number;
}) {
  const [runs, setRuns] = useState<WorkflowRunDTO[]>([]);

  useEffect(() => {
    api.listWorkflowRuns({ kind, limit: 50 }).then(setRuns).catch(() => setRuns([]));
  }, [kind, refreshKey]);

  if (runs.length === 0) return null;

  return (
    <div className="m-3 rounded-lg border border-border bg-surface-2 p-3">
      <h3 className="mb-2 font-display text-xs font-semibold text-muted">過去回測 · Run History</h3>
      <ul className="space-y-1">
        {runs.map((r) => (
          <li key={r.id}>
            <button
              onClick={() => onOpen(r.id)}
              className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-xs hover:bg-surface-3"
            >
              <span className="rounded-sm bg-surface-3 px-1.5 py-0.5 text-[10px] text-muted uppercase">
                {r.kind}
              </span>
              <span className="flex-1 truncate text-left text-text">
                {r.symbols.join(", ")}
              </span>
              <span
                className={
                  (r.metrics_json?.total_return_pct ?? 0) >= 0
                    ? "text-up"
                    : "text-down"
                }
              >
                {r.metrics_json?.total_return_pct != null
                  ? `${r.metrics_json.total_return_pct.toFixed(2)}%`
                  : "—"}
              </span>
              <time className="text-faint">
                {new Date(r.created_at).toLocaleString()}
              </time>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
