# 開發歷程 / Development Log

依 `CLAUDE.md`「Create Step-by-Step Checkpoints」逐步推進,每個 checkpoint 完成後 commit。
每步都記錄:完成內容、驗證方式。

| # | 主題 | 完成內容 | 驗證 |
| --- | --- | --- | --- |
| 1 | 專案骨架 | `CLAUDE.md`、README、`.gitignore`、`.env.example`、docker-compose、後端 Dockerfile/pyproject | 檔案就緒、commit |
| 2 | 後端核心 | `schemas`、`config`、`db`、`Broker` 抽象(ccxt + paper)、registry、markets API | app 匯入 OK;ccxt 路徑正確(外網被擋→fail-loud 502) |
| 3 | 指標與策略 | `ta` 指標包裝 + MA交叉 / RSI 策略 | 11 測試(交叉、超買賣、防呆) |
| 4 | 紙上引擎 + 風控/組合 | `models`、`risk`、`portfolio`、共用 `execution`、orders API + DB | 22 測試(撮合、風控、組合、HTTP) |
| 5 | AI 層 | `claude_client`、`signal_agent`(結構化輸出)、`/api/ai/signal` | 25 測試(mock 離線映射/夾擠) |
| 6 | 工作流引擎 | 圖 schema、節點、拓撲執行、循環偵測、workflows API | 30 測試(端對端下單、hold、循環) |
| 7 | 前端 | Next.js:K線、AI訊號、React Flow 編輯器、組合/訂單、`/api/config` | tsc 乾淨 + production build 成功 |
| 8 | 回測 | 策略 registry、逐根回測引擎、`/api/backtest`、前端面板 + 權益曲線 | 35 測試 |
| 9 | 更多策略 + 比較 | MACD、布林通道、`/api/backtest/compare`、前端通用參數 + 比較表 | 43 測試 |
| 10 | 排程自動執行 | `Schedule` 模型、APScheduler 服務、`/api/schedules`、前端 Save + 排程面板 | 49 測試 |
| 11 | 參數最佳化 | 網格搜尋 `optimize`、`/api/backtest/optimize`、前端 Optimize + 套用最佳 | 53 測試 |
| 文件 | 技術文件 + 使用說明書 | `docs/`(本目錄)、前端 `/manual` 圖文並茂頁面 | tsc + build |
| 12 | 通知 | `notifications/`(站內 + webhook)、成交自動通知、`/api/notifications`、前端 NotificationsPanel | 58 測試 |
| 13 | 券商骨架 + 台美股離線資料 | 元大 / Firstrade live 骨架(fail loud)、CSV 匯入(`/api/markets/import`)、`CsvDataBroker` 讓台股/美股離線回測與紙上交易、前端市場選擇 + 匯入面板 | 63 測試 |
| 14 | 紙上帳戶持久化 | `PaperAccount`/`PaperPosition` 資料表、`trading/paper_store.py`、`PaperBroker` 載入/儲存、`/api/orders/paper/reset`、前端 Reset 鈕 | 66 測試 |
| 15 | 停損/停利 | `risk_exit` 工作流節點(依持倉均價與現價判斷停損/停利→sell)、前端節點 | 70 測試 |

## v2 (依 `docs/PRD-v2.md`，Phase 0：金融正確性與安全地基)

> 基準幣別 = **TWD**;本期實作範圍 = **Phase 0 (M0.1–M0.7)**。Phase 0 全綠前**禁止 live**。

| # | 里程碑 | 完成內容 | 驗證 |
| --- | --- | --- | --- |
| M0.1 | 交易成本模型 | `trading/costs.py`(`CostModel`/`FillCost`,依 `MarketKind`:crypto bps、台股手續費+證交稅僅賣出、美股費率+最低收費、共同滑價);`config.py` 8 個 `COST_*` 設定 + `.env.example`;`brokers/paper.py` 與 `backtest/engine.py` 每筆成交套用成本(`Trade` 加 `gross_pnl`/`cost`,`pnl` 改為淨額);`api/backtest.py`/`optimize.py` 傳入 `market`。成本預設 ON。 | 81 測試(新增 `test_costs.py` 11 項:費率/賣出稅/折讓/最低收費/滑價/env 覆寫/fail-loud/紙上淨額恆等式/回測淨額恆等式/高換手淨<毛);既有受影響的零成本斷言已更新為含費精確值 |
| M0.2 | 修正成交時點(消除前視偏差) | `backtest/engine.py` 改用 pending-action 狀態機:訊號以資料 ≤ `close[i]` 決策、成交於 **`open[i+1]`**;最後一根訊號不開新倉;權益於 `close[i]` 標記;docstring 寫明成交慣例。 | 83 測試(新增 2 項:成交價 == `open[i+1]` ≠ `close[i]`、末根訊號不開倉);既有「獲利回合」測試改用誠實 next-bar 成交下仍獲利的價格序列 |

## 設計原則落實(對照 `CLAUDE.md`)
- **Simplicity First**:先做 crypto+紙上一條完整切片,再水平擴充。
- **Surgical Changes**:重構策略 registry 時只動相關處。
- **Fail Loud**:缺資料/外部錯誤/風控違規一律明確回報。
- **Business-Logic Tests**:53 項皆驗證真實行為。
- **Checkpoints**:每步 commit 並記錄(本表)。
- **Match Codebase Style**:後端 snake_case、前端慣用 React/TS。

## 尚未實作(規劃中)
- 真實券商:台股 **元大證券**、美股 **元大複委託 / Firstrade**(需金鑰 + 外網;Firstrade 無官方 API)。
- 使用者驗證 / 多使用者、雲端部署強化、訊號通知。
