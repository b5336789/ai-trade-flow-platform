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
