"use client";

import { useState } from "react";
import { api, MARKETS } from "@/lib/api";

const SAMPLE = `timestamp,open,high,low,close,volume
2024-01-01,100,105,99,104,1000
2024-01-02,104,110,103,109,1200`;

export function DataImportPanel() {
  const [market, setMarket] = useState("tw_stock");
  const [symbol, setSymbol] = useState("2330");
  const [csv, setCsv] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function importCsv() {
    setMsg(null);
    setError(null);
    try {
      const res = await api.importHistory(market, symbol, csv);
      setMsg(`已匯入 ${res.imported} 根 K 線到 ${res.market}:${res.symbol}。現在可在上方回測。`);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <section className="rounded-lg border border-border bg-surface-1 p-4">
      <h2 className="font-display mb-1 text-lg font-semibold">匯入歷史資料(台股 / 美股)</h2>
      <p className="mb-3 text-xs text-muted">
        台股/美股尚未串接真實券商(元大 / Firstrade)。可在此貼上 OHLCV CSV,即可離線回測與紙上交易。
      </p>
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <select
          value={market}
          onChange={(e) => setMarket(e.target.value)}
          className="rounded-md bg-surface-2 px-2 py-1 text-sm"
        >
          {MARKETS.map((m) => (
            <option key={m.value} value={m.value}>
              {m.label}
            </option>
          ))}
        </select>
        <input
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          className="rounded-md bg-surface-2 px-2 py-1 text-sm"
          placeholder="代號 (如 2330 / AAPL)"
        />
        <button onClick={importCsv} className="rounded-md bg-accent px-3 py-1 text-sm font-medium hover:bg-accent-dim">
          匯入
        </button>
        <button
          onClick={() => setCsv(SAMPLE)}
          className="rounded-md bg-surface-2 px-2 py-1 text-xs hover:bg-surface-3"
        >
          填入範例
        </button>
      </div>
      <textarea
        value={csv}
        onChange={(e) => setCsv(e.target.value)}
        rows={5}
        placeholder={"timestamp,open,high,low,close,volume\n2024-01-01,100,105,99,104,1000"}
        className="w-full rounded-lg border border-border bg-bg p-2 font-mono text-xs text-text"
      />
      {msg && <p className="mt-2 text-sm text-up">{msg}</p>}
      {error && <p className="mt-2 text-sm text-error">{error}</p>}
    </section>
  );
}
