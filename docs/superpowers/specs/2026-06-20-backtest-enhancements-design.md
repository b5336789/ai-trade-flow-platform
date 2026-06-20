# 完善回測功能 — 設計文件

- 日期：2026-06-20
- 分支：`feature/backtest-enhancements`
- 狀態：已通過 brainstorming，待 spec review

## 背景與問題

後端回測引擎（`backend/app/backtest/`）已相當成熟：

- `engine.py` — 逐根 K 棒、無未來函數（訊號於 `close[i]` 決定、於 `open[i+1]` 成交）、每筆成交套用交易成本，並算出豐富指標：CAGR、年化波動、Sharpe、Sortino、Calmar、profit factor、avg win/loss、exposure、turnover、最大連敗等，外加 `trades` 明細與 `equity_curve`。
- `optimize.py` — 網格搜尋，含 OOS 切分模式（以樣本外風險調整指標排名，防過擬合）。
- `validation.py` — `walk_forward` walk-forward 驗證（anchored / rolling），**已實作但未在 API 暴露**。

落差全在前端與 API 邊界：

1. **指標未呈現**：後端回傳的 Sharpe / Sortino / Calmar / profit factor / CAGR / exposure / turnover 等，前端 TS 型別 `BacktestResult`（`frontend/lib/api.ts`）直接丟棄，UI 只顯示 4 個基本指標。
2. **無真正權益曲線**：`BacktestPanel.tsx` 只畫一條迷你 sparkline，未用專案已安裝的 `lightweight-charts`。
3. **無交易明細**：後端 `trades` 陣列前端完全沒用。
4. **walk-forward 用不到**：後端寫好卻無 API、無 UI。
5. **timeframe / limit 寫死**：前端固定送 `"1h" / 500`，使用者無法調整。

## 目標

把後端「已算出但未呈現」的能力完整呈現於前端，並接通 walk-forward。**不重寫已成熟的 engine / metrics / optimize 邏輯**。

## 非目標（YAGNI）

- 不改回測核心演算法（成交慣例、成本模型、指標公式）。
- 不做做空 / 多部位 / 槓桿。
- 不新增前端測試框架（CI 僅 `npm run build`）。
- 不做回測結果持久化 / 歷史紀錄。

## 設計

### 一、後端：暴露 walk-forward（唯一後端改動）

於 `backend/app/api/backtest.py` 新增：

```
POST /api/backtest/walk-forward
```

Request model（新增 `WalkForwardRequest`）：

| 欄位 | 型別 | 預設 |
|---|---|---|
| symbol | str | — |
| market | MarketKind | crypto |
| timeframe | str | "1h" |
| limit | int (10–1000) | 500 |
| strategy | str | "ma_cross" |
| param_grid | dict[str, list] | {} |
| n_folds | int (≥2) | 4 |
| metric | str | "sharpe" |
| anchored | bool | true |
| max_combinations | int (1–500) | 200 |

Response：直接以 `validation.WalkForwardReport` 當 `response_model`，呼叫既有 `walk_forward(...)`。

錯誤處理沿用此檔既有四段式：

- `ValueError` → 422（如 n_folds 不足、grid 過大、candle 不足）
- `NotImplementedError` → 501（市場資料 broker 尚未實作）
- 其他 → 502（外部資料取得失敗）

### 二、前端型別補齊（`frontend/lib/api.ts`）

`BacktestResult` 介面補上後端 Pydantic 已回傳但漏掉的欄位：

```ts
starting_cash, final_equity, wins, cagr, annualized_volatility,
sharpe, sortino, calmar, profit_factor (number | null),
avg_win, avg_loss, exposure_pct, max_consecutive_losses, turnover,
trades: Trade[]
```

新增介面：

- `Trade { entry_time, exit_time, entry_price, exit_price, quantity, pnl, gross_pnl, cost, return_pct }`（對應 `engine.py:Trade`）
- `WalkForwardRequest`、`FoldResult`、`WalkForwardReport`（對應 `validation.py` 的 model）

新增 client 方法 `api.walkForward(req: WalkForwardRequest)` → `POST /api/backtest/walk-forward`。

### 三、前端 UI（`frontend/components/BacktestPanel.tsx` + 抽元件）

**控制列**新增兩個下拉，取代寫死值：

- timeframe：`1m / 5m / 15m / 1h / 4h / 1d`（state，預設 1h）
- limit：`200 / 500 / 1000`（state，預設 500）

Run / Compare / Optimize / Walk-forward 四個動作都改吃這兩個 state。

**結果區改為分頁籤（Tabs）**：

- **概覽 (Overview)**
  - 指標卡片組：Return、Buy & Hold、CAGR、Sharpe、Sortino、Max DD、Win rate、Profit factor 為主卡；exposure / turnover / 最大連敗 / avg win / avg loss 以小字次要呈現。
  - 下方 `EquityChart`（新元件）：用 `lightweight-charts` line series 畫完整權益曲線。沿用 `CandleChart.tsx` 的慣例：從 CSS 變數讀色（`--up/--down/--accent/--bg/--border/--muted`）、`clientWidth` 設寬、`window resize` 監聽、卸載時 `chart.remove()`。曲線上漲/下跌以 `--up/--down` 決定（依終值 vs 起值）。
- **交易 (Trades)**
  - 表格：進場時間 / 出場時間 / 進場價 / 出場價 / 數量 / 報酬% / 淨損益 / 成本。
  - 淨損益、報酬% 用 `--up/--down` token 上色，**不**硬寫綠漲紅跌（遵守 DESIGN.md；台股經 `data-market="tw"` 反向）。
  - 長列表以 `max-h-*` 容器內捲。
- **Walk-forward**
  - 「Run walk-forward」按鈕（僅內建策略，沿用 `lib/strategies.ts:OPTIMIZE_GRID`；saved 策略 disable，比照現有 Optimize）。
  - 標題顯示 `aggregate_oos_metric` 與 `aggregate_oos_return_pct`。
  - 每個 fold 一列：fold / best params / IS metric / OOS metric / OOS return% / OOS maxDD。
  - 錯誤的 fold 顯示其 `error` 字串（fail-loud，不靜默）。

頁籤狀態與既有 `result / comparison / optimization` 並存；`resetOutputs()` 一併清掉 walk-forward 結果與當前頁籤。

### 四、資料流

維持單一路徑，前端不下沉業務邏輯：

```
UI 控制 → frontend/lib/api.ts → FastAPI /api/backtest/* router
        → 既有 run_backtest / grid_search / walk_forward
```

### 五、元件邊界

| 元件 | 職責 | 依賴 |
|---|---|---|
| `EquityChart.tsx`（新） | 把 `EquityPoint[]` 畫成權益曲線 | lightweight-charts、CSS token |
| `BacktestPanel.tsx`（改） | 控制列、四動作、分頁籤呈現 | api.ts、EquityChart、strategies.ts |
| `api/backtest.py`（改） | 新增 walk-forward endpoint | validation.walk_forward |
| `lib/api.ts`（改） | 型別補齊 + walkForward 方法 | — |

## 錯誤處理

- 後端：四段式 HTTP 對應（422 / 501 / 502），fail-loud。
- 前端：既有 try/catch 設 `error` state 並顯示「Backtest error: …」；walk-forward 沿用同模式。壞 fold 在表內就地顯示 error。

## 測試

- 後端：新增 `backend/app/tests/test_backtest_api.py`（若不存在），涵蓋：
  - walk-forward 成功路徑 → 回傳含 `folds` 與 `aggregate_oos_metric` 的結構。
  - 壞輸入（如 `n_folds=1` 或 grid 超限）→ 422。
  - 既有 `walk_forward` 單元測試若存在則沿用，不重複。
- 前端：無 test runner；以 `npm run build` 通過 + 手動驗證（Run / Compare / Optimize / Walk-forward 四動作、分頁籤切換、權益圖繪製）為準。

## 遵循規範（CLAUDE.md / DESIGN.md）

- 外觀全走 DESIGN.md token；電光青 `--accent` 僅限 AI / 自動化。
- 漲跌一律 `--up/--down`，不硬寫綠漲紅跌。
- Fail-loud：壞 fold、壞 combo、API 錯誤都顯示，不靜默跳過。
- Git flow：feature branch → PR → merge，不直接推 `main`。
- 外科手術式改動：只動回測相關檔，不順手清理周邊。
