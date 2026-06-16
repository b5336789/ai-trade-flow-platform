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
    <section className="card">
      <div className="mb-3 flex items-center gap-2">
        <h2 className="panel-title">🔔 通知 Notifications</h2>
        {notifications.data && notifications.data.length > 0 && (
          <span className="badge bg-neutral-800 text-neutral-400">{notifications.data.length}</span>
        )}
        <button onClick={test} className="btn btn-ghost btn-xs ml-auto">
          測試
        </button>
      </div>

      {notifications.isError ? (
        <p className="text-sm text-red-400">{(notifications.error as Error).message}</p>
      ) : notifications.data && notifications.data.length > 0 ? (
        <ul className="space-y-1">
          {notifications.data.map((n) => (
            <li
              key={n.id}
              className="flex items-start gap-2 rounded-md border-b border-white/5 px-1 py-1.5 text-xs transition-colors hover:bg-white/5"
            >
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
        <div className="flex flex-col items-center gap-1 py-6 text-center">
          <span className="text-2xl opacity-50">🔕</span>
          <p className="text-xs text-neutral-500">尚無通知。成交與訊號會即時顯示於此。</p>
        </div>
      )}
    </section>
  );
}
