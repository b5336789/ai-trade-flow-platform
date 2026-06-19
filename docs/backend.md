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
`OrderRecord`、`Workflow`、`RunLog`、`Schedule`、`Notification`、`PaperAccount`、`PaperPosition`、`RuntimeFlag`。
`RuntimeFlag(key, value, updated_at)` 持久化 kill switch、`halted` 旗標,以及每日權益基準(鍵 `equity_baseline:<UTC日期>`),M0.6。

## `marketdata/` — 行情接縫
| 檔案 | 內容 |
| --- | --- |
| `fx.py` | `FxConverter(base_currency, rates)`:以**設定驅動的靜態匯率**把金額折算為基準幣;`to_base(amount, ccy)` 同幣別直接回傳、缺率 fail loud(`ValueError`);`from_settings()` 由設定建立;`MARKET_QUOTE_CURRENCY`/`quote_currency_for` 提供 市場→計價幣(crypto→USDT、tw_stock→TWD、us_stock→USD)。Phase-0 最小接縫,M1.1 在同介面換成即時來源 (M0.6) |
| `calendar.py` | `is_market_open(market, dt)`:純函式、決定性。tw_stock 09:00–13:30 Asia/Taipei、us_stock 09:30–16:00 America/New_York(皆排除週末與內建假日集),crypto 永遠開盤。**dt 契約**:tz-aware 依其時區、naive 視為 UTC,內部轉成市場時區。假日為可匯入/可變的 `TW_STOCK_HOLIDAYS`/`US_STOCK_HOLIDAYS` 集合,`add_holidays(market, dates)` 可擴充。用 `zoneinfo`,無新依賴 (M1.4) |

## `brokers/` — 券商抽象(核心接縫)

| 檔案 | 內容 |
| --- | --- |
| `base.py` | `Broker` ABC,所有市場/模式的統一介面 |
| `crypto_ccxt.py` | `CcxtBroker`:Binance(含 testnet)。公開行情免金鑰;`create_order` 無金鑰時 fail loud。`get_positions()` 由現貨餘額合成 `Position`(非計價幣別資產;`avg_price=0` 因為餘額快照無成本基礎),讓現貨部位上限生效(M0.5) |
| `paper.py` | `PaperBroker`:包一個資料來源 broker 取真實價,模擬撮合,記憶體追蹤現金/部位(加權平均成本) |
| `yuanta.py` | `YuantaBroker`:台股 元大(及美股 元大複委託)live 骨架,所有方法 fail loud 並說明所需金鑰/SDK |
| `firstrade.py` | `FirstradeBroker`:美股 Firstrade live 骨架;明確標示無官方 API、依賴非官方函式庫 |
| `market_data.py` | 記憶體 OHLCV 倉儲(依 market+symbol)+ `parse_csv`;讓台股/美股可離線匯入資料 |
| `csv_data.py` | `CsvDataBroker`:以匯入的 CSV 歷史供應 ticker/ohlcv,作為 PaperBroker 的資料來源 |
| `registry.py` | `get_data_broker`(crypto→ccxt;台股/美股→有匯入資料則 CsvDataBroker,否則 fail loud)、`get_live_broker`(crypto→ccxt;台股→元大;美股→Firstrade)、`get_broker(market, mode)` |

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
| `risk.py` | `RiskGuard.check(req, fill_price, held, current_price)`:單筆金額上限、部位總值上限;部位上限改以**現價市值**判斷(現有持倉 × `current_price` + 新單 × `fill_price`),違規拋 `RiskError`(M0.5)。`PortfolioGuard.check(req, fill_price, market, broker, session)`:以**基準幣 (TWD)** 經 `FxConverter` 判斷總曝險、當日虧損(觸發設 `halted`)、每日下單數、kill switch;任一觸發**只擋進場(買入),永遠放行出場(減倉賣出)**,並發 `notify`(M0.6) |
| `runtime_state.py` | 隔離 `RuntimeFlag` 的持久化:get/set kill switch、get/set `halted`、`get_or_snapshot_day_start_equity`(依 UTC 日快照一次)、`count_orders_today`(`OrderRecord.created_at >= 今日 UTC 起點`)(M0.6) |
| `portfolio.py` | `build_portfolio(broker)`:部位帶入即時價、未實現損益、權益總值;取價失敗退回成本價並標記 |
| `execution.py` | `execute_order(...)`:手動與工作流共用的唯一下單路徑(冪等檢查→價→風控→撮合→存檔→通知)。可帶 `client_order_id`(M0.5):若該鍵已有 `OrderRecord` 則**跳過下單**並回傳既有結果(`info.idempotent_skip=True`);手動下單預設 `None`,行為不變 |
| `paper_store.py` | `PaperStore`:把紙上帳戶現金/部位持久化到 DB,讓 `PaperBroker` 重啟後仍保留狀態 |
| `ledger.py` | FIFO 已實現損益帳本(M1.3)。`FifoLedger.record_buy(...)` 開一個 `Lot`(數量、價、買進手續費計入成本基礎);`record_sell(...)` 依時間最舊先出消耗 `Lot`,每筆消耗產生一筆 `RealizedPnL`:`gross_pnl = (賣價−買價)×數量`、`realized_net = gross − 分攤買進手續費 − 分攤賣出手續費 − 證交稅`(費用/稅一律取自 M0.1 `CostModel`,crypto 稅=0、tw_stock 賣出課證交稅)。`record_fill(...)` 是接到 `execute_order` 的接縫:買進開 `Lot`、賣出 FIFO 消耗;賣出量超過已記錄 `Lot` 時消耗現有部分並對缺口發 `warning` 通知(永不擋出場)。`execute_order` 只在**實際成交且非冪等跳過**時才記帳,故不會重複計算 |

## `workflow/` — 節點圖引擎
見 [workflow.md](./workflow.md)。`schema.py`(圖/節點/結果模型)、`nodes.py`(節點執行器)、
`engine.py`(拓撲排序、循環偵測、逐節點 fail-loud)。

## `backtest/` — 回測與最佳化
見 [backtesting.md](./backtesting.md)。`engine.py`(逐根回測)、`optimize.py`(網格搜尋)。

## `notifications/` — 通知
`service.py`:`record_notification`(寫入站內通知)、`dispatch_webhook`(best-effort 外送,失敗不影響交易)、
`notify`(兩者合一)。`execute_order` 成交後會發出 `success` 通知。`Notification` 資料表保存站內動態。

## `scheduler/` — 自動執行
`service.py`:APScheduler `BackgroundScheduler`。`Schedule` 對應一個 job;觸發時跑工作流、
寫 `RunLog`、更新排程狀態。啟動時還原已啟用排程。
M1.4:job 設 `max_instances=1`、`coalesce=True`、`misfire_grace_time=30`;`Schedule.cron` 有值時
以 `CronTrigger` 取代 interval。`respect_market_hours=True`(預設)時,觸發當下市場收盤則 **SKIP**
(`last_status="skipped: market closed"`,非錯誤、不寫 RunLog)。排程市場取自工作流第一個 `data_source`
節點的 `params["market"]`(預設 crypto,與引擎一致),無 data_source(如純 logger)視為永遠開盤。

## `api/` — HTTP 路由
`markets.py`、`orders.py`、`ai.py`、`workflows.py`、`backtest.py`、`schedules.py`、`ledger.py`
(`GET /api/ledger/realized` 已實現損益報表,可依 `market`/`symbol`/`start`/`end` 篩選並回傳合計;
`GET /api/ledger/realized.csv` 匯出 CSV 供報稅)。
見 [api-reference.md](./api-reference.md)。

## `main.py` — 入口
建立 FastAPI app、CORS、lifespan(啟動 `init_db` + `start_scheduler`,關閉 `shutdown_scheduler`)、
掛載所有路由、`/health`、`/api/config`。
