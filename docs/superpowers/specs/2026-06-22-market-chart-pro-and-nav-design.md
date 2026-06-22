# 設計:選單中文化+icon、市場線圖專業化

> 日期:2026-06-22 · 分支:`feat/market-chart-pro-and-nav`
> 來源:使用者需求 — 「選單中英並陳看起來奇怪,改成中文+icon;以專業投資人角度繼續優化市場看線圖功能」

## 目標與成功標準

1. **選單**:左側 tree-nav 從「中英並陳」改為**純中文 label + lucide icon**,更乾淨專業。
2. **市場線圖**:以專業投資人(TradingView 等級判讀)角度,補齊技術指標與終端機操作體驗。

成功標準:
- 選單每一項有對應 icon、只顯示中文;active/live/AI 色彩規則不變。
- 市場頁可疊加 MA/EMA/布林,可開 RS/MACD 副圖,可切線圖類型、對數座標、全螢幕,十字準星有 OHLC 讀數。
- `tsc --noEmit` 乾淨、`npm run build` 通過、新指標數學有單元測試、瀏覽器實測截圖驗證。

## 範圍

### 做(In scope)
- 選單:`lib/nav.ts` 加 `icon`、`TreeNav.tsx` 改渲染、加 `lucide-react`、更新 `DESIGN.md`。
- 指標數學:`lib/chart-helpers.ts` 新增 `ema/rsi/macd/bollinger`(前端計算,沿用既有 client-side `sma` 模式)+ 單元測試。
- `PriceChart`:十字準星 OHLC 讀數、線圖類型切換(K線/折線/區域)、對數座標、主圖疊加(MA/EMA/布林)、RSI 與 MACD 副圖(v4 堆疊圖 + 時間軸同步)、成交量開關、全螢幕。
- `MarketPanel`:指標工具列(toggle + 週期)、timeframe 擴充(1m·5m·15m·1h·4h·1d·1w)、歷史根數(200/500/1000)、接上讀數。

### 不做(Out of scope,本輪 YAGNI)
- 繪圖工具(趨勢線/斐波那契)、多標的疊圖比較、K 線回放(replay)、升級 lightweight-charts v5、新增後端指標 API。

## 取捨決策

| 決策 | 選擇 | 理由 |
|------|------|------|
| 圖表庫版本 | **留在 v4.2.3** | v5 是破壞性改版,會波及 EquityChart/CandleChart/WorkflowBacktestChart;留 v4 把影響面限縮在市場線圖。 |
| 副圖(RSI/MACD) | **堆疊多張圖 + 時間軸同步** | v4 無原生 pane;標準做法是各 oscillator 一張獨立 chart,訂閱主圖 `timeScale().subscribeVisibleLogicalRangeChange` 雙向同步。 |
| 指標計算位置 | **前端計算** | 沿用 `PriceChart` 既有的 client-side `sma`;零往返、即時、不增後端表面積。數值正確性以單元測試保證。 |
| icon 來源 | **lucide-react** | 細線條符合 refined-terminal 美學、tree-shakeable、業界標準。 |
| accent 紀律 | 指標線用中性/各自色票 | DESIGN.md:cyan(`--accent`)只保留給 AI/automation。AI 訊號標記仍是唯一 cyan。 |

## 架構與單元邊界

### 1. `lib/chart-helpers.ts`(純函式層,可獨立測試)
新增與既有 `sma` 同型的純函式:
- `ema(values: number[], period): (number|null)[]`
- `rsi(values: number[], period=14): (number|null)[]`
- `macd(values, fast=12, slow=26, signal=9): { macd, signal, hist }`(各為 `(number|null)[]`)
- `bollinger(values, period=20, mult=2): { upper, mid, lower }`
依賴:無(純數值)。輸入收盤價陣列,輸出對齊長度、暖機期為 `null`。

### 2. `PriceChart`(圖表引擎,展示層)
新增 props(全部可選,預設關閉 → 不影響回測等既有呼叫端):
- `chartType?: "candles" | "line" | "area"`(預設 candles)
- `logScale?: boolean`
- `indicators?: IndicatorConfig[]`(主圖疊加:ma/ema/bollinger,帶 period/color)
- `oscillators?: OscillatorConfig[]`(副圖:rsi/macd)
- `showLegend?: boolean`(十字準星 OHLC 讀數)
- 既有 `volume`/`live`/`markers`/`overlays`/`onCrosshairMove` 維持相容。

內部:
- 副圖以 `createChart` 各建一張,固定高度(RSI≈110px、MACD≈120px),`rightPriceScale` 對齊主圖寬度;主圖與副圖互相訂閱 `subscribeVisibleLogicalRangeChange` 同步縮放/平移,並共用 crosshair。
- 全螢幕:容器層用 Fullscreen API(`requestFullscreen`),退出還原高度。
- 讀數列:沿用 `onCrosshairMove`,在圖內絕對定位 legend(mono、tabular-nums、漲跌色走 `--up/--down`)。

### 3. `MarketPanel`(控制 + 接線,容器層)
- 指標工具列:緊湊 toggle 列(MA20 / MA50 / EMA20 / BB / RSI / MACD),狀態存 component state,組成 `indicators`/`oscillators` 傳入 `PriceChart`。
- timeframe 與歷史根數改為常數陣列驅動的 select。
- 接 `onCrosshairMove` 顯示讀數(或交給 PriceChart 內建 legend,擇一,以 PriceChart 內建 legend 為準以保持自含)。

### 4. 選單
- `lib/nav.ts`:`NavItem`/`NavLeaf` 加 `icon?: LucideIcon`(或 icon 名稱字串);移除對英文 subtitle 的依賴(欄位可留作資料,但不再渲染)。
- `TreeNav.tsx`:渲染 `icon + 中文 label`(單行);父項/葉項/active/live dot 規則不變。
- `DESIGN.md`:更新 Navigation 區的 ASCII tree(中文+icon)、加一筆 Decisions Log。

## 資料流

OHLCV(`api.ohlcv`,既有)→ `MarketPanel` 持有 candles → 傳 `PriceChart` → 圖內以 `chart-helpers` 純函式由收盤價推導指標序列 → 疊加/副圖繪製。指標**不經後端**。AI 訊號維持既有 `api.aiSignal` → markers。

## 錯誤處理(fail loud)
- candles 不足以暖機(如資料筆數 < 指標 period):該指標序列前段為 `null`,圖上自然不畫,不丟錯、不偽造數值。
- 副圖建立/同步若 chart 已 dispose:沿用既有 `chartRef.current !== chart` 守衛,避免 "Value is undefined"。
- ohlcv 抓取錯誤:維持既有 `candles.isError` 區塊顯示。

## 測試
- **指標數學驗證**:專案前端**無 test runner**(CLAUDE.md:CI 只跑 `npm run build`),不在本輪引入 runner(YAGNI)。改以實作期間的一次性 node 斷言腳本(`node --import tsx` 或編譯後)比對已知參照值驗證:ema 收斂、rsi 落在 0–100、macd = ema_fast − ema_slow、bollinger = mid ± mult·std;驗證後不留在 repo。再以瀏覽器對同一標的的數值/形狀做交叉核對(對照 RSI 70/30 觸碰、MACD 柱翻正負)。
- **建置/型別**:`tsc --noEmit` + `npm run build` 為硬性關卡。
- **瀏覽器實測(`run-app` skill)**:逐一開啟各指標/副圖、切線圖類型、對數、全螢幕、十字準星讀數,截圖驗證;切 crypto 即時輪詢仍正常;切台股確認 `data-market="tw"` 漲跌色翻轉不受影響。

## 分階段交付(檢查點)
- **P1 — 選單**:中文化 + icon + lucide-react + DESIGN.md。最低風險,先驗收。
- **P2 — 圖表引擎**:chart-helpers 指標(+測試)→ PriceChart 副圖/疊加/類型/對數/全螢幕/讀數。
- **P3 — 控制接線**:MarketPanel 指標工具列 + timeframe/根數擴充。

每階段結束:`tsc` + build + 瀏覽器截圖檢查點,再進下一階段。

## 風險
- v4 多圖時間軸同步在快速縮放時可能有 1 幀錯位 → 雙向訂閱 + 防遞迴旗標處理。
- 全螢幕 API 在巢狀容器的高度計算 → 進入全螢幕時重設 chart height、退出還原。
- 指標數量過多影響可讀性 → 預設只開少量(例如 MA20/MA50),其餘由使用者按需開啟。
