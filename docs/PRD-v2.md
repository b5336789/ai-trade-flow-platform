# PRD：ai-trade-flow-platform v2

> **交付對象：Claude Code。** 這份文件是開發規格，請逐階段（Phase）執行。
> **基礎：** 改造現有 repo `b5336789/ai-trade-flow-platform`（開發分支 `claude/ai-trading-platform-v2-jo2o2n`），**不是重寫**。
> **用途：** 作者個人真實資產累積的自動交易系統。**最高指導原則：不要因為程式 bug 或過擬合而賠掉真錢；數字必須可信；架構要撐得住長時間自動運行。**

---

## 0. 給 Claude Code 的工作守則（動手前先讀完這段）

### 0.1 Prime directive
任何會「下真單」或「產生報酬數字」的程式，正確性 > 功能完整度 > 美觀。寧可少做、明確報錯，也不要靜默地做錯。

### 0.2 工作方式（沿用本 repo 既有 `CLAUDE.md`）
1. **一次一個里程碑（milestone）。** 每完成一個 milestone 就停下來，回報：改了哪些檔、加了哪些測試、驗證了什麼、還剩什麼。等確認後再進下一個。
2. **Test-first。** 每個需求先寫**會失敗的測試**（對照「驗收標準」），再實作到綠燈。沿用 `backend/app/tests/` 的 pytest 風格。
3. **永不破壞既有可運行路徑。** 目前「crypto + paper」端到端是可用的，且既有測試全綠。每個 checkpoint 前跑完整 `pytest`，既有測試必須持續通過。
4. **Fail-loud 全程保留。** 缺資料／外部錯誤／違規 → 明確 raise + 記錄，絕不 `except: pass`。
5. **Config 驅動，禁止硬編祕密。** 新設定一律加進 `backend/app/config.py` 的 `Settings`，並更新 `.env.example`。
6. **外科手術式修改 + 沿用風格。** snake_case、`Broker` ABC、FastAPI + SQLModel + Next.js + React Flow。不要「順手清理」無關程式。
7. **預設安全。** 預設 `TRADING_MODE=paper`；live 必須同時要求 (a) 顯式 `TRADING_MODE=live`、(b) 有效金鑰、(c) 通過本 PRD 的新風控閘。
8. **新依賴要先說明理由。** 優先用既有依賴（`ccxt` / `ta` / `sqlmodel` / `fastapi` / `apscheduler` / `anthropic`）與標準庫。要新增重量級套件先提出。
9. 每個 milestone 結束時，同步更新 `docs/` 對應文件與 `docs/development-log.md`。

### 0.3 鐵則（違反即視為 bug）
- 回測與紙上交易**必須**計入交易成本（見 M0.1）。任何「零成本」的報酬數字都是錯的。
- 回測**不得**用「決策當根 K 棒的收盤價」成交（見 M0.2，前視偏差）。
- Optimizer **不得**只在樣本內挑最佳參數（見 M0.4，過擬合）。
- 任何「只出訊號、人工執行」的市場（預設：美股），其下單節點**絕不可**真的打到任何券商；必須改為發出「人工下單通知」並記錄 `status="manual_pending"`。
- 「策略室」生成的程式碼**絕不可**在主行程內執行；只能在硬沙箱內跑（見 M2.2）。

---

## 1. 背景與目標

### 1.1 v1 現況（已存在、可沿用的骨架）
- `brokers/base.py`：乾淨的 `Broker` ABC，是 paper/live × 多市場唯一接縫——**保留並沿用**。
- `trading/execution.py:execute_order()`：手動與工作流共用的單一下單路徑——**保留並沿用**。
- `brokers/crypto_ccxt.py`（幣安）、`brokers/paper.py`（紙上）、`trading/paper_store.py`（持久化）：crypto+paper 可運行。
- `workflow/`（拓撲排序引擎 + 節點）、`backtest/`（單策略回測 + grid search）、`ai/signal_agent.py`（行情摘要 → Claude → buy/sell/hold）、`scheduler/`（APScheduler）。
- 18 個測試檔，業務邏輯導向。

### 1.2 v2 要解決的核心問題（依嚴重度）
1. **金融正確性**：無成本、前視偏差、過擬合最佳化 → 報酬數字不可信。
2. **實盤安全**：風控只有兩道金額閘，且部位上限對實盤現貨失效；重複下單；無 kill switch / 單日虧損上限。
3. **存取安全**：無任何身分驗證、CORS 全開。
4. **概念落差**：策略室（NL→code→庫）、邏輯節點、市場消息、工作流回測、實盤 broker——大多沒做。

### 1.3 範圍邊界（先講清楚）
- **現貨/現股，long/flat only**（買進=持有、賣出=出清、無做空、無槓桿/期權/期貨/融資）。本期強制此不變式。
- **K 棒級節奏**，非毫秒級 HFT。
- 單人自用，**不做**多帳號/計費/SaaS。

---

## 2. 已確認的決定

- **基準幣別（base currency）：`TWD`**（作者為台灣資產累積）。所有 equity/各 balance/各 position 一律換算成 TWD 呈現；風控上限以 TWD 解讀。crypto(USDT) 與 us_stock(USD) 經 FX 換算。
- **台股 live 券商：元大證券 SPARK API（已定案）。**
  - 已確認可用：SPARK API 提供即時行情、台股下單、帳務服務。跨平台支援 Linux，且有 Linux x64/arm64 的 Python 元件；申請無財力/交易量門檻。
  - 整合現實：原生元件為平台特定下載式元件（非 pip / 非 PyPI），需 vendored 進 repo / Docker image；API 為 callback/事件驅動，adapter 需包裝成同步 `Broker` 介面；需 CA 憑證（TWCA）；UAT 測試環境需固定 IP 防火牆；官方「API 測試軟體」為 Windows-only `setup.exe`（屬作者人工 onboarding）。
  - 置於 `Broker` ABC 之後（見 M1.2）；日後若整合過痛仍可換成永豐 Shioaji。
- **美股 live：** 預設 **signal-only（只出訊號、人工執行）**。理由：元大複委託無散戶下單 API、Firstrade 無官方 API。未來若改用 IBKR/Alpaca 再新增 adapter，本期**不做**，列 backlog。

---

## 3. 架構原則與新增概念

沿用既有 seam，新增以下橫向概念（各自有對應 milestone）：

| 新概念 | 位置（新檔/改檔） | 解決 |
|---|---|---|
| 成本模型 CostModel | `trading/costs.py`（新）；用於 `backtest/engine.py`、`brokers/paper.py` | 無成本失真 |
| 基準幣別 + 匯率 FX | `marketdata/fx.py`（新）；用於 `trading/portfolio.py`、`trading/risk.py` | 跨市場幣別盲 |
| 部位感知 + 冪等下單 | `trading/execution.py`、`workflow/nodes.py` | 重複下單 |
| 投組級風控 + kill switch | `trading/risk.py`（擴充）、`config.py`、新 runtime flag | 無總曝險/單日虧損上限 |
| Signal-only broker | `brokers/signal_only.py`（新）、`brokers/registry.py` | 美股無 API |
| 工作流回測 + AI 重播 | `backtest/`（擴充）、`ai/signal_agent.py`（加快取） | AI 工作流無法回測 |
| FIFO 損益帳本 | `trading/ledger.py`（新）、`models.py` | 無已實現損益/稅務 |
| 開盤行事曆 | `marketdata/calendar.py`（新）、`scheduler/service.py` | 收盤仍嘗試交易 |
| 邏輯/組合節點 | `workflow/nodes.py`、`workflow/schema.py` | 多訊號被靜默吃掉 |
| 策略室 + 硬沙箱 | `strategy_lab/`（新）、`models.py` | 招牌功能缺席 |

---

## 4. 里程碑與需求（驗收標準皆可寫成測試；每項至少一個 pytest）

### Phase 0：金融正確性與安全地基（接任何真錢前必須全部完成）

- **M0.1 交易成本模型** — `trading/costs.py` `CostModel`（依 `MarketKind`），參數由 `Settings` 設定（crypto taker/maker bps、tw_stock 手續費+證交稅僅賣出、us_stock 費率+最低收費、共同滑價）。`backtest/engine.py` 與 `brokers/paper.py` 每筆成交套用成本。驗收：(1) 買→賣 `realized_net == gross_pnl − buy_cost − sell_cost − sell_tax`；(2) 開啟成本後高換手淨報酬 < 毛報酬；(3) 成本可由 env 覆寫。
- **M0.2 修正成交時點** — 訊號用「資料 ≤ close[i]」決策、成交於 **open[i+1]**；最後一根不開新倉。驗收：成交價 == `open[i+1]` ≠ `close[i]`。
- **M0.3 回測指標擴充** — `cagr`、`annualized_volatility`、`sharpe`、`sortino`、`calmar`、`profit_factor`、`avg_win`、`avg_loss`、`exposure_pct`、`max_consecutive_losses`、`turnover`。驗收：對已知序列手算對照 Sharpe/Sortino/profit_factor。
- **M0.4 Optimizer 樣本外/Walk-forward** — `backtest/validation.py` `walk_forward(...)`，回傳每折 OOS 表現；`grid_search` 加 train/test 切分、回報 IS+OOS、依風險調整後 OOS 排序（預設 OOS Sharpe）。驗收：IS 極佳/OOS 失敗的參數不會排第 1。
- **M0.5 部位感知 + 冪等下單 + 修現貨部位上限** — 目標部位語意（buy⇒持有、sell⇒出清、hold⇒不動作）、`client_order_id` 冪等鍵、`CcxtBroker.get_positions()` 由現貨餘額合成 Position、風控以市值（基準幣別）判斷。驗收：連續 buy ≤1 筆、同鍵重跑僅 1 筆、現貨買超上限被拒。
- **M0.6 投組級風控 + Kill switch** — `max_total_exposure_value`、`max_daily_loss`（觸發 halt）、`max_orders_per_day`、`kill_switch`（config 旗標 + 可由 API/DB 切換的持久化 runtime flag）。任一觸發：拒絕新進場、仍允許出清、設 halt、通知。驗收：每閘各一測試 + halt 期間出清可執行。全部以基準幣別計。
- **M0.7 存取鎖定 + 金鑰權限** — 所有 `/api/*` 需 bearer token（`Settings.api_token`），`/health` 開放；CORS 由 config 提供（移除 `*`）；前端帶 token；security 指引（幣安關提領 + 綁 IP、唯讀/下單分鑰）。驗收：無 token → 401、正確 token → 200。

> **Phase 0 完成定義：** 全綠 + 既有測試持續通過 + `docs/go-live-checklist.md`。未完成前文件須標示「禁止 live」。

### Phase 1：跨市場一致性與誠實的 broker 故事
- **M1.1 基準幣別 + 匯率** — `Settings.base_currency`（TWD）、`marketdata/fx.py`（線上 provider；回測/離線允許固定/匯入匯率）。portfolio equity、風控上限一律換算成基準幣別。
- **M1.2 Broker 故事定案** — `Broker` ABC 加 `capabilities`；crypto 沿用 `CcxtBroker`；台股新增 `brokers/yuanta_spark_tw.py`（包裝 SPARK callback、原生元件 vendored、mock contract test）；美股新增 `brokers/signal_only.py`（不打券商、發人工下單通知、`status="manual_pending"`）。
- **M1.3 FIFO 損益帳本** — `trading/ledger.py`、`models.py` `Lot`/`RealizedPnL`、報表/CSV 匯出。驗收：FIFO 已實現損益計算正確。
- **M1.4 開盤行事曆 gating + cron** — `marketdata/calendar.py` `is_market_open(market, dt)`；`Schedule.respect_market_hours` + cron；APScheduler `max_instances=1`/`coalesce=True`/`misfire_grace_time`。
- **M1.5 工作流回測 + AI 訊號可重播** — workflow 引擎加回測模式；`ai_signal` 從重播快取讀取（`AISignalLog`），回測時必須命中快取否則 fail loud；預熱快取工具。

### Phase 2：招牌功能（在地基穩固後安全地做）
- **M2.1 邏輯/組合節點** — `condition`/`combine`(AND/OR/加權投票)/`branch`；移除 `_first_signal` 靜默丟棄。
- **M2.2 策略室 + 硬沙箱 + 上線前回測 gate** — NL→策略 code→`GeneratedStrategy`；硬沙箱（隔離子行程、無網路、受限 FS、CPU/記憶體/wall-time 上限、import 白名單、AST 拒絕危險呼叫）；狀態流轉 `draft → validated → backtested → live_eligible`，只有 `live_eligible` 可進 live。
- **M2.3 市場消息接入（選配）** — `marketdata/news.py`；摘要新聞餵入 `signal_agent` 的 `extra_context`，記錄 provenance，可關閉。

---

## 5. 跨領域需求（每個 PR 都要遵守）
先寫失敗測試 → 實作到綠 → 跑完整 `pytest` → checkpoint 回報；全程 fail-loud；config 驅動禁硬編；預設 paper；外科手術式修改沿用風格；新依賴先提理由；向後相容；同步更新 `docs/`。

## 6. 非目標
不做多帳號/帳號系統/計費/SaaS；不做毫秒級 HFT；本期不做期權/期貨/槓桿/融資/做空；不做行動 App；美股自動實盤不做（signal-only）。

## 7. 總完成定義（Definition of Done）
1. Phase 0 全部完成且測試全綠（可接真錢最低門檻）。
2. `docs/go-live-checklist.md` 存在且作者逐項確認。
3. live 切換需顯式 `TRADING_MODE=live` + 有效 creds + 新風控全生效 + kill switch 已實測。
4. 任何 signal-only 市場確認零真實下單路徑。

## 8. 測試清單範式（每個 milestone 至少涵蓋）
Happy path、Fail-loud、邊界、回歸、安全（適用時）。
