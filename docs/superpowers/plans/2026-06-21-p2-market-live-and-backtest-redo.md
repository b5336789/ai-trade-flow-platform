# P2 市場即時看盤 + 回測頁重做 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把市場頁升級為即時看盤(live `PriceChart` + ticker 列 + AI 訊號疊圖 + 台股離線誠實標示),並重做回測頁(操作引導兩段式、K 線疊買賣點、指標分級+解讀、結果統一分頁),全部消費 P1 已交付的 `PriceChart`/`chart-helpers`/`labels`/`Term` 介面。

**Architecture:** 純前端,建立在 P1 的 `PriceChart`(靜態+live)與語言層之上。市場頁改吃 live `PriceChart` 並用既有 OHLCV 推導 24h 統計、用新 `api.ticker` 取現價;回測頁把四個平鋪按鈕重組為主按鈕+折疊進階分析,概覽分頁加靜態 K 線疊 `tradesToMarkers(result.trades)`(回測前/後另抓同條件 candles,spec 方案 A,後端 payload 不變),指標分主次卡 + `<Term>` 解讀,並把四種分析結果收進單一分頁容器只顯示跑過的頁。

**Tech Stack:** Next 14 App Router · React 18 · TypeScript · lightweight-charts 4.2.3 · @tanstack/react-query 5

## Global Constraints

- **設計系統權威 = `DESIGN.md`**;漲跌色只透過 `--up` / `--down` CSS token,絕不硬編綠漲;`data-market="tw"` 翻轉(用 `setMarket`);cyan(`--accent`)僅限 AI;數字一律 `tabular-nums`(`.num`);圓角用 `--r-*`。沿用既有 Tailwind token 類名(`bg-surface-1/2/3`、`border-border`/`border-border-strong`、`text-up`/`text-down`/`text-muted`/`text-faint`/`text-warning`/`text-error`、`bg-accent`/`text-accent`/`bg-accent-dim`)。
- **lightweight-charts v4 API**(非 v5):`chart.addCandlestickSeries()` / `addHistogramSeries()` / `addLineSeries()` / `series.update()` / `series.setMarkers()` / `chart.subscribeCrosshairMove()`。比照現有 `components/PriceChart.tsx`(P1 已建)。
- **前端無單元測試 runner(刻意)**:CLAUDE.md 載明 CI 只跑 `npm run build`。本計畫每個任務的驗收循環 = `npx tsc --noEmit`(型別)→ `npm run build`(建置)→(行為型任務)`run-app` skill 視覺驗證。**不寫空殼單元測試湊覆蓋率**;純邏輯放 `lib/chart-helpers.ts`(P1)以利未來導入 runner。
- **Fail loud**:資料錯誤/空資料/後端 detail 顯式呈現(沿用既有 `(e as Error).message`、`candles.error`),不靜默吞掉。
- **Surgical**:只動本計畫列出的檔;不順手重構鄰近碼。中英混雜 UI 動詞改引 `L.*`(P1 `lib/labels.ts`),但不改與本任務無關的字串。
- 所有指令前綴 `cd frontend`(前端 root = `/Users/b5336789/Documents/workspace/ai-trade-flow-platform/frontend`)。

---

## File Structure

- **Modify** `frontend/lib/api.ts` — 新增 `Ticker` 型別 + `api.ticker(symbol, market)`;`L.market`/`L.backtest`/`L.metrics` 補欄位(在 `lib/labels.ts`)。
- **Modify** `frontend/lib/labels.ts` — 補本計畫用到、P1 尚未涵蓋的文案鍵(市場頁、進階分析說明、分頁名)。
- **Create** `frontend/lib/market-stats.ts` — 純函式:從 `Candle[]` 推導 24h 漲跌/高低/量(誠實:後端 Ticker 只給現價)。
- **Modify** `frontend/components/MarketPanel.tsx` — Area B:live `PriceChart`、ticker 列、商品選擇器(datalist)、AI 訊號 marker、台股離線徽章、URL query 持久化。
- **Modify** `frontend/components/BacktestPanel.tsx` — Area C1/C3/C4/C5:操作引導、概覽 K 線疊買賣點、指標分級、統一結果分頁。
- **Create** `frontend/components/MetricCard.tsx` — 回測主指標大卡(含健康度色標 + `<Term>` 標題)。

---

### Task 1: `api.ticker` + `Ticker` 型別

**Files:**
- Modify: `frontend/lib/api.ts` (新增型別於 `EquityPoint`(L125)附近;新增方法於 `api.ohlcv`(L378-381)之後)

**Interfaces:**
- Produces: `export interface Ticker { symbol: string; price: number; timestamp: string }`;`api.ticker(symbol: string, market?: string): Promise<Ticker>`。
- Consumes: 既有後端 `GET /api/markets/ticker?symbol=&market=`(回 `{symbol, price, timestamp}`,501/502 fail loud)。

- [ ] **Step 1: 新增 `Ticker` 型別** — 在 `lib/api.ts` 的 `export interface Candle { … }`(L9-16)之後插入:

```ts
export interface Ticker {
  symbol: string;
  price: number;
  timestamp: string;
}
```

- [ ] **Step 2: 新增 `api.ticker` 方法** — 在 `api` 物件內 `ohlcv` 方法(L378-381)之後、`aiSignal` 之前插入:

```ts
  ticker: (symbol: string, market = "crypto") =>
    request<Ticker>(
      `/api/markets/ticker?symbol=${encodeURIComponent(symbol)}&market=${market}`,
    ),
```

- [ ] **Step 3: 型別檢查** — Run: `cd frontend && npx tsc --noEmit` — Expected: 無錯誤。

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/api.ts
git commit -m "feat(frontend): add api.ticker + Ticker type (consume existing /api/markets/ticker)"
```

---

### Task 2: 補語言層文案鍵

**Files:**
- Modify: `frontend/lib/labels.ts` (`L.market` 物件、`L.backtest` 物件)

**Interfaces:**
- Produces: 本計畫用到的新文案鍵(若 P1 已存在則略過,只補缺的)。
- Consumes: 無。

- [ ] **Step 1: 補 `L.market` 缺鍵** — 確認 `L.market` 含下列鍵,缺者補上(P1 已有 `title`/`symbol`/`timeframe`/`live`/`paused`/`offlineCsv`)。在 `L.market` 物件補:

```ts
    pause: "暫停",
    resume: "恢復",
    aiSignal: "AI 訊號",
    askingAi: "AI 分析中…",
    change24h: "24h 漲跌",
    high24h: "24h 高",
    low24h: "24h 低",
    chartError: "線圖錯誤",
    loadingCandles: "載入 K 線中…",
```

- [ ] **Step 2: 補 `L.backtest` 缺鍵** — 在 `L.backtest` 物件補(P1 已有 `title`/`run`/`compare`/`optimize`/`walkforward`/`overview`/`trades`/`excess`/`noTrades`):

```ts
    compareDesc: "同條件跑四個內建策略並排名,看哪個最適合此商品。",
    optimizeDesc: "掃描參數網格找最佳組合;以樣本外指標排名,避免挑到過擬合的參數。",
    walkforwardDesc: "Walk-forward k 折:用過去選參數、在沒看過的未來驗證,檢查穩健度。",
    advancedOnlyBuiltin: "最佳化 / 樣本外驗證僅支援內建策略;策略庫策略請改用「執行回測」或「比較全部策略」。",
    moreMetrics: "更多指標",
    tabCompare: "比較",
    tabOptimize: "最佳化",
    tabWalkforward: "樣本外",
    applied: "已套用參數,重新「執行回測」以查看結果。",
    vsBuyHold: "vs 大盤(Buy & Hold)",
    barsSuffix: "根",
```

- [ ] **Step 3: 型別檢查** — Run: `cd frontend && npx tsc --noEmit` — Expected: 無錯誤。

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/labels.ts
git commit -m "feat(frontend): extend labels for market live view + backtest redo"
```

---

### Task 3: `market-stats.ts` 24h 統計純函式

**Files:**
- Create: `frontend/lib/market-stats.ts`

**Interfaces:**
- Consumes: `Candle` from `@/lib/api`。
- Produces: `interface MarketStats { last: number; first: number; changeAbs: number; changePct: number; high: number; low: number; volume: number } | null`;`deriveStats(candles: Candle[], window: number): MarketStats | null`。
- 誠實註記:後端 `Ticker` 只給現價,24h 漲跌/高低由已抓到的 OHLCV 推導(不偽造後端欄位)。

- [ ] **Step 1: 建立純函式**

```ts
// frontend/lib/market-stats.ts
// 從已抓到的 OHLCV 推導「24h 漲跌/高低/量」。後端 Ticker 只回現價,
// 為了不偽造不存在的後端欄位,這裡誠實地用最後 N 根 K 線估算(window 對應約 24h 的根數)。
import type { Candle } from "./api";

export interface MarketStats {
  last: number;
  first: number;
  changeAbs: number;
  changePct: number;
  high: number;
  low: number;
  volume: number;
}

// window = 對應約 24h 的根數(由 timeframe 推算,呼叫端傳入);取最後 window 根。
export function deriveStats(candles: Candle[], window: number): MarketStats | null {
  if (!candles.length) return null;
  const slice = candles.slice(-Math.max(1, window));
  const first = slice[0].open;
  const last = slice[slice.length - 1].close;
  const high = Math.max(...slice.map((c) => c.high));
  const low = Math.min(...slice.map((c) => c.low));
  const volume = slice.reduce((s, c) => s + c.volume, 0);
  const changeAbs = last - first;
  const changePct = first !== 0 ? (changeAbs / first) * 100 : 0;
  return { last, first, changeAbs, changePct, high, low, volume };
}

// 由 timeframe 估算「約 24h 需要幾根」。未知週期退回整段。
export function barsPer24h(timeframe: string): number {
  const map: Record<string, number> = {
    "1m": 1440, "5m": 288, "15m": 96, "30m": 48,
    "1h": 24, "4h": 6, "1d": 1,
  };
  return map[timeframe] ?? 24;
}
```

- [ ] **Step 2: 型別檢查** — Run: `cd frontend && npx tsc --noEmit` — Expected: 無錯誤。

- [ ] **Step 3: 邏輯自驗(無 runner 暫行檢查)**

```bash
cd frontend && node --input-type=module -e "
function deriveStats(candles, window){ if(!candles.length) return null; const slice=candles.slice(-Math.max(1,window)); const first=slice[0].open; const last=slice[slice.length-1].close; const high=Math.max(...slice.map(c=>c.high)); const low=Math.min(...slice.map(c=>c.low)); const volume=slice.reduce((s,c)=>s+c.volume,0); const changeAbs=last-first; const changePct=first!==0?(changeAbs/first)*100:0; return {last,first,changeAbs,changePct,high,low,volume}; }
const cs=[{open:100,high:110,low:95,close:105,volume:1},{open:105,high:120,low:100,close:118,volume:2}];
const s=deriveStats(cs,2);
if(s.first!==100||s.last!==118) throw new Error('first/last wrong');
if(s.high!==120||s.low!==95) throw new Error('high/low wrong');
if(Math.abs(s.changePct-18)>1e-9) throw new Error('changePct wrong');
if(s.volume!==3) throw new Error('volume wrong');
console.log('market-stats logic OK');
"
```
Expected: 印出 `market-stats logic OK`。

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/market-stats.ts
git commit -m "feat(frontend): add market-stats (derive 24h stats from OHLCV honestly)"
```

---

### Task 4: 市場頁 — live PriceChart + ticker 列(Area B 核心)

**Files:**
- Modify: `frontend/components/MarketPanel.tsx`(整檔重寫;沿用既有 state/askAi 結構)

**Interfaces:**
- Consumes: `PriceChart` from `@/components/PriceChart`;`tradesToMarkers`? 不用;`type ChartMarker, OHLCV` from `@/lib/chart-helpers`;`api.ohlcv`/`api.ticker`/`api.aiSignal`;`deriveStats`/`barsPer24h` from `@/lib/market-stats`;`L` from `@/lib/labels`;`Term` 不必;`setMarket` from `@/lib/useMarket`。
- Produces: 即時看盤面板。本任務交付 live 圖 + ticker 列 + 市場/週期選擇 + 商品 datalist;AI marker 與 URL query 在 Task 5/6 接。

- [ ] **Step 1: 重寫 import 區與常數** — 把 `MarketPanel.tsx` 頂部(L1-13)替換為:

```tsx
"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, type Signal } from "@/lib/api";
import { setMarket } from "@/lib/useMarket";
import { PriceChart } from "@/components/PriceChart";
import { deriveStats, barsPer24h } from "@/lib/market-stats";
import { L } from "@/lib/labels";

const SIGNAL_COLORS: Record<string, string> = {
  buy: "text-up",
  sell: "text-down",
  hold: "text-warning",
};

// 內建常用標的;保留自由輸入(datalist)。
const COMMON_SYMBOLS: Record<string, string[]> = {
  crypto: ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "DOGE/USDT"],
  tw_stock: ["2330", "2317", "2454", "0050"],
  us_stock: ["AAPL", "MSFT", "NVDA", "TSLA", "SPY"],
};
const TIMEFRAMES = ["15m", "1h", "4h", "1d"];

const fmt = (n: number) => n.toLocaleString(undefined, { maximumFractionDigits: 4 });
const signed = (n: number) => `${n >= 0 ? "+" : ""}${n.toFixed(2)}`;
```

- [ ] **Step 2: 重寫元件主體(state + queries)** — 把 `export function MarketPanel() { … }` 開頭到 `async function askAi()` 之前(L15-29)替換為:

```tsx
export function MarketPanel() {
  const [symbol, setSymbol] = useState("BTC/USDT");
  const [timeframe, setTimeframe] = useState("1h");
  const [market, setMarketState] = useState("crypto");
  const [paused, setPaused] = useState(false);
  const [aiSignal, setAiSignal] = useState<Signal | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);
  const [aiLoading, setAiLoading] = useState(false);

  useEffect(() => { setMarket(market); }, [market]);

  const isCrypto = market === "crypto";

  // 歷史 K 線(給圖初始資料 + 推導 24h 統計)。
  const candles = useQuery({
    queryKey: ["ohlcv", symbol, timeframe, market],
    queryFn: () => api.ohlcv(symbol, timeframe, 200, market),
    retry: false,
  });

  // 現價(crypto 即時輪詢;台股/美股為離線 CSV,不偽裝即時)。
  const ticker = useQuery({
    queryKey: ["ticker", symbol, market],
    queryFn: () => api.ticker(symbol, market),
    retry: false,
    enabled: isCrypto && !paused,
    refetchInterval: isCrypto && !paused ? 3000 : false,
    refetchIntervalInBackground: false,
  });

  const stats = candles.data ? deriveStats(candles.data, barsPer24h(timeframe)) : null;
  const live = isCrypto && !paused ? { symbol, timeframe, market, intervalMs: 3000 } : null;
```

- [ ] **Step 3: 保留 askAi(微調文案)** — 把既有 `askAi`(L31-42)中 `120` 改用 `200` 以對齊抓的根數,其餘不變(此步只調數字參數,保留 try/catch fail-loud):

```tsx
  async function askAi() {
    setAiLoading(true);
    setAiError(null);
    setAiSignal(null);
    try {
      setAiSignal(await api.aiSignal(symbol, market, timeframe, 200));
    } catch (e) {
      setAiError((e as Error).message);
    } finally {
      setAiLoading(false);
    }
  }
```

- [ ] **Step 4: 重寫 JSX(控制列 + ticker 列 + 圖)** — 把 `return ( … );`(L44-105)整段替換為:

```tsx
  return (
    <section className="rounded-lg border border-border bg-surface-1 p-4">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <h2 className="font-display mr-2 text-lg font-semibold">{L.market.title}</h2>
        <input
          list="market-symbols"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value.toUpperCase())}
          className="rounded-md bg-surface-2 px-2 py-1 text-sm"
          placeholder={L.market.symbol}
        />
        <datalist id="market-symbols">
          {(COMMON_SYMBOLS[market] ?? []).map((s) => (
            <option key={s} value={s} />
          ))}
        </datalist>
        <select
          value={market}
          onChange={(e) => setMarketState(e.target.value)}
          className="rounded-md bg-surface-2 px-2 py-1 text-sm"
        >
          <option value="crypto">Crypto</option>
          <option value="tw_stock">台股</option>
          <option value="us_stock">美股</option>
        </select>
        <select
          value={timeframe}
          onChange={(e) => setTimeframe(e.target.value)}
          className="rounded-md bg-surface-2 px-2 py-1 text-sm"
        >
          {TIMEFRAMES.map((tf) => (
            <option key={tf} value={tf}>{tf}</option>
          ))}
        </select>
        {isCrypto && (
          <button
            onClick={() => setPaused((p) => !p)}
            className="rounded-md border border-border-strong bg-surface-2 px-3 py-1 text-sm text-text hover:bg-surface-3"
          >
            {paused ? L.market.resume : L.market.pause}
          </button>
        )}
        <button
          onClick={askAi}
          disabled={aiLoading}
          className="rounded-md bg-accent px-3 py-1 text-sm font-medium text-bg hover:brightness-110 disabled:opacity-50"
        >
          {aiLoading ? L.market.askingAi : L.market.aiSignal}
        </button>
        {!isCrypto && (
          <span className="rounded-sm bg-surface-3 px-2 py-1 text-xs text-muted">
            {L.market.offlineCsv}
          </span>
        )}
      </div>

      {stats && (
        <div className="mb-3 flex flex-wrap items-baseline gap-x-5 gap-y-1 text-sm">
          <span className="num text-xl font-semibold text-text">
            {fmt(ticker.data?.price ?? stats.last)}
          </span>
          <span className={`num ${stats.changeAbs >= 0 ? "text-up" : "text-down"}`}>
            {L.market.change24h} {signed(stats.changeAbs)} ({signed(stats.changePct)}%)
          </span>
          <span className="num text-muted">{L.market.high24h} {fmt(stats.high)}</span>
          <span className="num text-muted">{L.market.low24h} {fmt(stats.low)}</span>
        </div>
      )}

      {candles.isError && (
        <p className="mb-2 text-sm text-error">{L.market.chartError}: {(candles.error as Error).message}</p>
      )}
      {candles.data && candles.data.length > 0 ? (
        <PriceChart candles={candles.data} live={live} height={360} />
      ) : (
        !candles.isError && <p className="text-sm text-faint">{L.market.loadingCandles}</p>
      )}

      {aiError && <p className="mt-3 text-sm text-error">AI error: {aiError}</p>}
      {aiSignal && (
        <div className="mt-3 rounded-lg border border-border bg-surface-2 p-3 text-sm">
          <span className={`font-bold uppercase ${SIGNAL_COLORS[aiSignal.action]}`}>
            {aiSignal.action}
          </span>{" "}
          <span className="text-muted">
            (confidence <span className="num">{(aiSignal.confidence * 100).toFixed(0)}</span>% · {aiSignal.source})
          </span>
          <p className="mt-1 text-text">{aiSignal.reason}</p>
        </div>
      )}
    </section>
  );
}
```

- [ ] **Step 5: 型別檢查 + 建置** — Run: `cd frontend && npx tsc --noEmit && npm run build` — Expected: tsc 無錯;build 成功。

- [ ] **Step 6: 視覺驗證** — `run-app` 啟動 → 開市場頁 → 確認:現價/24h 漲跌/高低列出現且數字 mono;crypto 時圖右上現價徽章每約 3s 更新且整圖不重繪;按「暫停」停止輪詢、「恢復」續抓;切台股顯示「離線資料(CSV)」徽章、無暫停鈕、`<html data-market="tw">`(漲跌色翻轉)。Expected: 即時更新且台股誠實標示。

- [ ] **Step 7: Commit**

```bash
git add frontend/components/MarketPanel.tsx
git commit -m "feat(frontend): market live PriceChart + ticker row + symbol datalist + tw offline badge + pause"
```

---

### Task 5: 市場頁 — AI 訊號 marker 疊圖

**Files:**
- Modify: `frontend/components/MarketPanel.tsx`(`import` 區、`live` 計算後、`<PriceChart>` 呼叫)

**Interfaces:**
- Consumes: `type ChartMarker` from `@/lib/chart-helpers`;`candles.data`。
- Produces: AI 訊號以 marker 疊在最後一根 K 上(buy ▲ / sell ▼ / hold 不疊),附 confidence text。

- [ ] **Step 1: 補 import** — 在 `MarketPanel.tsx` import 區 `import { L } from "@/lib/labels";` 之後加:

```tsx
import type { ChartMarker } from "@/lib/chart-helpers";
```

- [ ] **Step 2: 計算 aiMarkers** — 在元件主體 `const live = …;`(Task 4 Step 2 結尾)之後插入:

```tsx
  // AI 訊號疊在最後一根 K(hold 不疊);text 帶信心度。
  const aiMarkers: ChartMarker[] = (() => {
    if (!aiSignal || aiSignal.action === "hold" || !candles.data?.length) return [];
    const lastIso = candles.data[candles.data.length - 1].timestamp;
    const time = Math.floor(new Date(lastIso).getTime() / 1000);
    const isBuy = aiSignal.action === "buy";
    return [{
      time,
      position: isBuy ? "belowBar" : "aboveBar",
      kind: isBuy ? "buy" : "sell",
      text: `AI ${aiSignal.action} ${(aiSignal.confidence * 100).toFixed(0)}%`,
    }];
  })();
```

- [ ] **Step 3: 傳 markers 給圖** — 把 Task 4 Step 4 的 `<PriceChart candles={candles.data} live={live} height={360} />` 改為:

```tsx
        <PriceChart candles={candles.data} live={live} markers={aiMarkers} height={360} />
```

- [ ] **Step 4: 型別檢查 + 建置** — Run: `cd frontend && npx tsc --noEmit && npm run build` — Expected: pass。

- [ ] **Step 5: 視覺驗證** — `run-app` → 市場頁 → 按「AI 訊號」→ 回 buy/sell 時圖最後一根出現 ▲/▼ 與「AI buy NN%」標籤;hold 不疊 marker。Expected: marker 正確疊出。

- [ ] **Step 6: Commit**

```bash
git add frontend/components/MarketPanel.tsx
git commit -m "feat(frontend): overlay AI signal as chart marker on market live view"
```

---

### Task 6: 市場頁 — URL query 持久化 symbol/timeframe/market

**Files:**
- Modify: `frontend/components/MarketPanel.tsx`(import 區、state 初值、新增同步 effect)

**Interfaces:**
- Consumes: `useSearchParams`/`useRouter`/`usePathname` from `next/navigation`。
- Produces: `symbol`/`timeframe`/`market` 寫入 URL query,重整/分享保持;進頁從 query 還原。

- [ ] **Step 1: 補 import** — 在 `MarketPanel.tsx` import 區 `import { useEffect, useState } from "react";` 之後加:

```tsx
import { usePathname, useRouter, useSearchParams } from "next/navigation";
```

- [ ] **Step 2: 用 query 當初值** — 把 Task 4 Step 2 的三行 state 初值改為從 query 還原(放在 `export function MarketPanel() {` 之後第一行):

```tsx
  const router = useRouter();
  const pathname = usePathname();
  const sp = useSearchParams();
  const [symbol, setSymbol] = useState((sp.get("symbol") ?? "BTC/USDT").toUpperCase());
  const [timeframe, setTimeframe] = useState(sp.get("timeframe") ?? "1h");
  const [market, setMarketState] = useState(sp.get("market") ?? "crypto");
```

(刪掉 Task 4 Step 2 原本那三行 `useState("BTC/USDT")`/`useState("1h")`/`useState("crypto")`。)

- [ ] **Step 3: 同步回 URL** — 在 `useEffect(() => { setMarket(market); }, [market]);` 之後插入:

```tsx
  useEffect(() => {
    const q = new URLSearchParams({ symbol, timeframe, market });
    router.replace(`${pathname}?${q.toString()}`, { scroll: false });
  }, [symbol, timeframe, market, pathname, router]);
```

- [ ] **Step 4: 型別檢查 + 建置** — Run: `cd frontend && npx tsc --noEmit && npm run build` — Expected: pass。

- [ ] **Step 5: 視覺驗證** — `run-app` → 市場頁 → 改商品/週期/市場 → 網址列 query 同步更新 → 重整頁面後選擇保持。Expected: query 持久化生效。

- [ ] **Step 6: Commit**

```bash
git add frontend/components/MarketPanel.tsx
git commit -m "feat(frontend): persist market symbol/timeframe/market in URL query"
```

---

### Task 7: 回測頁 — 操作引導兩段式(Area C1)

**Files:**
- Modify: `frontend/components/BacktestPanel.tsx`(import 區 L1-15、新增 `advancedOpen` state、標題 L142、按鈕區 L219-249)

**Interfaces:**
- Consumes: `L` from `@/lib/labels`;`Term` from `@/components/Term`。
- Produces: 主按鈕「執行回測」(cyan,大)+ 折疊「進階分析」(內含比較/最佳化/樣本外,各帶一行說明 + `<Term>` + 禁用態可見灰字說明)。

- [ ] **Step 1: 補 import** — 在 `BacktestPanel.tsx` import 區末(`import { setMarket } from "@/lib/useMarket";` 之後)加:

```tsx
import { L } from "@/lib/labels";
import { Term } from "@/components/Term";
```

- [ ] **Step 2: 新增折疊 state** — 在 `const [walkforward, setWalkforward] = useState<WalkForwardReport | null>(null);`(L37)之後加:

```tsx
  const [advancedOpen, setAdvancedOpen] = useState(false);
```

- [ ] **Step 3: 中文化標題** — 把 `<h2 className="font-display mb-3 text-lg font-semibold">Backtest</h2>`(L142)改為:

```tsx
      <h2 className="font-display mb-3 text-lg font-semibold">{L.backtest.title}</h2>
```

- [ ] **Step 4: 重寫按鈕區** — 把四個按鈕(L219-248,即 `<button onClick={run}>…Run…</button>` 起到 `Walk-forward</button>` 止)整段替換為主按鈕 + 折疊進階區:

```tsx
        <button
          onClick={run}
          disabled={loading}
          className="rounded-md bg-accent px-4 py-1.5 text-sm font-semibold text-bg hover:brightness-110 disabled:opacity-50"
        >
          {loading ? L.common.loading : L.backtest.run}
        </button>
        <button
          type="button"
          onClick={() => setAdvancedOpen((o) => !o)}
          className="rounded-md border border-border-strong bg-surface-2 px-3 py-1.5 text-sm text-text hover:bg-surface-3"
        >
          {L.common.advanced} {advancedOpen ? "▴" : "▾"}
        </button>
      </div>

      {advancedOpen && (
        <div className="mb-3 space-y-2 rounded-md border border-border bg-surface-2 p-3">
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={compare}
              disabled={loading}
              className="rounded-md border border-border-strong bg-surface-1 px-3 py-1 text-sm text-text hover:bg-surface-3 disabled:opacity-50"
            >
              {L.backtest.compare}
            </button>
            <span className="text-xs text-muted">{L.backtest.compareDesc}</span>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={optimize}
              disabled={loading || isSaved}
              className="rounded-md border border-border-strong bg-surface-1 px-3 py-1 text-sm text-text hover:bg-surface-3 disabled:opacity-50"
            >
              <Term k="optimize">{L.backtest.optimize}</Term>
            </button>
            <span className="text-xs text-muted">{L.backtest.optimizeDesc}</span>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={runWalkForward}
              disabled={loading || isSaved}
              className="rounded-md border border-border-strong bg-surface-1 px-3 py-1 text-sm text-text hover:bg-surface-3 disabled:opacity-50"
            >
              <Term k="walk_forward">{L.backtest.walkforward}</Term>
            </button>
            <span className="text-xs text-muted">{L.backtest.walkforwardDesc}</span>
          </div>
          {isSaved && (
            <p className="text-xs text-warning">{L.backtest.advancedOnlyBuiltin}</p>
          )}
        </div>
      )}
```

(注意:此替換**移除**了原本緊接四按鈕後的 `</div>`(L249),因為新區塊已自帶 `</div>` 收掉控制列;確認控制列 `<div className="mb-3 flex flex-wrap items-end gap-2">` 仍正確閉合。)

- [ ] **Step 5: 型別檢查 + 建置** — Run: `cd frontend && npx tsc --noEmit && npm run build` — Expected: pass。

- [ ] **Step 6: 視覺驗證** — `run-app` → 回測頁 → 確認:主按鈕「執行回測」醒目(cyan、較大);「進階分析」預設收起,展開後三鈕各帶一行說明;最佳化/樣本外標題 hover 出 `?` 解讀;選策略庫策略時兩鈕灰掉且顯示灰字說明。Expected: 兩段式引導成立。

- [ ] **Step 7: Commit**

```bash
git add frontend/components/BacktestPanel.tsx
git commit -m "feat(frontend): backtest C1 — primary run button + collapsible advanced analysis with descriptions"
```

---

### Task 8: 回測頁 — 概覽 K 線疊買賣點(Area C3)

**Files:**
- Modify: `frontend/components/BacktestPanel.tsx`(import 區、新增 `overviewCandles` state、`run()` 內抓 candles、`tab==="overview"` 區塊 L269-294)

**Interfaces:**
- Consumes: `PriceChart`;`tradesToMarkers`、`type ChartMarker`、`type Overlay` from `@/lib/chart-helpers`;`api.ohlcv`;`STRATEGY_PARAMS`(已 import `@/lib/strategies`)。
- Produces: 概覽分頁在 `EquityChart` 之上加靜態 `PriceChart`,疊 `tradesToMarkers(result.trades)`;ma_cross 額外疊 fast/slow SMA overlays。方案 A:回測前另抓同 symbol/timeframe/limit 的 candles(後端 payload 不變)。

- [ ] **Step 1: 補 import** — 在 `BacktestPanel.tsx` import 區加(`Term` import 之後):

```tsx
import { PriceChart } from "@/components/PriceChart";
import { tradesToMarkers, type Overlay } from "@/lib/chart-helpers";
import type { Candle } from "@/lib/api";
```

- [ ] **Step 2: 新增 candles state** — 在 `const [advancedOpen, setAdvancedOpen] = useState(false);`(Task 7 Step 2)之後加:

```tsx
  const [overviewCandles, setOverviewCandles] = useState<Candle[]>([]);
```

- [ ] **Step 3: resetOutputs 也清 candles** — 在 `resetOutputs()`(L55-61)的 `setError(null);` 之後加一行:

```tsx
    setOverviewCandles([]);
```

- [ ] **Step 4: run() 抓 candles** — 在 `run()`(L87-102)的 `setResult(res);` 之前插入(方案 A:同條件另抓一次 K 線給圖用;失敗不阻斷回測,只是圖空):

```tsx
      try {
        setOverviewCandles(await api.ohlcv(symbol, timeframe, limit, market));
      } catch {
        setOverviewCandles([]);
      }
```

- [ ] **Step 5: 概覽插入 PriceChart** — 在 `tab === "overview"` 區塊(L269-295)裡,把 `<EquityChart points={result.equity_curve} />`(L293)**之前**插入 K 線圖區塊(指標卡保持不動,Task 9 再改);即在 `<div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted"> … </div>` 與 `<EquityChart …/>` 之間插入:

```tsx
              {overviewCandles.length > 0 && (
                <PriceChart
                  candles={overviewCandles}
                  markers={tradesToMarkers(result.trades)}
                  overlays={ovOverlays}
                  height={320}
                />
              )}
```

- [ ] **Step 6: 計算 ma_cross overlays** — 在 `run()` 等函式之後、`return (` 之前(約 L139),新增以 `params` 推導的 overlays(僅 ma_cross):

```tsx
  const ovOverlays: Overlay[] =
    strategy === "ma_cross"
      ? [
          { id: "fast", type: "sma", period: Number(params.fast ?? 10), color: "var(--accent)" },
          { id: "slow", type: "sma", period: Number(params.slow ?? 20), color: "var(--muted)" },
        ]
      : [];
```

(注意:`Overlay.color` 是字串;若 P1 `PriceChart` 對 overlay 顏色用 `cssVar` 解析,改傳實際 token 名 `"--accent"`/`"--muted"`。實作時對齊 P1 `PriceChart` overlays 的 color 解讀方式——P1 元件對 overlay `color` 傳入 `addLineSeries({ color })`,故應傳可直接吃的色值;若 P1 用 `ov.color ?? cssVar("--accent")`,則此處傳 `cssVar` 解析後的值或保留 token 由 P1 處理。**驗證 P1 實作後二選一**,預設傳 `"--accent"`/`"--muted"` 並在 Step 7 視覺確認線有畫出。)

- [ ] **Step 7: 型別檢查 + 建置 + 視覺驗證** — Run: `cd frontend && npx tsc --noEmit && npm run build`,再 `run-app` → 回測頁 → ma_cross 執行回測 → 概覽上方出現 K 線,每筆 trade 有 ▲ 進場/▼ 出場(賣出帶報酬%),並疊兩條均線;下方仍為淨值曲線。Expected: 買賣點與均線正確疊在 K 線。若均線未顯示,依 P1 overlay color 解讀調整 Step 6 的 color 值。

- [ ] **Step 8: Commit**

```bash
git add frontend/components/BacktestPanel.tsx
git commit -m "feat(frontend): backtest C3 — overview K-line with trade markers + ma_cross SMA overlays (plan A fetch)"
```

---

### Task 9: 回測頁 — 指標分級 + 解讀(Area C4)

**Files:**
- Create: `frontend/components/MetricCard.tsx`
- Modify: `frontend/components/BacktestPanel.tsx`(概覽指標區 L271-292、import、`Metric` 舊元件可保留給次指標)

**Interfaces:**
- Consumes: `Term`、`L`、`GLOSSARY`(經 `Term`)。
- Produces: `MetricCard`(放大主卡 + 健康度色標 + `<Term>` 標題);概覽 4 大主卡(總報酬含 Buy&Hold+超額、最大回撤、Sharpe、勝率)、次指標收進「更多指標」toggle、`num_trades===0` 顯眼提示。

- [ ] **Step 1: 建立 MetricCard** — Create `frontend/components/MetricCard.tsx`:

```tsx
// frontend/components/MetricCard.tsx
"use client";
import { Term } from "@/components/Term";

type Health = "up" | "down" | "neutral";

// 放大的主指標卡;標題用 <Term> 帶白話解讀,值依 health 上色。
export function MetricCard({
  termKey, label, value, sub, health = "neutral",
}: {
  termKey: string;
  label: string;
  value: string;
  sub?: React.ReactNode;
  health?: Health;
}) {
  const color = health === "up" ? "text-up" : health === "down" ? "text-down" : "text-text";
  return (
    <div className="rounded-md border border-border bg-surface-2 p-3">
      <div className="text-xs text-faint">
        <Term k={termKey}>{label}</Term>
      </div>
      <div className={`num text-xl font-semibold ${color}`}>{value}</div>
      {sub != null && <div className="mt-0.5 text-xs">{sub}</div>}
    </div>
  );
}
```

- [ ] **Step 2: 補 import + 次指標 toggle state** — 在 `BacktestPanel.tsx` import 區加 `import { MetricCard } from "@/components/MetricCard";`;在 state 區(Task 8 Step 2 附近)加:

```tsx
  const [moreMetrics, setMoreMetrics] = useState(false);
```

- [ ] **Step 3: 重寫概覽主指標區** — 把概覽分頁裡的主指標 grid(L271-284,`<div className="grid grid-cols-2 …"> … </div>` 8 個 `<Metric>`)替換為 4 大卡:

```tsx
              <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
                <MetricCard
                  termKey="total_return"
                  label={L.metrics.total_return}
                  value={pct(result.total_return_pct)}
                  health={result.total_return_pct >= 0 ? "up" : "down"}
                  sub={
                    <span className="text-muted">
                      {L.metrics.buy_hold} {pct(result.buy_hold_return_pct)} ·{" "}
                      <span className={result.total_return_pct - result.buy_hold_return_pct >= 0 ? "text-up" : "text-down"}>
                        {L.backtest.excess} {pct(result.total_return_pct - result.buy_hold_return_pct)}
                      </span>
                    </span>
                  }
                />
                <MetricCard
                  termKey="max_drawdown"
                  label={L.metrics.max_drawdown}
                  value={pct(-result.max_drawdown_pct)}
                  health="down"
                />
                <MetricCard
                  termKey="sharpe"
                  label={L.metrics.sharpe}
                  value={result.sharpe.toFixed(2)}
                  health={result.sharpe < 0 ? "down" : result.sharpe > 1 ? "up" : "neutral"}
                />
                <MetricCard
                  termKey="win_rate"
                  label={L.metrics.win_rate}
                  value={`${result.win_rate.toFixed(0)}%`}
                  health="neutral"
                />
              </div>
```

- [ ] **Step 4: 空交易提示 + 次指標 toggle** — 把次指標列(L285-292,`<div className="flex flex-wrap gap-x-4 …"> … </div>`)替換為:

```tsx
              {result.num_trades === 0 && (
                <p className="rounded-md border border-warning/40 bg-surface-2 px-3 py-2 text-sm text-warning">
                  {L.backtest.noTrades}
                </p>
              )}
              <div>
                <button
                  type="button"
                  onClick={() => setMoreMetrics((m) => !m)}
                  className="text-xs text-muted hover:text-text"
                >
                  {L.backtest.moreMetrics} {moreMetrics ? "▴" : "▾"}
                </button>
                {moreMetrics && (
                  <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
                    <span><Term k="cagr">{L.metrics.cagr}</Term> <span className="num">{pct(result.cagr)}</span></span>
                    <span><Term k="sortino">{L.metrics.sortino}</Term> <span className="num">{result.sortino.toFixed(2)}</span></span>
                    <span><Term k="calmar">{L.metrics.calmar}</Term> <span className="num">{result.calmar.toFixed(2)}</span></span>
                    <span><Term k="profit_factor">{L.metrics.profit_factor}</Term> <span className="num">{result.profit_factor == null ? "∞" : result.profit_factor.toFixed(2)}</span></span>
                    <span><Term k="annualized_volatility">{L.metrics.annualized_volatility}</Term> <span className="num">{pct(result.annualized_volatility * 100)}</span></span>
                    <span><Term k="exposure">{L.metrics.exposure}</Term> <span className="num">{result.exposure_pct.toFixed(0)}%</span></span>
                    <span><Term k="turnover">{L.metrics.turnover}</Term> <span className="num">{result.turnover.toFixed(2)}×</span></span>
                    <span><Term k="max_consecutive_losses">{L.metrics.max_consecutive_losses}</Term> <span className="num">{result.max_consecutive_losses}</span></span>
                    <span><Term k="num_trades">{L.metrics.num_trades}</Term> <span className="num">{result.num_trades}</span></span>
                  </div>
                )}
              </div>
```

- [ ] **Step 5: 型別檢查 + 建置** — Run: `cd frontend && npx tsc --noEmit && npm run build` — Expected: pass。

- [ ] **Step 6: 視覺驗證** — `run-app` → 回測頁 → 執行回測 → 確認:4 大主卡放大;總報酬卡並列 Buy&Hold + 超額(正綠負紅);Sharpe<0 紅 / 0–1 中性 / >1 綠;回撤永遠 down 色;勝率中性;每標題 hover 出解讀;「更多指標」toggle 展開次指標;造一個 0 交易情境(極端參數)→ 顯眼出現「此區間策略未產生任何交易」。Expected: 分級+解讀+空交易提示成立。

- [ ] **Step 7: Commit**

```bash
git add frontend/components/MetricCard.tsx frontend/components/BacktestPanel.tsx
git commit -m "feat(frontend): backtest C4 — tiered metric cards with health coloring, glossary, no-trades notice"
```

---

### Task 10: 回測頁 — 統一結果分頁(Area C5)

**Files:**
- Modify: `frontend/components/BacktestPanel.tsx`(`tab` state L36、分頁列 L255-267、各結果區塊 L297-490)

**Interfaces:**
- Consumes: `L`。
- Produces: 單一分頁容器 `概覽 | 交易明細 | 比較 | 最佳化 | 樣本外`;只顯示跑過的分頁;跑哪個自動切到該頁;移除「按上面按鈕」死角;最佳化 use 套參後切回概覽並提示。

- [ ] **Step 1: 擴充 tab 型別** — 把 `const [tab, setTab] = useState<"overview" | "trades" | "walkforward">("overview");`(L36)改為:

```tsx
  const [tab, setTab] = useState<"overview" | "trades" | "compare" | "optimize" | "walkforward">("overview");
  const [appliedHint, setAppliedHint] = useState(false);
```

- [ ] **Step 2: 各分析自動切頁** — 在各 setter 後設對應 tab:
  - `compare()`(L104-114)的 `setComparison(...)` 之後加 `setTab("compare");`
  - `optimize()`(L63-85)的 `setOptimization(...)` 之後加 `setTab("optimize");`
  - `runWalkForward()`(L116-138)的 `setWalkforward(...)` 之後加 `setTab("walkforward");`
  - `run()` 已有 `setTab("overview")`(保留);並在 `resetOutputs()` 內(Task 8 Step 3 附近)加 `setAppliedHint(false);`。

- [ ] **Step 3: 重寫分頁列為「只顯示跑過的」** — 把分頁列(L255-267,外層 `{result && ( … )}` 內的 `<div className="flex gap-2 border-b border-border text-sm"> … </div>`)整段連同其外層條件改為一個統一容器。把 L253 的 `{result && (` 起到 L338 的對應 `)}` 之間,以及後面散落的 optimization/comparison/walkforward 區塊統一收進這個容器。**做法**:在 `{error && …}`(L251)之後、原 `{result && (`(L253)位置,替換為:

```tsx
      {(result || comparison || optimization || walkforward) && (
        <div className="space-y-3">
          <div className="flex gap-2 border-b border-border text-sm">
            {result && (
              <>
                <TabBtn id="overview" tab={tab} setTab={setTab}>{L.backtest.overview}</TabBtn>
                <TabBtn id="trades" tab={tab} setTab={setTab}>{L.backtest.trades}</TabBtn>
              </>
            )}
            {comparison && <TabBtn id="compare" tab={tab} setTab={setTab}>{L.backtest.tabCompare}</TabBtn>}
            {optimization && <TabBtn id="optimize" tab={tab} setTab={setTab}>{L.backtest.tabOptimize}</TabBtn>}
            {walkforward && <TabBtn id="walkforward" tab={tab} setTab={setTab}>{L.backtest.tabWalkforward}</TabBtn>}
          </div>

          {appliedHint && tab === "overview" && (
            <p className="text-xs text-accent">{L.backtest.applied}</p>
          )}
```

- [ ] **Step 4: 概覽/交易分頁條件改 result 守門** — 確認原本 `{tab === "overview" && ( … )}`(含 Task 8/9 的 K 線與指標)與 `{tab === "trades" && ( … )}` 區塊保留,但把它們各自加上 `result &&` 守門(避免無 result 時存取 `result.*`):把 `{tab === "overview" && (` 改為 `{result && tab === "overview" && (`,`{tab === "trades" && (` 改為 `{result && tab === "trades" && (`。並把交易明細裡 `No trades.`(L300)改為 `{L.backtest.noTrades}`。

- [ ] **Step 5: 移除 walkforward 死角、把三表搬進容器** — 刪除舊的 `{tab === "walkforward" && ( <p>點上方…</p> )}`(L334-336)。把原本散落在 `</section>` 前的 `{optimization && ( <table>…</table> )}`(L340-399)、`{comparison && ( <table>…</table> )}`(L401-437)、`{walkforward && ( <div>…</div> )}`(L439-490)三段,**移到本容器內**並改為分頁守門:
  - 比較表外層 `{comparison && (` → `{tab === "compare" && comparison && (`
  - 最佳化表外層 `{optimization && (` → `{tab === "optimize" && optimization && (`
  - 樣本外外層 `{walkforward && (` → `{tab === "walkforward" && walkforward && (`
  容器最後補一個 `</div>` 收掉 Step 3 開的 `<div className="space-y-3">`,並以 `)}` 收掉 `{(result || …) && (`。原 `{result && ( … )}` 舊包裝整段移除(其內容已被新容器吸收)。

- [ ] **Step 6: 最佳化 use 切回概覽** — 把最佳化表內 `use` 按鈕 onClick(L383-388)改為:

```tsx
                        onClick={() => {
                          setParams({ ...(r.params as Record<string, number>) });
                          setOptimization(null);
                          setAppliedHint(true);
                          setTab("overview");
                        }}
```

- [ ] **Step 7: 新增 TabBtn 子元件** — 在檔末 `function Metric(...)` 之後加(`Metric` 若已無人引用可保留不刪——surgical):

```tsx
function TabBtn({
  id, tab, setTab, children,
}: {
  id: "overview" | "trades" | "compare" | "optimize" | "walkforward";
  tab: string;
  setTab: (t: "overview" | "trades" | "compare" | "optimize" | "walkforward") => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={() => setTab(id)}
      className={`px-3 py-1.5 ${tab === id ? "border-b-2 border-accent text-text" : "text-muted hover:text-text"}`}
    >
      {children}
    </button>
  );
}
```

- [ ] **Step 8: 型別檢查 + 建置** — Run: `cd frontend && npx tsc --noEmit && npm run build` — Expected: tsc 無錯(注意所有 `result.*` 已被 `result &&` 守門);build 成功。

- [ ] **Step 9: 視覺驗證** — `run-app` → 回測頁 →(a)執行回測 → 只見「概覽/交易明細」分頁、自動停在概覽;(b)展開進階 → 比較全部 → 自動切到「比較」分頁、且不再出現概覽/交易分頁;(c)最佳化 → 切到「最佳化」分頁 → 按某列 use → 自動回概覽並顯示「已套用…」提示;(d)樣本外 → 切到「樣本外」分頁,無「按上面按鈕」死角。Expected: 結果統一於分頁、只顯示跑過的、自動切頁。

- [ ] **Step 10: Commit**

```bash
git add frontend/components/BacktestPanel.tsx
git commit -m "feat(frontend): backtest C5 — unified result tabs (only-run tabs, auto-switch, optimize-use returns to overview)"
```

---

## Self-Review

**1. Spec 覆蓋(對照 spec §5 Area B、§6 Area C，跳過 C2):**

| Spec 需求 | 任務 |
|---|---|
| **B** live `PriceChart`(live 模式預設開、可暫停) | Task 4(`live` config + 暫停鈕 + `refetchIntervalInBackground:false` 由 P1 處理失焦) |
| **B** Ticker 列(現價/24h 漲跌/高低,mono + 漲跌色) | Task 1(`api.ticker`)+ Task 3(`deriveStats` 誠實推導 24h)+ Task 4(渲染) |
| **B** 可搜尋商品選擇器(常用清單 + 自由輸入) | Task 4(`<input list>` + `<datalist>`) |
| **B** AI 訊號疊 marker | Task 5 |
| **B** 台股 `data-market` + 離線 CSV 徽章(不偽裝即時) | Task 4(`setMarket` + 徽章 + 非 crypto 停輪詢) |
| **B** 失焦暫停 | P1 `PriceChart`/ticker query `refetchIntervalInBackground:false` + Task 4 手動暫停 |
| **B** URL query 持久化 symbol/timeframe/market | Task 6 |
| **C1** 主按鈕「執行回測」+ 折疊進階分析(各帶說明 + `<Term>` + 禁用態可見說明) | Task 7 |
| **C3** 概覽加靜態 K 線疊 `tradesToMarkers(result.trades)`(方案 A 另抓 candles)+ ma_cross SMA overlays | Task 8 |
| **C4** 4 主卡(總報酬+B&H+超額/回撤/Sharpe/勝率)放大、次指標收納、`<Term>` 全覆蓋、健康度色標、空交易提示 | Task 9 |
| **C5** 統一分頁(概覽/交易明細/比較/最佳化/樣本外)、只顯示跑過、自動切頁、移除死角、optimize use 切回概覽 | Task 10 |
| 中英文化(`Market`/`Backtest`/`Run`/`Compare all`…→ `L.*`) | Task 2/4/7/9/10 |

**2. C2 明確排除:** 本計畫不含日期區間(`start`/`end`)— `limit`(最近 N 根)維持不動,C2 屬 P3(需後端)獨立計畫。✅

**3. Placeholder 掃描:** 無 TBD/TODO;每個 code step 均含完整可貼上的 TSX/TS。唯一帶判斷的點是 Task 8 Step 6 overlay `color` 值,已給明確預設(`"--accent"`/`"--muted"`)並要求對齊 P1 `PriceChart` overlay color 解讀後在 Step 7 視覺確認——非佔位,是「對齊既有實作」的驗證步驟。✅

**4. 型別一致性檢查:**
- `Ticker`(Task 1)= `{symbol, price, timestamp}`,與後端 `app/schemas.py:Ticker`(`symbol/price/timestamp`)相符;**不**含 bid/ask/24h,故 24h 由 OHLCV 推導(Task 3,誠實)。✅
- `api.ohlcv(symbol, timeframe, limit, market)`、`api.aiSignal(symbol, market, timeframe, limit)` 簽名與 `lib/api.ts` 相符。✅
- `PriceChart` props(`candles`/`live`/`markers`/`overlays`/`height`)、`tradesToMarkers(trades)`、`type ChartMarker/Overlay/LiveConfig/OHLCV`、`<Term k=…>`、`L`/`GLOSSARY` 全部消費自 P1 交付,未重新定義。✅
- `BacktestResult` 欄位(`total_return_pct`/`buy_hold_return_pct`/`max_drawdown_pct`/`sharpe`/`win_rate`/`cagr`/`sortino`/`calmar`/`profit_factor`/`annualized_volatility`/`exposure_pct`/`turnover`/`max_consecutive_losses`/`num_trades`/`trades`/`equity_curve`)與 `lib/api.ts` 相符。✅
- `result.trades`(`Trade`:`entry_time`/`exit_time`/`return_pct`…)滿足 `tradesToMarkers` 的 `TradeLike`。✅
- `Overlay` 用 `{ id, type:"sma", period, color }`(對齊 P1 `chart-helpers` 的 `Overlay = { id; type:"sma"|"ema"; period; color? }`)。✅

**已知務實取捨:** 前端無單元 runner,行為以 `tsc --noEmit` + `npm run build` + `run-app` 視覺驗證把關;純邏輯(`market-stats.ts`)以 node 暫行檢查。24h 統計因後端 Ticker 不提供,誠實由 OHLCV 推導而非偽造後端欄位(fail-loud 精神)。
