# 完善回測功能 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把後端已算出但前端未呈現的回測能力（豐富指標、權益曲線、交易明細）完整呈現，並接通 walk-forward 驗證、開放 timeframe/區間。

**Architecture:** 後端僅新增一個 `/api/backtest/walk-forward` endpoint 包裝既有 `validation.walk_forward`；其餘為前端工作——補齊 `lib/api.ts` 的 TS 型別、新增 `EquityChart` 元件、把 `BacktestPanel` 結果區改為分頁籤並加上 timeframe/limit 控制。資料流維持單一路徑（UI → api.ts → FastAPI router → 既有引擎函式）。

**Tech Stack:** 後端 FastAPI + Pydantic + pytest；前端 Next.js 14 App Router + TypeScript + lightweight-charts。

## Global Constraints

- Fail-loud：壞 fold / 壞 combo / API 錯誤都要顯示，絕不靜默跳過（CLAUDE.md）。
- 外觀全走 DESIGN.md token；電光青 `--accent` 僅限 AI / 自動化用途。
- 漲跌一律用 `--up` / `--down` token（class `text-up` / `text-down`），不硬寫綠漲紅跌（台股經 `data-market="tw"` 反向）。
- 不重寫已成熟的 `engine.py` / `metrics.py` / `optimize.py` / `validation.py` 邏輯。
- 外科手術式改動：只動回測相關檔，不順手清理周邊。
- Git flow：已在分支 `feature/backtest-enhancements`，最後開 PR，不直接推 `main`。
- 後端測試：`cd backend && pytest`（config 在 pyproject.toml，`-q`）。前端無 test runner，以 `npm run build` 通過驗證。

---

### Task 1: 後端 walk-forward API endpoint

**Files:**
- Modify: `backend/app/api/backtest.py`（在檔尾、`backtest()` 之前或之後新增；import 區加入 `walk_forward`/`WalkForwardReport`）
- Test: `backend/app/tests/test_backtest_api.py`（Create）

**Interfaces:**
- Consumes: `app.backtest.validation.walk_forward(candles, strategy_name, param_grid, n_folds, metric, anchored, max_combinations, starting_cash, position_fraction, market, timeframe) -> WalkForwardReport`；`app.brokers.registry.get_data_broker(market).get_ohlcv(symbol, timeframe, limit)`。
- Produces: `POST /api/backtest/walk-forward`，request body 對應 `WalkForwardRequest`，回傳 `WalkForwardReport`（含 `folds`、`aggregate_oos_metric`、`aggregate_oos_return_pct`）。

- [ ] **Step 1: 寫 failing 測試**

建立 `backend/app/tests/test_backtest_api.py`：

```python
"""API-level tests for the backtest router (walk-forward endpoint)."""

from __future__ import annotations

import math

from fastapi.testclient import TestClient

from app.main import app
from app.tests.helpers import StubBroker, make_candles

client = TestClient(app)

# Oscillating closes so ma_cross actually crosses within each fold.
_CLOSES = [100 + 10 * math.sin(i / 5) for i in range(200)]


def _stub_data_broker(monkeypatch):
    """Make the walk-forward endpoint use deterministic offline candles."""
    monkeypatch.setattr(
        "app.api.backtest.get_data_broker",
        lambda market: StubBroker({"BTC/USDT": 100.0}, candles=make_candles(_CLOSES)),
    )


def test_walk_forward_returns_fold_structure(monkeypatch):
    _stub_data_broker(monkeypatch)
    resp = client.post(
        "/api/backtest/walk-forward",
        json={
            "symbol": "BTC/USDT",
            "strategy": "ma_cross",
            "param_grid": {"fast": [5, 10], "slow": [20, 30]},
            "n_folds": 3,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["strategy"] == "ma_cross"
    assert body["n_folds"] == 3
    assert len(body["folds"]) == 3
    assert "aggregate_oos_metric" in body
    assert "aggregate_oos_return_pct" in body
    # each fold carries the in-sample vs out-of-sample structure
    for fold in body["folds"]:
        assert "best_params" in fold
        assert "oos_metric" in fold
        assert "oos_return_pct" in fold


def test_walk_forward_bad_n_folds_is_422(monkeypatch):
    _stub_data_broker(monkeypatch)
    resp = client.post(
        "/api/backtest/walk-forward",
        json={
            "symbol": "BTC/USDT",
            "strategy": "ma_cross",
            "param_grid": {"fast": [5, 10], "slow": [20, 30]},
            "n_folds": 1,
        },
    )
    # n_folds must be >= 2; FastAPI request-validation (Field ge=2) returns 422.
    assert resp.status_code == 422, resp.text
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `cd backend && pytest app/tests/test_backtest_api.py -q`
Expected: FAIL（404 — endpoint 尚未存在）

- [ ] **Step 3: 實作 endpoint**

在 `backend/app/api/backtest.py` 的 import 區，把 validation 的符號加進來。現有：

```python
from app.backtest.engine import BacktestResult, run_backtest
from app.backtest.optimize import OptimizeRow, grid_search
```

於其後新增：

```python
from app.backtest.validation import WalkForwardReport, walk_forward
```

在檔尾（最後一個 endpoint 之後）新增 request model 與 endpoint：

```python
class WalkForwardRequest(BaseModel):
    symbol: str
    market: MarketKind = MarketKind.crypto
    timeframe: str = "1h"
    limit: int = Field(default=500, ge=10, le=1000)
    strategy: str = "ma_cross"
    param_grid: dict[str, list] = Field(default_factory=dict)
    n_folds: int = Field(default=4, ge=2, le=20)
    metric: str = "sharpe"
    anchored: bool = True
    max_combinations: int = Field(default=200, ge=1, le=500)


@router.post("/walk-forward", response_model=WalkForwardReport)
def walk_forward_endpoint(req: WalkForwardRequest) -> WalkForwardReport:
    """Walk-forward (anchored/rolling) out-of-sample validation of a strategy's parameters.

    Picks best params per fold on the in-sample window by a risk-adjusted ``metric`` and scores
    them on the following out-of-sample window; ranking by raw return is deliberately unavailable
    (the overfitting trap). Fails loud on bad inputs.
    """
    try:
        candles = get_data_broker(req.market).get_ohlcv(req.symbol, req.timeframe, req.limit)
        return walk_forward(
            candles,
            req.strategy,
            req.param_grid,
            n_folds=req.n_folds,
            metric=req.metric,
            anchored=req.anchored,
            max_combinations=req.max_combinations,
            starting_cash=100_000.0,
            position_fraction=1.0,
            market=req.market,
            timeframe=req.timeframe,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"{type(exc).__name__}: {exc}")
```

- [ ] **Step 4: 跑測試確認通過**

Run: `cd backend && pytest app/tests/test_backtest_api.py -q`
Expected: PASS（2 passed）

- [ ] **Step 5: 跑全套後端測試確認無回歸**

Run: `cd backend && pytest -q`
Expected: 全綠（既有測試不受影響）

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/backtest.py backend/app/tests/test_backtest_api.py
git commit -m "feat(backtest): expose walk-forward validation via API

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: 前端型別補齊與 walk-forward client 方法

**Files:**
- Modify: `frontend/lib/api.ts`（`BacktestResult` 介面約 130–140 行；新增介面；`api` 物件約 302–303 行後加方法）

**Interfaces:**
- Consumes: 後端 `BacktestResult`（已含這些欄位）、`WalkForwardReport`。
- Produces:
  - 擴充後的 `BacktestResult`（含 metrics 與 `trades: Trade[]`）。
  - `Trade`、`WalkForwardRequest`、`FoldResult`、`WalkForwardReport` 介面。
  - `api.walkForward(req: WalkForwardRequest) => Promise<WalkForwardReport>`。

- [ ] **Step 1: 擴充 `BacktestResult` 並新增 `Trade`**

把 `frontend/lib/api.ts` 現有：

```ts
export interface BacktestResult {
  starting_cash: number;
  final_equity: number;
  total_return_pct: number;
  buy_hold_return_pct: number;
  num_trades: number;
  wins: number;
  win_rate: number;
  max_drawdown_pct: number;
  equity_curve: EquityPoint[];
}
```

替換為（新增 metrics 欄位與 `trades`；對應 `backend/app/backtest/engine.py:BacktestResult`）：

```ts
export interface Trade {
  entry_time: string;
  exit_time: string;
  entry_price: number;
  exit_price: number;
  quantity: number;
  pnl: number; // net of costs
  gross_pnl: number;
  cost: number;
  return_pct: number;
}

export interface BacktestResult {
  starting_cash: number;
  final_equity: number;
  total_return_pct: number;
  buy_hold_return_pct: number;
  num_trades: number;
  wins: number;
  win_rate: number;
  max_drawdown_pct: number;
  cagr: number;
  annualized_volatility: number;
  sharpe: number;
  sortino: number;
  calmar: number;
  profit_factor: number | null;
  avg_win: number;
  avg_loss: number;
  exposure_pct: number;
  max_consecutive_losses: number;
  turnover: number;
  trades: Trade[];
  equity_curve: EquityPoint[];
}
```

- [ ] **Step 2: 新增 walk-forward 型別**

在 `OptimizeRequest` 介面（約 202 行 `}` 結尾）之後新增（對應 `backend/app/backtest/validation.py`）：

```ts
export interface WalkForwardRequest {
  symbol: string;
  market?: string;
  timeframe?: string;
  limit?: number;
  strategy: string;
  param_grid: Record<string, number[]>;
  n_folds?: number;
  metric?: string; // "sharpe" | "sortino" | "calmar" | "return_over_maxdd"
  anchored?: boolean;
  max_combinations?: number;
}

export interface FoldResult {
  fold: number;
  best_params: Record<string, number>;
  train_start: number;
  train_end: number;
  test_start: number;
  test_end: number;
  train_size: number;
  test_size: number;
  is_metric: number;
  oos_metric: number;
  is_return_pct: number;
  oos_return_pct: number;
  oos_max_drawdown_pct: number;
  error: string | null;
}

export interface WalkForwardReport {
  strategy: string;
  metric: string;
  n_folds: number;
  anchored: boolean;
  folds: FoldResult[];
  aggregate_oos_metric: number;
  aggregate_oos_return_pct: number;
}
```

- [ ] **Step 3: 新增 client 方法**

在 `api` 物件的 `optimize: ...` 行（約 302–303 行）之後新增：

```ts
  walkForward: (req: WalkForwardRequest) =>
    request<WalkForwardReport>("/api/backtest/walk-forward", {
      method: "POST",
      body: JSON.stringify(req),
    }),
```

- [ ] **Step 4: 型別檢查（build）**

Run: `cd frontend && npx tsc --noEmit`
Expected: 無錯誤（注意：`BacktestPanel.tsx` 此時尚未用到新欄位，故不會報錯）

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/api.ts
git commit -m "feat(backtest): type full BacktestResult metrics + trades + walk-forward client

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: `EquityChart` 權益曲線元件

**Files:**
- Create: `frontend/components/EquityChart.tsx`

**Interfaces:**
- Consumes: `EquityPoint[]`（from `@/lib/api`）、lightweight-charts、CSS token。
- Produces: `export function EquityChart({ points, height }: { points: EquityPoint[]; height?: number })`。

- [ ] **Step 1: 建立元件**

建立 `frontend/components/EquityChart.tsx`（沿用 `CandleChart.tsx` 的 CSS-token 取色 / resize / cleanup 慣例，改用 line series；上漲綠跌紅依終值 vs 起值，用 `--up/--down` token）：

```tsx
"use client";

import { createChart, ColorType, LineStyle, type UTCTimestamp } from "lightweight-charts";
import { useEffect, useRef } from "react";
import type { EquityPoint } from "@/lib/api";

export function EquityChart({ points, height = 280 }: { points: EquityPoint[]; height?: number }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || points.length < 2) return;
    const css = getComputedStyle(document.documentElement);
    const v = (n: string, f: string) => css.getPropertyValue(n).trim() || f;
    const up = v("--up", "#34D399");
    const down = v("--down", "#F87171");
    const bg = v("--bg", "#0A0B0D");
    const gridColor = v("--border", "#1f1f1f");
    const textColor = v("--muted", "#8A9099");

    const isUp = points[points.length - 1].equity >= points[0].equity;

    const chart = createChart(containerRef.current, {
      layout: { background: { type: ColorType.Solid, color: bg }, textColor },
      grid: { vertLines: { color: gridColor }, horzLines: { color: gridColor } },
      width: containerRef.current.clientWidth,
      height,
      timeScale: { timeVisible: true },
    });
    const series = chart.addLineSeries({
      color: isUp ? up : down,
      lineWidth: 2,
      lineStyle: LineStyle.Solid,
      priceLineVisible: false,
    });
    series.setData(
      points.map((p) => ({
        time: (new Date(p.timestamp).getTime() / 1000) as UTCTimestamp,
        value: p.equity,
      })),
    );
    chart.timeScale().fitContent();

    const onResize = () => chart.applyOptions({ width: containerRef.current!.clientWidth });
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.remove();
    };
  }, [points, height]);

  if (points.length < 2) return null;
  return <div ref={containerRef} className="w-full" />;
}
```

- [ ] **Step 2: 型別檢查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 無錯誤

- [ ] **Step 3: Commit**

```bash
git add frontend/components/EquityChart.tsx
git commit -m "feat(backtest): add EquityChart line component (lightweight-charts)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: `BacktestPanel` — timeframe/limit 控制 + 分頁籤（概覽 + 交易）

**Files:**
- Modify: `frontend/components/BacktestPanel.tsx`

**Interfaces:**
- Consumes: Task 2 的型別、Task 3 的 `EquityChart`、`api.backtest`/`compareStrategies`/`optimize`/`backtestSavedStrategy`。
- Produces: 帶 `timeframe`/`limit` state 的控制列；結果區分頁籤；`ResultTab` 型別 `"overview" | "trades" | "walkforward"`。（walk-forward 分頁與動作在 Task 5 補。）

- [ ] **Step 1: 加入 timeframe/limit state 與控制列下拉**

在 `BacktestPanel` 既有 state 區（`const [saved, ...]` 之後）新增：

```tsx
  const [timeframe, setTimeframe] = useState("1h");
  const [limit, setLimit] = useState(500);
  const [tab, setTab] = useState<"overview" | "trades" | "walkforward">("overview");
```

並在檔案頂部（`SAVED_PREFIX` 常數附近）新增選項常數：

```tsx
const TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"];
const LIMITS = [200, 500, 1000];
```

在控制列 symbol `<input>`（約 145–150 行）之後、strategy `<select>` 之前，插入兩個下拉：

```tsx
        <select
          value={timeframe}
          onChange={(e) => setTimeframe(e.target.value)}
          className="rounded-md bg-surface-2 px-2 py-1 text-sm"
        >
          {TIMEFRAMES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <select
          value={limit}
          onChange={(e) => setLimit(Number(e.target.value))}
          className="rounded-md bg-surface-2 px-2 py-1 text-sm"
        >
          {LIMITS.map((n) => (
            <option key={n} value={n}>
              {n} bars
            </option>
          ))}
        </select>
```

- [ ] **Step 2: 讓三個動作改吃 `timeframe`/`limit` state**

把 `run()`、`compare()`、`optimize()` 內寫死的 `timeframe: "1h", limit: 500` 全部換成 `timeframe, limit`。具體三處：

`run()` 內：
```tsx
      const res =
        isSaved && savedId != null
          ? await api.backtestSavedStrategy(savedId, { symbol, market, timeframe, limit })
          : await api.backtest({ symbol, market, strategy, params, timeframe, limit });
```

`compare()` 內：
```tsx
      setComparison(await api.compareStrategies({ symbol, market, timeframe, limit }));
```

`optimize()` 內（保留既有 split/rank_metric）：
```tsx
        await api.optimize({
          symbol,
          market,
          strategy,
          param_grid: OPTIMIZE_GRID[strategy],
          timeframe,
          limit,
          split: true,
          rank_metric: "oos_sharpe",
        }),
```

- [ ] **Step 3: `run()` 成功後切回概覽分頁**

在 `run()` 的 `setResult(res);` 之後加一行，確保新跑的結果落在概覽頁：

```tsx
      setResult(res);
      setTab("overview");
```

- [ ] **Step 4: 把結果區（`result` 區塊）改成分頁籤 + 完整指標 + 權益圖 + 交易表**

於檔案頂部加入 `EquityChart` import：

```tsx
import { EquityChart } from "@/components/EquityChart";
```

把現有的 `{result && ( ... )}` 區塊（約 213–223 行，含 Sparkline 與 4 個 Metric）整段替換為：

```tsx
      {result && (
        <div className="space-y-3">
          <div className="flex gap-2 border-b border-border text-sm">
            {(["overview", "trades", "walkforward"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-3 py-1.5 ${
                  tab === t ? "border-b-2 border-accent text-text" : "text-muted hover:text-text"
                }`}
              >
                {t === "overview" ? "概覽" : t === "trades" ? "交易" : "Walk-forward"}
              </button>
            ))}
          </div>

          {tab === "overview" && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
                <Metric label="Return" value={pct(result.total_return_pct)} good={result.total_return_pct >= 0} />
                <Metric label="Buy & Hold" value={pct(result.buy_hold_return_pct)} good={result.buy_hold_return_pct >= 0} />
                <Metric label="CAGR" value={pct(result.cagr)} good={result.cagr >= 0} />
                <Metric label="Max DD" value={pct(-result.max_drawdown_pct)} good={false} />
                <Metric label="Sharpe" value={result.sharpe.toFixed(2)} good={result.sharpe >= 0} />
                <Metric label="Sortino" value={result.sortino.toFixed(2)} good={result.sortino >= 0} />
                <Metric label="Win rate" value={`${result.win_rate.toFixed(0)}%`} />
                <Metric
                  label="Profit factor"
                  value={result.profit_factor == null ? "∞" : result.profit_factor.toFixed(2)}
                  good={result.profit_factor == null ? true : result.profit_factor >= 1}
                />
              </div>
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
                <span>Calmar {result.calmar.toFixed(2)}</span>
                <span>Vol {pct(result.annualized_volatility * 100)}</span>
                <span>Exposure {result.exposure_pct.toFixed(0)}%</span>
                <span>Turnover {result.turnover.toFixed(2)}×</span>
                <span>Max consec. losses {result.max_consecutive_losses}</span>
                <span>Trades {result.num_trades}</span>
              </div>
              <EquityChart points={result.equity_curve} />
            </div>
          )}

          {tab === "trades" && (
            <div className="max-h-80 overflow-y-auto">
              {result.trades.length === 0 ? (
                <p className="text-sm text-muted">No trades.</p>
              ) : (
                <table className="w-full text-left text-xs">
                  <thead className="text-faint">
                    <tr>
                      <th className="py-1">Entry</th>
                      <th>Exit</th>
                      <th className="num">Entry px</th>
                      <th className="num">Exit px</th>
                      <th className="num">Qty</th>
                      <th className="num">Return%</th>
                      <th className="num">Net PnL</th>
                      <th className="num">Cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.trades.map((t, i) => (
                      <tr key={i} className="border-t border-border">
                        <td className="py-1 font-mono">{t.entry_time.slice(0, 16).replace("T", " ")}</td>
                        <td className="font-mono">{t.exit_time.slice(0, 16).replace("T", " ")}</td>
                        <td className="num">{t.entry_price.toFixed(2)}</td>
                        <td className="num">{t.exit_price.toFixed(2)}</td>
                        <td className="num">{t.quantity.toFixed(4)}</td>
                        <td className={`num ${t.return_pct >= 0 ? "text-up" : "text-down"}`}>{pct(t.return_pct)}</td>
                        <td className={`num ${t.pnl >= 0 ? "text-up" : "text-down"}`}>{t.pnl.toFixed(2)}</td>
                        <td className="num text-muted">{t.cost.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {tab === "walkforward" && (
            <p className="text-sm text-muted">Walk-forward 將在下一步加入。</p>
          )}
        </div>
      )}
```

> 註：`Sparkline` 元件（檔頂約 18–39 行）不再被引用後會造成 unused 警告；於 Step 5 一併刪除 `Sparkline` 函式定義以保持乾淨（外科手術範圍內，因為它專屬此面板）。

- [ ] **Step 5: 刪除未使用的 `Sparkline`**

刪除 `frontend/components/BacktestPanel.tsx` 頂部的 `Sparkline` 函式（`function Sparkline(...) { ... }` 整段，約 18–39 行）與其上方相關 import（`EquityPoint` 若仍被其他處引用則保留；此檔不再直接用到 `EquityPoint`，可從 import 移除）。

- [ ] **Step 6: lint + build**

Run: `cd frontend && npm run lint && npm run build`
Expected: lint 無 error（無 unused 變數）、build 成功

- [ ] **Step 7: Commit**

```bash
git add frontend/components/BacktestPanel.tsx
git commit -m "feat(backtest): tabbed results with full metrics, equity chart, trade list + timeframe/limit controls

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: BacktestPanel — Walk-forward 動作與分頁內容

**Files:**
- Modify: `frontend/components/BacktestPanel.tsx`

**Interfaces:**
- Consumes: Task 2 的 `api.walkForward` / `WalkForwardReport`、Task 4 的 `tab` state 與分頁籤骨架、`OPTIMIZE_GRID`。
- Produces: `walkforward` state + `runWalkForward()` action + 「Run walk-forward」按鈕 + walk-forward 分頁表格。

- [ ] **Step 1: 新增 state 與 import**

在 import 區補上型別：

```tsx
import {
  api,
  MARKETS,
  type BacktestResult,
  type CompareRow,
  type OptimizeRow,
  type StrategyListItem,
  type WalkForwardReport,
} from "@/lib/api";
```

（注意：若 Task 4 已移除 `EquityPoint` import，這裡維持移除狀態。）

在 state 區新增：

```tsx
  const [walkforward, setWalkforward] = useState<WalkForwardReport | null>(null);
```

並在 `resetOutputs()` 內加入 `setWalkforward(null);`。

- [ ] **Step 2: 新增 `runWalkForward()` action**

在 `compare()` 之後新增（僅內建策略；沿用 OPTIMIZE_GRID；跑完切到 walk-forward 分頁並讓結果區顯示——為了讓分頁籤容器顯示，需有 `result`，故 walk-forward 結果用獨立顯示區塊，見 Step 4）：

```tsx
  async function runWalkForward() {
    setLoading(true);
    resetOutputs();
    try {
      setWalkforward(
        await api.walkForward({
          symbol,
          market,
          strategy,
          param_grid: OPTIMIZE_GRID[strategy],
          timeframe,
          limit,
          n_folds: 4,
          metric: "sharpe",
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }
```

- [ ] **Step 3: 新增「Run walk-forward」按鈕**

在控制列 `Optimize` 按鈕（約 200–208 行 `</button>`）之後新增：

```tsx
        <button
          onClick={runWalkForward}
          disabled={loading || isSaved}
          title={isSaved ? "Walk-forward 僅支援內建策略" : undefined}
          className="rounded-md bg-surface-2 text-text border border-border-strong px-3 py-1 text-sm font-medium hover:bg-surface-3 disabled:opacity-50"
        >
          Walk-forward
        </button>
```

- [ ] **Step 4: 新增 walk-forward 結果顯示區塊**

walk-forward 不依賴單次 `result`，用獨立區塊呈現。在 `{comparison && ( ... )}` 區塊之後（`</section>` 之前）新增：

```tsx
      {walkforward && (
        <div className="space-y-2">
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
            <span className="text-muted">
              {walkforward.strategy} · {walkforward.metric} · {walkforward.anchored ? "anchored" : "rolling"} ·{" "}
              {walkforward.n_folds} folds
            </span>
            <span className={walkforward.aggregate_oos_return_pct >= 0 ? "text-up" : "text-down"}>
              Agg OOS return {pct(walkforward.aggregate_oos_return_pct)}
            </span>
            <span className="text-muted">Agg OOS {walkforward.metric} {walkforward.aggregate_oos_metric.toFixed(2)}</span>
          </div>
          <table className="w-full text-left text-xs">
            <thead className="text-faint">
              <tr>
                <th className="py-1">Fold</th>
                <th>Best params</th>
                <th className="num">IS {walkforward.metric}</th>
                <th className="num">OOS {walkforward.metric}</th>
                <th className="num">OOS Ret</th>
                <th className="num">OOS Max DD</th>
              </tr>
            </thead>
            <tbody>
              {walkforward.folds.map((f) => (
                <tr key={f.fold} className="border-t border-border">
                  <td className="py-1">{f.fold}</td>
                  {f.error ? (
                    <td colSpan={5} className="text-error">
                      {f.error}
                    </td>
                  ) : (
                    <>
                      <td className="font-mono">
                        {Object.entries(f.best_params)
                          .map(([k, v]) => `${k}=${v}`)
                          .join(", ")}
                      </td>
                      <td className="num">{f.is_metric.toFixed(2)}</td>
                      <td className={`num ${f.oos_metric >= 0 ? "text-up" : "text-down"}`}>{f.oos_metric.toFixed(2)}</td>
                      <td className={`num ${f.oos_return_pct >= 0 ? "text-up" : "text-down"}`}>{pct(f.oos_return_pct)}</td>
                      <td className="num text-down">{pct(-f.oos_max_drawdown_pct)}</td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
```

> 說明：Task 4 在 `result` 分頁籤內的 `walkforward` 分頁僅是佔位提示；walk-forward 結果採此獨立區塊呈現（與 Compare/Optimize 同層級），因為它是獨立動作、不綁定單次回測。Task 4 分頁籤的佔位文字可保留（當使用者剛跑完單次回測、切到該分頁時提示去按 Run walk-forward 鈕）。

- [ ] **Step 5: lint + build**

Run: `cd frontend && npm run lint && npm run build`
Expected: lint 無 error、build 成功

- [ ] **Step 6: Commit**

```bash
git add frontend/components/BacktestPanel.tsx
git commit -m "feat(backtest): wire walk-forward action and per-fold report UI

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: 端到端手動驗證

**Files:** 無（驗證任務）

- [ ] **Step 1: 啟動後端**

Run: `cd backend && source .venv/bin/activate && uvicorn app.main:app --reload`
Expected: 啟動於 http://localhost:8000，`/docs` 可見 `POST /api/backtest/walk-forward`

- [ ] **Step 2: 啟動前端**

Run: `cd frontend && npm run dev`
Expected: http://localhost:3000

- [ ] **Step 3: 在交易室回測頁逐項驗證**

開 `/trading-room/backtest`，確認：
- timeframe / limit 下拉可切換並影響結果。
- 「Run」後概覽分頁顯示完整指標卡（含 Sharpe/Sortino/CAGR/Profit factor）與權益曲線圖（漲跌色正確）。
- 「交易」分頁列出每筆交易；Net PnL / Return% 依正負以 `--up/--down` 上色。
- 「Compare all」「Optimize」維持原行為。
- 「Walk-forward」按鈕跑出各 fold 表與 aggregate OOS 數字；切到非內建（策略庫）策略時該鈕 disabled。
- 任一動作失敗時（如不存在的 symbol）顯示紅字錯誤，不靜默。

- [ ] **Step 4: 回報驗證結果**

把實際觀察（含任何未過項目）如實記錄；若有問題回到對應 Task 修正。

---

## Self-Review

**Spec coverage：**
- 呈現完整指標 → Task 2（型別）+ Task 4 概覽分頁。✅
- 真正權益曲線 + 交易明細 → Task 3（EquityChart）+ Task 4（概覽圖 + 交易分頁）。✅
- 接通 walk-forward → Task 1（API）+ Task 2（型別/client）+ Task 5（UI）。✅
- 可調 timeframe/區間 → Task 4 Step 1–2。✅
- Fail-loud / DESIGN.md token / 不改核心 / git flow → Global Constraints + 各 Task。✅
- 測試：後端 Task 1（新 API 測試 + 全套回歸）；前端 build/lint + Task 6 手動驗證。✅

**Placeholder scan：** 各 step 皆含實際程式碼/指令與預期輸出；Task 4 的 walkforward 分頁佔位文字是刻意的 UX 提示（非未完成項），Task 5 說明已交代其與獨立區塊的關係。無 TBD/TODO。

**Type consistency：** `BacktestResult`/`Trade`/`WalkForwardReport`/`FoldResult` 欄位與後端 `engine.py`/`validation.py` 對齊；`api.walkForward` 簽章與 Task 5 呼叫一致；`tab` 型別 `"overview" | "trades" | "walkforward"` 在 Task 4 定義、Task 5 沿用；`runWalkForward` 名稱前後一致。
