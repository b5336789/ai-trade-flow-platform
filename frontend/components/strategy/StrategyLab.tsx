"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, type DesignResponse, type StrategySpec } from "@/lib/api";
import { DesignChat } from "./DesignChat";
import { GeneratedStrategy } from "./GeneratedStrategy";
import { StrategyLibrary } from "./StrategyLibrary";

export function StrategyLab() {
  const qc = useQueryClient();
  const [design, setDesign] = useState<DesignResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  function handleSpecChange(spec: StrategySpec) {
    setDesign((prev) => (prev ? { ...prev, spec } : prev));
  }

  async function handleLoad(id: number) {
    setLoadError(null);
    try {
      const saved = await api.getSavedStrategy(id);
      setDesign({
        spec: saved.spec,
        rendered_python: saved.rendered_python,
        explanation: `已從策略庫載入「${saved.name}」。可繼續用 AI 調整或修改參數後另存。`,
      });
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : "載入失敗");
    }
  }

  return (
    <div className="space-y-4">
      <header>
        <h1 className="font-display text-xl font-bold">策略室 · Strategy Lab</h1>
        <p className="mt-1 text-[13px] text-muted">
          用白話與 AI 設計交易策略 → 生成可回測的宣告式策略 → 存入策略庫,於交易室組成工作流。
        </p>
      </header>

      {loadError && (
        <p className="rounded-md border border-error/40 bg-error/10 px-3 py-2 text-[13px] text-error">
          ⚠ {loadError}
        </p>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1.1fr_1.2fr]">
        <DesignChat priorSpec={design?.spec ?? null} onDesigned={setDesign} />
        <GeneratedStrategy
          design={design}
          onSpecChange={handleSpecChange}
          onSaved={() => qc.invalidateQueries({ queryKey: ["savedStrategies"] })}
        />
      </div>

      <StrategyLibrary onLoad={handleLoad} />
    </div>
  );
}
