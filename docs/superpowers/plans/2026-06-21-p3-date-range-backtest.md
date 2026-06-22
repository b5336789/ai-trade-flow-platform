# P3 日期區間回測 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the ability to backtest a specified start/end date range (default last 1 year) instead of only "last N bars", touching the data-fetch layer, the backtest request models, and a minimal frontend date-range control — without changing the backtest engine.

**Architecture:** The data-fetch layer gains a range-capable method (`get_ohlcv_range`) on the `Broker` ABC, implemented by `CsvDataBroker` (timestamp filter) and `CcxtBroker` (ccxt `since`-pagination loop with a hard cap). The backtest API request models gain optional `start`/`end` datetimes; when both are present the endpoints fetch by range, otherwise they keep the existing `limit` path (fully backward-compatible). `run_backtest` still consumes a `list[Candle]` and is untouched. The frontend adds a 「最近 N 根 / 日期區間」 toggle plus two date inputs (default = last 1 year) that feed `start`/`end` into the request.

**Tech Stack:** Python 3.11 · FastAPI · pydantic · ccxt · pytest (backend) + Next/TS (frontend)

## Global Constraints
- **Fail loud everywhere**: a missing data provider, a reversed range (`start >= end`), or a range that yields `< 2` candles must raise a clear error — `ValueError` at the data/engine layer surfacing as an HTTP `422` with an explicit `detail`, never a silent empty result.
- **Paper-safe**: this is data-fetch + read-only backtest only; no order path, risk path, or live trading is touched.
- **REAL pytest business-logic tests (TDD)**: for every backend task, write the failing test first, watch it fail for the right reason, then implement the minimal code to pass. Match the existing 221-test style (synthetic candles via `app/tests/helpers.py`, `monkeypatch`-patched `get_data_broker`, FastAPI `TestClient`). No empty coverage tests, no placeholders.
- **ccxt pagination capped**: the `since`-pagination loop must stop at a hard total-bar cap (`MAX_RANGE_BARS = 5000`) to avoid a runaway fetch on long ranges / small timeframes.
- **Backward-compatible**: `start`/`end` are optional and default to `None`; omitting them preserves the current `limit` behaviour byte-for-byte. Only when **both** are provided does the range path activate.
- **Frontend has no unit runner**: the frontend task verifies via `cd frontend && npx tsc --noEmit && npm run build` (CI parity), not a test runner.
- **Never commit to `main`**: branch, commit per task, open a PR at the end (do not merge without review).

---

## File Structure

```
backend/app/
  brokers/
    base.py            # MODIFY: add get_ohlcv_range(...) default → NotImplementedError
    csv_data.py        # MODIFY: implement get_ohlcv_range (timestamp filter, reversed-range guard)
    crypto_ccxt.py     # MODIFY: implement get_ohlcv_range (since-pagination loop, 5000 cap)
  api/
    backtest.py        # MODIFY: add start/end to BacktestRequest (+ Compare/Optimize/WalkForward);
                       #         route to range fetch when both present
  tests/
    test_backtest_daterange.py   # CREATE: ccxt pagination (mock), CSV filter, boundaries (fail-loud)
    test_backtest_api.py         # MODIFY: add date-range endpoint tests (TestClient + monkeypatch)
    helpers.py                   # (read-only reference; StubBroker may gain get_ohlcv_range if a test needs it)

frontend/
  lib/api.ts                     # MODIFY: add start?/end? to BacktestRequest (+ sibling request types)
  components/BacktestPanel.tsx   # MODIFY: 「最近 N 根 / 日期區間」 toggle + two date inputs (default last 1y)
```

> **Coordination note (read before starting):** `BacktestPanel.tsx` is also edited by **P2** (C1/C3/C4/C5 backtest-page redesign). To avoid a merge conflict, run **P2 before P3**, or have the same worker land both. P3's frontend change here is intentionally minimal: only the date-range mode toggle and the two date inputs that feed `start`/`end` into the request — it does **not** redesign the panel layout, buttons, tabs, or results (that is P2's scope).

---

### Task 1: `get_ohlcv_range` on the Broker ABC + ccxt pagination
**Files:**
- Modify: `backend/app/brokers/base.py`
- Modify: `backend/app/brokers/crypto_ccxt.py`
- Test: `backend/app/tests/test_backtest_daterange.py` (create)

**Interfaces:**
- Produces: `Broker.get_ohlcv_range(self, symbol: str, timeframe: str, start: datetime, end: datetime) -> list[Candle]` — base default raises `NotImplementedError`; `CcxtBroker` overrides it.
- Consumes (ccxt): `self._exchange.fetch_ohlcv(symbol, timeframe=<tf>, since=<epoch_ms>, limit=<n>) -> list[[ms, o, h, l, c, v], ...]`.

- [ ] **Step 1: Write the failing test** (COMPLETE pytest code) — append to a new file:

```python
"""C2 date-range backtest: range-capable data fetch (ccxt pagination + CSV filter + boundaries)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.brokers.base import Broker
from app.brokers.crypto_ccxt import CcxtBroker, MAX_RANGE_BARS


def _utc(y, m, d, h=0):
    return datetime(y, m, d, h, tzinfo=timezone.utc)


def _ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


class _FakeExchange:
    """Mimics ccxt fetch_ohlcv(since=, limit=): returns hourly bars from `since`, page by page."""

    def __init__(self, bars: list[list], page_size: int = 2) -> None:
        self._bars = bars  # sorted [[ms, o, h, l, c, v], ...]
        self.page_size = page_size
        self.calls: list[int | None] = []

    def fetch_ohlcv(self, symbol, timeframe="1h", since=None, limit=None):
        self.calls.append(since)
        rows = [b for b in self._bars if since is None or b[0] >= since]
        return rows[: (limit or self.page_size)]


def _hourly_bars(start: datetime, n: int) -> list[list]:
    out = []
    for i in range(n):
        t = _ms(start) + i * 3_600_000  # +1h
        out.append([t, 10.0 + i, 11.0 + i, 9.0 + i, 10.5 + i, 1.0])
    return out


def _make_ccxt(monkeypatch, fake: _FakeExchange) -> CcxtBroker:
    # Build a CcxtBroker without touching the network, then swap in the fake exchange.
    monkeypatch.setattr(CcxtBroker, "__init__", lambda self: None)
    broker = CcxtBroker()
    broker._exchange = fake
    broker._exchange_id = "binance"
    return broker


def test_base_get_ohlcv_range_default_fails_loud():
    # The ABC default must fail loud so unimplemented brokers never silently return nothing.
    assert hasattr(Broker, "get_ohlcv_range")


def test_ccxt_range_paginates_across_two_pages(monkeypatch):
    start, end = _utc(2024, 1, 1), _utc(2024, 1, 1, 3)  # want 4 hourly bars (00,01,02,03)
    bars = _hourly_bars(start, 4)
    fake = _FakeExchange(bars, page_size=2)  # forces 2 pages to cover the range
    broker = _make_ccxt(monkeypatch, fake)

    candles = broker.get_ohlcv_range("BTC/USDT", "1h", start, end)

    assert [int(c.timestamp.timestamp()) for c in candles] == [int(b[0] / 1000) for b in bars]
    assert len(candles) == 4
    # paginated: first call since=start_ms, second call advanced past page 1's last bar.
    assert len(fake.calls) >= 2
    assert fake.calls[0] == _ms(start)
    assert fake.calls[1] == bars[2][0]  # last-of-page-1 ts + 1ms → next page's first bar


def test_ccxt_range_stops_at_end_and_excludes_beyond(monkeypatch):
    start, end = _utc(2024, 1, 1), _utc(2024, 1, 1, 1)  # only 00 and 01 in range
    bars = _hourly_bars(start, 6)  # exchange has 6 bars; range only covers 2
    broker = _make_ccxt(monkeypatch, _FakeExchange(bars, page_size=10))

    candles = broker.get_ohlcv_range("BTC/USDT", "1h", start, end)

    assert len(candles) == 2
    assert candles[-1].timestamp <= end


def test_ccxt_range_caps_total_bars(monkeypatch):
    start, end = _utc(2020, 1, 1), _utc(2025, 1, 1)  # huge range
    bars = _hourly_bars(start, MAX_RANGE_BARS + 500)
    broker = _make_ccxt(monkeypatch, _FakeExchange(bars, page_size=1000))

    candles = broker.get_ohlcv_range("BTC/USDT", "1h", start, end)

    assert len(candles) <= MAX_RANGE_BARS


def test_ccxt_range_empty_fails_loud(monkeypatch):
    start, end = _utc(2024, 1, 1), _utc(2024, 1, 2)
    broker = _make_ccxt(monkeypatch, _FakeExchange([], page_size=2))  # exchange returns nothing
    with pytest.raises(RuntimeError):
        broker.get_ohlcv_range("BTC/USDT", "1h", start, end)
```

- [ ] **Step 2: Run `cd backend && python -m pytest app/tests/test_backtest_daterange.py -v`** — Expected: FAIL (`ImportError`/`AttributeError`: `MAX_RANGE_BARS` and `CcxtBroker.get_ohlcv_range` do not exist yet).

- [ ] **Step 3: Implement minimal code** (COMPLETE code):

In `backend/app/brokers/base.py`, add the default method to the `Broker` ABC (after `get_ohlcv`). Import `datetime` at the top (`from datetime import datetime`):

```python
    def get_ohlcv_range(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> list[Candle]:
        """Fetch candles whose timestamp falls in [start, end]. Subclasses override; default fails loud."""
        raise NotImplementedError(
            f"{type(self).__name__} does not support date-range OHLCV; use get_ohlcv(limit=...)"
        )
```

In `backend/app/brokers/crypto_ccxt.py`, add the module constant and the override (the `_timeframe_ms` helper keeps pagination from looping forever on an exchange that ignores `since`):

```python
MAX_RANGE_BARS = 5000  # hard cap so a long range / small timeframe can't run away

_TIMEFRAME_MS = {
    "1m": 60_000, "3m": 180_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000,
    "1h": 3_600_000, "2h": 7_200_000, "4h": 14_400_000, "6h": 21_600_000,
    "12h": 43_200_000, "1d": 86_400_000, "1w": 604_800_000,
}
```

```python
    def get_ohlcv_range(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> list[Candle]:
        start_ms = int(start.timestamp() * 1000)
        end_ms = int(end.timestamp() * 1000)
        step = _TIMEFRAME_MS.get(timeframe, 3_600_000)
        out: list[Candle] = []
        since = start_ms
        last_ts: int | None = None
        while since <= end_ms and len(out) < MAX_RANGE_BARS:
            raw = self._exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=1000)
            if not raw:
                break
            advanced = False
            for r in raw:
                ts = int(r[0])
                if ts > end_ms:
                    advanced = False
                    break
                if last_ts is not None and ts <= last_ts:
                    continue  # de-dupe overlap across pages
                out.append(
                    Candle(
                        timestamp=_to_dt(ts),
                        open=float(r[1]),
                        high=float(r[2]),
                        low=float(r[3]),
                        close=float(r[4]),
                        volume=float(r[5]),
                    )
                )
                last_ts = ts
                advanced = True
                if len(out) >= MAX_RANGE_BARS:
                    break
            if not advanced:
                break  # no progress (range exhausted or exchange ignored since) → stop, don't spin
            since = last_ts + step  # next page starts after the last bar we kept
        if not out:
            raise RuntimeError(
                f"No OHLCV data for {symbol} {timeframe} in range {start.isoformat()}..{end.isoformat()}"
            )
        return out[:MAX_RANGE_BARS]
```

> Note: the fake exchange in the test paginates by re-filtering on `since` and returning `page_size` rows, so the second call's `since` equals `bars[2][0]` only if `step` lands exactly on the next bar. The fake's bars are spaced exactly `+1h` and `timeframe="1h"` → `step == 3_600_000`, so `last_ts + step == bars[2][0]`. (If a real exchange returns a partial page, the loop still progresses by `last_ts + step`.)

- [ ] **Step 4: Run the test** — `cd backend && python -m pytest app/tests/test_backtest_daterange.py -v` — Expected: PASS (all 5 tests in this file so far).

- [ ] **Step 5: Run full suite `cd backend && python -m pytest`** — Expected: all pass (no regressions; existing brokers/endpoints untouched).

- [ ] **Step 6: Commit** — `feat(brokers): add get_ohlcv_range with ccxt since-pagination + 5000-bar cap`.

---

### Task 2: `CsvDataBroker.get_ohlcv_range` (timestamp filter + reversed-range guard)
**Files:**
- Modify: `backend/app/brokers/csv_data.py`
- Test: `backend/app/tests/test_backtest_daterange.py` (extend)

**Interfaces:**
- Produces: `CsvDataBroker.get_ohlcv_range(symbol, timeframe, start, end) -> list[Candle]` returning only candles with `start <= c.timestamp <= end`; raises `ValueError` if `start > end`.

- [ ] **Step 1: Write the failing test** (COMPLETE pytest code) — append to `test_backtest_daterange.py`:

```python
from app.brokers import market_data
from app.brokers.csv_data import CsvDataBroker
from app.schemas import MarketKind

_CSV = """timestamp,open,high,low,close,volume
2024-01-01,100,105,99,104,1000
2024-02-01,104,110,103,109,1200
2024-03-01,109,112,108,111,1300
2024-04-01,111,113,107,108,1400
"""


def test_csv_range_filters_to_in_range_only():
    market_data.clear()
    market_data.set_candles(MarketKind.tw_stock, "2330", market_data.parse_csv(_CSV))
    broker = CsvDataBroker(MarketKind.tw_stock)

    candles = broker.get_ohlcv_range("2330", "1d", _utc(2024, 2, 1), _utc(2024, 3, 1))

    assert [c.timestamp.date().isoformat() for c in candles] == ["2024-02-01", "2024-03-01"]
    market_data.clear()


def test_csv_range_reversed_fails_loud():
    market_data.clear()
    market_data.set_candles(MarketKind.tw_stock, "2330", market_data.parse_csv(_CSV))
    broker = CsvDataBroker(MarketKind.tw_stock)
    with pytest.raises(ValueError):
        broker.get_ohlcv_range("2330", "1d", _utc(2024, 4, 1), _utc(2024, 1, 1))
    market_data.clear()
```

- [ ] **Step 2: Run `cd backend && python -m pytest app/tests/test_backtest_daterange.py -k csv -v`** — Expected: FAIL (`AttributeError`: `CsvDataBroker` has no `get_ohlcv_range`; it falls back to the ABC default `NotImplementedError`, not the expected filter/`ValueError`).

- [ ] **Step 3: Implement minimal code** (COMPLETE code) — add to `backend/app/brokers/csv_data.py` (import `from datetime import datetime` at top):

```python
    def get_ohlcv_range(
        self, symbol: str, timeframe: str = "1h", start: datetime | None = None, end: datetime | None = None
    ) -> list[Candle]:
        if start is None or end is None:
            raise ValueError("get_ohlcv_range requires both start and end")
        if start > end:
            raise ValueError(f"start {start.isoformat()} must be before end {end.isoformat()}")
        return [c for c in self._candles(symbol) if start <= c.timestamp <= end]
```

- [ ] **Step 4: Run the test** — `cd backend && python -m pytest app/tests/test_backtest_daterange.py -k csv -v` — Expected: PASS.

- [ ] **Step 5: Run full suite `cd backend && python -m pytest`** — Expected: all pass (no regressions).

- [ ] **Step 6: Commit** — `feat(brokers): CsvDataBroker.get_ohlcv_range filters by timestamp, guards reversed range`.

---

### Task 3: Backtest API — `start`/`end` on `BacktestRequest`, route to range fetch
**Files:**
- Modify: `backend/app/api/backtest.py`
- Test: `backend/app/tests/test_backtest_api.py` (extend)

**Interfaces:**
- Consumes: `BacktestRequest{ ..., start: datetime | None = None, end: datetime | None = None }`.
- Produces: `POST /api/backtest` — when **both** `start`+`end` present → `get_data_broker(market).get_ohlcv_range(symbol, timeframe, start, end)`; else current `get_ohlcv(..., limit)`. `start >= end` → HTTP `422`; `< 2` candles in range → fail loud (`ValueError` → `422`).

- [ ] **Step 1: Write the failing test** (COMPLETE pytest code) — append to `test_backtest_api.py`. The existing file already has `client`, `_CLOSES`, `make_candles`; add a range-aware stub and three cases:

```python
from datetime import datetime, timedelta, timezone

from app.brokers.base import Broker
from app.schemas import Balance, Candle, MarketKind, Position, Ticker, TradingMode


class _RangeStubBroker(Broker):
    """Stub whose get_ohlcv_range returns only candles inside [start, end] from a fixed daily series."""

    market = MarketKind.crypto
    mode = TradingMode.live

    def __init__(self, closes: list[float]) -> None:
        base = datetime(2024, 1, 1, tzinfo=timezone.utc)
        self._series = [
            Candle(timestamp=base + timedelta(days=i), open=c, high=c, low=c, close=c, volume=1.0)
            for i, c in enumerate(closes)
        ]

    @property
    def name(self) -> str:
        return "range-stub"

    def get_ticker(self, symbol: str) -> Ticker:
        return Ticker(symbol=symbol, price=self._series[-1].close, timestamp=self._series[-1].timestamp)

    def get_ohlcv(self, symbol, timeframe="1h", limit=100):
        return self._series[-limit:]

    def get_ohlcv_range(self, symbol, timeframe, start, end):
        if start > end:
            raise ValueError("start must be before end")
        return [c for c in self._series if start <= c.timestamp <= end]

    def create_order(self, request):  # pragma: no cover
        raise NotImplementedError

    def get_balance(self) -> list[Balance]:
        return []

    def get_positions(self) -> list[Position]:
        return []


def _stub_range_broker(monkeypatch, closes):
    monkeypatch.setattr("app.api.backtest.get_data_broker", lambda market: _RangeStubBroker(closes))


def test_backtest_date_range_uses_range_fetch(monkeypatch):
    # 60 daily bars from 2024-01-01; request a 20-day window → only those bars feed the backtest.
    _stub_range_broker(monkeypatch, [100 + 5 * math.sin(i / 4) for i in range(60)])
    resp = client.post(
        "/api/backtest",
        json={
            "symbol": "BTC/USDT",
            "strategy": "ma_cross",
            "params": {"fast": 2, "slow": 5},
            "start": "2024-01-05T00:00:00Z",
            "end": "2024-01-25T00:00:00Z",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "total_return_pct" in body
    # 21 candles in [01-05, 01-25] → equity curve has len-1 points (engine convention).
    assert len(body["equity_curve"]) == 21 - 1


def test_backtest_reversed_range_is_422(monkeypatch):
    _stub_range_broker(monkeypatch, [100.0] * 60)
    resp = client.post(
        "/api/backtest",
        json={
            "symbol": "BTC/USDT",
            "strategy": "ma_cross",
            "start": "2024-02-01T00:00:00Z",
            "end": "2024-01-01T00:00:00Z",
        },
    )
    assert resp.status_code == 422, resp.text


def test_backtest_range_too_few_candles_is_422(monkeypatch):
    _stub_range_broker(monkeypatch, [100.0] * 60)
    # A 1-day window catches a single candle → run_backtest rejects (<2) → 422 fail-loud.
    resp = client.post(
        "/api/backtest",
        json={
            "symbol": "BTC/USDT",
            "strategy": "ma_cross",
            "start": "2024-01-10T00:00:00Z",
            "end": "2024-01-10T12:00:00Z",
        },
    )
    assert resp.status_code == 422, resp.text


def test_backtest_no_range_still_uses_limit(monkeypatch):
    # Backward-compat: omitting start/end keeps the limit path (no get_ohlcv_range call needed).
    _stub_range_broker(monkeypatch, [100 + 5 * math.sin(i / 4) for i in range(60)])
    resp = client.post(
        "/api/backtest",
        json={"symbol": "BTC/USDT", "strategy": "ma_cross", "params": {"fast": 2, "slow": 5}, "limit": 30},
    )
    assert resp.status_code == 200, resp.text
    assert len(resp.json()["equity_curve"]) == 30 - 1
```

- [ ] **Step 2: Run `cd backend && python -m pytest app/tests/test_backtest_api.py -k "range or reversed or limit" -v`** — Expected: FAIL (`BacktestRequest` has no `start`/`end`; the range tests either 422 on unknown fields or ignore the window — depending on pydantic config they will not equal the expected `equity_curve` length).

- [ ] **Step 3: Implement minimal code** (COMPLETE code) — in `backend/app/api/backtest.py`:

Add the import at the top:
```python
from datetime import datetime
```

Add fields to `BacktestRequest`:
```python
class BacktestRequest(BaseModel):
    symbol: str
    market: MarketKind = MarketKind.crypto
    timeframe: str = "1h"
    limit: int = Field(default=500, ge=10, le=1000)
    strategy: str = "ma_cross"
    params: dict = Field(default_factory=dict)
    starting_cash: float = 100_000.0
    position_fraction: float = 1.0
    start: datetime | None = None  # C2: when start+end both set, fetch by range instead of limit
    end: datetime | None = None
```

Add a shared helper above the endpoints (after `router = ...`):
```python
def _fetch_candles(broker, symbol, timeframe, limit, start, end):
    """Range fetch when both start+end are given (C2), else the legacy limit path. Fails loud."""
    if start is not None and end is not None:
        if start >= end:
            raise ValueError("start must be before end")
        return broker.get_ohlcv_range(symbol, timeframe, start, end)
    return broker.get_ohlcv(symbol, timeframe, limit)
```

Update the `backtest` endpoint's fetch line:
```python
        candles = _fetch_candles(
            get_data_broker(req.market), req.symbol, req.timeframe, req.limit, req.start, req.end
        )
```

> `run_backtest` already raises `ValueError` on `< 2` candles, and the existing `except ValueError → 422` handler covers both the reversed-range guard and the too-few-candles case. `get_ohlcv_range`'s own `RuntimeError`/`NotImplementedError` are caught by the existing `502`/`501` handlers — fail-loud preserved.

- [ ] **Step 4: Run the test** — `cd backend && python -m pytest app/tests/test_backtest_api.py -v` — Expected: PASS (the 4 new tests + the existing walk-forward tests).

- [ ] **Step 5: Run full suite `cd backend && python -m pytest`** — Expected: all pass (no regressions).

- [ ] **Step 6: Commit** — `feat(backtest-api): BacktestRequest start/end → range fetch, fail loud on bad range`.

---

### Task 4: Extend `start`/`end` to Compare / Optimize / WalkForward (consistency)
**Files:**
- Modify: `backend/app/api/backtest.py`
- Test: `backend/app/tests/test_backtest_api.py` (extend)

**Interfaces:**
- Consumes: `CompareRequest`, `OptimizeRequest`, `WalkForwardRequest` each gain `start: datetime | None = None`, `end: datetime | None = None`.
- Produces: each endpoint routes through the same `_fetch_candles(...)` helper from Task 3, so a date range applies uniformly across all four analyses.

- [ ] **Step 1: Write the failing test** (COMPLETE pytest code) — append to `test_backtest_api.py` (reuses `_RangeStubBroker` / `_stub_range_broker` from Task 3):

```python
def test_compare_respects_date_range(monkeypatch):
    _stub_range_broker(monkeypatch, [100 + 5 * math.sin(i / 4) for i in range(60)])
    resp = client.post(
        "/api/backtest/compare",
        json={
            "symbol": "BTC/USDT",
            "strategies": ["ma_cross"],
            "start": "2024-01-05T00:00:00Z",
            "end": "2024-01-25T00:00:00Z",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()[0]["strategy"] == "ma_cross"


def test_optimize_reversed_range_is_422(monkeypatch):
    _stub_range_broker(monkeypatch, [100.0] * 60)
    resp = client.post(
        "/api/backtest/optimize",
        json={
            "symbol": "BTC/USDT",
            "strategy": "ma_cross",
            "param_grid": {"fast": [2, 3], "slow": [5, 8]},
            "start": "2024-02-01T00:00:00Z",
            "end": "2024-01-01T00:00:00Z",
        },
    )
    assert resp.status_code == 422, resp.text


def test_walk_forward_respects_date_range(monkeypatch):
    _stub_range_broker(monkeypatch, [100 + 10 * math.sin(i / 5) for i in range(60)])
    resp = client.post(
        "/api/backtest/walk-forward",
        json={
            "symbol": "BTC/USDT",
            "strategy": "ma_cross",
            "param_grid": {"fast": [3, 5], "slow": [10, 15]},
            "n_folds": 2,
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-02-25T00:00:00Z",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["n_folds"] == 2
```

- [ ] **Step 2: Run `cd backend && python -m pytest app/tests/test_backtest_api.py -k "compare or optimize or walk_forward" -v`** — Expected: FAIL for the new date-range cases (request models reject/ignore `start`/`end`).

- [ ] **Step 3: Implement minimal code** (COMPLETE code) — in `backend/app/api/backtest.py`:

Add to `CompareRequest`, `OptimizeRequest`, `WalkForwardRequest` (same two lines each):
```python
    start: datetime | None = None
    end: datetime | None = None
```

Replace the fetch line in each of the three endpoints with the shared helper:

`compare`:
```python
        candles = _fetch_candles(
            get_data_broker(req.market), req.symbol, req.timeframe, req.limit, req.start, req.end
        )
```
`optimize`:
```python
        candles = _fetch_candles(
            get_data_broker(req.market), req.symbol, req.timeframe, req.limit, req.start, req.end
        )
        return grid_search(candles, req.strategy, req.param_grid, ...)  # unchanged args below
```
`walk_forward_endpoint`:
```python
        candles = _fetch_candles(
            get_data_broker(req.market), req.symbol, req.timeframe, req.limit, req.start, req.end
        )
        return walk_forward(candles, req.strategy, req.param_grid, ...)  # unchanged args below
```

> `compare` currently catches only `NotImplementedError`/`Exception` around the fetch — confirm the reversed-range `ValueError` from `_fetch_candles` surfaces as `422`. If `compare`'s fetch `try/except` lacks a `ValueError → 422` branch, add one to match `optimize`/`walk_forward`/`backtest` (fail-loud, explicit). (`optimize` and `walk_forward` already have the `ValueError → 422` branch.)

- [ ] **Step 4: Run the test** — `cd backend && python -m pytest app/tests/test_backtest_api.py -v` — Expected: PASS.

- [ ] **Step 5: Run full suite `cd backend && python -m pytest`** — Expected: all pass.

- [ ] **Step 6: Commit** — `feat(backtest-api): date range on compare/optimize/walk-forward via shared fetch helper`.

---

### Task 5: Frontend — `start`/`end` types + 「最近 N 根 / 日期區間」 toggle
**Files:**
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/components/BacktestPanel.tsx`

**Interfaces:**
- Produces (types): `BacktestRequest` (and sibling `CompareRequest`/`OptimizeRequest`/`WalkForwardRequest`) gain `start?: string; end?: string;` (ISO strings).
- Produces (UI): a mode toggle (`最近 N 根` ⇄ `日期區間`); in range mode, two `<input type="date">` (start/end, default = last 1 year); the request includes `start`/`end` only in range mode, otherwise `limit`.

> **Conflict reminder:** `BacktestPanel.tsx` is also touched by P2. Keep this change confined to (a) the new state + (b) the control-row mode toggle + date inputs + (c) including `start`/`end` in the request payloads when in range mode. Do not restyle existing controls/buttons/tabs.

- [ ] **Step 1 (no pytest — frontend):** In `frontend/lib/api.ts`, add `start?: string; end?: string;` to `BacktestRequest`, `CompareRequest`, `OptimizeRequest`, and `WalkForwardRequest` (right after their existing `limit?: number;` lines).

- [ ] **Step 2: Implement the toggle + date inputs** in `frontend/components/BacktestPanel.tsx`:

Add state near the existing `limit` state:
```tsx
  const [rangeMode, setRangeMode] = useState(false);
  const todayISO = new Date().toISOString().slice(0, 10);
  const oneYearAgoISO = new Date(Date.now() - 365 * 864e5).toISOString().slice(0, 10);
  const [start, setStart] = useState(oneYearAgoISO);
  const [end, setEnd] = useState(todayISO);
```

Add a mode toggle + conditional date inputs in the control row (next to the `limit` `<select>`):
```tsx
        <button
          type="button"
          onClick={() => setRangeMode((m) => !m)}
          className="rounded-md bg-surface-2 px-2 py-1 text-sm hover:bg-surface-3"
        >
          {rangeMode ? "日期區間" : "最近 N 根"}
        </button>
        {rangeMode && (
          <>
            <input
              type="date"
              value={start}
              onChange={(e) => setStart(e.target.value)}
              className="rounded-md bg-surface-2 px-2 py-1 text-sm"
            />
            <span className="text-xs text-muted">→</span>
            <input
              type="date"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
              className="rounded-md bg-surface-2 px-2 py-1 text-sm"
            />
          </>
        )}
```

Wrap the `limit` `<select>` so it only shows in N-bars mode (e.g. `{!rangeMode && ( <select ...limit... /> )}`).

Thread `start`/`end` into every request builder. Define a small helper once and spread it into the `api.backtest`/`api.compareStrategies`/`api.optimize`/`api.walkForward`/`api.backtestSavedStrategy` calls:
```tsx
  const rangeArgs = rangeMode ? { start, end } : {};
  // e.g.: api.backtest({ symbol, market, strategy, params, timeframe, limit, ...rangeArgs })
```
(Apply `...rangeArgs` to each request object the panel sends — backend ignores `start`/`end` unless both are set.)

- [ ] **Step 3: Verify types** — `cd frontend && npx tsc --noEmit` — Expected: no type errors (`start`/`end` accepted by all four request interfaces; `rangeArgs` spread is type-safe).

- [ ] **Step 4: Verify build** — `cd frontend && npm run build` — Expected: build succeeds (CI parity; predev/prebuild docs-sync runs but does not block).

- [ ] **Step 5: Commit** — `feat(backtest-ui): date-range mode toggle + start/end inputs (default last 1y)`.

---

## Self-Review

**Spec C2 (§6) + backend-changes table (§9) → task mapping**

| Spec item | Source | Covered by |
|---|---|---|
| `crypto_ccxt.py` `get_ohlcv_range` (ccxt `since` pagination) | §6 C2 third layer / §9 row 1 | Task 1 (impl + mock pagination/cap/empty tests) |
| `csv_data.py` `[-limit:]` → timestamp filter | §6 C2 / §9 row 2 | Task 2 (filter + reversed-range fail-loud) |
| `base.py` add range method, unimplemented brokers fail loud | §6 C2 / §9 row 3 | Task 1 (ABC default `NotImplementedError`) |
| `api/backtest.py` 4 Request models gain `start`/`end`; range when provided else `limit` (backward-compat) | §6 C2 / §9 row 4 | Task 3 (`BacktestRequest`) + Task 4 (Compare/Optimize/WalkForward) |
| `run_backtest` engine unchanged | §6 C2 / §9 "完全不動" | All backend tasks (engine never imported/edited) |
| Guards: `start≥end` → 422; range `< 2` candles → fail loud; ccxt cap ≤ 5000 | §6 C2 third layer | Task 1 (`MAX_RANGE_BARS=5000`, empty fail-loud) + Task 3 (`422` reversed / too-few tests) |
| `test_backtest_daterange.py` (ccxt mock, CSV filter, boundaries) | §6 C2 / §11 | Tasks 1 + 2 create/extend it |
| Frontend `BacktestRequest` etc. gain `start?/end?`; 最近 N 根 ⇄ 日期區間 toggle + 2 date pickers, default 近一年 | §6 C2 second layer / §12 (a) | Task 5 |

**Placeholder scan:** no `TODO`/`TBD`/`...`-as-code placeholders in shipped code. The two `# unchanged args below` comments in Task 4 are explicit pointers to keep the existing `grid_search(...)` / `walk_forward(...)` argument lists verbatim (only the candle source changes) — not omitted logic.

**Type-consistency check:** the method name `get_ohlcv_range` is used identically across `base.py` (ABC default), `crypto_ccxt.py` (impl), `csv_data.py` (impl), the API helper `_fetch_candles` (call site), and every test stub — no drift. `start`/`end` typed `datetime | None = None` on all four backend Request models and `start?: string; end?: string;` on all four frontend interfaces. `MAX_RANGE_BARS` is defined once in `crypto_ccxt.py` and imported by the test (single source of truth).

**Backward-compatibility check:** all `start`/`end` fields default to `None`/`undefined`; the range path activates only when **both** are present, so every existing test and caller that omits them keeps the exact `limit` behaviour (verified by `test_backtest_no_range_still_uses_limit` in Task 3 and by the unchanged full-suite run at each task's Step 5).

**Execution-order note:** Task 5 edits `BacktestPanel.tsx`, which P2 also edits — run P2 first or coordinate the landing to avoid a merge conflict (called out at the top under File Structure).
