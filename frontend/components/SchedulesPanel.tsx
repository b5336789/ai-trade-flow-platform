"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import { L } from "@/lib/labels";

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
      setError(L.schedules.selectWorkflow);
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
    <section className="rounded-lg border border-border bg-surface-1 p-4">
      <h2 className="font-display mb-3 text-lg font-semibold">{L.schedules.title}</h2>

      <div className="mb-3 flex flex-wrap items-end gap-2">
        <label className="text-xs text-muted">
          {L.schedules.workflow}
          <select
            value={workflowId}
            onChange={(e) => setWorkflowId(e.target.value === "" ? "" : Number(e.target.value))}
            className="ml-1 rounded-md bg-surface-2 px-2 py-1 text-sm"
          >
            <option value="">{L.schedules.selectPlaceholder}</option>
            {workflows.data?.map((w) => (
              <option key={w.id} value={w.id}>
                #{w.id} {w.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs text-muted">
          {L.schedules.everySeconds}
          <input
            type="number"
            min={5}
            value={interval}
            onChange={(e) => setInterval(Number(e.target.value))}
            className="ml-1 w-20 rounded-md bg-surface-2 px-1 py-1 text-sm"
          />
        </label>
        <button
          onClick={schedule}
          className="rounded-md bg-accent px-3 py-1 text-sm font-medium text-bg hover:brightness-110"
        >
          {L.schedules.schedule}
        </button>
      </div>

      {error && <p className="mb-2 text-sm text-error">{error}</p>}

      {schedules.data && schedules.data.length > 0 ? (
        <table className="w-full text-left text-xs">
          <thead className="text-faint">
            <tr>
              <th className="py-1">{L.schedules.workflow}</th>
              <th>{L.schedules.colInterval}</th>
              <th>{L.schedules.colState}</th>
              <th>{L.schedules.colLastRun}</th>
              <th>{L.schedules.colLastStatus}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {schedules.data.map((s) => (
              <tr key={s.id} className="border-t border-border">
                <td className="py-1">{wfName(s.workflow_id)}</td>
                <td className="num">{s.interval_seconds}s</td>
                <td>
                  <button
                    onClick={() => toggle(s.id)}
                    className={`rounded-sm px-2 py-0.5 text-xs font-medium ${
                      s.enabled ? "bg-up/15 text-up" : "bg-surface-3 text-muted"
                    }`}
                  >
                    {s.enabled ? L.schedules.running : L.schedules.paused}
                  </button>
                </td>
                <td className="text-muted">
                  {s.last_run_at ? new Date(s.last_run_at).toLocaleTimeString() : "—"}
                </td>
                <td className={s.last_status?.startsWith("error") ? "text-error" : "text-text"}>
                  {s.last_status ?? "—"}
                </td>
                <td>
                  <button onClick={() => remove(s.id)} className="text-error hover:underline">
                    {L.schedules.delete}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="text-xs text-faint">{L.schedules.empty}</p>
      )}
    </section>
  );
}
