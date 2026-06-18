# 任務總表與路線圖 / Task Backlog & Roadmap

> 本文件**鉅細靡遺**列出 `ai-trade-flow-platform` 從 v1 至今的**所有開發任務**(已完成 + 未完成),
> 依 effort 分類,並標示完成狀態。是判斷「目前做到哪裡、接下來做什麼」的單一事實來源(single
> source of truth)。
>
> 規格來源:v2 = [`PRD-v2.md`](./PRD-v2.md);v1 = [`development-log.md`](./development-log.md)。
> 技術細節 = [`README.md`](./README.md) 索引的各技術文件。

## 圖例 / Legend

**狀態**
- `[x]` = ✅ 已完成(已 commit、測試綠燈)
- `[ ]` = ⬜ 未完成

**Effort(工作量)**
- 🟢 **low** — 單一/少數檔案、邏輯清楚、無設計決策。約半天內可完成 + 測試。
- 🟡 **medium** — 跨數個檔案、含一定設計或演算法。約一天可完成 + 測試。
- ⛔ **(超過 medium)** — 不直接列為單一任務;**一律切割**成數個 low/medium 子任務(見各里程碑拆解)。

**慣例**:每個任務含「項目名稱 / 內容 / 大致修改位置」。驗收標準詳見 [`PRD-v2.md`](./PRD-v2.md) 對應 milestone。

---

## 進度總覽 / Progress Summary

| 階段 | 範圍 | 狀態 | 備註 |
| --- | --- | --- | --- |
| **v1 骨架** | Checkpoint 1–15 | ✅ 全數完成 | crypto + paper 端到端可運行,70 測試 |
| **v2 Phase 0** | M0.1–M0.7(接真錢前最低門檻) | 🟡 進行中(M0.1、M0.2、M0.3 ✅,其餘未完成) | **Phase 0 全綠前禁止 live** |
| **v2 Phase 1** | M1.1–M1.5(跨市場一致性 + broker) | ⬜ 未開始 | |
| **v2 Phase 2** | M2.1–M2.3(招牌功能) | ⬜ 未開始 | M2.2 策略室為最高風險 |
| **Backlog** | 非目標 / 未來 | ⬜ 不在本期 | 美股 live(IBKR/Alpaca)等 |

> **基準幣別 = TWD**(已確認)。**目前 Phase 0 未完成 → 系統禁止 live 交易。**

---

# Part A — v1 骨架(Checkpoint 1–15)✅ 全數完成

> 對應 [`development-log.md`](./development-log.md)。以下皆**已完成**,列出供回溯。

| ID | ✓ | 任務 | Effort | 內容 | 大致位置 |
| --- | --- | --- | --- | --- | --- |
| V1.1 | [x] | 專案骨架 | 🟢 | `CLAUDE.md`、README、`.gitignore`、`.env.example`、docker-compose、後端 Dockerfile/pyproject | 倉庫根目錄、`backend/` |
| V1.2 | [x] | 後端核心 | 🟡 | `schemas`、`config`、`db`、`Broker` ABC(ccxt + paper)、registry、markets API | `backend/app/{schemas,config,db}.py`、`brokers/`、`api/markets.py` |
| V1.3 | [x] | 指標與策略 | 🟡 | `ta` 指標包裝 + MA 交叉 / RSI 策略 | `strategies/{indicators,ma_cross,rsi}.py` |
| V1.4 | [x] | 紙上引擎 + 風控/組合 | 🟡 | `models`、`risk`、`portfolio`、共用 `execution`、orders API + DB | `trading/`、`models.py`、`api/orders.py` |
| V1.5 | [x] | AI 層 | 🟡 | `claude_client`、`signal_agent`(結構化輸出)、`/api/ai/signal` | `ai/`、`api/ai.py` |
| V1.6 | [x] | 工作流引擎 | 🟡 | 圖 schema、節點、拓撲執行、循環偵測、workflows API | `workflow/`、`api/workflows.py` |
| V1.7 | [x] | 前端 | 🟡 | Next.js:K 線、AI 訊號、React Flow 編輯器、組合/訂單、`/api/config` | `frontend/` |
| V1.8 | [x] | 回測 | 🟡 | 策略 registry、逐根回測引擎、`/api/backtest`、前端面板 | `backtest/engine.py`、`api/backtest.py` |
| V1.9 | [x] | 更多策略 + 比較 | 🟡 | MACD、布林通道、`/compare`、前端比較表 | `strategies/{macd,bollinger}.py`、`api/backtest.py` |
| V1.10 | [x] | 排程自動執行 | 🟡 | `Schedule` 模型、APScheduler 服務、`/api/schedules`、前端面板 | `scheduler/`、`api/schedules.py` |
| V1.11 | [x] | 參數最佳化 | 🟡 | 網格搜尋 `optimize`、`/api/backtest/optimize`、前端 Optimize | `backtest/optimize.py` |
| V1.12 | [x] | 技術文件 + 使用說明書 | 🟡 | `docs/`、前端 `/manual` 頁面 | `docs/`、`frontend/app/manual/` |
| V1.13 | [x] | 通知 | 🟡 | `notifications/`(站內 + webhook)、成交通知、`/api/notifications` | `notifications/`、`api/notifications.py` |
| V1.14 | [x] | 券商骨架 + 台美股離線資料 | 🟡 | 元大 / Firstrade live 骨架(fail loud)、CSV 匯入、`CsvDataBroker` | `brokers/{yuanta,firstrade,csv_data}.py`、`api/markets.py` |
| V1.15 | [x] | 紙上帳戶持久化 | 🟡 | `PaperAccount`/`PaperPosition` 表、`paper_store.py`、reset | `trading/paper_store.py`、`models.py` |
| V1.16 | [x] | 停損/停利節點 | 🟡 | `risk_exit` 工作流節點(依均價與現價判斷→sell) | `workflow/nodes.py` |

---

# Part B — v2 Phase 0:金融正確性與安全地基

> **接任何真錢前必須全部完成。** 目前僅 M0.1 完成。

## M0.1 — 交易成本模型 ✅ 已完成

| ID | ✓ | 任務 | Effort | 內容 | 大致位置 |
| --- | --- | --- | --- | --- | --- |
| 0.1.1 | [x] | CostModel 模組 | 🟢 | `CostModel`/`FillCost` 依 `MarketKind`:crypto bps、台股手續費+證交稅(僅賣出)、美股費率+最低收費、共同滑價;`from_settings()`/`zero()` | `trading/costs.py`(新) |
| 0.1.2 | [x] | 成本設定 + env | 🟢 | 8 個 `COST_*` 欄位,可由環境變數覆寫 | `config.py`、`.env.example` |
| 0.1.3 | [x] | 紙上 broker 計入成本 | 🟢 | 滑價套用成交價;手續費/稅扣現金;`info` 帶 fee/tax | `brokers/paper.py` |
| 0.1.4 | [x] | 回測引擎計入成本 | 🟡 | 每筆成交套成本;`Trade` 加 `gross_pnl`/`cost`,`pnl` 改淨額,`wins` 依淨額;新增 `market`/`cost_model` 參數 | `backtest/engine.py` |
| 0.1.5 | [x] | market 串接 | 🟢 | `grid_search` + 3 個 API 端點傳入 `market` | `backtest/optimize.py`、`api/backtest.py` |
| 0.1.6 | [x] | 測試 | 🟡 | 新增 `test_costs.py`(11);更新既有零成本斷言為含費精確值 | `tests/test_costs.py` 等 |
| 0.1.7 | [x] | 文件 | 🟢 | `PRD-v2.md`、`backtesting.md`、`development-log.md` | `docs/` |

## M0.2 — 修正成交時點(消除前視偏差)✅ 已完成

| ID | ✓ | 任務 | Effort | 內容 | 大致位置 |
| --- | --- | --- | --- | --- | --- |
| 0.2.1 | [x] | next-bar open 成交 | 🟢 | 訊號用「資料 ≤ close[i]」決策、成交於 **open[i+1]**(pending-action 狀態機);最後一根無次根→不開新倉(明確記錄) | `backtest/engine.py` |
| 0.2.2 | [x] | 成交慣例 docstring + 測試 | 🟢 | 構造 close[i] 觸發 buy,斷言成交價 == `open[i+1]` ≠ `close[i]`;末根訊號不開倉;docstring 寫明慣例 | `backtest/engine.py`、`tests/test_backtest.py` |

## M0.3 — 回測指標擴充 ✅ 已完成

| ID | ✓ | 任務 | Effort | 內容 | 大致位置 |
| --- | --- | --- | --- | --- | --- |
| 0.3.1 | [x] | 年化基礎 | 🟢 | `metrics.periods_per_year(timeframe)` 推導;`run_backtest` 加 `timeframe`/`risk_free_rate`;`config.backtest_risk_free_rate`(預設 0) | `backtest/metrics.py`、`backtest/engine.py`、`config.py` |
| 0.3.2 | [x] | 風險指標計算 | 🟡 | `BacktestResult` 新增 `cagr`/`annualized_volatility`/`sharpe`/`sortino`/`calmar`/`profit_factor`/`avg_win`/`avg_loss`/`exposure_pct`/`max_consecutive_losses`/`turnover`(純函式於 `metrics.py`) | `backtest/metrics.py`、`backtest/engine.py` |
| 0.3.3 | [x] | 指標測試 | 🟢 | `test_metrics.py` 手算對照 Sharpe/Sortino/PF/CAGR/Calmar/PPY;勝率非唯一排序依據(docstring 註記) | `tests/test_metrics.py`、`tests/test_backtest.py` |

## M0.4 — Optimizer:樣本外 / Walk-forward(消除過擬合)⛔ 已切割

| ID | ✓ | 任務 | Effort | 內容 | 大致位置 |
| --- | --- | --- | --- | --- | --- |
| 0.4.1 | [ ] | walk_forward | 🟡 | anchored/rolling 多折,回傳每折**樣本外(OOS)**表現 + 彙總 | `backtest/validation.py`(新) |
| 0.4.2 | [ ] | grid_search train/test | 🟡 | 加切分模式,**同時**回報 IS + OOS,依**風險調整後 OOS**(預設 OOS Sharpe)排序而非原始報酬 | `backtest/optimize.py` |
| 0.4.3 | [ ] | API 套用 OOS 最佳值 | 🟢 | 「套用最佳值」套 OOS 選出的參數,回傳 IS↔OOS 落差(不可隱藏) | `api/backtest.py` |
| 0.4.4 | [ ] | 前端顯示 IS/OOS 落差 | 🟢 | Optimize 結果顯示 OOS 指標與落差 | `frontend/components/BacktestPanel.tsx` |
| 0.4.5 | [ ] | 過擬合測試 | 🟡 | 構造「IS 極佳/OOS 失敗」參數,斷言不會排第 1 | `tests/test_validation.py`、`tests/test_optimize.py` |

## M0.5 — 部位感知 + 冪等下單 + 修現貨部位上限 ⛔ 已切割

| ID | ✓ | 任務 | Effort | 內容 | 大致位置 |
| --- | --- | --- | --- | --- | --- |
| 0.5.1 | [ ] | `client_order_id` 欄位 | 🟢 | `OrderRecord` 新增 `client_order_id`(索引);schema 相容 | `models.py` |
| 0.5.2 | [ ] | 目標部位語意 | 🟡 | buy⇒持有(size 由節點設定)、sell⇒出清、hold⇒不動作;執行層算差額,已在目標→no-op | `trading/execution.py`、`workflow/nodes.py` |
| 0.5.3 | [ ] | 冪等鍵 | 🟡 | 每次(排程執行×節點)產生 `client_order_id`,儲存;重複鍵→跳過並記錄 | `workflow/nodes.py`、`scheduler/service.py`、`trading/execution.py` |
| 0.5.4 | [ ] | 現貨部位合成 | 🟡 | `CcxtBroker.get_positions()` 由非報價幣餘額合成 `Position`(數量取自餘額) | `brokers/crypto_ccxt.py` |
| 0.5.5 | [ ] | 部位上限改用市值 | 🟢 | 風控部位/總曝險上限以**當前市值(基準幣別)**判斷,不依賴 avg_price | `trading/risk.py` |
| 0.5.6 | [ ] | 測試 | 🟡 | 連續 buy×5→≤1 筆;同鍵重跑→1 筆;現貨買超上限→拒絕 | `tests/test_orders_api.py`、`tests/test_workflow.py` |

## M0.6 — 投組級風控 + Kill switch ⛔ 已切割

> 依賴 **最小 FX seam**(Phase 0:config 靜態匯率、缺匯率 fail-loud;M1.1 換成線上 provider)。

| ID | ✓ | 任務 | Effort | 內容 | 大致位置 |
| --- | --- | --- | --- | --- | --- |
| 0.6.1 | [ ] | 最小 FX seam | 🟢 | config 靜態匯率換算成基準幣別(TWD);缺匯率 fail-loud。介面預留 M1.1 換 provider | `marketdata/fx.py`(新)、`config.py` |
| 0.6.2 | [ ] | 風控設定 | 🟢 | `max_total_exposure_value`/`max_daily_loss`/`max_orders_per_day`/`kill_switch` 設定欄位 | `config.py`、`.env.example` |
| 0.6.3 | [ ] | runtime flag 持久化 | 🟢 | 可由 API/DB 切換的 halt / kill-switch 持久化旗標 | `models.py` |
| 0.6.4 | [ ] | PortfolioGuard | 🟡 | 全以基準幣別計:總曝險、單日虧損(觸發 halt)、單日下單數、kill switch;觸發→拒新進場、仍允許出清、設 halt、通知 | `trading/risk.py` |
| 0.6.5 | [ ] | kill switch 端點 | 🟢 | API 切換 kill switch / 查 halt 狀態 | `api/`(新或擴充) |
| 0.6.6 | [ ] | 接線進下單路徑 | 🟢 | `execute_order` 套用 PortfolioGuard | `trading/execution.py` |
| 0.6.7 | [ ] | 測試 | 🟡 | 每個上限各一測試 + halt 期間出清單仍可執行 | `tests/test_risk_*.py` |

## M0.7 — 存取鎖定 + 金鑰權限 ⬜

| ID | ✓ | 任務 | Effort | 內容 | 大致位置 |
| --- | --- | --- | --- | --- | --- |
| 0.7.1 | [ ] | token + CORS 設定 | 🟢 | `Settings.api_token`;CORS `allow_origins` 由 config(預設 `["http://localhost:3000"]`),移除 `"*"` | `config.py`、`.env.example` |
| 0.7.2 | [ ] | bearer auth dependency | 🟢 | 所有 `/api/*` 需 bearer token,`/health` 開放;缺/錯→401 | `api/deps.py`(新)、`main.py` |
| 0.7.3 | [ ] | 前端帶 token | 🟢 | `lib/api.ts` 共用 `request()` 帶 Authorization header(env 驅動) | `frontend/lib/api.ts` |
| 0.7.4 | [ ] | 安全文件 | 🟢 | 幣安關提領 + 綁 IP、唯讀/下單分鑰;`docs/configuration.md` + README | `docs/configuration.md`、`README.md` |
| 0.7.5 | [ ] | 測試 | 🟢 | 無 token→401、正確 token→200 | `tests/` |

## M0.8 — Phase 0 完成定義 ⬜

| ID | ✓ | 任務 | Effort | 內容 | 大致位置 |
| --- | --- | --- | --- | --- | --- |
| 0.8.1 | [ ] | go-live checklist | 🟢 | `docs/go-live-checklist.md`(小額起步、各風控閘已設、kill switch 已實測、金鑰權限已確認);文件標示「Phase 0 完成前禁止 live」 | `docs/go-live-checklist.md`(新) |

---

# Part C — v2 Phase 1:跨市場一致性與誠實的 broker 故事 ⬜

## M1.1 — 基準幣別 + 匯率 ⛔ 已切割

| ID | ✓ | 任務 | Effort | 內容 | 大致位置 |
| --- | --- | --- | --- | --- | --- |
| 1.1.1 | [ ] | base_currency + FX 介面 | 🟢 | `Settings.base_currency`(TWD);FX provider 介面 | `config.py`、`marketdata/fx.py` |
| 1.1.2 | [ ] | FX provider 實作 | 🟡 | 線上 provider;回測/離線允許固定或匯入匯率;升級 M0.6 的最小 seam | `marketdata/fx.py` |
| 1.1.3 | [ ] | 組合換算基準幣別 | 🟡 | equity、各 balance/position 一律換算成基準幣別呈現 | `trading/portfolio.py` |
| 1.1.4 | [ ] | 風控以基準幣別解讀 | 🟢 | 風控上限換算基準幣別(接 M0.6) | `trading/risk.py` |
| 1.1.5 | [ ] | 測試 | 🟢 | 假匯率測 equity 換算 + 風控金額 | `tests/` |

## M1.2 — Broker 故事定案(crypto live / 台股 SPARK / 美股 signal-only)⛔ 已切割

| ID | ✓ | 任務 | Effort | 內容 | 大致位置 |
| --- | --- | --- | --- | --- | --- |
| 1.2.1 | [ ] | Broker capabilities | 🟢 | ABC 加 `capabilities`(`market_data`/`paper`/`live_order`/`supports_native_stop`);registry 可查詢 | `brokers/base.py`、`brokers/registry.py` |
| 1.2.2 | [ ] | signal-only broker | 🟡 | `create_order()` **不打券商**,發人工下單通知(side/數量/symbol/參考價)+ `OrderRecord(status="manual_pending")` | `brokers/signal_only.py`(新)、`brokers/registry.py`、`notifications/` |
| 1.2.3 | [ ] | manual_pending 狀態 + 測試 | 🟢 | 美股 order 節點(live)→ 通知 + manual_pending,**零** broker 呼叫 | `models.py`、`tests/test_stock_brokers.py` |
| 1.2.4 | [ ] | 元大 SPARK adapter | 🟡 | 把 SPARK callback/事件模型包裝成同步 `Broker`(行情快取 + 回報佇列);行情+下單+部位+餘額+成交回報;CA 憑證 + creds 走 `Settings` | `brokers/yuanta_spark_tw.py`(新) |
| 1.2.5 | [ ] | vendored 原生元件 + Dockerfile | 🟡 | linux-x64/arm64 元件 vendored;釘住 Python 版本/架構;Dockerfile 安裝 | `backend/vendor/yuanta_spark/`、`backend/Dockerfile` |
| 1.2.6 | [ ] | SPARK contract tests(mock) | 🟡 | mock SPARK 元件:登入失敗、部分成交、斷線重連、回報延遲;CI 不依賴真實元件 | `tests/test_stock_brokers.py` |
| 1.2.7 | [ ] | SPARK 設定文件 | 🟢 | 憑證、UAT 固定 IP、Windows 認證、PROD 切換、手動 smoke test | `docs/yuanta-spark-setup.md`(新) |

## M1.3 — FIFO 損益帳本 ⛔ 已切割

| ID | ✓ | 任務 | Effort | 內容 | 大致位置 |
| --- | --- | --- | --- | --- | --- |
| 1.3.1 | [ ] | Lot / RealizedPnL 模型 | 🟢 | 新增資料表 | `models.py` |
| 1.3.2 | [ ] | FIFO ledger | 🟡 | 每 (market, symbol) FIFO lots;買開 lot、賣沖銷最舊 lot 計逐筆已實現損益(含成本/稅,沿用 M0.1) | `trading/ledger.py`(新) |
| 1.3.3 | [ ] | 接線進成交 | 🟡 | paper broker 成交時更新 ledger | `brokers/paper.py` |
| 1.3.4 | [ ] | 報表 + CSV 匯出 | 🟢 | 依期間/標的報表端點,CSV 供報稅 | `api/` |
| 1.3.5 | [ ] | 測試 | 🟢 | 買100@10、買100@12、賣150@15 → 已實現 650(再扣成本) | `tests/test_ledger.py`(新) |

## M1.4 — 開盤行事曆 gating + cron 排程 ⛔ 已切割

| ID | ✓ | 任務 | Effort | 內容 | 大致位置 |
| --- | --- | --- | --- | --- | --- |
| 1.4.1 | [ ] | calendar | 🟡 | `is_market_open(market, dt)`:台股(09:00–13:30 台北、工作日、可匯入假日)、美股(常規盤、時區假日)、crypto 永遠開 | `marketdata/calendar.py`(新) |
| 1.4.2 | [ ] | Schedule gating | 🟢 | `respect_market_hours` 旗標 + 選配 cron;收盤跳過記 `skipped: market closed`(非 error) | `models.py`、`scheduler/service.py` |
| 1.4.3 | [ ] | APScheduler 設定 | 🟢 | `max_instances=1`、`coalesce=True`、`misfire_grace_time` | `scheduler/service.py` |
| 1.4.4 | [ ] | 測試 | 🟢 | 凍結時間,台股 03:00 觸發→跳過且狀態正確 | `tests/test_scheduler.py` |

## M1.5 — 工作流回測 + AI 訊號可重播 ⛔ 已切割

| ID | ✓ | 任務 | Effort | 內容 | 大致位置 |
| --- | --- | --- | --- | --- | --- |
| 1.5.1 | [ ] | AISignalLog + 快取鍵 | 🟢 | 快取 key = `model + prompt hash`;存 prompt+response | `models.py`、`ai/signal_agent.py` |
| 1.5.2 | [ ] | signal_agent 快取 | 🟡 | 讀寫快取;回測模式**必須命中快取否則 fail loud**(禁回測打線上 API) | `ai/signal_agent.py` |
| 1.5.3 | [ ] | workflow 回測模式 | 🟡 | bar-by-bar 跑整張 graph:data_source 餵歷史窗、order 模擬成交(成本 + next-bar open)、ai_signal 讀重播快取 | `workflow/engine.py`、`backtest/` |
| 1.5.4 | [ ] | 預熱快取工具 | 🟢 | 先對歷史算好 AI 訊號 | 工具腳本 / `ai/` |
| 1.5.5 | [ ] | 測試 | 🟡 | 含 ai_signal 工作流回測→零網路、確定性可重現、成本已計入 | `tests/` |

---

# Part D — v2 Phase 2:招牌功能(地基穩固後安全地做)⬜

## M2.1 — 邏輯 / 組合節點 ⛔ 已切割

| ID | ✓ | 任務 | Effort | 內容 | 大致位置 |
| --- | --- | --- | --- | --- | --- |
| 2.1.1 | [ ] | 新 NodeType schema | 🟢 | `condition`(門檻判斷)、`combine`(AND/OR/加權投票→單一 Signal)、`branch`(依條件路由) | `workflow/schema.py` |
| 2.1.2 | [ ] | 引擎支援多 Signal | 🟡 | `combine` 接多 Signal;**移除 `_first_signal` 靜默丟棄**(單輸入才直通) | `workflow/nodes.py`、`workflow/engine.py` |
| 2.1.3 | [ ] | 前端節點 | 🟢 | 新節點型別 UI | `frontend/components/workflow/` |
| 2.1.4 | [ ] | 測試 | 🟢 | buy+sell 進 `combine(AND)`→hold;`combine(OR)` 依規格;衝突不再被靜默丟棄 | `tests/test_workflow.py` |

## M2.2 — 策略室 + 硬沙箱 + 上線前回測 gate ⛔ 已切割(**最高風險,合併前需安全審查**)

| ID | ✓ | 任務 | Effort | 內容 | 大致位置 |
| --- | --- | --- | --- | --- | --- |
| 2.2.1 | [ ] | GeneratedStrategy 模型 + 狀態流轉 | 🟡 | code 文本、參數 schema、version、status;`draft→validated→backtested→live_eligible` | `models.py` |
| 2.2.2 | [ ] | NL→code 生成器 | 🟡 | 以自然語言經 LLM 產生符合 `Strategy` ABC(`generate(candles)->Signal`)的程式碼 | `strategy_lab/generator.py`(新) |
| 2.2.3 | [ ] | AST 驗證器 | 🟡 | **拒絕** `os`/`sys`/`subprocess`/`open`/`eval`/`exec`/`__import__`/dunder 存取;import 白名單(`pandas`/`numpy`/`ta`/`app.schemas`) | `strategy_lab/validator.py`(新) |
| 2.2.4 | [ ] | 硬沙箱執行器 | 🟡 | 隔離子行程/容器:無網路、唯讀/受限 FS、CPU+記憶體+wall-time 上限、受限 builtins;**絕不在主行程跑** | `strategy_lab/sandbox_runner.py`(新) |
| 2.2.5 | [ ] | 上線資格 gate | 🟡 | 依序(a)靜態驗證(b)沙箱跑樣本歷史(c)計入成本回測;server 端強制**只有 `live_eligible` 可選入 live 工作流** | `strategy_lab/gate.py`(新)、`workflow/` |
| 2.2.6 | [ ] | API 端點 | 🟢 | 生成/驗證/回測/狀態查詢 | `api/` |
| 2.2.7 | [ ] | 前端策略室介面 | 🟡 | NL 輸入、狀態顯示、回測結果 | `frontend/` |
| 2.2.8 | [ ] | 測試(含惡意樣本) | 🟡 | `import os` 被拒;無窮迴圈被 wall-time 終止;非 `live_eligible` 無法進 live | `tests/test_strategy_lab.py`(新) |
| 2.2.9 | [ ] | 安全審查 checkpoint | 🟢 | 合併前人工安全審查(沙箱逃逸面、資源限制實測) | — |

## M2.3 — 市場消息接入(選配)⛔ 已切割

| ID | ✓ | 任務 | Effort | 內容 | 大致位置 |
| --- | --- | --- | --- | --- | --- |
| 2.3.1 | [ ] | news provider 介面 | 🟢 | provider 介面 + 設定(可關閉) | `marketdata/news.py`(新)、`config.py` |
| 2.3.2 | [ ] | 餵入 signal_agent | 🟢 | 摘要新聞→`extra_context`,記錄來源(provenance) | `ai/signal_agent.py` |
| 2.3.3 | [ ] | 降級 + 測試 | 🟢 | 帶新聞 context 的 ai_signal prompt 含該新聞;無 provider 優雅降級(非 error) | `tests/` |

---

# Part E — Backlog / 非目標(明確不做或未來)

| ID | ✓ | 項目 | 說明 |
| --- | --- | --- | --- |
| BK.1 | [ ] | 美股自動 live(IBKR / Alpaca adapter) | 本期**不做**;美股維持 signal-only。日後若改用有官方 API 的券商再新增 adapter |
| BK.2 | [ ] | 永豐 Shioaji adapter | 元大 SPARK 整合若過痛的備案(`pip install shioaji`) |
| — | ❌ | 多帳號 / 帳號系統 / 計費 / SaaS | **非目標**,不做 |
| — | ❌ | 毫秒級 HFT | **非目標**;維持 K 棒級節奏 |
| — | ❌ | 期權 / 期貨 / 槓桿 / 融資 / 做空 | **非目標**;本期強制 long/flat only |
| — | ❌ | 行動 App | **非目標**,不做 |

---

## 維護說明

- 完成一個任務後:把 `[ ]` 改成 `[x]`,並在 [`development-log.md`](./development-log.md) 補一列。
- 任務若發現超過 medium,**就地切割**成更小的 low/medium 子任務(沿用本表編號 `X.Y.Z`)。
- 規格疑義一律以 [`PRD-v2.md`](./PRD-v2.md) 的「驗收標準」為準。
