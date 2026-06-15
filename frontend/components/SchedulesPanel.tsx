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
    <section className="rounded-lg border border-neutral-800 bg-neutral-900/40 p-4">
      <h2 className="mb-3 text-lg font-semibold">Schedules (auto-run)</h2>

      <div className="mb-3 flex flex-wrap items-end gap-2">
        <label className="text-xs text-neutral-400">
          workflow
          <select
            value={workflowId}
            onChange={(e) => setWorkflowId(e.target.value === "" ? "" : Number(e.target.value))}
            className="ml-1 rounded bg-neutral-800 px-2 py-1 text-sm"
          >
            <option value="">— select —</option>
            {workflows.data?.map((w) => (
              <option key={w.id} value={w.id}>
                #{w.id} {w.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs text-neutral-400">
          every (s)
          <input
            type="number"
            min={5}
            value={interval}
            onChange={(e) => setInterval(Number(e.target.value))}
            className="ml-1 w-20 rounded bg-neutral-800 px-1 py-1 text-sm"
          />
        </label>
        <button
          onClick={schedule}
          className="rounded bg-green-600 px-3 py-1 text-sm font-medium hover:bg-green-500"
        >
          Schedule
        </button>
      </div>

      {error && <p className="mb-2 text-sm text-red-400">{error}</p>}

      {schedules.data && schedules.data.length > 0 ? (
        <table className="w-full text-left text-xs">
          <thead className="text-neutral-500">
            <tr>
              <th className="py-1">Workflow</th>
              <th>Interval</th>
              <th>State</th>
              <th>Last run</th>
              <th>Last status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {schedules.data.map((s) => (
              <tr key={s.id} className="border-t border-neutral-800">
                <td className="py-1">{wfName(s.workflow_id)}</td>
                <td>{s.interval_seconds}s</td>
                <td>
                  <button
                    onClick={() => toggle(s.id)}
                    className={`rounded px-2 py-0.5 ${s.enabled ? "bg-green-700" : "bg-neutral-700"}`}
                  >
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
                  <button onClick={() => remove(s.id)} className="text-red-400 hover:underline">
                    delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="text-xs text-neutral-500">
          No schedules yet. Save a workflow in the builder, then schedule it here.
        </p>
      )}
    </section>
  );
}
