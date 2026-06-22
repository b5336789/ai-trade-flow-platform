# 選單中文化+icon、市場線圖專業化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把左側選單改成「純中文 label + lucide icon」,並以專業投資人角度為市場線圖補齊技術指標(MA/EMA/布林/RSI/MACD)、線圖類型/對數座標/全螢幕/十字準星讀數等終端機操作體驗。

**Architecture:** 三層 — 純函式指標數學落在 `lib/chart-helpers.ts`(可獨立驗證);`components/PriceChart.tsx` 為圖表引擎(lightweight-charts v4,副圖用堆疊獨立 chart + 時間軸同步);`components/MarketPanel.tsx` 為控制容器(指標工具列、timeframe/根數)。選單為獨立小工作(`lib/nav.ts` + `TreeNav.tsx` + lucide-react)。

**Tech Stack:** Next.js 14 (App Router) · React 18 · TypeScript · lightweight-charts **4.2.3** · lucide-react · Tailwind · @tanstack/react-query。

## Global Constraints

- **不升級 lightweight-charts**:維持 v4.2.3。副圖用「多張獨立 chart + `subscribeVisibleLogicalRangeChange` 雙向同步」,不用 v5 pane API。
- **指標一律前端計算**:不新增後端 API、不增加網路往返。
- **色彩紀律(DESIGN.md)**:`--accent`(電光藍 cyan)只給 AI/automation;指標線用中性或各自色票,AI 訊號標記仍是唯一 cyan。
- **市場感知漲跌色**:漲跌一律走 `--up` / `--down` token,經 `cssVar()` 取得,**禁止硬編 hex**;台股 `data-market="tw"` 翻轉不可被破壞。
- **Fail loud**:指標暖機期資料不足時輸出 `null`(圖上不畫),**不得偽造數值**、不得靜默吞錯。
- **選單只顯示中文 label**:不再渲染英文 subtitle。
- **icon 來源**:`lucide-react`(細線條)。
- **分支**:`feat/market-chart-pro-and-nav`。**頻繁 commit**,每個 Task 結束即 commit。
- **硬性關卡**:每個含程式碼的 Task 結束跑 `npx tsc --noEmit`(於 `frontend/`)必須乾淨;最終跑 `npm run build`。

---

## File Structure

| 檔案 | 動作 | 責任 |
|------|------|------|
| `frontend/package.json` | Modify | 新增 `lucide-react` 相依 |
| `frontend/lib/nav.ts` | Modify | `NavItem`/`NavLeaf` 加 `icon`;移除英文 subtitle 的使用 |
| `frontend/components/shell/TreeNav.tsx` | Modify | 渲染 `icon + 中文 label`(單行) |
| `DESIGN.md` | Modify | Navigation ASCII tree 改中文+icon;加 Decisions Log |
| `frontend/lib/chart-helpers.ts` | Modify | 新增純函式 `sma/ema/rsi/macd/bollinger` + `IndicatorConfig`/`OscillatorConfig` 型別 |
| `frontend/components/PriceChart.tsx` | Modify | 線圖類型、對數座標、主圖疊加、RSI/MACD 副圖、十字準星讀數、成交量開關、全螢幕 |
| `frontend/lib/labels.ts` | Modify | 新增市場頁控制文案(中文) |
| `frontend/components/MarketPanel.tsx` | Modify | 指標工具列、timeframe/根數擴充、把設定傳入 PriceChart |

---

## Phase 1 — 選單中文化 + icon

### Task 1: 加入 lucide-react 相依

**Files:**
- Modify: `frontend/package.json`

**Interfaces:**
- Produces: `lucide-react` 可被 import(具名 icon component,如 `FlaskConical`、`LineChart`)。

- [ ] **Step 1: 安裝相依**

Run(於 `frontend/`):
```bash
npm install lucide-react@^0.460.0
```
Expected: `package.json` 與 `package-lock.json` 出現 `lucide-react`;無 peer-dep 錯誤(lucide-react 支援 React 18)。

- [ ] **Step 2: 驗證可被解析**

Run(於 `frontend/`):
```bash
node -e "require.resolve('lucide-react'); console.log('lucide-react OK')"
```
Expected: 印出 `lucide-react OK`。

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "build(frontend): add lucide-react for nav icons"
```

---

### Task 2: 選單改純中文 + icon,並更新 DESIGN.md

**Files:**
- Modify: `frontend/lib/nav.ts`
- Modify: `frontend/components/shell/TreeNav.tsx`
- Modify: `DESIGN.md`

**Interfaces:**
- Consumes: `lucide-react`(Task 1)。
- Produces: `NavItem.icon?: LucideIcon`、`NavLeaf.icon?: LucideIcon`;`TreeNav` 渲染 icon + 中文 label。

- [ ] **Step 1: 改寫 `lib/nav.ts` — 加 icon、保留中文 label**

完整取代檔案內容:
```ts
import {
  FlaskConical, MessageSquareCode, Library,
  Network, History, Workflow,
  CandlestickChart, Wallet,
  Wrench, CalendarClock, Bell, Upload,
  type LucideIcon,
} from "lucide-react";

export interface NavLeaf { label: string; href: string; live?: boolean; icon?: LucideIcon }
export interface NavItem { label: string; href?: string; ai?: boolean; icon?: LucideIcon; children?: NavLeaf[] }

export const NAV: NavItem[] = [
  {
    label: "策略室",
    ai: true,
    icon: FlaskConical,
    children: [
      { label: "與 AI 設計策略", href: "/strategy-lab", icon: MessageSquareCode },
      // 策略庫 saved strategies are injected dynamically under this leaf (see StrategyLibraryTree).
      { label: "策略庫", href: "/strategy-lab#library", icon: Library },
    ],
  },
  {
    label: "交易室",
    icon: Network,
    children: [
      { label: "模擬回測", href: "/trading-room/backtest", icon: History },
      { label: "工作流", href: "/trading-room/workflow", icon: Workflow },
    ],
  },
  { label: "市場", href: "/market", icon: CandlestickChart },
  { label: "投組", href: "/portfolio", icon: Wallet },
  {
    label: "工具",
    icon: Wrench,
    children: [
      { label: "排程", href: "/schedules", icon: CalendarClock },
      { label: "通知", href: "/notifications", icon: Bell },
      { label: "匯入", href: "/data-import", icon: Upload },
    ],
  },
];
```

- [ ] **Step 2: 改寫 `components/shell/TreeNav.tsx` — 渲染 icon + 中文(移除英文 subtitle)**

完整取代檔案內容:
```tsx
"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV, type NavItem } from "@/lib/nav";
import { StrategyLibraryTree } from "./StrategyLibraryTree";

function isActive(pathname: string, href?: string) {
  return !!href && (pathname === href || pathname.startsWith(href + "/"));
}

export function TreeNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav className="flex-1 overflow-y-auto p-2 text-sm">
      {NAV.map((item) => (
        <TreeRow key={item.label} item={item} pathname={pathname} onNavigate={onNavigate} />
      ))}
    </nav>
  );
}

function TreeRow({ item, pathname, onNavigate }: { item: NavItem; pathname: string; onNavigate?: () => void }) {
  const active = isActive(pathname, item.href);
  const Icon = item.icon;
  return (
    <div>
      <Link
        href={item.href ?? "#"}
        onClick={onNavigate}
        className={`flex items-center gap-2.5 rounded-md border-l-2 px-3 py-2 ${
          active ? "border-accent bg-accent-dim text-text" : "border-transparent text-muted hover:bg-surface-2"
        }`}
      >
        {Icon && <Icon size={16} strokeWidth={1.75} className={item.ai ? "text-accent" : "text-faint"} aria-hidden />}
        <span className="nav-label font-display font-semibold leading-tight">{item.label}</span>
      </Link>
      {item.children && (
        <div className="ml-3 border-l border-border pl-1">
          {item.children.map((leaf) => {
            const la = isActive(pathname, leaf.href);
            const isLibrary = leaf.href === "/strategy-lab#library";
            const LeafIcon = leaf.icon;
            return (
              <div key={leaf.href}>
                <Link
                  href={leaf.href}
                  onClick={onNavigate}
                  className={`flex items-center gap-2.5 rounded-md border-l-2 px-3 py-2 text-[13px] ${
                    la ? `${leaf.live ? "border-live text-live" : "border-accent text-text"} bg-accent-dim`
                       : "border-transparent text-muted hover:bg-surface-2"
                  }`}
                >
                  {LeafIcon && <LeafIcon size={15} strokeWidth={1.75} className={leaf.live ? "text-live" : "text-faint"} aria-hidden />}
                  <span className="nav-label leading-tight">{leaf.label}</span>
                </Link>
                {isLibrary && <StrategyLibraryTree onNavigate={onNavigate} />}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: 型別檢查**

Run(於 `frontend/`): `npx tsc --noEmit`
Expected: 無錯誤(特別確認 `nav.ts` 不再有未使用的 `subtitle`、`TreeNav` icon 型別正確)。

- [ ] **Step 4: 更新 `DESIGN.md` — Navigation 區的 ASCII tree 改成中文+icon 並加 Decisions Log**

在 `### Navigation — Left Tree Menu` 區塊,把現有的雙語 ASCII tree(```AI Trade Flow. … └─ 通知 Notifications```)取代為:
```
AI Trade Flow.
├─ 🧪 策略室
│  ├─ 與 AI 設計策略
│  └─ 策略庫
│     └─ … (saved strategies)
├─ 🔀 交易室
│  ├─ 模擬回測
│  └─ 工作流
├─ 📈 市場
├─ 👛 投組
└─ 🔧 工具
   ├─ 排程
   ├─ 通知
   └─ 匯入
```
並在該段落末新增一句:「label 僅中文;每項以 lucide icon 前綴(策略室=FlaskConical、交易室=Network、市場=CandlestickChart、投組=Wallet、工具=Wrench;leaf 各有對應 icon)。AI leaf 的 icon 用 `--accent`,其餘用 `--text-faint`,active/live 色彩規則不變。」

在 `## Decisions Log` 表格新增一列:
```
| 2026-06-22 | 選單改純中文 label + lucide icon(移除英文 subtitle) | 中英並陳視覺雜訊大;icon + 中文更貼近專業終端機。使用者核准的偏離。 |
```

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/nav.ts frontend/components/shell/TreeNav.tsx DESIGN.md
git commit -m "feat(nav): Chinese-only labels with lucide icons"
```

- [ ] **Step 6: 瀏覽器檢查點(P1 驗收)**

用 `run-app` skill 啟動,開 `http://localhost:3000`,截圖左側選單。
Expected:每項有 icon + 中文、無英文行;策略室 icon 為 cyan;active 項仍有 cyan 左邊框 + tint。

---

## Phase 2 — 圖表引擎(`chart-helpers` + `PriceChart`)

### Task 3: chart-helpers 指標數學 + 型別

**Files:**
- Modify: `frontend/lib/chart-helpers.ts`
- Test(throwaway): `frontend/scripts/indicators.check.ts`(驗證後刪除,不留 repo — 專案無前端 test runner)

**Interfaces:**
- Produces:
  - `sma(values: number[], period: number): (number｜null)[]`
  - `ema(values: number[], period: number): (number｜null)[]`
  - `rsi(values: number[], period?: number): (number｜null)[]`
  - `macd(values: number[], fast?: number, slow?: number, signal?: number): { macd:(number｜null)[]; signal:(number｜null)[]; hist:(number｜null)[] }`
  - `bollinger(values: number[], period?: number, mult?: number): { upper:(number｜null)[]; mid:(number｜null)[]; lower:(number｜null)[] }`
  - `export interface IndicatorConfig { id:string; type:"sma"|"ema"|"bollinger"; period:number; color?:string }`
  - `export interface OscillatorConfig { id:string; type:"rsi"|"macd"; period?:number }`

- [ ] **Step 1: 寫驗證腳本(會先失敗,因函式尚未存在)**

建立 `frontend/scripts/indicators.check.ts`:
```ts
import { sma, ema, rsi, macd, bollinger } from "../lib/chart-helpers";

const approx = (a: number | null, b: number, eps = 1e-6) =>
  a != null && Math.abs(a - b) < eps;
let failed = 0;
const check = (name: string, ok: boolean) => {
  if (!ok) { failed++; console.error("FAIL:", name); } else console.log("ok:", name);
};

// SMA
const s = sma([1, 2, 3, 4, 5], 3);
check("sma warmup null", s[0] === null && s[1] === null);
check("sma[2]==2", approx(s[2], 2));
check("sma[4]==4", approx(s[4], 4));

// EMA: period 3 over [1,2,3,4,5]; seed=SMA(1..3)=2; k=0.5
// ema[3]=4*.5+2*.5=3 ; ema[4]=5*.5+3*.5=4
const e = ema([1, 2, 3, 4, 5], 3);
check("ema warmup null", e[0] === null && e[1] === null);
check("ema seed==2", approx(e[2], 2));
check("ema[3]==3", approx(e[3], 3));
check("ema[4]==4", approx(e[4], 4));

// RSI: strictly rising series → RSI = 100 (no losses)
const r = rsi([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16], 14);
check("rsi warmup null", r[13] === null);
check("rsi all-gains==100", approx(r[14], 100) && approx(r[15], 100));
check("rsi in range", r.filter((x): x is number => x != null).every((x) => x >= 0 && x <= 100));

// MACD: macd line == emaFast - emaSlow where both defined
const px = Array.from({ length: 60 }, (_, i) => 100 + Math.sin(i / 5) * 5 + i * 0.2);
const m = macd(px);
const ef = ema(px, 12), es = ema(px, 26);
check("macd==emaFast-emaSlow", approx(m.macd[40]!, ef[40]! - es[40]!));
check("macd hist==macd-signal", m.hist[50] != null && m.signal[50] != null &&
  approx(m.hist[50]!, m.macd[50]! - m.signal[50]!));

// Bollinger: mid==sma; upper/lower symmetric around mid
const b = bollinger(px, 20, 2);
check("bb mid==sma", approx(b.mid[30]!, sma(px, 20)[30]!));
check("bb symmetric", approx((b.upper[30]! + b.lower[30]!) / 2, b.mid[30]!));
check("bb upper>mid>lower", b.upper[30]! > b.mid[30]! && b.mid[30]! > b.lower[30]!);

console.log(failed === 0 ? "\nALL PASS" : `\n${failed} FAILED`);
process.exit(failed === 0 ? 0 : 1);
```

- [ ] **Step 2: 跑驗證,確認失敗(函式未定義)**

Run(於 `frontend/`): `npx -y tsx scripts/indicators.check.ts`
Expected: 編譯/執行失敗(`chart-helpers` 尚未 export `ema/rsi/macd/bollinger`)。
（若 `npx tsx` 無法下載——離線——改用瀏覽器 Step 5 的數值交叉核對作為替代驗證,並在計畫筆記註明。)

- [ ] **Step 3: 在 `lib/chart-helpers.ts` 新增型別與純函式**

在既有 `Overlay` interface 後新增型別:
```ts
export interface IndicatorConfig {
  id: string;
  type: "sma" | "ema" | "bollinger";
  period: number;
  color?: string; // CSS var (e.g. "--up") or hex; default neutral
}
export interface OscillatorConfig {
  id: string;
  type: "rsi" | "macd";
  period?: number; // rsi window (default 14)
}
```
在檔案末新增純函式:
```ts
// ── 技術指標(純函式,前端計算)。暖機期不足以計算時填 null(fail loud:不偽造數值)。──
export function sma(values: number[], period: number): (number | null)[] {
  const out: (number | null)[] = [];
  let sum = 0;
  for (let i = 0; i < values.length; i++) {
    sum += values[i];
    if (i >= period) sum -= values[i - period];
    out.push(i >= period - 1 ? sum / period : null);
  }
  return out;
}

// EMA:以前 period 根的 SMA 作種子,其後用遞迴 k=2/(period+1)。
export function ema(values: number[], period: number): (number | null)[] {
  const out: (number | null)[] = new Array(values.length).fill(null);
  if (period <= 0 || values.length < period) return out;
  const k = 2 / (period + 1);
  let prev = 0;
  for (let i = 0; i < period; i++) prev += values[i];
  prev /= period;
  out[period - 1] = prev;
  for (let i = period; i < values.length; i++) {
    prev = values[i] * k + prev * (1 - k);
    out[i] = prev;
  }
  return out;
}

// RSI:Wilder 平滑。第一個值落在索引 period。
export function rsi(values: number[], period = 14): (number | null)[] {
  const out: (number | null)[] = new Array(values.length).fill(null);
  if (values.length <= period) return out;
  let gain = 0, loss = 0;
  for (let i = 1; i <= period; i++) {
    const d = values[i] - values[i - 1];
    if (d >= 0) gain += d; else loss -= d;
  }
  let avgGain = gain / period, avgLoss = loss / period;
  out[period] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
  for (let i = period + 1; i < values.length; i++) {
    const d = values[i] - values[i - 1];
    const g = d >= 0 ? d : 0;
    const l = d < 0 ? -d : 0;
    avgGain = (avgGain * (period - 1) + g) / period;
    avgLoss = (avgLoss * (period - 1) + l) / period;
    out[i] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
  }
  return out;
}

// MACD:macd = ema(fast) − ema(slow);signal = macd 的 ema(signal);hist = macd − signal。
export function macd(
  values: number[], fast = 12, slow = 26, signalPeriod = 9
): { macd: (number | null)[]; signal: (number | null)[]; hist: (number | null)[] } {
  const emaFast = ema(values, fast);
  const emaSlow = ema(values, slow);
  const macdLine: (number | null)[] = values.map((_, i) =>
    emaFast[i] != null && emaSlow[i] != null ? emaFast[i]! - emaSlow[i]! : null
  );
  // 對「已定義的 macd 段」算 EMA,再映射回原索引。
  const defined: number[] = macdLine.filter((v): v is number => v != null);
  const sigDefined = ema(defined, signalPeriod);
  const signal: (number | null)[] = new Array(values.length).fill(null);
  let j = 0;
  for (let i = 0; i < values.length; i++) {
    if (macdLine[i] != null) { signal[i] = sigDefined[j]; j++; }
  }
  const hist: (number | null)[] = values.map((_, i) =>
    macdLine[i] != null && signal[i] != null ? (macdLine[i] as number) - (signal[i] as number) : null
  );
  return { macd: macdLine, signal, hist };
}

// 布林通道:mid = SMA(period);upper/lower = mid ± mult × 母體標準差。
export function bollinger(
  values: number[], period = 20, mult = 2
): { upper: (number | null)[]; mid: (number | null)[]; lower: (number | null)[] } {
  const mid = sma(values, period);
  const upper: (number | null)[] = new Array(values.length).fill(null);
  const lower: (number | null)[] = new Array(values.length).fill(null);
  for (let i = period - 1; i < values.length; i++) {
    let sum = 0;
    for (let k = i - period + 1; k <= i; k++) sum += values[k];
    const mean = sum / period;
    let varSum = 0;
    for (let k = i - period + 1; k <= i; k++) varSum += (values[k] - mean) ** 2;
    const sd = Math.sqrt(varSum / period);
    upper[i] = mean + mult * sd;
    lower[i] = mean - mult * sd;
  }
  return { upper, mid, lower };
}
```

- [ ] **Step 4: 跑驗證,確認通過**

Run(於 `frontend/`): `npx -y tsx scripts/indicators.check.ts`
Expected: 輸出多行 `ok:` 與最後 `ALL PASS`,exit 0。

- [ ] **Step 5: 刪除驗證腳本 + 型別檢查**

Run(於 `frontend/`):
```bash
rm scripts/indicators.check.ts
rmdir scripts 2>/dev/null || true
npx tsc --noEmit
```
Expected: `tsc` 乾淨(scripts 已刪不影響;chart-helpers 新 export 型別正確)。

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/chart-helpers.ts
git commit -m "feat(chart): add ema/rsi/macd/bollinger indicator math + config types"
```

---

### Task 4: PriceChart 線圖類型 + 對數座標

**Files:**
- Modify: `frontend/components/PriceChart.tsx`

**Interfaces:**
- Consumes: 既有 `toCandlestickData`(chart-helpers)。
- Produces: `PriceChartProps` 新增 `chartType?: "candles" | "line" | "area"`(預設 `"candles"`)、`logScale?: boolean`(預設 false)。

- [ ] **Step 1: 擴充 props 並依 chartType 建立主序列**

在 `PriceChartProps` 介面加入:
```ts
  chartType?: "candles" | "line" | "area";
  logScale?: boolean;
```
在 import 行加入 `PriceScaleMode`:
```ts
import { createChart, ColorType, PriceScaleMode, type IChartApi, type ISeriesApi, type UTCTimestamp } from "lightweight-charts";
```
函式簽名加上預設值:
```tsx
export function PriceChart({
  candles, height = 360, markers, overlays, volume = true, live, onCrosshairMove,
  chartType = "candles", logScale = false,
}: PriceChartProps) {
```
在建圖 effect 內,把固定建立 candlestick 改成依 `chartType` 建立,並把 ref 型別放寬:
```tsx
// 主序列 ref(可能是 candlestick / line / area)
const mainSeriesRef = useRef<ISeriesApi<"Candlestick" | "Line" | "Area"> | null>(null);
```
（移除舊的 `candleSeriesRef`,全檔以 `mainSeriesRef` 取代。）建圖時:
```tsx
const chart = createChart(el, {
  layout: { background: { type: ColorType.Solid, color: bg }, textColor: text },
  grid: { vertLines: { color: grid }, horzLines: { color: grid } },
  width: el.clientWidth, height,
  timeScale: { timeVisible: true },
  crosshair: { mode: 1 },
  rightPriceScale: { mode: logScale ? PriceScaleMode.Logarithmic : PriceScaleMode.Normal },
});
let main: ISeriesApi<"Candlestick" | "Line" | "Area">;
if (chartType === "line") {
  main = chart.addLineSeries({ color: up, lineWidth: 2 });
} else if (chartType === "area") {
  main = chart.addAreaSeries({ lineColor: up, topColor: up, bottomColor: "rgba(0,0,0,0)", lineWidth: 2 });
} else {
  main = chart.addCandlestickSeries({
    upColor: up, downColor: down, borderVisible: false, wickUpColor: up, wickDownColor: down,
  });
}
mainSeriesRef.current = main;
```
把建圖 effect 的依賴改為 `[height, volume, onCrosshairMove, chartType, logScale]`(類型/座標改變需重建)。

- [ ] **Step 2: setData 依 chartType 餵不同形狀**

把資料更新 effect 改為:
```tsx
useEffect(() => {
  const cs = mainSeriesRef.current, chart = chartRef.current;
  if (!cs || !chart) return;
  const up = cssVar("--up", "#34D399"), down = cssVar("--down", "#F87171");
  if (chartType === "candles") {
    (cs as ISeriesApi<"Candlestick">).setData(toCandlestickData(candles));
  } else {
    const line = candles.map((c) => ({
      time: Math.floor(new Date(c.timestamp).getTime() / 1000) as UTCTimestamp,
      value: c.close,
    }));
    (cs as ISeriesApi<"Line" | "Area">).setData(line);
  }
  if (volumeSeriesRef.current) volumeSeriesRef.current.setData(toVolumeData(candles, up, down));
  chart.timeScale().fitContent();
}, [candles, chartType]);
```
同步把 markers effect、live update effect、crosshair effect 內所有 `candleSeriesRef` 改成 `mainSeriesRef`。

- [ ] **Step 3: 型別檢查**

Run(於 `frontend/`): `npx tsc --noEmit`
Expected: 乾淨(注意 line/area 的 `setData` 形狀與 cast)。

- [ ] **Step 4: Commit**

```bash
git add frontend/components/PriceChart.tsx
git commit -m "feat(chart): chart-type (candles/line/area) + log-scale toggle in PriceChart"
```

---

### Task 5: PriceChart 主圖疊加(MA/EMA/布林)

**Files:**
- Modify: `frontend/components/PriceChart.tsx`

**Interfaces:**
- Consumes: `sma/ema/bollinger`、`IndicatorConfig`(Task 3)。
- Produces: `PriceChartProps` 新增 `indicators?: IndicatorConfig[]`。沿用既有 `overlays`(向下相容,內部轉為等效 indicator)。

- [ ] **Step 1: 移除 PriceChart 內建 `sma`,改用 chart-helpers**

刪除 `PriceChart.tsx` 內的本地 `function sma(...)`,並在 import 補上:
```ts
import {
  toCandlestickData, toVolumeData, markerToSeries,
  sma, ema, bollinger,
  type ChartMarker, type Overlay, type LiveConfig, type OHLCV, type IndicatorConfig,
} from "@/lib/chart-helpers";
```

- [ ] **Step 2: 加 `indicators` prop 並以單一 effect 繪製主圖疊加**

`PriceChartProps` 加:
```ts
  indicators?: IndicatorConfig[];
```
函式簽名加 `indicators`。把既有「疊加均線」effect 取代為下列(同時涵蓋舊 `overlays` → 轉等效 indicator,DRY):
```tsx
useEffect(() => {
  const chart = chartRef.current;
  if (!chart) return;
  const times = candles.map((c) => Math.floor(new Date(c.timestamp).getTime() / 1000) as UTCTimestamp);
  const closes = candles.map((c) => c.close);
  const toLine = (vals: (number | null)[]) =>
    times.map((t, i) => (vals[i] == null ? null : { time: t, value: vals[i]! }))
         .filter(Boolean) as { time: UTCTimestamp; value: number }[];

  // 舊 overlays(sma/ema)轉成 IndicatorConfig,維持向下相容。
  const legacy: IndicatorConfig[] = (overlays ?? []).map((o) => ({
    id: o.id, type: o.type, period: o.period, color: o.color,
  }));
  const all = [...legacy, ...(indicators ?? [])];

  const series = all.flatMap((cfg) => {
    const color = cfg.color
      ? (cfg.color.startsWith("--") ? cssVar(cfg.color, "#8A9099") : cfg.color)
      : cssVar("--text-muted", "#8A9099");
    if (cfg.type === "bollinger") {
      const bb = bollinger(closes, cfg.period, 2);
      const mid = chart.addLineSeries({ color, lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
      const upper = chart.addLineSeries({ color, lineWidth: 1, lineStyle: 2, priceLineVisible: false, lastValueVisible: false });
      const lower = chart.addLineSeries({ color, lineWidth: 1, lineStyle: 2, priceLineVisible: false, lastValueVisible: false });
      mid.setData(toLine(bb.mid)); upper.setData(toLine(bb.upper)); lower.setData(toLine(bb.lower));
      return [mid, upper, lower];
    }
    const vals = cfg.type === "ema" ? ema(closes, cfg.period) : sma(closes, cfg.period);
    const line = chart.addLineSeries({ color, lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
    line.setData(toLine(vals));
    return [line];
  });

  return () => {
    if (chartRef.current !== chart) return; // chart 已 dispose 時不可 removeSeries
    series.forEach((s) => chart.removeSeries(s));
  };
}, [overlays, indicators, candles]);
```

- [ ] **Step 3: 型別檢查**

Run(於 `frontend/`): `npx tsc --noEmit`
Expected: 乾淨。

- [ ] **Step 4: Commit**

```bash
git add frontend/components/PriceChart.tsx
git commit -m "feat(chart): MA/EMA/Bollinger overlays on price pane via chart-helpers"
```

---

### Task 6: PriceChart RSI / MACD 副圖(堆疊 + 時間軸同步)

**Files:**
- Modify: `frontend/components/PriceChart.tsx`

**Interfaces:**
- Consumes: `rsi/macd`、`OscillatorConfig`(Task 3)。
- Produces: `PriceChartProps` 新增 `oscillators?: OscillatorConfig[]`。

- [ ] **Step 1: 加 prop + 副圖容器**

`PriceChartProps` 加:
```ts
  oscillators?: OscillatorConfig[];
```
函式簽名加 `oscillators = []`(預設空陣列)。在 component 內加副圖容器 ref:
```tsx
const oscRefs = useRef<Record<string, HTMLDivElement | null>>({});
```
在 return 的 `<div ref={containerRef} className="w-full" />` 之後,加入副圖容器(各固定高度):
```tsx
{(oscillators ?? []).map((o) => (
  <div key={o.id} className="relative mt-1">
    <span className="absolute left-2 top-1 z-10 text-[10px] uppercase tracking-wide text-faint">
      {o.type === "rsi" ? `RSI ${o.period ?? 14}` : "MACD 12·26·9"}
    </span>
    <div ref={(el) => { oscRefs.current[o.id] = el; }} className="w-full" />
  </div>
))}
```

- [ ] **Step 2: 建立副圖、繪資料、雙向同步時間軸**

新增一個 effect(放在 live 輪詢 effect 之前):
```tsx
useEffect(() => {
  const mainChart = chartRef.current;
  if (!mainChart || !oscillators?.length) return;
  const grid = cssVar("--border", "#1f1f1f");
  const text = cssVar("--muted", "#8A9099");
  const bg = cssVar("--bg", "#0A0B0D");
  const accent = cssVar("--accent", "#22D3EE");
  const upC = cssVar("--up", "#34D399"), downC = cssVar("--down", "#F87171");
  const times = candles.map((c) => Math.floor(new Date(c.timestamp).getTime() / 1000) as UTCTimestamp);
  const closes = candles.map((c) => c.close);
  const toLine = (vals: (number | null)[]) =>
    times.map((t, i) => (vals[i] == null ? null : { time: t, value: vals[i]! }))
         .filter(Boolean) as { time: UTCTimestamp; value: number }[];

  const charts: IChartApi[] = [];
  let syncing = false; // 防雙向遞迴

  for (const o of oscillators) {
    const el = oscRefs.current[o.id];
    if (!el) continue;
    const h = o.type === "rsi" ? 110 : 120;
    const c = createChart(el, {
      layout: { background: { type: ColorType.Solid, color: bg }, textColor: text },
      grid: { vertLines: { color: grid }, horzLines: { color: grid } },
      width: el.clientWidth, height: h,
      timeScale: { timeVisible: true, visible: false },
      crosshair: { mode: 1 },
    });
    if (o.type === "rsi") {
      const line = c.addLineSeries({ color: accent, lineWidth: 1 });
      line.setData(toLine(rsi(closes, o.period ?? 14)));
      // 30/70 參考線
      line.createPriceLine({ price: 70, color: grid, lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: "70" });
      line.createPriceLine({ price: 30, color: grid, lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: "30" });
    } else {
      const m = macd(closes);
      const hist = c.addHistogramSeries({ priceLineVisible: false });
      hist.setData(times.map((t, i) => (m.hist[i] == null ? null : {
        time: t, value: m.hist[i]!, color: (m.hist[i] as number) >= 0 ? upC : downC,
      })).filter(Boolean) as { time: UTCTimestamp; value: number; color: string }[]);
      const macdLine = c.addLineSeries({ color: accent, lineWidth: 1 });
      const sigLine = c.addLineSeries({ color: text, lineWidth: 1 });
      macdLine.setData(toLine(m.macd));
      sigLine.setData(toLine(m.signal));
    }
    const ro = new ResizeObserver(() => c.applyOptions({ width: el.clientWidth }));
    ro.observe(el);
    (c as unknown as { _ro?: ResizeObserver })._ro = ro;
    charts.push(c);
  }

  // 雙向同步:主圖 ↔ 每張副圖
  const allCharts = [mainChart, ...charts];
  const unsub: Array<() => void> = [];
  for (const src of allCharts) {
    const handler = (range: unknown) => {
      if (syncing || range == null) return;
      syncing = true;
      for (const dst of allCharts) {
        if (dst !== src) dst.timeScale().setVisibleLogicalRange(range as never);
      }
      syncing = false;
    };
    src.timeScale().subscribeVisibleLogicalRangeChange(handler);
    unsub.push(() => src.timeScale().unsubscribeVisibleLogicalRangeChange(handler));
  }

  return () => {
    unsub.forEach((u) => u());
    charts.forEach((c) => {
      const ro = (c as unknown as { _ro?: ResizeObserver })._ro;
      ro?.disconnect();
      c.remove();
    });
  };
}, [oscillators, candles]);
```

- [ ] **Step 3: 型別檢查**

Run(於 `frontend/`): `npx tsc --noEmit`
Expected: 乾淨(留意 `setVisibleLogicalRange` 的型別 cast `as never`、histogram data cast)。

- [ ] **Step 4: Commit**

```bash
git add frontend/components/PriceChart.tsx
git commit -m "feat(chart): synced RSI & MACD oscillator sub-panes (lightweight-charts v4)"
```

---

### Task 7: PriceChart 十字準星讀數 + 成交量開關 + 全螢幕

**Files:**
- Modify: `frontend/components/PriceChart.tsx`

**Interfaces:**
- Produces: `PriceChartProps` 新增 `showLegend?: boolean`(預設 true);成交量沿用既有 `volume` prop;全螢幕為內部 UI 狀態(無新 prop)。

- [ ] **Step 1: 內部 OHLC 讀數(legend)— 訂閱 crosshair**

在 component 內新增狀態:
```tsx
const [legend, setLegend] = useState<OHLCV | null>(null);
```
`PriceChartProps` 加 `showLegend?: boolean`,簽名 `showLegend = true`。在建圖 effect 的 crosshair 訂閱區塊,即使外部沒給 `onCrosshairMove` 也要更新內部 legend:
```tsx
chart.subscribeCrosshairMove((param) => {
  const bar = param.seriesData.get(main) as
    | { open: number; high: number; low: number; close: number; value?: number } | undefined;
  const v = volumeSeriesRef.current
    ? (param.seriesData.get(volumeSeriesRef.current) as { value: number } | undefined)
    : undefined;
  if (!bar || param.time == null) { setLegend(null); onCrosshairMove?.(null); return; }
  const ohlcv: OHLCV = {
    time: param.time as number,
    open: bar.open ?? bar.value ?? 0, high: bar.high ?? bar.value ?? 0,
    low: bar.low ?? bar.value ?? 0, close: bar.close ?? bar.value ?? 0,
    volume: v?.value ?? 0,
  };
  setLegend(ohlcv);
  onCrosshairMove?.(ohlcv);
});
```
（注意:`onCrosshairMove` 仍在依賴陣列,但現在 crosshair 永遠訂閱;移除原本 `if (onCrosshairMove)` 的條件包裹。）

- [ ] **Step 2: 在圖上渲染 legend(mono、漲跌色走 token)**

在 return 內、主圖 `containerRef` 之前加入:
```tsx
{showLegend && legend && (
  <div className="num pointer-events-none absolute left-2 top-2 z-10 flex gap-2 rounded-md border border-border bg-surface-2/90 px-2 py-1 text-[11px]">
    <span className="text-faint">O <span className="text-text">{legend.open}</span></span>
    <span className="text-faint">H <span className="text-text">{legend.high}</span></span>
    <span className="text-faint">L <span className="text-text">{legend.low}</span></span>
    <span className="text-faint">C <span className={legend.close >= legend.open ? "text-up" : "text-down"}>{legend.close}</span></span>
    <span className="text-faint">Vol <span className="text-text">{legend.volume.toLocaleString()}</span></span>
  </div>
)}
```

- [ ] **Step 3: 全螢幕切換**

在最外層 wrapper div 加 ref 與按鈕:
```tsx
const wrapRef = useRef<HTMLDivElement>(null);
const toggleFullscreen = () => {
  const el = wrapRef.current;
  if (!el) return;
  if (document.fullscreenElement) document.exitFullscreen();
  else el.requestFullscreen?.();
};
```
最外層 `<div className="relative w-full">` 改為 `<div ref={wrapRef} className="relative w-full bg-bg">`,並在右上加按鈕(用 lucide,避免新文案):
```tsx
<button
  onClick={toggleFullscreen}
  className="absolute right-2 top-2 z-20 rounded-md border border-border bg-surface-2 p-1 text-muted hover:text-text"
  aria-label="全螢幕"
>
  <Maximize2 size={14} />
</button>
```
import 補:`import { Maximize2 } from "lucide-react";`。

- [ ] **Step 4: 型別檢查**

Run(於 `frontend/`): `npx tsc --noEmit`
Expected: 乾淨。

- [ ] **Step 5: Commit**

```bash
git add frontend/components/PriceChart.tsx
git commit -m "feat(chart): crosshair OHLCV legend, volume toggle, fullscreen"
```

---

## Phase 3 — 控制接線(`labels` + `MarketPanel`)

### Task 8: 新增市場頁控制文案

**Files:**
- Modify: `frontend/lib/labels.ts`

**Interfaces:**
- Produces: `L.market` 新增 key:`indicators`、`bars`、`chartType`、`candles`、`line`、`area`、`logScale`、`ma`、`ema`、`boll`、`rsi`、`macd`、`volume`。

- [ ] **Step 1: 在 `L.market` 物件補上控制文案**

於 `L.market` 內(`loadingCandles` 之後)新增:
```ts
    indicators: "指標",
    bars: "根數",
    chartType: "圖型",
    candlesType: "K 線",
    lineType: "折線",
    areaType: "區域",
    logScale: "對數",
    maLabel: "MA",
    emaLabel: "EMA",
    bollLabel: "布林",
    rsiLabel: "RSI",
    macdLabel: "MACD",
    volumeLabel: "量",
```

- [ ] **Step 2: 型別檢查**

Run(於 `frontend/`): `npx tsc --noEmit`
Expected: 乾淨。

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/labels.ts
git commit -m "feat(i18n): market chart control labels"
```

---

### Task 9: MarketPanel 指標工具列 + timeframe/根數擴充 + 接線

**Files:**
- Modify: `frontend/components/MarketPanel.tsx`

**Interfaces:**
- Consumes: `IndicatorConfig`/`OscillatorConfig`(chart-helpers)、`PriceChart` 新 props(Task 4–7)、`L.market`(Task 8)。

- [ ] **Step 1: 擴充常數與狀態**

把 `TIMEFRAMES` 改為:
```ts
const TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d", "1w"];
const BAR_COUNTS = [200, 500, 1000];
```
import 補:
```ts
import type { IndicatorConfig, OscillatorConfig } from "@/lib/chart-helpers";
```
在 `MarketPanel` 內新增狀態(放在既有 `useState` 群之後):
```tsx
const [bars, setBars] = useState(200);
const [chartType, setChartType] = useState<"candles" | "line" | "area">("candles");
const [logScale, setLogScale] = useState(false);
const [showVolume, setShowVolume] = useState(true);
// 指標開關
const [maOn, setMaOn] = useState(true);   // 預設開 MA20/MA50
const [emaOn, setEmaOn] = useState(false);
const [bollOn, setBollOn] = useState(false);
const [rsiOn, setRsiOn] = useState(false);
const [macdOn, setMacdOn] = useState(false);
```

- [ ] **Step 2: 用 `bars` 驅動 ohlcv 查詢,組裝 indicator/oscillator 設定**

把 candles query 的 `queryKey`/`queryFn` 改為帶 `bars`:
```tsx
const candles = useQuery({
  queryKey: ["ohlcv", symbol, timeframe, market, bars],
  queryFn: () => api.ohlcv(symbol, timeframe, bars, market),
  retry: false,
});
```
在 `return` 前組裝設定(用 DESIGN.md 中性色;MA20/50 用兩個中性色避免搶 accent):
```tsx
const indicators: IndicatorConfig[] = [
  ...(maOn ? [
    { id: "ma20", type: "sma" as const, period: 20, color: "--text-muted" },
    { id: "ma50", type: "sma" as const, period: 50, color: "--text-faint" },
  ] : []),
  ...(emaOn ? [{ id: "ema20", type: "ema" as const, period: 20, color: "--warning" }] : []),
  ...(bollOn ? [{ id: "bb", type: "bollinger" as const, period: 20, color: "--border-strong" }] : []),
];
const oscillators: OscillatorConfig[] = [
  ...(rsiOn ? [{ id: "rsi", type: "rsi" as const, period: 14 }] : []),
  ...(macdOn ? [{ id: "macd", type: "macd" as const }] : []),
];
```

- [ ] **Step 3: 加指標工具列 UI(緊湊 toggle 列)**

在現有控制列 `<div className="mb-3 flex flex-wrap items-center gap-2">…</div>` 之後、stats 區之前,新增第二列工具列:
```tsx
<div className="mb-3 flex flex-wrap items-center gap-1.5 text-[12px]">
  <select value={chartType} onChange={(e) => setChartType(e.target.value as typeof chartType)}
    className="rounded-md bg-surface-2 px-2 py-1">
    <option value="candles">{L.market.candlesType}</option>
    <option value="line">{L.market.lineType}</option>
    <option value="area">{L.market.areaType}</option>
  </select>
  <select value={bars} onChange={(e) => setBars(Number(e.target.value))}
    className="rounded-md bg-surface-2 px-2 py-1">
    {BAR_COUNTS.map((b) => <option key={b} value={b}>{b} {L.backtest.barsSuffix}</option>)}
  </select>
  <span className="ml-1 text-faint">{L.market.indicators}:</span>
  {([
    ["MA", maOn, setMaOn], ["EMA", emaOn, setEmaOn], ["BOLL", bollOn, setBollOn],
    ["RSI", rsiOn, setRsiOn], ["MACD", macdOn, setMacdOn],
  ] as const).map(([name, on, set]) => (
    <button key={name} onClick={() => set((v) => !v)}
      className={`rounded-md border px-2 py-1 ${on ? "border-accent/40 bg-accent-dim text-text" : "border-border bg-surface-2 text-muted hover:text-text"}`}>
      {name}
    </button>
  ))}
  <button onClick={() => setLogScale((v) => !v)}
    className={`rounded-md border px-2 py-1 ${logScale ? "border-accent/40 bg-accent-dim text-text" : "border-border bg-surface-2 text-muted hover:text-text"}`}>
    {L.market.logScale}
  </button>
  <button onClick={() => setShowVolume((v) => !v)}
    className={`rounded-md border px-2 py-1 ${showVolume ? "border-accent/40 bg-accent-dim text-text" : "border-border bg-surface-2 text-muted hover:text-text"}`}>
    {L.market.volumeLabel}
  </button>
</div>
```

- [ ] **Step 4: 把新設定傳入 PriceChart**

把既有 `<PriceChart … />` 呼叫改為:
```tsx
<PriceChart
  candles={candles.data}
  live={live}
  markers={aiMarkers}
  height={360}
  chartType={chartType}
  logScale={logScale}
  volume={showVolume}
  indicators={indicators}
  oscillators={oscillators}
/>
```

- [ ] **Step 5: 型別檢查 + build**

Run(於 `frontend/`):
```bash
npx tsc --noEmit
npm run build
```
Expected: 兩者皆成功。

- [ ] **Step 6: Commit**

```bash
git add frontend/components/MarketPanel.tsx
git commit -m "feat(market): indicator toolbar, timeframe/bars expansion, wire pro chart props"
```

- [ ] **Step 7: 瀏覽器檢查點(P2+P3 驗收)**

用 `run-app` skill 啟動,開 `http://localhost:3000/market?symbol=BTC/USDT&timeframe=1h&market=crypto`。逐項截圖驗證:
1. 開 MA/EMA → 主圖出現均線(非 cyan)。
2. 開 BOLL → 出現上中下通道。
3. 開 RSI → 下方出現 RSI 副圖含 30/70 線,縮放主圖時副圖時間軸同步。
4. 開 MACD → 出現 MACD 快慢線 + 正負柱(柱色走 `--up/--down`)。
5. 移動游標 → 左上 OHLCV 讀數列更新,close 漲跌色正確。
6. 切折線/區域、切對數座標、關成交量、全螢幕 → 皆正常。
7. 切 `market=tw_stock`(台股)→ `data-market="tw"` 漲跌色翻轉未被破壞;AI 訊號標記仍為 cyan。
Expected:全部符合;`console` 無 "Value is undefined" 等錯誤。

---

## Self-Review

**1. Spec coverage（逐項對照 spec)**
- 選單中文+icon+lucide+DESIGN.md → Task 1–2 ✅
- chart-helpers ema/rsi/macd/bollinger + 測試 → Task 3 ✅
- 線圖類型 / 對數 → Task 4 ✅
- 主圖疊加 MA/EMA/布林 → Task 5 ✅
- RSI/MACD 副圖(v4 堆疊同步)→ Task 6 ✅
- 十字準星讀數 / 成交量開關 / 全螢幕 → Task 7 ✅
- timeframe(1m–1w)/ 根數(200/500/1000)/ 指標工具列 / 接線 → Task 8–9 ✅
- fail-loud(暖機 null)、accent 紀律、`--up/--down` token、台股翻轉 → Global Constraints + Task 9 Step 7 驗證 ✅
- 不做清單(繪圖/多標的/replay/v5/後端 API)→ 未出現於任何 Task ✅

**2. Placeholder scan:** 無 TBD/TODO;每個程式碼步驟皆附完整程式碼。

**3. Type consistency:**
- `IndicatorConfig`(id/type/period/color)、`OscillatorConfig`(id/type/period?)於 Task 3 定義,Task 5/6/9 一致使用。
- `sma/ema/rsi/macd/bollinger` 簽名於 Task 3 固定,Task 5/6 依此呼叫(`macd()` 回傳 `{macd,signal,hist}`、`bollinger()` 回傳 `{upper,mid,lower}`)。
- `PriceChart` 主序列 ref 一律 `mainSeriesRef`(Task 4 起全檔替換 `candleSeriesRef`)。
- `OHLCV`(time/open/high/low/close/volume)沿用 chart-helpers 既有定義,Task 7 legend 一致。

**4. 注意事項(實作者必讀)**
- Task 4 起 `candleSeriesRef` 全面更名為 `mainSeriesRef`——markers/live/crosshair effect 都要一起改,否則 `tsc` 會報未定義。
- `npx tsx` 若因離線無法下載,Task 3 改以 Task 9 Step 7 的瀏覽器數值交叉核對替代,並於 commit message 註明驗證方式。
