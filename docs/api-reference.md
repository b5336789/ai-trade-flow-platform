# API 參考 / API Reference

Base URL(預設):`http://localhost:8000`。互動式文件:`http://localhost:8000/docs`(Swagger UI)。
所有 JSON。錯誤以 `{"detail": "..."}` 回傳。

## 慣例:錯誤碼

| 碼 | 意義 |
| --- | --- |
| 422 | 輸入無效 / 風控違規 / 資料不足 |
| 501 | 市場尚未實作(台股/美股) |
| 502 | 上游錯誤(交易所網路、Claude API、解析失敗) |
| 404 | 找不到資源(workflow / schedule) |

## Meta

### `GET /health`
→ `{"status": "ok"}`

### `GET /api/config`
→ `{"trading_mode": "paper", "markets": ["crypto","tw_stock","us_stock"], "implemented_markets": ["crypto"], "ai_model": "claude-opus-4-8"}`

## Markets

### `GET /api/markets/ticker`
Query:`symbol`(必填)、`market`(預設 `crypto`)。
→ `Ticker { symbol, price, timestamp }`

### `GET /api/markets/ohlcv`
Query:`symbol`、`market=crypto`、`timeframe=1h`、`limit=100`(1–1000)。
→ `Candle[] { timestamp, open, high, low, close, volume }`

### `POST /api/markets/import`
Body:`{ market, symbol, csv }`。`csv` 表頭需含 `timestamp,open,high,low,close[,volume]`。
匯入後該 (市場, 代號) 即可離線回測/紙上交易(台股/美股尚未串接真實券商時的資料來源)。
→ `{ market, symbol, imported }`。格式錯誤回 `422`。

### `GET /api/markets/imported?market=tw_stock`
→ `{ market, symbols: [...] }`(已匯入的代號清單)

## Orders

### `POST /api/orders?market=crypto`
Body:`OrderRequest { symbol, side: "buy"|"sell", quantity, type?: "market"|"limit", limit_price? }`
流程:解析價 → 風控 → 下單(paper/live)→ 寫入 DB。
→ `OrderResult { id, symbol, side, quantity, price, status, mode, broker, timestamp }`
錯誤:`422` 風控違規、`501` 未實作市場、`502` 上游。

### `GET /api/orders`
→ `OrderRecord[]`(最新在前)

### `GET /api/orders/portfolio?market=crypto`
→ `PortfolioView { cash, positions: PositionView[], positions_value, equity }`

### `POST /api/orders/paper/reset?market=crypto`
清除該市場的紙上交易帳戶(現金與部位,持久化於 DB)。→ `{ "reset": true }`
`PositionView { symbol, quantity, avg_price, current_price, market_value, unrealized_pnl, price_source }`
(`price_source` 為 `live` 或 `avg_fallback`,後者表示即時價不可得而退回成本價。)

## AI

### `POST /api/ai/signal`
Body:`{ symbol, market?, timeframe?, limit?, model? }`。
後端計算精簡行情摘要 → Claude 結構化輸出。
→ `Signal { action, confidence, reason, source }`
需要 `ANTHROPIC_API_KEY`,否則 `502`。

## Workflows

### `POST /api/workflows`
Body:`{ name, graph: WorkflowGraph }`。→ `Workflow`

### `GET /api/workflows` / `GET /api/workflows/{id}` / `PUT /api/workflows/{id}`
標準 CRUD。

### `POST /api/workflows/run`
Body:`WorkflowGraph`(臨時執行,不儲存)。→ `RunResult`

### `POST /api/workflows/{id}/run`
執行已儲存的工作流。→ `RunResult { status, steps, orders, error }`

`WorkflowGraph`:
```json
{
  "nodes": [{ "id": "d", "type": "data_source", "params": { "symbol": "BTC/USDT" } }],
  "edges": [{ "source": "d", "target": "s" }]
}
```
節點型別:`data_source` | `strategy` | `ai_signal` | `order` | `logger`。

## Workflow Run History

所有工作流執行(即時/紙上/回測)均自動持久化為 `WorkflowRun`,每筆訊號另存為 `WorkflowSignal`(含逐節點 `trace_json`)。

### `GET /api/workflows/runs`
Query:`kind`(可選,`backtest`/`live`/`paper`)、`limit`(預設 20)。
→ `WorkflowRun[]`(最新在前)
`WorkflowRun { id, run_id, workflow_id, kind, status, symbols, metrics_json, equity_curve_json, trades_json, created_at }`

### `GET /api/workflows/runs/{id}`
→ 單筆 `WorkflowRun`(含完整欄位)。找不到回 `404`。

### `GET /api/workflows/runs/{id}/signals`
Query:`symbol`(可選,篩選單一資產)。
→ `WorkflowSignal[]`
`WorkflowSignal { id, run_id, order_node_id, symbol, timestamp, bar_index, action, confidence, price, trace_json, created_at }`
`trace_json` 為 JSON 陣列,內含各節點 id → 輸出摘要的鍵值對,可用於前端重現訊號推導過程。

## Backtest

### `GET /api/backtest/strategies`
→ `{ "strategies": ["ma_cross","rsi","macd","bollinger"] }`

### `POST /api/backtest`
Body:`{ symbol, market?, timeframe?, limit?, strategy, params?, starting_cash?, position_fraction? }`
→ `BacktestResult { starting_cash, final_equity, total_return_pct, buy_hold_return_pct, num_trades, wins, win_rate, max_drawdown_pct, trades[], equity_curve[] }`

### `POST /api/backtest/compare`
Body:`{ symbol, ..., strategies? }`(預設全部)。
→ `CompareRow[]`(依報酬排名),`{ strategy, total_return_pct, buy_hold_return_pct, num_trades, win_rate, max_drawdown_pct, error }`

### `POST /api/backtest/optimize`
Body:`{ symbol, ..., strategy, param_grid: {fast:[5,10], slow:[20,30]}, metric?, max_combinations? }`
→ `OptimizeRow[]`(依 metric 排名),`{ params, total_return_pct, num_trades, win_rate, max_drawdown_pct, error }`
組合數超過 `max_combinations`(預設 200)回 `422`。

### `POST /api/backtest/workflow`
對一張 `WorkflowGraph` 執行多資產共用現金的歷史組合回測(逐根 K 線重放)。

Body:
```json
{
  "graph": { "nodes": [...], "edges": [...] },
  "workflow_id": "optional-uuid",
  "market": "crypto",
  "timeframe": "1h",
  "limit": 500,
  "starting_cash": 100000
}
```
`graph` 與 `workflow_id` 擇一(提供 `workflow_id` 時從 DB 讀取圖)。`market`、`timeframe`、`limit`、`starting_cash` 均有預設值。

→
```json
{
  "run_id": "uuid",
  "symbols": ["BTC/USDT", "ETH/USDT"],
  "result": { "...BacktestResult 欄位..." },
  "signals": [
    { "symbol": "BTC/USDT", "timestamp": "2024-01-02T01:00:00Z",
      "action": "buy", "confidence": 0.82, "trace_json": [...] }
  ]
}
```
驗證失敗(圖無 order 節點 / symbol 不唯一 / timeframe 不一致 / 資料不足 / AI 節點超過 bar 上限)回 `422`。

## Schedules(自動執行)

### `POST /api/schedules`
Body:`{ workflow_id, interval_seconds (>=5), enabled? }`。建立排程並註冊 APScheduler job。
→ `Schedule { id, workflow_id, interval_seconds, enabled, last_run_at, last_status, created_at }`

### `GET /api/schedules`
→ `Schedule[]`

### `POST /api/schedules/{id}/toggle`
啟用/停用(同步增刪排程 job)。→ `Schedule`

### `DELETE /api/schedules/{id}`
→ `{ "deleted": true }`

## Notifications

### `GET /api/notifications?limit=20`
→ `Notification[] { id, level, title, message, meta, created_at }`(最新在前)
`level`:`info` | `success` | `warning` | `error`。下單成交會自動產生一則 `success` 通知。

### `POST /api/notifications/test`
建立一則測試通知(並嘗試派送 webhook,若有設定 `NOTIFY_WEBHOOK_URL`)。→ `Notification`
