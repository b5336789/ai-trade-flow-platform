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
| M0.3 | 回測指標擴充 | 新增 `backtest/metrics.py`(純函式:`periods_per_year`、Sharpe/Sortino/Calmar、`profit_factor`、`cagr`、`max_consecutive_losses` 等);`BacktestResult` 加 `cagr`/`annualized_volatility`/`sharpe`/`sortino`/`calmar`/`profit_factor`/`avg_win`/`avg_loss`/`exposure_pct`/`max_consecutive_losses`/`turnover`;`run_backtest` 加 `timeframe`/`risk_free_rate`,迴圈追蹤曝險與成交名目;`config` 加 `backtest_risk_free_rate`;`api`/`optimize` 串接 `timeframe`。 | 93 測試(新增 `test_metrics.py` 9 項手算對照 Sharpe/Sortino/PF/CAGR/Calmar/PPY + 1 項回測指標齊備) |
| M0.4 | Optimizer 樣本外/Walk-forward(消除過擬合) | 新增 `backtest/validation.py` `walk_forward`(anchored/rolling 多折、`selection_score`);`grid_search` 加 `split` 模式(同時算 IS+OOS、揭露落差、依風險調整後 **OOS Sharpe** 排序);`api/backtest` + 前端 `BacktestPanel` 串接並顯示 IS↔OOS 落差。**並行 subagent 開發(Wave 1)**,PR #13。 | 103 測試(新增 `test_validation.py` 4 + `test_optimize.py` +6,含 `test_overfit_combo_does_not_rank_first`) |
| M0.5 | 部位感知 + 冪等下單 + 修現貨部位上限 | 目標部位語意重寫 `_run_order`;`OrderRecord.client_order_id` + `sha1(run_id:node_id)` 冪等鍵(排程傳每-tick 穩定 run_id);`CcxtBroker.get_positions()` 由餘額合成現貨部位;`RiskGuard` 改以現價市值判斷部位上限。**並行 subagent 開發(Wave 1)**,PR #14。 | 100 測試(新增 7:連續 buy ≤1 筆、同 run_id 1 筆、現貨超上限拒絕等) |
| M0.7 | 存取鎖定 + 金鑰權限 | `api/deps.py` `require_api_token` 全域套用 `/api/*`(`/health` 開放,空 token=開放+警告);`config` 加 `api_token`/`api_cors_origins`(移除 `"*"`);前端帶 bearer;安全文件(幣安關提領/綁 IP/分鑰)。**並行 subagent 開發(Wave 1)**,PR #12。 | 99 測試(新增 `test_auth.py` 6) |
| (wrap-up) | Wave 1 整合 + CAGR 加固 | 三條並行分支合併後完整套件 **116 測試**綠;`metrics.cagr` 改以 log 空間 + 夾擠避免短樣本年化 `OverflowError`;`task-backlog`/`development-log` 集中勾選 M0.4/M0.5/M0.7;`.gitignore` 加 `.claude/`。 | 116 測試(含 CAGR 短樣本不溢位 1 項) |
| M0.6 | 投組級風控 + Kill switch | 新增 `marketdata/fx.py`(`FxConverter`,靜態匯率換 TWD、缺率 fail-loud)、`trading/runtime_state.py` + `models.RuntimeFlag`(kill switch/halted/day-start equity/當日單數)、`trading/risk.py` `PortfolioGuard`(四閘以 TWD 計,**任一觸發擋進場、永遠放行出場**,單日虧損觸發設 halted)、`api/risk.py`(status/kill-switch/resume,掛 auth)、`execute_order` 接線。**Wave 2 subagent**,PR #16。 | 128 測試(新增 `test_risk_portfolio.py` 11:每閘拒 buy + halt/kill 放行 sell + FxConverter) |
| M0.8 | Phase 0 完成定義 | 新增 `docs/go-live-checklist.md`(DB 遷移/存取/金鑰/成本/風控+kill switch 實測/OOS/範圍/小額起步);`tests/conftest.py` 改為 session 起始 drop+create,讓測試 DB 決定性(消除 schema 漂移與當日單數累積)。**Phase 0(M0.1–M0.8)全數完成。** | 128 測試(連跑多次穩定) |

## v2 Phase 1 / 2(並行 Wave 4)

| # | 里程碑 | 完成內容 | 驗證 |
| --- | --- | --- | --- |
| M1.4 | 開盤行事曆 gating + cron | 新增 `marketdata/calendar.py` `is_market_open`(台股 09:00–13:30 Asia/Taipei、美股 09:30–16:00 ET、皆排除週末/內建假日,crypto 永遠開;dt naive 視為 UTC);`Schedule.respect_market_hours`/`cron`;scheduler 收盤跳過(`skipped: market closed`、非 error、不寫 RunLog)+ cron/interval + `max_instances=1`/`coalesce`/`misfire_grace_time`。**Wave 4 subagent**,PR #18。 | 142 測試(calendar 10 + scheduler 4;含 03:00 台北跳過驗收) |
| M2.1 | 邏輯/組合節點 | `NodeType` 加 `condition`/`combine`/`branch`;`_first_signal`→`_only_signal`(多 Signal **fail loud**,終結靜默丟棄);`combine` AND/OR/weighted 合併;前端三節點。**Wave 4 subagent**,PR #19。 | 138 測試(新增 10:各 combine 模式 + 多 Signal 進 order 報錯 + condition) |
| M1.3 | FIFO 損益帳本 | 新增 `trading/ledger.py`(`FifoLedger` FIFO 沖銷、逐筆已實現損益、`CostModel` 計費用/證交稅)、`models.Lot`/`RealizedPnL`、`api/ledger.py`(報表 + 報稅 CSV,掛 auth);接線 `execute_order`(冪等 skip 後、僅實際成交);賣超已記錄 lots 時消耗現有並發 warning(**不擋出場**)。**Wave 4 subagent**,PR #20。 | 135 測試(新增 7:毛額 650 恆等式 + 含費/證交稅 + 部分沖銷 + oversell + 整合 + 冪等不重複) |
| (整合) | Wave 4 合併驗證 | 三條並行分支(M1.3/M1.4/M2.1)合併後完整套件綠、連跑穩定;`task-backlog`/`development-log` 集中勾選。 | **159 測試**(連跑多次穩定) |

## Infra / AWS GitHub Actions 部署紀錄

| 日期 | 主題 | 完成內容 | 驗證 / 狀態 |
| --- | --- | --- | --- |
| 2026-06-19 | AWS production deploy pipeline | PR #24 建立並合併 GitHub Actions CI + production deploy workflow、Terraform bootstrap/prod stacks、ECS Fargate + ECR + ALB + RDS PostgreSQL + Secrets Manager、frontend/backend production Docker path、`docs/deployment/aws.md`;部署區域從 `ap-southeast-2` 改為 `ap-east-2`;`bwtseng.com` 已註冊但第一版仍用 ALB DNS。 | 本機驗證:backend `190 passed, 1 warning`;frontend build pass;Terraform bootstrap/prod validate pass;workflow YAML parse pass;Docker backend/frontend build pass。PR #24 CI pass 後 merge。 |
| 2026-06-19 | AWS bootstrap + first deploy | 使用 AWS SSO profile `AdministratorAccess-334317074103` 在 `ap-east-2` bootstrap Terraform state bucket、DynamoDB lock table、GitHub OIDC deploy role;設定 GitHub `production` environment secrets(`AWS_DEPLOY_ROLE_ARN`,`TF_STATE_BUCKET`,`TF_LOCK_TABLE`,`AWS_ACCOUNT_ID`,`API_TOKEN`,`NEXT_PUBLIC_API_TOKEN`);首次 production deploy 成功建立 ALB/ECS/RDS/VPC/ECR/Secrets。 | 修正 Terraform `1.8.5` 不認得 `ap-east-2` 的 S3 backend 問題:PR #25 升級 workflow 到 Terraform `1.15.6` 並合併。Deploy run `27822493926` 成功;ALB 曾為 `ai-trade-flow-prod-alb-1029134024.ap-east-2.elb.amazonaws.com`;`/health` 回 `200 OK {"status":"ok"}`;backend/frontend ECS 皆 running 1/1。 |
| 2026-06-19 | 停止 AWS 付費資源 | 依成本控制要求關閉 production runtime:先將 backend/frontend ECS services scale 到 0,再 destroy Terraform prod stack;臨時解除 RDS `prevent_destroy` 並刪除 RDS;刪除 ALB、NAT Gateway/EIP、ECS services/cluster、VPC/subnets/security groups、CloudWatch log groups、Secrets Manager app secrets;ECR repos 因含 image 改用 AWS CLI `delete-repository --force` 刪除,再從 Terraform state 移除殘留。 | 驗證:RDS `NOT_FOUND`;ALB `NOT_FOUND`;NAT 無 active/deleting;ECR `NOT_FOUND`;ECS cluster `INACTIVE`;VPC tag 查詢無結果;Secrets Manager 無 `ai-trade-flow-prod/*`;prod Terraform state 為空。保留 bootstrap 資源(S3 state bucket、DynamoDB lock table、GitHub OIDC role/provider)以便日後重啟部署。GitHub `Deploy Production` workflow 已手動 disable,避免 push `main` 自動重建付費資源。 |

## v2 前端完成(策略室 UI + 文件中心)

> 後端 spec-based 策略室(`api/strategies.py`、`strategies/spec.py`、`ai/strategy_agent.py`)已存在且 190 測試綠;
> 本波補齊前端缺口,使「策略室 / 交易室功能都齊備、技術文件上網頁」。分支 `feature/strategy-room-and-docs-web`。

| # | 主題 | 完成內容 | 驗證 |
| --- | --- | --- | --- |
| FE.1 | 策略室前端 | 將原本的 placeholder `strategy-lab` 改為 DESIGN.md 規格的完整策略室:AI 設計對話(左,cyan)+ 生成策略面板(rendered Python + 可調參數表)+ 策略庫卡片(載入 / 回測 / 刪除)。新增 `lib/api.ts` 策略庫型別與方法、`components/strategy/{DesignChat,GeneratedStrategy,StrategyLibrary,StrategyLab}`。 | tsc 乾淨、`next build` 通過;dogfood 確認設計面板、策略庫列表、單支回測端到端可用(無 console error);修正 `win_rate` 顯示(後端已是百分比,勿再 ×100)。 |
| FE.2 | 文件中心上網頁 | 新增 `/docs`:系統功能詳細說明(策略室 / 交易室 / 跨領域能力,AI 標記)+ 9 篇技術文件(架構 / 功能 / 營運)以 markdown 渲染。`content/docs/` 提交入庫並由 `scripts/sync-docs.mjs`(predev/prebuild)自 repo `docs/` 同步,因 Docker frontend build context 只含 `frontend/`。`react-markdown`+`remark-gfm`,on-brand components map。 | `next build` 把 `/docs` 與 9 篇 `/docs/[slug]` 預渲染為靜態 HTML(SSG,適配 standalone);dogfood hub + 內文 on-brand 渲染。 |
| FE.3 | 策略室 → 交易室 接通 | 交易室回測面板的策略下拉新增「策略庫」optgroup,可直接回測策略室設計的已存策略(走 `/api/strategies/{id}/backtest`,預設參數);Optimize 維持內建策略限定。 | dogfood:選策略庫策略 → Run → 權益曲線 + 指標正確顯示。 |

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
