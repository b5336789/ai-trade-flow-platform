// 系統功能詳細說明 — the platform's feature catalog, surfaced on the website.
// Grouped by the two-room IA (策略室 / 交易室) plus cross-cutting capabilities.

interface Feature {
  title: string;
  ai?: boolean;
  body: string;
  points: string[];
}

interface FeatureGroup {
  room: string;
  en: string;
  blurb: string;
  features: Feature[];
}

const GROUPS: FeatureGroup[] = [
  {
    room: "策略室",
    en: "Strategy Lab",
    blurb: "策略誕生的地方:用白話與 AI 對話,生成可回測、可重用的宣告式策略。",
    features: [
      {
        title: "AI 策略設計",
        ai: true,
        body: "以自然語言描述進出場規則,Claude 產生「宣告式策略 spec」(白名單指標 + 條件樹),而非任意可執行程式碼 — 從根本杜絕沙箱逃逸風險。",
        points: [
          "支援 RSI / SMA / EMA / MACD / 布林通道 / 收盤價 / 量等白名單指標",
          "可調參數自帶 default / min / max,使用時再微調",
          "spec 永不執行;由直譯器逐根 K 棒求值成 buy/sell/hold 訊號",
        ],
      },
      {
        title: "策略庫",
        body: "生成的策略存入策略庫成為可重用資產,於交易室組成工作流或直接回測。",
        points: ["建立 / 載入 / 刪除策略", "每支策略一鍵回測,顯示報酬 / Buy&Hold / 回撤 / 勝率", "AI 生成與手動建立來源標記"],
      },
    ],
  },
  {
    room: "交易室",
    en: "Trading Room",
    blurb: "策略運行的地方:模擬回測與節點式工作流,一套畫布兩種模式。",
    features: [
      {
        title: "策略回測 / 比較 / 最佳化",
        body: "單一策略看權益曲線與完整風險指標;一鍵比較多策略排名;對參數做網格搜尋並套用最佳值。",
        points: [
          "計入交易成本(手續費 / 證交稅 / 滑價),next-bar open 成交杜絕前視偏差",
          "Sharpe / Sortino / Calmar / Profit Factor / CAGR / 最大回撤 / 換手率",
          "Walk-forward 樣本外驗證:依風險調整後 OOS 排序,避免過擬合",
        ],
      },
      {
        title: "節點式工作流",
        ai: true,
        body: "拖拉節點串成自動交易流程:資料來源 → 策略 / AI 訊號 → 邏輯節點 → 下單(經風控)→ 輸出。",
        points: [
          "邏輯節點:condition(門檻)、combine(AND/OR/加權投票)、branch(路由)",
          "拓撲排序執行 + 循環偵測;手動與工作流共用單一下單路徑",
          "可即時 Run 或 Save 後交給排程器定時自動執行",
        ],
      },
    ],
  },
  {
    room: "跨領域能力",
    en: "Platform-wide",
    blurb: "撐得住長時間自動運行、可接真實資產的金融正確性與安全地基。",
    features: [
      {
        title: "風控 + Kill Switch",
        body: "每筆下單前經風控閘門:單筆金額、部位市值上限、投組總曝險、單日虧損(觸發 halt)、單日下單數,與可持久化的 kill switch。",
        points: ["全部以基準幣別(TWD)計算", "觸發時拒絕新進場、仍允許出清", "冪等下單鍵杜絕重複成交"],
      },
      {
        title: "多市場 Broker 抽象",
        body: "單一 Broker 介面同時是「紙上 vs 真實」與「不同市場」的接縫。",
        points: [
          "加密貨幣(Binance / ccxt):行情 + 紙上交易(live 可選)",
          "台股 / 美股:CSV 匯入做離線回測與紙上交易",
          "美股 live 預設 signal-only(只出訊號、人工執行),零真實下單路徑",
        ],
      },
      {
        title: "FIFO 損益帳本 + 通知",
        body: "每筆成交以 FIFO 沖銷計算逐筆已實現損益(含成本與證交稅),可匯出報稅 CSV;成交與訊號即時推送站內訊息流並可外送 webhook。",
        points: ["開盤行事曆 gating:收盤時段排程自動跳過", "紙上帳戶狀態跨重啟持久化", "存取需 bearer token,CORS 白名單"],
      },
    ],
  },
];

export function SystemFeatures() {
  return (
    <div className="space-y-6">
      {GROUPS.map((group) => (
        <section key={group.room} className="rounded-lg border border-border bg-surface-1 p-5">
          <div className="mb-4 flex flex-wrap items-baseline gap-2">
            <h3 className="font-display text-lg font-bold">{group.room}</h3>
            <span className="text-[13px] text-faint">{group.en}</span>
            <p className="w-full text-[13px] text-muted">{group.blurb}</p>
          </div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
            {group.features.map((f) => (
              <article key={f.title} className="rounded-md border border-border bg-surface-2 p-4">
                <div className="mb-1.5 flex items-center gap-2">
                  <h4 className="font-display text-[14px] font-semibold">{f.title}</h4>
                  {f.ai && (
                    <span className="rounded-sm bg-accent-dim px-1.5 py-0.5 text-[10px] font-medium text-accent">
                      AI
                    </span>
                  )}
                </div>
                <p className="text-[12.5px] leading-relaxed text-muted">{f.body}</p>
                <ul className="mt-2 space-y-1 text-[12px] text-text/80">
                  {f.points.map((pt) => (
                    <li key={pt} className="flex gap-1.5">
                      <span className="mt-1.5 h-1 w-1 shrink-0 rounded-sm bg-accent/70" />
                      <span>{pt}</span>
                    </li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
