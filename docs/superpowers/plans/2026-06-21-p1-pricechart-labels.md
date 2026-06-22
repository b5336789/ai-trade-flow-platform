# P1 地基:PriceChart 共用線圖 + 語言層 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立一個可即時輪詢、可疊買賣點與指標、增量更新不閃爍的共用 `PriceChart` 元件,以及集中化的中文術語/解讀語言層 —— P2–P5 全部建立其上。

**Architecture:** 純前端。一個純函式 helper 檔(`lib/chart-helpers.ts`,可被未來 runner 測試)+ 一個語言常數檔(`lib/labels.ts`)+ `<Term>` tooltip 元件 + `PriceChart` React 元件(lightweight-charts v4 封裝,靜態與 live 兩模式)。`CandleChart` 退化為薄包裝以維持既有引用。

**Tech Stack:** Next 14 App Router · React 18 · TypeScript · lightweight-charts 4.2.3 · @tanstack/react-query 5 · Tailwind(設計 token 來自 `DESIGN.md`)

## Global Constraints

- **設計系統權威 = `DESIGN.md`**;漲跌色只透過 `--up` / `--down` CSS token,絕不硬編綠漲;`data-market="tw"` 翻轉;cyan(`--accent`)僅限 AI;數字一律 `tabular-nums`(`.num`);圓角用 `--r-*`。
- **lightweight-charts v4 API**(非 v5):`chart.addCandlestickSeries()` / `addHistogramSeries()` / `addLineSeries()` / `series.update()` / `series.setMarkers()` / `chart.subscribeCrosshairMove()`。比照現有 `components/CandleChart.tsx`。
- **前端無單元測試 runner(刻意)**:CLAUDE.md 載明 CI 只跑 `npm run build`。本計畫每個任務的驗收循環 = `npx tsc --noEmit`(型別)→ `npm run build`(建置)→(行為型任務)`run-app` skill 視覺驗證。純邏輯集中在 `lib/chart-helpers.ts` 以利未來導入 runner。**不寫空殼單元測試湊覆蓋率。**
- **Fail loud**:資料錯誤/空資料顯式呈現,不靜默吞掉。
- **Surgical**:只動本計畫列出的檔;不順手重構鄰近碼。
- 所有指令前綴 `cd frontend`(前端 root = `/Users/b5336789/Documents/workspace/ai-trade-flow-platform/frontend`)。

---

## File Structure

- **Create** `frontend/lib/chart-helpers.ts` — 純函式 + 共用 chart 型別(`ChartMarker`/`Overlay`/`OHLCV`/`LiveConfig`),無 React。
- **Create** `frontend/lib/labels.ts` — `L`(UI 文案)+ `GLOSSARY`(指標白話解讀,全部指標)。
- **Create** `frontend/components/Term.tsx` — `<Term>` 文字+`?` tooltip,讀 `GLOSSARY`。
- **Create** `frontend/components/PriceChart.tsx` — 主元件(靜態+live)。
- **Modify** `frontend/components/CandleChart.tsx` — 退化為 `PriceChart` 薄包裝(維持既有 API,既有引用零改動)。

---

### Task 1: 語言層 `lib/labels.ts`

**Files:**
- Create: `frontend/lib/labels.ts`

**Interfaces:**
- Produces: `export const L`(巢狀文案物件)、`export const GLOSSARY: Record<string,string>`。後續 `<Term>`、回測頁、各面板引用。

- [ ] **Step 1: 建立檔案**

```ts
// frontend/lib/labels.ts
// 集中化 UI 文案與術語白話解讀。各頁引用此處,杜絕散落的硬編字串(尤其中英混雜)。
// 金融慣用詞(Sharpe/RSI/CAGR)保留原詞,解讀放 GLOSSARY。

export const L = {
  common: { run: "執行", loading: "執行中…", more: "更多", advanced: "進階分析", noData: "無資料" },
  market: { title: "市場行情", symbol: "商品", timeframe: "週期", live: "即時", paused: "已暫停", offlineCsv: "離線資料(CSV)" },
  backtest: {
    title: "模擬回測",
    run: "執行回測",
    compare: "比較全部策略",
    optimize: "參數最佳化",
    walkforward: "樣本外驗證",
    rangeRecent: "最近 N 根",
    rangeDates: "日期區間",
    overview: "概覽",
    trades: "交易明細",
    excess: "超額(策略 − 大盤)",
    noTrades: "此區間策略未產生任何交易",
  },
  metrics: {
    total_return: "總報酬",
    buy_hold: "Buy & Hold",
    cagr: "年化報酬 CAGR",
    max_drawdown: "最大回撤",
    sharpe: "Sharpe",
    sortino: "Sortino",
    calmar: "Calmar",
    win_rate: "勝率",
    profit_factor: "獲利因子",
    annualized_volatility: "年化波動",
    exposure: "曝險時間",
    turnover: "週轉率",
    max_consecutive_losses: "最大連虧",
    num_trades: "交易數",
  },
} as const;

// 每個指標一句白話(主+次全覆蓋)。<Term> 以 hover tooltip 呈現。
export const GLOSSARY: Record<string, string> = {
  total_return: "整段期間的總損益百分比。",
  buy_hold: "同期間「買進並持有」不操作的報酬,用來比較策略有沒有贏大盤。",
  cagr: "把總報酬換算成每年平均的複利成長率,跨不同長度才好比較。",
  max_drawdown: "從資產高點跌到後續低點的最大跌幅;越小代表越穩、越不會睡不著。",
  sharpe: "風險調整後報酬;>1 算不錯,接近 0 普通,<0 代表承擔波動卻虧損。",
  sortino: "類似 Sharpe,但只計算「下跌」的波動,對下檔風險更敏感。",
  calmar: "年化報酬 ÷ 最大回撤;衡量「賺的相對於最痛的那一跌」划不划算。",
  win_rate: "獲利交易佔總交易的比例。注意:勝率高 ≠ 賺錢(可能小賺多次、大賠一次)。",
  profit_factor: "總獲利 ÷ 總虧損;>1 才有正期望值,∞ 代表期間內沒有虧損交易。",
  annualized_volatility: "報酬的年化標準差;數字越大代表淨值上下震盪越劇烈。",
  exposure: "有持倉的時間佔比;100% 代表幾乎全程在場,低代表多在空手等訊號。",
  turnover: "交易頻繁度;越高代表進出越勤、累積的交易成本越多。",
  max_consecutive_losses: "連續虧損的最長次數;反映策略最糟的一段心理壓力。",
  num_trades: "完整進出場的交易筆數;太少則統計不具代表性。",
  walk_forward: "用過去資料選參數、在「沒看過的未來」資料上驗證,專門抓出過度最佳化。",
  optimize: "掃描參數網格找最佳組合;本系統以樣本外(OOS)指標排名,避免挑到過擬合的參數。",
};
```

- [ ] **Step 2: 型別檢查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 無錯誤(新檔僅匯出常數)。

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/labels.ts
git commit -m "feat(frontend): add centralized labels + metric glossary layer"
```

---

### Task 2: `<Term>` tooltip 元件

**Files:**
- Create: `frontend/components/Term.tsx`

**Interfaces:**
- Consumes: `GLOSSARY` from `@/lib/labels`。
- Produces: `export function Term({ k, children }: { k: string; children: React.ReactNode })` — 渲染 children + 若 `GLOSSARY[k]` 存在則附帶 `?` 與 hover/focus tooltip。

- [ ] **Step 1: 建立元件**

```tsx
// frontend/components/Term.tsx
"use client";
import { GLOSSARY } from "@/lib/labels";

// 顯示一個術語標籤;若有對應白話解讀,附一個可 hover/focus 的「?」氣泡。
// 純 CSS group-hover,不引入 tooltip 套件(YAGNI)。
export function Term({ k, children }: { k: string; children: React.ReactNode }) {
  const def = GLOSSARY[k];
  if (!def) return <>{children}</>;
  return (
    <span className="group relative inline-flex items-center gap-1">
      <span>{children}</span>
      <button
        type="button"
        aria-label={`${typeof children === "string" ? children : k} 說明`}
        className="grid h-3.5 w-3.5 place-items-center rounded-full border border-border-strong text-[9px] leading-none text-muted hover:text-text focus:outline-none focus-visible:ring-1 focus-visible:ring-accent"
      >
        ?
      </button>
      <span
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-0 z-30 mb-1 hidden w-56 rounded-md border border-border bg-surface-3 p-2 text-[11px] font-normal leading-snug text-text shadow-lg group-hover:block group-focus-within:block"
      >
        {def}
      </span>
    </span>
  );
}
```

- [ ] **Step 2: 型別檢查 + 建置**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: tsc 無錯;build 成功。

- [ ] **Step 3: Commit**

```bash
git add frontend/components/Term.tsx
git commit -m "feat(frontend): add <Term> glossary tooltip component"
```

---

### Task 3: 純函式 helper `lib/chart-helpers.ts`

**Files:**
- Create: `frontend/lib/chart-helpers.ts`

**Interfaces:**
- Consumes: `Candle` from `@/lib/api`;type-only imports from `lightweight-charts`。
- Produces:
  - 型別 `OHLCV`、`ChartMarker`、`Overlay`、`LiveConfig`。
  - `candleTime(c: Candle): UTCTimestamp`
  - `toCandlestickData(candles: Candle[]): CandlestickData[]`
  - `toVolumeData(candles: Candle[], upColor: string, downColor: string): HistogramData[]`
  - `tradesToMarkers(trades: TradeLike[]): ChartMarker[]`
  - `markerToSeries(m: ChartMarker, upColor: string, downColor: string): SeriesMarker<Time>`
  - `TradeLike` 介面。

- [ ] **Step 1: 建立 helper**

```ts
// frontend/lib/chart-helpers.ts
// 純函式 + 共用 chart 型別。無 React,可被未來單元 runner 直接測。
import type {
  UTCTimestamp,
  Time,
  CandlestickData,
  HistogramData,
  SeriesMarker,
} from "lightweight-charts";
import type { Candle } from "./api";

export interface OHLCV { time: number; open: number; high: number; low: number; close: number; volume: number }
export interface LiveConfig { symbol: string; timeframe: string; market?: string; intervalMs?: number }
export interface ChartMarker { time: number; position: "aboveBar" | "belowBar"; kind: "buy" | "sell"; text?: string }
export interface Overlay { id: string; type: "sma" | "ema"; period: number; color?: string }
export interface TradeLike { entry_time: string; exit_time: string; return_pct: number }

const toUtc = (iso: string): UTCTimestamp =>
  Math.floor(new Date(iso).getTime() / 1000) as UTCTimestamp;

export const candleTime = (c: Candle): UTCTimestamp => toUtc(c.timestamp);

export function toCandlestickData(candles: Candle[]): CandlestickData[] {
  return candles.map((c) => ({ time: candleTime(c), open: c.open, high: c.high, low: c.low, close: c.close }));
}

export function toVolumeData(candles: Candle[], upColor: string, downColor: string): HistogramData[] {
  return candles.map((c) => ({ time: candleTime(c), value: c.volume, color: c.close >= c.open ? upColor : downColor }));
}

// 每筆交易 → 進場(▲ buy)+ 出場(▼ sell,text 帶報酬%)。輸出依時間升冪(setMarkers 要求)。
export function tradesToMarkers(trades: TradeLike[]): ChartMarker[] {
  const out: ChartMarker[] = [];
  for (const t of trades) {
    out.push({ time: toUtc(t.entry_time), position: "belowBar", kind: "buy", text: "買" });
    const sign = t.return_pct >= 0 ? "+" : "";
    out.push({ time: toUtc(t.exit_time), position: "aboveBar", kind: "sell", text: `賣 ${sign}${t.return_pct.toFixed(1)}%` });
  }
  return out.sort((a, b) => a.time - b.time);
}

export function markerToSeries(m: ChartMarker, upColor: string, downColor: string): SeriesMarker<Time> {
  return {
    time: m.time as UTCTimestamp,
    position: m.position,
    color: m.kind === "buy" ? upColor : downColor,
    shape: m.kind === "buy" ? "arrowUp" : "arrowDown",
    text: m.text,
  };
}
```

- [ ] **Step 2: 型別檢查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 無錯誤。

- [ ] **Step 3: 邏輯自驗(無 runner 的暫行檢查)**

Run:
```bash
cd frontend && node --input-type=module -e "
const toUtc = (iso) => Math.floor(new Date(iso).getTime()/1000);
function tradesToMarkers(trades){const out=[];for(const t of trades){out.push({time:toUtc(t.entry_time),position:'belowBar',kind:'buy',text:'買'});const s=t.return_pct>=0?'+':'';out.push({time:toUtc(t.exit_time),position:'aboveBar',kind:'sell',text:'賣 '+s+t.return_pct.toFixed(1)+'%'});}return out.sort((a,b)=>a.time-b.time);}
const m = tradesToMarkers([{entry_time:'2021-02-01T00:00:00',exit_time:'2021-01-01T00:00:00',return_pct:3.2}]);
if(m.length!==2) throw new Error('expected 2 markers');
if(!(m[0].time < m[1].time)) throw new Error('markers not sorted ascending');
if(m.find(x=>x.kind==='sell').text!=='賣 +3.2%') throw new Error('sell label wrong');
console.log('chart-helpers logic OK');
"
```
Expected: 印出 `chart-helpers logic OK`(驗證:產 2 個 marker、時間升冪排序、賣出標籤格式)。

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/chart-helpers.ts
git commit -m "feat(frontend): add pure chart-helpers (series mappers + trade markers)"
```

---

### Task 4: `PriceChart` 靜態核心

**Files:**
- Create: `frontend/components/PriceChart.tsx`

**Interfaces:**
- Consumes: `Candle` from `@/lib/api`;helpers + 型別 from `@/lib/chart-helpers`。
- Produces: `export function PriceChart(props: PriceChartProps)`,`export interface PriceChartProps`。本任務只實作**靜態模式**(`live` 暫不啟用,Task 5 補)。

```ts
interface PriceChartProps {
  candles: Candle[];
  height?: number;            // 預設 360
  markers?: ChartMarker[];
  overlays?: Overlay[];
  volume?: boolean;           // 預設 true
  live?: LiveConfig | null;   // Task 5 啟用;本任務忽略
  onCrosshairMove?: (p: OHLCV | null) => void;
}
```

- [ ] **Step 1: 建立靜態元件**

```tsx
// frontend/components/PriceChart.tsx
"use client";
import { createChart, ColorType, type IChartApi, type ISeriesApi, type UTCTimestamp } from "lightweight-charts";
import { useEffect, useRef } from "react";
import type { Candle } from "@/lib/api";
import {
  toCandlestickData, toVolumeData, markerToSeries,
  type ChartMarker, type Overlay, type LiveConfig, type OHLCV,
} from "@/lib/chart-helpers";

export interface PriceChartProps {
  candles: Candle[];
  height?: number;
  markers?: ChartMarker[];
  overlays?: Overlay[];
  volume?: boolean;
  live?: LiveConfig | null;
  onCrosshairMove?: (p: OHLCV | null) => void;
}

function cssVar(name: string, fallback: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

// 簡單均線(用收盤價算 SMA);overlays 疊加用。
function sma(values: number[], period: number): (number | null)[] {
  const out: (number | null)[] = [];
  let sum = 0;
  for (let i = 0; i < values.length; i++) {
    sum += values[i];
    if (i >= period) sum -= values[i - period];
    out.push(i >= period - 1 ? sum / period : null);
  }
  return out;
}

export function PriceChart({
  candles, height = 360, markers, overlays, volume = true, onCrosshairMove,
}: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);

  // 建圖一次。candles 變動只 setData,不重建(避免閃爍/丟縮放)。
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const up = cssVar("--up", "#34D399");
    const down = cssVar("--down", "#F87171");
    const bg = cssVar("--bg", "#0A0B0D");
    const grid = cssVar("--border", "#1f1f1f");
    const text = cssVar("--text-muted", "#8A9099");

    const chart = createChart(el, {
      layout: { background: { type: ColorType.Solid, color: bg }, textColor: text },
      grid: { vertLines: { color: grid }, horzLines: { color: grid } },
      width: el.clientWidth, height,
      timeScale: { timeVisible: true },
      crosshair: { mode: 1 },
    });
    const candleSeries = chart.addCandlestickSeries({
      upColor: up, downColor: down, borderVisible: false, wickUpColor: up, wickDownColor: down,
    });
    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;

    if (volume) {
      const vol = chart.addHistogramSeries({ priceFormat: { type: "volume" }, priceScaleId: "" });
      vol.priceScale().applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
      volumeSeriesRef.current = vol;
    }

    // 十字準星 → 回拋當前根 OHLCV
    if (onCrosshairMove) {
      chart.subscribeCrosshairMove((param) => {
        const bar = param.seriesData.get(candleSeries) as
          | { open: number; high: number; low: number; close: number } | undefined;
        const v = volumeSeriesRef.current
          ? (param.seriesData.get(volumeSeriesRef.current) as { value: number } | undefined)
          : undefined;
        if (!bar || param.time == null) { onCrosshairMove(null); return; }
        onCrosshairMove({ time: param.time as number, ...bar, volume: v?.value ?? 0 });
      });
    }

    const ro = new ResizeObserver(() => chart.applyOptions({ width: el.clientWidth }));
    ro.observe(el);
    return () => { ro.disconnect(); chart.remove(); chartRef.current = null; candleSeriesRef.current = null; volumeSeriesRef.current = null; };
  // 僅在 height/volume/crosshair 身份改變時重建;candles 不在依賴內。
  }, [height, volume, onCrosshairMove]);

  // 資料更新:setData(整段)。增量 update 由 live 模式負責(Task 5)。
  useEffect(() => {
    const cs = candleSeriesRef.current, chart = chartRef.current;
    if (!cs || !chart) return;
    const up = cssVar("--up", "#34D399"), down = cssVar("--down", "#F87171");
    cs.setData(toCandlestickData(candles));
    if (volumeSeriesRef.current) volumeSeriesRef.current.setData(toVolumeData(candles, up, down));
    chart.timeScale().fitContent();
  }, [candles]);

  // 標記
  useEffect(() => {
    const cs = candleSeriesRef.current;
    if (!cs) return;
    const up = cssVar("--up", "#34D399"), down = cssVar("--down", "#F87171");
    cs.setMarkers((markers ?? []).map((m) => markerToSeries(m, up, down)));
  }, [markers]);

  // 疊加均線
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || !overlays?.length) return;
    const closes = candles.map((c) => c.close);
    const times = candles.map((c) => Math.floor(new Date(c.timestamp).getTime() / 1000) as UTCTimestamp);
    const lines = overlays.map((ov) => {
      const line = chart.addLineSeries({ color: ov.color ?? cssVar("--accent", "#22D3EE"), lineWidth: 1 });
      const series = sma(closes, ov.period);
      line.setData(times.map((t, i) => (series[i] == null ? null : { time: t, value: series[i]! })).filter(Boolean) as { time: UTCTimestamp; value: number }[]);
      return line;
    });
    return () => { lines.forEach((l) => chart.removeSeries(l)); };
  }, [overlays, candles]);

  if (!candles.length) {
    return (
      <div className="grid w-full place-items-center rounded-md border border-border bg-surface-1 text-sm text-muted" style={{ height }}>
        無資料
      </div>
    );
  }
  return <div ref={containerRef} className="w-full" />;
}
```

- [ ] **Step 2: 型別檢查 + 建置**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: tsc 無錯;build 成功。

- [ ] **Step 3: 視覺驗證(暫時掛到市場頁)**

在 `frontend/components/MarketPanel.tsx` 既有 `<CandleChart candles=... />` 之外,**暫時**加一行 `<PriceChart candles={candles.data ?? []} markers={[{time: Math.floor(Date.now()/1000), position:"belowBar", kind:"buy", text:"測試"}]} />`,用 `run-app` skill 啟動 app → 開 `/market` → 確認:K 線渲染、有成交量副圖、游標移動不報錯、出現一個買進▲標記。確認後**移除這行暫時程式碼**。
Expected: 圖正常顯示;主控台無錯。

- [ ] **Step 4: Commit**

```bash
git add frontend/components/PriceChart.tsx
git commit -m "feat(frontend): add PriceChart static core (incremental data, volume, crosshair, markers, overlays)"
```

---

### Task 5: `PriceChart` live 輪詢模式

**Files:**
- Modify: `frontend/components/PriceChart.tsx`

**Interfaces:**
- Consumes: `api.ohlcv` from `@/lib/api`;`useQuery` from `@tanstack/react-query`。
- Produces: 當 `live` 非 null 時,元件內部輪詢更新最後一根(`series.update()`)並顯示會閃爍的現價徽章。靜態行為(Task 4)在 `live==null` 時不變。

- [ ] **Step 1: 在 PriceChart 內加入 live 輪詢**

於 `PriceChart.tsx` 頂部 import 區補:
```tsx
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
```

在 `if (!candles.length)` 之前插入以下 live 邏輯(`useState`/`useQuery`/`useEffect` 必須在元件主體、early-return 之前):
```tsx
  // ── Live 輪詢(live 非 null 時啟用)──────────────────────────────
  const [lastPrice, setLastPrice] = useState<number | null>(null);
  const [flash, setFlash] = useState<"up" | "down" | null>(null);
  const lastTimeRef = useRef<number | null>(null);

  const liveQuery = useQuery({
    queryKey: ["price-live", live?.symbol, live?.timeframe, live?.market],
    queryFn: () => api.ohlcv(live!.symbol, live!.timeframe, 2, live!.market ?? "crypto"),
    enabled: !!live,
    refetchInterval: live ? Math.max(1000, live.intervalMs ?? 3000) : false,
    refetchIntervalInBackground: false, // 分頁失焦自動停
  });

  useEffect(() => {
    const cs = candleSeriesRef.current;
    const rows = liveQuery.data;
    if (!cs || !rows || !rows.length) return;
    const up = cssVar("--up", "#34D399"), down = cssVar("--down", "#F87171");
    for (const c of rows) {
      const t = Math.floor(new Date(c.timestamp).getTime() / 1000) as UTCTimestamp;
      cs.update({ time: t, open: c.open, high: c.high, low: c.low, close: c.close });
      if (volumeSeriesRef.current) {
        volumeSeriesRef.current.update({ time: t, value: c.volume, color: c.close >= c.open ? up : down });
      }
      lastTimeRef.current = t;
    }
    const newClose = rows[rows.length - 1].close;
    setLastPrice((prev) => {
      if (prev != null && newClose !== prev) setFlash(newClose > prev ? "up" : "down");
      return newClose;
    });
  }, [liveQuery.data]);

  useEffect(() => {
    if (!flash) return;
    const id = setTimeout(() => setFlash(null), 200);
    return () => clearTimeout(id);
  }, [flash]);
```

並把最終 `return` 改為帶現價徽章的包裝(保留 early-return 的空資料分支不變):
```tsx
  return (
    <div className="relative w-full">
      {live && lastPrice != null && (
        <div
          className={`num absolute right-2 top-2 z-10 rounded-md border border-border bg-surface-2 px-2 py-0.5 text-xs transition-colors ${
            flash === "up" ? "text-up" : flash === "down" ? "text-down" : "text-text"
          }`}
        >
          {lastPrice.toFixed(2)}
        </div>
      )}
      <div ref={containerRef} className="w-full" />
    </div>
  );
```

- [ ] **Step 2: 型別檢查 + 建置**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: tsc 無錯;build 成功。

- [ ] **Step 3: 視覺驗證(live)**

`run-app` 啟動 → 在市場頁暫時以 `<PriceChart candles={...} live={{symbol:"BTC/USDT", timeframe:"1m", intervalMs:3000}} />` 掛載 → 觀察:右上現價徽章出現;約 3 秒輪詢一次;最後一根 K 隨輪詢變動且不整張重建(縮放位置不跳)。確認後移除暫時碼。
Expected: 現價更新、變動時徽章閃 up/down 色、無整圖重繪。

- [ ] **Step 4: Commit**

```bash
git add frontend/components/PriceChart.tsx
git commit -m "feat(frontend): add PriceChart live polling mode (incremental update + price flash)"
```

---

### Task 6: `CandleChart` 退化為薄包裝

**Files:**
- Modify: `frontend/components/CandleChart.tsx`

**Interfaces:**
- Consumes: `PriceChart` from `@/components/PriceChart`。
- Produces: `CandleChart` 維持原 props `{ candles: Candle[]; height?: number }`,內部轉呼 `PriceChart`(靜態、無成交量以貼近舊行為)。既有引用(`MarketPanel` 等)零改動。

- [ ] **Step 1: 改寫 CandleChart**

```tsx
// frontend/components/CandleChart.tsx
"use client";
import type { Candle } from "@/lib/api";
import { PriceChart } from "@/components/PriceChart";

// 薄包裝:歷史引用沿用此 API;實作改委派給 PriceChart(靜態模式)。
// 保留 volume=false 以貼近舊版單純 K 線外觀。
export function CandleChart({ candles, height = 320 }: { candles: Candle[]; height?: number }) {
  return <PriceChart candles={candles} height={height} volume={false} />;
}
```

- [ ] **Step 2: 型別檢查 + 建置**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: tsc 無錯;build 成功(所有既有 `CandleChart` 引用仍編譯通過)。

- [ ] **Step 3: 視覺驗證(回歸)**

`run-app` → `/market` → 確認原本的 K 線圖仍正常顯示(現在底層走 PriceChart)。
Expected: 市場頁 K 線如常。

- [ ] **Step 4: Commit**

```bash
git add frontend/components/CandleChart.tsx
git commit -m "refactor(frontend): CandleChart delegates to PriceChart (keep existing API)"
```

---

## Self-Review

**1. Spec 覆蓋(對照 spec §F1/F2):**
- F1 增量更新 → Task 4(setData 不重建)+ Task 5(`series.update`)。✅
- F1 即時輪詢 + 漲跌閃爍 → Task 5。✅
- F1 十字準星 OHLC 浮標 → Task 4 `onCrosshairMove`。✅
- F1 買賣 markers → Task 3 `tradesToMarkers` + Task 4 setMarkers。✅
- F1 疊均線 → Task 4 overlays(sma)。✅
- F1 成交量副圖 → Task 4。✅
- F1 市場色/`--up/--down`/ResizeObserver/空資料 → Task 4。✅
- F1 遷移(CandleChart 薄包裝)→ Task 6。✅
- F2 labels + GLOSSARY(全指標)→ Task 1。✅
- F2 `<Term>` tooltip → Task 2。✅
- **超出 P1 範圍(後續計畫)**:market ticker 列接線、台股 `data-market` 切換、回測頁實際引用 PriceChart → 屬 P2;此處只交付可被引用的元件。

**2. Placeholder 掃描:** 無 TBD/TODO;每個 code step 均含完整程式碼。✅

**3. 型別一致性:** `ChartMarker`/`Overlay`/`LiveConfig`/`OHLCV` 定義於 Task 3,Task 4/5 一致引用;`api.ohlcv(symbol, timeframe, limit, market)` 簽名與 `lib/api.ts` 相符;lightweight-charts v4 方法名(`addCandlestickSeries`/`addHistogramSeries`/`update`/`setMarkers`/`subscribeCrosshairMove`)與安裝版 4.2.3 相符。✅

**已知務實取捨(見 Global Constraints):** 前端無單元 runner,行為以 build + run-app 視覺驗證把關;純邏輯(Task 3)以 node 暫行檢查 + 結構利於未來導入 runner。
