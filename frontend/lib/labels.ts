// frontend/lib/labels.ts
// 集中化 UI 文案與術語白話解讀。各頁引用此處,杜絕散落的硬編字串(尤其中英混雜)。
// 金融慣用詞(Sharpe/RSI/CAGR)保留原詞,解讀放 GLOSSARY。

export const L = {
  common: { run: "執行", loading: "執行中…", more: "更多", advanced: "進階分析", noData: "無資料" },
  market: { title: "市場行情", symbol: "商品", timeframe: "週期", live: "即時", paused: "已暫停", offlineCsv: "離線資料(CSV)" },
  backtest: {
    title: "模擬回測",
    run: "執行回測",
    compare: "比較全部策略",
    optimize: "參數最佳化",
    walkforward: "樣本外驗證",
    rangeRecent: "最近 N 根",
    rangeDates: "日期區間",
    overview: "概覽",
    trades: "交易明細",
    excess: "超額(策略 − 大盤)",
    noTrades: "此區間策略未產生任何交易",
  },
  metrics: {
    total_return: "總報酬",
    buy_hold: "Buy & Hold",
    cagr: "年化報酬 CAGR",
    max_drawdown: "最大回撤",
    sharpe: "Sharpe",
    sortino: "Sortino",
    calmar: "Calmar",
    win_rate: "勝率",
    profit_factor: "獲利因子",
    annualized_volatility: "年化波動",
    exposure: "曝險時間",
    turnover: "週轉率",
    max_consecutive_losses: "最大連虧",
    num_trades: "交易數",
  },
} as const;

// 每個指標一句白話(主+次全覆蓋)。<Term> 以 hover tooltip 呈現。
export const GLOSSARY: Record<string, string> = {
  total_return: "整段期間的總損益百分比。",
  buy_hold: "同期間「買進並持有」不操作的報酬,用來比較策略有沒有贏大盤。",
  cagr: "把總報酬換算成每年平均的複利成長率,跨不同長度才好比較。",
  max_drawdown: "從資產高點跌到後續低點的最大跌幅;越小代表越穩、越不會睡不著。",
  sharpe: "風險調整後報酬;>1 算不錯,接近 0 普通,<0 代表承擔波動卻虧損。",
  sortino: "類似 Sharpe,但只計算「下跌」的波動,對下檔風險更敏感。",
  calmar: "年化報酬 ÷ 最大回撤;衡量「賺的相對於最痛的那一跌」划不划算。",
  win_rate: "獲利交易佔總交易的比例。注意:勝率高 ≠ 賺錢(可能小賺多次、大賠一次)。",
  profit_factor: "總獲利 ÷ 總虧損;>1 才有正期望值,∞ 代表期間內沒有虧損交易。",
  annualized_volatility: "報酬的年化標準差;數字越大代表淨值上下震盪越劇烈。",
  exposure: "有持倉的時間佔比;100% 代表幾乎全程在場,低代表多在空手等訊號。",
  turnover: "交易頻繁度;越高代表進出越勤、累積的交易成本越多。",
  max_consecutive_losses: "連續虧損的最長次數;反映策略最糟的一段心理壓力。",
  num_trades: "完整進出場的交易筆數;太少則統計不具代表性。",
  walk_forward: "用過去資料選參數、在「沒看過的未來」資料上驗證,專門抓出過度最佳化。",
  optimize: "掃描參數網格找最佳組合;本系統以樣本外(OOS)指標排名,避免挑到過擬合的參數。",
};
