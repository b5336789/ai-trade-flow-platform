# AI Trade Flow — 平台全功能再評估與重設計藍圖

> **雙鏡頭:** 專業投資人／配置者(Lens A) × 資深前端設計師(Lens B)　|　**目標態:** 全景 full-vision（一個可被嚴肅資金信任的多市場 live 交易平台）
>
> **日期:** 2026-06-27　|　**性質:** 評估 + 重設計藍圖 + 優先路線圖（尚未動程式碼）

---

## 0. 方法論 — 這份藍圖怎麼來的

這不是憑感覺的點評。整份評估由 **31 個 agent** 對 **實際程式碼** 跑出來:

- **14 位領域分析師** — 每位負責一個功能域,先讀過該域的真實程式(frontend + backend),再以雙鏡頭評估。
- **14 道對抗式銳化(adversarial sharpening)** — 每個域交給一位更資深、更挑剔的審查者重讀程式碼,**刪掉與程式不符或過於空泛的指控、修正過重的 severity、替換 AI-slop 的重設計**。所以下面每一條 finding 都附上可查證的 `file:line` 或具體行為。
- **3 位綜合者** — 從 14 份銳化後的分析,合成「產品命題 / 北極星 IA / 優先路線圖」。

**判決尺度:** Keep（保留）/ Elevate（拉升）/ Rework（重做）/ Replace（替換）/ Add（新增）。**評分 1–5**(1 = 嚴肅使用者無法託付,5 = 機構級／craft-leading)。severity 以「serious live 平台」為基準——**資料完整性與資本安全的問題一律 critical/high**。

---

## 1. 執行摘要（先讀這頁）

**一句話結論:** 這是一個**地基紮實、但只蓋了「研究室」、還沒蓋「營運室」**的產品。它的核心 IP 是真的、且難複製——(1) 與 AI 對話即可收斂出一個 *never-executed、pydantic-validated* 的 `StrategySpec` 安全 DSL、(2) 一套**刻意抗自我欺騙**的 backtester(next-bar-open 無 look-ahead、costs 預設 ON、walk-forward 只用 train 選參、OOS 主動排除 raw-return ranking)、(3) 一條乾淨且 fail-loud 的 `Broker` 多市場 seam 配上 RiskGuard / FIFO ledger / TWD base-currency。**缺的不是地基,是把這套誠實研究包成「可被信任地下真錢」的整個 operations spine。** 因此 14 個域的判決高度一致:**13 個 Rework + 1 個 Add**,沒有一個域該打掉重練,但沒有一個域可以原樣上線真錢。

**雙鏡頭分數一面倒落在低分區**——投資人均分 **2.07/5**、設計均分 **2.29/5**;病灶高度收斂成一句話:**後端比 UI 誠實,而 UI 正在靜默丟棄後端的真相。**

### 五個你必須先知道的事實（最尖銳的）

1. **平台最大資產正在自我矛盾。** 同一張 workflow,**回測走一套下單系統、實盤走另一套**——backtest 是等權 all-in、忽略 order 節點的 quantity、每根 bar drift-rebalance、硬編 1h/500;live 是 delta-to-fixed-quantity、達標即 no-op。再加上 fantasy fills(limit 以限價即時全成、slippage 預設 0、long-only、無 per-signal sizing),**「回測賺錢」對「實盤會賺」幾乎不構成承諾。** 誠實 backtester 是護城河,但若其輸出不預測 live,護城河等於沒挖。
2. **真錢的財務真相是靜默壞掉的。** ccxt 完全成交回 `'closed'`,而 `execution.py` 只在 `status=='filled'` 才 `record_fill` → **live 的 FIFO realized-P&L ledger 永遠是空的**;且全平台**沒有任何 broker reconciliation**(內部 `OrderRecord` 與交易所實際持倉從不比對)——真錢部位是盲飛。這是 data-integrity = capital-safety 等級的 critical。
3. **paper↔live 這條產品脊椎,目前只是一個全域 env flag。** 把 server 翻成 `TRADING_MODE=live` 並重啟,會在**零 per-run 確認**下同時武裝所有 workflow、所有 schedule、編輯器的 ad-hoc Run。諷刺的對照:**送真實單零確認,刪一張 workflow 反而要 `confirm()`**——風險優先序完全顛倒。
4. **整層資本安全表面在 UI 裡根本不存在。** `/api/risk/*`(kill-switch / halt / 限額)三個端點後端齊備,**前端命中 0 次、無路由、無 nav**——最攸關安危的 kill-switch 只能 `curl`。`/api/ledger` 的 FIFO realized P&L + 報稅 CSV 也一樣:後端完整,前端無 api client 方法、nav 無 leaf。**「損益」這個域對使用者等於不存在。**
5. **AI 目前是 theater,不是可量測的 alpha。** 單發 LLM 訊號脈絡稀薄(無 volume/波動/多週期)、confidence 未校準卻以「72%」暗示機率、在 order 路徑被丟棄、**不可重現**(預設 opus-4-8 不收 temperature、無 seed)、provenance 在存檔時被銷毀(`source` 硬編 `manual`,所以那顆 cyan「AI」badge 在真實流程永遠不亮)。產品招牌(與 AI 對話設計)有淪為**不可證偽行銷**的風險。

### 接下來怎麼走

北極星很清楚:**保留兩室作為「上線前」脊椎(策略室 = 設計、交易室 = 驗證),新增第三個一級房間「監控室 Operations」承載整個「上線後」營運層,並用一條跨頁常駐的 Global Context Bar 把 market / mode / 權益 / 風控狀態變成任何一頁都不可錯認的事實。** 路線圖分三階段——**Now**(不碰任何 live broker,把 crypto+paper 切片做到 investor-grade)、**Next**(成交真實性 + 真風控 + 資料層 + live OMS/對帳)、**Vision**(可信 broker connectors + 上線治理 + live 績效歸因 + 不可竄改稽核)。詳見 §5(北極星 IA)與 §7(路線圖)。

---

## 2. 雙鏡頭評分矩陣（the re-evaluation）

| # | 功能域 | 投資人 | 設計 | 判決 | 一句話現況 |
|---|--------|:------:|:----:|:----:|------------|
| 1 | **策略室 Strategy Lab** | ●●○○○ 2 | ●●●○○ 3 | `Rework` | 底層是一套安全(never-executed、pydantic-validated、fail-loud)的 whitelisted-indicator D… |
| 2 | **回測 Backtest** | ●●●○○ 3 | ●●●○○ 3 | `Rework` | 引擎核心是誠實的(next-bar-open 無前視、交易成本預設 ON、walk-forward 在 fold 內未用 OOS 選參),但對外是一個「每… |
| 3 | **工作流 Workflow Builder** | ●●○○○ 2 | ●●○○○ 2 | `Rework` | 一個工程乾淨的 per-tick 決策函式(topo 排序、fail-loud、idempotent target-position、AI 與指標策略同型… |
| 4 | **市場 Market** | ●●○○○ 2 | ●●●○○ 3 | `Rework` | 圖表引擎（lightweight-charts，多副圖同步、theme-reactive、暖機 null fail-loud、market-aware -… |
| 5 | **投組 Portfolio + Ledger** | ●●○○○ 2 | ●●○○○ 2 | `Rework` | 後端 FIFO ledger、FX seam(已在 /api/risk/status 以 base-currency 暴露「單市場」equity_base… |
| 6 | **風控 Risk** | ●●○○○ 2 | ●○○○○ 1 | `Rework` | 後端有真實但僅及零售級的「下單前」風控骨架(kill switch / halt / 單日虧損 / 曝險 / FX base-ccy / exit-alw… |
| 7 | **排程 Schedules** | ●●○○○ 2 | ●●○○○ 2 | `Rework` | 後端排程有經過思考的原語(coalesce / max_instances=1 / misfire grace / target-position 冪等 … |
| 8 | **通知 Notifications** | ●●○○○ 2 | ●●○○○ 2 | `Rework` | 通知是一條被動、每 5 秒輪詢、藏在「工具」第二層的 read-only 流水帳:portfolio 級風控閘門(kill switch/halt/日損/… |
| 9 | **匯入 Data / Market-data** | ●●○○○ 2 | ●●○○○ 2 | `Rework` | 台股/美股 的資料層仍是「貼 CSV → 存進 process-local dict → 重啟即清空」的 demo:沒有 timeframe 維度、沒有 … |
| 10 | **AI 層** | ●●○○○ 2 | ●●●○○ 3 | `Rework` | strategy_agent 的 never-executed StrategySpec DSL 是扎實的安全地基,但 signal_agent 的單發 … |
| 11 | **Shell / IA / 設計系統** | ●●○○○ 2 | ●●●○○ 3 | `Rework` | design-token 地基扎實(完整 dark/light/market-aware 調色、mono tabular、tight radii、no-f… |
| 12 | **執行真實性 Execution** | ●●○○○ 2 | ●●○○○ 2 | `Rework` | 回測地基比第一版評估認定的更紮實——除無 look-ahead 的單序列 run_backtest 外,還有一條真實的 shared-cash 多資產 p… |
| 13 | **多市場 Brokers / Live** | ●●○○○ 2 | ●●○○○ 2 | `Rework` | Broker ABC seam 乾淨且 fail-loud 誠實,但只有 crypto paper 真正能跑;live 路徑缺 OMS / 成交對帳 / … |
| 14 | **全景新功能 New Features** | ●●○○○ 2 | ●●○○○ 2 | `Add` | 這是一套扎實的「策略設計 + 回測 + 紙上交易」引擎,但幾乎缺席整個「真錢營運層」— 沒有對帳、沒有 live 績效歸因、沒有上線治理、沒有稽核、沒有資… |

> **讀法:** ●=分數。投資人均分 **2.07**、設計均分 **2.29**。設計最低分是 **風控(1/5)**——因為它在 UI 上幾乎不存在;投資人最高也只到 3(Backtest——唯一真正紮實的引擎,但統計誠實的原語沒被設成預設路徑)。**全盤 Rework** 不代表「做得爛」,而代表「對的後端原語,壞在對外那一層」。

---

## 3. 產品命題 Product Thesis

### 3.1 這個平台正在成為什麼

這個平台正在成為的,不是「又一個 crypto bot」或「又一個畫圖工具」,而是一套**誠實優先(honesty-first)的 AI 策略工作室**——其差異化 DNA 由三件被實際寫進程式碼、而非投影片的東西構成:(1) 與 AI 對話即可把白話想法收斂成一個 *never-executed、pydantic-validated、whitelisted-indicator* 的 `StrategySpec` DSL(`strategies/spec.py`),把「AI 生成策略」這件危險事降維成可被信任的安全表示,且 AI agent 與 indicator 策略輸出同型的 `Signal`、在 workflow 內可互換;(2) 一套刻意抗自我欺騙的 backtester——`backtest/engine.py` next-bar-open 無 look-ahead、transaction costs 預設 ON、`validation.py` 的 walk-forward 在 fold 內只用 train 選參、OOS 只評分,且 `selection_score` 主動排除 raw return(註解直言 raw-return ranking 正是它要消滅的 overfitting trap);(3) `brokers/base.py:Broker` 這個乾淨且 fail-loud 的單一 seam,加上 RiskGuard/PortfolioGuard/kill-switch/FIFO ledger/base-currency(TWD)FX——一個多市場帳務骨架的雛形。這三者疊起來的命題是:**「讓半專業交易者用 AI 加速 idea→spec,再用一個不會騙自己的回測證明 edge,最後在受治理的邊界上跑真錢。」**

但必須對創辦人直說:今天的它是一個*誠實的研究與紙上交易引擎*,distance-to-target 幾乎完全落在「從誠實研究 → 可信賴的真錢營運」這道鴻溝上,而這道鴻溝在每一個 domain 都以同一種形狀復現。最致命的是平台最大資產(那個誠實 backtester)正在自我矛盾:workflow backtest 走 `PortfolioSim` 等權 all-in、忽略 order 節點的 quantity、每根 bar drift-rebalance,而 live 走 delta-to-fixed-quantity——**同一張圖的回測與實盤是兩套下單系統**;再加上 fantasy fills(limit 以限價即時全成、slippage 預設 0、long-only、無 per-signal sizing)與不可重現的 AI 回測,使得「回測賺錢」對「實盤會賺」幾乎不構成承諾。更深一層,真錢的*財務真相*本身是靜默壞掉的:ccxt 對完全成交回 `'closed'`,而 `execution.py` 只在 `status=='filled'` 才 record_fill,所以 **live 的 FIFO realized-P&L ledger 永遠是空的**,且全平台沒有 reconciliation——真錢部位是盲飛。最後,paper↔live 這條本該是產品脊椎的信任邊界,目前只是一個 server 全域 env flag:翻成 live 並重啟,所有既存 workflow、所有 schedule、編輯器的 ad-hoc Run 會在零 per-run 確認下同時被武裝。換句話說,**核心 IP(誠實、AI-safe-spec、多市場 seam)是真的、且難複製;缺的是把它包成「可被信任地下真錢」的整個 operations spine。** 這是一個「地基紮實、但只蓋了研究室、還沒蓋營運室」的產品。

### 3.2 最鋒利的使用者是誰

最鋒利的使用者**不是** 3Commas 那種只想複製跟單/grid 機器人的散戶,也**不是**會直接用 QuantConnect Lean 寫 Python、自己接 IBKR 的機構級 quant——這兩端它都服務不好。真正的 sharpest user 是**「台灣本位、quant-curious 的半專業系統化交易者 / builder」**:技術夠強到看得懂並且*在乎* walk-forward、OOS、transaction costs、num_trades 與 fail-loud(會被「單次 in-sample +40%、0 num_trades 卻顯示勝率 0%」這種假精度激怒的人),但又不想為了驗證一個想法去啃 Lean 的 boilerplate;他從 TWD base-currency 出發、同時想跑 crypto 與台股(在意 紅漲綠跌、證交稅、漲跌停),覺得 TradingView 的 Pine strategy tester 太樂觀、QuantConnect 太 code-heavy 又太美股中心、3Commas 太笨、Composer 太封閉又只有美股 ETF。他要的是**「不需要 PhD 的統計誠實 + AI 把白話變成可調 spec + 台股原生」**,並且願意在證明 edge 後拿*小額*真錢無人值守地跑。產品的 AI 對話設計降低了入門門檻、誠實 backtester 又設了能力門檻——這個交集精準地框出「懂一點、認真、但不是專職」的這群人。風險是:若 AI signal 始終是 theater(無 calibration、無證據贏過 indicator),這群恰恰最會驗證的人會第一個識破;若真錢營運層補不上,他們會停在 paper 而永不轉化。

### 3.3 對標定位（誠實分流,而非全面宣戰）

對標五家應採「誠實分流」而非全面宣戰:**TradingView**——對方贏在 data depth、real-time WS、screener、社群;本平台不該在畫圖上硬碰,而是吃下「Pine strategy tester 會給你樂觀數字,我們給你不會騙自己的 walk-forward/OOS + costs-ON 回測,外加 AI 把白話變成可調策略」這個誠實縫隙(且 TradingView 沒有 AI-design + 自動下單的閉環)。**QuantConnect**——這是能力上的天花板對照(Lean、真資料、live brokers、機構級),本平台的定位必須是它的「低代碼、AI 對話、台股原生、且 AI 不執行任意程式(safe `StrategySpec`)」的近民版;在 data/live 成熟度上認輸,在 approachability + 在地市場 + 安全表示上取勝。**Composer**——這是**最危險也最貼近的對手**:同樣 no-code、自動配置、接真實 brokerage(Alpaca);本平台真正的一句話定位就是「**Composer for 台股/crypto,前面加一個 AI 對話設計層、底層換成誠實優先的 backtester**」——但必須承認 Composer 的 operations spine(live 配置、對帳、券商整合)遠遠領先,這正是 roadmap 的北極星。**3Commas**——對方 live 執行成熟、交易所整合多;本平台的差異是「先證明 edge 再上線」的紀律(真 backtester + RiskGuard + promotion gate),賣點是嚴謹而非機器人數量,但要誠實面對 live 訂單成熟度落後一大截。**Bloomberg**——不是功能對手,而是**美學北極星**:DESIGN.md 的 refined-terminal(tight radii、mono tabular-nums、cyan 專屬 AI、dark-first)借的是「precision instrument」的身分氣場,不該被定位成 Bloomberg 的替代品。總結一句:**「把 Composer 的自動化、QuantConnect 的統計誠實、TradingView 的可親近度,壓進一個台股原生、AI-first 的精煉終端機」**——但目前只兌現了誠實與 AI-first,自動化與在地 live 還是承諾。

### 3.4 最大的幾個風險

- 核心信任資產自我矛盾(最高優先):平台最大賣點是誠實 backtester,但 workflow backtest(等權 all-in、忽略 order quantity、每根 bar drift-rebalance、固定 1h/500、忽略節點 timeframe)與 live(delta-to-fixed-quantity、達標即 no-op)是兩套下單系統,再加 fantasy fills(limit 即時全成、slippage 預設 0、long-only、無 sizing)與不可重現的 AI 回測——一旦使用者發現 backtest 不預測 live,整個價值主張歸零。
- 真錢財務真相靜默壞掉(data-integrity = capital-safety):ccxt 完全成交回 'closed' 而 execution.py 只在 'filled' 才 record_fill,導致 live FIFO realized-P&L ledger 永遠是空的;全平台無 broker reconciliation(真實部位盲飛);portfolio 取價失敗靜默退回 avg_price 且被風控當市值用;reset 留下 ghost FIFO lot 與 stale daily-loss baseline。真錢帳本既空又無對帳。
- paper↔live 沒有真正的信任邊界與治理:trading mode 是單一全域 env flag,翻成 live 即一次武裝所有 workflow+schedule、零 per-run 確認、無 arming gate、無 promotion gate;整個 /api/risk、/api/ledger、kill-switch UI 是後端獨有、前端 0 次呼叫;風控是 lazy pre-trade 而非 continuous monitor;無人值守 scheduler 失敗多在 notify 未覆蓋的那層靜默。DESIGN.md 規格的 LIVE 安全態幾乎沒實作。
- 非 crypto 市場的資料層撐不起多市場 live:台股/美股 OHLCV 存 process-local dict(重啟即清空)、無 timeframe 維度(日線當 1h 回測 → Sharpe 高估約 4.9x)、無 OHLC 健全性驗證、無 corporate-action 還原(假崩盤/假跳空)、無真實 vendor、天生 survivorship bias;live broker 全 raise NotImplementedError。所謂三市場其實是一個真市場 + 兩個 scaffold。
- AI 是 theater 而非可量測的 alpha:單發 LLM 訊號脈絡稀薄(無 volume/波動/多週期、不傳 timeframe)、confidence 未校準卻以『72%』暗示機率、在 order 路徑被丟棄、不可重現(預設 opus-4-8 不收 temperature、Anthropic 無 seed)、provenance 在存檔時被銷毀(source 硬編 manual)、無成本計量、也無任何證據顯示贏過 indicator 或隨機——產品招牌(與 AI 對話設計)有淪為不可證偽行銷的風險。
- refined-terminal 身分『有規不守』,稀釋識別:cyan(規定 AI 專屬)在多個房間被誤用於非 AI 的 toggle/CTA;--up/--down 價格 token 被當狀態色(在台股 data-market=tw 下把『成功/上漲』渲染成紅);data-market 跨頁殘留把 crypto 損益畫成台股反轉色;native confirm()/select、raw JSON dump、缺 aria-live。紀律寫在 DESIGN.md,但落地不均,『精煉終端機』目前是 aspiration 多於 reality。

### 3.5 橫切六大主題（病灶為何在每個域復現）

- **後端比 UI 誠實,而 UI 靜默丟棄後端的真相** — 反覆出現:num_trades/equity_curve/sharpe 已算好卻不渲染(策略室卡片只印單次 in-sample 報酬);/api/risk、/api/ledger、RiskStatus 完整卻前端 0 次呼叫、無路由、無 nav;price_source='avg_fallback' 旗標被忽略;fee/tax 算完即丟、OrderRecord 無此欄;RunLog 無讀取端點。平台系統性地 under-render 自己的 integrity,使最該被信任的數據對使用者不可見。
- **paper↔live 信任邊界是產品脊椎,卻在結構上缺席** — 在 workflow / risk / schedules / brokers / notifications / full-vision 全部復現同一缺口:mode = 全域 env、無 per-run authority、無 arming/promotion gate、無 reconciliation、無 continuous risk、標籤背離(paper『執行回測』實為下單)、live 訊號未上提到 shell。這是『serious live』與『demo』的分水嶺,也是目前最大的單一結構債。
- **backtest↔live 語意鴻溝 + fantasy fills,侵蝕唯一可信資產** — sizing(等權 vs 固定 quantity)、rebalance(drift vs no-op)、timeframe(忽略節點值)、fills(limit 即時全成、slippage=0、long-only)、AI 回測不可重現——全都讓回測結果無法轉移到實盤。誠實 backtester 是護城河,但若其輸出不預測 live,護城河等於沒挖。
- **統計誠實的原語已建好,卻不是預設路徑、也未端到端串接** — validation.py 的 walk-forward/OOS、metrics.py 的 risk-adjusted 指標都在,但策略室卡片、workflow backtest、AI backtest 都沒接上;單次 in-sample『+40%』當頭條、compare 以 raw return 排名掛🏆、slippage=0 預設被隱藏、股市年化用 365.25 而非 252、optimize split 的 OOS 已被測試窗挑選成樂觀上界。誠實工具存在,但不是使用者實際走的那條路。
- **provenance / versioning / audit / reconciliation 全面缺席——沒有任何東西是 asset of record** — 策略 source 硬編 manual、原始 NL prompt 與 AI explanation 存檔即丟、無 immutable version/lineage(live 中策略可被無聲覆寫)、無 immutable audit log(kill-switch/halt 就地覆寫不留 actor)、無 broker reconciliation、AI token/cost 不計量。一個要下真錢、要可回放、要可報稅的平台,目前沒有任何可稽核的記錄之錨。
- **DESIGN.md 的 token 紀律(cyan=AI、--up/--down 僅價格、fail-loud)寫得到位但執行不均** — accent 作裝飾滲漏(指標 toggle、Save CTA、匯入按鈕)、--up 被當狀態色(台股反轉成紅而誤讀成功/獲利)、data-market 跨頁殘留翻轉投組配色、native confirm()/select 破壞質感、缺 aria-live/focus-trap、raw JSON 取代該發光的 AI rationale。『refined terminal』的身分目前是 aspiration 與 reality 並存。
- **多市場是身分主張,現實是一個真市場 + 兩個 scaffold** — 台股/美股 live broker 全 raise NotImplementedError、資料 process-local 無 timeframe/無公司行動、RiskGuard 幣別不一致(同一個 50000 在 crypto 是 50k USDT、台股是 50k TWD,差約 31x)、日界用 UTC 切錯台股/美股 session、ledger 跨幣別直接相加、builder 無 market 路由。要兌現 crypto/台股/美股 的承諾,需要把 data vendor、券商 connector、幣別/session 正規化補成真實。

---

## 4. 分域深入 Per-Domain Deep Dives

> 每個域:現況 → 投資人鏡頭發現 → 設計鏡頭發現 → 重設計提案 →(若有)新功能。所有 finding 依 severity 排序,並附程式碼證據。

### D1. 策略室 Strategy Lab(AI 設計 + 策略庫)

**現況:** 底層是一套安全(never-executed、pydantic-validated、fail-loud)的 whitelisted-indicator DSL,外加堪用的對話與卡片庫;但 provenance 永遠斷成 "manual"、無版本/lineage、UI 無編輯路徑、AI 被 system prompt 誤導(推非法 eq|ne、藏起已支援的 cross),卡片把單次 in-sample 報酬當頭條卻丟掉後端已回傳的 num_trades/equity_curve——可探索,尚不可作為可信賴的可重用交易資產。

**評分:** 投資人 `2/5` · 設計 `3/5`　|　**判決: `Rework`**

**最高槓桿動作:**
- 修復 provenance 並把策略庫變成 asset of record:save 路徑正確標記 source="ai"、持久化原始 NL prompt + AI explanation + spec_hash(StrategyDef 加欄位),導入 immutable 版本與 parent_id lineage,並把已存在但 UI 無人呼叫的 PUT /api/strategies/{sid} 接成 api.updateStrategy,做出『更新 vs 另存為 vN』,終結孤兒分身。
- 補齊統計誠實:卡片改印後端已回傳的 num_trades/期間/成本ON/equity sparkline 並對 0-trade fail-loud,把策略室接上底層 walk-forward/OOS backtester 並在未跑 OOS 前顯示 ⚠——別再讓單次 in-sample『+40%』當頭條誤導真實資金決策。
- 修 AI 表達力與動線:strategy_agent.py system prompt 移除非法 eq|ne、明教 cross_above/cross_below/between(interpreter/render 都已支援),讓使用者把任意 literal 升級為可調 param;策略室掛 setMarket 讓台股配色正確反轉;把『設計→回測』做成面板內存檔後可直接觸發的單一動作,取代永遠灰掉的 CTA + 捲到卡片的交接。

**投資人鏡頭 — 發現**

- **🔴 critical** — 策略庫卡片把『單次 in-sample 報酬』當頭條,且丟棄後端已算好的脈絡:backtestSavedStrategy 硬編 timeframe "1h"、limit 300、不傳 param_overrides,卡面只渲染 報酬/B&H/回撤/勝率 四格,完全沒印出 num_trades、期間、成本、symbol/timeframe 標註——而這些 BacktestResult 全都有(num_trades/sharpe/calmar/equity_curve/exposure_pct)。更嚴重:num_trades=0(規則從未觸發)會被靜默顯示成『報酬 +0.00% / 勝率 0%』,看似一支平庸但有效的策略,違反 fail-loud。底層那套真正 solid 的 walk-forward/OOS/grid-optimize backtester 在策略室完全沒被接上。一個沒有樣本數、不分 in/out-of-sample、不標的的『+40%』會誘導使用者把過度擬合當成 edge,並據此投入真實資金。
  - 〔證據〕`StrategyLibrary.tsx L26-30 mutation 只送 {symbol,market,timeframe:"1h",limit:300};L91-98 僅 4 個 Metric,無 num_trades/期間/成本/symbol 標註;backtest/engine.py L41/L48/L57 BacktestResult 已含 num_trades/sharpe/calmar/equity_curve 但未被渲染;api/strategies.py L128-139 只呼叫 run_backtest(單次 in-sample),未接 optimize.py/validation.py 的 walk-forward/OOS`
- **🟠 high** — AI 表達力被 system prompt 主動誤導,而非被 DSL 限制:strategy_agent.py 的 op 清單寫成 "lt|le|gt|ge|eq|ne"——其中 eq|ne 根本不在 CmpOp enum 內(會被 pydantic 拒絕、觸發 Instructor 重試甚至硬失敗),而真正支援、且 interpreter(_eval cross/between)與 render(cross 以函式形式輸出)都實作好的 cross_above/cross_below/between 卻完全沒被提及。結果:三個示範 prompt 之一『20 日均線向上穿越 60 日均線』這種 MA cross,模型被偏置成退化的 sma_fast > sma_slow(『快線在上方每根 K 觸發』而非『穿越當下進場』),語意完全失真。另一示範『回到布林中軌賣出』則撞到 whitelist 缺口——只有 bollinger_hi/bollinger_lo、無中軌,macd 也只有主線、無 signal/histogram,所以黃金交叉類策略結構上做不出來。對 serious 平台這是 correctness + 可靠度雙重風險。
  - 〔證據〕`strategy_agent.py L24 system prompt op:"lt|le|gt|ge|eq|ne" vs spec.py L52-60 CmpOp 僅含 lt/le/gt/ge/cross_above/cross_below/between(無 eq/ne);spec.py L260-268 _eval 完整實作 cross/between;spec_render.py L33 cross 以 cross_above(a,b) 形式輸出(可呈現);indicator whitelist spec.py L41-49 無 bollinger 中軌與 macd signal/hist;EXAMPLES DesignChat.tsx L17-21 含 MA cross 與布林中軌兩例`
- **🟠 high** — Provenance 永久斷裂:create() 硬編 source="manual"、SaveRequest 無 source 欄位,所以每一支 AI 設計後存檔的策略在 DB 都是 "manual",策略庫用來標來源的 cyan『AI』badge 在真實流程永遠不會亮(只有測試碼寫過 source="ai")。同時產生它的原始白話 prompt 與 AI explanation 在存檔當下被丟棄——StrategyDef 只有 name/description/spec_json/source/created_at/updated_at,沒有 prompt/explanation 欄位,事後無法回答『我當初叫 AI 做了什麼才得到這支』。
  - 〔證據〕`api/strategies.py L87 create() 硬編 source="manual";SaveRequest L36-39 無 source;StrategyLibrary.tsx L78-84 AI badge 依賴 s.source==="ai";models.py StrategyDef 欄位僅 id/name/description/spec_json/source/created_at/updated_at(無 prompt/explanation)`
- **🟠 high** — 無版本/lineage,且 UI 編輯路徑是死的:後端其實有 PUT /api/strategies/{sid} 與 library.update_strategy,但 api.ts 沒有暴露任何 updateStrategy(唯一 PUT 是 /api/workflows),GeneratedStrategy.save 永遠走 POST 新建。所謂『載入→用 AI 調整→另存』實際是建立一支與原策略毫無 parent/lineage 的重複資料(載入時 id 也丟失);即便那個 PUT 被接上,update_strategy 也是就地覆寫 spec_json、無歷史可 diff/revert。作為 asset of record,缺 immutable version、lineage 與 diff。
  - 〔證據〕`api.ts L436 唯一 PUT 為 workflows;api.ts L463-473 strategy client 無 updateStrategy;GeneratedStrategy.tsx L18-28 save 只呼叫 api.saveStrategy(POST)、未持有 loaded id;library.py L30-45 update_strategy 就地覆寫 spec_json 無版本表`
- **🟡 medium** — StrategySpec 結構上裝不下風控:entry/exit 只是 indicator 的布林條件樹,沒有 stop-loss/take-profit/position size/time filter/holding period 的概念;SpecStrategy.generate 只回 buy/sell/hold。保護性出場只活在 workflow 的 risk_exit 節點,因此一支 AI『策略』資產對 live trading 而言結構性不完整——它連停損都寫不進自己。
  - 〔證據〕`spec.py L158-162 StrategySpec 僅 indicators/entry/exit/params;spec.py L270-282 generate 只回 buy/sell/hold,無 stop/target/size`
- **🟡 medium** — 關鍵閾值能不能被 tune,由 AI 隨機決定:面板只把 spec.params 渲染成可調;若 AI 把數字烤成 LiteralRef(如 rsi<30 的 30 是 literal),render_python 直接 inline repr,UI 永遠調不到它。更糟:system prompt 的示範本身就把 RSI 30 寫成 {"type":"literal","value":30},等於教模型把最常見策略的閾值烤死,卡片於是顯示『0 個可調參數』。
  - 〔證據〕`GeneratedStrategy.tsx L64-100 只迭代 spec.params;spec_render.py L18-23 _operand 對 LiteralRef 回 repr(value);strategy_agent.py L27 示範 entry 用 literal 30;StrategyLibrary.tsx L89 顯示 num_params`
- **🔵 low** — Spec 策略的 confidence 是二元的(buy=1.0 / hold=0.0),與會輸出漸進信心的 AI-signal agent 不對稱。CLAUDE.md 宣稱兩者可在 workflow 互換,但任何依 conf≥threshold 分支的流程裡,spec 策略只能 all-or-nothing,無法做信心加權的部位或過濾。
  - 〔證據〕`spec.py L279-282 generate 回傳 confidence=1.0/0.0`
- **🔵 low** — 存檔的 param default 不受 min/max 驗證:updateParamDefault 直接存 Number(value);ParamDef 無 default∈[min,max] 的 validator,SpecStrategy.__init__ 只驗證 runtime overrides、持久化 default 直接進 self.params。可存進一個低於 min 的預設值,之後不帶 override 回測時就用了越界值,且後端也照單全收。
  - 〔證據〕`GeneratedStrategy.tsx L38-44 updateParamDefault 存 Number 無檢查;spec.py L90-99 ParamDef 無 default 邊界 validator;spec.py L199 self.params 直接取 p.default;L205-209 只在 overrides 迴圈驗 min/max`

**設計鏡頭 — 發現**

- **🟠 high** — 台股方向性 token 在策略室不會反轉,違反 DESIGN.md 的非協商規則:StrategyLibrary 的 market 下拉提供 tw_stock,但元件從未呼叫 setMarket,所以針對它自己選的 tw_stock 從不設 data-market='tw' → 台股的 報酬/回撤 用預設 green=up/red=down 渲染,把『紅漲綠跌』的台股收益讀反。反向也成立:若使用者先在別的房間選了台股(setMarket 改了 <html> 的 data-market,App Router soft-nav 不重置),回到策略室時 crypto 結果會被套上台股反轉色。DESIGN.md 明文要求『切換 market 必須設 data-market』。
  - 〔證據〕`StrategyLibrary.tsx L49-59 market select 用 MARKETS(含 tw_stock)但全檔無 setMarket import/呼叫;L93 報酬 positive 依數值、L95 回撤 positive={false},皆走 text-up/text-down,只有 data-market='tw' 時才反轉;useMarket.ts setMarket 只在 market==='tw_stock' 設 data-market;DESIGN.md L102-104『Switching the market... must set data-market』`
- **🟡 medium** — 核心『設計→驗證』迴圈擺了一顆永遠壞掉的主 CTA + 卡頓交接:GeneratedStrategy 的『拿去回測 →』被硬編 disabled、緊貼亮色 accent 的 Save 旁,真正可用入口是下方策略庫卡片裡另一顆按鈕,成功提示還直接叫使用者『到下方策略庫點拿去回測』往下捲。一顆永遠灰掉的主視覺 CTA 讀作 broken,而非 intentional gating;在『refined terminal』裡這是質感破口。
  - 〔證據〕`GeneratedStrategy.tsx L118-125『拿去回測』button 寫死 disabled+opacity-50,僅用 title 傳達;L136 成功提示『到下方策略庫點拿去回測』;真正入口在 StrategyLibrary.tsx L103-113 router.push`
- **🟡 medium** — 策略的『規則本體』不可編輯且被當成程式碼呈現:entry/exit 條件樹只藏在唯讀、且明示『不執行任意程式』的 display-only pseudo-Python(def generate_signal(df,...))裡,對非工程使用者讀作 code 而非規則;explanation 段落在 chat、不在面板;面板只讓人調 param。要『理解/信任/編輯 AI 做了什麼』其實改不到規則。註:DESIGN.md L26-29 目前正是明訂『code block + 可調參數表』,故 rules-first 視圖屬於需核准的 DESIGN.md 演進,非單純 bug。
  - 〔證據〕`GeneratedStrategy.tsx L57-62 唯讀 <pre> + L51-53 badge『不執行任意程式』;L64-100 只渲染 params table;entry/exit tree 無人類可讀可編輯視圖;DESIGN.md L26-29『code block + adjustable parameter table』`
- **🟡 medium** — 設計 session 不持久:chat messages 與 design 都是 local React useState,refresh 或離開頁面整段對話即消失,只有存檔的 spec 能存活。多輪迭代(這房間的核心價值)是 volatile 的;且每次只送 priorSpec(非完整 history),所以『退回上一個版本』做不到。
  - 〔證據〕`DesignChat.tsx L24 useState messages、StrategyLab.tsx L12 useState design 皆無持久化;DesignChat.tsx L29 designStrategy 只帶 priorSpec`
- **🟡 medium** — 快速回測卡片 data density 不足以支撐信任:只有 4 個數字,沒有 num_trades、期間、成本註記、equity sparkline——而 num_trades 與 equity_curve 後端已回傳;報酬數字也沒標是用哪個 symbol/timeframe 跑的(改完 symbol 後卡片數字會 stale 而無提示)。在一個強調統計誠實的終端機裡,卻不給任何判讀基礎。
  - 〔證據〕`StrategyLibrary.tsx L91-98 metric grid 僅 報酬/B&H/回撤/勝率;backtest/engine.py L41/L57 已回傳 num_trades/equity_curve;卡片 results 以 id 為 key 但 symbol/timeframe 為 lab 級 state,改值後不重跑也不標註`
- **🔵 low** — Accent 誤用:『存入策略庫』主 CTA 用 bg-accent。Save 是 CRUD,不是 AI/automation;DESIGN.md 規定 cyan 為 AI 專屬(chat/AI 生成 badge/Run/strategy nodes)。在最該守規則的房間把 Save 漆成 accent,稀釋了『accent = AI 正在動作』的語意。(回測/Run 用 accent 是 DESIGN 允許的,故不在此列。)
  - 〔證據〕`GeneratedStrategy.tsx L111-117 Save 按鈕 className 含 bg-accent;DESIGN.md L73-75『--accent RESERVED for AI/automation only』`
- **🔵 low** — 刪除用原生 confirm():打斷 refined-terminal 質感,無法套主題/樣式,與 dark dense 介面格格不入。
  - 〔證據〕`StrategyLibrary.tsx L130 confirm(`刪除策略「${s.name}」?`)`
- **🔵 low** — 可及性與 loading craft 缺口:『AI 生成中…』與 error bubble 都無 aria-live,螢幕閱讀器不會播報;disabled 的『拿去回測』只靠 title 傳狀態(觸控不可見);生成中右側 GeneratedStrategy 面板沒有 skeleton,維持空白或上一支策略的 stale 狀態,只有 chat 顯示進行中。正面:DesignChat 的 IME isComposing 防誤送與 param 用真正的 <table> 是不錯的 craft。
  - 〔證據〕`DesignChat.tsx L90-95 生成中提示無 aria-live;GeneratedStrategy.tsx L118-125 disabled 僅 title;DesignChat.tsx L108-114 isComposing 防護(正面)、L105-118 textarea + <table> L67-98`

**重設計提案**

把策略室從『對話玩具 + 卡片堆』升級為『可信賴的交易資產工廠』,三條主線:provenance + 版本、規則優先(需核准的 DESIGN.md 演進)、驗證閘門(validation gate)。每一條都對應上面已驗證的具體缺口。

1) Provenance + 版本(最高槓桿,純後端 + 薄前端)。在 save 路徑帶上 source(AI 設計即 \"ai\",修掉 api/strategies.py L87 硬編),SaveRequest 加 source/prompt/explanation/spec_hash 欄位並在 StrategyDef 持久化(models.py 加欄位),讓策略庫卡片的 cyan『AI』badge 在真實流程會亮、且能回答『當初叫 AI 做了什麼』。引入 immutable version + parent_id lineage;前端補上 api.updateStrategy(接已存在但無人呼叫的 PUT /api/strategies/{sid}),GeneratedStrategy 在『載入』時記住 id,footer 給兩個明確動作:『更新原策略』與『另存為 vN』,終結孤兒分身。

2) 規則優先面板(提請 DESIGN.md 加一條 decision-log;目前 L26-29 只規定 code block + param table)。把策略靈魂(entry/exit 條件樹)變成一級、可讀、可就地編輯的物件,並讓使用者把任意 LiteralRef『升級成可調參數』(解決閾值不可 tune 的死角)。Python 預覽降為次要、預設摺疊的唯讀檢視(保留『不執行任意程式』badge)。footer 加 來源 與 驗證 兩條狀態列。

```
┌─ 生成的策略 ───────────── declarative spec · AI 生成 ──┐
│ ▸ 規則(人類可讀,可編輯)                              │
│   進場  rsi(14) cross_below  oversold[30]        ✎      │
│   出場  rsi(14)      >        exit_lvl[70]        ✎      │
│        ＋加條件   ｜  把「30」→ 參數                     │
│ ▸ 可調參數                                              │
│   oversold int 5…40 [ 30 ]    exit_lvl int 60…95 [ 70 ] │
│ ▸ Python(唯讀,僅供檢視)                  [展開 ▾]     │
│ ▸ 來源  AI ·「RSI 低於30進場、高於70出場」· v3↰v2↰v1   │
│ ▸ 驗證  OOS 未跑 ⚠ · 6 筆交易 · 90d · 成本ON           │
├────────────────────────────────────────────────────────┤
│ [策略名稱       ][描述(選填)     ]  另存為 v4 ｜ 更新  │
└────────────────────────────────────────────────────────┘
```

3) 驗證閘門 + 誠實的卡片。把卡片接到底層已 solid 的 backtester:策略在『未跑過 OOS』前 footer 顯示 ⚠;卡片不再只印單次 in-sample 報酬,改為呈現後端早已回傳但被丟棄的 num_trades + 期間 + 成本ON 標記 + 一條 equity_curve sparkline,並對 num_trades=0 fail-loud(『0 筆交易 — 規則從未觸發』而非偽裝成平盤)。timeframe 隨 market 改(別再對 tw_stock 硬塞 \"1h\"),數字旁標註用哪個 symbol/timeframe 跑的。卡片渲染前在策略室掛 setMarket(market),讓台股回測的 --up/--down 正確反轉(紅漲綠跌),回撤與報酬配色才不會誤導。

4) AI 表達力 + 動線收尾。修 strategy_agent.py 的 system prompt:移除不存在的 eq|ne、明確教模型使用 cross_above/cross_below/between(這些 interpreter 與 render 都已支援),並補上 bollinger 中軌 / macd signal 的 whitelist 缺口或在 prompt 註明如何近似。啟用『拿去回測』——存檔後即可直接從面板進回測(取代灰按鈕 + 往下捲);Save 主 CTA 從 bg-accent 改中性主按鈕樣式,讓 cyan 回歸 AI 專屬;delete 改 themed 確認 popover 取代原生 confirm();為『AI 生成中…』與 error 加 aria-live,生成時右側面板上 skeleton。

<br>

### D2. 回測 Backtest (single / compare / optimize / walk-forward)

**現況:** 引擎核心是誠實的(next-bar-open 無前視、交易成本預設 ON、walk-forward 在 fold 內未用 OOS 選參),但對外是一個「每跑一次就清空其餘結果、不留任何稽核軌跡」的暫態面板;且三項統計失真——零滑價預設、compare 以原始報酬掛 🏆、股市年化用 365.25 而非 252——讓它距離能託付真實資金的標準仍有實質落差。

**評分:** 投資人 `3/5` · 設計 `3/5`　|　**判決: `Rework`**

**最高槓桿動作:**
- 統計誠實性硬化(capital-safety 等級):給滑價一個非零可信預設並加成本敏感度測試(對應 config.py:156 預設 0)、把 compare 從原始報酬排名改為 Sharpe 排名並在 CompareRow 補 sharpe + Buy&Hold 欄(backtest.py:127-134/184,移除誤導性 🏆)、股市年化改 252 日(metrics.py:23)、並對 optimize/walk-forward 加多重檢定揭露(明示 split 的 OOS 是被挑選過的樂觀上界)。
- 持久化、可重現的 BacktestRun:每次執行快照 candle 區間 + cost 參數(taker/slippage)+ 策略版本寫入 DB(沿用 persist_workflow_run 模式),提供 run history 與跨 run overlay,取代 resetOutputs 造成的暫態互斥分頁,讓任何可能用來合理化真實資金的結果都可稽核、可重現。
- 量化 table-stakes 視覺與控制:權益圖疊 Buy&Hold(對等扣成本)+ underwater drawdown 子圖(複用 PriceChart 副圖同步模式)、walk-forward 串接連續 OOS 權益曲線 + fold 一致性統計、optimize 改 parameter-stability heatmap、trades 表補 MAE/MFE 與持有期,並開放 starting_cash / position_fraction 控制項。

**投資人鏡頭 — 發現**

- **🔴 critical** — 零滑價預設 + 無市場衝擊模型:平台文件強調「交易成本 ON 才誠實」,但 slippage 預設為 0,且 slippage_price 只按與單量/流動性無關的固定 bps 調整成交價。所有 crypto 回測的成交價系統性偏樂觀,直接灌水報酬並偏袒高換手策略——這是要上真錢時最致命的失真,且使用者在 UI 上完全看不到目前用的是 0 bps。
  - 〔證據〕`backend/app/config.py:156 `cost_slippage_bps: float = 0.0`;.env.example:57-58 註明「0 = no slippage」;costs.py:53 dataclass 預設 0.0,slippage_price(costs.py:84-87)僅 `price*(1±bps/1e4)`,無 size/volume/spread 依賴;costs.py:43 docstring 自承「leaves room for a spread/volume model later」=尚未實作`
- **🟠 high** — compare 把 optimize 好不容易避開的過擬合陷阱又放回來:/compare 以原始 total_return_pct 排名,UI 對最高原始報酬列直接掛 🏆,沒有任何風險調整。更關鍵的是 CompareRow DTO 根本不帶 sharpe 欄(只有 return/maxDD/trades/win),即使想改排序也得先補欄位;CompareRow 雖帶 buy_hold_return_pct 卻從未在 compare 表渲染,使用者無從判斷「冠軍」是否連 Buy&Hold 都贏不了、是否只是賭最大波動。
  - 〔證據〕`backend/app/api/backtest.py:184 `rows.sort(key=lambda r: r.total_return_pct, reverse=True)`;CompareRow(backtest.py:127-134)無 sharpe 欄;BacktestPanel.tsx:549 `{i===0 && !r.error ? "🏆 " : ""}`;compare 表欄位(BacktestPanel.tsx:537-543)僅 Strategy/Return/Max DD/Trades/Win%,無 B&H 與 Sharpe`
- **🟠 high** — optimize split 模式存在選擇偏誤:每組參數同時在 IS 與 OOS 評分,但 rows.sort 是『按 OOS 指標(rank_score=OOS Sharpe)』排序取最佳,headline 數字也直接取自 oos_result。等於用測試窗本身做篩選——rows[0] 的 oos_sharpe/oos_return 是整個網格在測試集上的最大值=向上偏誤,所謂 out-of-sample 已被消耗。程式註解宣稱「eliminates the overfitting trap」只對『不按 IS 報酬排名』為真,卻引入了新的 OOS-selection bias;全程無 deflated Sharpe / PBO / 多重檢定校正。(對照:walk_forward 在 fold 內僅用 train 選參、test 只評分,這才是誠實做法。)
  - 〔證據〕`backend/app/backtest/optimize.py:172 `rank_score=selection_score(oos_result, selection)`,:159-163 headline 取 oos_result,:188-191 `rows.sort(key=...rank_score..., reverse=True)`;repo 內無 deflated/PBO 函式(grep 確認);walk_forward 對比見 validation.py:170-181`
- **🟠 high** — 長倉、單資產、全倉,UI 從不送部位參數:引擎僅 long-only、單一 symbol 一條 candle 序列;且前端 run()/compare()/optimize() 從不傳 starting_cash/position_fraction,position_fraction 預設 1.0,每次回測都是 100% 全倉。沒有放空、沒有逐訊號部位大小、沒有波動目標、沒有多資產/組合回測。對一個以「serious multi-market live platform」為目標狀態的帳本,edge 的可信度根本無法從此處評估。
  - 〔證據〕`engine.py:1-6 docstring「long-only」,:107-142 僅 buy/sell 全進全出;backtest.py:105 `position_fraction: float = 1.0`;BacktestPanel.tsx:143-163 run() 僅送 symbol/market/strategy/params/timeframe/limit/rangeArgs;walk_forward_endpoint(backtest.py:278-279)甚至硬編 starting_cash=100_000、position_fraction=1.0`
- **🟠 high** — 跨市場年化用日曆年 365.25:periods_per_year 以 365.25 天換算,日線 台股/美股 因此以 ~365 而非 ~252 交易日年化,Sharpe、annualized_volatility、CAGR、Calmar 的數值全數失真(年化波動與 Sharpe 高估 ~1.20x = sqrt(365/252))。需精確界定影響:(a) crypto 24/7,8766 小時/年是對的,只有股市受害;(b) 因 sqrt(ppy) 是單調轉換、同一回測內所有 combo 共用同一 ppy,故參數『排名』不變——這是報告/跨市場可比性 bug,不是選參 bug。但對一個三市場平台,有兩個市場對外揭露的風險數字是錯的。
  - 〔證據〕`backend/app/backtest/metrics.py:18 `_SECONDS_PER_YEAR = 365.25*24*3600`,:23-35 periods_per_year 以日曆秒換算(「1d」→365.25);engine.py:174-175 餵入 sharpe/vol/cagr;無 252-day 股市分支(grep 確認無 252)`
- **🟡 medium** — 沒有 benchmark 權益曲線,且 Buy&Hold 與策略比較基準不對等:B&H 以 close→close 無摩擦計算(engine.py:181),策略卻付成本並以 next-bar-open 成交,UI 直接相減出「超額報酬」。方向上對策略偏保守(成本讓策略看起來更差,非更好),故非 capital-safety 風險,但這是 apples-to-oranges:交易員拿來建立信任的第一張圖(策略 vs B&H 權益疊圖)根本不存在,只剩一個純量。
  - 〔證據〕`engine.py:181 `buy_hold_return_pct=(last_price/first_price-1)*100`(close,零成本);BacktestPanel.tsx:432-435 B&H/超額僅以數字呈現;EquityChart.tsx:31 僅 addLineSeries 一條序列`
- **🟡 medium** — walk-forward 各 fold 的 OOS 從未串接成連續可交易 track record,aggregate 只是簡單平均;沒有 fold 離散度、最差 fold、正報酬 fold 佔比。平均值能把一個超棒 fold 與三個賠錢 fold 掩蓋掉。串接的 OOS 權益曲線才是真正『若當初部署會發生什麼』。
  - 〔證據〕`backend/app/backtest/validation.py:220-222 `agg_metric=sum(f.oos_metric for f in scored)/len(scored)` 僅平均;WalkForwardReport(:63-71)只有 folds 列表 + 兩個 aggregate 純量,無 stitched equity / 一致性統計`
- **🟡 medium** — 完全沒有 Monte Carlo / bootstrap / 交易順序重排:metrics.py 與 validation.py 只產出點估計,沒有報酬分布、回撤風險分位數、或運氣 vs edge 的信賴區間。對標 QuantConnect/Composer 級別的可信度,trade-resampling bootstrap CI 已是 table-stakes;量化使用者無法判斷單一回測是運氣還是真有優勢。
  - 〔證據〕`backend/app/backtest/metrics.py 全為純量函式(sharpe/sortino/calmar/...);validation.py 僅 walk_forward 一種抽樣;repo 內無 monte/bootstrap 相關碼(grep 確認)`
- **🟡 medium** — single/compare/optimize/walk-forward 結果暫態且不可重現:只活在 React state,沒有任何東西快照當時的 candle 區間、cost 參數(taker bps/slippage)、或策略版本;cost 假設也從未在 UI 顯示。沒有 run id、沒有稽核軌跡、無法重現或分享一個日後可能用來合理化真實資金的結果。對照:workflow 回測有 persist_workflow_run 落地。
  - 〔證據〕`BacktestPanel.tsx:36-51 結果全存 useState,resetOutputs(:105-113)直接丟棄;單一回測 backtest.py:291-311 不寫 DB;僅 workflow_backtest(backtest.py:72)呼叫 persist_workflow_run;全檔無任何 cost/slippage 顯示`
- **🟡 medium** — 無樣本量/regime/最少交易數防護,且對少量交易的 OOS 報以假精度:唯一的樣本品質提示是 num_trades===0 的警告;一個只成交 1–2 筆的回測照樣輸出完整 Sharpe/CAGR/Calmar 而無任何警示。walk-forward n_folds=4 把 500 根切成 ~100 根/fold,MA 類策略每 fold 可能僅數筆交易→OOS 指標極度雜訊卻以兩位小數呈現。(註:limit 路徑上限 1000 根確實偏短,但日期區間模式可繞過此上限抓整年,故問題不在硬上限,而在『任何模式都無樣本/regime 警告』。)
  - 〔證據〕`BacktestPanel.tsx:458-462 僅 num_trades===0 警告;backtest.py:101 `limit le=1000`、BacktestPanel.tsx:27 LIMITS=[200,500,1000];但 rangeMode 走 get_ohlcv_range(backtest.py:28-32)不受 limit 限制(BacktestPanel.tsx:46-48 預設一年);validation.py 無 min-trades-per-fold guard`
- **🔵 low** — win_rate 被抬到與報酬/回撤/Sharpe 並列的頭等 KPI:高勝率常與負期望值並存,等權呈現會放大一個弱統計;頭部缺 expectancy / 盈虧比這類真正反映 edge 的數字。avg_win/avg_loss 已在引擎算出卻連 moreMetrics 抽屜都未呈現,expectancy 則全無計算。
  - 〔證據〕`BacktestPanel.tsx:451-456 win_rate 為四張 MetricCard 之一且 health="neutral";moreMetrics(:472-481)列 cagr/sortino/calmar/profit_factor/vol/exposure/turnover/maxConsecLosses/numTrades,不含 avg_win/avg_loss;engine.py:52-53 avg_win/avg_loss 已算;repo 內無 expectancy`

**設計鏡頭 — 發現**

- **🟠 high** — 所謂「五分頁面板」其實是互斥的單一結果視圖:每個動作起手都先 resetOutputs() 清空 result/comparison/optimization/walkforward,TabBtn 又只對『目前存在的那個結果』條件式渲染。你永遠無法把一個回測的權益曲線與它的 optimize 掃描並列,也沒有任何 run history / pin / 跨 run overlay。IA 承諾了它根本無法兌現的比較能力,且零稽核軌跡。
  - 〔證據〕`BacktestPanel.tsx:105-113 resetOutputs() 清空四個結果 state;:117-202 每個動作(run/compare/optimize/runWalkForward)第二行皆呼叫 resetOutputs();:397-405 分頁按『該結果是否存在』條件渲染`
- **🟡 medium** — 權益圖既無 underwater/drawdown 子圖,也無 benchmark 疊圖:最大回撤只是一個數字,EquityChart 只畫策略一條線。交易員看一張曲線時最先讀的兩個視覺(回撤水下圖、策略 vs B&H 疊圖)都缺席。這是視覺完整度缺口而非資料正確性問題,故非 high,但對一個自我定位為 refined-terminal 的交易平台仍屬不及格。
  - 〔證據〕`BacktestPanel.tsx:442 max_drawdown 純數字;:493 `<EquityChart points={result.equity_curve} />`;EquityChart.tsx:31-42 僅單一 addLineSeries,無第二序列、無 drawdown panel`
- **🟡 medium** — optimize 只呈現 top-10 平面表格,沒有 parameter-stability surface / heatmap。使用者無從分辨『穩健的高原』與『脆弱的尖峰』——這正是信任一組最佳化參數最關鍵的那張圖,而 rank_score 已具備可拿來著色熱圖的數值卻未用。
  - 〔證據〕`BacktestPanel.tsx:587 `optimization.slice(0,10).map(...)` 僅前十列表格;無任何 2D 參數網格視覺化;OptimizeRow.rank_score(optimize.py:53)可用於熱圖`
- **🟡 medium** — 長運算無進度、不可取消:optimize split 模式每組跑 2 次回測(IS+OOS)、max_combinations 上限 500,最壞情況同步阻塞近千次回測,UI 卻只給一顆 disabled 按鈕顯示 loading 文字。沒有確定性進度、沒有串流、沒有取消;阻塞數秒在使用者眼中就是當機。
  - 〔證據〕`BacktestPanel.tsx:368-373 optimize 按鈕僅 `disabled={loading||isSaved}`;optimize.py:136-185 同步迴圈、每 combo 兩次 run_backtest;backtest.py:198 `max_combinations: Field(default=200, ge=1, le=500)``
- **🟡 medium** — 控制列是一整排無層級的 flex-wrap:market/symbol/timeframe/區間切換/strategy/逐參數 number input/Run/Advanced 全擠在同一個會換行的 row,較窄寬度 reflow 不可預測;而且根本沒有資金(starting_cash)與部位比例(position_fraction)的控制項,儘管引擎與 API 都支援。
  - 〔證據〕`BacktestPanel.tsx:236 單一 `flex flex-wrap items-end gap-2` 容器一路包到 :352;:327-337 逐 param 動態 input 直接塞進同列;全檔無 capital / position fraction 欄位(backtest.py:104-105 已支援)`
- **🔵 low** — accent 紀律破口:optimize 的「use」動作連結用 cyan(text-accent),而 🏆/▴▾ 字符在 refined-terminal 規範下偏隨意。DESIGN.md 明定 cyan 專屬 AI/automation;套用最佳參數雖屬自動化但非 AI,emoji 獎盃也不是終端機語彙。
  - 〔證據〕`BacktestPanel.tsx:622 `className="text-accent hover:underline"` 用於 use 連結;:549/:590 🏆、:350/:469 ▴▾;DESIGN.md:73-75 accent 保留給 AI/automation`
- **🔵 low** — Trades 表缺少量化會掃的欄位:沒有持有期/bars-held、沒有 MAE/MFE、沒有累積 PnL 欄。逐筆歸因很淺,無法看出策略是『讓利潤奔跑』還是『砍太早抱太久』。
  - 〔證據〕`BacktestPanel.tsx:502-513 表頭僅 Entry/Exit/Entry px/Exit px/Qty/Return%/Net PnL/Cost;Trade model engine.py:19-29 無 mae/mfe/bars_held`

**重設計提案**

## 回測室重設計:從「暫態面板」升級為「可重現、可比較、會自證誠實」的研究台

三個核心病灶:(1) 結果暫態且互斥(resetOutputs 每跑必清),(2) 視覺只給點估計、不給分布與 benchmark,(3) 引擎層統計失真(零滑價、股市年化 365.25、compare 原始報酬排名)從未被 UI 揭露。重設計圍繞三件事:**持久化 Run、Honesty Bar、分布化視覺**。所有顏色仍走 token:策略權益 `--up`/`--down`(台股 `data-market="tw"` 自動翻轉)、benchmark 走 `--text-faint`、警示走 `--warning`,cyan 僅保留給 AI 觸發的「用 AI 解讀此回測」。

### 1) 持久化 Run Registry,取代 resetOutputs 的互斥分頁
每次執行落地成一筆 BacktestRun,快照 symbol/market/timeframe/區間/**cost params(taker bps + slippage bps)**/策略版本,寫進 DB(沿用 backtest.py:72 已有的 persist_workflow_run 模式)。左側細欄列出近期 run,可 pin、可多選 overlay 比較。分頁(overview/trades/compare/optimize/walk-forward)變成「同一筆 run 內的視圖」,彼此共存而非互相清空——直接解掉 BacktestPanel.tsx:105-113 的互斥根因。

```
┌ 回測室 ─────────────────────────────────────────────────────────────┐
│ Runs        │  BTC/USDT · ma_cross(10/20) · 1h · 2025-01→2025-06     │
│ ───────────│  ┌ Honesty Bar ─────────────────────────────────────┐ │
│ ● #128 pin │  │ ⚠ slippage=0bps(未設,成交價偏樂觀)· cost 7.5bps │ │
│   #127     │  │ ⚠ 樣本 412 bars · 18 trades · grid 試 48 組→Sharpe │ │
│   #126     │  │   未做 deflate;OOS 由測試窗挑選,視為樂觀上界      │ │
│ ───────────│  └───────────────────────────────────────────────────┘ │
│ [+ 新回測] │  Return +18.3%  vs B&H +11.2%(已扣同等進出成本)       │
│            │  MaxDD -9.4%   Sharpe 1.42(252日年化)  Expectancy +0.6R│
│            │  ┌─ Equity:策略(實線 --up/--down)vs B&H(--text-faint)┐│
│            │  │            ╱╲      ╱──strategy                     │ │
│            │  │      ╱╲  ╱   ╲╱╲╱   ····· buy&hold                 │ │
│            │  ├─ Underwater drawdown(--down 填色)────────────────┤ │
│            │  │  ▁▁▂▅▇▅▂▁▁▁▃▆▃▁▁                                  │ │
│            │  └───────────────────────────────────────────────────┘ │
│            │  [overview][trades][compare][optimize][walk-fwd] 共存    │
└────────────┴──────────────────────────────────────────────────────────┘
```

### 2) Honesty Bar — 把引擎的隱性假設變成顯性警示
固定置於每筆 run 頂部,用 `--warning` 揭露三類風險,逐一對應目前的程式缺陷:
- **成本假設**:讀 cost model,若 `slippage_bps==0` 顯示「⚠ slippage 未設,成交價偏樂觀」(對應 config.py:156)。提供「成本敏感度」滑桿:以 1x/2x/3x 滑價重跑,看 edge 是否撐得住——這把 critical 的零滑價問題從隱形變成可操作。
- **多重檢定**:optimize/walk-forward 顯示「試了 N 組參數」,並明示 optimize split 的 OOS 是『被挑選過的上界』而非乾淨樣本(對應 optimize.py:188 的 OOS-selection bias);headline Sharpe 旁標 deflated 提示。
- **樣本/regime/交易數**:bars 或 trades 低於門檻時警告統計檢定力不足(對應目前只有 num_trades===0 才警告,BacktestPanel.tsx:458)。

### 3) 視覺分布化 + 引擎誠實性修正
- **Equity 疊 benchmark + underwater**:EquityChart 增第二序列(B&H,`--text-faint`),下方掛一條 drawdown 水下子圖。可直接複用 PriceChart.tsx:188-264 既有的「副圖 + 時間軸雙向同步」模式。B&H 同樣扣一次進出成本,讓「超額」對等(修 engine.py:181)。
- **optimize 改 heatmap**:雙參數時用 rank_score 著色熱圖、標出最佳點與鄰域(高原 vs 尖峰),IS→OOS gap 用色階提示過擬合(資料已在 OptimizeRow.is_oos_gap_pct)。
- **walk-forward 串接 OOS**:把各 fold 的 OOS 段接成一條連續『可交易 track record』,旁附一致性條(正報酬 fold 佔比 / 最差 fold / 離散度),取代 validation.py:220-222 的單純平均。
- **引擎修正(blueprint 必列)**:periods_per_year 對股市走 252 日(metrics.py:23);compare 在 CompareRow 補 sharpe + buy_hold 欄並改以 Sharpe 排名(backtest.py:127-134/184),🏆 改頒給風險調整冠軍;UI 開放 starting_cash / position_fraction 並為逐訊號部位大小留欄位;Trade model 補 MAE/MFE/bars_held 餵進 trades 表。

### 4) 長運算回饋 + 控制列分組
optimize/walk-forward 改為可回報進度(已完成 N/總組數)+ 可取消,取代目前單一 disabled 按鈕的假當機(BacktestPanel.tsx:368-373)。控制列拆成「資料(market/symbol/tf/區間)」「策略+參數」「資金+部位」「執行」四個分組,而非一整排 flex-wrap(BacktestPanel.tsx:236-352)。

<br>

### D3. 工作流 Workflow Builder (node canvas + engine)

**現況:** 一個工程乾淨的 per-tick 決策函式(topo 排序、fail-loud、idempotent target-position、AI 與指標策略同型 Signal 互換)被包在一個尚未長出 runtime、sizing 與 live-safety 層的畫布裡——而且 backtest 與 live 對同一張圖的執行語意是兩套不同系統(sizing、再平衡頻率、timeframe 皆分歧)。

**評分:** 投資人 `2/5` · 設計 `2/5`　|　**判決: `Rework`**

**最高槓桿動作:**
- 彌平 backtest↔live 語意鴻溝並讓節點設定 load-bearing:回測必須吃 order 的 sizing/quantity 與 data_source 的 timeframe/limit(今天回測等權 all-in、每根 bar 漂移再平衡、固定 1h/500、全部忽略節點參數),再平衡規則要與 live 的『達標即 no-op』一致,並把 walk-forward / OOS 接到 workflow 回測。否則沒有認真的交易者會信任一張圖的回測。
- 建造 DESIGN.md 已規格但缺席的 live-safety 層:滿版粉色 LIVE banner + 脈動 + LIVE 投組 chip,送出真實訂單前強制 dry-run 預覽與確認(今天送真實單零確認,刪 workflow 反而要確認),修正 paper『執行回測』錯標籤(實為下紙上單),並讓 builder 顯示 live/paper run log(今天只看得到 backtest)。
- 讓畫布本身溝通執行:型別化 port(拒絕 candles→order 與 condition→order footgun)、執行中/錯誤的 edge 與失敗節點高亮就地定位,並用設計過的 .num/tabular run/trace 視圖取代原始 JSON dump。

**投資人鏡頭 — 發現**

- **🔴 critical** — 同一張圖在 workflow backtest 與 paper/live 是兩套下單系統。Backtest 完全忽略 order 節點的 quantity,改用 PortfolioSim 等權(equity/N)all-in;live/paper 則按固定單位數交易 delta-to-target。回測賺錢不代表實盤會賺——這直接侵蝕平台最大資產(扎實的 backtester)的可信度,沒有認真的交易者會信任一張圖的回測。
  - 〔證據〕`workflow_backtest.py L171 `pending_targets = sim.target_quantities(longs, closes)` → portfolio.py L49-59 `per = equity / n; targets[sym] = per / prices[sym]`(全權益等權);nodes.py `_run_order` backtest 分支 L179-182 只 `ctx.backtest.record(...)` 不讀 quantity;live 分支 L188 `target_qty = float(p.get('quantity',1))`;nodeCatalog.ts L77 order.params 僅 quantity,該參數在回測中為死碼。`
- **🟠 high** — 除 sizing 外,回測還每根 bar 都把 desired-long 重算成等權目標並在次根 open 再平衡——只要價格漂移,等權目標股數每根都改變,持續產生 drift-rebalancing 的小額換手與成本拖累;live 的 _run_order 則只把部位推到固定 quantity,達標後每個 tick 都是 no-op、不因漂移交易。回測背了一筆 live 不存在的換手成本,turnover/Sharpe 雙雙失真。
  - 〔證據〕`workflow_backtest.py L169-171 每根 bar(非觸發式)`pending_targets = sim.target_quantities(...)`;portfolio.py rebalance L61-74 只要 |delta|>eps 就交易;對照 nodes.py L191-194 live 端 `delta = target_qty - held; if abs(delta)<=_QTY_EPS: return None`。`
- **🟠 high** — data_source 的 timeframe/limit 在 workflow 回測中為死碼,且與 live 路徑分歧。回測一律用 request 預設(1h/500)抓 OHLCV,連 Sharpe 年化都按 1h 算;而 live 的 _run_data_source 會讀節點 timeframe。前端又從不帶 timeframe,故節點設 4h/1d 仍跑 1h 回測——節點設定與實際執行靜默分歧,違反 fail-loud。因整份報告在同一個(錯的)timeframe 下自洽、blast radius 有界,列 high 而非 critical。
  - 〔證據〕`api/backtest.py L64 `histories = {s: broker.get_ohlcv(s, req.timeframe, req.limit)}`(WorkflowBacktestRequest 預設 timeframe='1h', limit=500, L39-40);_run_data_source backtest 分支只回 `ctx.backtest.window_for(symbol)`(nodes.py L87-88)不看 timeframe;WorkflowBuilder.tsx L166 `runWorkflowBacktest({ graph, limit: 500 })` 未帶 timeframe。`
- **🟠 high** — 平台最強的反過擬合資產(walk_forward / split-OOS optimize)未接到 workflow 抽象。圖的回測只有單一 in-sample run,WorkflowBacktestRequest 連 start/end 都沒有,無法選區間、無法做 OOS/walk-forward。最容易過擬合的那種多節點 AI 圖,恰恰最缺穩健性檢驗。
  - 〔證據〕`WorkflowBacktestRequest 僅 graph/workflow_id/market/timeframe/limit/starting_cash(api/backtest.py L35-42),無 start/end;/optimize、/walk-forward 端點吃 OptimizeRequest/WalkForwardRequest(需 symbol+strategy+param_grid),無 graph 路徑。`
- **🟠 high** — 圖的模型沒有部位大小維度,且丟棄 confidence。order 節點固定單位數、long/flat-only、完全忽略 Signal.confidence;無 %equity、ATR、risk-per-trade、target-weight、做空、槓桿。目標態(sizing/shorting/leverage)在節點層完全未被規格化,連 combine 算出的 confidence 到 order 也被丟掉。
  - 〔證據〕`nodes.py `_run_order` L188 `target_qty = float(p.get('quantity',1)) if buy else 0.0`,註解 L173『long/flat only — never short』;`_only_signal` 取的 Signal 只讀 .action,confidence 從不參與下單;nodeCatalog.ts order.params 僅 quantity。`
- **🟠 high** — live『執行』只是一次手動 single-tick,不是運行中的系統。按一次 run = topo 跑一遍;沒有事件迴圈、on-bar-close / on-fill 觸發。持續運行得另接 Schedule 子系統,而 builder UI 內沒有任何排程/部署入口——刪 workflow 還會因 Schedule 參照被擋下(回 409),正好證明兩者是分離子系統。對認真的 live 平台,這只是個手動開火的試算台。
  - 〔證據〕`WorkflowBuilder.run() → api.runWorkflow 一次 → run_ad_hoc → run_workflow 跑一遍 topo;workflows.py delete L100-105 因 Schedule 參照回 409;Toolbar/builder 無排程連結。`
- **🟠 high** — ai_signal 在 live 下單路徑做同步、非決定性 LLM 呼叫,無快取/降級。每個 tick 都即時打 Anthropic(structured_completion),結果不可重現、可能逾時;回測有 ai_bar_cap=200 上限,live 路徑無任何上限或延遲/成本/rate-limit 控制,且只留 rationale 文字、無完整 prompt 稽核。把這種外部呼叫放在會送真實單的關鍵路徑上,既是延遲也是稽核風險。
  - 〔證據〕`nodes.py `_run_ai_signal` L112-115 每次呼叫 generate_ai_signal;signal_agent.py generate_ai_signal → structured_completion(...) 無快取/fallback;workflow_backtest.py L64-69 ai_bar_cap=200,live 無對應上限。`
- **🟡 medium** — port 無型別:任一輸出可接任一輸入,toolbar 對會在執行期失敗的圖仍顯示『✓ 有效』(如 data_source→order 結構合法,執行期才報錯)。更糟的是 condition 節點在門檻成立時直接吐出 confidence=1.0 的 buy(本意是 gate),於是 Data→Condition→Order 可在純價格門檻上下真實單而驗證全綠——對下真單的工具是 footgun。驗證過度承諾。
  - 〔證據〕`validateGraph.ts 僅查 dupes/cycle/missing-input;TradeNode.tsx handle 泛型;nodes.py `_only_signal` L70 執行期才 raise『requires a Signal』;`_run_condition` L315-316 門檻成立回 `Signal(buy, confidence=1.0)`。`
- **🟡 medium** — live/paper run 被持久化卻被 builder 歷史面板濾掉。送出真實/紙上訂單後 _persist_live_run 以 kind=paper/live 寫 WorkflowRun,但 builder 的歷史面板寫死 kind='backtest',把實盤紀錄全濾掉——送單後在原地看不到任何稽核紀錄。資料仍在 DB(故列 medium),但對 live 平台仍是信任/稽核缺口。
  - 〔證據〕`WorkflowBuilder.tsx L334 `<WorkflowRunHistory kind="backtest">`;workflows.py `_persist_live_run` L143 kind=trading_mode(paper/live);list_runs(workflows.py L48-52)`where kind==kind` 濾除。`

**設計鏡頭 — 發現**

- **🔴 critical** — 全 App 最重要的 paper↔live 信任邊界嚴重低估,且風險優先序顛倒。送出真實訂單前『零確認』,但刪 workflow、重置紙上帳戶卻都要 confirm——把確認花在低風險動作、把高風險(送真實單)裸放。DESIGN.md L40-44 明定的 live 安全狀態(滿版粉色 LIVE banner + 脈動指示 + 投組 chip 讀 LIVE)幾乎沒實作,只剩一顆 bg-live/15 小 chip 與變色 run 按鈕,無 banner、無 pulse。
  - 〔證據〕`WorkflowBuilder.run() L152-161 直接 api.runWorkflow 無 window.confirm;對照 deleteWorkflow L129 與 PortfolioPanel.tsx L37 `confirm('重置紙上交易帳戶…')` 都有確認;Toolbar.tsx L42-44 僅 `交易室 · {MODE}` chip、L90 run 按鈕變 live 色,無 DESIGN.md 要求的 banner/pulse/LIVE 投組 chip。`
- **🟠 high** — 主要 CTA 標籤錯誤:paper 模式按鈕字面寫『▶ 執行回測』,但 onRun 走的是下單路徑(經 execute_order 真的建立 paper 訂單),不是回測;真正的回測是另一顆次要『📊 Backtest』。在最關鍵的交易按鈕上掛了會讓使用者『以為只是模擬』的標籤,等於誘導誤觸真實(紙上)下單。
  - 〔證據〕`Toolbar.tsx L92 `live ? '▶ 送出真實訂單' : '▶ 執行回測'`;onRun→WorkflowBuilder.run()→api.runWorkflow→run_ad_hoc→_run_order(execute_order);回測為 onBacktest→handleBacktest→/api/backtest/workflow。`
- **🟠 high** — 畫布完全不回饋執行/錯誤狀態,違反 DESIGN.md『Edge & run states』。L228-232 要求 running edge 動態虛線(accent)、error edge 紅色——皆未實作;驗證只把 errors[0] 顯示成 toolbar 一行字,從不就地標出出錯的節點/邊;run 失敗 engine 只回純文字『node X failed』,使用者得自行把 node id 對回畫布。一張會下真單的圖,連『現在跑到哪、哪裡爆了』都看不到。
  - 〔證據〕`Canvas.tsx 用預設 edge;useWorkflowState.ts buildGraph(L145-153)/setGraph edges(L164)不帶 style/animated;Toolbar.tsx L54-56 只顯示 valid.errors[0];engine.py L96 回 `node '{id}' ({type}) failed` 純文字。`
- **🟠 high** — 多市場在 builder UI 完全不可達。號稱 crypto/台股/美股,但 data_source 沒有 market 欄位、order 只有 quantity,後端一律預設 market=crypto、_persist_live_run 寫死 'crypto'、前端回測也不帶 market。畫布只能組出 crypto 圖,與 DESIGN.md 的 data-market 反轉(台股紅漲)更接不上——沒有 market 就無從設 data-market。
  - 〔證據〕`nodeCatalog.ts data_source.params 無 market、order.params 僅 quantity;nodes.py L84 `MarketKind(p.get('market','crypto'))`;workflows.py L146 `market='crypto'`;WorkflowBuilder.tsx L166 回測未帶 market。`
- **🟡 medium** — run 結果與 signal trace 以原始 JSON dump 呈現,是開發者 console 而非『精煉終端機』。builder 內 run result 每列直接 `{type} [{id}]: JSON.stringify(summary)`;SignalTraceDrawer 每步 summary 也是 `JSON.stringify(step.summary, null, 2)` 巢狀 dump(標頭的 symbol/action/conf 有格式化,問題在每步明細)。無 .num tabular 對齊、price/confidence 無格式化、直吐 enum 字串,落空 DESIGN.md『tabular-nums everywhere』。
  - 〔證據〕`WorkflowBuilder.tsx L307 `{s.type} [{s.node_id}]: {JSON.stringify(s.summary)}`;SignalTraceDrawer.tsx L150 `{JSON.stringify(step.summary, null, 2)}`(對照 L43-45 標頭已格式化)。`
- **🟡 medium** — Inspector 過於單薄,參數可信度不足。純 number/text/select 三型,無驗證/單位/上下限/說明;已存策略節點只顯示唯讀『已存策略 #id』,後端支援的 param_overrides 不可編輯;stop_loss_pct/take_profit_pct 只是裸數字,無 % 語意或護欄(可填 -5 或 999)。對一個會下真實單的工具,參數面板不該毫無防呆。
  - 〔證據〕`Inspector.tsx FieldInput 僅三型(L8-30);d.params.strategy_id 分支 L80-83 唯讀標籤;nodes.py `_run_strategy` L105 讀 param_overrides 但 UI 未暴露;nodeCatalog risk_exit 參數無 min/max/unit。`
- **🔵 low** — i18n / token / a11y 破口。狀態與面板文字夾雜英文(`Saved #id.`、`Running…`、`Backtesting…`、`Saved workflows`、`Open`/`Delete`、預設名 `My workflow`),與全中文契約不符;SignalTraceDrawer 整檔 inline style 並硬編 hex fallback(`#111317`、`#16181D`…),違反 DESIGN.md『CSS 變數是契約、勿硬編 hex』;a11y 薄弱:trace drawer 標 role='dialog' 卻無 focus trap / Esc / aria-modal,狀態僅以顏色+字符(✓/✗)表達。
  - 〔證據〕`WorkflowBuilder.tsx L24/L86 與 Toolbar.tsx L92/L99 英文字串;SignalTraceDrawer.tsx 整檔 inline style 含 `#111317` 等 fallback、無 keydown/Esc;Toolbar.tsx L55 ✓/✗。`

**重設計提案**

核心立場:engine 本體(topo 排序、fail-loud、idempotent target-position、AI 與指標策略同型 Signal 互換)是可保留資產;要重做的是它周圍三層——(A) live-safety 與 run 語意層、(B) 畫布的執行回饋與型別化 port、(C) 讓節點設定真正 load-bearing 並把 OOS 工具接上 workflow。

A. Live-safety 層(對齊 DESIGN.md L40-44 自己的規格,並補送單前確認/dry-run)。把 live 從『一顆變色按鈕』升級為一條無法忽視的安全帶:滿版粉色 --live banner + 脈動點(DESIGN.md 唯一刻意動畫)+ 投組 chip 讀 LIVE + 送單前強制 dry-run 預覽(列出本次會送出的每筆訂單:symbol/side/qty/預估金額,並跑過既有 RiskGuard/PortfolioGuard),確認後才送。paper 模式則明確拆成『試算(不下單)』與『執行(下紙上單)』,移除『執行回測』這個錯標籤——回測永遠走獨立的 📊 按鈕。

```
┌──────────────────────────────────────────────────────────────────────┐
│ ● LIVE · 真實資金 — 此圖會送出真實訂單           交易室 · LIVE  [切回 paper] │  ← --live 滿版 banner,● 脈動
├──────────────────────────────────────────────────────────────────────┤
│ Workflow Builder.   ↶ ↷   − fit ＋    ✓ 有效 · 6 nodes · 5 edges        │
│ [my-btc-momentum ▾] #12   開啟 儲存 另存 刪除      [⚑ 預覽訂單] [▶ 送出真實訂單]│  ← 送單前必經 預覽
└──────────────────────────────────────────────────────────────────────┘
      點『送出真實訂單』→ 彈出 dry-run 確認:
      ┌─ 將送出 2 筆訂單(LIVE) ───────────────┐
      │ BTC/USDT   BUY   0.0100   ≈ 642.10 USDT │  ← .num tabular,--up/--down 依 data-market
      │ ETH/USDT   SELL  0.0500   ≈ 158.20 USDT │
      │ 通過 RiskGuard ✓  剩餘日損額度 $1,840    │
      │           [取消]   [確認送出 — LIVE] ←--live│
      └─────────────────────────────────────────┘
```

B. 畫布即時溝通執行狀態 + 型別化 port。執行時沿 active edge 跑 --accent 動態虛線(DESIGN.md L230);失敗節點打紅框、把 engine 的 `node 'X' failed` 直接定位到該節點(而非 toolbar 一行字);驗證錯誤就地標在出錯的節點/邊,不再只顯示 errors[0]。port 加型別(candles / Signal / order)——把 data_source→order 這種圖在連線當下就拒絕,並擋掉 condition→order 這種『純價格門檻無中生有 buy』的 footgun,讓『✓ 有效』名副其實。節點 anatomy 維持現狀(158px、3px 類別色條、color chip、mono summary——已符合 DESIGN.md Node anatomy,予以保留)。

C. 讓節點設定 load-bearing,並把 sizing 與 OOS 接上。order 節點從『quantity 一個裸數字』升級為 sizing 模式(fixed_qty / pct_equity / risk_per_trade / target_weight)+ side(long/short)+ market 下拉;最關鍵:回測必須吃 order 的 sizing 與 data_source 的 timeframe/limit(今天兩者皆被丟棄),且回測的再平衡規則要與 live 一致(live 是『達標即 no-op』,backtest 不該每根 bar 漂移再平衡),否則 backtest≠live 永遠成立。workflow 回測請求補上 start/end 與 walk-forward/OOS 開關,把現有 validation.py / optimize.py 的誠實工具接到圖上。Inspector 加單位/護欄(stop_loss_pct 顯示 %、限正數)/說明,並暴露已存策略的 param_overrides。

```
Inspector — Order(下單)
  market     [crypto ▾]        side  [long ▾]
  symbol     BTC/USDT (繼承自 data)
  sizing     [pct_equity ▾]    value 10 %      ← 不再是裸 quantity
  ⚠ 回測將以此 sizing + 與 live 相同的再平衡規則計算
```

最後把 builder 的 run 歷史改成同時顯示 backtest 與 live/paper(今天 kind='backtest' 濾掉了實盤紀錄),讓『送出真實訂單』後在原地就看得到稽核紀錄;run result 與 trace 用設計過的 .num/tabular 視圖取代原始 JSON dump,SignalTraceDrawer 改用 token class、補上 Esc/focus-trap/aria-modal。

<br>

### D4. 市場 Market（行情資料 + 指標 + AI 訊號）

**現況:** 圖表引擎（lightweight-charts，多副圖同步、theme-reactive、暖機 null fail-loud、market-aware --up/--down）工藝扎實，但其下的資料層只有 OHLCV、靠雙路 3s REST 輪詢偽即時、每次請求重建 CcxtBroker（每輪可能重跑 load_markets）、24h 統計在特定週期被錯標、AI 訊號是一發脈絡稀薄且未校準的 LLM 意見——以「認真做 live」標準看，資料深度與訊號可信度遠未達桌面門檻。

**評分:** 投資人 `2/5` · 設計 `3/5`　|　**判決: `Rework`**

**最高槓桿動作:**
- 建立可信的行情資料層：以 WebSocket 串流取代雙路 3s REST 輪詢、把 CcxtBroker 改為快取單例並預載 markets（消除每輪隱式 load_markets 與 rate-limit 風險）、新增 order book/bid-ask、伺服器端 candle 快取與 OHLC 驗證（含 CSV 匯入），並用後端正確時間窗的 rolling-24h 統計取代前端 barsPer24h 的錯標，補上資料新鮮度/連線指示。
- 讓 AI 訊號可信且可執行：餵入成交量/波動率/多週期脈絡、把 200 根固定窗口語意講清楚、confidence 改離散信心等級或做校準、在卡片內嵌『此訊號歷史回測表現』把 AI 接上回測引擎，並提供一鍵『據此試算下單（套 RiskGuard）』銜接。
- 修 DESIGN.md 合規與 explorer 外殼：把 indicator/log/量 toggle 的 accent-dim 改回中性 active（青色只留給 AI 並為 AI 卡片補 badge），原生 <select> 換終端機風控制、切 market 自動帶入預設 symbol（修狀態 bug），把市場做成 watchlist+搜尋+指標參數的 room，並補齊 501/502 分流、skeleton、≥44px 觸控與 canvas a11y fallback。

**投資人鏡頭 — 發現**

- **🟠 high** — 行情資料只有 OHLCV 與 last price，完全沒有 order book / bid-ask / spread / 成交明細(tape) / 基本面。Ticker schema 僅 symbol/price/timestamp，markets.py 只暴露 /ticker、/ohlcv、/import、/imported。認真的 live 交易者無法評估流動性、價差、真實可成交價或市場深度——這是 QuantConnect / TradingView / Bloomberg 的基本盤，目前整層缺席。
  - 〔證據〕`backend/app/schemas.py:52-55 Ticker 僅 symbol/price/timestamp；backend/app/api/markets.py 只有 get_ticker/get_ohlcv/import/imported，無任何 depth/orderbook endpoint`
- **🟠 high** — 『24h 漲跌/高/低』實為前端用『目前 timeframe 的最後 N 根 K』推導，N 由 barsPer24h(timeframe) 估算、未知週期退回 24。預設 BTC/1h/200 路徑恰好正確（barsPer24h('1h')=24，切最後 24 根=精確 24h）；但 timeframe='1w' 不在 map → 退回 24 根=約 24 週卻仍標『24h』，1m/5m 在 bars 不足時窗口被截短（1m 需 1440 根、最大只給 1000）也仍標 24h。標籤與實際窗口在常見切換下不一致，是顯示層的資料誠實性瑕疵（market-stats.ts 註解坦白『不偽造後端欄位』，但 UI 標籤『24h』撒了謊）。
  - 〔證據〕`frontend/lib/market-stats.ts deriveStats + barsPer24h（map 無 1w，?? 24）；MarketPanel.tsx:79 deriveStats(candles.data, barsPer24h(timeframe))、L217-221 以 stats 渲染 L.market.change24h/high24h/low24h`
- **🟠 high** — 即時資料是『雙路 3s REST 輪詢、僅 crypto』：PriceChart 每 3s 抓 ohlcv(limit=2)、MarketPanel 同時每 3s 抓 fetch_ticker——同一畫面兩個獨立輪詢、兩個價格來源（標頭用 ticker.last、圖上 pill 用 ohlcv close，瞬間可不一致）。非 WebSocket，延遲/抖動高、漏 tick。更嚴重：registry 每次都 new 一個 CcxtBroker（markets 快取為空），ccxt 在首次 fetch_* 會隱式 load_markets()，等於每一輪都重拉一次 Binance 市場 metadata，rate-limit 與延遲風險被放大。對 live 而言這不是可信的行情管道。
  - 〔證據〕`frontend/components/PriceChart.tsx:270-276 liveQuery refetchInterval≈3000 + api.ohlcv(...,2)；MarketPanel.tsx:70-77 ticker refetchInterval 3000；backend/app/brokers/registry.py:30 與 :43 皆 return CcxtBroker()（非快取）；crypto_ccxt.py __init__ 不預載 markets`
- **🟠 high** — AI 訊號可信度站不住腳：餵給模型的 summary 只有 latest close、整段 change%、RSI(14) 末值、最後 15 根 close（_market_summary）——無成交量、無多週期、無波動率、無趨勢結構、無部位/regime 脈絡。confidence 是 LLM 自報、未校準的浮點數，卻以『confidence 72%』呈現，暗示一個它無法支撐的機率；且無任何回測背書、無歷史命中率。認真的交易者不能據此一發意見下單。
  - 〔證據〕`backend/app/ai/signal_agent.py:32-44 _market_summary 僅組 close/change/RSI/recent15，無 volume；AISignalResponse.confidence 直接 clamp LLM 值；MarketPanel.tsx:250-252 渲染為 (confidence 72% · ai:…)`
- **🟠 high** — 台股/美股行情是使用者匯入的 CSV，存於『process 內 module-level dict、重啟即清空』，且 parse_csv 只檢欄位齊全與逐列可解析，不驗 OHLC 邏輯（high≥low、open/close 落在 high/low 間）、不擋負量、不偵測重複時間戳或缺口，更無分割/股息還原（corporate action / survivorship）。回測與 paper 都建立在未驗證、重啟即失的資料上——不是可被認真信任的資料層。
  - 〔證據〕`backend/app/brokers/market_data.py:15 _store 為 module-level dict（註解 cleared on restart）；parse_csv:34-63 僅檢 required 欄位與 float 轉換，無 OHLC 一致性/還原`
- **🟡 medium** — AI 訊號的請求/使用語意混濁：MarketPanel askAi 固定以 limit=200 取回，但模型實際只看到 15 根原始 close 加兩個聚合（RSI 末值、200 根窗口的 change%）。『change over window』分母是 200 根中最舊那根 close，而 200 根對應的真實時長隨 timeframe 浮動（1h≈8.3 天、1w≈200 週）卻未在 prompt 標明，使『漲跌幅』語意隨週期漂移、無固定參考基準。
  - 〔證據〕`MarketPanel.tsx:117 api.aiSignal(symbol, market, timeframe, 200)；backend/app/api/ai.py:26 get_ohlcv(...,req.limit)；signal_agent.py:36-38 closes.iloc[0] 作分母、closes.iloc[-15:] 作 recent`
- **🟡 medium** — 沒有任何資料新鮮度/連線/延遲指示。crypto 輪詢無『最後更新時間 / 連線狀態』，live pill 只印 lastPrice 無 timestamp；台股/美股只有一個靜態『離線資料(CSV)』chip，不顯示匯入資料的 as-of 日期區間。交易者無從判斷自己看的是不是過期資料——對 live 是危險盲區。
  - 〔證據〕`MarketPanel.tsx:174-178 offlineCsv chip 為靜態字串 L.market.offlineCsv；PriceChart.tsx:327-335 live 區塊僅 lastPrice.toFixed(2)，無 timestamp/連線狀態`
- **🟡 medium** — AI 訊號是死路一條的『意見』：卡片輸出 buy/sell/hold 後，沒有任何『據此下單 / 試算部位 / 經 RiskGuard 的風險預覽』銜接，也沒有與回測引擎或策略庫的連結。平台最強的資產（bar-by-bar 回測、RiskGuard/PortfolioGuard）就在隔壁，AI 訊號卻給了方向而無可執行的下一步。
  - 〔證據〕`MarketPanel.tsx:245-255 aiSignal 卡片僅渲染 action/confidence/source/reason，無任何 action button 或導向 order/backtest`

**設計鏡頭 — 發現**

- **🟠 high** — 直接違反 DESIGN.md『電光青 --accent 僅保留給 AI/自動化』的不可協商規則：MA/EMA/BOLL/RSI/MACD 五個指標 toggle、對數、量 共七個檢視開關的 active 狀態，全部點亮 border-accent/40 + bg-accent-dim（青色）。RSI/MACD/量不是 AI，卻搶用 AI 專屬色，稀釋了『青色=AI 正在作用』的語意。這是本檔最明確的設計違規。
  - 〔證據〕`frontend/components/MarketPanel.tsx:198（五個指標 toggle）、:203（logScale）、:207（volume）三處 on 狀態皆 border-accent/40 bg-accent-dim`
- **🟡 medium** — 反向違規：真正屬於 automation 輸出的『AI 訊號卡片』反而沒有 accent 身分——它是樸素 bg-surface-2 文字框，無『AI 生成』badge、confidence 只是裸 number『72%』、51% 的 buy 與 95% 的 buy 視覺權重幾乎相同。DESIGN.md 規定 AI 區塊承載 accent 與徽章；指標 toggle 偷了青色、AI 輸出卻 under-design，恰好把規則用反。
  - 〔證據〕`frontend/components/MarketPanel.tsx:246 卡片 border-border bg-surface-2、:250-252 confidence 純文字、無 badge/accent；DESIGN.md『AI 生成 badges、accent leads here』`
- **🟡 medium** — 切換 market 不重置 symbol：setMarketState 只改 market，symbol 維持原值，於是『BTC/USDT』在切到台股後被送進 CsvDataBroker → 501/無資料錯誤；每個 market 的預設標的也不會自動帶入。這是 explorer 級工具不該有的狀態 bug，第一手體驗就會撞牆。
  - 〔證據〕`frontend/components/MarketPanel.tsx:142-149 onChange 僅 setMarketState；symbol state 不隨 market 改變；COMMON_SYMBOLS 只供 datalist，不自動套用`
- **🟡 medium** — 市場面板的外殼只是一條 flex-wrap 的原生 select/input/button 工具列，窄寬度會折成凌亂多行；沒有 watchlist、沒有真正的 symbol 搜尋（僅 <datalist>）、沒有 explorer 佈局。DESIGN.md 把『📈 市場』列為 top-level room，實作卻只是單一 <section> panel，離『refined terminal』承諾有距離。
  - 〔證據〕`frontend/components/MarketPanel.tsx:126-127 單一 <section> + flex flex-wrap 控制列；COMMON_SYMBOLS 走 <datalist>（L136-140）；DESIGN.md 導覽樹 📈 市場`
- **🟡 medium** — 四個核心控制（market/timeframe/chartType/bars）皆原生 <select>，雖貼 bg-surface-2，但展開後是 OS 預設下拉（淺色彈窗、系統字、非 tabular），與深色終端機身分割裂。終端機級工具不該在核心控制上露出系統 UI。
  - 〔證據〕`frontend/components/MarketPanel.tsx:142/150/182/188 四個 <select> 皆原生元素`
- **🟡 medium** — 空/錯誤/載入狀態缺乏工藝：載入是純文字『載入 K 線中…』，錯誤直接吐 (candles.error as Error).message，PriceChart 無資料是置中『無資料』。後端 501（台股/美股未實作）與 502（交易所故障）在 UI 完全不區分，也沒有 retry/skeleton。DESIGN.md 強調狀態設計，此處全缺。
  - 〔證據〕`frontend/components/MarketPanel.tsx:226 吐原始 message、:241 loadingCandles 純文字；PriceChart.tsx:309-314 置中『無資料』；markets.py 同一 message 字串供 501/502`
- **🟡 medium** — 行動裝置觸控目標不足：指標/檢視 toggle 與 select 皆 px-2 py-1（約 28–30px 高），低於 DESIGN.md RWD『≥44px』的精神（規範雖明寫於 nav rows，但密集控制列在手機同理）；第一排約 5 個控制 + 第二排約 9 個 toggle 在手機會折成很高的堆疊，加上固定 360px 圖、每個震盪指標再疊 110–120px，行動體驗未經處理。
  - 〔證據〕`frontend/components/MarketPanel.tsx 控制皆 px-2 py-1 / px-3 py-1；PriceChart height={360}（MarketPanel:233）、oscillator h=110(rsi)/120(macd)（PriceChart:209）；DESIGN.md RWD『Touch targets: ≥44px』`
- **🔵 low** — line/area 圖型把主序列顏色硬編成 --up（漲色），不論該段淨方向：一檔下跌標的會被畫成漲色線（台股經 data-market=tw 時 --up=red，又會反過來誤導）。應改用中性 --text 或依淨變動以 --up/--down 著色。
  - 〔證據〕`frontend/components/PriceChart.tsx:77 addLineSeries({ color: up })、:79 addAreaSeries({ lineColor: up, topColor: up })`
- **🔵 low** — 十字準星 legend 直接印原始浮點（legend.open/high/low/close），無 fmt、無逐商品精度——BTC 會出現 43218.123456789 之類長尾（雖有 .num tabular 仍傷可讀性）；legend 也只有 OHLCV，缺 symbol/time/該根漲跌。MarketPanel 已有 fmt() 卻未下放給 PriceChart legend。
  - 〔證據〕`frontend/components/PriceChart.tsx:320-324 直接渲染 legend.open 等未格式化值；對比 MarketPanel.tsx:28 fmt() 僅用於標頭`
- **🔵 low** — 語意與 a11y 細節：hold 用 text-warning(琥珀) 著色，把『中性/觀望』與 DESIGN.md『警示(--warning)』語意混為一談；指標期數全部硬編（MA20/50、EMA20、BOLL20/2、RSI14、MACD12/26/9），toggle 僅開關、無參數 affordance；且整張圖是 canvas，無 data-table fallback、legend 為 pointer-only（pointer-events-none）、無鍵盤操作，螢幕報讀者完全讀不到行情——對宣稱認真的平台是 a11y 空白。
  - 〔證據〕`MarketPanel.tsx:16 SIGNAL_COLORS.hold='text-warning'；indicators/oscillators 期數寫死於 useMemo（:99-110）；PriceChart legend pointer-events-none（:319），canvas 無 a11y 替代`

**重設計提案**

把『市場』從一塊 panel 升級成真正的 explorer room，並分三條主線重做：資料層、AI 訊號可信度、外殼與 DESIGN.md 合規。要保留的是已具高水準的圖表引擎（多副圖時間軸雙向同步、theme-reactive cssVar、暖機 null fail-loud、market-aware --up/--down、live 高水位防 stale update），不要重寫它。

A. 資料層（投資人信任的根本）
- 以 Binance WS 取代雙路 3s REST 輪詢（crypto），並讓標頭價與圖上 pill 同源（消除 ticker.last 與 ohlcv close 兩個數字打架）。擴充 Ticker schema 帶 bid/ask/spread，新增 /api/markets/depth 回 order book top-N，右欄顯示 mini DOM + 價差。
- 把 CcxtBroker 改為『快取單例 + 預載 markets』（目前 registry.py:30/:43 每次 new，導致每輪 fetch 隱式 load_markets）；加伺服器端 candle 快取與 OHLC 一致性驗證（high≥low、open/close∈[low,high]、無負量、重複時間戳/缺口偵測），CSV 匯入同樣驗，並把 _store 從 process 記憶體改為可持久化（重啟不失）。
- 修掉 24h 假標籤：由後端回傳真正 rolling-24h 統計（以時間窗而非『目前 timeframe 的 N 根』），前端不再用 barsPer24h 推導。標頭加『資料新鮮度 chip』：crypto 顯示連線狀態 + 最後 tick 時間（離線轉 --warning）；台股/美股顯示匯入資料 as-of 日期區間。

B. AI 訊號（從『一發意見』變成『可被檢驗、可執行的決策』）
- 餵更厚脈絡（成交量、波動率、多週期、近端結構），並把 200 根固定窗口改為標明時長或隨 timeframe 對齊；confidence 若無法校準，就把『72%』改為離散等級（強/中/弱）避免暗示偽機率。
- 在卡片內嵌『過去 N 次出此訊號的歷史回測表現』迷你 sparkline，把 AI 接上平台最強資產（bar-by-bar 回測引擎）。
- 提供一鍵『據此試算下單』→ 帶出已套 RiskGuard/PortfolioGuard 的部位/風險預覽，讓訊號不再是死路。

C. 外殼與合規（設計師）
- 立即移除 indicator/log/量 toggle 的 bg-accent-dim/border-accent（違反 AI 專屬青色）；active 改中性態（border-strong + surface-3）。青色只留給『⚡ AI 訊號』按鈕與 AI 輸出卡片，並補上『AI 生成』badge 與不確定性視覺化。
- 原生 <select> 換終端機風自訂 control；切 market 時自動帶入該市場預設 symbol（修 BTC/USDT 被送進股票 broker 的狀態 bug）；指標列加齒輪開參數；空/錯誤/載入做 skeleton 與『501 未實作 vs 502 交易所故障 + retry』分流；行動觸控列 ≥44px；canvas 補 data-table fallback 供報讀。

擬議佈局（桌面 explorer，three-pane）：

```
┌ 市場 ─────────────────────────────────────────────── ●live 12ms ─┐
│ [⌕ symbol]  Crypto▾ 1h▾  K線▾  指標⚙  ⏸  [⚡ AI 訊號]            │
├──────────┬──────────────────────────────────────┬───────────────┤
│ Watchlist│  O 43,218.1  H .. L .. C 43,290.4 +1.2%│ Order Book    │
│ BTC +1.2 │  ┌──────────────────────────────────┐ │ 43,291  0.8   │
│ ETH -0.4 │  │        candles + MA20/50         │ │ 43,290  1.2   │
│ SOL +3.1 │  │        (markers: AI buy · 強)    │ │ ─ spread 0.9 ─│
│ ...      │  └──────────────────────────────────┘ │ 43,289  0.5   │
│          │  ┌ RSI 14 ───────────────────────────┐ │ 43,288  2.1   │
│          │  └───────────────────────────────────┘ │               │
├──────────┴──────────────────────────────────────┴───────────────┤
│ ⚡ AI 訊號  BUY · 強(0.72)        ai:claude   據此試算下單 →      │
│ 近 20 次此訊號 ▁▂▅▇▅▃  命中 13/20 · 均報酬 +0.8%                  │
│ 理由：RSI 自 28 反彈、量增、站回 MA20…                            │
└──────────────────────────────────────────────────────────────────┘
```
青色僅出現在『⚡ AI 訊號』按鈕與下方 AI 卡片左緣；watchlist 漲跌與 order book 走 --up/--down（台股自動經 setMarket 反轉）；資料新鮮度 chip 在右上，離線轉 --warning。

**本域新功能提案**

- **Order Book / Depth-of-Market 面板** `(M)` — 後端新增 /api/markets/depth（ccxt fetch_order_book）+ 擴充 Ticker 帶 bid/ask/spread，前端右欄 mini DOM 與價差顯示。　_為何重要:_ 目前只有 OHLCV+last price，認真交易者無從判斷流動性、價差與真實可成交價；這是 TradingView/QuantConnect 的桌面門檻。
- **AI 訊號 → 下單試算橋接** `(M)` — 在 AI 訊號卡片加『據此試算下單』，呼叫既有 execute_order/RiskGuard 路徑回傳部位與風險預覽（不真下單）。　_為何重要:_ 把目前死路的 buy/sell/hold 意見接上平台最強的 risk/execution 資產，讓訊號可被驗證與執行。
- **訊號歷史回測徽章（signal backtest sparkline）** `(L)` — 對同一訊號條件在歷史資料上跑 bar-by-bar 回測，於卡片內嵌命中率/均報酬 sparkline。　_為何重要:_ 未校準的 LLM confidence 無法支撐機率語意；用回測歷史命中率才是可信的可信度來源。
- **資料新鮮度 / 連線狀態指示** `(S)` — 標頭 chip：crypto 顯示 WS 連線狀態+最後 tick 時間，台股/美股顯示匯入資料 as-of 區間，離線轉 --warning。　_為何重要:_ 目前無任何 staleness 指示，交易者可能對著過期資料下單——對 live 是危險盲區。

<br>

### D5. 投組 Portfolio + 損益 Ledger

**現況:** 後端 FIFO ledger、FX seam(已在 /api/risk/status 以 base-currency 暴露「單市場」equity_base)與 RiskGuard 的帳務基礎扎實,但使用者實際面對的「資本真相介面」只是一張寫死 crypto 單市場的側欄卡——跨市場 TWD 淨值、realized 損益 UI、帳戶 equity curve、price_source 失真標記與 reset 帳務一致性全數缺席。

**評分:** 投資人 `2/5` · 設計 `2/5`　|　**判決: `Rework`**

**最高槓桿動作:**
- 打造真正的『投組』房間:新增 GET /api/portfolio/summary,以既有 FxConverter.to_base + quote_currency_for(已在 api/risk.py:48-51 證明可用)做跨市場 TWD 彙總;前端呈現 總權益/總損益(R+U)/今日/曝險 KPI band + 帳戶 equity curve + 回撤 + 水平配置條 + 含 權重/報酬%/market_value/price_source 的部位表。
- 把已存在但全無 UI 的 realized『損益』ledger 接上:在 lib/api.ts/lib/nav.ts 新增 ledger 方法與『損益』leaf;做 date-range + market filter 的損益分頁、FX-normalized 總額(修掉 api/ledger.py:83-88 混幣別相加的 bug),並接 /api/ledger/realized.csv 報稅匯出。
- 帳務一致性與誠實性修補:reset_paper_account 須在同一交易清除該 market 的 Lot/RealizedPnL/OrderRecord 與 equity_baseline RuntimeFlag(消除幽靈 FIFO lot 與 stale daily-loss baseline);UI 把 price_source='avg_fallback' 亮成 --warning stale 並停止把 uPnL 畫成綠色 0;暴露 paper starting_cash 以呈現『總損益=realized+unrealized』與自開戶以來報酬。

**投資人鏡頭 — 發現**

- **🔴 critical** — 沒有任何跨市場彙總 / base-currency(TWD)總淨值。一個嚴肅的多市場平台,第一個要回答的問題是「我換算成 TWD 的總資產是多少」,而這個答案在前端不存在;更糟的是台股/美股的紙上部位在投組頁完全看不到。
  - 〔證據〕`trading/portfolio.py:build_portfolio(broker) 只吃單一 broker;api/orders.py:41 portfolio() 簽名為 ?market=crypto 回傳單市場 PortfolioView;PortfolioPanel.tsx:16 寫死 api.portfolio('crypto')。FX 換算能力其實已存在且已被證明可用——api/risk.py:48-51 以 FxConverter.to_base(view.equity, quote_currency_for(market)) 在 /api/risk/status 暴露『單市場』equity_base/exposure_base(TWD),但(a)從未跨市場相加,(b)lib/api.ts 整個 api 物件沒有任何 risk/ledger 方法、無人呼叫它。registry.py:_paper_cache 各市場分開快取,get_broker(tw_stock,paper) 可經 CsvDataBroker 真的產生台股紙上部位,卻因 PortfolioPanel 寫死 crypto 而永遠不可見。`
- **🔴 critical** — 整個 realized P&L「損益」域對使用者完全不可見——這正是我被指派評估的核心半邊,等於不存在。後端有完整 FIFO 損益帳與報稅 CSV,前端卻沒有任何入口。
  - 〔證據〕`api/ledger.py 提供 GET /api/ledger/realized 與 /api/ledger/realized.csv(回傳 proceeds/cost_basis/fee/tax/gross_pnl/realized_net 與逐筆 disposals);但 lib/api.ts:396-500 的 api 物件無任何 ledger/realized 方法;DESIGN.md 導覽樹(L130-145)與 lib/nav.ts:32 的『投組』下都沒有 損益/ledger leaf,也沒有對應 route。`
- **🟠 high** — 跨市場 realized 報表把不同幣別直接相加,total 是無意義數字。不帶 market filter 時 crypto(USDT)、台股(TWD)、美股(USD)的 proceeds/net 被未換匯加總;此路徑經離線紙上交易(CSV 匯入 tw/us)即可觸發,非純理論。
  - 〔證據〕`api/ledger.py:83-88 realized_report() 直接 sum(r.proceeds ...)、sum(r.realized_net ...);_query()(L58-69)在 market is None 時不加 where、跨市場混抓。models.py:116-134 RealizedPnL 以各市場 quote 幣別儲存(crypto=USDT、tw=TWD、us=USD)且無 FX 正規化欄位,total_realized_net 把三種幣別當同一單位相加。`
- **🟠 high** — 實際 paper/live 帳戶沒有 equity curve / 歷時績效 / 回撤 / benchmark。投組視圖是單一時間點純量快照,無法回答『這段期間賺賠多少、最大回撤多深、有沒有打敗 buy&hold』。
  - 〔證據〕`trading/portfolio.py:20-25 PortfolioView 只有 cash/positions/positions_value/equity 四個純量,無時間序列;models.py 內僅 WorkflowRun.equity_curve_json(L168)是給『回測/工作流 run』用,standing paper/live 帳戶沒有任何 PortfolioSnapshot 表被持久化,APScheduler 也未週期寫入帳戶淨值。`
- **🟠 high** — price_source='avg_fallback' 在 ticker 失效時把現價靜默改成成本價,使 unrealized_pnl=(avg-avg)*qty=0,且 UI 以『漲色(text-up)』渲染這個 0——一個價格失效被畫成綠色(台股紅色)的『微幅獲利/兩平』,主動誤導,違反 fail-loud。
  - 〔證據〕`trading/portfolio.py:37-52 except 後 price=pos.avg_price、source='avg_fallback'、unrealized_pnl 計為 0;PortfolioPanel.tsx:74 與 HomeDashboard.tsx:304 用 `unrealized_pnl >= 0 ? 'text-up' : 'text-down'`,0 落在 text-up;PositionView.price_source 雖在 lib/api.ts:52 有型別卻無人讀取,使用者無從分辨『真兩平』與『我們不知道現價』。`
- **🟠 high** — 重置紙上帳戶造成 PaperAccount 與 FIFO ledger / 風控 baseline 失同步。確定且嚴重的後果是『幽靈成本基礎』:reset 後 Lot.remaining_quantity 仍 >0,下一筆賣單會 FIFO 消耗 reset 前的舊 lot,產生錯誤 realized P&L;另在『當日曾較起始資金獲利』的情境下,殘留的 equity_baseline 會讓 daily-loss 誤觸 halt。
  - 〔證據〕`registry.py:70-73 reset_paper_account() 只呼叫 PaperStore(market).reset();paper_store.py:69-74 reset() 只刪 PaperAccount+PaperPosition。Lot/RealizedPnL(models.py:98-134)、OrderRecord、以及 RuntimeFlag 的 equity_baseline:<UTC date>(runtime_state.py:65-76 由 get_or_snapshot_day_start_equity 寫入、risk.py:138-141 用來算 daily-loss)皆未清。ledger.py:86-93 record_sell 以 order_by(opened_at,id) 取最舊 lot,故 reset 後第一筆 sell 直接吃幽靈 lot。`
- **🟡 medium** — 沒有『總損益 = realized + unrealized』與『自開戶以來報酬』的單一真相。使用者看得到 equity,卻無法得知淨賺賠多少:realized 在未被前端使用的 /api/ledger,unrealized 在 /api/orders/portfolio,兩者從未合併;且 paper 起始資金未透過 API 暴露。
  - 〔證據〕`PortfolioView(trading/portfolio.py:20-25)無 starting_cash/total_pnl/total_return_pct;paper.py:42 知道 settings.paper_starting_cash 與 _cash 但 build_portfolio 不回傳;realized 總額在 api/ledger.py 另一條未接 UI 的路徑,從未與 portfolio 合併。`
- **🟡 medium** — 缺少每部位的權重 / 曝險 / 報酬率,也沒有帳戶層級 benchmark;後端已算好的 market_value 在專屬投組頁完全沒用到。
  - 〔證據〕`PositionView(trading/portfolio.py:15)已含 market_value 卻在 PortfolioPanel.tsx:57-80 的表(代號/數量/均價/現價/未實現)完全沒顯示;無 position weight(market_value/equity)、無 unrealized_pnl_pct(lib/api.ts:45-53 PositionView 無此欄位);HomeDashboard.tsx:304 只顯示 unrealized 絕對值無 %,無 buy&hold/指數對照。`
- **🟡 medium** — 訂單歷史無法呈現成本與 realized 損益、跨市場混雜、且無分頁。paper fill 算出的 fee/tax 在落地時被丟棄,OrderRecord 不連 Lot/RealizedPnL;list_orders 無 market filter,使寫死 crypto 的投組頁實際顯示『全部市場』訂單。
  - 〔證據〕`paper.py:117 回傳 info={'fee','tax'};execution.py:88-101 寫 OrderRecord 時不存 fee/tax(models.py:14-29 OrderRecord 無此欄位,且 execution.py:115 只把 buy fee 轉給 record_fill,sell fee/tax 不落地於訂單);api/orders.py:36-37 list_orders() 一次回傳全部列且無 market 條件;PortfolioPanel.tsx:90 與 HomeDashboard.tsx:322 前端 .slice(0,8),無分頁、無 market·symbol·日期 filter。`

**設計鏡頭 — 發現**

- **🟠 high** — 『投組』被 DESIGN.md 提升為頂層房間,但 /portfolio 整頁只是把 交易室 的側欄小卡原封不動全螢幕化,沒有專屬高密度版面。
  - 〔證據〕`app/(rooms)/portfolio/page.tsx 全頁僅 `return <PortfolioPanel/>`;PortfolioPanel.tsx:23 是一張 rounded-lg 小 section(3 個 Stat + 一張 5 欄窄表 + 近 8 筆訂單),無 equity curve/allocation/drawdown/realized ledger。DESIGN.md L121 原把 portfolio 設計成 交易室 `2fr 1fr` 的側面板、L140 又把『投組』列為頂層 nav 房間,卻從未補上專屬密集版面 spec,實作直接沿用側卡。`
- **🟠 high** — 被指派的『損益 Ledger』在 IA 上完全不存在:導覽樹沒有 leaf、沒有 route、api client 沒有方法。對一個頂層關注點而言是結構性 IA 缺口。
  - 〔證據〕`lib/nav.ts:32 『投組』為無 children 的單一 leaf,底下沒有『損益』;DESIGN.md 導覽樹(L130-145)同樣無 損益;app/(rooms) 下無 ledger 路由;lib/api.ts 無 ledger 方法,/api/ledger/realized(.csv) 永遠到不了畫面。`
- **🟡 medium** — 在展示真實資本的 /portfolio 與首頁快照,LIVE 訊號只是一顆『不會脈動』的靜態 pill。DESIGN.md 對投組的硬性要求(portfolio chip reads LIVE)有達成,但 Motion 規範的『LIVE indicator pulses(唯一刻意動畫)』未落實,真錢面的『不可錯認』程度不足。
  - 〔證據〕`PortfolioPanel.tsx:27-34 與 HomeDashboard.tsx:198-204 的 live 標示為 bg-live/15 text-live 的小 pill、無 animate-pulse;DESIGN.md『Motion』段明訂 the LIVE indicator pulses;DESIGN.md『Live mode』要求的 portfolio chip=LIVE 已滿足,故此為動效/訊號強度問題而非 chip 缺失。`
- **🟡 medium** — KPI 階層在 PortfolioPanel 是平的——三張等權重卡(現金/部位市值/權益),最重要的 equity 沒有視覺主導;反而首頁快照做得比專屬頁好,造成退步式不一致。
  - 〔證據〕`PortfolioPanel.tsx:51-55 用 grid-cols-3 等大 Stat 呈現 cash/positions/equity;HomeDashboard.tsx:210-219 把 equity 做成 num text-3xl hero 再帶三個 KPI(含 uPnL 並上 tone 色),專屬投組頁反而比首頁卡退步。`
- **🟡 medium** — 破壞性的資本動作用瀏覽器原生 confirm(),off-brand、非主題感知,且沒有揭露對 Lot/RealizedPnL 的副作用,也沒有 paper-only 鎖定提示。
  - 〔證據〕`PortfolioPanel.tsx:36-37 onClick 內 `if (!confirm('重置紙上交易帳戶(現金與部位)?')) return;`——原生 confirm 不吃 DESIGN.md 深色終端機樣式;文案僅提『現金與部位』,未提同時遺留 Lot/RealizedPnL/equity_baseline 的一致性後果。`
- **🟡 medium** — 資料密度與易讀性不足:數量以原始 float 直出、價格用 2dp 的 money() 會吃掉小幣值精度、已算好的 market_value 不顯示,專業投組必備欄位缺席。
  - 〔證據〕`PortfolioPanel.tsx:71 `<td className='num'>{p.quantity}</td>` 與 HomeDashboard.tsx:301 直印未格式化數量;PortfolioPanel.tsx:72-73 對 avg/price 用 money()(maximumFractionDigits:2),對 0.00012 類小幣值會顯示為 0,而 HomeDashboard.tsx:35-39 已有依量級調整小數的 price() 卻未用於投組;PositionView.market_value 在 PortfolioPanel 完全沒用到;表內缺 市值/權重%/報酬% 欄。`
- **🟡 medium** — empty / loading / error / stale 狀態缺乏工藝。載入是一行字、錯誤直接吐 raw message、reset 成功無 toast、price_source='avg_fallback' 沒有任何視覺標記。
  - 〔證據〕`PortfolioPanel.tsx:84 載入只有 text-faint 一行『載入中…』、L48 錯誤直印 `(portfolio.error as Error).message`;無 skeleton、無 per-row『現價過期』狀態(price_source 被忽略)、reset(L36-44)後僅 invalidateQueries 無確認回饋。`
- **🟡 medium** — UI 無多市場切換 / 彙總,投組頁永遠只顯示加密貨幣;台股 data-market='tw' 的紅漲綠跌反轉路徑在此面走不到。
  - 〔證據〕`PortfolioPanel.tsx:16 寫死 'crypto',無 market tabs 也無合併視圖;HomeDashboard.tsx:49-51 雖會 setMarket() 切 data-market,但專屬投組頁只看得到 crypto,台股使用者的 --up/--down 反轉與部位都到不了。`

**重設計提案**

把『投組』從一張側欄卡升級為真正的高密度房間,並補上後端已具備、前端從未呈現的真相層(realized ledger、FX 彙總、price_source 旗標)。重點:幾乎所有零件都已存在於後端,redesign 主要是『接線 + 一個彙總 seam + 兩個一致性修補』,不是造新引擎。\n\n一、後端(複用既有零件,證據在 api/risk.py:48-51 已示範同一組 API):\n- 新增 GET /api/portfolio/summary:對『有 PaperAccount 的市場』(非只 implemented_markets,因 tw/us 可經 CsvDataBroker 紙上交易)各跑 build_portfolio(get_broker(m)),以 FxConverter.to_base(value, quote_currency_for(m)) 換成 base_currency(TWD),回傳 per-market(equity/positions/exposure)+ combined(total_equity_base/total_cash_base/total_exposure_base)+ fx_rate 與 fx_source(static/open_er_api)。把目前 risk.py『私用』的 FX 能力正式搬到真相介面。\n- 修 realized:realized_report() 對每列以 quote_currency_for(row.market) 換 base 後再加總,回傳 per-market 細項 + 一個 base-currency total,並標明 fx_source(修掉 api/ledger.py:83-88 USDT+TWD+USD 直接相加的 bug)。\n- 新增輕量 PortfolioSnapshot(market, equity_base, ts),由既有 APScheduler 週期寫入,餵帳戶 equity curve 與 max drawdown(目前 equity_curve 只存在於回測 WorkflowRun)。\n- reset 一致性:reset_paper_account 內於『同一交易』刪除該 market 的 Lot/RealizedPnL/OrderRecord 並清除 equity_baseline:<date> RuntimeFlag,杜絕幽靈 lot 與 stale daily-loss baseline。\n- lib/api.ts 補上 portfolio.summary、ledger.realized、ledger.realizedCsv(以及 risk.status,順帶讓 kill-switch/halt 在前端可見)。\n\n二、投組房間版面(深色終端機、Geist Mono tabular-nums、tight radii;台股載入時 root 設 data-market='tw' 走紅漲綠跌):\n\n┌─ 投組. ───────────────────────────── [paper] / 〔● LIVE 脈動 chip〕 ─┐\n│ 總權益(TWD)      總損益(R+U)        今日損益      現金        曝險 │\n│  3,142,880      +218,440 (+7.5%)   +12,300     980,400    68.7% │\n│  num 3xl hero    ▲up/▼down 色         today       cash      bar  │\n│  FX: open_er_api · USD 31.5 · 更新 12:03                          │\n├──────────────────────────────┬───────────────────────────────────┤\n│  權益曲線 + 回撤(下方陰影)   │  資產配置(水平條,非圓餅,避 slop)│\n│  ╱╲    ╱╲___╱                │  crypto  ████████████ 52%          │\n│  ──────────────  maxDD -9.2% │  台股    ██████ 28%                 │\n│                              │  美股    ████ 20%                  │\n├─────────────────────────────────────────────────────────────────┤\n│ [部位] [損益 Ledger] [訂單]  ← tabs                               │\n│ 代號     市場 數量     均價   現價    市值     權重  未實現(額/%) │\n│ BTC/USDT cx  0.842   58,210 61,340 51,648  28.4% +2,634 +5.4% │\n│ 2330     tw  1,000   915.0  1,040  1,040k  18.1% +125k +13.7%│\n│ AAPL ⚠   us  40      188.2  —(過期)7,528* —    n/a(現價過期)│\n│  ⚠ = price_source='avg_fallback':以 --warning 標列、現價顯示 —、 │\n│      uPnL 顯示 n/a(不可畫成綠色 0),tooltip 說明現價來源失效     │\n└─────────────────────────────────────────────────────────────────┘\n\n三、損益 Ledger 分頁(首次把 /api/ledger 接上 UI):日期區間 + market/symbol filter、總額卡(proceeds/cost_basis/fee/證交稅 tax/gross/net,FX 正規化並標 base 幣別),逐筆 disposal 表,右上『匯出報稅 CSV』直接打 /api/ledger/realized.csv;lib/nav.ts 在『投組』下新增『損益』leaf(icon 用 --text-faint,維持 cyan 僅限 AI)。\n\n四、信任邊界與一致性:\n- LIVE 時 chip 讀 LIVE 並加 animate-pulse(落實 DESIGN.md Motion『the LIVE indicator pulses』);因投組是檢視面而非送單面,沿用 chip 即符合 DESIGN.md 對 portfolio 的要求,不需把送單面的粉紅 banner 硬搬過來。\n- reset 改用主題化 modal(取代原生 confirm),文案明列『將同時清除部位、FIFO 成本基礎(Lot)、已實現損益與當日風控 baseline』,且僅在 paper 模式可用。\n- avg_fallback 一律以 --warning 標列 + tooltip『現價來源失效,以成本價標記,未實現損益不可信』;uPnL 不再以漲色畫 0。\n- 數量/價格走統一 num 格式器(沿用 HomeDashboard 的 price() 依量級決定小數位,而非投組頁的 2dp money()),market_value 一律顯示。\n\n色彩紀律:up/down 一律走 --up/--down token(台股 data-market='tw' 反轉);electric cyan --accent 不進投組(此處無 AI/自動化語意);live 僅用 --live。

<br>

### D6. 風控 Risk & capital controls

**現況:** 後端有真實但僅及零售級的「下單前」風控骨架(kill switch / halt / 單日虧損 / 曝險 / FX base-ccy / exit-always-allowed),卻採 lazy pre-trade 評估、限額部分硬編碼且幣別不一致、日界用 UTC、靠 avg_fallback 髒價判風險,而前端完全沒有任何風控介面 — 最攸關安危的 kill switch 只能用 curl 觸發。

**評分:** 投資人 `2/5` · 設計 `1/5`　|　**判決: `Rework`**

**最高槓桿動作:**
- 建 always-reachable Risk Cockpit + 全域常駐 kill switch:三個 /api/risk 端點已齊備,前端卻 0 次呼叫、無路由、無 nav,且 TopBar 連 DESIGN.md 規定的 live/paper context 都沒實作 — 先補齊 top bar、接上 UI,並讓 halted/kill 在所有頁永遠可見(遵 --live 危險信號)。
- 把風控從 lazy pre-trade 改為 continuous monitor:用既有 APScheduler 排程重算 equity/exposure/daily-loss、對 avg_fallback 髒價 fail loud,並把 day-start equity 改成各市場真實 session open 基準、halted 改日期作用域(修正 UTC 換日、首讀快照導致的跳空漏接,以及跨日未清的靜默熄火)。
- 讓限額可設定且幣別/單位一致:RiskGuard 加 from_settings() 並全程 fx.to_base(消除『50000』在 crypto 是 50k USDT、台股是 50k TWD 的 31x 失準),再補 %-of-equity 限額、用 Signal.confidence 的 per-signal position sizing、per-strategy 資本預算,與 check→place 的鎖以消除 TOCTOU 超限。

**投資人鏡頭 — 發現**

- **🔴 critical** — 風控閘門是「下單前、且僅在嘗試送出新進場(buy)那一刻」才被動評估 — 沒有任何持續性監控。max_daily_loss / max_total_exposure 只在 PortfolioGuard.check() 內計算,而該函式只由 execute_order 在 session 存在時、送單前呼叫一次。若使用者整天不下新單,equity 可盤中崩跌遠超過 max_daily_loss、曝險可因價格上漲突破 max_total_exposure_value,卻永遠不會觸發 halt。scheduler/service.py 雖用 APScheduler 但只跑 run_workflow,沒有任何排程式 risk re-eval。對 LIVE 平台這是資本安全的致命缺口。
  - 〔證據〕`backend/app/trading/risk.py:95-188 PortfolioGuard.check 僅由 backend/app/trading/execution.py:81-83 在送單時呼叫;backend/app/scheduler/service.py:53-80 僅 run_workflow,無 risk/halt re-eval`
- **🟠 high** — per-order RiskGuard 限額完全硬編碼、不可設定(注意:PortfolioGuard 反而可由 from_settings() 設定)。_default_guard = RiskGuard() 以 max_order_value=50_000、max_position_value=100_000 寫死;RiskGuard 沒有 from_settings(),.env.example 也只有 PortfolioGuard 的四個變數(MAX_TOTAL_EXPOSURE_VALUE/MAX_DAILY_LOSS/MAX_ORDERS_PER_DAY/KILL_SWITCH),無 RISK_MAX_ORDER_VALUE/RISK_MAX_POSITION_VALUE。orders API 以 execute_order(request, market, session) 呼叫、不傳 guard,故全平台單筆/單一部位上限鎖死,要改必須改 code。
  - 〔證據〕`backend/app/trading/risk.py:19,21-24;backend/app/api/orders.py:26 execute_order 未傳 guard;.env.example:77-85 無 RiskGuard 變數`
- **🟠 high** — RiskGuard 與 PortfolioGuard 的幣別單位不一致 — 同一套風控用兩種貨幣量。RiskGuard.check 直接以 fill_price*request.quantity(quote currency,crypto=USDT)判斷且不做任何 FX 換算;PortfolioGuard 全部 fx.to_base() 換成 base currency(TWD)。同一個寫死的「50000」對 crypto 是 50k USDT(≈1.58M TWD),對台股卻是 50k TWD — 真實風險相差約 31 倍,跨市場時 per-order 風控形同失準。
  - 〔證據〕`backend/app/trading/risk.py:35 order_value=fill_price*request.quantity(無 FX)對比 risk.py:103-113,172 PortfolioGuard 全程 fx.to_base`
- **🟠 high** — 風控以 build_portfolio 的市值為基準,但價格源失敗時靜默退回 avg_price(cost basis)且風控層不 fail loud。portfolio.py 在 get_ticker 例外時把 current_price 設為 avg_price、source='avg_fallback' 僅記在 view 內;PortfolioGuard 只讀 view.equity/positions_value,從不檢查 price_source。資料源中斷時,equity 與 exposure 會以成本價而非市價計算 — 行情急殺期間(最需要 halt 時)daily-loss/exposure 閘門卻看不到真實虧損。這違背風控路徑的 fail-loud 原則,是資料完整性×資本安全的複合缺口。
  - 〔證據〕`backend/app/trading/portfolio.py:36-40 例外退回 avg_price+source flag;risk.py:111-113 僅用 view.equity/positions_value,未消費 price_source`
- **🟠 high** — day-start equity 基準不是真正的盤前 equity,而是「今天第一次有人讀取它」時才快照(風控檢查或 /api/risk/status 都會觸發)。get_or_snapshot_day_start_equity 採 lazy first-read;且在 risk.py 中 exits 於 107-108 早退,baseline 快照在 138 行才執行。若隔夜跳空下殺後才首次觸發,基準被設在已虧損後的 equity,daily-loss halt 永遠不會對真正的損失觸發。
  - 〔證據〕`backend/app/trading/runtime_state.py:65-76 lazy first-read 快照;backend/app/api/risk.py:65 status 端點亦會觸發快照;risk.py:107-108 exit 早於 risk.py:138 baseline`
- **🟠 high** — 所有日界與計數用 UTC 行事曆日,對台股/美股是錯的。_today_utc()/_start_of_today_utc()/count_orders_today 都以 UTC 00:00 為界。台股(UTC+8)盤中、美股(ET)約晚間就會被 UTC 換日從中切斷 — max_daily_loss 視窗與 max_orders_per_day 會在交易時段中途被重置/分割。crypto(24/7)用 UTC 尚可,但多市場 LIVE 平台這是正確性 bug。
  - 〔證據〕`backend/app/trading/runtime_state.py:24-30,79-84 一律 UTC date,無 per-market session 邊界`
- **🟠 high** — 完全沒有 per-signal 部位規模(position sizing)。order node 用固定 quantity 參數(預設 1)算 target_qty,Signal.confidence 雖被 combine node 計算(AND/weighted)卻從不進入下單規模。沒有 %-of-equity、Kelly、ATR/波動度平價、風險預算化下單量。對嚴肅交易者這是 edge 可信度的根本缺口 — 訊號強弱與部位大小脫鉤(目標狀態明列 position sizing 應存在)。
  - 〔證據〕`backend/app/workflow/nodes.py:188 target_qty=float(p.get('quantity',1));Signal.confidence(backend/app/schemas.py:62)僅在 nodes.py:233/252/264 計算,未進下單路徑`
- **🟡 medium** — halted 是一個非日期作用域、無 UI 可清除的單向閂鎖,會無聲跨日延續。set_halted 寫入 RuntimeFlag key='halted'(無日期);equity baseline 以日期為 key 每日重置,但 halted 不會自動重置。週一 daily-loss breach 後,週二有了新 baseline 卻仍 halted=true、所有進場被擋,而前端無任何畫面顯示原因,只能靠 curl POST /api/risk/resume。雖 fail-closed(只擋進場、放行出場)語意安全,但對 LIVE 營運是嚴重的「策略被靜默熄火」陷阱。
  - 〔證據〕`backend/app/trading/runtime_state.py:61-62 set_halted 無日期 key;對比 65-76 baseline 以 _today_utc() 為 key 每日重置`
- **🟡 medium** — check 與下單之間存在 TOCTOU 競態,無任何鎖。execute_order 先 guard.check + pguard.check(讀 exposure/orders_today),再 broker.create_order、最後 session.add。BackgroundScheduler 以執行緒跑多個 workflow、加上手動下單並行時,兩筆訂單可各自讀到低於上限的曝險/筆數而同時通過,實際超限。SQLite 序列化寫入無法保護「讀-判-寫」的非原子性。
  - 〔證據〕`backend/app/trading/execution.py:75,83,85 check→create_order 間無 row lock/advisory lock;scheduler 為 BackgroundScheduler 多執行緒`
- **🟡 medium** — 限額皆為絕對金額,無權益百分比、無漸進去槓桿/波動度目標。max_daily_loss/max_total_exposure_value/max_position_value 都是固定數字,帳戶變大時相對保護縮水、變小時更易被擊穿;沒有 max position % of equity、沒有 drawdown-based deleveraging、沒有 volatility targeting。風控是二元 allow/block,無法隨回撤或波動縮放部位。(絕對硬停損本身合理,故非 high。)
  - 〔證據〕`backend/app/config.py:132-135 全為絕對值;backend/app/trading/risk.py 全程僅 > 比較,無 equity 比例或 scaling`
- **🟡 medium** — 沒有 per-strategy / per-workflow 資本預算 — 全平台共用一組全域限額。所有 workflow 的下單共享同一個 max_daily_loss/max_total_exposure/max_orders_per_day/kill_switch。無法對策略 A 配 100k、策略 B 配 50k,也無法單獨停掉某策略。多策略平台這是 table-stakes(Composer/QuantConnect 皆有)。
  - 〔證據〕`backend/app/trading/risk.py:83-93 PortfolioGuard.from_settings 僅讀單一全域 settings,無 strategy/workflow 維度`
- **🟡 medium** — 沒有集中度/相關性/產業限額。唯一的部位級限制是 per-symbol 絕對 max_position_value(且如上未 FX 正規化);沒有「單一標的最多佔權益 X%」、沒有 sector/asset-class 上限、沒有相關性叢集限制。可把全部資金壓在三檔高度相關標的而不觸發任何閘門。
  - 〔證據〕`backend/app/trading/risk.py:40-50 僅 per-symbol projected_value 比較,無跨標的集中度/相關性檢查`
- **🟡 medium** — 沒有槓桿/保證金/做空模型,exposure 定義天真。positions_value 只加總多頭市值;_is_exit 只認得「賣出已持有多頭」為出場。目標狀態要求的做空/槓桿在風控層完全未建模(無 gross/net notional、margin、buying power)。一旦開放做空,buy-to-cover 會被當成 entry 而被 halt 擋下(語意反向)。
  - 〔證據〕`backend/app/trading/portfolio.py:33-41 僅多頭市值;backend/app/trading/risk.py:53-62 _is_exit 僅 sell+held>0`
- **🟡 medium** — max_orders_per_day 是粗糙整日計數,無每分鐘速率限制或價格熔斷。出錯/迴圈的 workflow 在排程下可數秒內連發到打滿當日上限(預設 50);沒有 per-minute throttle、沒有對價格急跌的 circuit breaker、沒有 runaway-loop 防護。
  - 〔證據〕`backend/app/trading/runtime_state.py:79-84 count_orders_today 僅日計數;risk.py:157-169 僅比對當日總數,無時間窗速率`
- **🔵 low** — 出場(exits)繞過所有閘門且不留紀錄/不 notify;且 config 級 kill_switch 無法被 runtime resume 解除。risk.py:106-108 exit 直接 return 無 notify(entry 各 gate 皆 notify),halt/kill 期間的出場無 audit 軌跡;另 effective kill = settings.kill_switch OR runtime,故 .env 設 KILL_SWITCH=true 時,UI/curl 的 kill-switch off 與 resume 都無法解除,需改 env+重啟。
  - 〔證據〕`backend/app/trading/risk.py:106-108 exit 早退無 notify;risk.py:116 與 backend/app/api/risk.py:54 effective kill 為 config OR runtime`

**設計鏡頭 — 發現**

- **🔴 critical** — 平台完全沒有風控介面。後端 /api/risk/status、/api/risk/kill-switch、/api/risk/resume 三端點齊備,但 grep frontend/lib/api.ts 對 'api/risk' 命中 0(僅 'risk_exit' node type 與一段註解),前端從未呼叫;沒有 /risk 路由(app/(rooms) 下無 risk 目錄)、nav.ts 無風控節點。對要做 LIVE 的平台,這是最嚴重設計缺口:風控狀態完全不可見。
  - 〔證據〕`grep 'api/risk' frontend/lib/api.ts 僅命中 risk_exit/註解;frontend/app/(rooms) 無 risk 目錄;frontend/lib/nav.ts NAV 無風控項`
- **🔴 critical** — 最攸關安危的控制 — kill switch 與 resume(daily-loss halt 後手動恢復)— 只能用 curl 觸發。POST /api/risk/kill-switch 與 /resume 存在,但 UI 無任何按鈕(components/ 下無 Risk/KillSwitch 元件;grep kill_switch/halted 在前端僅命中 docs/manual 文案,非操作元件)。DESIGN.md 反覆強調 paper↔live 信任邊界與危險信號,實際的緊急停止鍵卻不存在於畫面上。
  - 〔證據〕`backend/app/api/risk.py:69-80 端點存在;前端 grep kill_switch/halted 僅 frontend/app/manual/page.tsx、components/docs/SystemFeatures.tsx、components/manual/Diagrams.tsx(文案)`
- **🟠 high** — halt/kill 狀態沒有全域常駐信號。現有的 paper/LIVE chip 是由 config.data.trading_mode 驅動(PortfolioPanel、workflow Toolbar),與風控 RiskStatus.halted/kill_switch 完全無關;AppShell/TopBar 都不消費 RiskStatus。使用者可能在策略被 halt 靜默擋單時毫不知情。DESIGN.md:40-44 要求 LIVE 必須有不可錯認的安全狀態,但風控介入態在任何頁面都不顯示。
  - 〔證據〕`frontend/components/PortfolioPanel.tsx:29 與 frontend/components/workflow/Toolbar.tsx:36,42 chip 來自 trading_mode,非 risk;RiskStatus.halted(api/risk.py:29,57)前端未消費`
- **🟡 medium** — 目前的 slim top bar 比 DESIGN.md 規格還薄,沒有風控/即時 context 的容身處。DESIGN.md:115-118 規定 top bar 放『market color、theme、live/paper』,但 TopBar.tsx 實際只 render 漢堡鍵 + 品牌(限 mobile)+ ThemeToggle + 文件中心連結 — 連 market 與 live/paper 控制都沒實作。要放常駐 kill-switch chip,必須先把這條 context bar 補齊。
  - 〔證據〕`frontend/components/shell/TopBar.tsx:19-27 僅 ThemeToggle + /docs 連結,無 market/live-paper 控制(對比 DESIGN.md:115-118)`
- **🟡 medium** — 風控告警只走後端 notify(),沒有對應的阻斷式 UI 反饋。每個 gate 觸發都 notify(warning/error)寫入通知,但前端 NotificationsPanel 是被動列表,沒有把『entry blocked / halted』升級為需確認的危險態 toast/banner(role=alert)。LIVE 下被擋單只多一條列表項,latency/feedback 不符 DESIGN.md 對 LIVE 的要求。
  - 〔證據〕`backend/app/trading/risk.py:117-187 各 gate notify;frontend/components/NotificationsPanel.tsx 為一般列表,無危險態升級`

**重設計提案**

目標:把現在「藏在後端、curl-only」的風控,升級為 always-reachable 的 Risk Cockpit + 全域常駐 kill switch,並把後端從 lazy pre-trade 改為 continuous monitor。顏色全遵 DESIGN.md:--accent 仍只給 AI;風控危險態一律用 --live(pink)/--warning/--error;漲跌走 --up/--down 且台股 data-market=tw 反轉;數字一律 .num tabular-nums。

先修正一個前提:TopBar.tsx 目前只有 ThemeToggle + 文件連結(19-27),連 DESIGN.md:115-118 要求的 market / live-paper 控制都還沒實作。所以第一步是把這條 slim context bar 補齊,kill-switch chip 與之同住。

A. 全域常駐 risk chip(補齊後的 top bar,所有頁面可見)
chip 消費目前前端 0 次呼叫的 /api/risk/status。平時極簡灰點;halted/kill 時整顆轉 --live 底並沿用 DESIGN.md「LIVE 指示燈那一個刻意的脈動」(Motion 章)。

```
┌ AI Trade Flow ─────────────────  [crypto▾] [paper▾] [◐ theme]  [● 風控 OK]  [文件中心 ↗]┐
                                                                  └ 點擊展開 Risk Drawer
 ── halt 觸發時(--error/--live 脈動,role=alert)──        [paper]   [⏻ HALTED · 點此處理]
```
- 常態:--text-faint 圓點 +「風控 OK」;halted/kill:--live 底 + pulse,文字「HALTED」/「KILL ON」。
- chip 一鍵展開 Risk Drawer,含 confirm 對話框後的「⏻ Kill Switch」與「Resume」(resume 用 --warning,因為它解除保護)。

B. Risk Cockpit 頁(nav 新增頂層「風控」leaf,icon=ShieldAlert,--text-faint;因攸關 LIVE 資本安全,放頂層而非埋進「工具」)
消費 /api/risk/status 全部欄位,版面 2fr 1fr 密集 tabular。

```
風控 Risk.            base: TWD   market: crypto▾                 [⏻ KILL SWITCH]  ← --live btn
┌─ 狀態 ────────────────────────────┐┌─ 限額使用率 (base TWD) ───────────────────┐
│ Kill switch   ● OFF  (cfg off/rt off) ││ 單日虧損   ▓▓▓▓▓░░░░░  62%   62,000/100,000 │ bar:--warning→--error
│ Halted        ● NO   (自 06-25 延續?) ││ 總曝險     ▓▓▓▓▓▓▓░░░  71%  710,000/1,000,000│
│ 今日下單      18 / 50                  ││ 今日下單   ▓▓▓▓░░░░░░  36%      18/50         │
│ 日初權益   1,000,000  現權益 938,000   ││ 單筆上限   50,000 USDT ⚠≈1.58M TWD(未 FX)   │ ← 攤開單位矛盾
│ 今日損益   ▼ −62,000 (−6.2%) [--down] ││ 單一部位   100,000 USDT ⚠ 跨市場不一致        │
│ 報價源     ⚠ 1 檔 avg_fallback(髒價)  ││                                              │
└────────────────────────────────────────┘└──────────────────────────────────────────────┘
┌─ 風控事件 (audit timeline) ──────────────────────────────────────────────────────────┐
│ 09:42  max_daily_loss breached → HALTED   −62,000 TWD   gate=max_daily_loss   [error]  │
│ 09:31  entry blocked  BTC/USDT buy 2      gate=max_total_exposure             [warning] │
└────────────────────────────────────────────────────────────────────────────────────────┘
```
- 今日損益用 --down(台股市場自動 --up 反轉);使用率 bar 80% 前 --warning、超標 --error。
- 「單筆上限」「單一部位」旁主動標 quote↔base 換算與 ⚠,把後端的幣別不一致直接攤在使用者面前(fail-loud 的 UI 版)。
- 新增「報價源」列:當 build_portfolio 有 price_source=avg_fallback 時亮 ⚠,提醒此刻 equity/exposure 可能用髒價算。
- Halted 列標示其延續日期,讓「跨日未清的閂鎖」可見可清。
- 事件流 render notify 的 meta.gate 作 audit timeline。

C. 後端必要重構(讓上面 UI 有真實、可信數據)
1. RiskGuard.from_settings() + RISK_MAX_ORDER_VALUE/RISK_MAX_POSITION_VALUE 入 .env,並全程 fx.to_base 與 PortfolioGuard 同幣別(消除幣別不一致)。
2. 風控改「pre-trade + 排程 post-trade monitor」:沿用既有 APScheduler(scheduler/service.py)每 N 秒重算 equity/exposure/daily-loss,跨門檻即 set_halted+notify,讓 cockpit 為實時而非「上次送單時」。
3. day-start equity 改為「該市場 session open」真實基準(非 UTC、非首次讀取);halted 改為日期作用域或每日 session open 自動清除(現為非日期 key、跨日延續)。
4. 風控路徑對 price_source=avg_fallback fail loud:髒價時拒絕放行新進場或在 cockpit 明示降級。
5. 新增 %-of-equity 限額(max_position_pct_of_equity、max_daily_loss_pct)與絕對值取 min;per-signal sizing 用 Signal.confidence(現已算出卻棄用)。
6. check→place 加鎖(per-market 序列化或 SELECT…FOR UPDATE 等價)消除 TOCTOU 超限。

D. RWD / a11y
- top bar 風控 chip 在 mobile 收進漢堡旁仍保留危險態圖示(halt 時絕不隱藏)。
- Kill/Resume 一律經 confirm dialog;按鈕 aria-label 明示「進場將被封鎖」;halt banner 用 role=alert。
- Cockpit 表格 horizontal scroll 不換行,tabular-nums 對齊不破(DESIGN.md RWD「No clipped data」)。

<br>

### D7. 排程 Schedules (automation)

**現況:** 後端排程有經過思考的原語(coalesce / max_instances=1 / misfire grace / target-position 冪等 / market-hours gate),但缺持久化 jobstore、缺 schedule 層失敗告警、cron 無時區,前端又把這些能力與全域 paper↔live 邊界整個藏在一張裸 admin 表後面——以「無人值守跑真錢」的標準仍不可信。

**評分:** 投資人 `2/5` · 設計 `2/5`　|　**判決: `Rework`**

**最高槓桿動作:**
- 閉合 schedule 層的靜默失敗迴路(資本安全最優先):RunResult.error 即 notify() 補上 risk/execution 未覆蓋的 data_source/strategy/broker 失敗路徑 + 連續 N 次失敗自動停機告警 + 換持久化 SQLAlchemyJobStore 並對停機漏跑寫 missed RunLog,讓無人值守 bot 失敗時一定被看見。
- 把面板重做成 trust surface:全域 TRADING_MODE banner(live 走 --live 脈動,因 mode 今日是全域 settings.trading_mode 而非每排程),真實健康(next_run_time / job-alive 心跳 / 可點開的 RunLog error 歷史),修掉 bg-up『綠=執行中』token 誤用(台股會反轉成紅),把狀態 pill 與開關拆開,刪除加 confirm。
- 接出並修正既有 M1.4 能力:表單與 TS 型別補上 cron + respect_market_hours + 明確 timezone(修掉 cron 無時區會在 server 本地時間觸發的 bug),並提供『每根 K 收盤對齊』取代裸 wall-clock 秒數,讓 live 觸發語意與回測一致。

**投資人鏡頭 — 發現**

- **🔴 critical** — Schedule 層的執行失敗無告警:是否被通知完全取決於『錯在哪一層』。run_scheduled_workflow 只寫 RunLog、更新 last_status,從不呼叫 notify()。RiskGuard 違規(risk.py)與成交成功(execution.py)確實會 notify,但 data_source 抓取失敗、strategy/AI node 例外、'error: workflow missing'、或在 get_positions/get_ticker 階段的 broker 連線錯誤(都發生在 execute_order 的 success-notify 之前)全部靜默——RunResult.error 落進一筆無讀取端點的 RunLog,既無 in-app 通知也無 webhook。對無人值守 live 而言,這正好在沒人盯著的那一層違反 fail-loud。
  - 〔證據〕`backend/app/scheduler/service.py:53-87 全程無 notify();service.py:62 'error: workflow missing' 僅寫欄位;對照 app/trading/risk.py:117-174 與 execution.py:118 會 notify()`
- **🔴 critical** — 無持久化 jobstore,停機期間的 tick 被無聲丟棄。BackgroundScheduler() 用預設 in-memory MemoryJobStore;start_scheduler() 重啟時僅以 DB enabled 旗標 add_job 全新建立,無 next_run_time 持久化。process 重啟/崩潰期間『應該觸發的 tick』憑空消失——不寫 RunLog、不留痕跡;coalesce / misfire_grace_time 只能涵蓋 process 仍存活時的 misfire。一個每日再平衡 cron,若重啟橫跨 09:00,該次再平衡就直接無聲不發生。
  - 〔證據〕`backend/app/scheduler/service.py:45,126 BackgroundScheduler() 無 jobstores 參數;_restore_enabled_jobs (115-118) 僅以 enabled 重建`
- **🟠 high** — 『執行中』只反映 DB enabled 旗標,不代表 APScheduler job 真的掛載/存活。前端每 5s 輪詢 DB row,『執行中』pill 由 s.enabled 驅動;APScheduler 的 next_run_time / job-alive 狀態從未被讀取或外露。若 scheduler process 已掛或 job 掛載失敗,該列仍顯示『執行中』+ 舊 last_run_at,沒有任何 heartbeat 可偵測一個已死的 bot。
  - 〔證據〕`frontend/components/SchedulesPanel.tsx:108-112 pill 綁 s.enabled;service.py:84-86 last_status/last_run_at 僅在 job body 內賦值;job.next_run_time 從未外露`
- **🟠 high** — 無連續失敗的自動停機/升級。Schedule 無 failure_count 欄位;一個 broker 金鑰過期的 bot 每個 tick 都失敗、持續重試。交易層有 kill-switch 與 daily-loss halt,但排程層完全沒有『連續 N 次錯誤 → 自動 pause + 告警』。
  - 〔證據〕`backend/app/models.py:48-60 Schedule 無 failure_count;service.py:53-87 失敗後不 disable、下個 tick 照跑`
- **🟠 high** — cron 無時區 → 在錯誤的 wall-clock 時間觸發。CronTrigger.from_crontab(schedule.cron) 未帶 timezone,採用 APScheduler 預設(server 本地時區,tzlocal),且 Schedule 無 timezone 欄位。'0 9 * * *' 會在 server 的 09:00 觸發;在 UTC 主機上等於 Asia/Taipei 17:00,已過 13:30 收盤——日頻策略用錯誤時間成交。
  - 〔證據〕`backend/app/scheduler/service.py:93 CronTrigger.from_crontab 無 tz 參數;models.py:48-60 無 timezone 欄位`
- **🟡 medium** — interval 以 wall-clock 觸發,未對齊 bar 收盤。trigger='interval' 在 bar 內任意相位觸發,一個 60s live bot 會讀到尚在形成的 candle,且觸發時點相對 candle 邊界持續漂移,與回測引擎 bar-by-bar / next-bar-open 模型分歧,使 live 與回測訊號時點不可比。註:nodes.py:_run_order 的 target-position 語意(『已達目標即 no-op』)使同一根 bar 的重複 tick 不會重複下單,故這是訊號時點保真度問題,非 over-trading。
  - 〔證據〕`backend/app/scheduler/service.py:95 trigger='interval';nodes.py:191-196 target-position no-op;backtest/engine.py next-bar-open`
- **🟡 medium** — 多市場工作流只用第一個 data_source 判斷盤別。_market_for_graph 回傳第一個 data_source node 的 market;一個首節點為 crypto 但同時交易 us_stock/tw_stock 的工作流,會被當成『永遠開盤』而在股市休市時照樣下單。今日範圍窄(單市場工作流不受影響),但對 target state 要求的多市場情境是錯的。
  - 〔證據〕`backend/app/scheduler/service.py:36-39 迴圈遇第一個 data_source 即 return`
- **🟡 medium** — 執行 overrun 被無聲丟棄。max_instances=1(防重複正確)代表單次執行若超過 interval(例如 AI signal node 呼叫 Claude 較慢),後續 tick 被 APScheduler 直接丟棄且無外露——一個 60s bot 實際可能每 120s 才跑一次,operator 無從得知。
  - 〔證據〕`backend/app/scheduler/service.py:103 max_instances=1;無 EVENT_JOB_MAX_INSTANCES listener 或 RunLog 紀錄`

**設計鏡頭 — 發現**

- **🔴 critical** — 面板完全沒有 paper↔live 邊界訊號,而每個 enabled 排程都以全域 TRADING_MODE 下單。order node 不傳 mode,execute_order 從 settings.trading_mode 解析(registry.py:55)——把 TRADING_MODE 翻成 live,會讓『所有』正在跑的排程同時轉為真錢下單,但面板與 paper 長得一模一樣。DESIGN.md 明訂 live 必須有不容錯認的安全狀態(粉色 LIVE banner + 脈動指示);無人值守自動化正是信任成本最高、最不該省略的地方。
  - 〔證據〕`backend/app/workflow/nodes.py:198-203 execute_order 未傳 mode;brokers/registry.py:54-55 預設 settings.trading_mode;SchedulesPanel.tsx 無 live/paper 訊號;DESIGN.md:42-44`
- **🟠 high** — 狀態 pill 用價格 token,且觸發台股反轉 bug。enabled pill 用 bg-up/15 text-up——把『價格上漲』token 用於非價格狀態。DESIGN.md 規定 --up/--down 專屬價格,狀態應走 --warning/--error/--live/accent。setMarket() 會在 <html> 設 data-market='tw'(useMarket.ts)且在 SPA 導航間持續存在,因此看過台股標的後,一個健康的『執行中』bot 會渲染成紅色(讀起來像危險)。
  - 〔證據〕`frontend/components/SchedulesPanel.tsx:109 'bg-up/15 text-up';app/globals.css:36 [data-market='tw'] 把 --up 翻紅;lib/useMarket.ts:4`
- **🟠 high** — 後端 M1.4 能力在 UI 完全不可觸及。createSchedule 只送 {workflow_id, interval_seconds};表單只暴露 interval;Schedule 的 TS interface 連 cron / respect_market_hours 欄位都沒有,連讀回顯示都做不到。後端兩者皆已完整支援。
  - 〔證據〕`frontend/lib/api.ts createSchedule body 僅 {workflow_id, interval_seconds};api.ts Schedule interface 缺 cron/respect_market_hours;SchedulesPanel.tsx:52-84 表單;backend api/schedules.py:16-21`
- **🟠 high** — 看不到 next-run、看不到執行歷史、錯誤細節被藏。UI 只顯示 last_run_at + last_status 文字;APScheduler 已知的 next_run_time 從未由 API 外露,RunLog.detail(含 result.error 與逐節點 trace)根本沒有任何讀取端點——operator 既看不到下次何時觸發,也看不到為何失敗。
  - 〔證據〕`frontend/components/SchedulesPanel.tsx:115-120 僅渲染 last_run_at/last_status;service.py:82 寫 RunLog.detail;api/* 無 RunLog GET 端點`
- **🟡 medium** — 載入/錯誤狀態偽裝成空狀態。兩個 query 皆 retry:false 且無 isLoading/isError 分支;list query 失敗(auth 失效、後端掛掉)會落到『尚無排程』文案——把錯誤偽裝成『沒有資料』,違反 fail-loud。workflows 下拉同樣會在失敗時無聲變空。
  - 〔證據〕`frontend/components/SchedulesPanel.tsx:10-16 retry:false;130-132 fall-through 到 L.schedules.empty`
- **🟡 medium** — 狀態 pill 其實是偽裝的開關,且刪除無確認。點『執行中/已暫停』pill 會無聲翻轉一個(可能是 live 的)bot 開/關——一個被當成狀態指示器的控制項;remove() 直接呼叫 deleteSchedule 無 confirm。排程僅以 workflow 名稱(wfName)標示,同一工作流的兩個排程視覺上無法區分,誤暫停或誤刪錯誤的 live bot 只需一次點擊。
  - 〔證據〕`frontend/components/SchedulesPanel.tsx:106-113 pill onClick toggle;41-44 remove() 無 confirm;46,103 僅以 wfName 顯示`
- **🔵 low** — setInterval state setter 遮蔽全域同名函式;interval 以原始秒數輸入(min 5),框架本身誘導使用者設定與 data_source timeframe 脫鉤的 sub-bar 間隔。
  - 〔證據〕`frontend/components/SchedulesPanel.tsx:19 const [interval, setInterval];70-77 input min=5 秒`

**重設計提案**

把排程面板從「一張 admin 表」升級為「能安心放著 bot 跑的可信控制台」,資料模型 → reliability 後端 → trust UI 三層一起改。

一、資料與後端(可信賴的無人值守):
- Schedule 加欄位:timezone(cron 必填,預設 Asia/Taipei)、label(可選名稱以區分同工作流的多個排程)、consecutive_failures、paused_reason。target state 再加 mode 欄位以支援『同一台機器上 paper 與 live 排程並存』(今日 mode 是全域 settings.trading_mode,order node 不傳 mode──見 nodes.py:198-203 / registry.py:55──所以今日全部排程共用同一個 paper/live)。
- 換成持久化 SQLAlchemyJobStore(共用同一個 SQLite engine);啟動時比對 DB 與 jobstore,對停機期間超出 misfire_grace_time 的漏跑寫一筆 RunLog(status='missed', detail 記區間),補上『missed bars』可觀測性,並 notify。
- run_scheduled_workflow 在 RunResult.status=='error' 時呼叫 notify(level='error')──沿用既有 webhook,補上 risk/execution 沒覆蓋到的 data_source/strategy/broker-connectivity 失敗路徑;連續 N 次(預設 3)失敗自動 enabled=False + paused_reason + notify。對齊既有 RiskGuard / kill-switch 的 fail-loud 哲學。
- cron 一律帶 ZoneInfo(schedule.timezone);interval 增加『每根 K 收盤對齊』選項(run on candle close),消除讀到形成中 candle 的問題,讓 live 與回測 next-bar-open 語意一致。
- 註冊 EVENT_JOB_MAX_INSTANCES listener,把 overrun 寫成 RunLog(status='overrun');新增 GET /api/schedules/{id}/runs(讀該排程 RunLog 歷史含 error detail)並回傳 next_run_time。

二、UI(SchedulesPanel 重構)。整個面板頂部一條全域 mode banner(因為今日 mode 是全域):TRADING_MODE=live 時整塊走 --live 粉色脈動,paper 時走 --text-faint。每列是一張「bot 健康列」,左緣 3px 色條一眼分流;狀態色全部改走 status token(執行中=--accent dot,已暫停=--text-muted,休市跳過=--warning,錯誤/未掛載=--error),不再用 --up 綠色:

```
排程(自動執行)            ● LIVE — 所有啟用排程送出真實訂單   [＋ 新增排程]
┌──────────────────────────────────────────────────────────────────────┐
│ │ MA-Cross · BTC/USDT        cron 0 9 * * 1-5 (Asia/Taipei)            │
│ │ ▲執行中   下次 09:00:00 (3m)   上次 08:00 ✓ ok   [▮▮暫停][歷史][刪除…]│
├──────────────────────────────────────────────────────────────────────┤
│ │ RSI-Rev · 2330             每根 K 收盤 (1m)                          │
│ │ ⚠休市跳過 下次 —          上次 13:31 ⚠ skipped: market closed        │
├──────────────────────────────────────────────────────────────────────┤
│ │ MACD · AAPL               每 60s                                     │
│ │ ✕ 已停  連續 3 次失敗已自動暫停  上次 21:30 ✕ error: broker auth     │
│ │ ↳ 點開歷史看完整 error detail   [重新啟用][刪除…]                    │
└──────────────────────────────────────────────────────────────────────┘
```

- 新增/編輯改成 dialog:工作流、觸發方式(interval / 每根 K 收盤 / cron)、cron 時帶 timezone select(預設 Asia/Taipei)、respect_market_hours toggle、label、enabled。把後端 M1.4 完整接出來;同步補 Schedule TS interface 的 cron/respect_market_hours/timezone 欄位與 createSchedule body。
- 信任邊界遵守 DESIGN.md:TRADING_MODE=live 時面板頂 --live banner + 脈動(這是無人值守送真錢的最高風險動作);建立/啟用排程在 live 下跳粉色確認(『此排程將送出真實訂單』);把『執行中』pill 改成純狀態徽記,暫停/啟用改為明確獨立按鈕(不再讓狀態指示器兼任開關);刪除一律 confirm,live 文案更重。
- 健康三件套:下次觸發(next_run_time,相對時間 + tooltip 顯絕對時間)、job-alive 心跳(DB enabled 但 jobstore 無對應 job → 標 --error『排程未掛載』而非假裝執行中)、上次結果(skipped 用 --warning、error 用 --error 並可點開 RunLog 歷史抽屜看完整 trace)。
- 失敗/載入:query 加 isLoading skeleton 與 isError 明示『無法載入排程(後端/授權)』,不可再 fall-through 成『尚無排程』。
- 數字全部 .num tabular(間隔、倒數、時間);cyan 僅用於『執行中』這個 automation 狀態與 AI 節點,符合 accent 專屬規則。

<br>

### D8. 通知 Notifications

**現況:** 通知是一條被動、每 5 秒輪詢、藏在「工具」第二層的 read-only 流水帳:portfolio 級風控閘門(kill switch/halt/日損/曝險)確實會 notify,但最致命的無人值守失敗(scheduler 崩潰、broker/data_source 例外、per-order RiskGuard 拒單)完全不發通知,單一 webhook 又是同步阻塞在交易執行緒上、失敗還被靜默吞掉——對 live bot 等於沒有可靠的 lifeline。

**評分:** 投資人 `2/5` · 設計 `2/5`　|　**判決: `Rework`**

**最高槓桿動作:**
- 讓無人值守的失敗會『叫醒人』:替 scheduler 失敗分支(scheduler/service.py:84)、workflow node 失敗(engine.py:88-96)、per-order RiskGuard 拒單(risk.py:33-50)、broker/data_source 例外補上 notify(level=error, category);並把 webhook 投遞失敗(service.py:42-44)從靜默改成 fail-loud 回寫一筆 system 通知。
- 把投遞做成可靠通道:將同步阻塞的 httpx.post(service.py:36)移出交易/scheduler 執行緒(避免慢 webhook 觸發 max_instances=1 排程 misfire),單一 NOTIFY_WEBHOOK_URL 升級為可路由 channels(Telegram/LINE/email/Slack/webhook),error 與 live 來源走高保證通道並支援退避重試。
- 前端做成 Alert Center:TopBar.tsx 全域鈴鐺 + 未讀徽章、/notifications 分級 filter + read/unread + paper/LIVE 標籤 + 跳轉來源 + 完整日期戳;同步修正 NotificationsPanel.tsx:7-12 的 token 誤用(success 勿用會在台股翻紅的 --up、info 勿用 off-palette 的 bg-sky-400),並新增缺漏的 --success status token。

**投資人鏡頭 — 發現**

- **🔴 critical** — 無人值守的 scheduler 失敗完全不發通知,這是 live bot 最致命的破口。run_scheduled_workflow 在工作流出錯時只把 schedule.last_status 寫成 "error: {error}" 並寫一筆 RunLog 後 commit;整個 scheduler/service.py 連 notify 都沒 import。一個跑真錢的背景策略 node 崩潰、data_source 抓不到資料、或 broker 拋錯,使用者收不到任何 in-app 或外部警示,只能自己去開『排程』頁面、看 last_status 字串才會發現。對標 3Commas / Composer『機器人停了會主動叫醒你』的最低標準,這裡是 0 分。注意 workflow engine 本身(engine.py:88-96)也只回傳 RunResult(error) 不 notify,所以連手動跑失敗也不留通知,只是手動情境會在 HTTP 回應看到——unattended 才是 critical。
  - 〔證據〕`backend/app/scheduler/service.py:84 僅 schedule.last_status = f"error: {result.error}";該檔 import 區無 notify;對照 engine.py:88-96 node 失敗只回 RunResult(status="error") 不 notify`
- **🟠 high** — 唯一的外部投遞通道是同步阻塞、且失敗被靜默吞掉,雙重違反 fail-loud。dispatch_webhook 用 httpx.post(timeout=5.0) 同步呼叫,直接掛在 notify() → execute_order 的執行緒上;在 scheduled run(max_instances=1)裡,每筆 fill 都會阻塞該 job 執行緒最多 5 秒,多個 order node 累加可能拖過 misfire_grace_time=30 而導致下一個 tick misfire——一個慢掉的 webhook 能連鎖造成漏跑排程。更糟的是 except Exception: return False 把 4xx/逾時/網路錯全吃掉,notify() 又丟棄這個回傳值,所以『webhook 沒送出去』不會被記成任何 in-app 通知,也無重試、無 dead-letter:使用者以為有外部告警,實際可能整天靜默失敗。
  - 〔證據〕`backend/app/notifications/service.py:36-44 同步 httpx.post(timeout=5.0)、except 吞錯 return False;service.py:55 notify() 丟棄 dispatch 回傳值;execute_order(execution.py:118)在交易執行緒同步呼叫;scheduler add_job max_instances=1 + misfire_grace_time=30(service.py:104)`
- **🟠 high** — 只有單一 NOTIFY_WEBHOOK_URL、無 severity routing、無 push/email/LINE/Telegram。對一個跑真錢、使用者群是台灣零售/quant 的平台,LINE/Telegram 才是真正會被看到的通道;現況只有一個泛用 webhook POST。error/live 等級的關鍵警示(日損熔斷、kill-switch 觸發)與一般成交走同一條盡力而為的管線、同樣可能靜默失敗,無法保證『最關鍵的事件一定送達』。
  - 〔證據〕`backend/app/notifications/service.py:32 url = settings.notify_webhook_url(單一);config.py notify_webhook_url: str = "";.env.example NOTIFY_WEBHOOK_URL=(單一 URL)`
- **🟡 medium** — per-order RiskGuard 拒單在通知 feed 裡是不一致地靜默。PortfolioGuard.check 的每一條閘門(kill switch / halt / 日損 / 單日筆數 / 曝險)都會 notify(且因 notify 先 commit、再 raise,通知能在 rollback 後存活),但更前面的 RiskGuard.check(單筆 order value 超限、持倉市值超限、非正價格)只 raise RiskError、不 notify。代表『某筆下單被風控擋下』在 scheduled/workflow 情境下完全不留痕跡(手動下單才會經 HTTP 回應看到例外)。capital-safety 路徑上兩個風控層的告警語意不一致,是真實的設計缺口。
  - 〔證據〕`backend/app/trading/risk.py:33-50 RiskGuard.check 只 raise RiskError;對照同檔 PortfolioGuard.check risk.py:117-183 每個 gate 都先 notify 再 raise`
- **🟡 medium** — 沒有去重 / rate-limit,通知會被洗版且舊紀錄不可回溯。每筆 fill(execution.py:118-124)無條件 notify(level=success),一個高頻或抖動的策略會同時灌爆 in-app feed 與 webhook;而 list 端點預設只回 20 筆、上限 100、無 cursor 分頁,超過就永遠看不到,關鍵 error 很容易被一串 success 擠出視窗。對 live 平台,通知 feed 同時也是 audit trail,只能看最後 20 筆是嚴重不足。
  - 〔證據〕`backend/app/trading/execution.py:118-124 每筆 fill 無節流 notify;backend/app/api/notifications.py:15-21 limit 預設 20、上限 100、order_by id desc、無 cursor/level filter`
- **🟡 medium** — 通知沒有 read/ack/escalation 生命週期。Notification 資料表只有 level/title/message/meta/created_at,沒有 read、acknowledged、category、source、mode 欄位。一筆『日損熔斷—已 halt』(risk.py:142, level=error)和一筆 info 的生命週期完全相同——沒人看也不會升級、不會重送、不會標記未處理,無法支撐『未確認的 critical 警示要持續糾纏使用者』的 alert center 行為。
  - 〔證據〕`backend/app/models.py:63-69 Notification 僅 id/level/title/message/meta/created_at`
- **🔵 low** — production UI 的『測試』按鈕把測試通知寫進與真實警示同一條 feed,且無法區分。NotificationsPanel 的 test 按鈕呼叫 POST /api/notifications/test,寫一筆真正的 Notification row;由於沒有 category/source 欄位,測試噪音與真實成交/風控告警混在同一審計流裡無法過濾。對嚴肅平台,測試事件汙染 audit trail 是個小但真實的整潔問題。
  - 〔證據〕`frontend/components/NotificationsPanel.tsx:23-26 test()→api.testNotification();backend/app/api/notifications.py:24-26 test_notification 寫入正式 Notification 表;model 無 category 可分流`

**設計鏡頭 — 發現**

- **🟠 high** — 通知被埋在『工具』選單第二層,且全 App 沒有任何全域未讀提示,違背 refined-terminal 的 fail-loud 精神。TopBar 目前只有 ThemeToggle + 文件中心連結——沒有 bell、沒有計數、沒有色點。一筆 kill-switch 觸發或日損熔斷(level=error)可以在你停留在『市場』或『投組』頁時靜靜寫進 DB,而你不會看到任何提示;NotificationsPanel 也只掛在 /notifications 頁,無全域 mount。DESIGN.md 把 live/danger 訊號定位在 nav 與 top bar(live leaf 用 --live dot),通知這條 lifeline 卻完全缺席於全域 chrome。
  - 〔證據〕`frontend/components/shell/TopBar.tsx:19-27 ml-auto 區僅 ThemeToggle + /docs Link,無 bell;frontend/lib/nav.ts:38 通知為『工具』children(Bell icon、無 badge);NotificationsPanel 僅見於 app/(rooms)/notifications/page.tsx`
- **🟠 high** — color token 誤用會在台股情境把『成功』顯示成紅色,並夾帶 off-palette 硬編碼。success 用 bg-up、info 用硬寫的 bg-sky-400。DESIGN.md 明定 status 要與 price 分離,而 --up 是會隨市場翻轉的『價格』token——在 data-market="tw" 下 --up 變紅(#F05252),於是一筆『下單成功』通知渲染成紅色(語意相反);sky-400 完全不在色票內,違反『CSS 變數是契約、never hardcode』。更尖銳的是:DESIGN.md 本身有內部矛盾——line 77 寫 info = accent,但 line 73 把 accent 保留給 AI/automation only,所以 info 既不該用 sky-400 也不該無條件用 cyan,這個矛盾必須在 redesign 一併釐清。
  - 〔證據〕`frontend/components/NotificationsPanel.tsx:7-12 DOT = { info: bg-sky-400, success: bg-up, warning: bg-warning, error: bg-error };DESIGN.md:73 accent AI-only vs DESIGN.md:77 info = accent 矛盾`
- **🟠 high** — 通知完全不區分 paper 與 LIVE,正好在最該標的地方破壞 paper↔live 信任邊界。execution.py:123 已把 result.mode 放進 meta,但 panel 只渲染 dot/title/message/time,使用者無法從一筆『Order filled: buy 0.5 BTC』看出這是模擬還是真錢成交。DESIGN.md 要求 LIVE 必須以 --live 不可誤認地標示(banner、btn-live、portfolio chip),通知這條真錢成交記錄卻完全不標 mode。
  - 〔證據〕`frontend/components/NotificationsPanel.tsx:44-54 列僅 dot+title+message+toLocaleTimeString,未讀 n.meta.mode;對照 execution.py:123 meta=result.model_dump(mode="json") 已含 mode`
- **🟡 medium** — 被動 5 秒輪詢的扁平清單,缺 read/unread、分級 filter、跳轉來源、與 load-more。listNotifications 不帶任何參數,後端 desc 取 20 筆;沒有 level/category filter(後端也沒提供)、沒有點擊成交通知跳到該訂單/投組或點風控告警跳到風險頁、沒有 load-more,超過 20 筆的歷史就消失。距離一個真正的 alert center(可篩選、可標記、可追溯)還很遠,只是 read-only 流水帳。
  - 〔證據〕`frontend/lib/api.ts:450 listNotifications: () => request("/api/notifications") 無 query;backend/app/api/notifications.py:15-21 僅 limit;NotificationsPanel 無 onClick 導航`
- **🟡 medium** — 時間戳只有時:分:秒(toLocaleTimeString),超過 24 小時即無法判讀;title 與 message 同時 truncate 且無展開,關鍵細節(例如熔斷的數字)被切掉。對 tabular、密集的終端機審計需求,缺日期 + 缺展開是實質可用性缺口;且後端 created_at 為 UTC,若序列化未帶 tz 後綴,new Date() 在瀏覽器可能誤判為 local time。
  - 〔證據〕`frontend/components/NotificationsPanel.tsx:48-53 title 與 message 皆 truncate、時間用 new Date(n.created_at).toLocaleTimeString()(無日期、無 relative time);models.py:11 created_at = datetime.now(timezone.utc)`
- **🔵 low** — 沒有 loading 骨架,且缺 a11y live region。三元判斷只有 isError / data&&length>0 / else——首次載入 data 為 undefined 時直接落到 empty state『尚無通知』閃一下;清單也沒有 role="status" / aria-live,螢幕報讀者在一筆 critical 警示進來時完全不會被通知,牴觸『lifeline 必達』。
  - 〔證據〕`frontend/components/NotificationsPanel.tsx:40-59 三元僅 isError/有資料/空,無 isLoading 分支與 aria-live 容器`

**重設計提案**

把「被動清單」升級成「Alert Center」,分前端 IA、後端模型、投遞三層,全部對齊 DESIGN.md 的 refined-terminal 與色彩紀律。\n\n一、全域層:top bar 鈴鐺 + 未讀徽章(補上目前 TopBar.tsx:19-27 缺席的 lifeline)\n- 在既有 ml-auto 區(ThemeToggle 左側)放一顆 Bell;右上角掛未讀計數。徽章顏色取「目前未讀中最高 severity」:有 error → --error,有 live 來源 → --live,否則 --warning;純 info/success 不亮(避免徽章疲勞)。\n- 動效紀律:DESIGN.md 規定 pulse 是『唯一刻意的動畫,專屬 LIVE indicator』。因此只有在『有 live 來源的未讀 critical』時才讓 bell 沿用該 pulse 規則,其餘一律靜態徽章,不擴張動效。\n- 點 bell 開右側 slide-over 快覽最近 20 筆;頁尾「查看全部」進 /notifications。nav.ts:38 的「通知」leaf 同步顯示未讀數。\n\n二、/notifications:完整 Alert Center(取代 NotificationsPanel 扁平 ul)\n- 頂部 filter tabs:全部 / 風險 Risk / 成交 Fills / 系統 System(以新 category 欄位分流),右側 level 多選 chip + 「僅未讀」toggle。\n- 每列:severity 點(用 status token,絕不用 price token)→ 標題 → 一個 mode 標籤(paper 用 --text-muted 邊框 outline,LIVE 用 --live 實心,直接落地 paper↔live 邊界)→ 來源/分類 → 完整日期+時間(.num / tabular-nums)。整列點擊展開 message + meta(JSON,JetBrains Mono),並提供「跳到來源」(成交→該訂單/投組,風控→風險頁)。\n- read/unread 視覺:cyan 是 AI 專屬不可挪用——未讀=左緣 2px --border-strong + 較亮 --text,已讀=降為 --text-muted。批次「全部標為已讀」「清除」。\n\n色彩修正(取代 NotificationsPanel.tsx:7-12,並順手修 DESIGN.md 的 info=accent 矛盾):\n  info → --text-muted(中性)。不可用 sky-400(off-palette),也不該無條件用 cyan(AI 專屬);唯一例外:category=ai 的 AI 來源通知可用 --accent,其餘 info 中性化。建議同步修 DESIGN.md『info = accent』那行為『info = --text-muted;AI 來源才用 --accent』。\n  success → 新增一個 status 級 --success token(DESIGN.md 目前根本沒有 success token);務必『不要』用 --up,因為 --up 在 data-market=\"tw\" 會翻紅、使成功通知變紅。\n  warning → --warning,error → --error,live 來源額外帶 --live 標籤。\n\nASCII(Alert Center 一列 + top bar 鈴鐺):\n```\n top bar:  …            ( 🔔 3 )  [◑ theme]  [文件中心 ↗]\n                          └ 徽章色=最高未讀severity;pulse 僅在有 live 來源 critical 未讀\n\n ┌ 通知 / Alert Center ───────────────────────────────────────────┐\n │ [全部][風險][成交][系統]      level: ●info ●warn ●err  ☐僅未讀  │\n ├────────────────────────────────────────────────────────────────┤\n │ ● 日損熔斷 — 已暫停交易        〔LIVE〕風控  2026-06-27 14:02:11 │  ← --error 點 + --live 實心標\n │   daily loss 124,300 TWD 超過 max_daily_loss 100,000 …  ▸展開   │\n │ ● 成交 buy 0.50 BTC @ 64,210  〔paper〕成交 2026-06-27 13:58:04 │  ← --success 點, paper outline 標\n │ ○ Webhook 投遞失敗 (timeout)  〔system〕系統 2026-06-27 13:58:05 │  ← 投遞失敗也記成一筆(fail-loud)\n └────────────────────────────────────────────────────────────────┘\n   ○=已讀 ●=未讀;每列可點擊跳到來源\n```\n\n三、後端模型 + 投遞(支撐上面,且不破壞交易路徑)\n- Notification 加欄位:read: bool、category(risk/fill/system/ai)、source(order_id / schedule_id / node_id)、mode(paper/live)。\n- API 補:GET 支援 ?level=&category=&unread=&cursor=、GET /unread_count、POST /{id}/read、POST /read_all。\n- 事件覆蓋補洞(investor 視角的 critical):scheduler/service.py:84 失敗分支、engine.py:88-96 node 失敗、RiskGuard.check 每筆拒單、broker/data_source 例外,全部接 notify(level=error, category=...)。\n- 投遞層去阻塞 + fail-loud:把同步 httpx.post 移出交易/scheduler 執行緒(改用 background job / 佇列 fire-and-forget),避免慢 webhook 拖累 max_instances=1 的排程造成 misfire;單一 webhook 升級為 channels 設定(webhook / Slack / Telegram / LINE / email),依 severity routing(error+live 必經高保證通道並支援退避重試);dispatch 失敗時『不再靜默』——回寫一筆 category=system 的 in-app 通知。\n\n此設計不改 DESIGN.md 既定的兩房 IA,只補上一個 status 色與一處 info 色澄清,把『被動 feed』補成符合 fail-loud 與 paper↔live 紀律的 alert center。

<br>

### D9. 匯入 Data Import + market-data infra

**現況:** 台股/美股 的資料層仍是「貼 CSV → 存進 process-local dict → 重啟即清空」的 demo:沒有 timeframe 維度、沒有 OHLC 清洗、沒有 corporate-action、ticker 是凍結的最後一根 bar、沒有真實 vendor —— 撐不起拿真錢的多市場平台(crypto 走 ccxt 的路徑反而是唯一真實且 API 失敗語意乾淨的部分)。

**評分:** 投資人 `2/5` · 設計 `2/5`　|　**判決: `Rework`**

**最高槓桿動作:**
- 把 process-local `_store` 換成持久化、以 (market, symbol, timeframe) 為複合鍵的 DB-backed OHLCV store,並讓 CsvDataBroker 真正依 timeframe 過濾、ImportRequest 補上 timeframe 欄位 —— 一次消滅『重啟即清空』與『日線當小時線回測、Sharpe 高估約 4.9 倍』兩個地基級問題(market_data.py:15 / api/markets.py:17-20 / csv_data.py:48-62 / engine.py:174,187-189)。
- 建立 parse→validate→commit 資料品質管線:OHLC 健全性 + 去重 + 缺口偵測 + timeframe 推斷比對 + 統一 tz 正規化(順手修 sort 與 get_ohlcv_range 的 naive/aware TypeError),並把 validation report 回傳前端做 commit 前預覽 —— 把 fail-loud 從 workflow engine 延伸到資料層。
- 前端從『盲貼 textarea』升級為資料來源管理室:消費既有 GET /api/markets/imported 顯示資料集清單(期間/筆數/來源/易失狀態)+ 檔案上傳 + 缺口/刪除 Inspector;同時修色彩紀律(移除 bg-accent CTA、停止用 --up 當狀態色)、補上『資料易失』警示。

**投資人鏡頭 — 發現**

- **🔴 critical** — 匯入的台股/美股歷史完全不持久化,且靜默遺失。所有資料只存在模組級 `_store: dict[tuple[MarketKind, str], list[Candle]]`,每次 restart/redeploy 全部清空;market_data.py 的 docstring 自己承認『Process-local (cleared on restart)』。專案用 SQLite 存 workflows/orders/strategies,卻獨獨不把 OHLCV 落地。對 serious 平台,這代表使用者貼進去的全部資料在下一次部署後無聲消失,而 registry 整個 stock 資料路徑都靠 `has_market_data()` 判斷記憶體有無資料 —— 重啟後 stock 市場直接回到 NotImplementedError。
  - 〔證據〕`backend/app/brokers/market_data.py:15 模組級 `_store`;:1-4 docstring 自承 cleared on restart;registry.py:31-38 get_data_broker 依 `market_data.has_market_data(market)` 決定 CsvDataBroker vs NotImplementedError。`
- **🔴 critical** — 資料與其聲稱的頻率完全脫鉤 —— 直接的 statistical-honesty 破口。`_store` 以 (market, symbol) 為 key、且 ImportRequest 根本沒有 timeframe 欄位,所以匯入資料沒有任何頻率標記;CsvDataBroker.get_ohlcv/get_ohlcv_range 收到 `timeframe` 卻完全不用,直接回傳整段資料。但回測引擎用『回測請求填的 timeframe』經 `periods_per_year()` 年化 Sharpe/Sortino/vol(1h→8766、1d→365.25)。使用者匯入日線、回測卻填 1h,系統不報錯,Sharpe/Sortino/年化波動被高估 √(8766/365.25)=√24≈4.9 倍;指標窗(RSI14、MA window)以 bar 數計也跟著 silently 錯位。此 bug 僅存在於 CSV 路徑(crypto 經 ccxt 以正確 timeframe 抓資料,不受影響),但對目標的多市場 live 平台是核心地基破洞。
  - 〔證據〕`market_data.py:15(key 無 timeframe)+ api/markets.py:17-20 ImportRequest 無 timeframe 欄位;csv_data.py:48-49 與 51-62 收 `timeframe` 但不使用;backtest/engine.py:174 `ppy = metrics.periods_per_year(timeframe)`、:187-189 sharpe/sortino/vol 以 ppy 年化;metrics.py:23-35 periods_per_year。`
- **🟠 high** — 完全沒有 OHLC 健全性檢查、去重、缺口偵測。parse_csv 只驗『required 欄位存在』與『可轉 float』,不檢查 high≥low、high≥max(open,close)、low≤min(open,close)、price>0、NaN/Inf;對重複 timestamp 不去重(只 sort);對缺漏 bar / 非交易日跳空不報告。Garbage-in 直接餵進回測引擎,結果失真而使用者毫無所覺,違反平台『fail loud』鐵律(該鐵律目前只落實在 workflow engine / RiskGuard,沒延伸到資料層)。
  - 〔證據〕`market_data.py:34-63 parse_csv 僅 required 欄位檢查(:39-42)+ float() 轉型(:51-55);:62 `candles.sort(...)` 後直接回傳,無 dedup / OHLC 驗證 / gap 檢查。`
- **🟠 high** — 無 corporate-action(分割/股利)調整,也無 survivorship 處理。Candle schema 只有 raw OHLCV、沒有 adj_close / split / dividend 欄位;匯入路徑亦無任何調整或 point-in-time universe 概念。台股/美股原始收盤遇 2:1 split 會呈現 -50% 假崩盤、除息日呈現假跳空,污染策略訊號;且只能匯入『現在還活著』的代號,delisted 標的無法納入 → 回測天生 survivorship bias。這是對標 QuantConnect/Bloomberg 的 table-stakes,目前為零。
  - 〔證據〕`schemas.py:43-49 Candle 僅 open/high/low/close/volume;api/markets.py:17-31 import 路徑無 adjustment / universe 概念。`
- **🟠 high** — paper『現價』是凍結的最後一根 bar —— paper↔live 信任邊界破洞。台股/美股 paper 交易經 PaperBroker(data_provider=CsvDataBroker) 取價,CsvDataBroker.get_ticker 永遠回傳最後一根匯入 K 線的 close。意即匯入到 2024-12-30 後,『現價』永遠是該日收盤,之後每筆 paper 單都成交在同一個死掉的靜態價,未實現損益幾乎不動(僅扣成本)。使用者以為在做接近真實的 forward paper trading,實際是對一張快照下單,paper 模擬形同失效。DESIGN.md 把 paper/live 安全狀態列為一級設計關注,此處的信任落差未被任何 UI 標示。
  - 〔證據〕`csv_data.py:44-46 get_ticker 回 `self._candles(symbol)[-1].close`;registry.py:56-62 paper 模式以 get_data_broker(=CsvDataBroker for stocks) 當 data_provider。`
- **🟠 high** — 無真實資料 vendor,資料供給全壓在人工貼 CSV —— 不可規模化。年級日線數千列、intraday 數十萬列靠 textarea 貼上不可行;台股/美股 live broker(YuantaBroker/FirstradeBroker)每個資料/交易方法皆 raise NotImplementedError,連『拉資料』都沒有。一個 serious 多市場平台需要 vendor 串接(台股 FinMind/TWSE/TEJ;美股 Polygon/Alpha Vantage/IEX/Yahoo),這是台股/美股從 scaffold 走向真實的前提。
  - 〔證據〕`frontend/components/DataImportPanel.tsx:63-69 唯一輸入是 `<textarea rows={5}>`;backend/app/brokers/yuanta.py:43-56 與 firstrade.py:37-50 所有方法 raise NotImplementedError(_NOT_WIRED)。`
- **🟡 medium** — 混合 timestamp 格式不是乾淨 fail-loud,而是 opaque 500。_parse_timestamp 對 ISO 裸日期『2024-01-01』回 tz-naive,對 epoch 回 tz-aware(UTC);同一份 CSV(或 ISO 帶 tz 與裸日期混用)會讓 `candles.sort(key=...)` 因 naive vs aware 不可比較拋 TypeError。該 sort 在 row-level try/except 之外,而 import_history 只 catch ValueError → TypeError 逸出 → FastAPI 回 500 Internal Server Error,而非文件聲稱的 422 fail-loud。使用者拿到不可解的 500,且暴露資料正規化未統一。
  - 〔證據〕`market_data.py:18-31 _parse_timestamp 兩分支 tzinfo 不一致;:62 sort 在迴圈 try/except(:47-59)之外;api/markets.py:26-29 只 `except ValueError`。`
- **🟡 medium** — (第一版漏掉)get_ohlcv_range 的 tz 正規化只對 tz-naive 儲存資料有效,epoch 匯入資料的『日期區間回測』會 TypeError。csv_data.py:60-61 把 start/end 強制轉 tz-naive,假設儲存的 candle 都是 tz-naive(來自 ISO 裸日期)。但若使用者匯入 epoch 時間戳(parse 後是 tz-aware UTC),`_start <= c.timestamp` 變成 naive 比 aware → TypeError,整個 range backtest 直接炸。等於『用日期區間回測 epoch 匯入的資料』這條常見路徑有 latent 崩潰。
  - 〔證據〕`market_data.py:29 epoch 分支回 tz-aware;csv_data.py:60-62 將 start/end 轉 naive 後與儲存 candle 直接比較。`
- **🟡 medium** — 再次匯入同一 (market, symbol) 靜默整段覆蓋,且無法刪除單一資料集。set_candles 直接 `_store[(market,symbol)] = candles`,無 append/merge/增量/版本/稽核;想補一段新資料反而洗掉舊資料。雪上加霜:API 沒有任何 DELETE 端點,market_data 只有全域 clear(),所以打錯 symbol/market 後既不能移除單一資料集、也不能清掉壞資料(除非重啟 process —— 但那會連帶清空全部)。
  - 〔證據〕`market_data.py:66-67 set_candles 直接覆蓋;:82-83 只有全域 clear();api/markets.py 無 DELETE 端點。`
- **🔵 low** — volume 缺漏被靜默補 0。沒有 volume 欄位或空值時 volume=0.0,與真實的 0 量無法區分,違反 fail-loud。影響範圍有限(內建 ma_cross/rsi/macd/bollinger 皆不吃量),但帶量突破/OBV 之類自訂或 AI 策略會拿到全 0 量而得無聲錯誤訊號。
  - 〔證據〕`market_data.py:55 `volume=float(norm.get("volume") or 0.0)`;CSV header 註記 volume 為 optional(`[,volume]`)但缺值未告警。`

**設計鏡頭 — 發現**

- **🟠 high** — 盲貼、無 preview / 無解析回饋 —— 對『資料是回測地基』的平台是 table-stakes 缺口。使用者貼上後只拿到 `已匯入 N 根` 一句話,看不到解析後表格預覽、偵測到的日期區間、推斷的 timeframe、欄位對應、被拒/被修的列。匯入前的 validation report 完全沒有。
  - 〔證據〕`DataImportPanel.tsx:18-27 importCsv 只把 `res.imported` 拼進訊息;api/markets.py:31 只回 `{market, symbol, imported}`。`
- **🟠 high** — 沒有任何『已匯入資料』的管理面,後端能力被閒置。GET /api/markets/imported 已存在能列出已匯入 symbols,前端卻從未呼叫(lib/api.ts 只有 importHistory,無 listImported)。使用者無法得知手上有哪些資料集、各涵蓋哪段期間、幾根 bar、何時匯入、是否易失,更無法刪除/更新單一資料集 —— 匯入是『寫入黑洞』,而資料正是回測可信度的地基。
  - 〔證據〕`api/markets.py:34-36 list_imported 端點無前端消費者;lib/api.ts:452-456 只有 importHistory;DataImportPanel.tsx 全元件無清單區塊。`
- **🟠 high** — 完全不暴露『資料易失』的真相,違反 fail-loud / 信任。面板文案說『可在此貼上 OHLCV CSV,即可離線回測與紙上交易』,卻不警告重啟即清空(連 market_data.py docstring 都承認 cleared on restart)。使用者貼完看到綠色成功、隔天回來資料不見、stock 市場回到 NotImplementedError —— 對拿真錢的人是嚴重信任傷害。
  - 〔證據〕`DataImportPanel.tsx:31-34 說明文字無任何 persistence/volatility 警示;對應 market_data.py:1-4 + :15 in-memory store。`
- **🟡 medium** — 匯入主 CTA 用 `bg-accent`(electric cyan)—— 違反 DESIGN.md『--accent 只保留給 AI/automation』的鐵律。匯入 CSV 不是 AI 行為,卻搶用了平台最稀缺、最具語意的顏色,稀釋『青色=AI 在運作』的識別力。應改為中性 strong button(--border-strong 邊框 + surface 底 + --text label),把 cyan 留給 AI。
  - 〔證據〕`DataImportPanel.tsx:53 『匯入』按鈕 `bg-accent ... text-bg`;DESIGN.md:73-75 + :257-259 明文 accent AI-only。`
- **🟡 medium** — 只有 textarea 貼上,無檔案上傳/拖放,且 POST 期間零回饋。瀏覽器原生 file upload 近乎零成本,卻只給 rows=5 的貼上框;真實資料集貼不進去。importCsv 期間按鈕無 loading/disabled,大段貼上時使用者不知有沒有在跑。
  - 〔證據〕`DataImportPanel.tsx:63-69 唯一輸入 `<textarea rows={5}>`;:18-27 importCsv 無 loading state、:53 按鈕無 disabled。`
- **🟡 medium** — 整個 domain 只是 data-import/page.tsx render 的一張裸面板,缺一個真正的資料管理室。注意:DESIGN.md:144 是『刻意』把『匯入』放在 工具 之下的 leaf,而 :211 的『資料 Data』是 workflow canvas 的節點分類(不同概念)—— 所以這不是 DESIGN.md 違規,而是現況面板對一個 serious 多市場平台的資料層太單薄;把它升級為一級『資料來源室』屬於需使用者核准的 nav 偏離,不能擅自重排。
  - 〔證據〕`frontend/app/(rooms)/data-import/page.tsx:1-5 整頁只 render `<DataImportPanel/>`;DESIGN.md:144(匯入=工具 leaf)vs :211(資料=node category)。`
- **🔵 low** — 成功訊息誤用 `text-up`(漲跌方向 token)當 UI 狀態色。DESIGN.md 規定 up/down 只驅動價格方向且台股反轉(red=up);把『匯入成功』染成 --up,等於把『價格上漲』與『操作成功』混為一談,在 `data-market="tw"` 下還會變紅,語意更亂。狀態色應走中性(--text-muted)或問題用 --warning,不應挪用 price token。
  - 〔證據〕`DataImportPanel.tsx:70 `{msg && <p className="... text-up">}`;DESIGN.md:95-105 up/down 僅供 price、:76-77 status 與 price 分離(--warning/--error/info=accent)。`

**重設計提案**

把『貼 CSV』升級為一個真正的「資料來源室」,底層換成持久化、帶 timeframe 維度、且帶品質驗證的 OHLCV store。三層同步重做,顏色嚴守 DESIGN.md。

1) 後端(Rework storage,保留 Broker seam)
- 新增 SQLite 表 `ohlcv_bar`(market, symbol, timeframe, ts, open, high, low, close, volume, adj_close, source),以 (market, symbol, timeframe) 複合鍵 + ts;`_store` 退場。CsvDataBroker 改讀 DB 並『真正依 timeframe 過濾』—— 同時修掉 csv_data.py:48-62 忽略 timeframe 與 metrics 年化脫鉤的 statistical-honesty 破口。
- ImportRequest 補上必填 `timeframe`(目前完全沒有),讓資料自帶頻率標記。
- parse→validate→stage→commit 四段式:驗 OHLC 健全性(high≥low、high≥max(open,close)、low≤min(open,close)、price>0、無 NaN/Inf)、去重(同 ts 報衝突或取最後)、缺口偵測(對齊 timeframe 推算缺漏 bar)、推斷實際 timeframe 與宣告值比對不符就 fail-loud。統一 timestamp 正規化(全 tz-aware UTC),一併修掉 market_data.py:62 與 csv_data.py:60-62 的 naive/aware 比較 TypeError。
- 補 DELETE 端點與 corporate-action:Candle 增 adj_close,回測可切 raw/adjusted。
- vendor adapter 介面對齊既有 Broker seam(台股 FinMind/TWSE、美股 Polygon/AlphaVantage/Yahoo),讓貼 CSV 只是眾多 source 之一。

2) 驗證回饋(commit 前可見):import 回傳 validation report(列數、被拒列、偵測 timeframe、日期區間、缺口數、OHLC 違規數),前端先預覽再確認。

3) 前端「資料來源」室(消費既有 GET /api/markets/imported,需使用者核准的 nav 偏離)。顏色紀律:此 domain 無 AI,cyan 不出現;資料節點維持 --c-data 灰系(DESIGN.md:211);CTA 改中性 strong button(非 bg-accent);問題用 --warning,成功用中性 --text-muted,price token --up/--down 絕不挪用為狀態色;TODAY 明確標示『此資料目前存於記憶體,重啟即清空』,落地 DB 後改標示覆蓋率/來源/是否還原。

```
工具 ▸ 資料來源                                      [＋ 新增來源]
⚠ 目前資料儲存於記憶體,服務重啟即清空(--warning 條)
┌───────────────── 已匯入資料集 ─────────────────────────────┐
│ MARKET  SYMBOL  TF   BARS    RANGE               ADJ  SRC  │ (mono, tabular-nums)
│ tw      2330    1d   2,418   2015-01-02→2024-12-30  ✓  csv │
│ tw      2330    1h     —     —  ⚠ 宣告 1h 但偵測為 1d        │ ← --warning
│ us      AAPL    1d   1,006   2021-01-04→2024-12-31  ✓  poly│
│ us      TSLA    1d     503   2023-01-03→2024-12-29  ✗  csv │ ← ✗=未還原 split
└───────────────────────────────────────────────────────────┘
  選取列 → Inspector:覆蓋率/缺口 12 處 · 重複 0 · OHLC 違規 0
           [檢視缺口] [重新拉取] [刪除]   (刪除 label 用 --down)

┌──────────────── 新增來源 ────────────────┐
│ 來源:( ◉ 上傳CSV   ○ 貼上   ○ Vendor )   │
│ market[台股▾] symbol[2330] tf[1d▾]←必填  │
│ [⤓ 拖放 .csv 或點擊上傳]                  │
│ ── 解析預覽(commit 前)──────────────── │
│  2,418 列 · 偵測 1d ✓ 符合宣告 · 2015→2024│
│  ⚠ 3 列 high<low 已拒 · 1 組重複 ts       │ ← --warning,非 --up
│              [取消]   [確認匯入]           │ ← 中性 strong,非 bg-accent
└──────────────────────────────────────────┘
```

**本域新功能提案**

- **持久化 + 帶 timeframe 的 OHLCV store(DB-backed)** `(M)` — 以 SQLite 表 `ohlcv_bar`(複合鍵含 timeframe + adj_close + source)取代 in-memory `_store`;CsvDataBroker 改讀 DB 並真正依 timeframe 過濾與回傳;ImportRequest 補必填 timeframe。　_為何重要:_ 消滅『重啟即清空』的靜默失憶,並修掉 timeframe 與資料脫鉤導致年化指標失真的 critical bug。這是整個多市場 live 路徑的地基,crypto 以外的市場全靠它。
- **資料品質驗證管線(commit 前報告)** `(M)` — ingestion 加 OHLC 健全性、去重、缺口偵測、timeframe 推斷與宣告值比對、統一 tz 正規化;匯入回傳 validation report,前端先預覽再 commit。　_為何重要:_ Garbage-in 的回測對拿真錢的人最危險;順帶修掉混合時間戳與 range 回測的 opaque crash。fail-loud 必須延伸到資料層。
- **資料來源管理室(資料集清單 + Inspector)** `(M)` — 工具▸資料來源 升級:左側列出所有資料集(market/symbol/timeframe/bar 數/期間/來源/是否還原),右側 Inspector 顯示品質(缺口/重複/OHLC 違規)與 重新拉取/刪除。消費既有 GET /api/markets/imported 並擴充 metadata、補 DELETE 端點。需使用者核准的 nav 偏離。　_為何重要:_ 目前匯入是寫入黑洞,使用者無從判斷手上資料涵蓋哪段、是否可信、能否刪除。資料是回測地基,沒有管理面就無法評估回測可信度。
- **Vendor 資料 adapter 層** `(L)` — 與既有 Broker seam 對齊的資料來源 adapter:台股 FinMind/TWSE、美股 Polygon/AlphaVantage/Yahoo,讓貼 CSV 只是眾多 source 之一,可一鍵拉取/增量更新。　_為何重要:_ 手動貼 CSV 不可規模化;真實 vendor 是對標 QuantConnect/TradingView 的 table-stakes,也是台股/美股從 NotImplementedError scaffold 走向真實的前提。
- **Corporate-action 還原 + point-in-time universe** `(L)` — Candle 增 adj_close,以 split/dividend 還原價格;維護含 delisted 標的的歷史成分,回測可選 raw/adjusted 並避免 survivorship。　_為何重要:_ 未還原的 split 會呈現假崩盤、只用存活標的會系統性高估報酬;沒有這兩者,台股/美股回測的 edge 數字不可信。

<br>

### D10. AI 層 (signal agent / strategy agent / model strategy)

**現況:** strategy_agent 的 never-executed StrategySpec DSL 是扎實的安全地基,但 signal_agent 的單發 LLM 訊號全程無法被釘住(預設 claude-opus-4-8 連 temperature 都不收、Anthropic 也無 seed,只有快取能讓回測可重現)、confidence 不進入下單、成本/provenance 全程不記錄 — 目前是 theater 而非可驗證的 alpha。

**評分:** 投資人 `2/5` · 設計 `3/5`　|　**判決: `Rework`**

**最高槓桿動作:**
- 讓 AI 訊號可重現可審計 — 但用對方法:不是加 temperature/seed(opus-4-8 會 400、Anthropic 無 seed),而是在 AI 回測以 (model, summary_hash) 快取回應達成決定性,並把 Instructor 改成 create_with_completion 以持久化 token/latency/model;在此之前任何含 AI 的回測都不可信、且排程 live 的 run_id idempotency 也站不住。
- 讓 confidence 有牙齒或誠實標示:新增 confidence_gate 節點 / confidence-scaled sizing,並建立 AI 訊號 evaluation harness(forward-return hit-rate、vs indicator baseline、calibration),把『AI alpha』從假設變成可量測。
- 讓 AI provenance 成為 first-class:為 StrategyDef 加 explanation/model 欄位、save 時寫 source='ai'+model+explanation;重設計 SignalTraceDrawer 把 AI 節點的 rationale/confidence 以 cyan 卡片(uncertainty bar)呈現,而非埋在 raw JSON。

**投資人鏡頭 — 發現**

- **🔴 critical** — 含 AI 節點的回測在統計上不誠實且不可重現,且這個病灶沒有任何『加 temperature/seed 就好』的快解:預設模型 claude-opus-4-8 對 temperature 直接回 400(Opus 4.7/4.8 移除 sampling params),Anthropic Messages API 也根本沒有 seed 參數,LLM 取樣本質非決定性且在此路徑上無任何可釘住的旋鈕。workflow_backtest 在每根 bar(上限 ai_bar_cap=200)呼叫 generate_ai_signal 卻不快取回應,因此同一 workflow、同一段歷史,兩次回測會得到不同的 equity curve / win_rate / Sharpe。更嚴重的是這也破壞了 live 的 idempotency 語意:order 節點以 run_id 折出 client_order_id 假設訊號是決定性的,但排程重跑同一 run_id 可能讓 buy↔hold 翻面卻共用同一 client_order_id — 嚴肅資金方既無法重跑驗證,也無法信任排程下單的一致性。
  - 〔證據〕`backend/app/ai/structured.py:107-140(三條 provider 路徑皆無 determinism 控制;且 opus-4-8 收到 temperature 會 400);backend/app/backtest/workflow_backtest.py:64-69 與 :118 每根 bar 呼叫 run_workflow→generate_ai_signal、無回應快取;backend/app/workflow/nodes.py:45-47,202 run_id→client_order_id 的 idempotency 假設訊號決定性`
- **🟠 high** — 單發 LLM 訊號作為 alpha 來源是 theater,且有實質正確性瑕疵:_market_summary 只餵最新收盤、區間漲跌%、RSI(14) 與最後 15 根收盤,卻『不傳 timeframe』(模型分不出這是 1m 還是 1d 的 15 根 K)、也丟棄 candles 內已有的 volume,無 volatility/regime/多週期/部位脈絡。這比既有確定性 indicator 策略掌握的資訊更少,卻包進一個非決定性、未經回測驗證、昂貴的黑箱;confidence 是模型自評的浮點數、無 calibration,沒有任何機制證明 AI 訊號優於 indicator 或優於隨機。
  - 〔證據〕`backend/app/ai/signal_agent.py:32-44(_market_summary 寫死 rsi(closes,14)+closes.iloc[-15:],未傳 timeframe、未用 volume),:17-21 單句 system prompt;對照 backend/app/strategies/registry.py 內建確定性策略`
- **🟠 high** — 全程無 AI 成本 / token / latency 計量:structured.py 用 Instructor 的 client.messages.create(...,response_model=)、只取回 parsed model,丟棄 Anthropic 原始回應與其 usage(input/output tokens)。一次 200-bar AI 回測 = 最多 200 次序列呼叫,且預設模型為 claude-opus-4-8(Opus 級前緣模型,$5/$25 每 1M tokens — 遠貴於 Haiku $1/$5 或 Sonnet $3/$15,後者才適合 per-bar 推論),卻無成本曝露、無預算 guard、無回應快取、未對穩定 system prompt 做 prompt caching、也未走 Batches API(可省 50%)。對主打『與 AI 對話設計策略』的產品,per-bar Opus 推論在規模上靜默燒錢。(注:claude-opus-4-8 非『最貴模型』,Fable 5 $10/$50 更貴 — 修正首版誇大。)
  - 〔證據〕`backend/app/ai/structured.py:90-140 未讀 response usage;backend/app/config.py:28 ai_model 預設 claude-opus-4-8;backend/app/backtest/workflow_backtest.py:47 ai_bar_cap=200`
- **🟠 high** — confidence 在『下單路徑』結構上無作用:signal_agent 夾限並回傳 confidence,workflow_backtest 記錄它,combine 節點確實有用它(weighted 模式 confidence*weight、AND 取 min、OR 取 max),但 _run_order 採 target-position 語意(buy=>固定 quantity、sell=>flat),完全不讀 confidence。UI(MarketPanel『confidence 72%』、SignalTraceDrawer)把它呈現得像在驅動決策,實際上對 position sizing 與成交毫無影響 — 對『嚴肅平台』是 credibility 負債。(修正首版:confidence 並非完全無下游作用,它影響 combine 聚合,但不影響 sizing/成交。)
  - 〔證據〕`backend/app/ai/signal_agent.py:69-74 產生 confidence;backend/app/workflow/nodes.py:167-203 _run_order 只用 signal.action 與固定 quantity;對照 nodes.py:255-274 combine 確有使用 confidence`
- **🟠 high** — AI provenance 在儲存時被銷毀,且資料模型本身就沒有承接它的欄位:design→save 流程中 api/strategies.py:create 硬寫 source="manual"(library.save_strategy 其實接受 source 參數),即使 StrategyDef.source 欄位專為 'ai' vs 'manual' 而存在。更根本的是 SaveRequest 沒有 explanation/model 欄位、StrategyDef 也沒有對應 column — AI 的推理、用了哪個模型、甚至『這是 AI 生成的』這件事,在策略存入 library 的瞬間全部遺失,AI 生成的交易策略沒有任何 audit trail。修復需新增 column,不只是接線。
  - 〔證據〕`backend/app/api/strategies.py:36-39 SaveRequest 無 explanation/model、:87 source="manual" 硬編碼;backend/app/models.py:88-95 StrategyDef 有 source 但無 explanation/model 欄位;backend/app/strategies/library.py:12-19 save_strategy 已接受 source`
- **🟡 medium** — prompt 嚴謹度單薄、無市場特化、workflow 路徑連 extra_context 都接不上:_market_summary 寫死 RSI(14) 與 15 根收盤,system prompt 僅一句;台股/美股 沿用同一套 crypto 形狀的 summary,無市場特化脈絡(交易時段、漲跌停、稅費結構)。signal_agent.generate_ai_signal 雖支援 extra_context,但 workflow 的 _run_ai_signal 從不傳入,等於工作流裡的 AI 節點無法被餵任何額外脈絡。這是 toy prompt,不是 institutional 訊號管線。
  - 〔證據〕`backend/app/ai/signal_agent.py:32-44 寫死指標、:17-21 單句 prompt、:51-59 extra_context 形參;backend/app/workflow/nodes.py:112-115 _run_ai_signal 不傳 extra_context`
- **🟡 medium** — strategy_agent 同樣無 determinism、且 retry 會遮蔽 drift:design_strategy 在預設 opus-4-8 路徑上沒有(也不能有)temperature/seed,ai_max_retries=5 讓 Instructor 在 StrategySpec 驗證失敗時靜默重擲最多 5 次直到通過 — robustness 好,但使用者看不到發生了 N 次嘗試或模型正被強制收斂。不過 spec DSL 本身(never-executed、whitelisted indicators、MAX_INDICATORS=16/MAX_TREE_DEPTH=6、ref↔id 交叉驗證、SpecStrategy 只解譯不執行 rendered python)是真正扎實的 institutional-grade 安全表示,這一塊應保留。
  - 〔證據〕`backend/app/ai/strategy_agent.py:44-50(無 determinism,且 model 預設走 opus-4-8);backend/app/config.py:41 ai_max_retries=5;backend/app/strategies/spec.py:20-22,158-190 安全約束;spec.py:193-282 SpecStrategy 解譯(rendered_python 僅預覽)`

**設計鏡頭 — 發現**

- **🟠 high** — AI rationale 是產品招牌(『與 AI 對話設計策略』)卻在 run trace 以 raw JSON 呈現:SignalTraceDrawer 用 JSON.stringify(step.summary) 把每個節點塞進 mono <pre>。AI 訊號的 reason(最有價值的 AI 產出)與 source:'ai:claude-opus-4-8' 被埋在 JSON blob 裡,視覺上與 data_source 的 {candles:200,last_close:...} 完全無異 — 沒有 cyan、沒有 AI badge、沒有 first-class rationale 區塊。AI-reserved cyan identity 沒有延伸到最該出現的地方:回測訊號的推導軌跡。
  - 〔證據〕`frontend/components/SignalTraceDrawer.tsx:139-152 用 JSON.stringify(step.summary,null,2);backend/app/workflow/engine.py:46-55 _summarize 把整個 Signal model_dump 進 summary`
- **🟡 medium** — confidence 無不確定性編碼、缺乏 advisory 框架(但修正首版的 trust-boundary 框架 — MarketPanel 的 AI 訊號是手動『取得 AI 訊號』面板,從不下單):問題不在『一個 LLM 的猜測正在驅動下單』(它沒有),而在 legibility — MarketPanel 把 confidence 當純數字呈現,51% buy 與 99% buy 視覺權重相同,無 uncertainty bar、無 calibration、無『模型自評、僅供參考』的框架;chart marker 也只是『AI buy 72%』文字。
  - 〔證據〕`frontend/components/MarketPanel.tsx:13-17 SIGNAL_COLORS、:245-254 confidence 純數字呈現、:86-97 aiMarkers 文字`
- **🟡 medium** — AI 設計策略的 explanation 在 chat 顯示一次後即成孤兒:GeneratedStrategy 渲染 rendered_python + 參數表,但不顯示 design.explanation(它只在 DesignChat 以暫時性 chat bubble 出現)。存檔後 explanation 完全消失(後端未持久化、也無欄位)。右側『生成的策略』面板 — spec 的永久家 — 從不說明 AI 為何這樣設計。
  - 〔證據〕`frontend/components/strategy/GeneratedStrategy.tsx:46-101 只渲染 rendered_python/params;explanation 僅在 DesignChat.tsx:30-35 作為短暫訊息`
- **🟡 medium** — 昂貴的『per-bar AI 回測』路徑無進度/成本/取消回饋(修正首版:把問題對準正確路徑):DesignChat 的單一 cyan pulse 點用於『單次』策略設計呼叫,尚可接受;真正的缺口是 AI 回測 — 最多 200 次序列 opus-4-8 呼叫、可能耗時數十秒到數分鐘,卻無 bar 進度、無 token/成本表、無 cancel。latency/feedback 故事在最貴的 AI 路徑上缺席。
  - 〔證據〕`frontend/components/strategy/DesignChat.tsx:90-95 單一 pulse(單次呼叫尚可);backend/app/backtest/workflow_backtest.py:64-69,95-118 AI 回測逐 bar 同步呼叫但 UI 無對應進度表面`
- **🟡 medium** — builder 的 ai_signal 節點只暴露一個空白選填 model 文字欄:nodeCatalog ai_signal params=[{key:'model'}]、summaryKeys=[],節點本體只顯示『AI signal』占位字。節點是 cyan(正確、AI-reserved)但其餘不透明 — 看不到也調不了 AI 被問什麼、無法設 confidence gate、無法預覽 prompt、無法覆寫 symbol/timeframe。對『嚴肅工具』而言過於陽春。
  - 〔證據〕`frontend/components/workflow/nodeCatalog.ts:59-64 ai_signal 僅 model 參數、summaryKeys=[];frontend/components/workflow/TradeNode.tsx:11,28,36 isAI 只切換 text-accent 與 'AI signal' 占位字`
- **🔵 low** — cyan identity 在既有處正確落地(DesignChat header dot +『AI 生成』badge、TradeNode isAI→text-accent、accent 送出鈕)— 這部分 lands 且應保留。GeneratedStrategy header 對非 AI-執行的 spec viewer 也用 cyan dot 屬輕微過度延伸,但作為『AI 生成產物』可辯護。
  - 〔證據〕`frontend/components/strategy/DesignChat.tsx:62-66 cyan dot+badge;frontend/components/workflow/TradeNode.tsx:28 isAI→text-accent;frontend/components/strategy/GeneratedStrategy.tsx:48-49 對 spec viewer 亦用 bg-accent dot`

**重設計提案**

四條主線:讓 AI 訊號可重現可審計、讓 confidence 有牙齒或誠實標示、讓 provenance 與 rationale 成為 first-class UI、把『AI alpha』從假設變成可量測。

1) 可重現性與成本(backend,根因 — 並修正首版的錯誤處方)。重點:**不要加 temperature/seed**。預設模型 claude-opus-4-8 收到 temperature 會回 400(Opus 4.7/4.8 已移除 sampling params),Anthropic Messages API 也沒有 seed 參數,LLM 取樣在此路徑上沒有任何可釘住的旋鈕。唯一誠實的決定性保證是『回應快取』:在 AI 回測時以 (model, market_summary 的 hash) 為鍵快取每根 bar 的 AISignalResponse — 相同 summary 不重打 LLM,直接讓回測 deterministic 且把 ≤200 次呼叫壓到實際不同 summary 的數量。同時把 structured.py 從 Instructor 的 `.create(response_model=)` 換成 `create_with_completion`(或讀 `._raw_response.usage`),持久化每次呼叫的 (model, input_tokens, output_tokens, latency_ms)。成本面:per-bar 推論預設改用較便宜層級(Haiku 4.5 $1/$5 或 Sonnet 4.6 $3/$15,而非 Opus 4.8 $5/$25)、對穩定 system prompt 開 prompt caching、離線 AI 回測走 Batches API(省 50%)。新增 AISignalCall 表持久化每次呼叫,讓 SignalTraceDrawer 能回溯『這格 buy 是哪個 model、哪段 prompt、花了多少 token』。(對 OpenAI 相容 provider lmstudio/openrouter 可額外傳 temperature=0+seed,但那是 provider-specific,非決定性保證。)

2) confidence 有牙齒。新增一個 logic 類別的 `confidence_gate` 節點(amber,沿用 --c-logic),參數 conf ≥ 0.70,夾在 AI/strategy 訊號與 order 之間把低信心轉成 hold;或讓 order 節點支援 confidence-scaled sizing(target = quantity × confidence)。文件與 UI 明示:未經 gate 時 confidence 不影響成交。

3) provenance 持久化。為 StrategyDef 新增 explanation / model 欄位(source 已存在);SaveRequest 增加 explanation/model;api/strategies.py:create 依來源寫入 source=\"ai\" 並存 explanation+model。GeneratedStrategy 永久顯示『AI 設計理由』區塊。

4) SignalTraceDrawer 重設計 — 把 AI 節點從 JSON blob 升格為 cyan-marked rationale 卡片(uncertainty bar 用填滿比例表達信心),deterministic 節點維持低調 mono summary:

```
┌─ Signal Trace · BTC/USDT ───────────────┐
│ BUY · conf 0.72 · 14:00 · px 64,210      │
├──────────────────────────────────────────┤
│ ① data_source   {candles 200, last …}    │  ← 灰,低調 mono
│ ② ⚡ ai_signal   ai:sonnet-4-6            │  ← cyan 左條
│    ┌ confidence ───────────────────────┐ │
│    │ ███████████████░░░░░  0.72         │ │  ← --accent 填滿條
│    └────────────────────────────────────┘ │
│    "RSI 28 + 連三紅,短線超賣反彈"          │  ← reason 直接呈現
│    summary_hash 9f3a · 1,204 tok · 1.8s   │  ← provenance(faint)
│ ③ confidence_gate  conf ≥ 0.70  → pass    │  ← amber --c-logic
└──────────────────────────────────────────┘
```

5) AI 訊號品質量表(投資人最在意)。新增離線 evaluation harness:對歷史拉 AI 訊號,計算 forward-return hit-rate、與 rsi/ma_cross baseline 的對照、confidence calibration(reliability 曲線),把『AI alpha』從假設變成可量測。在策略室提供一個『AI vs 內建策略』小對照卡,誠實呈現 AI 是否真的贏。

**本域新功能提案**

- **AI 訊號回測回應快取(決定性 + 成本)** `(M)` — AI 回測以 (model, market-summary hash) 為鍵快取每根 bar 的 AISignalResponse;structured.py 改用 create_with_completion 持久化 token/latency/model。不引入 temperature/seed(預設 opus-4-8 不收 temperature、Anthropic 無 seed)。　_為何重要:_ 把含 AI 的回測從 run-to-run 隨機變成可重現、可重跑驗證,順帶把 ≤200 次 Opus 呼叫壓到實際不同 summary 數,並讓 run_id 的 live idempotency 重新成立 — 一次解決統計誠實、成本、與排程一致性三個病灶。
- **AI 訊號品質量表 (evaluation harness)** `(M)` — 離線跑歷史 AI 訊號,輸出 forward-return hit-rate、與 rsi/ma_cross baseline 對照、confidence reliability 曲線;策略室加『AI vs 內建』對照卡。　_為何重要:_ 目前無任何證據顯示單發 LLM 訊號優於內建 indicator 或隨機;沒有量表就無法主張 edge,嚴肅資金方不會在『未被衡量的 alpha』上下注。
- **confidence_gate 節點 + provenance 持久化** `(M)` — logic 類別新節點(amber)把低信心訊號降為 hold;StrategyDef 加 explanation/model 欄位,save 寫入 source='ai'+model+explanation 並在 GeneratedStrategy 常駐顯示理由。　_為何重要:_ 讓目前純裝飾的 confidence 真正影響交易,並建立 AI 生成策略的 audit trail — 兩者都是『可用真錢的 AI 平台』的 table stakes。

<br>

### D11. Shell / IA / 設計系統 / nav / theme / onboarding / docs

**現況:** design-token 地基扎實(完整 dark/light/market-aware 調色、mono tabular、tight radii、no-flash theme script),但持久性 shell(TopBar/Sidebar)不承載任何資本脈絡 — paper/LIVE 模式只零散出現在 home 與 workflow 兩頁、IA 缺 orders/risk/ledger/broker 一級入口、tree 實際不可收合且父層為死連結。

**評分:** 投資人 `2/5` · 設計 `3/5`　|　**判決: `Rework`**

**最高槓桿動作:**
- 在 TopBar 建一條永遠在場的 Global Context Bar(落實 DESIGN.md:116):把已存在於 Toolbar.tsx:42 / HomeDashboard.tsx:200 的 LIVE chip 上提為 shell-persistent · 收斂 market 選擇器為單一全域控制(同時修掉 data-market 跨頁殘留與 PortfolioPanel 方向誤色)· 帶出後端 risk/ledger/orders 的 equity、當日損益、kill-switch/halt 與連線健康度。
- 擴充 IA 讓資本安全面成為一級公民:交易室 加『下單簿/委託』與『實際下單(leaf.live=true,點亮 TreeNav.tsx:49,53 既有 --live 死碼)』,新增一級『風控』『帳本』,工具下加『Broker 連線/帳戶』。
- 清償 nav/可及性負債:tree 真正可收合(chevron+收合狀態,移除 TreeNav.tsx:28 的 href='#' 死錨)· rail 補 logomark 與 title/flyout 標籤、empty/error 補 nav-label · drawer 補 focus trap/return · mobile nav 列 ≥44px · --faint 退出微型文字改 --muted。

**投資人鏡頭 — 發現**

- **🟠 high** — paper/LIVE 模式不在持久性 shell(TopBar/Sidebar)中,只零散出現在兩個頁面 — 切到 market/portfolio/backtest/strategy-lab/schedules/notifications 時模式脈絡完全消失。DESIGN.md 第 116 行明訂 top bar 應承載『market color, theme, live/paper』context control,但 TopBar 的 ml-auto 區只有 ThemeToggle 與 /docs 連結。對一個 serious live 平台,『我現在是否武裝成真實下單』必須在任何頁面都一眼可辨,而非頁面層細節。(更正第一版:模式並非『整個 shell 不可見』— Toolbar.tsx:42-43 與 HomeDashboard.tsx:200-203 確實顯示 LIVE chip,故降為 high 而非 critical。)
  - 〔證據〕`TopBar.tsx:19-27 ml-auto 僅 ThemeToggle+/docs;對照 HomeDashboard.tsx:200-203 與 Toolbar.tsx:42-43 已有 bg-live/15 text-live chip、Toolbar.tsx:90-92 已把 run 按鈕翻成『送出真實訂單』— 證明模式信號存在但未上提到 shell;DESIGN.md:116。`
- **🟠 high** — NavLeaf.live + TreeNav 的 border-live/text-live 是死碼:nav.ts 沒有任何 leaf.live=true,故 DESIGN.md 第 155 行『實際下單 leaves use the --live dot』這條規則從未在 nav 觸發。IA 也因此沒有任何 live 下單入口。對宣稱可接真實資產的平台,nav 結構裡完全沒有 live 面是資本安全層級的缺位。
  - 〔證據〕`nav.ts:9 NavLeaf 定義 live?:boolean;nav.ts:12-42 無任一 leaf 設 live=true;TreeNav.tsx:49,53 的 border-live/text-live 與 text-live 因此永不觸發;DESIGN.md:155。`
- **🟠 high** — shell 不承載任何持久性帳戶/風險脈絡:TopBar 無 account equity、無當日損益、無 daily-loss halt 或 kill-switch 狀態、無 broker 連線健康度。後端已有 risk/ledger/orders router(CLAUDE.md 架構;SystemFeatures.tsx:74 自陳有 RiskGuard+kill switch+FIFO ledger),帳戶數字只在 home 頁出現,離開 home 即失去。Bloomberg-grade『精密儀器』的頂欄目前是空 chrome。
  - 〔證據〕`TopBar.tsx 整支只渲染 hamburger、mobile 品牌、ThemeToggle、docs 連結;equity/P&L/halt/連線指標皆無;對照 HomeDashboard.tsx:99 已讀 config.trading_mode 但僅作用於該頁。`
- **🟠 high** — IA 無法承載 serious live 多市場平台:NAV 缺『下單簿/委託(Orders blotter)』『風控(Risk console)』『帳本(Ledger/已實現損益)』『Broker 連線/帳戶』等資本安全一級入口。真實下單的監控與稽核面被埋在頁面內而非結構化導覽。另:策略庫 leaf 掛在 策略室 下,但其 saved strategy 子項卻導向 交易室/模擬回測(StrategyLibraryTree.tsx:31),破壞 DESIGN.md:127『tree 永遠顯示你在哪』。
  - 〔證據〕`nav.ts:12-42 僅 策略室/交易室(模擬回測·工作流)/市場/投組/工具(排程·通知·匯入);無 orders/risk/ledger/broker;StrategyLibraryTree.tsx:31 href 跨 room 跳轉。`
- **🟡 medium** — market-aware --up/--down 方向色跨頁殘留,會直接誤讀 P&L 方向。setMarket 只在 HomeDashboard/MarketPanel/BacktestPanel 的 useEffect 被呼叫,且 useMarket.ts 只在 market==='tw_stock' 時設 data-market、其餘 delete — 但 portfolio/notifications/schedules 三頁從不呼叫 setMarket 也無 unmount reset。看完一支 台股(red=up)回測後切到 投組,document.documentElement.dataset.market='tw' 仍掛著,PortfolioPanel.tsx:74 的 unrealized_pnl 就會把 crypto 獲利渲染成紅色(台股慣例)。違反『Never hardcode green-as-gain』背後的方向正確性意圖。
  - 〔證據〕`useMarket.ts:2-6;呼叫點僅 HomeDashboard.tsx:50、MarketPanel.tsx:53、BacktestPanel.tsx:89;PortfolioPanel.tsx:74 用 text-up/text-down 且無 setMarket 呼叫;market 選擇器散落於 MarketPanel.tsx:143 / BacktestPanel.tsx:239 而非 top bar。`
- **🟡 medium** — paper 與 live 在 shell/nav 層沒有結構性區隔:trading_mode 是後端單一全域值(HomeDashboard.tsx:99、WorkflowBuilder mode=config.data.trading_mode),投組只有單一入口,paper↔live 的信任邊界淪為頁面內 chip 而非 IA 一級維度。serious 平台應讓使用者在導覽層即分辨自己看的是模擬或真實帳戶/部位。
  - 〔證據〕`nav.ts:32 單一 { label:'投組', href:'/portfolio' };無 paper/live 維度;trading_mode 為後端全域(HomeDashboard.tsx:99)。`

**設計鏡頭 — 發現**

- **🟠 high** — 樹狀導覽實際上不可收合,與 DESIGN.md 第 151 行『parent rows expand/collapse(chevron, 120ms)』直接衝突。TreeNav 無 expand state、無 chevron,children 在 :37-61 無條件渲染;且帶 children 的父層(策略室/交易室/工具)在 nav.ts 無 href,經 TreeNav.tsx:28 的 href={item.href ?? '#'} 渲染成 <Link href='#'> — 點父層標籤是個死錨點(跳頁頂並把 # 寫進 URL)。當策略庫成長,這棵樹無法被收束,正是 DESIGN.md 引入 tree(讓 nav 隨 library 擴張仍可導覽)的初衷反被打破。
  - 〔證據〕`TreeNav.tsx:26-36 父列無 onClick/useState/chevron;TreeNav.tsx:28 href ?? '#';nav.ts:14,24,35 父項 策略室/交易室/工具 無 href;children 於 TreeNav.tsx:37-61 無條件展開;DESIGN.md:151。`
- **🟠 high** — 64px icon-rail 模式(tablet 768–1279,涵蓋整段平板/小筆電)破損且不可發現:(1) 品牌『AI Trade Flow.』未收成 logomark、未掛 .nav-label,在 64px 欄(扣 px-4 後約 32px)必溢位/換行裁切;(2) nav 列無 title/aria-label,icon-only 項目沒有任何方式取得標籤,違反 DESIGN.md:167『labels on hover/flyout』;(3) StrategyLibraryTree 的 empty/error <p> 未掛 .nav-label,在 rail 中文字照樣顯示而溢出 64px(注意 saved-strategy Link 本身已掛 nav-label,只有空/錯狀態漏掛)。
  - 〔證據〕`AppShell.tsx:20 [&_.nav-label]:hidden xl:[&_.nav-label]:inline;Sidebar.tsx:12-14 品牌 text-base font-bold 無 rail 變體/無 nav-label;TreeNav.tsx:27-36,45-55 各 Link 無 title;StrategyLibraryTree.tsx:21,25 <p> 無 nav-label;DESIGN.md:167。`
- **🟡 medium** — 行動 drawer 缺焦點管理,未達 DESIGN.md:173『trap focus when open』。AppShell 有 Esc 關閉(:11)、scrim 點擊關閉(:24)、hamburger 為真 <button aria-expanded>(TopBar.tsx:11),且 drawer 關閉時設 inert(:27)— 這些 a11y 基本面正確;但開啟時 main/TopBar 未設 inert、焦點未移入 drawer 也未被 trap,可 Tab 到 scrim 後方,關閉後焦點不回到 hamburger。
  - 〔證據〕`AppShell.tsx:9-15 僅監聽 Escape;:26-27 inert 僅在 !open 時加;無 focus trap/return;對照 DESIGN.md:173-174。`
- **🟡 medium** — 行動 nav 列觸控目標低於 DESIGN.md:175『≥44px tall nav rows on mobile(override 桌面密度)』。TreeRow 與 leaf 皆 px-3 py-2(約 32–36px),saved strategy 更只 py-1.5(約 30px),且 drawer 沿用桌面 .nav-label 樹、無任何 mobile 高度 override。第一版漏掉此 RWD 缺口。
  - 〔證據〕`TreeNav.tsx:30 px-3 py-2、:48 leaf py-2、StrategyLibraryTree.tsx:40 py-1.5;DESIGN.md:175;AppShell.tsx:28 drawer 直接渲染同一 Sidebar 無密度切換。`
- **🟡 medium** — --faint 用於微型『文字』時對比不足:--faint #5B616B 疊在 --bg #0A0B0D 上約 3.15:1,低於 WCAG AA 文字 4.5:1(light 主題 --faint #8A9099 疊 #FBFBFA 同樣約 3:1)。更正第一版:nav leaf icon 用 text-faint 屬圖形物件(門檻 3:1),3.15:1 通過,不算缺陷;真正失格的是 12–13px 文字用途(策略庫 empty/error、docs 分類標籤、SystemFeatures 英文小標)。
  - 〔證據〕`globals.css:16 --faint #5B616B、:14 --bg #0A0B0D;文字用途:StrategyLibraryTree.tsx:21,25(12px)、docs/page.tsx:52(uppercase 12px)、SystemFeatures.tsx:102(13px);圖形(可豁免):TreeNav.tsx:34,53。`
- **🔵 low** — accent 作為裝飾滲漏,違反 DESIGN.md:259『accent is cyan and earns its place; it is not decoration』與 AI-reserved 規則。SystemFeatures 把每個 feature(含非 AI 的 風控/FIFO ledger)的所有條列點都用 bg-accent/70 圓點;Markdown 把所有 inline code 一律染成 text-accent。屬 docs/說明面而非交易終端,故 low,但仍稀釋 cyan=AI 的語意。
  - 〔證據〕`SystemFeatures.tsx:120 bg-accent/70 套用所有 points;Markdown.tsx:76 inline code className 含 text-accent;DESIGN.md:73,259。`
- **🔵 low** — 設計文件漂移:DESIGN.md:149 將 --nav-w 240px / --nav-w-rail 64px 列為 token,但 globals.css:5-37 從未定義這兩個變數,寬度硬寫在 AppShell 的 tailwind grid class。非 bug,但破壞 DESIGN.md:67『CSS custom properties are the contract』的單一真相。
  - 〔證據〕`globals.css:5-37 無 --nav-w/--nav-w-rail;AppShell.tsx:18 硬寫 md:grid-cols-[64px_1fr] xl:grid-cols-[240px_1fr];DESIGN.md:149。`
- **🔵 low** — onboarding 從不建立 paper↔live 信任心智模型:三步引導為 strategy-lab→backtest→schedules,完全沒提到『paper 是安全預設、live 必須明確武裝』或任何風控概念。對一個目標為 serious live 的平台,首觸引導未交代信任邊界是設計層的疏漏。
  - 〔證據〕`Onboarding.tsx:8-12 STEPS 僅 strategy-lab/backtest/schedules;body/title 無 paper/live/risk 字眼。`

**重設計提案**

核心主張:把 shell 從『導覽外殼』升級為『交易儀器框架』。兩件事必須結構化 —(A)一條永遠在場的 Global Context Bar,(B)讓 paper/live 與資本安全面成為 IA 一級公民。全部沿用既有 token 與既有元件樣式,不新增調色盤、不重寫已存在的信號。\n\n重要前提(避免重造輪子):LIVE chip 與 btn-live 已存在於 Toolbar.tsx:42-43,90-92 與 HomeDashboard.tsx:200-203 — 本案是把這套既有樣式『上提到持久 shell』,而非新發明。market 選擇器目前散落在 MarketPanel.tsx:143 / BacktestPanel.tsx:239 — 本案是把它『收斂為單一全域控制』,順手修掉 data-market 跨頁殘留。\n\n【A. Global Context Bar(改寫 TopBar 的 ml-auto 區,落實 DESIGN.md:116)】\n把目前只有 ThemeToggle+docs 的空 chrome,換成密集、.num tabular、隨時可讀的脈絡列。market 選擇器在此全域驅動 data-market;mode pill 在 live 時走 --live 並用 DESIGN.md:187 唯一允許的脈動點。\n\nDARK · LIVE(危險僅以 --live 標,其餘維持 calm data field):\n```\n┌──────────────────────────────────────────────────────────────────────────────┐\n│ ☰ ATF.  [ crypto ▾ ]  ┃ ● LIVE ┃  權益 1,284,503 TWD  ▲ +0.82%   今日 +8,420 │\n│                         (--live·脈動)  .num tabular        --up/--down        │\n│        kill-switch ○ armed    連線 ● ok          [系統 亮 暗]    文件中心 ↗     │\n└──────────────────────────────────────────────────────────────────────────────┘\n```\nPAPER(安全預設,mode pill 走 --surface-3/--muted,無脈動):\n```\n│ ☰ ATF.  [ crypto ▾ ]  ┃ paper ┃  紙上權益 1,000,000 TWD  ▲ +0.82%  …  亮 暗 │\n```\n規則:LIVE pill = bg-live/15 text-live + 脈動點(重用 Toolbar.tsx:42 已驗證樣式);paper = 中性。權益/今日損益走 --up/--down,且因 market 全域化,方向色恆正確。kill-switch 觸發時整段 chip 轉 --error 並要求確認 — 把後端 risk router 的 halt/kill 狀態第一次帶到使用者眼前。連線健康度讀 broker 狀態。窄螢幕(<lg)只保留 market+mode pill,equity/連線折進 hamburger 後抽屜頭。\n\n【B. IA 擴充(nav.ts)— 點亮死碼、補齊 live/資本安全面】\n```\n策略室 (FlaskConical, ai)\n  ├ 與 AI 設計策略   └ 策略庫(saved 動態;子項應留在本 room 的 backtest context)\n交易室 (Network)\n  ├ 模擬回測   ├ 工作流\n  ├ 下單簿/委託   ← 新:Orders blotter(orders router 已存在)\n  └ 實際下單       ← 新:leaf.live=true,終於用上 TreeNav.tsx:49,53 既有 --live 死碼\n市場 · 投組(分 paper / live 兩節)\n風控 (ShieldAlert)   ← 新一級:RiskGuard / Portfolio 上限 / kill-switch(risk router)\n帳本 (BookText)      ← 新一級:FIFO 已實現損益 / 報稅 CSV(ledger router)\n工具 ├ 排程 ├ 通知 ├ 匯入 └ Broker 連線/帳戶   ← 新\n```\n這同時把 nav.ts:9 的 NavLeaf.live 與 TreeNav.tsx:49,53 那條死路徑真正接上;cyan 仍只標 active 與 AI leaf,live leaf 用 --live 點。\n\n【C. 隨手清償的設計負債】\n1) 樹真正可收合:父列改 <button aria-expanded> + chevron(120ms,DESIGN.md:151),展開狀態存 localStorage;移除 TreeNav.tsx:28 的 href='#' 死錨。\n2) Rail(md):品牌收成『ATF.』logomark;每列補 title/aria-label 或 hover flyout;StrategyLibraryTree.tsx:21,25 的 empty/error <p> 補 .nav-label。\n3) Drawer:開啟時 main 設 inert + focus trap,關閉 return focus 至 hamburger(補齊 AppShell.tsx 既有 Esc/inert-when-closed 之外的 trap/return,DESIGN.md:173)。\n4) Mobile 觸控:drawer 內 nav 列覆寫為 min-h-[44px](DESIGN.md:175)。\n5) market 全域化:仿 providers.tsx 的 ThemeProvider 加一個 MarketProvider(market/mode/account),shell 與各 panel 訂閱;setMarket 不再散落於三個 panel,徹底消除跨頁紅綠殘留(修 PortfolioPanel.tsx:74 誤色)。\n6) a11y 對比:--faint 退出微型『文字』,改 --muted;icon 用途可保留 --faint(通過 3:1 圖形門檻)。\n7) 補回 --nav-w/--nav-w-rail token,AppShell.tsx:18 改吃變數。\n8) accent 去裝飾:SystemFeatures.tsx:120 非 AI 條列點改 --faint;Markdown.tsx:76 inline code 改 text-text + bg-surface-3(保留 cyan 給 AI 徽章)。\n9) onboarding:在三步前加一張『paper 是安全預設、live 需明確武裝』的信任卡,呼應 Global Context Bar 的 mode pill。

<br>

### D12. 執行真實性 Execution & order model (fills / slippage / order types / sizing / shorting)

**現況:** 回測地基比第一版評估認定的更紮實——除無 look-ahead 的單序列 run_backtest 外,還有一條真實的 shared-cash 多資產 portfolio backtest(workflow_backtest.py),但「成交本身」仍是整條信任鏈最脆弱的環:limit 幻想成交、預設滑價 0 且與規模無關、long-only、無 per-signal sizing、無訂單生命週期,且 live ccxt 回傳 status='closed' 直接繞過 ledger 的 =='filled' 記帳——對嚴肅實盤,核心可信度尚未達標。

**評分:** 投資人 `2/5` · 設計 `2/5`　|　**判決: `Rework`**

**最高槓桿動作:**
- 修掉成交原語 + 狀態契約:limit 需 marketability check(next-open 觸及才成交)、stop 需 intrabar(bar.high/low)觸發、新增 open/partially_filled/cancelled 狀態與 filled_quantity/avg_fill_price;並修正 execution.py:107 讓 live ccxt 'closed' 成交能進 ledger(今日 live realized-P&L 靜默為空);paper 與兩條 backtest 共用同一 fills 引擎,消除 execution.py:67-70 與 paper.py:77-80 兩份重複限價邏輯。
- 用 size/liquidity/volatility 滑價模型取代固定 bps,並給非零預設(現為 COST_SLIPPAGE_BPS=0.0),讓任何具規模/高週轉策略的 net edge 不再被系統性高估、optimize.py 不再於零摩擦下挑高週轉 overfit。
- 導入 sizing 引擎(fixed-risk by 停損距離 / vol-target / equity-fraction)取代靜態 quantity(nodes.py:188)、position_fraction 與 equal-weight PortfolioSim,並餵入目前被丟棄的 signal.confidence;順勢補做空/保證金與 PortfolioSim 權重,讓可回測範圍對齊 PortfolioGuard 的可實盤範圍。

**投資人鏡頭 — 發現**

- **🔴 critical** — Limit 單為「幻想成交」(fantasy fill):限價單被假設在限價瞬間、全額成交,完全不檢查市場是否觸及限價,也無掛單(resting)語意。買進限價掛在遠低於市價處仍立即成交於限價。今日 blast radius 精確為:可透過 orders API(POST /api/orders {type:'limit', limit_price})觸及——回測引擎(engine.py)為 market-only next-bar-open、不走 limit;workflow builder 的 order 節點永遠送 market(nodes.py:197 不帶 type),故 builder 與回測結果今日不受此污染。但對一個以 limit 為 table-stakes 的嚴肅實盤平台,paper 是上線前唯一的驗證面,在 paper/live 共用的 execute_order 上建立 fantasy-fill 原語會毒害日後一切疊加(sizing/bracket),故列 critical。
  - 〔證據〕`execution.py:67-70 `if request.type==OrderType.limit and request.limit_price: fill_price=request.limit_price`;paper.py:77-80 同邏輯 base_price=limit_price 後 slippage_price 全額 fill,paper.py:113 status 硬寫 'filled'`
- **🟠 high** — Live ccxt 成交永遠不會進 FIFO realized-P&L ledger——靜默失敗(違反 fail-loud)。CcxtBroker.create_order 回傳 `status=order.get('status') or 'open'`;ccxt 對完全成交的市價單正規化為 'closed'(非 'filled')。但 execution.py 只在 `result.status=='filled'` 時呼叫 record_fill。PaperBroker 硬寫 'filled' 故 paper 會記帳,live('closed')整批繞過——live 的已實現損益帳是空的。OrderRecord 仍會被持久化(execution.py:87-101 不分 status),但 ledger 缺漏,直接打臉「single order path / broker-agnostic ledger」的設計意圖。這是比第一版『desync』更精確、可驗證的具體 bug。
  - 〔證據〕`crypto_ccxt.py create_order `status=order.get('status') or 'open'`(Binance 市價全成→'closed');execution.py:107 `if result.status=='filled': record_fill(...)`;paper.py:113 硬寫 'filled'`
- **🟠 high** — 預設滑價為 0,且滑價模型與訂單大小/流動性/波動度無關(固定 bps)。出廠 COST_SLIPPAGE_BPS=0.0 代表預設 paper/backtest 成交「零滑價」(但 fees 預設非零,taker 7.5bps,故非完全 frictionless);即便設非零,0.01 BTC 與 100 BTC 受相同滑價。對具規模/高週轉策略,net edge 被系統性高估,且 optimize.py 的 grid search 會在零摩擦下主動挑出高週轉 overfit。屬可信度侵蝕的 high(非 critical:可組態、不造成對帳失敗)。
  - 〔證據〕`config.py:156 `cost_slippage_bps: float = 0.0`;.env.example:58 `COST_SLIPPAGE_BPS=0.0`;costs.py:84-87 `slippage_price` 僅 `price*(1±bps/1e4)`,costs.py:43 自承「leaves room for a spread/volume model later」`
- **🟠 high** — 完全沒有 per-signal 部位 sizing,signal.confidence 一路算出後被丟棄。workflow order 節點用靜態 quantity(catalog 預設 0.01),單序列 backtest 用全域 position_fraction,多資產 portfolio backtest 用 equal-weight(per=equity/n);三者皆無 fixed-risk(由停損距離反推)、vol-target 或 Kelly。combine 的 weighted 模式辛苦算出的 confidence 在 order 節點與 portfolio 的 desired_long(布林)被棄用,故每筆風險敞口未定義。
  - 〔證據〕`nodes.py:188 `target_qty=float(p.get('quantity',1))`(confidence 未用);backtest/engine.py:109 `spend=cash*position_fraction`;backtest/portfolio.py:49-59 `target_quantities` equal-weight `per=equity/n`;workflow_backtest.py:161-164 desired_long 布林化、confidence 僅入 signals 紀錄不入 sizing`
- **🟠 high** — 全鏈 long-only,無做空、無保證金/槓桿、無 sell-to-open。Position 僅 symbol/quantity/avg_price(隱含非負,無 side),PaperBroker 賣出被 held 上限卡死並 raise,單序列與多資產回測引擎皆自述 long/flat,PortfolioSim 目標永遠 ≥0。market-neutral/pairs/放空/槓桿策略空間整片無法表達——與『serious multi-market live platform』目標直接衝突。
  - 〔證據〕`schemas.py:94-98 `Position(symbol,quantity,avg_price)` 無 side;paper.py:96-104 sell 以 held 為上限 raise;backtest/engine.py:71 'long-only';backtest/portfolio.py:1-3 'One cash pool, long/flat only. Equal-weight';nodes.py:170-173 'long/flat only — never short'`
- **🟠 high** — 無訂單生命週期與部分成交模型。OrderType 僅 market/limit(無 stop/stop_limit);OrderResult.status 是自由字串、單一 price 欄,無 new/open/partially_filled/cancelled 狀態機,無 filled_quantity 對 quantity、無 avg_fill_price 對下單價之分。一旦 ccxt 回傳 open 或部分成交,paper/ledger 無法誠實表達,且與上面 live-ledger 繞過 bug 疊加,使 live 帳務不可靠。
  - 〔證據〕`schemas.py:32-35 `OrderType{market,limit}`;schemas.py:75-85 `status: str  # 'filled'|'open'|'rejected'`、單一 `price`;OrderRequest 無 stop_price/TIF/reduce_only(schemas.py:67-72)`
- **🟡 medium** — 多資產 portfolio backtest 雖存在,但為 equal-weight、long/flat,且時間軸採『嚴格交集』,有靜默截斷史料的 data-integrity 隱憂(更正第一版『無 portfolio backtest』的錯誤結論)。_aligned_timeline 取所有 symbol 時間戳的交集 `common & ts`;對交易日曆不同的標的(台股 vs 美股 vs crypto 24/7),稀疏標的會悄悄縮短整段回測窗,且只在剩 <2 bar 時才 fail-loud——違反 fail-loud 慣例。組合層仍無 per-asset 權重/相關性/sizing/做空。
  - 〔證據〕`workflow_backtest.py:30-36 `_aligned_timeline` 用 `common & ts`(交集);workflow_backtest.py:60-62 僅 <2 bar 才 raise;backtest/portfolio.py equal-weight long/flat;PortfolioGuard(trading/risk.py:66+)管 base-currency 組合敞口的可實盤範圍 > 可回測的權重表達範圍`
- **🟡 medium** — 停損/SL-TP 非真正 intrabar——close-only 檢查、next-bar-open 市價成交(更正第一版對缺口的描述)。risk_exit 只在 close[i] 評估 P&L、訊號於 open[i+1] 成交。後果其實有二:(a) bar 內觸碰停損後又收上去的 whipsaw 完全被漏算(只在 bar 邊界檢查);(b) 成交價是 next-open、非停損價,可能優於亦可能劣於停損。注意:跳空時 open[i+1] 會吃掉缺口(成交更差),故『低估缺口風險』的說法不精確——真正問題是『不是 intrabar 觸發』與『成交價脫離名目停損』。
  - 〔證據〕`nodes.py:145 `pnl_pct=(price/avg_price-1)*100`,price=candles[-1].close;backtest/engine.py:108,123 一律 next-bar `bar.open` 成交,全程不讀 bar.high/bar.low`
- **🟡 medium** — maker/taker 在實務中從未區分(撮合永遠以 taker 計費),且 live ccxt 合成部位 avg_price=0。paper.py 與兩處 backtest 呼叫 fill_cost 都不帶 liquidity → costs.py 預設 taker;惟出廠 crypto_taker_bps==crypto_maker_bps==7.5,故此差異在組態出不同費率前為 latent。live 既有持倉 cost-basis 為 0 → 未實現損益失真(看似 100% 獲利),且 FIFO 賣出觸發 'untracked disposal' 警告。
  - 〔證據〕`paper.py:84 與 backtest/engine.py:111,124 呼叫 fill_cost 未帶 liquidity → costs.py:96/102 預設 taker;config.py:149-150 maker==taker==7.5;crypto_ccxt.py:192 `avg_price=0.0`;ledger.py:184-189 對未匹配數量發 'untracked disposal' warning`

**設計鏡頭 — 發現**

- **🟠 high** — 下單 Order 節點只暴露一個 quantity 數字欄位。無 order type(market/limit/stop/bracket)、無 limit/stop 價、無 TIF、無 sizing 模式。schema 雖有 limit/limit_price,但 builder 永遠送 market(nodes.py:197 OrderRequest 不帶 type),limit/stop 在唯一的建流程裡根本不可達。交易員無法在唯一能表達下單意圖的地方表達真實意圖——這也是 investor finding 1 今日 blast radius 限於 API 的原因。
  - 〔證據〕`frontend/components/workflow/nodeCatalog.ts:74-79 order 節點 `params:[{key:'quantity',default:0.01}]` 僅此一欄;workflow/nodes.py:197 `OrderRequest(symbol,side,quantity=abs(delta))` 未帶 type/limit_price`
- **🟠 high** — 送出真實訂單前沒有任何 order ticket / pre-trade preview。orders API place_order 直接執行,無預估成交價、預估費用、預估滑價、保證金影響、現金影響的確認步驟。DESIGN.md 要求 live 必須 unmistakable + fail-loud,run 按鈕雖會翻成 btn-live,但在『按下送出』這個最危險的瞬間,UI 不提供任何單筆成交品質預覽。
  - 〔證據〕`DESIGN.md:40-44 live 安全狀態要求;api/orders.py:19-32 place_order 直接 `execute_order(...)` 無預覽;BacktestPanel/PortfolioPanel 全無下單預覽元件`
- **🟡 medium** — 成交品質完全沒被 surface,且後端根本沒持久化讓前端可顯示。PortfolioPanel recent orders 只顯示 side+qty+symbol+price,無 fee/cost/滑價/order type/狀態 badge。更關鍵:fee/tax 只活在 OrderResult.info 與 ledger,OrderRecord 模型『沒有』fee 欄位,故 orders list endpoint 回的資料根本不含費用——要 surface 成交成本需先在後端持久化 fee 或 join ledger(第一版稱『OrderRecord 在 info 有 fee』不精確)。
  - 〔證據〕`frontend/components/PortfolioPanel.tsx:88-110 recent orders 僅 side/quantity/symbol/price;models.py OrderRecord 欄位無 fee/tax/info;execution.py:115 fee 僅由 result.info 傳入 record_fill,未寫回 OrderRecord`
- **🟡 medium** — Backtest trades 表已顯示 Net PnL 與 Cost(此處做對了),但缺成交品質揭露:無滑價欄、無『決策價 vs 成交價』、亦無『此為 market-only、固定/零滑價、next-bar-open 模擬』的免責標示。Trade 本身也只存 entry_price=fill price(無 decision price),故此揭露需後端配合。使用者無從得知 fill 假設多脆弱,易把樂觀回測當真。
  - 〔證據〕`frontend/components/BacktestPanel.tsx trades 表欄位為 Entry/Exit/Entry px/Exit px/Qty/Return%/Net PnL/Cost——無 slippage / decision-vs-fill 欄,無 fill-model 揭露文案;backtest/engine.py:19-29 Trade 無 decision_price 欄`
- **🟡 medium** — risk_exit 被歸為綠色『下單 Order』節點並以 SL/TP 百分比呈現(category:'order'、title 'Risk Exit (SL/TP)'),視覺上等同保護性停損,但底層是 close-only 評估、next-open 市價成交,無 intrabar 觸發。UI 語意誇大了實際保護力,且與 investor finding 7 的更正一致(漏算 intrabar whipsaw、成交脫離名目停損)。
  - 〔證據〕`frontend/components/workflow/nodeCatalog.ts:65-73 risk_exit category:'order'、params stop_loss_pct/take_profit_pct;對應 workflow/nodes.py:118-164 close-only 評估邏輯`

**重設計提案**

定位 Rework:外圍腳手架正是對的地基——單一 execute_order 路徑、RiskGuard/PortfolioGuard、broker-agnostic FIFO ledger、CostModel 掛勾、no-look-ahead 的單序列『與』多資產 portfolio backtest(workflow_backtest.py + PortfolioSim 已存在,第一版漏記)。要重建的是『成交本身』,分四層下手。

(1) 訂單模型 + 狀態契約(schemas.py / crypto_ccxt.py / execution.py)。OrderType 增 `stop / stop_limit`;OrderRequest 增 `stop_price / time_in_force(GTC/IOC/FOK/DAY) / reduce_only`;bracket/trailing 以『父單+子單』群組(OCO)表達,別硬塞單一 enum。OrderResult.status 改 enum(`new/open/partially_filled/filled/cancelled/rejected`)並拆出 `filled_quantity` 與 `avg_fill_price`(與下單價分離)。同時修掉 live-ledger 靜默繞過:把 execution.py:107 的 `=='filled'` 換成『正規化的終態成交判斷』(把 ccxt 'closed' 映射為 filled),否則 live realized-P&L 永遠是空的。Position 增 `side: long|short` 並允許負 quantity,使 sell-to-open 與 close 可區分。

(2) 撮合與滑價引擎(新 trading/fills.py,paper.py 與兩條 backtest 共用)。limit 必須做 marketability check:買限價僅在 next-open ≤ limit 時成交(成交於 min(open,limit)),否則維持 open;stop 在 bar.high/low 觸發後轉市價(終結 close-only 停損)。滑價改 `spread + size-impact + vol`:以近窗 ATR/已實現波動估 spread,size-impact 隨 `qty/bar.volume` 以平方根衝擊遞增,預設給非零值。關鍵:消除目前 execution.py:67-70 與 paper.py:77-80 兩份重複的 limit 邏輯,paper 與 backtest 共用同一 fills 引擎。

(3) Sizing 引擎(新 trading/sizing.py)。把 order 節點靜態 quantity 換成 policy:`fixed_qty / fixed_risk_pct(由 risk_exit 停損距離反推 qty=risk$/stop_dist) / vol_target / equity_fraction`,並把目前被丟棄的 signal.confidence 餵入。同一 policy 同時驅動 workflow order 節點、單序列 backtest(取代 position_fraction)與 PortfolioSim(取代 equal-weight `per=equity/n`)。

(4) 做空/保證金/組合權重 + 時間軸誠實。PaperBroker 支援負部位與 borrow/維持率;PortfolioSim 支援權重與 short;workflow_backtest 的 _aligned_timeline 交集截斷要 fail-loud 或顯式回報被丟棄的 bar 數,別靜默縮短回測窗。

設計面同步交付三個介面,皆守 DESIGN.md token 規則。

下單 Order 節點 inspector(取代單一 quantity 欄;節點維持 --c-order 綠,cyan 僅留給 AI):
```
下單 Order ───────────────────────
類型  ●市價 ○限價 ○停損 ○停損限價 ○區間bracket
限價  [ 64,200.00 ]   TIF [ GTC ▾ ]   □ reduce_only
方向  ●做多/平倉  ○做空(sell-to-open)   槓桿[1× ▾]
部位大小
  ○固定數量    [ 0.01 ]
  ●固定風險%   [ 1.0% ]  停損距離←risk_exit 節點
  ○波動目標    [ 年化 15% ]
─ 預估 (paper・next-open) ────────────
  ~0.0152 BTC · 名目 ~976 USDT · 費 0.73
  滑價模型 spread+size · ⚠限價以「觸及才成交」撮合
```

送出真實訂單前的 pre-trade ticket(live,DESIGN.md:40-44 --live 粉色 + pulse;名目/費用/現金走 .num tabular,中性數字 --text-muted,僅 LIVE 與維持率告警用 --live/--warning):
```
送出真實訂單   ● LIVE
BUY 0.0152 BTC/USDT  限價 64,200  GTC
──────────────────────────────
名目        976.00 USDT
預估費用      0.73 USDT (taker 7.5bps)
預估滑價      1.95 USDT (size 0.02%+spread)
保證金影響    488 USDT(2×)→ 維持率 162%
帳戶現金      9,024 → 8,536 USDT
──────────────────────────────
[ 取消 ]              [ 送出真實訂單 ▶ ]
```

Backtest trades 表加『決策價→成交價』與『滑價』兩欄(需後端在 Trade 增 decision_price),並於表頭掛一行 fill-model 揭露:`market-only · 滑價模型: spread+size · next-bar open`,讓使用者一眼看穿模擬假設的脆弱處。PortfolioPanel recent orders 加 fee/狀態 badge/type(前提:OrderRecord 先持久化 fee 或 join ledger)。up/down 一律走 token、台股以 data-market="tw" 反轉,cyan 不下放到這些中性資料。

<br>

### D13. 多市場 Brokers & live trading（台股/美股 path to live）

**現況:** Broker ABC seam 乾淨且 fail-loud 誠實,但只有 crypto paper 真正能跑;live 路徑缺 OMS / 成交對帳 / exchange 級冪等 / 精度與 minNotional 處理,而 paper↔live 只是 server 全域 env 的唯讀鏡像、無 per-run 控制也無 arming gate。

**評分:** 投資人 `2/5` · 設計 `2/5`　|　**判決: `Rework`**

**最高槓桿動作:**
- 把 mode 端到端串成權威 per-run 參數(runWorkflow→execute_order→get_broker 帶 mode、_run_order 不再回退全域 env),在 live 下單前加 type-to-confirm 武裝閘,並修掉標籤背離(paper 執行鈕別寫『執行回測』)——capital-safety 第一順位
- 修 live 帳本資料完整性:把 execution.py 的 `status=='filled'` 改成標準化終態(ccxt 'closed' 才是成交),補 OMS 介面(cancel/get_open_orders/get_order)+ APScheduler reconciliation worker(open→filled/partial/canceled 落地補 ledger)
- live 下單前置:CcxtBroker 補 load_markets()+amount_to_precision/minNotional 檢查、把 client_order_id 下推 newClientOrderId 做 exchange 級 exactly-once;registry 改 per-market BROKER_ROUTING(美股先接 Alpaca、台股先接 Shioaji/Fugle,Firstrade 降 opt-in),並開『連線 室』暴露 has_credentials/連線狀態/憑證 server 端保存

**投資人鏡頭 — 發現**

- **🔴 critical** — Trading mode 是 server 全域 env 的單一旗標,而非 per-run 權威參數,且 live 前無任何 arming/二次確認。execute_order(mode=None) 一律回退 settings.trading_mode(registry.py:55),_run_order 刻意不傳 mode,/api/workflows/run 與前端 runWorkflow 都只送 graph。後果不是『看起來像 paper 卻打真實單』(UI 其實會翻成 LIVE chip),而是相反:paper↔live 是全有全無的全域開關——一旦把 server 設成 TRADING_MODE=live 並重啟,所有既有 workflow、所有 schedule 觸發、以及編輯器的 ad-hoc Run 按鈕,全部在零 per-run 確認下同時被武裝成打真實單。對真實資金平台,缺少 per-run 意圖與 arming gate 是第一順位的 capital-safety 破口。
  - 〔證據〕`workflow/nodes.py:198-203 _run_order 呼叫 execute_order 未傳 mode;trading/execution.py:41,48 mode 預設 None → get_broker(market, None);brokers/registry.py:55 mode = mode or settings.trading_mode;api/workflows.py:158-159 /run 只收 graph;frontend/lib/api.ts:416 runWorkflow 只送 graph`
- **🟠 high** — Live 成交永遠進不了 ledger,且 OrderRecord 會留下非 filled 狀態——這是資料完整性的硬傷。execution.py:107 以 `if result.status == "filled"` 作為 record_fill 的唯一閘門,但 ccxt 對『完全成交』的 unified status 是 'closed'(掛單未成交是 'open'),crypto_ccxt.py:156 直接沿用 broker 回傳值,因此任何 live 單(就算是同步成交的 market 單)status 都不會等於 'filled' → record_fill 被跳過 → FIFO realized-P&L ledger 對 live 永遠是空的,OrderRecord 也存著 'closed'/'open' 而非系統他處假設的 'filled'。再加上 limit 單回 'open' 後沒有任何 polling/webhook/reconciliation 把 open→filled/partial/canceled 落地。PaperBroker 永遠硬回 'filled'(paper.py:113)把整個缺口遮蔽,paper 看起來正常,一上 live 就出現幽靈訂單與部位漂移。
  - 〔證據〕`trading/execution.py:107-116(僅 status=='filled' 才 record_fill);brokers/crypto_ccxt.py:156(status=order.get('status') or 'open',ccxt 成交為 'closed' 不會命中);brokers/paper.py:113(永遠 'filled');全 repo 無 reconciliation worker(base.py 連 get_order 介面都沒有)`
- **🟠 high** — 沒有 exchange 層級的 exactly-once。client_order_id 只在『下單前』於 DB 去重(execution.py:52-64),且只有 workflow 路徑會帶(manual orders.py place_order 傳 client_order_id=None,完全不去重)。CcxtBroker.create_order 並未把 clientOrderId/newClientOrderId 下推交易所(crypto_ccxt.py:142-148)。若在『交易所已接受、本地 commit 前』崩潰/逾時,retry 時 DB 查不到紀錄,會在 Binance 重複下一張真實單。真正的冪等需要把 client order id 下推給 broker 並用它查單,目前缺。
  - 〔證據〕`trading/execution.py:52-64(僅 DB 層去重);api/orders.py:26(manual order 無 client_order_id);brokers/crypto_ccxt.py:142-148(create_order 未帶 client order id)`
- **🟠 high** — 沒有 order-management 面,而且這條路徑從介面起就缺。orders.py 只有 POST 下單 / GET 列表 / portfolio / paper-reset,沒有取消單、查 open orders、改單(replace)。Broker ABC(base.py:48-57)只有 create_order/get_balance/get_positions,沒有 cancel_order/get_open_orders/get_order 抽象方法。對 live,『掛單後能查、能取消、能改價』是 table stakes;介面缺則所有 connector 都無從實作。
  - 〔證據〕`api/orders.py 全檔僅 place/list/portfolio/paper-reset;brokers/base.py:48-57 ABC 無 cancel_order/get_open_orders/get_order`
- **🟡 medium** — Live 下單缺交易所精度 / minNotional / lot-size 處理,實質上無法可靠成交。CcxtBroker.__init__ 從不呼叫 load_markets(),create_order 直接把 request.quantity / request.limit_price 原樣丟給 ccxt(crypto_ccxt.py:142-148),沒有 amount_to_precision / price_to_precision,也沒有檢查 market['limits'](minNotional、最小下單量、step size)。在 Binance 上,帶過多小數位或低於 minNotional 的單會被 filter 直接 reject。雖然會 fail loud,但意味著 live 對多數實際下單尺寸根本不可用——這是 live-readiness 的 table-stakes 缺口。
  - 〔證據〕`brokers/crypto_ccxt.py:47-54 __init__ 未 load_markets;crypto_ccxt.py:142-148 create_order 傳原始 quantity/limit_price,無 amount_to_precision/minNotional 檢查`
- **🟡 medium** — 美股 live 預設錨定在最脆弱的路徑(僅為方向性問題,非當下執行風險)。get_live_broker(us_stock) 硬寫回 FirstradeBroker()(無官方 API、靠逆向工程的非官方 library,firstrade.py 自承 fragile),而同檔註解說 YuantaBroker(us_stock) 元大複委託『available』卻沒有任何參數能路由到它——是死碼。注意:Firstrade 與 Yuanta 兩者目前所有方法都 raise NotImplementedError,故今天沒有真實資金風險;問題在於『將來有人接線時會接到錯的、不可信的 broker』,以及缺少官方 API 券商(IBKR / Alpaca / Tradier)的方向設定。
  - 〔證據〕`brokers/registry.py:47-49(us_stock 硬寫 FirstradeBroker,YuantaBroker(us_stock) 無從路由);brokers/firstrade.py:1-6 & 22-26 自承無官方 API、fragile,且全方法 raise NotImplementedError`
- **🟡 medium** — BINANCE_TESTNET 預設 True,使『行情來源』與『下單目標』被同一旗標耦合,且預設破壞 paper 的數據完整性。set_sandbox_mode(True) 會把同一個 CcxtBroker 實例的所有 endpoint(含公開 ticker/OHLCV)切到 testnet(testnet.binance.vision,獨立且稀薄的 order book);這顆 broker 又被當成 PaperBroker(crypto) 的 data_provider。結果預設下 paper 的『真實價格』其實來自 Binance testnet,與 production 偏離——『paper 用真價』的前提被預設組態破壞;而且一個 flag 同時決定了行情源與下單目標,兩者本該分離。
  - 〔證據〕`config.py:54 binance_testnet 預設 True;brokers/crypto_ccxt.py:56-58 set_sandbox_mode 套用全 endpoint;brokers/registry.py:29-30 & 58-60 同一 CcxtBroker 既當 paper 行情源又當 live 下單目標`
- **🟡 medium** — 單租戶、全域明文憑證,無法服務多個真實使用者的 live 帳戶。所有 broker 金鑰來自單一全域 Settings(config.py:52-53 一組 BINANCE 金鑰,Yuanta/Firstrade 同理走 env),CcxtBroker 直接讀全域 settings(crypto_ccxt.py:51-53),沒有 per-user 加密 vault、沒有輪替、沒有 scope 分離。目標若是認真的多市場 live 平台,每位使用者的券商憑證需 server 端加密保管 + 不可回顯,現況連第二位使用者都無從 onboard。
  - 〔證據〕`config.py:52-53 單組全域 BINANCE 金鑰、無 per-user 維度;crypto_ccxt.py:51-53 直接讀 settings 全域金鑰`
- **🟡 medium** — Live 部位成本基礎不可知,本地 ledger 無法與券商對帳。CcxtBroker.get_positions 由 balances 合成 spot 部位且 avg_price 報 0(crypto_ccxt.py:183-194);本地 FIFO ledger 以本地成交價建 lot(execution.py:107-116),一旦走 live、或有 app 外的手動成交,本地成本基礎會與券商真實均價/已實現損益分歧,卻沒有任何 broker→本地的 position/cost-basis 對帳。疊加 finding 2 的 'closed' bug(live 根本不進 ledger),live 的損益帳本實際上既空又無對帳。
  - 〔證據〕`brokers/crypto_ccxt.py:183-194(avg_price=0.0);trading/execution.py:107-116(以本地 result.price 建 ledger,無 broker 對帳)`

**設計鏡頭 — 發現**

- **🟠 high** — IA 完全沒有『連線 / 帳戶 Connections』房間。DESIGN.md:130-145 的左側 tree-menu 在 工具 底下只有 排程 / 通知 / 匯入,沒有任何地方能輸入/管理券商憑證、看連線狀態、切 testnet/live。CcxtBroker 已有 has_credentials(crypto_ccxt.py:64-66)這個事實,卻沒有被任何 api/*.py 暴露(grep 確認 api 層無引用),所以 UI 連『這個市場是否已連上 live』都顯示不出來。對多市場 live 平台,這是 onboarding 的核心缺口。
  - 〔證據〕`DESIGN.md:130-145 nav tree 工具僅含 排程/通知/匯入;brokers/crypto_ccxt.py:64-66 has_credentials 未被任何 api/*.py 暴露`
- **🟠 high** — DESIGN.md:36 承諾的『清楚標示的 toggle』在實作裡不存在——mode 是 server 設定的唯讀鏡像,且 live 前無 arming/二次確認。WorkflowBuilder.tsx:62 `mode = config.data?.trading_mode`,Toolbar 依此把按鈕翻成 pink『▶ 送出真實訂單』(Toolbar.tsx:42,90-92),但點下去送出的 runWorkflow 不帶 mode(WorkflowBuilder.tsx:152-156)。使用者無法在 UI 選擇 paper/live;唯一切換方式是改 server env 重啟。真要打真實單前也沒有任何 type-to-confirm / 風控彙整 / 名目金額揭露的武裝閘。
  - 〔證據〕`frontend/components/workflow/WorkflowBuilder.tsx:62(mode 來自 config 唯讀)、152-156(run 不帶 mode);frontend/components/workflow/Toolbar.tsx:42,90-92;DESIGN.md:36『清楚標示的 toggle』`
- **🟠 high** — paper 模式下 Run 按鈕標示『▶ 執行回測』,實際卻走 live 執行路徑、會下 paper 單並改動已持久化的 paper 帳戶——標籤與行為背離,破壞信任邊界。Toolbar.tsx:92 在非 live 時把按鈕寫成『▶ 執行回測』,但 onRun→api.runWorkflow→/api/workflows/run→run_workflow→_run_order→execute_order(paper)→PaperBroker.create_order 會扣現金/動部位並透過 PaperStore 落地(paper.py:106,_persist);真正的回測是另一顆獨立的『📊 Backtest』按鈕(/api/workflows/backtest)。一個寫著『執行回測』的鈕卻會異動帳戶狀態,對嚴肅平台是會誤導使用者的設計缺陷。
  - 〔證據〕`frontend/components/workflow/Toolbar.tsx:88-93(非 live 標籤『▶ 執行回測』、onRun);WorkflowBuilder.tsx:152-156 run()→api.runWorkflow;api/workflows.py:158-162 /run 走 execute 路徑;brokers/paper.py:106-118 create_order 改帳並 _persist;另有獨立 onBacktest 按鈕(Toolbar.tsx:94-100)`
- **🟡 medium** — 沒有 paper→live 升級流程與安全閘。UI 無法區分『只在 paper 驗證過的 workflow』與『被授權動用真實資金的 workflow』;沒有把 backtest 表現、風控狀態(/api/risk/status 已存在且回傳完整 RiskStatus)、券商連線狀態收斂成一個『可以上 live 嗎?』的 promotion gate。對嚴肅平台,從紙上到真錢那一步必須是有阻力、有檢核清單的流程,而非顏色變化的按鈕。
  - 〔證據〕`無對應前端流程;api/risk.py:25-66 RiskStatus 已含 kill_switch/halted/exposure_base/orders_today 可餵 gate,但未被用於任何升級流程`
- **🟡 medium** — live 連線的 error/empty/loading 狀態無人設計。當 get_data_broker/get_live_broker 對台股/美股丟 NotImplementedError、或 CcxtBroker 缺金鑰時,orders.py 只是把 501/502 與原始 detail 字串丟回前端,沒有任何『此市場尚未連線,點此設定』的引導面。使用者撞到的是裸 error,而非引導他去連線/匯入 CSV 的狀態。
  - 〔證據〕`api/orders.py:29-32(501/502 raw detail);brokers/registry.py:33-39 & yuanta.py:43-56 / firstrade.py:37-50 對 stock live 直接 raise NotImplementedError`

**重設計提案**

把這個 domain 從『一條能跑的 crypto paper + 一堆誠實空殼』重做成『一條可信的多市場 live 骨幹』,五件事:\n\n1) 讓 mode 變成權威控制,而不是鏡像。RunResult / runWorkflow 帶 `mode: 'paper' | 'live'`,一路傳到 execute_order(..., mode=mode) → get_broker(market, mode);_run_order 不再回退全域 env。前端 toggle 從『讀 config』改成『使用者選擇 + 二次武裝』。同時修掉標籤背離:paper 的執行鈕改名(例如『▶ 模擬下單 paper』)以免與『📊 Backtest』混淆——一個會異動帳戶的鈕不該寫『執行回測』。\n\n2) 在 live 下單前插一個 type-to-confirm 武裝閘:輸入市場代號才解鎖,並把『券商連線狀態 + 今日風控(/api/risk/status:kill_switch/halted/orders_today/exposure_base)+ 本次預估名目金額』攤在同一張卡上。pink --live(#FB7185)只在『真正會打真實單』時亮,顏色與行為對齊;--accent 不出現在這裡(非 AI)。\n\n3) 在 Broker ABC 補上 OMS 介面:cancel_order / get_open_orders / get_order(對帳)。新增 reconciliation worker(掛在既有 APScheduler 上)輪詢 open orders,把 open/closed/partial/canceled 落地、補回 ledger;修掉 execution.py 的 `== \"filled\"` 判斷,改用 OrderResult 的標準化終態(ccxt 'closed' = 成交)決定 record_fill。CcxtBroker.__init__ 補 load_markets() 並在 create_order 用 amount_to_precision / price_to_precision + 檢 minNotional;把 client_order_id 下推 newClientOrderId、retry 先查單,做 exchange 層 exactly-once。\n\n4) 重新錨定可信 live brokers,並讓路由可設定。新增 AlpacaBroker(美股,有官方 paper endpoint,最適合當『美股 live 第一步』)與 Shioaji / Fugle(台股,官方 Python API 比元大複委託成熟);registry 改成 BROKER_ROUTING 設定表(per-market 指定 provider),Firstrade 從預設降為 opt-in 實驗路徑。把 BINANCE_TESTNET 從『耦合行情+下單的單一 flag』拆成 data_source vs execution 兩個維度,讓 paper 預設用 production 行情。\n\n5) 新增『連線 室』(IA 第三類)。nav tree 在 工具 之上新增 🔌 連線,每市場一張 connection 卡;憑證 server 端保存、永不回顯(只顯示尾碼)。\n\n連線室 mock(深色終端機、tight radii、tabular-nums、--accent 不用於此):\n\n┌─ 🔌 連線 ────────────────────────────────────────────┐\n│  市場          狀態           模式        帳戶                │\n│  ──────────────────────────────────────────────────   │\n│  ● crypto      ✓ 已連線       [testnet▼]  Binance ····3f2a  │\n│      行情 production · 下單 testnet  ⟳ 12s 前對帳            │\n│      [中斷] [輪替金鑰]                                       │\n│  ──────────────────────────────────────────────────   │\n│  ◑ 台股        ⚠ 未連線       —           Shioaji(永豐)     │\n│      尚未設定憑證 · paper 可用(CSV 匯入)                    │\n│      [連線 Shioaji →]                                       │\n│  ──────────────────────────────────────────────────   │\n│  ○ 美股        ⚠ 未連線       —           Alpaca / IBKR     │\n│      [連線 Alpaca →]   Firstrade(實驗)⌄                    │\n└──────────────────────────────────────────────────────┘\n\n狀態點走 status token(✓ 走 --up 之外的中性 success、⚠ 走 --warning),不挪用 --accent。live 武裝閘 mock(邊框 --live):\n\n┌─ 送出真實訂單前 · LIVE 武裝 ──────────────┐\n│  市場 crypto · Binance(production)          │\n│  風控 ✓ 未觸發 · 今日 3/50 單 · 曝險 420k/1M │\n│  本次預估名目 ≈ 38,500 TWD                    │\n│  輸入「BTC/USDT」以解鎖 ▸ [____________]      │\n│           [取消]   [● 武裝並送出]            │\n└────────────────────────────────────────────┘\n\n如此 paper↔live 的邊界第一次變成『程式上真實、UI 上不可繞過』,而非顏色裝飾;live 帳本也第一次真的會記到成交。

**本域新功能提案**

- **權威 mode + LIVE 武裝閘** `(M)` — 把 trading mode 從全域 env 提升為 per-run 參數,端到端傳遞(runWorkflow→execute_order→get_broker);前端在送真實單前加 type-to-confirm 武裝閘,彙整 /api/risk/status、券商連線狀態、預估名目金額;並修正 paper 執行鈕的誤導標籤。　_為何重要:_ 目前 UI 的 LIVE 切換只是 server env 的唯讀鏡像,且 paper Run 鈕寫『執行回測』卻會動帳戶;改 server 旗標即一次武裝所有 workflow+schedule,是會誤打真實單的 capital-safety 破口。
- **Live OMS + Reconciliation 層** `(L)` — 在 Broker ABC 增 cancel_order/get_open_orders/get_order;修 execution.py 的成交判斷(ccxt 'closed'=成交)讓 live 真的進 FIFO ledger;加 APScheduler 對帳 worker 把 open→filled/partial/canceled 落地補 ledger,並把 client_order_id 下推交易所做 exactly-once。　_為何重要:_ 現況 `status=='filled'` 永遠不命中 live 單(ccxt 回 'closed'/'open'),live 成交既不進 ledger、OrderRecord 又留錯狀態;limit 永卡 open、partial 無人處理、retry 可能重下真實單;PaperBroker 永遠 'filled' 把缺口遮蔽。
- **可信 broker connectors + 精度/路由表** `(XL)` — 新增 AlpacaBroker(美股,含官方 paper)、Shioaji/Fugle(台股);CcxtBroker 補 load_markets()+amount_to_precision/minNotional;registry 改 BROKER_ROUTING 設定表,Firstrade 降為 opt-in;BINANCE_TESTNET 拆成 data_source vs execution 兩維度。　_為何重要:_ get_live_broker 目前把美股 live 硬寫到無官方 API 的 Firstrade、YuantaBroker(us_stock) 是死碼;且 live 下單缺交易所精度/minNotional 會被 Binance reject;testnet 旗標還把 paper 行情污染成 testnet 價。
- **連線 室(Connections IA + 憑證安全 UX)** `(L)` — nav 新增『🔌 連線』房間,每市場一張 connection 卡:狀態/testnet-live/server 端保存且不回顯的憑證/對帳時間/中斷與輪替;後端把 has_credentials 與連線狀態以 API 暴露。　_為何重要:_ 目前無任何前端面能輸入憑證或看連線狀態(has_credentials 也沒被 API 暴露),live onboarding 與 paper→live 升級無從進行;撞到的只有 orders.py 丟回的裸 501/502。

<br>

### D14. 全景新功能 Full-vision NEW features(serious multi-market live platform gaps)

**現況:** 這是一套扎實的「策略設計 + 回測 + 紙上交易」引擎,但幾乎缺席整個「真錢營運層」— 沒有對帳、沒有 live 績效歸因、沒有上線治理、沒有稽核、沒有資料品質與公司行動調整,live 仍只是一個全域 env 開關。

**評分:** 投資人 `2/5` · 設計 `2/5`　|　**判決: `Add`**

**最高槓桿動作:**
- 券商對帳(Broker Reconciliation):在 Broker 抽象加 fetch_open_orders/fetch_my_trades/fetch_account_state,把內部 OrderRecord/positions 與交易所實際回報 diff 並 fail-loud。這是唯一直接危及資本與資料完整性的缺口 — 真錢交易前必須先讓帳本與交易所一致。
- Paper→Live 上線審核 Gate:把 live 從全域 env 升級為 per-workflow 治理狀態機(門檻取自既有 walk-forward/metrics),通過才解鎖 btn-live、核准入稽核。這是與產品身分對齊、目前完全缺席的治理防線。
- 監控室三件套:Live 績效分析與策略歸因(補 RealizedPnL→strategy 外鍵 + equity 時序)、不可竄改稽核日誌、資料品質 + 公司行動調整 — 把『投組』從快照升級為分析室,並讓 live broker 從內部帳本變成可被信賴。

**投資人鏡頭 — 發現**

- **🔴 critical** — 沒有 broker reconciliation(對帳)。平台內部狀態(OrderRecord、PaperPosition、PortfolioView)與交易所/券商實際回報的餘額/部位/成交完全沒有比對。唯一真正可跑的 live 路徑(crypto via CcxtBroker)有 fetch_balance,但沒有任何 endpoint/排程把內部 OrderRecord 與 live fills/balances 做 diff,無法偵測孤兒單、部分成交、被拒單、手續費漂移、內外部位漂移。對真錢而言,不知道自己真實部位等於盲飛 — 這是唯一直接危及資本與資料完整性的缺口。
  - 〔證據〕`api/orders.py:portfolio() 全由內部 broker 狀態(build_portfolio)建構;brokers/base.py:Broker 抽象只有 create_order/get_balance/get_positions,無 fetch_open_orders / fetch_my_trades / reconcile;crypto_ccxt.py:166 有 fetch_balance 卻無人拿來與內部 OrderRecord 對帳。`
- **🟠 high** — 沒有 paper→live promotion gate。是否下真單由單一全域 env(settings.trading_mode)決定;workflows.py:_persist_live_run 直接以全域 trading_mode 當 run kind,orders.py:place_order 直接呼叫 execute_order,沒有 per-workflow 的治理(最少 paper 天數/交易數、OOS 門檻、maxDD 上限)。env 一旦翻成 live,任何已存 workflow 即可送真單。這與產品核心身分(paper 為安全預設、live 必須慎重)正面衝突。
  - 〔證據〕`api/workflows.py:143 kind=settings.trading_mode;api/orders.py:26 execute_order 無 per-workflow gate;trading/risk.py 只管 exposure/daily-loss/kill-switch,不評估『這個策略夠不夠格上線』;無任何 gate model/endpoint。`
- **🟠 high** — Live/paper 帳戶沒有績效時間序列與策略歸因(attribution)。回測有完整 Sharpe/Sortino/Calmar/maxDD(metrics.py),但真實帳戶只有一張快照,且資料模型上根本無法歸因:RealizedPnL 只有 market/symbol/lot_id,沒有 workflow_id / strategy_id / run_id,無法 join 回是哪個 strategy 賺賠;WorkflowRun 的 equity_curve_json 對 live/paper 一律為 null。嚴肅交易者無法量測真錢表現。
  - 〔證據〕`trading/portfolio.py:PortfolioView 僅 cash/positions/positions_value/equity;models.py:RealizedPnL(L116-134)無策略/run 外鍵;models.py:WorkflowRun 註解明示 live/paper 的 metrics/equity/trades『stay null』。`
- **🟠 high** — 股票資料沒有公司行動調整(splits / dividends / 台股除權息)。匯入路徑 parse_csv 只存原始 OHLCV,無拆分/配息回溯調整,也無調整係數欄位 — 跨除權息或分割點的 台股/美股 回測與 live 估值會出現假性跳空,污染績效與訊號。多市場平台這是 data-integrity 等級的硬傷。
  - 〔證據〕`brokers/market_data.py:parse_csv 僅解析 timestamp,open,high,low,close[,volume];grep split/dividend/adjust/corporate 在 market_data.py 全無;且 _store 為 process-local(restart 即清),股票歷史本身也未持久化。`
- **🟠 high** — 沒有訂單生命週期管理(open orders / cancel / amend / partial fills / 進階單型)。OrderRecord 是單一終端記錄,沒有『working/open order』概念,沒有取消或改單 endpoint,也沒有部分成交回補。對 live 限價/條件/掛單交易這是必備;現況市價即發即忘無法經營真實掛單簿。
  - 〔證據〕`api/orders.py 只有 place_order/list_orders/portfolio/paper-reset,無 GET open-orders 或 DELETE/PATCH order;models.py:OrderRecord 只有終端 status,無 working/filled_qty/remaining_qty;Broker 抽象無 cancel_order。`
- **🟠 high** — 沒有 immutable audit log。誰、何時、為何下單/觸發 RiskGuard 否決/engage kill-switch/resume/改策略,全無不可竄改軌跡。kill-switch 與 halted 直接覆寫 RuntimeFlag,不記 actor 也不留歷史。真錢出事時無法回放,也無法支撐多人/合規場景。
  - 〔證據〕`models.py 只有 RunLog(status+detail JSON)與 OrderRecord;trading/runtime_state.py:_set 對 RuntimeFlag 就地覆寫無歷史;api/risk.py:set_kill_switch/resume 不記錄 actor;execute_order 的 RiskGuard 否決也未留稽核列。`
- **🟠 high** — 沒有資料品質監控(data-quality / feed health)。candle 取得路徑無 gap/staleness/重複/異常跳動檢測;portfolio.py 取不到價時靜默回退 avg_price(雖標 price_source=avg_fallback)但無人聚合監控;近期才修 candle rollover 崩潰(4c24810)顯示 feed 脆弱。髒資料下真單是直接虧損來源。
  - 〔證據〕`api/markets.py:get_ohlcv 直接回傳 broker candles,無完整性檢查;trading/portfolio.py:38-40 以 source='avg_fallback' 靜默回退;無 feed-health endpoint/聚合。`
- **🟡 medium** — 沒有獨立的 alerts / conditions 引擎。條件邏輯只存在於 workflow 的 condition node,且只能靠 schedules 以整張 workflow 為單位定時觸發 — 想要『BTC 跌破 X / RSI<30 / 回撤>Y 時通知我』必須建並排程一整張 workflow。這是 TradingView/3Commas 的 table-stakes,也是 live 風控(回撤/部位異動)的耳目。
  - 〔證據〕`api/notifications.py 只有 list + test;無 alert-rule 表/評估器;條件能力綁死 workflow/schema.py:NodeType.condition,經 schedules.py 的 interval/cron 整圖觸發。`
- **🟡 medium** — 多策略資金配置只有等權重原型,缺可配置政策。backtest/portfolio.py:PortfolioSim 已實作『共享資金池 + 等權(1/N)再平衡 + 成本感知 fill』並由 /api/backtest/workflow 暴露 — 但僅等權、long/flat、無可設定權重、無再平衡頻率、無相關性感知 sizing、無 per-strategy 資本配置,也無 live 端配置層。要成為 Composer 式投組平台,需在既有引擎上加配置政策層。
  - 〔證據〕`backtest/portfolio.py:target_quantities 寫死 per=equity/n(等權);workflow_backtest.py:103 sim.rebalance 每根對齊 bar 全再平衡;api/backtest.py:BacktestRequest/StrategyBacktestRequest 仍為單 strategy + 純量 position_fraction。`
- **🟡 medium** — 沒有 screener / scanner。只能交易/回測已知或已 CSV 匯入的 symbol;無 universe 概念、無跨 symbol 條件掃描。嚴肅多市場平台把 scanner 當每日主力面板與策略點子源頭。
  - 〔證據〕`api/markets.py 只有 per-symbol ticker/ohlcv/import/imported;無 universe 或 scan endpoint。`
- **🟡 medium** — 策略沒有版本控管,且 live 會在執行時即時載入當前 spec。StrategyDef 就地覆寫(update_strategy),而 workflow 的 strategy node 以 strategy_id 在 run 時呼叫 load_spec — 代表正在跑的 live/排程 workflow 的策略可被底層無聲改掉。這同時破壞資本安全與可重現性。
  - 〔證據〕`strategies/library.py:update_strategy 直接覆寫 spec_json,無版本/歷史;workflow/nodes.py:97-106 strategy node 以 strategy_id 在執行時 load_spec(ctx.session, ...);models.py:StrategyDef 無 version 欄。`
- **🟡 medium** — 稅務/報表單一管轄、缺持有期維度。已有正統 FIFO(Lot)+ 台股證交稅,但 RealizedPnL.tax 僅 tw_stock,且無短/長期持有分類、無美股 wash-sale/1099、無 per-jurisdiction 處理。多市場下這層不足以真正報稅。
  - 〔證據〕`api/ledger.py 僅 RealizedPnL FIFO 聚合 + realized_pnl.csv;models.py:RealizedPnL 註解 tax='證交稅 (tw_stock only)',無 holding-period / jurisdiction 欄。`
- **🟡 medium** — 沒有 trade journal / 交易後復盤。OrderRecord(成交)與 WorkflowSignal.trace_json(產生訊號的軌跡)都在,但兩者間無明確外鍵把 fill 反查回觸發 signal,也無註記/標籤/R-multiple/MAE-MFE 模型。系統化與裁量交易者的改進迴圈缺一塊。
  - 〔證據〕`models.py:OrderRecord 有 client_order_id,WorkflowSignal 有 order_node_id/trace_json,但 RealizedPnL/OrderRecord 與 WorkflowSignal 之間無 FK;無 journal/annotation 表或 fill→signal 反查 endpoint。`

**設計鏡頭 — 發現**

- **🟠 high** — 整個 IA 沒有『營運/監控』的家。nav.ts 只有 策略室/交易室/市場/投組/工具,frontend/app/(rooms) 下實際只有 strategy-lab/trading-room/market/portfolio/schedules/notifications/data-import — 對帳、稽核、資料品質、即時績效、警示這些 live 平台主面板在導覽上完全沒有落點,使用者無從對真錢建立信任。
  - 〔證據〕`frontend/lib/nav.ts:12-42 五個頂層項目;ls app/(rooms) 無 ops/recon/audit/alerts/analytics 路由。`
- **🟠 high** — 投組是快照而非分析室,資訊密度遠低於 refined-terminal 應有水準。DESIGN.md 標榜 Bloomberg 級資料密度與 precision instrument,但 portfolio 能呈現的只有 cash/部位/未實現損益,沒有 equity curve、歸因、benchmark 對照的資料基礎(後端 PortfolioView 即為快照型,WorkflowRun 對 live equity 為 null)。
  - 〔證據〕`trading/portfolio.py:PortfolioView 為快照;DESIGN.md L13/L49『data-dense / precision instrument』;無 live 時間序列可畫。`
- **🟠 high** — paper↔live 信任邊界有強視覺規格,卻無對應的『治理/上線審核』介面。DESIGN.md L40-43 與 Workflow Builder 段詳述 LIVE banner、btn-live、pulsing 指示,但邊界在互動上只是一個二元 toggle,缺少把『為何此策略可上線』講清楚的 checklist/gate 畫面 — 視覺嚇阻有了,程序信任沒有。
  - 〔證據〕`DESIGN.md L40-43 + L194-197 規範 live 視覺;後端僅 settings.trading_mode 單一全域開關,無 promotion/gating 畫面或 endpoint。`
- **🟡 medium** — 通知是被動 feed,沒有警示作者化(alert authoring)介面。使用者無法在 UI 建立『條件→通知』規則,只能看已發生通知或按 test;無 drawdown/部位告警的設定面板。
  - 〔證據〕`frontend/app/(rooms)/notifications 對應 api/notifications.py 僅 list + test;無 alert-rule 建立 UI。`
- **🟡 medium** — 沒有 server-push(WebSocket/SSE)層,live 終端機在感知上是靜態的。backend main.py 只掛 REST 路由,唯一 streaming 是 ledger 的 CSV 下載;live 部位/PnL/成交/警示全靠 client 輪詢。DESIGN.md 期望 price tick flash 與 LIVE pulse 的即時感,但缺低延遲推送基礎,真錢場景的回饋延遲與陳舊風險偏高。
  - 〔證據〕`backend/app/main.py:49-58 僅 include REST routers;grep websocket/SSE/text-event-stream 全無(除 ledger.py 的 CSV StreamingResponse);市場 live 更新近期才修 candle rollover 崩潰(4c24810)。`

**重設計提案**

## 從「兩室」擴成「三室 + 升級的投組室」:給 live 營運一個家

現況 IA(nav.ts)是 策略室(設計)/ 交易室(執行)/ 市場 / 投組 / 工具。所有 live 營運面板(對帳、稽核、資料品質、即時績效、警示、掛單簿)在導覽上無處可放,這是嚴肅 live 平台最大的結構缺口。提案:新增第三個頂層房間 **監控室(Operations)**,把投組升級為分析室,並在交易室的 paper↔live 邊界插入 **上線審核** gate。所有新面板沿用 DESIGN.md 既有 token、tight radii、mono tabular-nums;cyan 僅限 AI、真錢列只給 --live。

### 擴充後的左側樹狀導覽(沿用 DESIGN.md L130 風格)
```
AI Trade Flow.
├─ 🧪 策略室        ← 不變(設計 + 策略庫;版本歷史新增於此)
├─ 🔀 交易室
│  ├─ 模擬回測
│  ├─ 工作流
│  └─ 上線審核 ●LIVE   ← 新:promotion gate(--live dot,過關才解鎖 btn-live)
├─ 📈 市場
│  ├─ 行情
│  └─ 掃描          ← 新:Screener/Scanner
├─ 👛 投組          ← 升級:快照 → 分析室(equity 曲線 + 策略歸因)
├─ 🛰 監控室         ← 新房間:live 營運中樞
│  ├─ 即時績效       ← Live Analytics & Attribution
│  ├─ 對帳          ← Broker Reconciliation(內外 diff)
│  ├─ 掛單簿        ← Order blotter(open/partial/cancel)
│  ├─ 警示          ← Alerts Engine(規則作者化)
│  ├─ 資料品質       ← Data-Quality + Corporate Actions
│  └─ 稽核日誌       ← Audit Log
└─ 🔧 工具(排程 / 通知 / 匯入)
```
監控室 icon 用 --text-faint(非 AI 不得用 cyan);任何牽涉真錢的列(對帳不一致、稽核中的 live 事件、未平掛單)用 --live dot,沿用 DESIGN.md L155 危險房間可讀性規則。

### 上線審核 Gate(交易室內,paper→live 邊界的程序信任)
DESIGN.md 把 live 的「視覺嚇阻」規範得很足(LIVE banner、btn-live、pulsing),但缺「程序信任」。Gate 用一張 checklist 把「為何此策略可上線」講清楚,全部通過前 btn-live 維持 disabled:

```
┌─ 上線審核 · 工作流「BTC RSI 反轉」 ──────────────── 交易室 ─┐
│  狀態  paper ▸ 待審核                                       │
│  ✓ paper 運行  14 / 14 天          達標                     │
│  ✓ 最少交易數  37 / 30             達標                     │
│  ✓ OOS Sharpe  0.82 / ≥0.50       達標   (來自 walk-forward) │
│  ✗ 最大回撤    −24.1% / ≤ −20%    未達   ←  紅 --error       │
│  ☐ 已閱讀並同意 live 風險揭露                                │
│  [ 仍無法上線:1 項未達門檻 ]      ▸ 送出上線申請(disabled)  │
└────────────────────────────────────────────────────────────┘
```
門檻可設;OOS Sharpe / maxDD 直接取自既有 backtest/validation.py(walk_forward)與 metrics.py — 不重造輪子,而是把現成統計誠實度接到上線決策;核准寫入稽核日誌(who/when)。

### 投組分析室(快照 → 密集分析,對齊 refined-terminal)
PortfolioView 目前只有快照、且 RealizedPnL 無策略外鍵。升級需先在 RealizedPnL/OrderRecord 補 run_id/strategy_id,再上半畫 equity 曲線(vs Buy&Hold,用 --up/--down 且尊重 data-market="tw" 反轉),下半左部位表(tabular-nums、scroll-x 不 reflow,DESIGN.md L176),下半右 **策略歸因** 長條:

```
┌ 即時績效 ── paper ───────────────────────────────────────┐
│ equity  142,380   ▴ +2.1% 今日    Sharpe 1.31  maxDD −18.4% │
│ ╭──────────────── equity curve ── vs Buy&Hold ─────────╮   │
│ │   ____╱╲╱╲__╱╲__╱      (--up 線;benchmark 灰虛線)      │   │
│ ╰────────────────────────────────────────────────────────╯ │
├ 部位 ───────────────────────┬ 策略歸因(realized) ─────────┤
│ BTC/USDT  0.42  +1,204 ▴     │ RSI 反轉   ████████  +3,120   │
│ ETH/USDT  3.10  −   88 ▾     │ MA cross  ███       +  910   │
│ …(scroll-x)                 │ AI signal █▌        −  420 ▾ │
└──────────────────────────────┴──────────────────────────────┘
```

### 為何這組合是對的
- 投資人視角:對帳 + 即時績效/歸因 + 上線治理 + 稽核/資料品質,正好補上「能不能信任它下真錢」的缺口,且全部站在既有扎實資產(metrics.py、validation.py、PortfolioSim、RealizedPnL FIFO、RiskGuard、ccxt fetch_balance)之上延伸,而非另起爐灶。
- 設計視角:新增一個房間 + 升級一個房間,完全不破壞 two-room 心智模型;cyan 仍只給 AI、真錢列只給 --live,維持 DESIGN.md 的色彩紀律與終端機密度。

**本域新功能提案**

- **券商對帳儀表板(Broker Reconciliation)** `(L)` — 在 Broker 抽象新增 fetch_open_orders / fetch_my_trades / fetch_account_state,定期把交易所/券商實際回報與內部 OrderRecord/positions diff,標出孤兒單、部分成交、被拒單、手續費漂移、內外部位不一致;不一致超閾值時 fail-loud 告警並可選自動暫停下單(沿用既有 kill-switch)。　_為何重要:_ 唯一真正可跑的 live 路徑(crypto via ccxt,已有 fetch_balance)目前完全不對帳,內部狀態一旦與真實持倉漂移,風險與績效全錯。這是把 live broker 從『內部帳本』推向可信賴的前提,也是唯一直接危及資本的缺口。
- **Paper→Live 上線審核(Promotion Gate)** `(L)` — 把 live 從全域 env 升級為 per-workflow 治理狀態機:每張要上線的 workflow 須通過可設定門檻(最少 paper 天數/交易數、OOS Sharpe、maxDD 上限、近 N 日 paper 與回測一致性、強制風險揭露勾選),全通過才在 UI 解鎖 btn-live;核准事件寫入稽核軌跡(who/when)。門檻直接取自既有 validation.py(walk-forward/OOS)與 metrics.py。　_為何重要:_ 現況 env 一翻成 live,任何已存 workflow 即可送真單(workflows.py 用全域 trading_mode)。這是與產品身分(paper 安全預設、live 慎重)直接對齊、且完全缺席的治理防線,不重造輪子而是把現成統計誠實度接到上線決策。
- **Live 績效分析與策略歸因(Live Analytics & Attribution)** `(L)` — 對 paper/live 帳戶定時 snapshot equity 形成時間序列,套用既有 metrics.py 算 live Sharpe/Sortino/maxDD;並在 RealizedPnL(及 OrderRecord)補上 run_id/strategy_id 的 join key,做 per-strategy/symbol/market 損益歸因與 vs Buy&Hold benchmark。把『投組』從快照升級為分析室。　_為何重要:_ 你無法經營一個量不到的帳戶。回測指標完整、真錢卻只有快照,且 RealizedPnL 連歸因的外鍵都沒有 — 這是嚴肅交易者最先質疑的落差,也是 live 留存與資本配置決策的核心。
- **稽核與營運可觀測性(Audit Log + Observability)** `(M)` — 新增 append-only AuditEvent 表 + middleware,記錄每筆下單、RiskGuard 否決、kill-switch engage/resume、設定與策略變更的 who/when/why/before-after;搭配一個 ops 時間軸面板。讓 runtime_state 的 kill-switch/halted 與 execute_order 的風險決策都留痕。　_為何重要:_ 真錢出事要能回放『當時發生什麼、誰按了什麼』。現況只有 RunLog 的 status+detail,RuntimeFlag 就地覆寫不留 actor。沒有不可竄改稽核,既無法事後復盤也無法支撐合規/多人場景。
- **資料品質與公司行動調整(Data Quality + Corporate Actions)** `(M)` — (1) 在 candle 取得路徑加入 gap/staleness/重複/異常跳動檢測,聚合每個 market×symbol 的 feed 健康(最後更新、缺口數、avg_fallback 命中率),異常 fail-loud 並可阻擋以髒資料下單;(2) 為股票 CSV 匯入加入 split/dividend/除權息回溯調整與調整係數欄,並把匯入歷史持久化(現為 process-local)。　_為何重要:_ live 決策只能跟乾淨資料一樣可靠。portfolio.py 已會靜默回退 avg_price 卻無人監控;股票未做公司行動調整會在除權息/分割點製造假跳空,污染 台股/美股 回測與估值 — 兩者都是直接的 data-integrity 風險。
- **訂單生命週期與進階單型(Order Lifecycle & Advanced Orders)** `(L)` — 在 Broker 抽象與 OrderRecord 上引入 working/open order 狀態、filled/remaining 量、cancel/amend endpoint 與部分成交回補;支援 limit / stop / OCO 等單型,前端提供 live order blotter(掛單簿)。　_為何重要:_ 現況市價即發即忘、單一終端記錄,無法管理真實掛單。serious live 跨市場交易(限價/條件單、部分成交、取消改單)沒有訂單生命週期等於只能盲打市價單。
- **警示引擎(Standalone Alerts Engine)** `(M)` — 獨立 alert-rule 表 + 評估器,複用 condition 語意(price/indicator/portfolio drawdown/部位變動)但不需建整張 workflow;命中即經 notify 服務發送,並可作為 promotion/kill-switch 的訊號源。前端在『通知』加上規則作者化介面。　_為何重要:_ 輕量條件→告警是 TradingView/3Commas 的 table-stakes,現況要監看一個價位都得建+排程一張 workflow(schedules 整圖觸發),門檻過高;也是 live 風控(回撤/部位異動)的耳目。
- **可配置資金配置政策(Allocation Policy on PortfolioSim)** `(L)` — 在既有 PortfolioSim(已具共享資金池 + 等權再平衡 + 成本感知 fill)之上加配置層:可設定權重(等權/風險平價/自訂)、再平衡頻率、(選配)相關性感知 sizing 與 per-signal 風險化 position sizing,並把同一政策套到 live。　_為何重要:_ 等權原型已存在且已暴露於 /api/backtest/workflow,但缺政策化 — 嚴肅資產配置者要的是『一籃子策略的權重與再平衡』。在現成引擎上加政策層即可從『策略測試器』躍遷到『投組平台』,故 effort 為 L 而非從零的 XL。
- **市場掃描器(Screener / Scanner)** `(L)` — 引入 symbol universe 概念,提供跨 symbol 的條件掃描(指標/量能/型態/相對強弱),命中清單一鍵帶進回測或 workflow;掛在『市場』下作為主面板。　_為何重要:_ 現況只能操作已知或已匯入的 symbol(markets.py per-symbol),沒有發現新機會的入口。Scanner 是多市場平台把使用者每天留在產品裡的主力面板,也是策略點子的源頭。
- **策略版本控管(Strategy Versioning)** `(M)` — StrategyDef 由就地覆寫改為帶版本歷史,workflow 的 strategy node 釘選版本;編輯產生新版,正在跑的 live/排程 workflow 不被底層無聲改動,可 diff/回滾。　_為何重要:_ nodes.py 在 run 時以 strategy_id 即時 load_spec,而 library.update_strategy 就地覆寫 — live 中策略可被無聲改變,同時破壞資本安全與可重現性。版本釘選是讓 backtest↔live 可信、事故可回溯的基礎工程。
- **多市場合規與微結構規則(Compliance & Microstructure)** `(L)` — 在 order 路徑前置 per-market 規則:台股 tick size/最小張數/漲跌停、美股 PDT 與 wash-sale 提示、crypto 最小下單量;並在首次啟用 live 前加風險揭露/免責同意 gate。稅務側補持有期(短/長期)與 per-jurisdiction 處理。　_為何重要:_ 認真做 台股/美股 必須編碼各市場規則,否則 live 單會被拒或違規;現況完全無微結構與合規層,是跨市場 live 上線的硬阻擋。

<br>

---

## 5. 北極星 IA / UX North-Star

### 5.1 兩室還撐得住嗎?

兩室的「心智模型」存活,但兩室的「字面 nav」在 full multi-market LIVE 規模下不成立——必須從 2-room 演進為「設計 → 驗證 → 營運」三段脊椎,外加一條跨頁常駐的 Global Context Bar。

理由很乾脆:現行 策略室(設計)/ 交易室(回測+工作流=測試)這條二分法,完整涵蓋了「真錢上線前」的一切,卻完整漏掉了「真錢上線後」。一個 serious live 平台的營運活動——對帳(reconciliation)、即時風控、下單簿(open orders / cancel / amend)、稽核軌跡、資料品質、bot 健康監控——在本質上不是「設計」也不是「測試」,而是「監看與控制正在動用的資本」。把它硬塞進 交易室,等於把平台最攸關安危的表面埋進一個以「編排與回測」為心智框架的房間;而證據顯示,目前它們不是被埋,是根本不存在於 IA(風控 frontend 命中 0 次、ledger 無 nav leaf 也無 api client 方法、reconciliation 是被點名為唯一直接危及資本的 critical 缺口)。

所以:保留兩室作為「上線前」的脊椎(策略室=設計、交易室=驗證/佈署),新增第三個一級房間 監控室(Operations)作為「上線後」的營運中樞,並把 paper↔live 的信任邊界從「頁面內的一顆變色按鈕」升級為「交易室→監控室 交接處的 上線審核 gate + 全域 Context Bar」。兩室沒有被推翻,而是長出了它原本缺的下半身。

### 5.2 提議的北極星資訊架構

北極星 IA:沿用 DESIGN.md 既有的「左側 collapsible tree-menu + slim top bar」骨架與 lucide-icon / cyan=AI / live=--live dot 規則,但 (1) 把 top bar 的空殼(目前只有 ThemeToggle + 文件連結)升級為跨頁常駐的 Global Context Bar,(2) 兩室 → 三室,(3) 把所有資本安全表面拉成一級。

```
┌ Global Context Bar — 每一頁常駐(改寫 TopBar.tsx 的 ml-auto 空殼,落實 DESIGN.md L116)─────┐
│  ☰  ATF.   [ crypto ▾ ]   ┃ ● paper ┃   權益 1,284,503 TWD   ▴ +0.82%  今日 +8,420      │
│            └全域 data-market └LIVE 時轉 --live + 脈動(唯一刻意動畫) .num tabular(--up/--down)│
│            風控 ● OK     連線 ● ok      ( 🔔 3 )      [◐ 主題]      文件中心 ↗            │
│            └/api/risk/status └broker health └Alert Center 未讀=最高 severity 色               │
└────────────────────────────────────────────────────────────────────────────────────────────┘

AI Trade Flow.
│
├─ 🧪 策略室  Strategy Lab — 設計 (ai · FlaskConical)
│  ├─ 與 AI 設計策略             cyan AI leaf
│  ├─ 策略庫                     └─ saved strategies · v3↰v2↰v1 immutable lineage / diff
│  └─ 掃描 Scanner  ▸NEW         universe 條件掃描 → 一鍵帶進回測/工作流(策略點子源頭)
│
├─ 🔬 交易室  Trading Room — 驗證 / 佈署 (Network)
│  ├─ 模擬回測                   single·compare·optimize·walk-fwd · 持久化 Run Registry
│  ├─ 工作流                     canvas(編排;type-safe ports;paper 與 live 佈署皆從此 author)
│  └─ 上線審核 ●  ▸NEW           Promotion Gate(--live dot)— paper→live 唯一閘門,過關才解鎖 btn-live
│
├─ 🛰 監控室  Operations — 營運真錢 ▸NEW ROOM (Gauge / RadioTower · icon 用 --text-faint)
│  ├─ 總覽                       running bots 健康 · schedule heartbeat · live/paper 帳戶快照
│  ├─ 即時績效                   live equity curve(套 metrics.py)· per-strategy 歸因
│  ├─ 下單簿                     open orders · 部分成交 · 取消 / 改單(OMS,今日完全缺)
│  ├─ 對帳 ●  ▸NEW              broker vs 內部 OrderRecord/positions diff(資本安全第一缺口)
│  ├─ 風控                       kill-switch · halt · 限額使用率(curl-only → 終於上 UI)
│  ├─ 稽核  ▸NEW                immutable audit(下單 / RiskGuard 否決 / kill / resume,who·when·why)
│  └─ 資料品質  ▸NEW            feed staleness · gap · 重複 · avg_fallback 命中率
│
├─ 📈 市場  Market (CandlestickChart)
│     watchlist · 圖表(保留扎實引擎)· order book / depth · ⚡ AI 訊號 · 資料新鮮度 chip
│
├─ 💼 投組  Portfolio — 資本真相 / 績效 (Wallet)
│  ├─ 總覽 / 部位                跨市場 TWD 彙總(用既有 FxConverter)· 配置條 · 權重 / 報酬% / market_value
│  └─ 損益 帳本  ▸NEW           FIFO realized P&L · FX-normalized · 報稅 CSV(接已存在的 /api/ledger)
│
└─ 🔧 工具  Tools (Wrench)
   ├─ 連線 / 帳戶  ▸NEW          broker credentials(server 端保存、永不回顯)· 暴露 has_credentials 狀態
   ├─ 排程                       bot 觸發 CRUD(timezone + 每根K收盤;健康在 監控室總覽)
   ├─ 警示 Alerts  ▸NEW          輕量 條件→通知 規則(不必為一個價位建整張 workflow)
   ├─ 通知 / Alert Center        全域 🔔 + 分級 filter + paper/LIVE 標籤 + 跳轉來源
   └─ 資料來源                   匯入升級為資料室(DB 持久化 · OHLC 驗證 · timeframe 維度)

(獨立 route group) 📖 文件中心 /docs — 亮色閱讀 Portal,維持與深色 App 分流(現狀保留)
```

一句話定位,消除房間邊界混淆:
- 策略室 =「想出策略」 · 交易室 =「證明它值得上線」 · 監控室 =「真錢有沒有在安全地跑」
- 投組 =「我有多少、賺賠多少」(review 面) · 監控室 =「機器與風控的狀態」(control 面)
- 市場 / 投組 維持一級 cross-cutting 參考面(非生命週期階段,不收進房間)。

### 5.3 關鍵 IA 動作

- 兩室 → 三室脊椎:把「執行」拆成 交易室(驗證 / 佈署)與新增的 監控室 Operations(營運真錢)。理由是營運活動(對帳 / 下單簿 / 即時風控 / 稽核 / 資料品質)本質上不是設計也不是測試,且證據顯示它們今天根本不在 IA 裡——不是被埋,是不存在。
- 建跨頁常駐 Global Context Bar(落實 DESIGN.md L116,改寫目前只有 ThemeToggle+docs 的 TopBar 空殼):單一 market 選擇器全域驅動 data-market(一次修掉跨頁紅綠殘留與 PortfolioPanel 方向誤色)+ mode chip(paper 中性 / LIVE 走 --live 脈動)+ live equity / 今日損益 + 風控狀態 chip(讀 0 次被呼叫的 /api/risk/status)+ 全域通知鈴鐺。用 MarketProvider/ModeProvider context 取代散落於三個 panel 的 setMarket。
- 把資本安全表面從 curl-only / 無 nav / 不存在 全部拉成一級:風控 cockpit(接上三個已齊備但前端命中 0 的 /api/risk 端點、kill-switch 上 UI)、帳本 ledger(在 lib/api.ts 與 nav 補方法與 leaf、接 /api/ledger/realized.csv)、對帳 reconciliation(全新、Broker ABC 補 fetch_open_orders/fetch_my_trades)、下單簿 OMS、連線室(暴露 has_credentials)、稽核 audit log。
- mode 從『全域 env 唯讀鏡像』升級為『per-deployment 權威參數』:runWorkflow→execute_order→get_broker 端到端帶 mode,_run_order 不再回退 settings.trading_mode;一張 workflow 預設 paper,通過 交易室 的 上線審核 Promotion Gate(最少 paper 天數/交易數、OOS Sharpe、maxDD 上限、風險揭露同意,門檻取自既有 walk_forward/metrics)並顯式 arming 後才為 live。兩張 workflow 可同時跑在不同 mode。
- 送真實單前的不可繞過 friction(目前送真單零確認、刪 workflow 反而要確認——風險優先序顛倒):dry-run 預覽(逐筆 symbol/side/qty/預估名目/成本,跑過 RiskGuard/PortfolioGuard)→ type-to-confirm 市場代號 → btn-live。並修正『執行回測』錯標籤(paper run 實為下紙上單,改名『模擬下單』,回測永遠走獨立按鈕)。
- 投組從側欄卡升級為跨市場分析室:總覽(用既有 FxConverter 做 TWD 彙總 + equity curve + 回撤 + 配置條 + 含權重/報酬%/market_value 的部位表)+ 損益帳本子頁(FX-normalized,修掉混幣別直接相加的 bug)。即時績效 + 策略歸因放 監控室(需先補 RealizedPnL 的 run_id/strategy_id 外鍵)。
- Alert Center 化:全域 🔔(未讀徽章取最高 severity 色、僅 live-critical 未讀才沿用 LIVE 脈動)+ /notifications 升級為分級 filter + read/unread + paper/LIVE 標籤 + 跳轉來源;另立輕量 警示引擎(條件→通知,不必建整張 workflow)。並補上無人值守失敗會『叫醒人』的通知洞(scheduler/engine node 失敗、RiskGuard 拒單、webhook 投遞失敗)。
- 清償 nav 機制與色彩紀律負債:tree 真正可收合(chevron 120ms、移除 TreeNav 的 href='#' 死錨)、點亮 NavLeaf.live + --live dot 死碼、策略庫子項留在本房間 backtest context、rail flyout 標籤、empty/error 補 nav-label、mobile nav 列 ≥44px、drawer focus-trap;全域強制 cyan=AI only(移除指標 toggle / Save / 匯入 CTA 的 accent-dim)、--live=真錢 only、--up/--down=價格 only 且台股反轉、狀態色不借用 price token。

### 5.4 為什麼這樣切

這個 IA 不是把現況打掉重練,而是把一個誠實的「策略設計 + 回測 + 紙上交易」引擎,補上它缺席的整個「真錢營運層」——而且補的方式全部站在既有扎實資產上延伸(metrics.py、validation.py 的 walk-forward/OOS、PortfolioSim、RealizedPnL FIFO、RiskGuard/PortfolioGuard、FxConverter、ccxt fetch_balance),不另起爐灶。

驅動三室決策的是橫跨十二個 domain 的同一個結構訊號,且全部可驗證、不是觀感:風控三端點 /api/risk/* 齊備但 frontend 命中 0、無路由、無 nav,最攸關安危的 kill-switch 只能 curl;ledger 後端有完整 FIFO + 報稅 CSV,前端卻無 api 方法、nav 無 leaf,realized「損益」域對使用者等於不存在;reconciliation 被兩個 domain 各自點名為唯一直接危及資本與資料完整性的 critical 缺口(內部 OrderRecord 與交易所實際持倉從不比對);execution.py 的 `status=='filled'` 判斷讓 live ccxt 成交('closed')永遠進不了 ledger——live 損益帳既空又無對帳。這些不是「介面不夠漂亮」,是「serious live 平台的營運中樞整片缺席」。兩室之所以撐不住,正因為它在設計上沒有為這層留下任何結構性落點。

幾乎每個 domain 的 investor/designer 雙鏡頭都落在 2/2 或 2/3、verdict 一致 Rework,病灶高度收斂:後端原語往往是對的(broker ABC seam 乾淨、回測無前視、DSL never-executed、target-position 冪等),壞在「對外的那一層」——暫態不可稽核、隱性假設不揭露、資本安全藏在 curl 後面、paper↔live 只是顏色。北極星 IA 把這條共同病灶變成兩個結構動作:(1) 一條常駐 Context Bar 讓 mode/market/風控/帳戶在任何頁都不可錯認、(2) 一個 監控室 + 一級化的資本安全 leaves 讓營運面有家。

設計面這同時尊重 DESIGN.md:two-room 心智模型沒被推翻(只長出第三段與一條 bar)、tree-menu 與 RWD rail/drawer 不變、cyan 仍只給 AI、--live 仍只給真錢、market-aware 反轉透過全域化的 data-market 才第一次真正成立。換句話說,DESIGN.md 寫了很足的「視覺嚇阻」(LIVE banner / btn-live / pulse),北極星 IA 補上它缺的「程序信任」(per-run mode / 上線審核 / 對帳 / 稽核 / 全域風控可見)。

### 5.5 全 App 一致的 paper↔live 信任模型

全 App 一致的 paper↔live 信任模型,四層,且每一層都對應一個已驗證的具體缺陷:

第 1 層|Mode 是 per-deployment 權威,不是全域 env 鏡像。現況 execute_order(mode=None) 一律回退 settings.trading_mode、_run_order 刻意不傳 mode,所以把 server 翻成 TRADING_MODE=live 並重啟,會在零 per-run 確認下同時武裝所有 workflow、所有 schedule、與編輯器 ad-hoc Run。北極星把 mode 端到端串成參數(runWorkflow→execute_order→get_broker),一張 workflow 預設 paper,且兩張 workflow 可同時跑在不同 mode——paper↔live 從「全有全無的全域開關」變成「逐佈署的權威狀態」。

第 2 層|全域常駐訊號(Context Bar)。paper↔live 不能是頁面內細節:離開 home / workflow 後模式脈絡今天就消失。一條跨頁 bar 永遠承載 mode chip(paper 中性 / LIVE 走 --live + DESIGN.md 唯一允許的脈動)、live equity / 今日損益、以及讀 /api/risk/status 的風控 chip。halted / kill 觸發時 chip 在每一頁轉 --error 並不可隱藏(mobile 收進漢堡仍保留危險圖示)。色彩鐵律:只有 --live 代表真錢,只有 --warning/--error 代表危險,--accent(cyan)永不用於危險或裝飾,--up/--down 只代表價格且台股經全域 data-market 反轉。

第 3 層|不可繞過的 friction,且 friction 與風險成正比(修正目前顛倒的優先序——送真單零確認、刪 workflow 卻要 confirm)。能不能上 live:由 交易室 的 上線審核 Promotion Gate 決定(最少 paper 天數/交易數、OOS Sharpe ≥ 門檻、maxDD ≤ 上限、強制風險揭露勾選,門檻直接取自既有 walk_forward/metrics,全綠才解鎖 btn-live)。每次送真單:dry-run 預覽(逐筆 symbol/side/qty/預估名目/成本,跑過 RiskGuard/PortfolioGuard)→ type-to-confirm 市場代號 → btn-live 確認。所有 arming / kill / resume / 策略改版事件寫入 immutable audit log(who·when·why)。

第 4 層|Fail-loud 一致化,讓「安全」在資料層與通知層都成立。execution.py 的成交判斷改用標準化終態(ccxt 'closed' = 成交)讓 live 真的進 ledger;對帳 worker 把內外部位 diff,漂移超閾值即 fail-loud 並可自動接 kill-switch;avg_fallback 髒價一律 --warning 標示、未實現損益絕不畫成綠色 0;無人值守失敗(scheduler / engine node / RiskGuard 拒單 / webhook 投遞失敗)一律 notify 並升級到全域 Alert Center;通知逐筆標 paper/LIVE。錯標籤(paper『執行回測』實為下紙上單)更名為『模擬下單』,回測永遠走獨立路徑。

一句話:paper 是安全預設且結構性安全(per-deployment、不可被全域旗標一鍵武裝),live 是「程式上真實、UI 上不可繞過」的明確武裝動作,而非顏色裝飾——真錢的每一個觸點(下單前、執行中、成交後、失敗時)都有對應的可見性與摩擦。

---

## 6. 全景新功能目錄 New-Feature Catalog

> 全景目標下,一個 serious 平台該有、但目前缺席的能力。彙整自各域的 `newFeatureProposals`(依來源域分組)。effort: S/M/L/XL。

**來自 D4 · 市場 Market**

- **Order Book / Depth-of-Market 面板** `(M)` — 後端新增 /api/markets/depth（ccxt fetch_order_book）+ 擴充 Ticker 帶 bid/ask/spread，前端右欄 mini DOM 與價差顯示。
  - _為何重要:_ 目前只有 OHLCV+last price，認真交易者無從判斷流動性、價差與真實可成交價；這是 TradingView/QuantConnect 的桌面門檻。
- **AI 訊號 → 下單試算橋接** `(M)` — 在 AI 訊號卡片加『據此試算下單』，呼叫既有 execute_order/RiskGuard 路徑回傳部位與風險預覽（不真下單）。
  - _為何重要:_ 把目前死路的 buy/sell/hold 意見接上平台最強的 risk/execution 資產，讓訊號可被驗證與執行。
- **訊號歷史回測徽章（signal backtest sparkline）** `(L)` — 對同一訊號條件在歷史資料上跑 bar-by-bar 回測，於卡片內嵌命中率/均報酬 sparkline。
  - _為何重要:_ 未校準的 LLM confidence 無法支撐機率語意；用回測歷史命中率才是可信的可信度來源。
- **資料新鮮度 / 連線狀態指示** `(S)` — 標頭 chip：crypto 顯示 WS 連線狀態+最後 tick 時間，台股/美股顯示匯入資料 as-of 區間，離線轉 --warning。
  - _為何重要:_ 目前無任何 staleness 指示，交易者可能對著過期資料下單——對 live 是危險盲區。

**來自 D9 · 匯入 Data / Market-data**

- **持久化 + 帶 timeframe 的 OHLCV store(DB-backed)** `(M)` — 以 SQLite 表 `ohlcv_bar`(複合鍵含 timeframe + adj_close + source)取代 in-memory `_store`;CsvDataBroker 改讀 DB 並真正依 timeframe 過濾與回傳;ImportRequest 補必填 timeframe。
  - _為何重要:_ 消滅『重啟即清空』的靜默失憶,並修掉 timeframe 與資料脫鉤導致年化指標失真的 critical bug。這是整個多市場 live 路徑的地基,crypto 以外的市場全靠它。
- **資料品質驗證管線(commit 前報告)** `(M)` — ingestion 加 OHLC 健全性、去重、缺口偵測、timeframe 推斷與宣告值比對、統一 tz 正規化;匯入回傳 validation report,前端先預覽再 commit。
  - _為何重要:_ Garbage-in 的回測對拿真錢的人最危險;順帶修掉混合時間戳與 range 回測的 opaque crash。fail-loud 必須延伸到資料層。
- **資料來源管理室(資料集清單 + Inspector)** `(M)` — 工具▸資料來源 升級:左側列出所有資料集(market/symbol/timeframe/bar 數/期間/來源/是否還原),右側 Inspector 顯示品質(缺口/重複/OHLC 違規)與 重新拉取/刪除。消費既有 GET /api/markets/imported 並擴充 metadata、補 DELETE 端點。需使用者核准的 nav 偏離。
  - _為何重要:_ 目前匯入是寫入黑洞,使用者無從判斷手上資料涵蓋哪段、是否可信、能否刪除。資料是回測地基,沒有管理面就無法評估回測可信度。
- **Vendor 資料 adapter 層** `(L)` — 與既有 Broker seam 對齊的資料來源 adapter:台股 FinMind/TWSE、美股 Polygon/AlphaVantage/Yahoo,讓貼 CSV 只是眾多 source 之一,可一鍵拉取/增量更新。
  - _為何重要:_ 手動貼 CSV 不可規模化;真實 vendor 是對標 QuantConnect/TradingView 的 table-stakes,也是台股/美股從 NotImplementedError scaffold 走向真實的前提。
- **Corporate-action 還原 + point-in-time universe** `(L)` — Candle 增 adj_close,以 split/dividend 還原價格;維護含 delisted 標的的歷史成分,回測可選 raw/adjusted 並避免 survivorship。
  - _為何重要:_ 未還原的 split 會呈現假崩盤、只用存活標的會系統性高估報酬;沒有這兩者,台股/美股回測的 edge 數字不可信。

**來自 D10 · AI 層**

- **AI 訊號回測回應快取(決定性 + 成本)** `(M)` — AI 回測以 (model, market-summary hash) 為鍵快取每根 bar 的 AISignalResponse;structured.py 改用 create_with_completion 持久化 token/latency/model。不引入 temperature/seed(預設 opus-4-8 不收 temperature、Anthropic 無 seed)。
  - _為何重要:_ 把含 AI 的回測從 run-to-run 隨機變成可重現、可重跑驗證,順帶把 ≤200 次 Opus 呼叫壓到實際不同 summary 數,並讓 run_id 的 live idempotency 重新成立 — 一次解決統計誠實、成本、與排程一致性三個病灶。
- **AI 訊號品質量表 (evaluation harness)** `(M)` — 離線跑歷史 AI 訊號,輸出 forward-return hit-rate、與 rsi/ma_cross baseline 對照、confidence reliability 曲線;策略室加『AI vs 內建』對照卡。
  - _為何重要:_ 目前無任何證據顯示單發 LLM 訊號優於內建 indicator 或隨機;沒有量表就無法主張 edge,嚴肅資金方不會在『未被衡量的 alpha』上下注。
- **confidence_gate 節點 + provenance 持久化** `(M)` — logic 類別新節點(amber)把低信心訊號降為 hold;StrategyDef 加 explanation/model 欄位,save 寫入 source='ai'+model+explanation 並在 GeneratedStrategy 常駐顯示理由。
  - _為何重要:_ 讓目前純裝飾的 confidence 真正影響交易,並建立 AI 生成策略的 audit trail — 兩者都是『可用真錢的 AI 平台』的 table stakes。

**來自 D13 · 多市場 Brokers / Live**

- **權威 mode + LIVE 武裝閘** `(M)` — 把 trading mode 從全域 env 提升為 per-run 參數,端到端傳遞(runWorkflow→execute_order→get_broker);前端在送真實單前加 type-to-confirm 武裝閘,彙整 /api/risk/status、券商連線狀態、預估名目金額;並修正 paper 執行鈕的誤導標籤。
  - _為何重要:_ 目前 UI 的 LIVE 切換只是 server env 的唯讀鏡像,且 paper Run 鈕寫『執行回測』卻會動帳戶;改 server 旗標即一次武裝所有 workflow+schedule,是會誤打真實單的 capital-safety 破口。
- **Live OMS + Reconciliation 層** `(L)` — 在 Broker ABC 增 cancel_order/get_open_orders/get_order;修 execution.py 的成交判斷(ccxt 'closed'=成交)讓 live 真的進 FIFO ledger;加 APScheduler 對帳 worker 把 open→filled/partial/canceled 落地補 ledger,並把 client_order_id 下推交易所做 exactly-once。
  - _為何重要:_ 現況 `status=='filled'` 永遠不命中 live 單(ccxt 回 'closed'/'open'),live 成交既不進 ledger、OrderRecord 又留錯狀態;limit 永卡 open、partial 無人處理、retry 可能重下真實單;PaperBroker 永遠 'filled' 把缺口遮蔽。
- **可信 broker connectors + 精度/路由表** `(XL)` — 新增 AlpacaBroker(美股,含官方 paper)、Shioaji/Fugle(台股);CcxtBroker 補 load_markets()+amount_to_precision/minNotional;registry 改 BROKER_ROUTING 設定表,Firstrade 降為 opt-in;BINANCE_TESTNET 拆成 data_source vs execution 兩維度。
  - _為何重要:_ get_live_broker 目前把美股 live 硬寫到無官方 API 的 Firstrade、YuantaBroker(us_stock) 是死碼;且 live 下單缺交易所精度/minNotional 會被 Binance reject;testnet 旗標還把 paper 行情污染成 testnet 價。
- **連線 室(Connections IA + 憑證安全 UX)** `(L)` — nav 新增『🔌 連線』房間,每市場一張 connection 卡:狀態/testnet-live/server 端保存且不回顯的憑證/對帳時間/中斷與輪替;後端把 has_credentials 與連線狀態以 API 暴露。
  - _為何重要:_ 目前無任何前端面能輸入憑證或看連線狀態(has_credentials 也沒被 API 暴露),live onboarding 與 paper→live 升級無從進行;撞到的只有 orders.py 丟回的裸 501/502。

**來自 D14 · 全景新功能 New Features**

- **券商對帳儀表板(Broker Reconciliation)** `(L)` — 在 Broker 抽象新增 fetch_open_orders / fetch_my_trades / fetch_account_state,定期把交易所/券商實際回報與內部 OrderRecord/positions diff,標出孤兒單、部分成交、被拒單、手續費漂移、內外部位不一致;不一致超閾值時 fail-loud 告警並可選自動暫停下單(沿用既有 kill-switch)。
  - _為何重要:_ 唯一真正可跑的 live 路徑(crypto via ccxt,已有 fetch_balance)目前完全不對帳,內部狀態一旦與真實持倉漂移,風險與績效全錯。這是把 live broker 從『內部帳本』推向可信賴的前提,也是唯一直接危及資本的缺口。
- **Paper→Live 上線審核(Promotion Gate)** `(L)` — 把 live 從全域 env 升級為 per-workflow 治理狀態機:每張要上線的 workflow 須通過可設定門檻(最少 paper 天數/交易數、OOS Sharpe、maxDD 上限、近 N 日 paper 與回測一致性、強制風險揭露勾選),全通過才在 UI 解鎖 btn-live;核准事件寫入稽核軌跡(who/when)。門檻直接取自既有 validation.py(walk-forward/OOS)與 metrics.py。
  - _為何重要:_ 現況 env 一翻成 live,任何已存 workflow 即可送真單(workflows.py 用全域 trading_mode)。這是與產品身分(paper 安全預設、live 慎重)直接對齊、且完全缺席的治理防線,不重造輪子而是把現成統計誠實度接到上線決策。
- **Live 績效分析與策略歸因(Live Analytics & Attribution)** `(L)` — 對 paper/live 帳戶定時 snapshot equity 形成時間序列,套用既有 metrics.py 算 live Sharpe/Sortino/maxDD;並在 RealizedPnL(及 OrderRecord)補上 run_id/strategy_id 的 join key,做 per-strategy/symbol/market 損益歸因與 vs Buy&Hold benchmark。把『投組』從快照升級為分析室。
  - _為何重要:_ 你無法經營一個量不到的帳戶。回測指標完整、真錢卻只有快照,且 RealizedPnL 連歸因的外鍵都沒有 — 這是嚴肅交易者最先質疑的落差,也是 live 留存與資本配置決策的核心。
- **稽核與營運可觀測性(Audit Log + Observability)** `(M)` — 新增 append-only AuditEvent 表 + middleware,記錄每筆下單、RiskGuard 否決、kill-switch engage/resume、設定與策略變更的 who/when/why/before-after;搭配一個 ops 時間軸面板。讓 runtime_state 的 kill-switch/halted 與 execute_order 的風險決策都留痕。
  - _為何重要:_ 真錢出事要能回放『當時發生什麼、誰按了什麼』。現況只有 RunLog 的 status+detail,RuntimeFlag 就地覆寫不留 actor。沒有不可竄改稽核,既無法事後復盤也無法支撐合規/多人場景。
- **資料品質與公司行動調整(Data Quality + Corporate Actions)** `(M)` — (1) 在 candle 取得路徑加入 gap/staleness/重複/異常跳動檢測,聚合每個 market×symbol 的 feed 健康(最後更新、缺口數、avg_fallback 命中率),異常 fail-loud 並可阻擋以髒資料下單;(2) 為股票 CSV 匯入加入 split/dividend/除權息回溯調整與調整係數欄,並把匯入歷史持久化(現為 process-local)。
  - _為何重要:_ live 決策只能跟乾淨資料一樣可靠。portfolio.py 已會靜默回退 avg_price 卻無人監控;股票未做公司行動調整會在除權息/分割點製造假跳空,污染 台股/美股 回測與估值 — 兩者都是直接的 data-integrity 風險。
- **訂單生命週期與進階單型(Order Lifecycle & Advanced Orders)** `(L)` — 在 Broker 抽象與 OrderRecord 上引入 working/open order 狀態、filled/remaining 量、cancel/amend endpoint 與部分成交回補;支援 limit / stop / OCO 等單型,前端提供 live order blotter(掛單簿)。
  - _為何重要:_ 現況市價即發即忘、單一終端記錄,無法管理真實掛單。serious live 跨市場交易(限價/條件單、部分成交、取消改單)沒有訂單生命週期等於只能盲打市價單。
- **警示引擎(Standalone Alerts Engine)** `(M)` — 獨立 alert-rule 表 + 評估器,複用 condition 語意(price/indicator/portfolio drawdown/部位變動)但不需建整張 workflow;命中即經 notify 服務發送,並可作為 promotion/kill-switch 的訊號源。前端在『通知』加上規則作者化介面。
  - _為何重要:_ 輕量條件→告警是 TradingView/3Commas 的 table-stakes,現況要監看一個價位都得建+排程一張 workflow(schedules 整圖觸發),門檻過高;也是 live 風控(回撤/部位異動)的耳目。
- **可配置資金配置政策(Allocation Policy on PortfolioSim)** `(L)` — 在既有 PortfolioSim(已具共享資金池 + 等權再平衡 + 成本感知 fill)之上加配置層:可設定權重(等權/風險平價/自訂)、再平衡頻率、(選配)相關性感知 sizing 與 per-signal 風險化 position sizing,並把同一政策套到 live。
  - _為何重要:_ 等權原型已存在且已暴露於 /api/backtest/workflow,但缺政策化 — 嚴肅資產配置者要的是『一籃子策略的權重與再平衡』。在現成引擎上加政策層即可從『策略測試器』躍遷到『投組平台』,故 effort 為 L 而非從零的 XL。
- **市場掃描器(Screener / Scanner)** `(L)` — 引入 symbol universe 概念,提供跨 symbol 的條件掃描(指標/量能/型態/相對強弱),命中清單一鍵帶進回測或 workflow;掛在『市場』下作為主面板。
  - _為何重要:_ 現況只能操作已知或已匯入的 symbol(markets.py per-symbol),沒有發現新機會的入口。Scanner 是多市場平台把使用者每天留在產品裡的主力面板,也是策略點子的源頭。
- **策略版本控管(Strategy Versioning)** `(M)` — StrategyDef 由就地覆寫改為帶版本歷史,workflow 的 strategy node 釘選版本;編輯產生新版,正在跑的 live/排程 workflow 不被底層無聲改動,可 diff/回滾。
  - _為何重要:_ nodes.py 在 run 時以 strategy_id 即時 load_spec,而 library.update_strategy 就地覆寫 — live 中策略可被無聲改變,同時破壞資本安全與可重現性。版本釘選是讓 backtest↔live 可信、事故可回溯的基礎工程。
- **多市場合規與微結構規則(Compliance & Microstructure)** `(L)` — 在 order 路徑前置 per-market 規則:台股 tick size/最小張數/漲跌停、美股 PDT 與 wash-sale 提示、crypto 最小下單量;並在首次啟用 live 前加風險揭露/免責同意 gate。稅務側補持有期(短/長期)與 per-jurisdiction 處理。
  - _為何重要:_ 認真做 台股/美股 必須編碼各市場規則,否則 live 單會被拒或違規;現況完全無微結構與合規層,是跨市場 live 上線的硬阻擋。

---

## 7. 優先排序路線圖 Roadmap

> 三階段。**Now** = 不碰 live broker,把 crypto+paper 做到可信;**Next** = 多市場 live 骨幹(成交真實性 + 真風控 + 資料層 + OMS/對帳);**Vision** = 整個真錢營運層 + 差異化能力。每項標 effort(S/M/L/XL)、鏡頭、依賴。

### 7.1 階段:Now

**階段目標:** 在不碰任何 live broker 的前提下,把唯一真正能跑的 crypto + paper 切片做到 investor-grade:補滿最強資產(backtester)的 statistical honesty、讓含 AI 的回測可重現、堵住所有會誤導真實資金決策的信任與 UX 缺口(錯標籤、accent 誤用、跨頁方向色殘留、隱形風控、不可見損益、斷裂 provenance)。此階段大多數項目彼此獨立,可平行開工。

| # | 項目 | Effort | 鏡頭 | 域 | 依賴 |
|---|------|:------:|:----:|----|------|
| 1 | **回測引擎 statistical honesty 硬化(slippage 預設 / Sharpe 排名 / 252 年化 / multiple-testing 揭露)** | `M` | Lens A(投資人) | 回測 Backtest | — |
| 2 | **持久化 BacktestRun + Honesty Bar** | `L` | Lens A+B | 回測 Backtest | 回測引擎 statistical honesty 硬化(slippage 預設… |
| 3 | **AI 訊號回測決定性 response cache + token/latency 計量** | `M` | Lens A(投資人) | AI 層 | — |
| 4 | **Workflow backtest↔live 語意對齊(吃 node sizing/timeframe、再平衡一致)** | `L` | Lens A(投資人) | 工作流 Workflow Build | AI 訊號回測決定性 response cache + token/laten… |
| 5 | **Global Context Bar(market / mode / equity 持久 shell)** | `M` | Lens A+B | Shell / IA / 設計系統 | — |
| 6 | **Risk Cockpit + 全域常駐 kill switch(UI 接線)** | `L` | Lens B(設計) | 風控 Risk & capital  | Global Context Bar(market / mode / equi… |
| 7 | **Portfolio 分析室 + 跨市場 FX 彙總 + realized Ledger UI** | `L` | Lens A+B | 投組 Portfolio + 損益  | — |
| 8 | **帳務一致性修補(reset 清 Lot/baseline + price_source fail-loud)** | `S` | Lens A(投資人) | 投組 Portfolio + 損益  | — |
| 9 | **Strategy Lab:provenance + 版本 lineage + 誠實卡片** | `L` | Lens A+B | 策略室 Strategy Lab | — |
| 10 | **strategy_agent DSL 表達力修正(移除 eq／ne、教 cross_above/below/between)** | `S` | Lens A(投資人) | 策略室 Strategy Lab | — |
| 11 | **無人值守失敗 notify 補洞(scheduler / workflow node / RiskGuard / broker)** | `M` | Lens A(投資人) | 通知 Notifications | — |
| 12 | **DESIGN.md 合規 sweep(accent 回歸 AI、price token 與 status 分離、原生控制收斂)** | `M` | Lens B(設計) | Shell / IA / 設計系統 | — |

<details><summary>各項理由（why）</summary>

1. **回測引擎 statistical honesty 硬化(slippage 預設 / Sharpe 排名 / 252 年化 / multiple-testing 揭露)** — 給 slippage 一個非零可信預設(config.py:156 現為 0,成交價系統性偏樂觀)、compare 從原始 total_return 改 Sharpe 排名並補 Buy&Hold 欄(backtest.py:184/127-134,移除誤導性 🏆)、股市年化改 252 日(metrics.py:23 現用 365.25,Sharpe/vol 高估約 1.2x)、optimize/walk-forward 明示 split 的 OOS 是被挑選過的樂觀上界。這是『能否託付真實資金』的最根本一層。
2. **持久化 BacktestRun + Honesty Bar** — 每次執行快照 candle 區間 + cost 參數(taker/slippage)+ 策略版本落地 DB(沿用既有 persist_workflow_run 模式),取代 resetOutputs 造成的暫態互斥分頁;頂部 Honesty Bar 把零滑價、樣本/交易數不足、被挑選的 OOS 等隱性假設變成顯性 --warning。任何可能被用來合理化真實資金的結果都必須可稽核、可重現。
3. **AI 訊號回測決定性 response cache + token/latency 計量** — 不加 temperature/seed(預設 opus-4-8 會 400、Anthropic 無 seed),改以 (model, summary_hash) 快取每根 bar 的 AISignalResponse 達成回測可重現,並把 ≤200 次 Opus 呼叫壓到實際不同 summary 數;同時改 create_with_completion 持久化 token/latency/model。在此之前任何含 AI 的回測 run-to-run 隨機、且排程 live 的 run_id idempotency 也站不住。
4. **Workflow backtest↔live 語意對齊(吃 node sizing/timeframe、再平衡一致)** — 今天回測完全忽略 order 節點 quantity(改等權 all-in)、每根 bar 漂移再平衡、硬編 1h/500、丟棄 data_source 的 timeframe/limit;回測必須吃節點參數、且再平衡規則對齊 live 的『達標即 no-op』。否則 backtest≠live 永遠成立,沒有認真的交易者會信任一張圖的回測。
5. **Global Context Bar(market / mode / equity 持久 shell)** — TopBar 目前只有 ThemeToggle + docs,連 DESIGN.md:116 要求的 market/mode context 都沒實作;把已存在於 workflow/home 的 LIVE chip 上提為全頁可見、收斂 market 選擇器為單一全域控制(修掉 data-market 跨頁殘留導致 PortfolioPanel 把 crypto 獲利畫成台股紅),並承載 equity/今日損益/kill-switch/連線狀態。這是 risk chip 與 mode 信號的共同地基。
6. **Risk Cockpit + 全域常駐 kill switch(UI 接線)** — 三個 /api/risk 端點已齊備,前端卻 0 次呼叫、無路由、無 nav,最攸關安危的 kill switch 只能 curl。接上 cockpit 頁(限額使用率 / 今日損益 / 報價源 / 風控事件 audit)與常駐 chip,讓 halted/kill 在所有頁永遠可見(遵 --live 危險信號)。即使 paper,daily-loss halt 也會靜默熄火策略而使用者毫不知情。
7. **Portfolio 分析室 + 跨市場 FX 彙總 + realized Ledger UI** — 新增 GET /api/portfolio/summary 用既有 FxConverter.to_base 做跨市場 TWD 彙總(api/risk.py:48-51 已證明可用);把後端已具備但全無 UI 的 realized『損益』ledger 接上(nav 加 leaf、修 api/ledger.py:83-88 混幣別相加 bug、接 report CSV);呈現 equity curve/回撤/權重/報酬%/market_value/price_source。realized P&L 對使用者完全不可見,是核心資本真相缺口。
8. **帳務一致性修補(reset 清 Lot/baseline + price_source fail-loud)** — reset_paper_account 須在同一交易清除該 market 的 Lot/RealizedPnL/OrderRecord 與 equity_baseline RuntimeFlag,消除『幽靈 FIFO lot 算錯 realized P&L』與『stale daily-loss baseline 誤觸 halt』;UI 把 price_source='avg_fallback'(現價失效退回成本價)亮成 --warning,停止把 uPnL 畫成綠色 0。高槓桿的小修。
9. **Strategy Lab:provenance + 版本 lineage + 誠實卡片** — save 路徑正確標 source='ai'(修 api/strategies.py:87 硬編 manual)、持久化原始 prompt+explanation+model(StrategyDef 加欄位)、導入 immutable 版本 + parent_id lineage 並接上已存在卻無人呼叫的 PUT 做『更新 vs 另存為 vN』;卡片改印後端已回傳卻被丟棄的 num_trades/期間/成本/equity sparkline 並對 0-trade fail-loud;掛 setMarket 讓台股配色反轉。讓策略庫成為可信賴的 asset of record。
10. **strategy_agent DSL 表達力修正(移除 eq／ne、教 cross_above/below/between)** — system prompt 把非法 eq|ne 列入 op 清單(會被 pydantic 拒、觸發重試或硬失敗),卻完全沒提 interpreter 與 render 都已支援的 cross_above/cross_below/between,導致 MA cross 退化成 sma_fast>sma_slow 語意失真;移除非法 op、明教 cross/between、讓使用者把 literal 升級為可調 param。純 prompt 修正,correctness 高槓桿快贏。
11. **無人值守失敗 notify 補洞(scheduler / workflow node / RiskGuard / broker)** — scheduler 失敗(service.py:84)、workflow node 失敗(engine.py:88-96)、per-order RiskGuard 拒單(risk.py:33-50)、broker/data_source 例外全程不發通知,而 webhook 投遞失敗 except 吞錯靜默 return;補上 notify(level=error) 並把投遞失敗改 fail-loud 回寫 system 通知。即使是 paper 排程,失敗也必須被看見——這是 live bot 的 lifeline。
12. **DESIGN.md 合規 sweep(accent 回歸 AI、price token 與 status 分離、原生控制收斂)** — 移除指標/log/量 toggle 與匯入/Save CTA 的 bg-accent 誤用(青色稀釋 AI 語意)、停止用 --up 當狀態色(成功通知/排程『執行中』在 data-market=tw 會翻紅誤讀)、新增缺漏的 --success token、切 market 自動帶入預設 symbol(修 BTC/USDT 被送進股票 broker 的狀態 bug)、原生 confirm/select 換 themed 控制。跨域 craft 快贏叢集,守住 refined-terminal 紀律。

</details>

### 7.2 階段:Next

**階段目標:** 把 paper 這個唯一的上線前驗證面,升級成可信的 multi-market live 骨幹:成交真實性(fills/slippage/sizing/shorting)、可設定且幣別一致的 continuous 風控、台股/美股資料層落地、live 帳本對帳與 OMS、可信排程與通知通道。live 下單能力在此被打通但仍受嚴格 gate。

| # | 項目 | Effort | 鏡頭 | 域 | 依賴 |
|---|------|:------:|:----:|----|------|
| 1 | **成交引擎 + 訂單狀態契約(limit marketability / stop intrabar / partial fills)** | `L` | Lens A(投資人) | 執行真實性 Execution | Workflow backtest↔live 語意對齊(吃 node sizi… |
| 2 | **Slippage 模型(size / liquidity / volatility)** | `M` | Lens A(投資人) | 執行真實性 Execution | 成交引擎 + 訂單狀態契約(limit marketability / sto… |
| 3 | **Sizing 引擎 + 做空 / 保證金(confidence-driven)** | `L` | Lens A(投資人) | 執行真實性 Execution | 成交引擎 + 訂單狀態契約(limit marketability / sto… |
| 4 | **權威 per-run mode + LIVE 武裝閘(dry-run 預覽 + type-to-confirm)** | `M` | Lens A+B | 多市場 Brokers & live | Risk Cockpit + 全域常駐 kill switch(UI 接線) |
| 5 | **Live OMS + Reconciliation(ccxt closed 入 ledger、cancel/查單、精度)** | `L` | Lens A(投資人) | 多市場 Brokers & live | 成交引擎 + 訂單狀態契約(limit marketability / sto… |
| 6 | **風控 continuous monitor + 可設定 / 幣別一致限額** | `L` | Lens A(投資人) | 風控 Risk & capital  | Risk Cockpit + 全域常駐 kill switch(UI 接線) |
| 7 | **資料層落地:DB-backed + timeframe 維度 + 品質管線(台股/美股)** | `L` | Lens A(投資人) | 匯入 Data Import + m | — |
| 8 | **市場資料層 live-grade(WebSocket / order book / cache / rolling-24h)** | `L` | Lens A(投資人) | 市場 Market | — |
| 9 | **排程可信化(SQLAlchemyJobStore + trust surface + cron timezone)** | `M` | Lens A+B | 排程 Schedules | 無人值守失敗 notify 補洞(scheduler / workflow n… |
| 10 | **可靠通知通道(非阻塞 + 多通道 severity routing)+ Alert Center** | `M` | Lens A+B | 通知 Notifications | 無人值守失敗 notify 補洞(scheduler / workflow n… |
| 11 | **回測量化視覺(equity vs B&H + underwater + optimize heatmap + walk-forward 串接)** | `M` | Lens B(設計) | 回測 Backtest | 持久化 BacktestRun + Honesty Bar |
| 12 | **Market AI 訊號可信且可執行(厚脈絡 + 歷史回測徽章 + 試算下單)** | `M` | Lens A(投資人) | 市場 Market / AI 層 | AI 訊號回測決定性 response cache + token/laten… |

<details><summary>各項理由（why）</summary>

1. **成交引擎 + 訂單狀態契約(limit marketability / stop intrabar / partial fills)** — limit 需 marketability check(next-open 觸及才成交,終結 execution.py:67-70 的 fantasy fill)、stop 需 intrabar(bar.high/low)觸發、新增 open/partially_filled/cancelled 狀態與 filled_quantity/avg_fill_price;paper 與兩條 backtest 共用同一 fills 引擎,消除重複限價邏輯。這是整條信任鏈最脆弱、且所有後續 live 能力疊加其上的原語。
2. **Slippage 模型(size / liquidity / volatility)** — 用 spread + size-impact(隨 qty/volume 平方根衝擊)+ vol 取代固定 bps,讓具規模/高週轉策略的 net edge 不再被系統性高估、optimize.py 不再於零摩擦下主動挑出高週轉 overfit。
3. **Sizing 引擎 + 做空 / 保證金(confidence-driven)** — 用 fixed-risk(由停損距離反推)/vol-target/equity-fraction 取代靜態 quantity(nodes.py:188)、position_fraction 與 equal-weight PortfolioSim,並餵入目前被丟棄的 signal.confidence;Position 加 side、支援 sell-to-open,PortfolioSim 支援權重與 short。讓可回測範圍對齊目標狀態的 sizing/shorting/leverage。
4. **權威 per-run mode + LIVE 武裝閘(dry-run 預覽 + type-to-confirm)** — 把 trading mode 從全域 env 升級為端到端 per-run 參數(runWorkflow→execute_order→get_broker,_run_order 不再回退 settings.trading_mode),live 下單前強制 dry-run 預覽(逐筆 symbol/side/qty/預估金額,跑過 RiskGuard/PortfolioGuard)+ type-to-confirm 武裝;落實 DESIGN.md:40-44 滿版粉色 LIVE banner + 脈動。今天送真實單零確認、改 server 旗標即一次武裝所有 workflow 是第一順位 capital-safety 破口。
5. **Live OMS + Reconciliation(ccxt closed 入 ledger、cancel/查單、精度)** — 修 execution.py:107 的 status=='filled' 為標準化終態(ccxt 'closed' 才是成交,今天 live realized-P&L 靜默為空);Broker ABC 補 cancel_order/get_open_orders/get_order;掛 APScheduler reconciliation worker 把 open→filled/partial/canceled 落地補 ledger 並 diff 內外部位;client_order_id 下推 newClientOrderId 做 exchange 級 exactly-once;CcxtBroker load_markets()+amount_to_precision/minNotional。
6. **風控 continuous monitor + 可設定 / 幣別一致限額** — 從 lazy pre-trade 改用既有 APScheduler 排程重算 equity/exposure/daily-loss、跨門檻 set_halted+notify;RiskGuard 加 from_settings() 並全程 fx.to_base(消除『50000』crypto=50k USDT vs 台股=50k TWD 的 31x 失準);day-start equity 改各市場真實 session open、halted 改日期作用域(修 UTC 換日 / 首讀快照跳空漏接 / 跨日靜默熄火);check→place 加鎖消除 TOCTOU;補 %-of-equity 限額。
7. **資料層落地:DB-backed + timeframe 維度 + 品質管線(台股/美股)** — process-local _store 換 DB-backed (market,symbol,timeframe) store、CsvDataBroker 真正依 timeframe 過濾、ImportRequest 補 timeframe —— 一次消滅『重啟即清空』與『日線當小時線回測、Sharpe 高估約 4.9x』兩個地基級 bug;parse→validate→commit 品質管線(OHLC 健全性/去重/缺口/統一 tz,順手修 naive-vs-aware TypeError)+ commit 前預覽 report + DELETE 端點。多市場 live 路徑的地基。
8. **市場資料層 live-grade(WebSocket / order book / cache / rolling-24h)** — 以 Binance WS 取代雙路 3s REST 輪詢並讓標頭價與圖上 pill 同源、CcxtBroker 改快取單例並預載 markets(消除每輪隱式 load_markets/rate-limit)、新增 order book/bid-ask、伺服器端 candle 快取與 OHLC 驗證、後端正確時間窗 rolling-24h 取代前端 barsPer24h 錯標、補資料新鮮度/連線指示。認真交易者需要評估流動性與真實可成交價。
9. **排程可信化(SQLAlchemyJobStore + trust surface + cron timezone)** — 換持久化 SQLAlchemyJobStore + 對停機漏跑寫 missed RunLog、連續 N 次失敗自動停機告警;面板做 trust surface(全域 mode banner、next_run_time/job-alive 心跳、可點開 RunLog error 歷史、修 bg-up『綠=執行中』台股翻紅、狀態 pill 與開關拆開、刪除加 confirm);接出 cron+respect_market_hours+明確 timezone(修 cron 無時區會在 server 本地時間觸發的 bug)+『每根 K 收盤對齊』。
10. **可靠通知通道(非阻塞 + 多通道 severity routing)+ Alert Center** — 把同步阻塞的 httpx.post 移出交易/scheduler 執行緒(避免慢 webhook 觸發 max_instances=1 排程 misfire),單一 NOTIFY_WEBHOOK_URL 升級為可路由 channels(Telegram/LINE/email/Slack)依 severity routing + 退避重試;前端 TopBar 全域鈴鐺 + 未讀徽章、/notifications 分級 filter + read/unread + paper/LIVE 標籤 + 跳轉來源。
11. **回測量化視覺(equity vs B&H + underwater + optimize heatmap + walk-forward 串接)** — EquityChart 疊 Buy&Hold(對等扣進出成本)+ underwater drawdown 子圖(複用 PriceChart 副圖同步模式)、walk-forward 串接連續 OOS 權益曲線 + fold 一致性統計(取代單純平均)、optimize 改 parameter-stability heatmap(高原 vs 尖峰)、trades 表補 MAE/MFE/持有期,並開放 starting_cash/position_fraction 控制。量化使用者建立信任的第一批圖。
12. **Market AI 訊號可信且可執行(厚脈絡 + 歷史回測徽章 + 試算下單)** — 餵入成交量/波動率/多週期脈絡並標明窗口時長、confidence 改離散等級或做 calibration、卡片內嵌『此訊號歷史回測命中率』sparkline 把 AI 接上回測引擎、一鍵『據此試算下單(套 RiskGuard/PortfolioGuard)』把死路意見變可驗證可執行的決策。

</details>

### 7.3 階段:Vision

**階段目標:** 補上整個『真錢營運層』與差異化能力,把產品從『策略測試器 + 紙上交易』躍遷成可被嚴肅資金信任的 multi-market live 投組平台:可信 broker connectors、上線治理、live 績效歸因、不可竄改稽核、資料 vendor 與公司行動還原、策略版本、配置政策、scanner、合規微結構。

| # | 項目 | Effort | 鏡頭 | 域 | 依賴 |
|---|------|:------:|:----:|----|------|
| 1 | **可信 broker connectors(Alpaca / Shioaji / Fugle)+ 連線室** | `XL` | Lens A+B | 多市場 Brokers & live | Live OMS + Reconciliation(ccxt closed 入… |
| 2 | **Paper→Live 上線審核 Promotion Gate** | `L` | Lens A+B | 全景新功能 / 多市場 Broker | Live 績效分析與策略歸因(snapshot 時序 + RealizedPn… |
| 3 | **Live 績效分析與策略歸因(snapshot 時序 + RealizedPnL→strategy 外鍵)** | `L` | Lens A(投資人) | 全景新功能 / 投組 Portfol | Portfolio 分析室 + 跨市場 FX 彙總 + realized Le… |
| 4 | **不可竄改稽核日誌 + 營運可觀測性** | `M` | Lens A(投資人) | 全景新功能 | — |
| 5 | **資料 vendor adapter + 公司行動還原 + point-in-time universe** | `XL` | Lens A(投資人) | 匯入 Data Import + m | 資料層落地:DB-backed + timeframe 維度 + 品質管線(台… |
| 6 | **AI alpha 量表 evaluation harness + confidence_gate** | `M` | Lens A(投資人) | AI 層 | AI 訊號回測決定性 response cache + token/laten… |
| 7 | **策略版本控管(釘選 + diff / 回滾)** | `M` | Lens A(投資人) | 全景新功能 / 策略室 | Strategy Lab:provenance + 版本 lineage + … |
| 8 | **可配置資金配置政策(Allocation Policy on PortfolioSim)** | `L` | Lens A(投資人) | 全景新功能 | Sizing 引擎 + 做空 / 保證金(confidence-driven) |
| 9 | **市場掃描器 Scanner + 獨立警示引擎** | `L` | Lens A+B | 全景新功能 / 市場 Market | 可靠通知通道(非阻塞 + 多通道 severity routing)+ Ale… |
| 10 | **訂單生命週期 UI(掛單簿)+ 多市場合規 / 微結構** | `L` | Lens A+B | 全景新功能 / 多市場 Broker | Live OMS + Reconciliation(ccxt closed 入… |

<details><summary>各項理由（why）</summary>

1. **可信 broker connectors(Alpaca / Shioaji / Fugle)+ 連線室** — 新增 AlpacaBroker(美股,官方 paper endpoint)、Shioaji/Fugle(台股,官方 API),registry 改 per-market BROKER_ROUTING、把無官方 API 的 Firstrade 從預設降為 opt-in,BINANCE_TESTNET 拆 data_source vs execution 兩維度;開『連線室』暴露 has_credentials/連線狀態、憑證 server 端加密保存且永不回顯。今天美股 live 硬寫到最脆弱的 Firstrade、且單租戶全域明文金鑰連第二位使用者都無從 onboard。
2. **Paper→Live 上線審核 Promotion Gate** — 把 live 從全域 env 升級為 per-workflow 治理狀態機:最少 paper 天數/交易數、OOS Sharpe、maxDD 上限、paper 與回測一致性(門檻直接取自既有 walk-forward/metrics),全通過才在 UI 解鎖 btn-live,核准事件寫入稽核。這是與產品身分(paper 安全預設、live 慎重)正面對齊、目前完全缺席的程序信任防線。
3. **Live 績效分析與策略歸因(snapshot 時序 + RealizedPnL→strategy 外鍵)** — 對 paper/live 定時 snapshot equity 形成時序、套既有 metrics.py 算 live Sharpe/Sortino/maxDD;在 RealizedPnL/OrderRecord 補 run_id/strategy_id join key 做 per-strategy/symbol/market 損益歸因 + vs Buy&Hold benchmark。你無法經營一個量不到的帳戶——這是 live 留存與資本配置決策的核心。
4. **不可竄改稽核日誌 + 營運可觀測性** — 新增 append-only AuditEvent 表 + middleware,記錄每筆下單、RiskGuard 否決、kill-switch engage/resume、設定與策略變更的 who/when/why/before-after,搭配 ops 時間軸面板。現況只有 RunLog status+detail、RuntimeFlag 就地覆寫不留 actor;真錢出事必須能回放並支撐合規/多人場景。
5. **資料 vendor adapter + 公司行動還原 + point-in-time universe** — 與 Broker seam 對齊的 vendor adapter(台股 FinMind/TWSE、美股 Polygon/AlphaVantage/Yahoo)讓貼 CSV 只是一種 source、可增量更新;Candle 加 adj_close 以 split/dividend 還原(避免假崩盤/假跳空),維護含 delisted 的歷史成分避免 survivorship bias。沒有這兩者,台股/美股回測的 edge 數字不可信。
6. **AI alpha 量表 evaluation harness + confidence_gate** — 離線跑歷史 AI 訊號算 forward-return hit-rate、vs rsi/ma_cross baseline 對照、confidence reliability 曲線,把『AI alpha』從假設變成可量測;新增 logic 類 confidence_gate 節點 / confidence-scaled sizing 讓目前純裝飾的 confidence 真正影響成交。沒有量表就無法主張 edge。
7. **策略版本控管(釘選 + diff / 回滾)** — StrategyDef 由就地覆寫改帶版本歷史,workflow strategy node 釘選版本,正在跑的 live/排程不被底層 update_strategy 無聲改動,可 diff/回滾。讓 backtest↔live 可信、事故可回溯的基礎工程。
8. **可配置資金配置政策(Allocation Policy on PortfolioSim)** — 在既有 PortfolioSim(共享資金池 + 等權 + 成本感知 fill)之上加配置層:可設定權重(等權/風險平價/自訂)、再平衡頻率、相關性感知 sizing、per-strategy 資本預算,並把同一政策套到 live。從『策略測試器』躍遷到 Composer 式『投組平台』。
9. **市場掃描器 Scanner + 獨立警示引擎** — 引入 symbol universe + 跨 symbol 條件掃描(指標/量能/型態/相對強弱),命中一鍵帶進回測或 workflow;獨立 alert-rule 引擎複用 condition 語意但不需建整圖(現況監看一個價位都得建+排程一張 workflow),並作為 promotion/kill-switch 的訊號源。多市場平台的留存主力面板與 live 風控耳目。
10. **訂單生命週期 UI(掛單簿)+ 多市場合規 / 微結構** — live order blotter(open/partial/cancel/amend);order 路徑前置 per-market 規則(台股 tick size/最小張數/漲跌停、美股 PDT/wash-sale 提示、crypto 最小下單量)+ 首次 live 風險揭露同意;稅務補持有期(短/長期)與 per-jurisdiction。認真做台股/美股必須編碼各市場微結構,否則 live 單會被拒或違規。

</details>

### 7.4 排序原則（sequencing）

排序遵循三條硬性原則。其一,Now 刻意完全不碰 live broker:目標是把唯一真正能跑的 crypto+paper 切片做到可信,而非鋪新攤子;此階段的價值在於修補會直接誤導真實資金決策的 statistical-honesty 與信任 UX 缺口(零滑價/365.25 年化/單次 in-sample『+40%』當頭條、不可重現的 AI 回測、curl-only 的 kill switch、不可見的 realized P&L、斷裂的 provenance、錯標籤的 CTA)。其二,真實依賴鏈決定 Next/Vision 的次序——live broker 不可早於『執行真實性(fills/狀態契約/sizing)+ 真正的 Risk Cockpit + reconciliation』;因此 Next 先補 X1 成交引擎與訂單狀態契約(limit marketability/partial/closed→ledger),再疊滑價模型、sizing、武裝閘與 OMS;而 Vision 的 Promotion Gate 是真錢前的最後一道閘,必須等 live 績效歸因(V3)與稽核(V4)就位才有意義。其三,地基先於外觀:Global Context Bar(N5)是 risk chip、mode 信號、通知鈴鐺共同的 shell 地基,故排在 Risk Cockpit UI(N6)與 Alert Center(X10)之前;AI 決定性 cache(N3)是『可信任 AI 回測』與排程 live run_id idempotency 的前提,故排在 Workflow 對齊(N4)與 AI 可執行化(X12)、AI 量表(V6)之前;資料層落地+timeframe(X7)是 multi-market 誠實與 vendor/公司行動(V5)的地基。一個跨階段的關鍵 invariant:backtest 與 live 必須共用同一 fills/sizing 路徑——N4 先讓 workflow 回測吃節點參數,X1/X3 再把共用引擎做實,否則『回測賺錢、實盤不賺』會貫穿整個產品、侵蝕最強資產的可信度。Now 內多數項目(Strategy Lab、Portfolio、Risk UI、Backtest 引擎、AI cache、通知補洞)彼此獨立,適合 worktree 平行開工;Next 的執行真實性三件套(X1→X2/X3)則需序列推進。

### 7.5 Quick Wins（高槓桿快贏 — 多為數行或純設定改動）

- strategy_agent system prompt 修正:移除不存在的 eq|ne、明教已支援的 cross_above/cross_below/between——純 prompt 改動即修掉 MA cross 語意失真(S)。
- 股市年化改 252 日(metrics.py:23)+ compare 改 Sharpe 排名並移除誤導性 🏆(backtest.py:184)——少數行修正,直接提升風險數字誠實度。
- 非零 slippage 預設(config.py:156 / .env COST_SLIPPAGE_BPS)——config 改動,停止系統性高估成交品質(需與 Honesty Bar 揭露搭配才完整)。
- reset_paper_account 同交易清除 Lot/RealizedPnL/equity_baseline——消除幽靈 FIFO lot 與 stale daily-loss baseline 兩個確定性帳務 bug(S)。
- 修 paper『執行回測』錯標籤(Toolbar.tsx:92,實為下紙上單會動帳戶)+ 在送單路徑加最小確認——零成本、高信任價值。
- 卡片對 num_trades=0 fail-loud(『0 筆交易—規則從未觸發』而非偽裝成平盤 +0.00%)+ 把後端已回傳的 num_trades/期間印上卡面。
- price_source='avg_fallback' 亮成 --warning 並停止把 uPnL 畫成綠色 0(PortfolioPanel/HomeDashboard)——把現價失效從靜默誤導變顯性。
- DESIGN.md accent 紀律修正:移除 indicator/log/量 toggle 與匯入/Save CTA 的 bg-accent、停止用 --up 當狀態色、補 --success token——多處 CSS class 替換的 craft 叢集。
- 切 market 自動帶入該市場預設 symbol(修 BTC/USDT 被送進股票 broker 的 501 撞牆)+ 在策略室/投組掛 setMarket 讓台股 --up/--down 正確反轉。
- webhook 投遞失敗從靜默 except return 改為回寫一筆 system 通知(notifications/service.py)——fail-loud 的最小落地。

---

## 8. 需要你拍板的決策 Open Decisions

這份藍圖把「該做什麼、為什麼、什麼順序」講清楚了;以下幾個叉路口需要你的方向才能把某段展開成可執行的 implementation plan:

1. **Live broker 的首攻市場?** — Next/Vision 的次序取決於此。選項:**台股先**(Shioaji / Fugle 有官方 API)、**美股先**(Alpaca 有官方 paper endpoint,最好串)、或**先把 crypto live 打磨到極致**再擴市場。(現況:美股 live 硬寫在最脆弱的非官方 Firstrade 上。)
2. **單機自用 vs 多租戶 SaaS?** — 現在是單租戶、全域明文金鑰,連第二位使用者都無從 onboard。若要走 SaaS,auth / 加密憑證保存 / per-user 隔離 / 稽核 的投入會大幅前移。
3. **AI 的賭注下多大?** — 要用 evaluation harness **證明 AI alpha**(賭差異化,但這群使用者最會驗證、識破成本高),還是把 AI 收斂到「**把白話變成可調 spec**」這個已經可信的價值、訊號交還給 indicators?
4. **自建資料 vendor adapter,還是維持貼 CSV?** — 台股/美股要不要接 FinMind / TWSE / Polygon 並做公司行動還原?不接,台股/美股回測的 edge 數字結構上不可信(假崩盤/假跳空 + survivorship)。
5. **核准對 `DESIGN.md` 的演進。** — 北極星提案了三項偏離:**兩室 → 三室(新增監控室)**、**Global Context Bar**、**策略改為 rules-first 視圖(而非 code-block)**。這些需要你核准才動,因為 `DESIGN.md` 是視覺/UI 的單一真相來源。
6. **我先把哪一條展開成可執行 plan?** — 我建議首選 **Now 的 backtest honesty 叢集**(投資人信任的根)或 **Global Context Bar + Risk Cockpit**(設計+安全的共同地基);兩者都是高槓桿、可獨立交付。告訴我一個,我就用 `writing-plans` 把它變成逐步實作計畫。

---

_本藍圖由多 agent 對程式碼實證生成;所有 finding 均附 `file:line` 或具體行為,可逐條查核。下一步:挑一條路線展開為 implementation plan,或先核准 §8 的方向。_