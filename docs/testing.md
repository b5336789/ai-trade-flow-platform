# 測試 / Testing

所有測試為**商業邏輯測試**(驗證真實意圖,非空覆蓋率),且**完全離線**:用合成資料與
stub broker,不需網路或 API 金鑰(`CLAUDE.md`:Use Business-Logic Tests)。

## 執行

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest                 # 53 passed
```

## 測試檔一覽(`backend/app/tests/`)

| 檔案 | 涵蓋 |
| --- | --- |
| `test_indicators.py` | 指標包裝(SMA 等於手算均值、RSI 上升趨勢偏高、空資料 fail loud) |
| `test_strategies.py` | MA 交叉(上穿買/下穿賣/持平)、RSI(超買賣)、資料不足與參數防呆 |
| `test_more_strategies.py` | MACD(震盪序列產生交易)、布林(跌破/突破/區間內)、註冊表 |
| `test_paper_trading.py` | 紙上撮合(買賣現金/部位、加權平均成本、現金不足/超賣 fail loud)、風控、組合損益 |
| `test_orders_api.py` | 下單 HTTP 流程(以 stub 離線)、風控回 422 |
| `test_ai_signal.py` | AI 訊號代理(mock Claude:映射、信心夾擠、空資料 fail loud) |
| `test_workflow.py` | 工作流端對端(買訊號下單、hold 不下單、循環拒絕、拓撲序、節點失敗回報) |
| `test_backtest.py` | 回測(獲利 round trip、買入持有對照、權益曲線/回撤、防呆) |
| `test_optimize.py` | 網格搜尋(排名、錯誤組合排末、組合上限、未知 metric fail loud) |
| `test_scheduler.py` | 排程 job 主體(寫 RunLog、更新狀態)、停用略過、增/刪 job |
| `test_schedules_api.py` | 排程 HTTP(建立/列出/切換/刪除、未知工作流 404、間隔過短 422) |
| `test_notifications.py` | 通知(站內寫入、webhook 派送/未設/錯誤吞掉、成交自動通知) |
| `test_stock_brokers.py` | CSV 解析、元大/Firstrade live fail loud、匯入後 CsvDataBroker 供應資料、台股端對端回測 |
| `test_paper_persistence.py` | 紙上帳戶持久化(跨實例載入、賣出後重載、reset 清除) |
| `test_risk_exit.py` | 停損/停利節點(觸發停損賣出、觸發停利賣出、區間內持有、無部位持有) |

共 **70** 項測試。`conftest.py` 在測試開始前建立所有資料表。

## 環境限制說明(Fail Loud)
本開發沙箱**封鎖對外網路**,因此無法在此對 Binance 真實抓取行情;相關程式路徑正確且會明確
回報 `502 NetworkError`。所有測試使用合成資料,故與網路無關、可完整通過。在有對外網路與
(必要時)API 金鑰的環境即可端對端驗證真實行情與下單。
