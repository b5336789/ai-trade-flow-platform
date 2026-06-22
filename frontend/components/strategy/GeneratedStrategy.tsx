"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { api, type DesignResponse, type SpecParamDef, type StrategySpec } from "@/lib/api";
import { L } from "@/lib/labels";

interface GeneratedStrategyProps {
  design: DesignResponse | null;
  onSpecChange: (spec: StrategySpec) => void;
  onSaved: () => void;
}

export function GeneratedStrategy({ design, onSpecChange, onSaved }: GeneratedStrategyProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const save = useMutation({
    mutationFn: () => {
      if (!design) throw new Error("尚未生成策略");
      return api.saveStrategy(name.trim(), design.spec, description.trim());
    },
    onSuccess: () => {
      setName("");
      setDescription("");
      onSaved();
    },
  });

  if (!design) {
    return (
      <section className="flex h-full min-h-[520px] items-center justify-center rounded-lg border border-dashed border-border bg-surface-1 p-6 text-center text-[13px] text-faint">
        生成的策略會顯示在這裡 — Python 程式碼與可調參數。
      </section>
    );
  }

  function updateParamDefault(target: SpecParamDef, value: number) {
    if (!design) return;
    const params = design.spec.params.map((p) =>
      p.name === target.name ? { ...p, default: value } : p,
    );
    onSpecChange({ ...design.spec, params });
  }

  return (
    <section className="flex h-full min-h-[520px] flex-col rounded-lg border border-border bg-surface-1">
      <header className="flex items-center gap-2 border-b border-border px-4 py-3">
        <span className="h-1.5 w-1.5 rounded-sm bg-accent" />
        <h2 className="font-display text-[15px] font-semibold">生成的策略</h2>
        <span className="rounded-sm bg-surface-3 px-1.5 py-0.5 text-[11px] text-muted">
          declarative spec · 不執行任意程式
        </span>
      </header>

      <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
        <div>
          <h3 className="mb-1.5 text-[11px] uppercase tracking-wide text-faint">Python (預覽)</h3>
          <pre className="max-h-64 overflow-auto rounded-md border border-border bg-bg p-3 font-code text-[12px] leading-relaxed text-text">
            {design.rendered_python}
          </pre>
        </div>

        {design.spec.params.length > 0 && (
          <div>
            <h3 className="mb-1.5 text-[11px] uppercase tracking-wide text-faint">可調參數</h3>
            <table className="w-full text-left text-[13px]">
              <thead className="text-faint">
                <tr>
                  <th className="py-1 font-normal">名稱</th>
                  <th className="font-normal">型別</th>
                  <th className="font-normal">範圍</th>
                  <th className="font-normal">預設值</th>
                </tr>
              </thead>
              <tbody>
                {design.spec.params.map((p) => (
                  <tr key={p.name} className="border-t border-border">
                    <td className="py-1.5 font-code text-accent">{p.name}</td>
                    <td className="text-muted">{p.type}</td>
                    <td className="num text-muted">
                      {p.min ?? "−∞"} … {p.max ?? "∞"}
                    </td>
                    <td>
                      <input
                        type="number"
                        value={p.default}
                        min={p.min ?? undefined}
                        max={p.max ?? undefined}
                        step={p.step ?? (p.type === "int" ? 1 : "any")}
                        onChange={(e) => updateParamDefault(p, Number(e.target.value))}
                        className="num w-24 rounded-sm border border-border bg-surface-2 px-2 py-1 outline-none focus:border-accent"
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="space-y-2 border-t border-border p-3">
        <div className="flex gap-2">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="策略名稱"
            className="flex-1 rounded-md border border-border bg-surface-2 px-3 py-2 text-[13px] outline-none focus:border-accent"
          />
          <button
            onClick={() => save.mutate()}
            disabled={!name.trim() || save.isPending}
            className="rounded-md bg-accent px-4 py-2 text-[13px] font-semibold text-bg disabled:opacity-40"
          >
            {save.isPending ? "儲存中…" : "存入策略庫"}
          </button>
          <button
            type="button"
            disabled
            title={L.linking.sendToBacktestHint}
            className="rounded-md border border-border bg-surface-2 px-4 py-2 text-[13px] text-faint opacity-50"
          >
            {L.linking.sendToBacktest} →
          </button>
        </div>
        <input
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="描述(選填)"
          className="w-full rounded-md border border-border bg-surface-2 px-3 py-1.5 text-[12px] text-muted outline-none focus:border-accent"
        />
        {save.isError && (
          <p className="text-[12px] text-error">⚠ {(save.error as Error).message}</p>
        )}
        {save.isSuccess && <p className="text-[12px] text-up">✓ 已存入策略庫 · 到下方策略庫點「拿去回測」</p>}
      </div>
    </section>
  );
}
