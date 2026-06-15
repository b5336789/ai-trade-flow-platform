# 後端模組 / Backend Modules

後端位於 `backend/app/`。以下逐一說明每個模組。

## `schemas.py` — 共用領域型別
集中所有 enum 與 Pydantic 模型,跨 brokers / strategies / ai / workflow 重用:
- Enums:`MarketKind`(crypto / tw_stock / us_stock)、`TradingMode`(paper / live)、
  `OrderSide`、`OrderType`、`SignalAction`(buy / sell / hold)
- Models:`Candle`、`Ticker`、`Signal`、`OrderRequest`、`OrderResult`、`Balance`、`Position`

## `config.py` — 環境設定
`pydantic-settings` 讀取 `.env`。欄位名對應 UPPER_CASE 環境變數。見 [configuration.md](./configuration.md)。

## `db.py` — 資料庫
SQLModel engine(預設 SQLite)。`init_db()` 建表;`get_session()` 為 FastAPI 依賴。

## `models.py` — 資料表
`OrderRecord`、`Workflow`、`RunLog`、`Schedule`。

## `brokers/` — 券商抽象(核心接縫)

| 檔案 | 內容 |
| --- | --- |
| `base.py` | `Broker` ABC,所有市場/模式的統一介面 |
| `crypto_ccxt.py` | `CcxtBroker`:Binance(含 testnet)。公開行情免金鑰;`create_order` 無金鑰時 fail loud |
| `paper.py` | `PaperBroker`:包一個資料來源 broker 取真實價,模擬撮合,記憶體追蹤現金/部位(加權平均成本) |
| `registry.py` | `get_data_broker(market)`(行情)、`get_broker(market, mode)`(執行;paper 以 market 快取保留狀態) |

## `strategies/` — 指標與策略
見 [strategies.md](./strategies.md)。`registry.py` 集中 4 種策略,供工作流與回測共用。

## `ai/` — Claude 訊號

| 檔案 | 內容 |
| --- | --- |
| `claude_client.py` | 延遲建立 `anthropic.Anthropic`,無 `ANTHROPIC_API_KEY` 時 fail loud |
| `signal_agent.py` | 在程式端算精簡行情摘要(收盤、變化%、RSI)→ Claude `messages.parse` 結構化輸出 → `Signal`。預設 `claude-opus-4-8` |

> 設計:機械性計算留在程式端(`CLAUDE.md`「Keep Deterministic Work out of AI」),
> 只把摘要交給模型,控制 token。

## `trading/` — 風控、組合、下單

| 檔案 | 內容 |
| --- | --- |
| `risk.py` | `RiskGuard.check(req, price, held)`:單筆金額上限、部位總值上限;違規拋 `RiskError` |
| `portfolio.py` | `build_portfolio(broker)`:部位帶入即時價、未實現損益、權益總值;取價失敗退回成本價並標記 |
| `execution.py` | `execute_order(...)`:手動與工作流共用的唯一下單路徑(價→風控→撮合→存檔) |

## `workflow/` — 節點圖引擎
見 [workflow.md](./workflow.md)。`schema.py`(圖/節點/結果模型)、`nodes.py`(節點執行器)、
`engine.py`(拓撲排序、循環偵測、逐節點 fail-loud)。

## `backtest/` — 回測與最佳化
見 [backtesting.md](./backtesting.md)。`engine.py`(逐根回測)、`optimize.py`(網格搜尋)。

## `scheduler/` — 自動執行
`service.py`:APScheduler `BackgroundScheduler`。`Schedule` 對應一個間隔 job;觸發時跑工作流、
寫 `RunLog`、更新排程狀態。啟動時還原已啟用排程。

## `api/` — HTTP 路由
`markets.py`、`orders.py`、`ai.py`、`workflows.py`、`backtest.py`、`schedules.py`。
見 [api-reference.md](./api-reference.md)。

## `main.py` — 入口
建立 FastAPI app、CORS、lifespan(啟動 `init_db` + `start_scheduler`,關閉 `shutdown_scheduler`)、
掛載所有路由、`/health`、`/api/config`。
