"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";

export function SchedulesPanel() {
  const qc = useQueryClient();
  const workflows = useQuery({ queryKey: ["workflows"], queryFn: api.listWorkflows, retry: false });
  const schedules = useQuery({
    queryKey: ["schedules"],
    queryFn: api.listSchedules,
    refetchInterval: 5000,
    retry: false,
  });

  const [workflowId, setWorkflowId] = useState<number | "">("");
  const [interval, setInterval] = useState(60);
  const [error, setError] = useState<string | null>(null);

  async function schedule() {
    setError(null);
    if (workflowId === "") {
      setError("Select a saved workflow first (save one in the builder above).");
      return;
    }
    try {
      await api.createSchedule(Number(workflowId), interval);
      qc.invalidateQueries({ queryKey: ["schedules"] });
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function toggle(id: number) {
    await api.toggleSchedule(id);
    qc.invalidateQueries({ queryKey: ["schedules"] });
  }

  async function remove(id: number) {
    await api.deleteSchedule(id);
    qc.invalidateQueries({ queryKey: ["schedules"] });
  }

  const wfName = (id: number) => workflows.data?.find((w) => w.id === id)?.name ?? `#${id}`;

  return (
    <section className="card">
      <h2 className="panel-title mb-3">⏱️ 自動執行 Schedules</h2>

      <div className="mb-3 flex flex-wrap items-end gap-2">
        <label className="text-xs text-neutral-400">
          workflow
          <select
            value={workflowId}
            onChange={(e) => setWorkflowId(e.target.value === "" ? "" : Number(e.target.value))}
            className="input ml-1"
          >
            <option value="">— 選擇 —</option>
            {workflows.data?.map((w) => (
              <option key={w.id} value={w.id}>
                #{w.id} {w.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs text-neutral-400">
          每隔 (秒)
          <input
            type="number"
            min={5}
            value={interval}
            onChange={(e) => setInterval(Number(e.target.value))}
            className="input ml-1 w-20 px-1.5 py-1"
          />
        </label>
        <button onClick={schedule} className="btn btn-success">
          建立排程
        </button>
      </div>

      {error && <p className="mb-2 text-sm text-red-400">{error}</p>}

      {schedules.data && schedules.data.length > 0 ? (
        <table className="w-full text-left text-xs">
          <thead className="text-neutral-500">
            <tr>
              <th className="py-1 font-medium">Workflow</th>
              <th className="font-medium">Interval</th>
              <th className="font-medium">State</th>
              <th className="font-medium">Last run</th>
              <th className="font-medium">Last status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {schedules.data.map((s) => (
              <tr key={s.id} className="border-t border-white/5 transition-colors hover:bg-white/5">
                <td className="py-1.5">{wfName(s.workflow_id)}</td>
                <td>{s.interval_seconds}s</td>
                <td>
                  <button
                    onClick={() => toggle(s.id)}
                    className={`badge transition-colors ${
                      s.enabled
                        ? "bg-emerald-500/15 text-emerald-300 hover:bg-emerald-500/25"
                        : "bg-neutral-700 text-neutral-300 hover:bg-neutral-600"
                    }`}
                  >
                    <span className={`h-1.5 w-1.5 rounded-full ${s.enabled ? "bg-emerald-400" : "bg-neutral-400"}`} />
                    {s.enabled ? "running" : "paused"}
                  </button>
                </td>
                <td className="text-neutral-400">
                  {s.last_run_at ? new Date(s.last_run_at).toLocaleTimeString() : "—"}
                </td>
                <td className={s.last_status?.startsWith("error") ? "text-red-400" : "text-neutral-300"}>
                  {s.last_status ?? "—"}
                </td>
                <td>
                  <button onClick={() => remove(s.id)} className="font-medium text-red-400 hover:text-red-300 hover:underline">
                    刪除
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="text-xs text-neutral-500">
          尚無排程。先在上方建立器 Save 一個工作流,再於此排程自動執行。
        </p>
      )}
    </section>
  );
}
