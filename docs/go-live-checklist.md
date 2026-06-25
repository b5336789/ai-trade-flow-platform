# 上線前檢查清單 / Go-Live Checklist

> **狀態:Phase 0(金融正確性與安全地基)程式已全部完成(M0.1–M0.7 ✅)。**
> 這是 PRD「接真錢前最低門檻」的**人工**確認清單。**在你逐項打勾完成本清單之前,禁止切到 live。**
> 切 live 必須同時滿足:① 顯式 `TRADING_MODE=live` ② 有效金鑰 ③ 本清單全數通過 ④ kill switch 已實測。

本系統是基礎建設,不是印鈔機;不承諾獲利。最高原則:**不要因 bug 或過擬合賠掉真錢。**

---

## 0. 前置(資料庫 / 環境)
- [ ] 全新或已遷移的資料庫:M0.5 新增 `OrderRecord.client_order_id`、M0.6 新增 `RuntimeFlag` 表。`init_db()` 的 `create_all` **不會**幫既有舊表加欄位 — 上線用乾淨 DB,或手動 `ALTER TABLE`/重建。
- [ ] `.env` 由 `.env.example` 複製並填妥,且**未**提交到 git。

## 1. 存取安全(M0.7)
- [ ] `API_TOKEN` 設為**強隨機字串**(留空 = 驗證關閉/全開放,僅限本機開發)。
- [ ] 前端 `NEXT_PUBLIC_API_TOKEN` 與 `API_TOKEN` 一致。
- [ ] `API_CORS_ORIGINS` 僅列出你實際使用的前端來源(非 `*`)。
- [ ] 後端未曝露於公網,或已置於受信任網路/反向代理之後。

## 2. 交易所金鑰最小權限
- [ ] 幣安 API key **關閉提領(withdrawals disabled)**。
- [ ] API key **綁定後端固定 IP(IP allowlist)**。
- [ ] 行情用**唯讀** key;下單用另一把**僅限交易、鎖死**的 key。
- [ ] 先用 `BINANCE_TESTNET=true` 驗證下單路徑,再切正式。

## 3. 交易成本(M0.1)
- [ ] `COST_*` 參數反映你的實際費率(幣安等級費率、台股折讓、滑價)。
- [ ] 已確認回測/紙上報酬為**淨額**(計入手續費/稅/滑價)。

## 4. 投組級風控 + Kill switch(M0.6)——全部以基準幣別 TWD 計
- [ ] `BASE_CURRENCY=TWD`;`FX_RATES` 為近期合理匯率(Phase 0 為靜態值,M1.1 才接即時匯率 — 上線期間請定期人工校正)。
- [ ] `MAX_TOTAL_EXPOSURE_VALUE`、`MAX_DAILY_LOSS`、`MAX_ORDERS_PER_DAY` 設為你能承受的保守值。
- [ ] 單筆/單標的 `RiskGuard`(`max_order_value`/`max_position_value`)已設。
- [ ] **實測 kill switch**:`POST /api/risk/kill-switch {engaged:true}` → 確認**新進場(buy)被擋**、**出清(sell)仍可成交** → `POST /api/risk/resume` 解除。
- [ ] **實測單日虧損 halt**:在 paper 觸發 `MAX_DAILY_LOSS` → 確認自動 halt(擋進場、放行出場)、通知有發出、`POST /api/risk/resume` 可恢復。
- [ ] `GET /api/risk/status` 顯示的曝險/權益/當日單數符合預期。

## 5. 金融正確性(M0.2–M0.4)
- [ ] 回測無前視偏差(成交於次根開盤,M0.2)。
- [ ] 參數最佳化用**樣本外(OOS)**排序(`split=true`,M0.4),已檢視 IS↔OOS 落差,未挑過擬合參數。
- [ ] 已用 Sharpe/Sortino/Calmar/最大回撤(M0.3)而非僅勝率/報酬評估策略。

## 6. 範圍確認(本期不變式)
- [ ] 僅**現貨/現股、long/flat**(無做空/槓桿/期權/期貨/融資)。
- [ ] 美股維持 **signal-only**(本期無自動實盤下單路徑)。
- [ ] K 棒級節奏(非毫秒 HFT)。

## 7. 上線啟動
- [ ] **小額起步**(遠低於各上限),先觀察數日。
- [ ] 監看站內通知 / webhook(成交、風控觸發、halt)。
- [ ] 確認排程的 `max_instances=1`/`coalesce` 與重複下單防護(M0.5 冪等鍵)行為符合預期。

---

## 尚未涵蓋(Phase 1+,上線前須知其限制)
- **開盤行事曆 gating(M1.4)尚未做**:crypto 24/7 無妨;**台股/美股**目前無自動「收盤跳過」,故不應將台股/美股排成自動 live(美股本就 signal-only;台股 live 待 M1.2 元大 SPARK + M1.4)。
- **即時匯率(M1.1)尚未做**:`FX_RATES` 為靜態值,需人工維護。
- **FIFO 損益/稅務帳本(M1.3)尚未做**:報稅數字需另行核對。

> 逐項打勾並確認後,方可設定 `TRADING_MODE=live`。任何一項存疑 → 留在 `paper`。
