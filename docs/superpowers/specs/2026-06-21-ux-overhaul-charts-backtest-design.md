# 設計文件:介面體驗翻修 — 即時線圖 / 回測重做 / 導覽中文化

- **日期:** 2026-06-21
- **狀態:** 設計中(待使用者 review)
- **分支:** `design/ux-overhaul-charts-backtest`
- **觸發:** 使用者回饋「介面操作邏輯看不懂、不直覺、回測不完整;一套交易工具最重要的是即時資料線圖,這塊也要做好」

---

## 1. 背景與問題

現有系統的**後端核心紮實**(221 個測試守著下單/風控/回測/帳本),但**前端體驗有結構性落差**。經實際讀碼確認的具體痛點:

| # | 痛點 | 證據(檔案) |
|---|---|---|
| P1 | 線圖非即時,且每次資料變動整張重建(閃爍、丟縮放) | `components/CandleChart.tsx` `useEffect` 依賴 `candles`,內部 `chart.remove()` 重建 |
| P2 | 市場頁只抓一次 120 根,無自動更新 | `MarketPanel.tsx` `useQuery` 無 `refetchInterval` |
| P3 | 回測 4 按鈕平鋪無引導,不知先後與差異 | `BacktestPanel.tsx:219-248` 四個同級按鈕 |
| P4 | 回測只能「最近 N 根」,無法選日期區間 | `api/backtest.py` `BacktestRequest.limit`;無 start/end |
| P5 | 回測只有淨值曲線,看不到買賣點落在哪根 K | `BacktestPanel.tsx:293` 僅 `EquityChart` |
| P6 | Walk-forward 動線斷裂(分頁叫你按按鈕、結果在最底下) | `BacktestPanel.tsx:334-336` vs `439-490` |
| P7 | 指標一次倒一堆無主次、無解讀 | `BacktestPanel.tsx:271-292` 8 卡 + 6 數字 |
| P8 | 中英文混雜(導覽中文、面板英文、分頁中文) | `BacktestPanel.tsx` "Backtest"/"Run" vs "概覽/交易" |
| P9 | 側欄標籤過簡、策略庫未掛入、無首次引導 | `lib/nav.ts` 扁平標籤;`TreeNav.tsx` 無 library 子樹 |
| P10 | 策略室→回測→實盤需手動切頁、手動找策略,動線斷 | 各頁獨立,無「拿去回測」一鍵帶入 |

## 2. 目標與非目標

**目標**
- 一套**共用即時線圖元件**,同時服務「即時看盤」與「回測買賣點視覺化」。
- 回測頁重做:操作引導、日期區間、K 線疊買賣點、指標分級+解讀。
- 導覽中文化、術語統一、首次引導、策略庫掛入側欄。
- 策略室→回測→實盤三段一鍵貫通。

**非目標(本次不做,列後續)**
- 真 WebSocket / ccxt.pro tick 級即時(本次用輪詢準即時)。
- 台股/美股**即時**行情(維持 CSV 離線,僅誠實標示)。
- 前端測試框架導入(目前無 runner;本次最多加關鍵 e2e,不強求)。
- 重寫工作流編輯器(已符合 DESIGN.md,不動)。

## 3. 確認的假設

1. 使用者 = 技術型散戶 + 開發者本人 → **好預設值 + 行內解讀**,不弱智化。
2. 語言 = 繁中為主,金融慣用詞(Sharpe/RSI/CAGR/K線)保留原詞+首次 tooltip。
3. 即時 = **輪詢準即時(2–5s)**;WebSocket 留 P5。
4. 日期區間回測 **需動後端**,納入本次範圍。
5. 嚴守 `DESIGN.md`:`--up/--down` token、`data-market="tw"` 翻轉、`tabular-nums`、cyan 僅限 AI、終端機密度。

---

# 4. 跨頁基礎(只設計一次,被多頁複用)

## F1. `PriceChart` 共用線圖元件(取代 `CandleChart`)

> **這是整個設計的樞紐**:即時看盤(B)與回測買賣點(C)共用它。

### 第一層 — 對外介面

```ts
interface PriceChartProps {
  candles: Candle[];              // 初始/歷史 K 線
  height?: number;                // 預設 360
  live?: LiveConfig | null;       // 即時輪詢設定,null = 靜態(回測用)
  markers?: ChartMarker[];        // 買賣點/事件標記
  overlays?: Overlay[];           // 疊加均線/布林等
  volume?: boolean;               // 是否顯示成交量副圖,預設 true
  market?: "crypto" | "tw_stock" | "us_stock"; // 驅動 data-market 漲跌色
  onCrosshairMove?: (p: OHLCV | null) => void;  // 浮標資料回拋(給外部 ticker 列)
}
interface LiveConfig { symbol: string; timeframe: string; intervalMs?: number; } // 預設 3000
interface ChartMarker { time: number; position: "aboveBar" | "belowBar"; kind: "buy" | "sell"; text?: string; }
interface Overlay { id: string; type: "sma" | "ema" | "bollinger"; params: Record<string, number>; color?: string; }
```

### 第二層 — 內部行為

1. **增量更新**:改用 `series.update(lastBar)` 只更新最後一根,**不再 `chart.remove()` 重建**。新增整段資料才 `setData()`。保留使用者縮放/平移位置。
2. **即時輪詢**(`live` 非 null):內部 `react-query` `useQuery({ refetchInterval })` 重抓最後 ~2 根;最後一根 close 變動時觸發**漲跌色閃爍**(120ms,DESIGN.md motion 允許的 price tick flash)。
3. **十字準星 + OHLC 浮標**:`subscribeCrosshairMove` → 透過 `onCrosshairMove` 回拋當前根 O/H/L/C/V;外層渲染浮動標籤。
4. **標記層**:`markers` → `series.setMarkers()`,買=▲(`--up`)、賣=▼(`--down`),帶 text(如成交價)。
5. **疊加層**:`overlays` 每項一條 `addLineSeries`,資料由前端用既有指標公式或後端回傳計算。
6. **成交量副圖**:`addHistogramSeries` 綁第二 priceScale,bar 漲跌色跟隨。
7. **主題/市場色**:讀 CSS token(沿用現有 `getComputedStyle` 寫法);`market="tw_stock"` 時套用翻轉色。

### 第三層 — 邊界條件與實作細節

- **空資料**:`candles=[]` 顯示 skeleton + 「無資料」提示,不丟例外。
- **去重/亂序**:`update()` 前確保 timestamp 遞增;同一根重複到達只更新不新增(lightweight-charts 對相同 time 視為 update)。
- **時間轉換**:沿用 `new Date(c.timestamp).getTime()/1000 as UTCTimestamp`;後端 `Candle.timestamp` 是 ISO datetime。
- **記憶體**:`useEffect` cleanup 移除 listener + `chart.remove()`;輪詢用 react-query 自動取消。
- **效能**:輪詢只更新差異根;`intervalMs` 下限 clamp 1000ms 防打爆。
- **RWD**:`ResizeObserver`(取代現有 window resize)讓圖隨容器寬度流動(DESIGN.md「charts fluid width」)。
- **a11y**:容器 `role="img"` + `aria-label` 描述商品/週期。
- **遷移**:保留 `CandleChart` 薄包裝轉呼 `PriceChart`(靜態模式),漸進替換各引用點;`EquityChart` 維持獨立(語義不同:淨值非 K 線)。

## F2. 語言 / 術語層 `lib/labels.ts`

### 第一層
單一檔集中所有 UI 文案與術語 tooltip,各元件引用,杜絕散落字串。

### 第二層
```ts
export const L = {
  backtest: { run: "執行回測", compare: "比較全部策略", optimize: "參數最佳化", walkforward: "樣本外驗證" /* ... */ },
  metrics: { total_return: "總報酬", max_drawdown: "最大回撤", sharpe: "Sharpe", win_rate: "勝率" /* ... */ },
};
export const GLOSSARY: Record<string, string> = {
  sharpe: "風險調整後報酬;>1 算不錯,<0 代表承擔風險卻虧損。",
  max_drawdown: "從高點到低點的最大跌幅;越小越穩。",
  walk_forward: "用過去資料選參數、在「沒看過的未來」資料驗證,專抓過度最佳化。",
  // ...每個指標一句白話
};
```

### 第三層
- **`<Term>` 元件**:`<Term k="sharpe">Sharpe</Term>` → 渲染文字 + `?` hover tooltip(讀 `GLOSSARY`)。
- **保留原則**:金融慣用詞(Sharpe/RSI/CAGR/CTA)保留英文原詞,只加解讀;操作動詞、區塊標題、狀態全中文。
- **不引入 i18n 框架**(YAGNI):只一份繁中常數,未來要雙語再抽。
- **驗收**:全 app grep 不應再有硬編英文 UI 動詞(`Run`/`Compare`/`Backtest` 標題等)。

---

# 5. Area B — 市場頁即時看盤

### 第一層
把「市場」頁從「靜態快照」升級為「能看盤」的即時頁。

### 第二層
1. **即時線圖**:`PriceChart` `live` 模式預設開;可手動暫停。
2. **Ticker 列**(圖上方):現價、24h 漲跌額/幅、24h 高/低、成交量;數字 mono + 漲跌色閃爍。
3. **商品選擇器**:可搜尋下拉取代手打 input(P 防打錯);crypto 內建常用清單(BTC/ETH/SOL…),保留自由輸入。
4. **AI 訊號疊圖**:`api.aiSignal` 結果以 marker 疊在對應時間點,旁附 confidence/reason。

### 第三層
- **Ticker 資料源**:新增 `api.ticker(symbol, market)`(後端 `/api/markets/ticker` 已存在,前端目前未用)→ 接上即可,免新後端。
- **暫停/節流**:分頁失焦(`visibilitychange`)自動停輪詢省流量;回焦恢復。
- **市場切換**:切 `tw_stock` → 設 `data-market="tw"` + 改用 imported 清單(`/api/markets/imported`)+ 圖上標「離線資料(CSV)」徽章,不偽裝即時。
- **錯誤**:ohlcv 502/501 → 圖區顯示後端 detail(fail loud),不空白。
- **狀態**:`symbol`/`timeframe`/`market` 寫入 URL query,可分享/重整保持。

---

# 6. Area C — 回測頁重做(核心痛點)

## C1. 操作引導(解 P3）

### 第一層
把 4 個平鋪按鈕改成**有主次的兩段式**:主流程「執行回測」醒目;進階分析收納並各帶說明。

### 第二層
- **主按鈕** `執行回測`(cyan,最大);跑單一策略單次回測。
- **進階分析** 折疊區(預設收起),內含三鈕,每個帶一行說明 + `<Term>` tooltip:
  - `比較全部策略` — 同條件跑四個內建策略排名。
  - `參數最佳化` — 掃參數網格找最佳組合(樣本外排名,防過擬合)。
  - `樣本外驗證` — Walk-forward k 折,驗證參數穩健度。

### 第三層
- **禁用態說明**:策略庫策略不支援 Optimize/Walk-forward(沿用現有 `disabled` + `title`),改成可見的灰字說明而非只有 hover title。
- **狀態互斥**:跑任一分析時其餘按鈕 disabled + 顯示進度文字(現有 `loading`)。
- **首次提示**:回測頁頂一行「① 選商品與策略 → ② 執行回測 → ③ 看 K 線買賣點與指標」,可關(localStorage 記住)。

## C2. 日期區間回測(解 P4,**需後端**)

### 第一層
除「最近 N 根」外,支援指定起訖日期回測(如 2021-01 ~ 2023-12)。

### 第二層 — 前端
- 控制列新增模式切換:`最近 N 根` ⇄ `日期區間`。
- 日期區間模式:兩個 date picker(start/end),預設近一年。
- `BacktestRequest` 等型別新增 `start?: string; end?: string`(ISO date)。

### 第三層 — 後端(最重要的一塊)
- **資料層** `Broker.get_ohlcv` 擴充為支援區間。最小侵入做法:
  - 在 `crypto_ccxt.py` 新增 `get_ohlcv_range(symbol, timeframe, start, end)`:用 `fetch_ohlcv(symbol, timeframe, since=start_ms, limit=1000)` **分頁迴圈**,直到 `until` 或無新資料;ccxt 已支援 `since`。
  - `csv_data.py`:改為按 `timestamp` 篩 `start<=t<=end`(目前是 `[-limit:]`)。
  - `base.py` 加抽象/預設方法;未實作的 broker fail loud。
- **API 層** `api/backtest.py`:`BacktestRequest`/`CompareRequest`/`OptimizeRequest`/`WalkForwardRequest` 新增 `start: datetime | None`、`end: datetime | None`;當提供時走 range 取數,否則維持 `limit`(向後相容)。
- **引擎**:`run_backtest(candles, ...)` **不需改**(吃 candle list)。
- **守護**:start≥end → 422;區間資料 < 2 根 → fail loud 明確訊息;ccxt 分頁設上限(如 ≤ 5000 根)避免拖死。
- **測試**:新增 `test_backtest_daterange.py` — ccxt 分頁(mock fetch_ohlcv)、CSV 區間篩選、邊界(空區間/反向)。

## C3. K 線疊買賣點(解 P5)

### 第一層
回測結果除淨值曲線,**多一張 `PriceChart` 把每筆 trade 的進出場畫在 K 線上**。

### 第二層
- 「概覽」分頁:上 `PriceChart`(靜態,疊 trade markers)、下 `EquityChart`(淨值)。
- 每筆 `Trade` → 兩個 marker:entry(▲ buy)、exit(▼ sell),text 帶報酬%。

### 第三層
- **資料**:回測已回 `trades[]`(含 entry/exit time+price)與 `equity_curve`;K 線需另存——回測時前端已有抓到的 candles?目前 `api.backtest` **只回結果不回 candles**。
  - 方案 A(推薦):回測前先 `api.ohlcv` 抓同條件 K 線給圖用(多一次請求,簡單)。
  - 方案 B:後端 `BacktestResult` 增 `candles` 欄(回傳變大)。→ **採 A**,避免膨脹 payload。
- **marker 對齊**:trade time 對到最近 K 線 time;next-bar-open 成交慣例(M0.2)在 tooltip 註明「進場價=次根開盤」。
- **疊均線**:若策略是 ma_cross,順手疊該策略的 fast/slow 均線(用 `overlays`),讓訊號可解釋。

## C4. 指標分級 + 解讀(解 P7)

### 第一層
指標分主次,主指標放大、次指標收納,每項可 hover 看白話解讀。

### 第二層
- **主指標(4 大卡)**:總報酬(vs Buy&Hold 對比)、最大回撤、Sharpe、勝率。
- **次指標(收進「更多指標」)**:CAGR/Sortino/Calmar/Vol/Exposure/Turnover/連虧/交易數/Profit factor。
- 每指標標題用 `<Term>`,hover 顯 `GLOSSARY` 解讀。

### 第三層
- **對比語意**:總報酬卡並列 Buy&Hold,並算「超額」(策略−B&H),正綠負紅,直接回答「贏大盤了嗎」。
- **健康度色標**:Sharpe<0 紅、0–1 中性、>1 綠;回撤永遠 down 色;勝率僅中性(避免誤導,勝率高≠賺)。
- **空交易**:`num_trades=0` 顯眼提示「此區間策略未產生交易」(常見於參數/區間不當),非靜默 0。

## C5. 統一結果動線(解 P6)
- **第一層**:四種分析(單次/比較/最佳化/Walk-forward)結果**統一在分頁容器**內,不再散落上下。
- **第二層**:分頁 = `概覽 | 交易明細 | 比較 | 最佳化 | 樣本外`;只顯示「跑過的」分頁,跑哪個自動切到該頁。
- **第三層**:移除現有「分頁叫你按下面按鈕」的死角(`BacktestPanel.tsx:334-336`);最佳化「use」套用參數後自動切回概覽並提示「已套用,重新執行以查看」。

---

# 7. Area D — 導覽 / IA + 中文化(解 P8/P9)

### 第一層
側欄資訊更清楚、術語統一、首次引導,讓「一進來知道從哪開始」。

### 第二層
1. **側欄標籤補副標**:`策略室` → 主標+英文副標(對齊 DESIGN.md `策略室 Strategy Lab` 樣式)。
2. **策略庫掛入側欄**:`策略室` 下展開已存策略(`api.listSavedStrategies`),DESIGN.md 原設計即如此。
3. **首頁三步引導**:`① 策略室設計 → ② 交易室回測 → ③ 排程/實盤`,卡片可點直達,可關。
4. **分組**:`排程/通知/匯入` 歸到次級或「工具」分組,不與主房間扁平並列。

### 第三層
- **`lib/nav.ts` 擴充**:`NavItem` 增 `subtitle?` 與動態 `children`(策略庫從 API 注入,client 端 fetch)。
- **active/live 規範**:沿用 DESIGN.md — active leaf cyan 左框 + `--accent-dim`;未來 `實際下單` leaf 用 `--live` dot(本次先佔位)。
- **icon rail(<xl)**:現有 `[&_.nav-label]:hidden` 已實作;補 hover flyout 顯示完整標籤+副標(DESIGN.md tablet 規格)。
- **中文化掃描**:`MarketPanel`/`BacktestPanel` 等標題 `Market`/`Backtest` → 改引 `L`;驗收見 F2。

---

# 8. Area E — 策略室 → 回測 → 實盤 串接(解 P10)

### 第一層
三段一鍵貫通,驗證過的策略能順順往下走,不必手動切頁找。

### 第二層
1. **策略室 →**「拿去回測」:存策略後一鍵帶到回測頁並選好該策略。
2. **回測 →**「套用到工作流/排程」:回測結果頁加入口,把策略推進實盤。

### 第三層
- **帶參跳轉**:回測頁讀 URL query `?strategy=saved:<id>&symbol=&timeframe=`,進頁自動選定(`BacktestPanel` 初始 state 從 query 取)。
- **回填來源**:策略室 `GeneratedStrategy`/`StrategyLibrary` 卡片加按鈕 → `router.push('/trading-room/backtest?strategy=saved:'+id)`。
- **往實盤**:回測結果加「建立工作流」→ 預生成含該策略 + order node 的 graph,帶到 `/trading-room/workflow`(用既有 `api.createWorkflow`);實盤安全態維持 DESIGN.md `--live` 規範。
- **狀態保存**:不引入全域 store(YAGNI),靠 URL query + 既有 API 串接。

---

# 9. 後端改動彙總(誠實標示)

| 項目 | 檔案 | 改動 | 風險 |
|---|---|---|---|
| 日期區間取數 | `brokers/crypto_ccxt.py` | 新增 `get_ohlcv_range`(ccxt `since` 分頁) | 中 |
| 區間篩選 | `brokers/csv_data.py` | `[-limit:]` → 按 timestamp 篩 | 低 |
| 介面契約 | `brokers/base.py` | 加 range 方法 | 低 |
| 回測 API | `api/backtest.py` | 4 個 Request 加 `start/end` | 低 |
| 即時 ticker | (無新後端) | 前端接既有 `/api/markets/ticker` | 無 |

**完全不動**:`run_backtest` 引擎、風控、下單路徑、工作流引擎。前端為主,後端僅「取數層」擴充。

---

# 10. 實作階段(里程碑)

| 階段 | 內容 | 產出可驗收 |
|---|---|---|
| **P1 地基** | `PriceChart` 元件 + `lib/labels.ts`/`<Term>` | 市場頁換上即時圖即見效 |
| **P2 看盤+回測** | B 即時看盤;C1/C3/C4/C5 回測重做(吃 P1) | 回測 K 線見買賣點、指標可解讀 |
| **P3 日期區間** | C2 前後端 + 測試 | 能跑「2021–2023」區間回測 |
| **P4 導覽** | D 中文化+側欄+引導(可與 P2 並行) | 全站無英文 UI 動詞、策略庫入側欄 |
| **P5 串接** | E 三段貫通 | 策略室一鍵回測、回測一鍵建流 |
| **P6 後續** | 真 WebSocket 即時(獨立 spec) | — |

每階段獨立成一份實作計畫(writing-plans),逐段 review checkpoint。

# 11. 測試策略

- **後端**:日期區間取數新增 `test_backtest_daterange.py`(ccxt 分頁 mock、CSV 篩選、邊界 fail-loud)。維持「business-logic test」原則(CLAUDE.md)。
- **前端**:目前無 runner。P1 `PriceChart` 為高複用核心,建議補最小 Playwright e2e(用 `frontend/.claude/skills` 的 `run-app` 驅動):載入市場頁→圖渲染→輪詢更新一根→回測頁見 marker。**屬建議非阻塞**。
- **不為覆蓋率寫空測試**(CLAUDE.md)。

# 12. 風險與未決

1. **ccxt 分頁深度**:長區間 + 小週期(如 5 年 1m)會抓爆。**對策**:後端設根數上限 + 前端對極端組合警示。
2. **即時輪詢成本**:多分頁/長時間輪詢的請求量。**對策**:失焦暫停 + interval 下限 clamp。
3. **台股/美股即時**:本次仍無;UI 必須誠實標「離線資料」,避免誤導(fail loud 精神)。
4. **未決(待使用者定)**:
   - (a) 日期 picker 預設區間 = 近一年?
   - (b) Profit factor / Calmar 等要不要也給白話解讀,或只主指標給?
   - (c) E 階段「建立工作流」要不要這次就做,或先只做策略室→回測一段?

---

## 附錄:設計自我檢查(spec self-review)
- placeholder 掃描:無 TBD;未決項已明列於 §12。
- 一致性:各頁共用 `PriceChart`/`labels`,無相互矛盾。
- 範圍:已切 P1–P6 階段,每段可獨立成計畫。
- 歧義:「即時」「回測完整」已在 §2/§3 明確定義為輪詢準即時 + 日期區間+買賣點。
