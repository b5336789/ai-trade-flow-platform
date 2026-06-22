# 工作流引擎 / Workflow Engine

工作流是一張**有向無環圖 (DAG)**:節點產生輸出,沿邊傳給下游。前端的 React Flow 編輯器
與後端 `WorkflowGraph` schema 一一對應。

## 節點型別(`workflow/schema.py` `NodeType`)

| 型別 | 輸入 | 輸出 | params |
| --- | --- | --- | --- |
| `data_source` | — | `Candle[]` | `symbol, market, timeframe, limit` |
| `strategy` | candles | `Signal` | `name` + 該策略參數 |
| `ai_signal` | candles | `Signal` | `symbol?, model?` |
| `risk_exit` | candles | `Signal`(停損/停利→sell,否則 hold) | `stop_loss_pct, take_profit_pct, symbol?, market?` |
| `order` | Signal | `OrderResult`(無動作則 None) | `quantity, symbol?, market?` |
| `logger` | 任意 | 透傳 | — |
| `condition` | candles | `Signal`(門檻成立→buy,否則 hold) | `source(預設 close), operator(>,>=,<,<=,==,!=), value` |
| `combine` | 多個 Signal | 單一 `Signal` | `mode(AND/OR/weighted)`, OR 用 `bias`, weighted 用 `weights{source:w}, epsilon` |
| `branch` | Signal + candles | `Signal`(條件成立→透傳上游 Signal,否則 hold) | 同 `condition` |

### 多 Signal 與「不再靜默丟棄」(M2.1)
- 期望單一 Signal 的節點(如 `order`)若收到**多個** Signal 會 **fail loud**(`_only_signal` 拋錯,提示改接 `combine`)——取代舊的 `_first_signal` 靜默取首個的 bug。
- 單一上游 Signal 仍直通(passthrough)不變。

### `combine` 合併語意
- **AND(共識)**:所有 Signal 必須一致同向(全 buy→buy、全 sell→sell)才動作;任何不一致或出現 hold → `hold`。confidence 取一致 Signal 的**最小值**(最弱環節)。
- **OR(任一動作優先)**:任一 buy/sell 勝過 hold;若同時出現 buy 與 sell 衝突,由可設定的 `bias`(預設 `buy`)決定勝方。confidence 取勝方 Signal 的**最大** confidence。
- **weighted(加權投票)**:buy 加 `+confidence*weight`、sell 加 `-confidence*weight`、hold 不計;`weight` 由 `weights`(以 Signal 的 `source` 為鍵,預設 1.0)提供。淨值 > `epsilon`→buy、< `-epsilon`→sell、否則 `hold`。confidence = `min(1, |淨值| / 總權重)`。

```mermaid
flowchart LR
    DS[data_source] --> ST[strategy]
    DS --> AI[ai_signal]
    ST --> OR[order]
    AI --> OR
    OR --> LOG[logger]
```

## 執行(`workflow/engine.py`)
1. `_topological_order`:拓撲排序,偵測重複 id、未知邊、循環(皆 fail loud → `RunResult.error`)。
2. 依序執行每個節點,輸入為其前驅節點的輸出。
3. 每個節點輸出做摘要存入 `steps`;`order` 節點的 `OrderResult` 收進 `orders`(僅 order 節點計入,
   避免 logger 透傳重複計算)。
4. 任一節點丟例外 → 停止並回報是哪個節點失敗(fail loud)。

`RunResult { status, steps[], orders[], error }`。

## 節點執行器(`workflow/nodes.py`)
- `RunContext`:跨節點暫存(如 data_source 設定的 `symbol`/`market`,供 order 節點預設)+ DB session + `run_id`(本次邏輯執行的識別碼,預設隨機;排程器傳入「每個 tick 固定」的值)。
- `_first_candles`:從上游輸入取出 candles,缺少則 fail loud。
- `_only_signal`:取出**唯一**上游 Signal;缺少或出現多個皆 fail loud(多個須先接 `combine`)。`combine` 改用 `_signals` 取全部 Signal 後合併。
- `order` 節點呼叫共用的 `trading/execution.execute_order`(含風控)。
- **目標部位語意(M0.5)**:訊號代表「目標」而非動作——buy⇒持有 `quantity` 單位、sell⇒出清(0)、hold⇒不動作。節點讀取現有持倉、只交易差額(僅做多/出清,不放空);已達目標則不下單,故重複 tick 天然冪等。
- **冪等鍵(M0.5)**:每筆下單以 `sha1("{run_id}:{node_id}")` 推導 `client_order_id` 傳入 `execute_order`;同一 `run_id` 重跑會得到相同鍵 → 跳過重複下單。排程的同一 tick 重試共用同鍵,下一 tick 取得新鍵。

## 自動執行(排程)
已儲存的工作流可由 `Schedule` 綁定間隔,APScheduler 定時觸發 `run_scheduled_workflow`,
重用同一個引擎,把結果寫入 `RunLog` 並更新排程狀態。見 [backend.md](./backend.md) `scheduler/`。

```mermaid
sequenceDiagram
    participant SCH as APScheduler
    participant J as run_scheduled_workflow
    participant E as Workflow 引擎
    participant DB as SQLite
    SCH->>J: 每 N 秒觸發(schedule_id)
    J->>DB: 載入 Workflow.graph
    J->>E: run_workflow(graph)
    E-->>J: RunResult
    J->>DB: 寫 RunLog + 更新 Schedule.last_status
```

## 工作流歷史回測(Workflow Backtest)

除了即時 / 紙上交易,工作流也可以以**歷史 K 線逐根重放**的方式執行,一次對圖中所有資產做**多資產共用現金組合回測**。

### 運作方式
引擎以 `BacktestContext` 取代一般 `RunContext`:
- `data_source` 節點:傳回截至當根為止的歷史切片(無前視偏差)。
- `order` 節點:記錄下單意圖,**不觸碰任何 broker**。
- `risk_exit` 節點:讀取模擬持倉。

每根 K 線執行完整圖後,各 `order` 節點所對應資產的訊號送入 `PortfolioSim`:
- **Equal-weight** 配置:現金平均分配給當下所有 active-long 的資產。
- **Next-bar-open 成交**:與單資產回測相同,無前視偏差。
- **交易成本**:與 `trading/costs.py` 的 `CostModel` 相同,預設開啟。

### 驗證規則(fail loud)
- 圖中需至少一個 `order` 節點。
- 每個 `order` 節點必須能解析到唯一一個 symbol。
- 所有 `data_source` 節點必須使用相同 `timeframe`。
- 歷史資料至少需 2 根對齊的 K 線。

### AI 節點限制
`ai_signal` 節點在回測中**每根 K 線都會呼叫 LLM**,故設有**最大 bar 數上限(預設 200 根)**;超過上限會 fail loud,避免大量 API 呼叫。

### 前端(交易室 workflow builder)
工作流編輯器右上角有 **Backtest** 按鈕:點擊後對當前圖執行歷史回測並顯示**權益曲線**。曲線上每個有訊號的時間點會出現可點擊的**買/賣標記(買/賣)**,點擊標記開啟側邊抽屜,呈現**逐節點衍生過程(node-by-node trace)**。頁面下方另有跑過的**回測歷史清單**可供重載。

## 執行記錄(Unified Run History)

所有工作流執行——無論是即時/紙上交易或歷史回測——皆以 `WorkflowRun` 型別持久化至 DB,每筆產生的訊號另存為 `WorkflowSignal`(含 `trace_json`:各節點的輸入輸出紀錄)。

| 記錄型別 | 說明 |
| --- | --- |
| `WorkflowRun` | 執行元資料:`run_id`、`kind`(`backtest`/`live`/`paper`)、`status`、`started_at`、`symbols`、回測指標摘要 |
| `WorkflowSignal` | 每個訊號:所屬 `run_id`、`symbol`、`action`、`confidence`、`bar_time`、`trace_json` |

讀取端點見 [api-reference.md](./api-reference.md) 的 Workflow Run History 段。

## API
建立/執行/排程見 [api-reference.md](./api-reference.md) 的 Workflows 與 Schedules 段。
