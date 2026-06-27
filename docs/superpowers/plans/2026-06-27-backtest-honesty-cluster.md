# Backtest Honesty Cluster (Now-1/2/3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the backtester statistically honest and reproducible — correct stock annualization, a non-zero disclosed slippage default, risk-adjusted compare ranking, a persisted run registry with an "Honesty Bar" surfacing hidden assumptions, and deterministic + metered AI-signal backtests.

**Architecture:** Three independent backend-first slices on top of the existing pure backtester (`backtest/engine.py`, `metrics.py`) and the existing run-persistence pattern (`workflow/run_store.py` + `WorkflowRun` table). Part A hardens the metric/cost layer; Part B adds a `BacktestRun` table + an assumptions object surfaced by two new React components; Part C adds a DB-backed AI response cache + token/latency metering so AI backtests are reproducible run-to-run. Each task is TDD (backend) or build-verified (frontend).

**Tech Stack:** Python 3.11, FastAPI, SQLModel (SQLite), pydantic, pytest (backend, config in `backend/pyproject.toml`, run with `-q`); Next.js 14 App Router + TypeScript + React Query (frontend, no test runner — verify with `npm run build`). The `ta` library for indicators. `instructor` + Anthropic SDK for structured LLM output.

## Global Constraints

- **Branch, never `main`.** All work on a branch `feat/backtest-honesty`; open a PR at the end. (Repo rule: never commit directly to `main`.)
- **Fail loud.** Missing data / external errors / risk violations raise explicitly — never silently skipped.
- **Costs ON by default; zero-cost numbers are dishonest** (existing convention, `config.py:147-148`). Slippage becomes part of that default.
- **Determinism in tests.** Backtest unit tests that assert exact numbers pass `cost_model=CostModel.zero()` (see `test_backtest.py:97,128`) — do not change those.
- **Market-aware color is frontend-only** and out of scope here; this plan touches no `--up`/`--down` logic.
- **`periods_per_year` default must stay `market=crypto`** so existing `test_metrics.py:12-16` assertions remain valid.
- **No new dependencies.** `instructor`, `anthropic`, `sqlmodel`, `pydantic` are already present.
- **Backend test command:** `cd backend && pytest -q` (full suite must stay green after every task).

---

### Task 1: Market-aware annualization (`periods_per_year(timeframe, market)`)

Stock metrics are inflated because daily bars annualize over 365.25 calendar days instead of 252 trading days (Sharpe/vol overstated ~×1.2; intraday far worse). Make annualization market-aware; crypto (24/7) is unchanged.

**Files:**
- Modify: `backend/app/backtest/metrics.py:18-35` (constants + `periods_per_year`)
- Modify: `backend/app/backtest/engine.py:174` (pass `market`)
- Modify: `backend/app/backtest/workflow_backtest.py:182-196` (thread `market` into `_assemble_result`)
- Test: `backend/app/tests/test_metrics.py` (add cases)

**Interfaces:**
- Produces: `metrics.periods_per_year(timeframe: str, market: MarketKind = MarketKind.crypto) -> float`. Consumed by `engine.run_backtest` and `workflow_backtest._assemble_result`.

- [ ] **Step 1: Write the failing test** — append to `backend/app/tests/test_metrics.py`:

```python
from app.schemas import MarketKind


def test_periods_per_year_crypto_unchanged():
    # default market is crypto (24/7) — existing behaviour preserved.
    assert metrics.periods_per_year("1h") == pytest.approx(8766.0)
    assert metrics.periods_per_year("1d", MarketKind.crypto) == pytest.approx(365.25)


def test_periods_per_year_stocks_use_trading_calendar():
    # Daily stock bars: 252 trading days/year, not 365.25.
    assert metrics.periods_per_year("1d", MarketKind.tw_stock) == pytest.approx(252.0)
    assert metrics.periods_per_year("1d", MarketKind.us_stock) == pytest.approx(252.0)
    # Weekly: 52 trading weeks.
    assert metrics.periods_per_year("1w", MarketKind.us_stock) == pytest.approx(52.0)
    # Intraday US (6.5h session): 1h -> 252 * 6.5 = 1638 bars/yr.
    assert metrics.periods_per_year("1h", MarketKind.us_stock) == pytest.approx(1638.0)
    # Intraday TW (4.5h session): 30m -> 252 * (16200/1800) = 252 * 9 = 2268.
    assert metrics.periods_per_year("30m", MarketKind.tw_stock) == pytest.approx(2268.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest app/tests/test_metrics.py -q`
Expected: FAIL — `periods_per_year()` takes 1 positional arg / `MarketKind` import unused until impl.

- [ ] **Step 3: Implement market-aware annualization** — in `backend/app/backtest/metrics.py`, replace the constants block (lines 18-19) and `periods_per_year` (lines 23-35):

```python
from app.schemas import MarketKind

_SECONDS_PER_YEAR = 365.25 * 24 * 3600
_UNIT_SECONDS = {"m": 60, "h": 3600, "d": 86400, "w": 604800}
_TRADING_DAYS_PER_YEAR = 252.0
_TRADING_WEEKS_PER_YEAR = 52.0
# Regular cash-session length per equity market (seconds): TW 09:00-13:30 = 4.5h; US 09:30-16:00 = 6.5h.
_STOCK_SESSION_SECONDS = {
    MarketKind.tw_stock: 4.5 * 3600,
    MarketKind.us_stock: 6.5 * 3600,
}
_EPS = 1e-12  # keep existing constant below this block


def periods_per_year(timeframe: str, market: MarketKind = MarketKind.crypto) -> float:
    """Bars per year for a ccxt-style timeframe.

    Crypto (24/7) uses the calendar-second basis (``"1h"`` -> 8766, ``"1d"`` -> 365.25).
    Equities use a TRADING calendar — 252 trading days/year, intraday scaled by the cash session
    length — so daily stock Sharpe/vol are not inflated ~1.2x by counting 365 days.
    """
    tf = timeframe.strip().lower()
    num = ""
    i = 0
    while i < len(tf) and tf[i].isdigit():
        num += tf[i]
        i += 1
    unit = tf[i:]
    if not num or unit not in _UNIT_SECONDS:
        raise ValueError(f"unsupported timeframe for annualisation: {timeframe!r}")
    n = int(num)
    session = _STOCK_SESSION_SECONDS.get(market)
    if session is None:  # crypto / 24-7 — unchanged calendar-second basis
        return _SECONDS_PER_YEAR / (n * _UNIT_SECONDS[unit])
    if unit == "d":
        return _TRADING_DAYS_PER_YEAR / n
    if unit == "w":
        return _TRADING_WEEKS_PER_YEAR / n
    bars_per_session = session / (n * _UNIT_SECONDS[unit])  # intraday
    return _TRADING_DAYS_PER_YEAR * bars_per_session
```

Note: the existing `_EPS = 1e-12` line stays; only the two constant lines above it and the function body change. Keep `_SECONDS_PER_YEAR`/`_UNIT_SECONDS` names.

- [ ] **Step 4: Thread `market` into both call sites**

In `backend/app/backtest/engine.py:174` change:
```python
    ppy = metrics.periods_per_year(timeframe, market)
```

In `backend/app/backtest/workflow_backtest.py`, change the `_assemble_result` call (lines 182-184) and its signature (line 187-189):
```python
    return _assemble_result(
        sim, equity_curve, starting_cash, timeframe, market, rf, bars_in_pos, max_dd, symbols, signals, histories
    )


def _assemble_result(
    sim, equity_curve, starting_cash, timeframe, market, rf, bars_in_pos, max_dd, symbols, signals, histories
) -> WorkflowBacktestResult:
```
and inside it (line 196):
```python
    ppy = metrics.periods_per_year(timeframe, market)
```

- [ ] **Step 5: Run the metrics + backtest tests**

Run: `cd backend && pytest app/tests/test_metrics.py app/tests/test_backtest.py app/tests/test_workflow_backtest.py -q`
Expected: PASS (crypto unchanged → old assertions hold; new stock cases pass).

- [ ] **Step 6: Run the full suite**

Run: `cd backend && pytest -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/backtest/metrics.py backend/app/backtest/engine.py backend/app/backtest/workflow_backtest.py backend/app/tests/test_metrics.py
git commit -m "fix(backtest): market-aware annualization (252 trading days for stocks)"
```

---

### Task 2: Non-zero, disclosed slippage default

A `0.0` slippage default makes every fill price optimistic. Set a conservative non-zero default and document it; the Honesty Bar (Task 6) surfaces the value.

**Files:**
- Modify: `backend/app/config.py:156`
- Modify: `.env.example` (repo root — add/adjust the slippage var)
- Test: `backend/app/tests/test_costs_default.py` (new)

**Interfaces:**
- Produces: `settings.cost_slippage_bps == 5.0` by default → flows through `CostModel.from_settings()` (`costs.py:68`).

- [ ] **Step 1: Write the failing test** — create `backend/app/tests/test_costs_default.py`:

```python
"""The default cost model must apply non-zero slippage (zero is dishonest)."""
from __future__ import annotations

from app.config import Settings
from app.trading.costs import CostModel


def test_default_slippage_is_nonzero():
    assert Settings().cost_slippage_bps == 5.0


def test_cost_model_from_settings_carries_slippage():
    model = CostModel.from_settings(Settings())
    assert model.slippage_bps == 5.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest app/tests/test_costs_default.py -q`
Expected: FAIL — default is `0.0`.

- [ ] **Step 3: Change the default** — `backend/app/config.py:156`:

```python
    cost_slippage_bps: float = 5.0  # 固定滑價 (買進成交較高、賣出較低). 保守非零預設 — 零滑價會高估成交品質; Next 階段升級為 size/liquidity-aware 模型.
```

- [ ] **Step 4: Document it in `.env.example`** — add (or update) the line under the transaction-cost section:

```bash
# Fixed slippage in basis points applied to every paper + backtest fill (buy fills higher, sell lower).
# Conservative non-zero default; 0 overstates fill quality. Surfaced in the backtest Honesty Bar.
COST_SLIPPAGE_BPS=5.0
```

- [ ] **Step 5: Run the full suite**

Run: `cd backend && pytest -q`
Expected: PASS. (The two exact-number backtest tests use `CostModel.zero()` so they are unaffected; if any other test asserts an exact default-cost equity figure it should be updated to the new value the assertion prints — the slippage change is intentional and the new number is the correct one.)

- [ ] **Step 6: Commit**

```bash
git add backend/app/config.py .env.example backend/app/tests/test_costs_default.py
git commit -m "fix(costs): conservative non-zero default slippage (5 bps), disclosed"
```

---

### Task 3: Compare ranks by Sharpe + exposes Sharpe / Buy&Hold

`/api/backtest/compare` ranks by raw `total_return_pct` and the frontend crowns the top return with 🏆 — rewarding the riskiest fit. Rank by risk-adjusted Sharpe and expose it.

**Files:**
- Modify: `backend/app/api/backtest.py:127-134` (`CompareRow`), `:162-184` (populate + sort)
- Test: `backend/app/tests/test_compare_ranking.py` (new)

**Interfaces:**
- Produces: `CompareRow` gains `sharpe: float`; rows sorted by `sharpe` desc. Frontend (Task 6) reads `row.sharpe`.

- [ ] **Step 1: Write the failing test** — create `backend/app/tests/test_compare_ranking.py`:

```python
"""compare endpoint must rank by risk-adjusted Sharpe and expose it."""
from __future__ import annotations

from datetime import datetime, timedelta

import app.api.backtest as bt
from app.api.backtest import CompareRequest, compare
from app.schemas import Candle


def _candles(closes):
    t0 = datetime(2024, 1, 1)
    out = []
    for i, c in enumerate(closes):
        out.append(Candle(timestamp=t0 + timedelta(hours=i), open=c, high=c, low=c, close=c, volume=1.0))
    return out


class _FakeBroker:
    def __init__(self, candles):
        self._candles = candles

    def get_ohlcv(self, symbol, timeframe, limit):
        return self._candles[:limit]

    def get_ohlcv_range(self, symbol, timeframe, start, end):
        return self._candles


def test_compare_sorts_by_sharpe_and_exposes_it(monkeypatch):
    # Trending series so multiple built-ins actually trade.
    candles = _candles([100 + (i % 7) - 3 + i * 0.5 for i in range(120)])
    monkeypatch.setattr(bt, "get_data_broker", lambda market: _FakeBroker(candles))
    rows = compare(CompareRequest(symbol="BTC/USDT", limit=120, strategies=["ma_cross", "rsi"]))
    assert all(hasattr(r, "sharpe") for r in rows)
    sharpes = [r.sharpe for r in rows if r.error is None]
    assert sharpes == sorted(sharpes, reverse=True)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest app/tests/test_compare_ranking.py -q`
Expected: FAIL — `CompareRow` has no `sharpe` attribute.

- [ ] **Step 3: Add the field + populate + re-sort** — `backend/app/api/backtest.py`:

In `CompareRow` (after line 129 `total_return_pct: float`) add:
```python
    sharpe: float
```

In the success append (lines 162-171) add `sharpe=result.sharpe,` to the `CompareRow(...)`:
```python
            rows.append(
                CompareRow(
                    strategy=name,
                    total_return_pct=result.total_return_pct,
                    buy_hold_return_pct=result.buy_hold_return_pct,
                    num_trades=result.num_trades,
                    win_rate=result.win_rate,
                    max_drawdown_pct=result.max_drawdown_pct,
                    sharpe=result.sharpe,
                )
            )
```

In the error append (lines 173-182) add `sharpe=0.0,`:
```python
            rows.append(
                CompareRow(
                    strategy=name,
                    total_return_pct=0.0,
                    buy_hold_return_pct=0.0,
                    num_trades=0,
                    win_rate=0.0,
                    max_drawdown_pct=0.0,
                    sharpe=0.0,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
```

Change the sort (line 184) and update the docstring (line 139):
```python
    rows.sort(key=lambda r: r.sharpe, reverse=True)
```
Docstring line 139 → `"""Run several strategies over the same history and rank them by risk-adjusted Sharpe (fetch once)."""`

- [ ] **Step 4: Run the test + compare API test**

Run: `cd backend && pytest app/tests/test_compare_ranking.py app/tests/test_backtest_api.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/backtest.py backend/app/tests/test_compare_ranking.py
git commit -m "fix(backtest): rank compare by Sharpe, expose sharpe column"
```

---

### Task 4: `BacktestAssumptions` + pure honesty assessment

A pure, testable function that turns the hidden assumptions behind a result into explicit warnings, attached to every `BacktestResult`.

**Files:**
- Create: `backend/app/backtest/honesty.py`
- Modify: `backend/app/backtest/engine.py:36-58` (add `assumptions` field), `:177-199` (populate)
- Test: `backend/app/tests/test_honesty.py` (new)

**Interfaces:**
- Produces: `honesty.BacktestAssumptions` model and `honesty.assess(*, slippage_bps, cost_taker_bps, bars, num_trades, timeframe, market, oos_selected=False) -> BacktestAssumptions`; `honesty.representative_cost_bps(market, settings) -> float`. `BacktestResult.assumptions: BacktestAssumptions | None`.

- [ ] **Step 1: Write the failing test** — create `backend/app/tests/test_honesty.py`:

```python
from __future__ import annotations

from app.backtest.honesty import assess, representative_cost_bps
from app.config import Settings
from app.schemas import MarketKind


def test_warns_on_zero_slippage_low_trades_few_bars():
    a = assess(slippage_bps=0.0, cost_taker_bps=7.5, bars=50, num_trades=3,
               timeframe="1h", market="crypto")
    joined = " ".join(a.warnings)
    assert "零滑價" in joined
    assert "樣本過少" in joined
    assert "K 線過少" in joined
    assert a.annualization_basis.startswith("365.25")


def test_clean_run_has_no_warnings():
    a = assess(slippage_bps=5.0, cost_taker_bps=7.5, bars=500, num_trades=40,
               timeframe="1d", market="us_stock")
    assert a.warnings == []
    assert "252" in a.annualization_basis


def test_oos_selected_flag_warns():
    a = assess(slippage_bps=5.0, cost_taker_bps=7.5, bars=500, num_trades=40,
               timeframe="1d", market="crypto", oos_selected=True)
    assert any("OOS" in w for w in a.warnings)


def test_representative_cost_bps_per_market():
    s = Settings()
    assert representative_cost_bps(MarketKind.crypto, s) == s.cost_crypto_taker_bps
    assert representative_cost_bps(MarketKind.tw_stock, s) == s.cost_tw_fee_rate * s.cost_tw_fee_discount * 10_000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest app/tests/test_honesty.py -q`
Expected: FAIL — module `app.backtest.honesty` does not exist.

- [ ] **Step 3: Implement** — create `backend/app/backtest/honesty.py`:

```python
"""Backtest assumptions → explicit honesty warnings (pure, deterministic, fully unit-testable).

Surfaces the silent assumptions a return number hides: zero slippage, tiny sample, too few bars,
optimistically-selected OOS results, and which annualization calendar was used.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas import MarketKind

_MIN_TRADES = 30
_MIN_BARS = 100


class BacktestAssumptions(BaseModel):
    slippage_bps: float
    cost_taker_bps: float
    bars: int
    num_trades: int
    timeframe: str
    market: str
    annualization_basis: str
    oos_selected: bool = False
    warnings: list[str] = Field(default_factory=list)


def representative_cost_bps(market: MarketKind, settings) -> float:
    """One-side representative transaction cost in bps, for display."""
    if market == MarketKind.crypto:
        return settings.cost_crypto_taker_bps
    if market == MarketKind.tw_stock:
        return settings.cost_tw_fee_rate * settings.cost_tw_fee_discount * 10_000
    return settings.cost_us_fee_rate * 10_000


def assess(
    *,
    slippage_bps: float,
    cost_taker_bps: float,
    bars: int,
    num_trades: int,
    timeframe: str,
    market: str,
    oos_selected: bool = False,
) -> BacktestAssumptions:
    warnings: list[str] = []
    if slippage_bps <= 0:
        warnings.append("零滑價:成交品質被系統性高估")
    if num_trades < _MIN_TRADES:
        warnings.append(f"樣本過少({num_trades} 筆 < {_MIN_TRADES}):績效統計不顯著")
    if bars < _MIN_BARS:
        warnings.append(f"K 線過少({bars} < {_MIN_BARS}):結論脆弱")
    if oos_selected:
        warnings.append("此為被挑選後的 OOS 結果:屬樂觀上界,非未來表現保證")
    basis = (
        "365.25 日 × 24h (crypto, 24/7)"
        if market == MarketKind.crypto.value
        else "252 交易日 (stock trading calendar)"
    )
    return BacktestAssumptions(
        slippage_bps=slippage_bps,
        cost_taker_bps=cost_taker_bps,
        bars=bars,
        num_trades=num_trades,
        timeframe=timeframe,
        market=market,
        annualization_basis=basis,
        oos_selected=oos_selected,
        warnings=warnings,
    )
```

- [ ] **Step 4: Run the honesty test**

Run: `cd backend && pytest app/tests/test_honesty.py -q`
Expected: PASS.

- [ ] **Step 5: Attach `assumptions` to `BacktestResult`** — `backend/app/backtest/engine.py`:

Add the import near the top (after line 12 `from app.backtest import metrics`):
```python
from app.backtest.honesty import BacktestAssumptions, assess, representative_cost_bps
```
Add the field to `BacktestResult` (after line 58 `equity_curve: ...`):
```python
    assumptions: BacktestAssumptions | None = None
```
Populate it in the `return BacktestResult(...)` (insert before `trades=trades,` at line 197):
```python
        assumptions=assess(
            slippage_bps=costs.slippage_bps,
            cost_taker_bps=representative_cost_bps(market, settings),
            bars=len(candles),
            num_trades=len(trades),
            timeframe=timeframe,
            market=market.value,
        ),
```

- [ ] **Step 6: Run the engine + full suite**

Run: `cd backend && pytest app/tests/test_backtest.py -q && pytest -q`
Expected: PASS (the two `CostModel.zero()` tests now report `slippage_bps=0` in assumptions — they assert returns, not assumptions, so still green).

- [ ] **Step 7: Commit**

```bash
git add backend/app/backtest/honesty.py backend/app/backtest/engine.py backend/app/tests/test_honesty.py
git commit -m "feat(backtest): attach explicit honesty assumptions to every result"
```

---

### Task 5: Persist single-strategy backtests (`BacktestRun` table + endpoints)

Single backtests are transient — re-running clobbers the prior result. Persist each run (with its cost params + range) so results are auditable and reproducible, mirroring the workflow `WorkflowRun` pattern.

**Files:**
- Modify: `backend/app/models.py` (add `BacktestRun` after `WorkflowRun`, ~line 172)
- Modify: `backend/app/api/backtest.py:291-311` (add session + persist), add list/get endpoints
- Test: `backend/app/tests/test_backtest_runs.py` (new)

**Interfaces:**
- Consumes: `get_session` (FastAPI dep), `BacktestResult` (Task 4).
- Produces: `BacktestRun` table; `POST /api/backtest` persists and the response is unchanged (`BacktestResult`); `GET /api/backtest/runs?limit=` → `list[BacktestRun]`; `GET /api/backtest/runs/{id}` → `BacktestRun`.

- [ ] **Step 1: Write the failing test** — create `backend/app/tests/test_backtest_runs.py`:

```python
"""POST /api/backtest persists a BacktestRun retrievable via the runs endpoints."""
from __future__ import annotations

from datetime import datetime, timedelta

import app.api.backtest as bt
from app.api.backtest import BacktestRequest, backtest, list_backtest_runs
from app.db import get_session
from app.schemas import Candle


def _candles(n):
    t0 = datetime(2024, 1, 1)
    return [
        Candle(timestamp=t0 + timedelta(hours=i), open=100 + i, high=100 + i,
               low=100 + i, close=100 + i, volume=1.0)
        for i in range(n)
    ]


class _FakeBroker:
    def __init__(self, candles):
        self._candles = candles

    def get_ohlcv(self, symbol, timeframe, limit):
        return self._candles[:limit]

    def get_ohlcv_range(self, symbol, timeframe, start, end):
        return self._candles


def test_backtest_persists_and_lists(monkeypatch, session):
    monkeypatch.setattr(bt, "get_data_broker", lambda market: _FakeBroker(_candles(60)))
    result = backtest(BacktestRequest(symbol="BTC/USDT", limit=60, strategy="ma_cross"), session=session)
    assert result.assumptions is not None
    runs = list_backtest_runs(limit=10, session=session)
    assert len(runs) == 1
    assert runs[0].symbol == "BTC/USDT"
    assert runs[0].strategy == "ma_cross"
    assert runs[0].metrics_json["total_return_pct"] == result.total_return_pct
```

(The `session` fixture comes from `backend/app/tests/conftest.py`, which creates the tables on the app engine — confirm a `session` fixture exists; if it is named differently, use that name.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest app/tests/test_backtest_runs.py -q`
Expected: FAIL — `list_backtest_runs` / `BacktestRun` not defined; `backtest()` takes no `session`.

- [ ] **Step 3: Add the `BacktestRun` table** — in `backend/app/models.py`, after the `WorkflowRun` class (after line 171), add:

```python
class BacktestRun(SQLModel, table=True):
    """One single-strategy backtest, persisted for auditability + reproducibility.

    Captures the inputs that determine the numbers (strategy/params/range/cost slippage) alongside
    the metrics, the honesty assumptions, the equity curve and the trades.
    """

    id: int | None = Field(default=None, primary_key=True)
    symbol: str = Field(index=True)
    market: str = ""
    timeframe: str = ""
    strategy: str = Field(index=True)
    params_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    starting_cash: float = 0.0
    position_fraction: float = 1.0
    slippage_bps: float = 0.0
    bars: int = 0
    range_start: str = ""
    range_end: str = ""
    metrics_json: dict | None = Field(default=None, sa_column=Column(JSON))
    assumptions_json: dict | None = Field(default=None, sa_column=Column(JSON))
    equity_curve_json: list | None = Field(default=None, sa_column=Column(JSON))
    trades_json: list | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_now, index=True)
```

(`Column`, `JSON`, `_now`, `Field`, `SQLModel` are already imported at the top of `models.py` — they back `WorkflowRun`.)

- [ ] **Step 4: Persist on POST + add runs endpoints** — `backend/app/api/backtest.py`:

Update imports: add to the `from app.models import Workflow` line (line 17):
```python
from app.models import BacktestRun, Workflow
```
Replace the `backtest` endpoint (lines 291-311) with:
```python
@router.post("", response_model=BacktestResult)
def backtest(req: BacktestRequest, session: Session = Depends(get_session)) -> BacktestResult:
    try:
        strategy = build_strategy(req.strategy, req.params)
        candles = _fetch_candles(
            get_data_broker(req.market), req.symbol, req.timeframe, req.limit, req.start, req.end
        )
        result = run_backtest(
            candles,
            strategy,
            starting_cash=req.starting_cash,
            position_fraction=req.position_fraction,
            market=req.market,
            timeframe=req.timeframe,
        )
        session.add(
            BacktestRun(
                symbol=req.symbol,
                market=req.market.value,
                timeframe=req.timeframe,
                strategy=req.strategy,
                params_json=req.params,
                starting_cash=req.starting_cash,
                position_fraction=req.position_fraction,
                slippage_bps=result.assumptions.slippage_bps if result.assumptions else 0.0,
                bars=len(candles),
                range_start=candles[0].timestamp.isoformat(),
                range_end=candles[-1].timestamp.isoformat(),
                metrics_json=result.model_dump(mode="json", exclude={"trades", "equity_curve", "assumptions"}),
                assumptions_json=result.assumptions.model_dump(mode="json") if result.assumptions else None,
                equity_curve_json=[p.model_dump(mode="json") for p in result.equity_curve],
                trades_json=[t.model_dump(mode="json") for t in result.trades],
            )
        )
        session.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"{type(exc).__name__}: {exc}")


@router.get("/runs", response_model=list[BacktestRun])
def list_backtest_runs(limit: int = 50, session: Session = Depends(get_session)) -> list[BacktestRun]:
    from sqlmodel import select

    return list(session.exec(select(BacktestRun).order_by(BacktestRun.id.desc()).limit(limit)))


@router.get("/runs/{run_id}", response_model=BacktestRun)
def get_backtest_run(run_id: int, session: Session = Depends(get_session)) -> BacktestRun:
    run = session.get(BacktestRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="backtest run not found")
    return run
```

(`Session`, `Depends`, `get_session` are already imported at the top of `backtest.py` — lines 7-16.)

- [ ] **Step 5: Run the runs test + full suite**

Run: `cd backend && pytest app/tests/test_backtest_runs.py -q && pytest -q`
Expected: PASS. (New table auto-creates via `SQLModel.metadata.create_all` in `db.py:init_db` and the test conftest.)

- [ ] **Step 6: Commit**

```bash
git add backend/app/models.py backend/app/api/backtest.py backend/app/tests/test_backtest_runs.py
git commit -m "feat(backtest): persist single backtests as BacktestRun + runs endpoints"
```

---

### Task 6: Frontend — Honesty Bar + Run Registry + Sharpe in compare

Surface the assumptions and the run history; show Sharpe (not raw return) as the compare winner.

**Files:**
- Modify: `frontend/lib/api.ts` (types + client methods)
- Create: `frontend/components/backtest/HonestyBar.tsx`
- Create: `frontend/components/backtest/BacktestRunRegistry.tsx`
- Modify: `frontend/components/BacktestPanel.tsx` (mount both; compare table Sharpe column + 🏆 on best Sharpe)

**Interfaces:**
- Consumes: `BacktestResult.assumptions`, `CompareRow.sharpe`, `GET /api/backtest/runs`.
- Produces: `api.listBacktestRuns()`, `api.getBacktestRun(id)`; `<HonestyBar assumptions={...} />`; `<BacktestRunRegistry onSelect={...} />`.

- [ ] **Step 1: Extend the typed client** — `frontend/lib/api.ts`:

Add interfaces (after `BacktestResult`, near line 171):
```typescript
export interface BacktestAssumptions {
  slippage_bps: number;
  cost_taker_bps: number;
  bars: number;
  num_trades: number;
  timeframe: string;
  market: string;
  annualization_basis: string;
  oos_selected: boolean;
  warnings: string[];
}

export interface BacktestRunDTO {
  id: number;
  symbol: string;
  market: string;
  timeframe: string;
  strategy: string;
  starting_cash: number;
  slippage_bps: number;
  bars: number;
  range_start: string;
  range_end: string;
  metrics_json: Record<string, number> | null;
  assumptions_json: BacktestAssumptions | null;
  created_at: string;
}
```
Add `assumptions` to `BacktestResult` (after line 170 `equity_curve: EquityPoint[];`):
```typescript
  assumptions: BacktestAssumptions | null;
```
Add `sharpe` to `CompareRow` (after line 188 `total_return_pct: number;`):
```typescript
  sharpe: number;
```
Add client methods inside the `api` object (after `walkForward`, near line 432):
```typescript
  listBacktestRuns: (limit = 50) =>
    request<BacktestRunDTO[]>(`/api/backtest/runs?limit=${limit}`),
  getBacktestRun: (id: number) => request<BacktestRunDTO>(`/api/backtest/runs/${id}`),
```

- [ ] **Step 2: Create the Honesty Bar** — `frontend/components/backtest/HonestyBar.tsx`:

```tsx
import type { BacktestAssumptions } from "@/lib/api";

/** Surfaces the silent assumptions behind a backtest result. Warnings use --warning (never price tokens). */
export function HonestyBar({ assumptions }: { assumptions: BacktestAssumptions | null }) {
  if (!assumptions) return null;
  const a = assumptions;
  return (
    <div className="rounded-md border border-border bg-surface-2 px-3 py-2 text-[11px] text-muted">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
        <span>滑價 <span className="num text-text">{a.slippage_bps.toFixed(1)} bps</span></span>
        <span>成本 <span className="num text-text">{a.cost_taker_bps.toFixed(1)} bps</span></span>
        <span>K 線 <span className="num text-text">{a.bars}</span></span>
        <span>交易 <span className="num text-text">{a.num_trades}</span></span>
        <span>年化基準 <span className="text-text">{a.annualization_basis}</span></span>
      </div>
      {a.warnings.length > 0 && (
        <ul className="mt-1 space-y-0.5">
          {a.warnings.map((w) => (
            <li key={w} className="text-warning">⚠ {w}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Create the Run Registry** — `frontend/components/backtest/BacktestRunRegistry.tsx`:

```tsx
"use client";
import { useQuery } from "@tanstack/react-query";

import { api, type BacktestRunDTO } from "@/lib/api";

/** Past persisted backtests; click to inspect. Replaces transient single-result state. */
export function BacktestRunRegistry({ onSelect }: { onSelect?: (run: BacktestRunDTO) => void }) {
  const { data: runs = [] } = useQuery({
    queryKey: ["backtest-runs"],
    queryFn: () => api.listBacktestRuns(50),
    refetchInterval: 10_000,
  });
  if (runs.length === 0) {
    return <div className="text-[11px] text-faint">尚無回測紀錄 — 執行一次回測後會在此列出。</div>;
  }
  return (
    <div className="flex flex-col gap-1">
      {runs.map((r) => (
        <button
          key={r.id}
          onClick={() => onSelect?.(r)}
          className="flex items-center justify-between rounded-sm border border-border px-2 py-1 text-left text-[11px] hover:bg-surface-2"
        >
          <span className="text-text">{r.strategy} · {r.symbol}</span>
          <span className="num text-muted">
            {r.metrics_json ? `${r.metrics_json.total_return_pct?.toFixed(1)}% · Sharpe ${r.metrics_json.sharpe?.toFixed(2)}` : "—"}
          </span>
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Wire into `BacktestPanel.tsx`**

Add imports at the top of `frontend/components/BacktestPanel.tsx`:
```tsx
import { HonestyBar } from "@/components/backtest/HonestyBar";
import { BacktestRunRegistry } from "@/components/backtest/BacktestRunRegistry";
```
In the Overview tab, render `<HonestyBar assumptions={result.assumptions} />` immediately above the metrics grid (where the single-backtest `result` is shown). In the compare table, add a `Sharpe` column reading `row.sharpe.toFixed(2)` and move the 🏆 marker to the row with the highest `sharpe` (rows already arrive Sharpe-sorted from Task 3, so 🏆 belongs on `rows[0]` among non-error rows). Mount `<BacktestRunRegistry onSelect={...} />` in the panel's side column (the executor places it next to the controls; selecting a run can call `api.getBacktestRun(run.id)` to repopulate the view, or simply scroll/highlight — minimum: render the list).

- [ ] **Step 5: Build to verify**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no type errors (the new `assumptions`/`sharpe` fields are non-optional on the response types and present from the backend).

- [ ] **Step 6: Manual smoke (optional but recommended)**

Use the `run-app` skill (or `uvicorn app.main:app --reload` + `npm run dev`), open the backtest room, run a backtest, confirm the Honesty Bar shows `5.0 bps` slippage + a low-sample/short-range warning when applicable, and that a run appears in the registry.

- [ ] **Step 7: Commit**

```bash
git add frontend/lib/api.ts frontend/components/backtest/HonestyBar.tsx frontend/components/backtest/BacktestRunRegistry.tsx frontend/components/BacktestPanel.tsx
git commit -m "feat(backtest-ui): Honesty Bar + run registry + Sharpe-ranked compare"
```

---

### Task 7: Metered structured completion (`structured_completion_with_meta`)

Capture token usage + latency from the LLM call so AI runs are accountable, without breaking the existing `structured_completion`.

**Files:**
- Modify: `backend/app/ai/structured.py` (refactor client selection; add metered variant)
- Test: `backend/app/tests/test_structured_meta.py` (new)

**Interfaces:**
- Produces: `structured.CompletionMeta` (`model`, `prompt_tokens`, `completion_tokens`, `latency_ms`) and `structured.structured_completion_with_meta(*, system, content, output_model, model=None, max_tokens=2048, max_retries=None) -> tuple[T, CompletionMeta]`.

- [ ] **Step 1: Write the failing test** — create `backend/app/tests/test_structured_meta.py`:

```python
from __future__ import annotations

from types import SimpleNamespace

from pydantic import BaseModel

import app.ai.structured as structured


class _Out(BaseModel):
    value: int


def test_with_meta_returns_tokens_and_latency(monkeypatch):
    out = _Out(value=7)
    completion = SimpleNamespace(usage=SimpleNamespace(input_tokens=11, output_tokens=5))

    class _FakeMessages:
        def create_with_completion(self, **kwargs):
            return out, completion

    monkeypatch.setattr(structured, "_client_and_mode",
                        lambda provider: (SimpleNamespace(messages=_FakeMessages()), "messages"))
    obj, meta = structured.structured_completion_with_meta(
        system="s", content="c", output_model=_Out, model="claude-test"
    )
    assert obj.value == 7
    assert meta.prompt_tokens == 11
    assert meta.completion_tokens == 5
    assert meta.model == "claude-test"
    assert meta.latency_ms >= 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest app/tests/test_structured_meta.py -q`
Expected: FAIL — `_client_and_mode` / `structured_completion_with_meta` / `CompletionMeta` not defined.

- [ ] **Step 3: Implement** — in `backend/app/ai/structured.py`:

Add imports at the top (after line 16 `from typing import TypeVar`):
```python
import time
```
Add after the three `_get_*_client` helpers (after line 87), a unifier + the metered variant + `CompletionMeta`:
```python
def _client_and_mode(provider: str):
    """Return (instructor client, "messages"|"chat") for the configured provider."""
    if provider == "anthropic":
        return _get_anthropic_client(), "messages"
    if provider == "lmstudio":
        return _get_lmstudio_client(), "chat"
    if provider == "openrouter":
        return _get_openrouter_client(), "chat"
    raise RuntimeError(f"Unknown ai_provider: {provider!r}")


class CompletionMeta(BaseModel):
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0


def _usage_tokens(usage) -> tuple[int, int]:
    """Anthropic uses input/output_tokens; OpenAI uses prompt/completion_tokens."""
    if usage is None:
        return 0, 0
    prompt = getattr(usage, "input_tokens", None) or getattr(usage, "prompt_tokens", 0) or 0
    completion = getattr(usage, "output_tokens", None) or getattr(usage, "completion_tokens", 0) or 0
    return int(prompt), int(completion)


def structured_completion_with_meta(
    *,
    system: str,
    content: str,
    output_model: type[T],
    model: str | None = None,
    max_tokens: int = 2048,
    max_retries: int | None = None,
) -> tuple[T, CompletionMeta]:
    model = model or settings.ai_model
    max_retries = settings.ai_max_retries if max_retries is None else max_retries
    client, mode = _client_and_mode(settings.ai_provider)
    start = time.perf_counter()
    if mode == "messages":
        obj, completion = client.messages.create_with_completion(
            model=model, max_tokens=max_tokens, max_retries=max_retries,
            system=system, messages=[{"role": "user", "content": content}],
            response_model=output_model,
        )
    else:
        obj, completion = client.chat.completions.create_with_completion(
            model=model, max_tokens=max_tokens, max_retries=max_retries,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": content}],
            response_model=output_model,
        )
    latency_ms = (time.perf_counter() - start) * 1000.0
    prompt_tokens, completion_tokens = _usage_tokens(getattr(completion, "usage", None))
    return obj, CompletionMeta(
        model=model, prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens, latency_ms=latency_ms,
    )
```

- [ ] **Step 4: Run the meta test + existing AI test**

Run: `cd backend && pytest app/tests/test_structured_meta.py app/tests/test_ai_signal.py -q`
Expected: PASS (existing `structured_completion` untouched; `test_ai_signal` still monkeypatches `signal_agent.structured_completion`).

- [ ] **Step 5: Commit**

```bash
git add backend/app/ai/structured.py backend/app/tests/test_structured_meta.py
git commit -m "feat(ai): metered structured completion (tokens + latency)"
```

---

### Task 8: Deterministic AI signals via a DB-backed cache

The same market summary must yield the same AI signal across runs (so AI backtests are reproducible and cheap), and each genuine call is metered. Cache `AISignalResponse` keyed by `sha256(model + system + summary)`.

**Files:**
- Modify: `backend/app/models.py` (add `AiSignalCache` table)
- Create: `backend/app/ai/signal_cache.py`
- Modify: `backend/app/ai/signal_agent.py:47-74` (cache-through + metering)
- Modify: `backend/app/tests/test_ai_signal.py` (monkeypatch the metered fn; assert determinism)

**Interfaces:**
- Consumes: `structured_completion_with_meta` (Task 7).
- Produces: `signal_cache.cache_key(model, system, summary) -> str`; `signal_cache.lookup(key) -> dict | None`; `signal_cache.store(key, model, response: BaseModel, meta) -> None`. `generate_ai_signal` signature is unchanged.

- [ ] **Step 1: Write the failing test** — replace the body of `backend/app/tests/test_ai_signal.py`'s first test and add a determinism test. Concretely, add this test and update the monkeypatch target (the existing tests monkeypatch `signal_agent.structured_completion`; switch to the metered fn):

```python
def test_ai_signal_is_cached_and_deterministic(monkeypatch):
    from app.ai import signal_agent
    from app.ai.signal_agent import AISignalResponse, generate_ai_signal
    from app.ai.structured import CompletionMeta

    calls = {"n": 0}

    def fake(**kwargs):
        calls["n"] += 1
        return AISignalResponse(action="buy", confidence=0.6, rationale="x"), CompletionMeta(model="m")

    monkeypatch.setattr(signal_agent, "structured_completion_with_meta", fake)
    candles = make_candles([float(i) for i in range(1, 40)])
    first = generate_ai_signal("BTC/USDT", candles)
    second = generate_ai_signal("BTC/USDT", candles)
    assert calls["n"] == 1  # second call served from cache
    assert first.action == second.action == "buy"
    assert first.confidence == second.confidence
```

Also update the existing `test_ai_signal.py` tests that monkeypatch `signal_agent.structured_completion`: change the target to `signal_agent.structured_completion_with_meta` and have the fake return `(AISignalResponse(...), CompletionMeta(model="m"))` instead of a bare response. (The `session`/DB fixture from conftest must be active so the cache table exists; if those tests don't already pull the DB fixture, add the `session` fixture param.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest app/tests/test_ai_signal.py -q`
Expected: FAIL — `structured_completion_with_meta` not referenced by `signal_agent`; no cache.

- [ ] **Step 3: Add the cache table** — in `backend/app/models.py`, after `BacktestRun` (from Task 5), add:

```python
class AiSignalCache(SQLModel, table=True):
    """Deterministic cache of AI signal responses keyed by (model, system, summary) hash.

    Makes AI backtests reproducible run-to-run and avoids re-paying for identical bar summaries.
    """

    cache_key: str = Field(primary_key=True)
    model: str = ""
    response_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    created_at: datetime = Field(default_factory=_now, index=True)
```

- [ ] **Step 4: Implement the cache module** — create `backend/app/ai/signal_cache.py`:

```python
"""DB-backed cache for AI signal responses (deterministic, metered)."""
from __future__ import annotations

import hashlib

from pydantic import BaseModel
from sqlmodel import Session

from app.db import engine
from app.models import AiSignalCache


def cache_key(model: str, system: str, summary: str) -> str:
    raw = f"{model}\x00{system}\x00{summary}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def lookup(key: str) -> dict | None:
    with Session(engine) as session:
        row = session.get(AiSignalCache, key)
        return dict(row.response_json) if row is not None else None


def store(key: str, model: str, response: BaseModel, meta) -> None:
    with Session(engine) as session:
        if session.get(AiSignalCache, key) is not None:
            return
        session.add(
            AiSignalCache(
                cache_key=key,
                model=model,
                response_json=response.model_dump(mode="json"),
                prompt_tokens=getattr(meta, "prompt_tokens", 0),
                completion_tokens=getattr(meta, "completion_tokens", 0),
                latency_ms=getattr(meta, "latency_ms", 0.0),
            )
        )
        session.commit()
```

- [ ] **Step 5: Cache-through in `signal_agent`** — `backend/app/ai/signal_agent.py`:

Change the import (line 12) from:
```python
from app.ai.structured import structured_completion
```
to:
```python
from app.ai import signal_cache
from app.ai.structured import structured_completion_with_meta
```
Replace the body of `generate_ai_signal` (lines 56-74) after `summary` is built:
```python
    model = model or settings.ai_model
    summary = _market_summary(symbol, candles)
    if extra_context:
        summary += f"\nAdditional context: {extra_context}"

    key = signal_cache.cache_key(model, _SYSTEM_PROMPT, summary)
    cached = signal_cache.lookup(key)
    if cached is not None:
        out = AISignalResponse.model_validate(cached)
    else:
        out, meta = structured_completion_with_meta(
            system=_SYSTEM_PROMPT,
            content=summary,
            output_model=AISignalResponse,
            model=model,
            max_tokens=1024,
        )
        signal_cache.store(key, model, out, meta)

    return Signal(
        action=out.action,
        confidence=max(0.0, min(1.0, out.confidence)),
        reason=out.rationale,
        source=f"ai:{model}",
    )
```

- [ ] **Step 6: Run the AI tests + full suite**

Run: `cd backend && pytest app/tests/test_ai_signal.py -q && pytest -q`
Expected: PASS — second `generate_ai_signal` with identical candles serves from cache (underlying fake called once); full suite green.

- [ ] **Step 7: Commit**

```bash
git add backend/app/models.py backend/app/ai/signal_cache.py backend/app/ai/signal_agent.py backend/app/tests/test_ai_signal.py
git commit -m "feat(ai): deterministic DB-backed AI signal cache + metering"
```

---

## Self-Review

**1. Spec coverage** (against roadmap Now-1/2/3 + quick wins):
- Now-1 "回測引擎 statistical honesty 硬化": 252 annualization → Task 1; non-zero slippage → Task 2; Sharpe-ranked compare + Buy&Hold → Task 3 (Buy&Hold already present on `CompareRow`); multiple-testing/OOS disclosure → Task 4 `oos_selected` warning + Honesty Bar (Task 6). ✔
- Now-2 "持久化 BacktestRun + Honesty Bar": Task 4 (assumptions) + Task 5 (persistence + endpoints) + Task 6 (Honesty Bar + registry). ✔
- Now-3 "AI 訊號回測決定性 response cache + token/latency 計量": Task 7 (metering) + Task 8 (deterministic cache). ✔
- Quick wins covered: 252 annualization (T1), Sharpe-rank + remove misleading 🏆 (T3/T6), non-zero slippage default (T2). ✔
- Deferred (correctly out of this cluster): the OOS optimize/walk-forward "selected upper bound" is *disclosed* (T4 flag) but the optimize endpoint isn't yet wired to set `oos_selected` on its rows — that belongs with the Next-phase backtest-visual task; noted, not silently dropped.

**2. Placeholder scan:** No "TBD"/"handle edge cases"/"similar to Task N" — every code step has literal code. Frontend Task 6 Step 4 describes mount points rather than reproducing all 850 lines of `BacktestPanel.tsx`; the two new components are fully specified, and the integration is a bounded insertion.

**3. Type consistency:** `periods_per_year(timeframe, market)` signature is consistent across T1 call sites. `CompletionMeta` (T7) is consumed by `signal_cache.store`/`generate_ai_signal` (T8) with matching attrs (`prompt_tokens`/`completion_tokens`/`latency_ms`). `BacktestAssumptions` (T4) fields match `HonestyBar` props and `BacktestRunDTO.assumptions_json` (T6). `CompareRow.sharpe` (T3 backend) matches `CompareRow.sharpe` (T6 frontend).

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-06-27-backtest-honesty-cluster.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Backend tasks (1–5, 7–8) are TDD with a green-bar gate; the frontend task (6) is build-verified.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints for review.

**Which approach?**
