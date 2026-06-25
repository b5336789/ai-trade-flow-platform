# 上線前策略品質 Gate / Pre-Launch Strategy Quality Gate

> **守門原則:不要因 bug 或過擬合賠掉真錢。** 系統是基礎建設,不承諾獲利。
> 任何「可以上線」的結論都要保守。這份 gate 是 [go-live-checklist](./go-live-checklist.md)
> 第 5 節「金融正確性」的**量化展開** — 把「OOS 排序、看 Sharpe/回撤」變成可重現的 PASS/FAIL 門檻。

一個候選 crypto 策略**必須通過下列每一項**才可被建議切到小額 live。任何一項 FAIL → 整體 **NO-GO**。
評估一律以 **net(扣手續費 + 滑價後)** 報酬,用**真實 Binance OHLCV**,以樣本外 / walk-forward 為準,絕不以樣本內原始報酬排名。

---

## 0. 前置:基礎設施正確性(策略無關,先確認一次)

| 項目 | 要求 | 驗證 |
|---|---|---|
| 無前視偏差 | 訊號以 `close[i]` 決策,成交於 `open[i+1]` | `test_fills_at_next_bar_open_not_decision_close`、`test_last_bar_signal_opens_no_position` 通過 |
| 成本內建 | 每筆成交都過 `CostModel`,回測預設 ON | `backtest/engine.py` + `trading/costs.py`;`pytest -k cost` 通過 |
| 滑價 > 0 | 評估時 `COST_SLIPPAGE_BPS` 不得為 0(prod 預設 0,評估必須調高) | gate 腳本強制 `slippage_bps=5.0` |
| 可重現 | 同一份 candles → 同一結果(純函式、無隨機) | `walk_forward` / `run_backtest` 為 deterministic |
| 資料完整 | 時間戳嚴格遞增、無缺口/重複;抓不到資料 → fail loud | gate 腳本 `fetch_candles` 完整性檢查 |

> 回測不得打線上**下單/帳戶** API。抓**歷史公開 OHLCV**作為輸入是資料取得步驟,與「無前視、純函式」的回測引擎分離,允許且為本評估所必需。

## 1. 量化門檻(逐項 PASS/FAIL)

評估設定:`timeframe=1d`、taker `7.5bps`、slippage `5bps`、anchored walk-forward `n_folds=4`、
holdout = 末端 30% 樣本外、參數以樣本內 Sharpe 選定後在 holdout 評估。

| # | 門檻 | 閾值 | 為什麼 |
|---|---|---|---|
| G1 | **樣本數** OOS round-trip 交易數 | `≥ 30` | < 30 筆無統計信心;少數幾筆的高報酬是運氣不是 edge |
| G2 | **OOS 風險調整報酬** walk-forward 平均 OOS Sharpe | `≥ 0.3` | 必須有意義為正,不是貼著 0 |
| G3 | **OOS 淨報酬** holdout 樣本外 net 報酬 | `> 0%` | 扣成本後仍要賺錢 |
| G4 | **獲利因子** holdout net profit factor | `≥ 1.2` | 毛利/毛損要有安全邊際,不是 1.0 邊緣 |
| G5 | **回撤天花板** holdout OOS 最大回撤 | `≤ 35%` | crypto 保守上限;超過代表部位/風控吃不消 |
| G6 | **跨 fold 穩健** OOS metric 為正的 fold 比例 | `≥ 50%` | 不能只靠單一 fold/單一行情賺到 |
| G7 | **IS→OOS 衰減** holdout OOS Sharpe(當 IS Sharpe > 0) | `≥ (1 − 0.7) × IS Sharpe` | OOS 不得相對 IS 崩跌 → 過擬合訊號 |
| G8 | **成本壓力測試** 2× 滑價後 holdout OOS net 報酬 | `≥ 0%` | edge 必須撐得住比預期更差的摩擦成本 |

### 輔助觀察(不單獨擋關,但須在報告中揭露)
- **vs Buy & Hold**:同窗 B&H 報酬。擇時若報酬輸 B&H 但回撤顯著更低,可作為「風險調整後」理由說明 — 但仍須通過 G1–G8。
- **Turnover / exposure**:換手過高代表成本侵蝕、對滑價敏感。
- **勝率**:僅參考;低勝率 + 高賺賠比仍可接受,反之亦然。

## 2. 範圍不變式(沿用 go-live-checklist)
- 僅現貨、long/flat(無做空/槓桿/期權/期貨/融資)。
- K 棒級節奏(非毫秒 HFT)。
- 首發**小額**,部位遠低於 `MAX_TOTAL_EXPOSURE_VALUE` 等風險上限。

## 3. 判讀
- **GO**:G1–G8 全 PASS,且在 ≥ 2 個標的 / 多個 regime 上一致成立。
- **REFINE**:核心邏輯合理但個別門檻邊緣 → 調參/換 timeframe 後重跑,不得放寬門檻來硬過。
- **NO-GO**:任一硬門檻 FAIL,或結果只靠少數交易 / 單一行情。**預設立場是 NO-GO**;證據不足就留在 paper。

## 4. 如何重現

```bash
cd backend
python3.11 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python scripts/gate_eval.py          # 全部 4 策略 × BTC/ETH
# 輸出:人類摘要 + scripts/gate_eval_result.json(含每個 fold、holdout、壓力測試明細)
```

門檻定義在 `scripts/gate_eval.py` 的 `GATE` dict,與本文件一致。改門檻必須同時改兩處並說明理由。
