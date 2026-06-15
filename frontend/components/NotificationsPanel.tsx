"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

const DOT: Record<string, string> = {
  info: "bg-sky-400",
  success: "bg-green-400",
  warning: "bg-yellow-400",
  error: "bg-red-400",
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
    <section className="rounded-lg border border-neutral-800 bg-neutral-900/40 p-4">
      <div className="mb-3 flex items-center gap-2">
        <h2 className="text-lg font-semibold">Notifications</h2>
        <button
          onClick={test}
          className="ml-auto rounded bg-neutral-800 px-2 py-1 text-xs hover:bg-neutral-700"
        >
          Test
        </button>
      </div>

      {notifications.isError ? (
        <p className="text-sm text-red-400">{(notifications.error as Error).message}</p>
      ) : notifications.data && notifications.data.length > 0 ? (
        <ul className="space-y-1">
          {notifications.data.map((n) => (
            <li key={n.id} className="flex items-start gap-2 border-b border-neutral-800 py-1 text-xs">
              <span className={`mt-1 h-2 w-2 shrink-0 rounded-full ${DOT[n.level] ?? "bg-neutral-400"}`} />
              <div className="min-w-0 flex-1">
                <div className="truncate font-medium text-neutral-100">{n.title}</div>
                {n.message && <div className="truncate text-neutral-400">{n.message}</div>}
              </div>
              <span className="shrink-0 text-neutral-600">
                {new Date(n.created_at).toLocaleTimeString()}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-neutral-500">No notifications yet. Orders and signals appear here.</p>
      )}
    </section>
  );
}
