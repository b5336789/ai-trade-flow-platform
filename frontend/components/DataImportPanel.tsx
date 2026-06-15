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
    <section className="rounded-lg border border-neutral-800 bg-neutral-900/40 p-4">
      <h2 className="mb-1 text-lg font-semibold">匯入歷史資料(台股 / 美股)</h2>
      <p className="mb-3 text-xs text-neutral-400">
        台股/美股尚未串接真實券商(元大 / Firstrade)。可在此貼上 OHLCV CSV,即可離線回測與紙上交易。
      </p>
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <select
          value={market}
          onChange={(e) => setMarket(e.target.value)}
          className="rounded bg-neutral-800 px-2 py-1 text-sm"
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
          className="rounded bg-neutral-800 px-2 py-1 text-sm"
          placeholder="代號 (如 2330 / AAPL)"
        />
        <button onClick={importCsv} className="rounded bg-blue-600 px-3 py-1 text-sm font-medium hover:bg-blue-500">
          匯入
        </button>
        <button
          onClick={() => setCsv(SAMPLE)}
          className="rounded bg-neutral-800 px-2 py-1 text-xs hover:bg-neutral-700"
        >
          填入範例
        </button>
      </div>
      <textarea
        value={csv}
        onChange={(e) => setCsv(e.target.value)}
        rows={5}
        placeholder={"timestamp,open,high,low,close,volume\n2024-01-01,100,105,99,104,1000"}
        className="w-full rounded border border-neutral-800 bg-neutral-950 p-2 font-mono text-xs text-neutral-200"
      />
      {msg && <p className="mt-2 text-sm text-green-400">{msg}</p>}
      {error && <p className="mt-2 text-sm text-red-400">{error}</p>}
    </section>
  );
}
