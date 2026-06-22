"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { L } from "@/lib/labels";

const DOT: Record<string, string> = {
  info: "bg-sky-400",
  success: "bg-up",
  warning: "bg-warning",
  error: "bg-error",
};

export function NotificationsPanel() {
  const qc = useQueryClient();
  const notifications = useQuery({
    queryKey: ["notifications"],
    queryFn: api.listNotifications,
    refetchInterval: 5000,
    retry: false,
  });

  async function test() {
    await api.testNotification();
    qc.invalidateQueries({ queryKey: ["notifications"] });
  }

  return (
    <section className="rounded-lg border border-border bg-surface-1 p-4">
      <div className="mb-3 flex items-center gap-2">
        <h2 className="font-display text-lg font-semibold">{L.notifications.title}</h2>
        <button
          onClick={test}
          className="ml-auto rounded-md bg-surface-2 px-2 py-1 text-xs hover:bg-surface-3"
        >
          {L.notifications.test}
        </button>
      </div>

      {notifications.isError ? (
        <p className="text-sm text-error">{(notifications.error as Error).message}</p>
      ) : notifications.data && notifications.data.length > 0 ? (
        <ul className="space-y-1">
          {notifications.data.map((n) => (
            <li key={n.id} className="flex items-start gap-2 border-b border-border py-1 text-xs">
              <span className={`mt-1 h-2 w-2 shrink-0 rounded-full ${DOT[n.level] ?? "bg-muted"}`} />
              <div className="min-w-0 flex-1">
                <div className="truncate font-medium text-text">{n.title}</div>
                {n.message && <div className="truncate text-muted">{n.message}</div>}
              </div>
              <span className="shrink-0 text-faint">
                {new Date(n.created_at).toLocaleTimeString()}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-faint">{L.notifications.empty}</p>
      )}
    </section>
  );
}
