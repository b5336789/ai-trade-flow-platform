# Portfolio Truth Surface — Cross-Market Summary + Realized Ledger UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make capital truth visible. (1) A new `GET /api/portfolio/summary` aggregates each market's equity into the base currency (TWD) via the FX seam; (2) the realized-P&L report gains a correct base-currency aggregate (fixing the mixed-currency `sum`); (3) the frontend gains a cross-market portfolio overview and a **Realized Ledger** page wired to the backend's FIFO ledger + tax CSV that the UI currently never calls.

**Architecture:** Backend adds one read-only router (`app/api/portfolio.py`) and a base-currency aggregate to the existing ledger report — both reuse `build_portfolio`, `FxConverter`, and `quote_currency_for` (the same pattern `api/risk.py` already uses). Frontend adds typed clients, a cross-market summary section on the 投組 overview, and a new `投組 → 損益帳本` page + nav. No changes to execution, brokers, or the FIFO ledger writer.

**Tech Stack:** Backend: FastAPI + SQLModel + pydantic + pytest (TDD). Frontend: Next.js 14 App Router + TypeScript + React Query + Tailwind; **no frontend test runner** (verify with `npx tsc --noEmit` + `npm run build` + run-app visual).

## Global Constraints

- **Branch, never `main`.** Work on `feat/portfolio-ledger`; open a PR at the end.
- **Fail loud:** per-market portfolio failures are reported (an `available:false` + `error` field), never silently dropped; invalid ledger date filters already 422 (keep).
- **FX correctness:** every cross-currency aggregate goes through `FxConverter.to_base(value, quote_currency_for(market))`. Never sum native amounts across markets.
- **DESIGN.md tokens (verbatim):** price/PnL via `--up`/`--down` (台股 inverts via `data-market="tw"`); realized P&L is a price-direction value → `--up`/`--down` is correct for it. `price_source="avg_fallback"` must render a `--warning` flag (don't hide a stale price). `--accent` (cyan) = AI only — not for portfolio/ledger UI. `.num` for figures. Tight radii.
- **No new dependencies.**
- **Backend test command:** `cd backend && ./.venv/bin/python -m pytest -q`. **Frontend:** `cd frontend && npx tsc --noEmit` (per task) + `npm run build` (controller, per wave).

---

### Task 1: `GET /api/portfolio/summary` — cross-market FX aggregate (backend, TDD)

**Files:**
- Create: `backend/app/api/portfolio.py`
- Modify: `backend/app/main.py` (register the router — mirror the existing `app.include_router(...)` lines)
- Test: `backend/app/tests/test_portfolio_summary.py`

**Interfaces:**
- Produces: `GET /api/portfolio/summary` → `PortfolioSummary { base_currency, total_cash_base, total_positions_value_base, total_equity_base, markets: MarketSummary[] }`; `MarketSummary { market, available, quote_currency, cash_native, positions_value_native, equity_native, cash_base, positions_value_base, equity_base, num_positions, error }`.

- [ ] **Step 1: Write the failing test** — `backend/app/tests/test_portfolio_summary.py`:

```python
"""Cross-market portfolio summary aggregates each market's equity into the base currency."""
from __future__ import annotations

import pytest

import app.api.portfolio as pf
from app.schemas import MarketKind


class _Bal:
    def __init__(self, free): self.free = free

class _Pos:
    def __init__(self, symbol, quantity, avg_price):
        self.symbol, self.quantity, self.avg_price = symbol, quantity, avg_price

class _Tick:
    def __init__(self, price): self.price = price

class _CryptoBroker:
    def get_balance(self): return [_Bal(1000.0)]
    def get_positions(self): return [_Pos("BTC/USDT", 1.0, 50.0)]
    def get_ticker(self, symbol): return _Tick(60.0)


def test_summary_aggregates_to_base_and_skips_unavailable(monkeypatch):
    def fake_get_broker(market):
        if market == MarketKind.crypto:
            return _CryptoBroker()
        raise NotImplementedError(f"{market.value}: live brokers not implemented yet")
    monkeypatch.setattr(pf, "get_broker", fake_get_broker)

    out = pf.portfolio_summary()

    assert out.base_currency == "TWD"
    crypto = next(m for m in out.markets if m.market == "crypto")
    # equity_native = 1000 cash + 60 (1 * 60 ticker) = 1060 USDT
    assert crypto.available is True
    assert crypto.quote_currency == "USDT"
    assert crypto.equity_native == pytest.approx(1060.0)
    # USDT->TWD via default static fx_rates (USDT: 31.5)
    assert crypto.equity_base == pytest.approx(1060.0 * 31.5)
    assert out.total_equity_base == pytest.approx(1060.0 * 31.5)
    # tw/us unavailable, contribute 0 and carry the loud error
    tw = next(m for m in out.markets if m.market == "tw_stock")
    assert tw.available is False and tw.error and "not implemented" in tw.error
    assert tw.equity_base == 0.0
```

- [ ] **Step 2: Run it — fails** (`module app.api.portfolio` missing):

Run: `cd backend && ./.venv/bin/python -m pytest app/tests/test_portfolio_summary.py -q`
Expected: FAIL (import error / `portfolio_summary` undefined).

- [ ] **Step 3: Implement the router** — `backend/app/api/portfolio.py`:

```python
"""Cross-market portfolio summary: per-market equity converted to base currency, then aggregated.

Read-only. Reuses build_portfolio + the FX seam (same pattern as api/risk.py). A market whose
broker isn't available (no live/imported data -> NotImplementedError) is reported available=false
with its error, never silently dropped.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.brokers.registry import get_broker
from app.marketdata.fx import FxConverter, quote_currency_for
from app.schemas import MarketKind
from app.trading.portfolio import build_portfolio

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


class MarketSummary(BaseModel):
    market: str
    available: bool
    quote_currency: str
    cash_native: float
    positions_value_native: float
    equity_native: float
    cash_base: float
    positions_value_base: float
    equity_base: float
    num_positions: int
    error: str | None = None


class PortfolioSummary(BaseModel):
    base_currency: str
    total_cash_base: float
    total_positions_value_base: float
    total_equity_base: float
    markets: list[MarketSummary]


@router.get("/summary", response_model=PortfolioSummary)
def portfolio_summary() -> PortfolioSummary:
    fx = FxConverter.from_settings()
    markets: list[MarketSummary] = []
    total_cash = total_pos = total_eq = 0.0

    for market in MarketKind:
        quote = quote_currency_for(market)
        try:
            view = build_portfolio(get_broker(market))
        except NotImplementedError as exc:
            markets.append(
                MarketSummary(
                    market=market.value, available=False, quote_currency=quote,
                    cash_native=0.0, positions_value_native=0.0, equity_native=0.0,
                    cash_base=0.0, positions_value_base=0.0, equity_base=0.0,
                    num_positions=0, error=str(exc),
                )
            )
            continue
        cash_base = fx.to_base(view.cash, quote)
        pos_base = fx.to_base(view.positions_value, quote)
        eq_base = fx.to_base(view.equity, quote)
        total_cash += cash_base
        total_pos += pos_base
        total_eq += eq_base
        markets.append(
            MarketSummary(
                market=market.value, available=True, quote_currency=quote,
                cash_native=view.cash, positions_value_native=view.positions_value,
                equity_native=view.equity, cash_base=cash_base,
                positions_value_base=pos_base, equity_base=eq_base,
                num_positions=len(view.positions),
            )
        )

    return PortfolioSummary(
        base_currency=fx.base_currency, total_cash_base=total_cash,
        total_positions_value_base=total_pos, total_equity_base=total_eq, markets=markets,
    )
```

- [ ] **Step 4: Register the router** — in `backend/app/main.py`, add `portfolio` to the `from app.api import (...)` group and an `app.include_router(portfolio.router)` line alongside the others (mirror the existing registrations exactly; read the file to place it).

- [ ] **Step 5: Run the test — passes**

Run: `cd backend && ./.venv/bin/python -m pytest app/tests/test_portfolio_summary.py -q`
Expected: PASS. (If `quote_currency_for(MarketKind.crypto)` is not `"USDT"`, read `marketdata/fx.py:MARKET_QUOTE_CURRENCY` and adjust the test's expected quote/rate to the actual mapping — the FX math, not the literal, is the assertion.)

- [ ] **Step 6: Run the full suite**

Run: `cd backend && ./.venv/bin/python -m pytest -q`
Expected: PASS.

- [ ] **Step 7: Commit** — `feat(portfolio): cross-market FX-aggregated /api/portfolio/summary`

---

### Task 2: Base-currency aggregate on the realized-P&L report (backend, TDD)

The report sums `realized_net` etc. across markets in **native** currencies (`ledger.py:83-88`) — meaningless when markets differ. Add base-currency totals; keep native per-disposal values + the CSV (tax filing is per-market native).

**Files:**
- Modify: `backend/app/api/ledger.py` (`RealizedPnLReport` + `realized_report`)
- Test: `backend/app/tests/test_ledger_base_currency.py`

**Interfaces:**
- Produces: `RealizedPnLReport` gains `base_currency: str`, `total_realized_net_base: float`, `total_gross_pnl_base: float`.

- [ ] **Step 1: Write the failing test** — `backend/app/tests/test_ledger_base_currency.py`:

```python
"""Realized-P&L report exposes a correct base-currency aggregate across markets."""
from __future__ import annotations

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.api.ledger import realized_report
from app.models import RealizedPnL


@pytest.fixture()
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    import app.models  # noqa: F401
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_base_currency_aggregate(session):
    # crypto disposal: realized_net 100 USDT; tw disposal: realized_net 100 TWD.
    session.add(RealizedPnL(market="crypto", symbol="BTC/USDT", quantity=1, proceeds=0,
                            cost_basis=0, realized_net=100.0, gross_pnl=100.0))
    session.add(RealizedPnL(market="tw_stock", symbol="2330", quantity=1, proceeds=0,
                            cost_basis=0, realized_net=100.0, gross_pnl=100.0))
    session.commit()

    rep = realized_report(session=session)

    assert rep.count == 2
    assert rep.base_currency == "TWD"
    # 100 USDT * 31.5 + 100 TWD * 1.0 = 3250
    assert rep.total_realized_net_base == pytest.approx(100.0 * 31.5 + 100.0)
    assert rep.total_gross_pnl_base == pytest.approx(100.0 * 31.5 + 100.0)
    # native total stays a naive sum (only meaningful with a single-market filter)
    assert rep.total_realized_net == pytest.approx(200.0)
```

- [ ] **Step 2: Run it — fails** (`base_currency`/`total_realized_net_base` undefined).

Run: `cd backend && ./.venv/bin/python -m pytest app/tests/test_ledger_base_currency.py -q`
Expected: FAIL.

- [ ] **Step 3: Implement** — `backend/app/api/ledger.py`:

Add imports near the top (after line 20):
```python
from app.marketdata.fx import FxConverter, quote_currency_for
```
Add fields to `RealizedPnLReport` (after `total_realized_net: float`, line 34):
```python
    base_currency: str
    total_realized_net_base: float
    total_gross_pnl_base: float
```
Replace the `return RealizedPnLReport(...)` in `realized_report` (lines 81-90) with:
```python
    fx = FxConverter.from_settings()

    def _to_base(attr: str) -> float:
        return sum(fx.to_base(getattr(r, attr), quote_currency_for(MarketKind(r.market))) for r in rows)

    return RealizedPnLReport(
        count=len(rows),
        total_proceeds=sum(r.proceeds for r in rows),
        total_cost_basis=sum(r.cost_basis for r in rows),
        total_fee=sum(r.fee for r in rows),
        total_tax=sum(r.tax for r in rows),
        total_gross_pnl=sum(r.gross_pnl for r in rows),
        total_realized_net=sum(r.realized_net for r in rows),
        base_currency=fx.base_currency,
        total_realized_net_base=_to_base("realized_net"),
        total_gross_pnl_base=_to_base("gross_pnl"),
        disposals=rows,
    )
```
(`MarketKind` is already imported in `ledger.py`.)

- [ ] **Step 4: Run test + full suite**

Run: `cd backend && ./.venv/bin/python -m pytest app/tests/test_ledger_base_currency.py -q && ./.venv/bin/python -m pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit** — `fix(ledger): base-currency aggregate (stop summing across currencies)`

---

### Task 3: Typed clients (frontend)

**Files:**
- Modify: `frontend/lib/api.ts`

**Interfaces:**
- Produces: `PortfolioSummary`/`MarketSummary`, `RealizedPnLReport`/`RealizedDisposal` interfaces; `api.portfolioSummary()`, `api.realizedLedger(params?)`, and `api.downloadLedgerCsv(params?)` (a fetch+blob download that carries the auth header).

- [ ] **Step 1: Add interfaces** — in `frontend/lib/api.ts`, after `PortfolioView` (after line 60):

```typescript
export interface MarketSummary {
  market: string;
  available: boolean;
  quote_currency: string;
  cash_native: number;
  positions_value_native: number;
  equity_native: number;
  cash_base: number;
  positions_value_base: number;
  equity_base: number;
  num_positions: number;
  error: string | null;
}

export interface PortfolioSummary {
  base_currency: string;
  total_cash_base: number;
  total_positions_value_base: number;
  total_equity_base: number;
  markets: MarketSummary[];
}

export interface RealizedDisposal {
  id: number;
  market: string;
  symbol: string;
  quantity: number;
  proceeds: number;
  cost_basis: number;
  fee: number;
  tax: number;
  gross_pnl: number;
  realized_net: number;
  closed_at: string;
}

export interface RealizedPnLReport {
  count: number;
  total_proceeds: number;
  total_cost_basis: number;
  total_fee: number;
  total_tax: number;
  total_gross_pnl: number;
  total_realized_net: number;
  base_currency: string;
  total_realized_net_base: number;
  total_gross_pnl_base: number;
  disposals: RealizedDisposal[];
}
```

- [ ] **Step 2: Add client methods** — inside the `api` object, after `orders` (after line 415):

```typescript
  portfolioSummary: () => request<PortfolioSummary>("/api/portfolio/summary"),
  realizedLedger: (params?: { market?: string; symbol?: string; start?: string; end?: string }) => {
    const q = new URLSearchParams();
    if (params?.market) q.set("market", params.market);
    if (params?.symbol) q.set("symbol", params.symbol);
    if (params?.start) q.set("start", params.start);
    if (params?.end) q.set("end", params.end);
    const qs = q.toString();
    return request<RealizedPnLReport>(`/api/ledger/realized${qs ? `?${qs}` : ""}`);
  },
  downloadLedgerCsv: async (params?: { market?: string }) => {
    const q = new URLSearchParams();
    if (params?.market) q.set("market", params.market);
    const qs = q.toString();
    const headers: Record<string, string> = {};
    if (API_TOKEN) headers.Authorization = `Bearer ${API_TOKEN}`;
    const res = await fetch(`${BASE}/api/ledger/realized.csv${qs ? `?${qs}` : ""}`, { headers });
    if (!res.ok) throw new Error(`CSV download failed: ${res.status}`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "realized_pnl.csv";
    a.click();
    URL.revokeObjectURL(url);
  },
```

- [ ] **Step 3: Typecheck** — `cd frontend && npx tsc --noEmit` → no errors.
- [ ] **Step 4: Commit** — `feat(api): portfolio summary + realized ledger client methods`

---

### Task 4: Cross-market summary on the 投組 overview (frontend)

Add a cross-market TWD aggregate + per-market allocation to the top of `PortfolioPanel`, and surface the `price_source="avg_fallback"` flag on positions (don't hide a stale price). The existing single-(active-)market positions table stays.

**Files:**
- Modify: `frontend/components/PortfolioPanel.tsx`

**Interfaces:**
- Consumes: `api.portfolioSummary` (T3), `useActiveMarket` (already merged).

- [ ] **Step 1: Add the cross-market summary block** — in `frontend/components/PortfolioPanel.tsx`:

Add the query (after the existing `portfolio` query):
```tsx
  const summary = useQuery({ queryKey: ["portfolio-summary"], queryFn: api.portfolioSummary, refetchInterval: 5000, retry: false });
```
Render this block immediately under the panel header (above the existing single-market `Stat` grid). It shows the base-currency total equity and a per-available-market allocation row:
```tsx
      {summary.data && (
        <div className="mb-3 rounded-md border border-border bg-surface-2 p-3">
          <div className="flex items-baseline justify-between">
            <span className="text-xs text-faint">跨市場總權益（{summary.data.base_currency}）</span>
            <span className="num text-lg font-semibold">{money(summary.data.total_equity_base)}</span>
          </div>
          <div className="mt-2 space-y-1">
            {summary.data.markets.filter((m) => m.available).map((m) => {
              const w = summary.data.total_equity_base > 0 ? (m.equity_base / summary.data.total_equity_base) * 100 : 0;
              return (
                <div key={m.market} className="flex items-center gap-2 text-xs">
                  <span className="w-20 text-muted">{m.market}</span>
                  <div className="h-1.5 flex-1 overflow-hidden rounded-sm bg-surface-3">
                    <div className="h-full bg-text/40" style={{ width: `${w}%` }} />
                  </div>
                  <span className="num w-28 text-right text-text">{money(m.equity_base)}</span>
                  <span className="num w-12 text-right text-faint">{w.toFixed(0)}%</span>
                </div>
              );
            })}
            {summary.data.markets.filter((m) => !m.available).length > 0 && (
              <p className="text-[11px] text-faint">
                未連線市場：{summary.data.markets.filter((m) => !m.available).map((m) => m.market).join("、")}（無資料 / 尚未實作）
              </p>
            )}
          </div>
        </div>
      )}
```
In the existing positions table, surface the stale-price flag: in the position row, when `p.price_source === "avg_fallback"`, append a `--warning` marker next to the current price, e.g. change the current-price cell to:
```tsx
                    <td className="num">
                      {money(p.current_price)}
                      {p.price_source === "avg_fallback" && <span className="ml-1 text-warning" title="現價不可得，退回成本價">⚠</span>}
                    </td>
```

- [ ] **Step 2: Typecheck** — `cd frontend && npx tsc --noEmit` → no errors.
- [ ] **Step 3: Commit** — `feat(portfolio-ui): cross-market TWD summary + avg_fallback price flag`

---

### Task 5: Realized Ledger page + 投組 nav (frontend)

**Files:**
- Create: `frontend/app/(rooms)/portfolio/ledger/page.tsx`
- Create: `frontend/components/LedgerPanel.tsx`
- Modify: `frontend/lib/nav.ts` (投組 → 總覽 + 損益帳本)

**Interfaces:**
- Consumes: `api.realizedLedger` + `api.downloadLedgerCsv` (T3).

- [ ] **Step 1: Nav** — in `frontend/lib/nav.ts`, add `ReceiptText` to the lucide import and turn 投組 into a parent (replace the single `{ label: "投組", href: "/portfolio", icon: Wallet }` entry):

```tsx
  {
    label: "投組",
    icon: Wallet,
    children: [
      { label: "總覽", href: "/portfolio", icon: Wallet },
      { label: "損益帳本", href: "/portfolio/ledger", icon: ReceiptText },
    ],
  },
```
(Add `ReceiptText` to the existing `from "lucide-react"` import.)

- [ ] **Step 2: LedgerPanel** — `frontend/components/LedgerPanel.tsx`:

```tsx
"use client";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

function money(n: number) {
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export function LedgerPanel() {
  const ledger = useQuery({ queryKey: ["realized-ledger"], queryFn: () => api.realizedLedger(), retry: false });

  if (ledger.isError) {
    return <p className="text-sm text-error">損益帳本載入失敗：{(ledger.error as Error).message}</p>;
  }
  if (!ledger.data) return <p className="text-sm text-faint">載入中…</p>;
  const r = ledger.data;

  return (
    <section className="space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="font-display text-xl font-semibold">損益帳本（已實現）</h1>
        <span className="text-xs text-faint">{r.count} 筆處分 · 計價 {r.base_currency}</span>
        <button
          onClick={() => api.downloadLedgerCsv()}
          className="ml-auto rounded-md border border-border bg-surface-2 px-3 py-1.5 text-[13px] text-muted hover:text-text"
        >
          匯出 CSV（報稅）
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Kpi label={`已實現淨損益（${r.base_currency}）`} value={r.total_realized_net_base} colored />
        <Kpi label={`毛損益（${r.base_currency}）`} value={r.total_gross_pnl_base} colored />
        <Kpi label="總手續費（native sum）" value={r.total_fee} />
        <Kpi label="總證交稅（native sum）" value={r.total_tax} />
      </div>

      {r.disposals.length === 0 ? (
        <p className="text-sm text-faint">尚無已實現損益 — 平倉後會在此列出。</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="text-faint">
              <tr>
                <th className="py-1">平倉時間</th><th>市場</th><th>代號</th><th>數量</th>
                <th>賣出金額</th><th>成本</th><th>費用</th><th>稅</th><th>淨損益</th>
              </tr>
            </thead>
            <tbody>
              {r.disposals.map((d) => (
                <tr key={d.id} className="border-t border-border">
                  <td className="py-1">{new Date(d.closed_at).toLocaleString()}</td>
                  <td>{d.market}</td>
                  <td>{d.symbol}</td>
                  <td className="num">{d.quantity}</td>
                  <td className="num">{money(d.proceeds)}</td>
                  <td className="num">{money(d.cost_basis)}</td>
                  <td className="num">{money(d.fee)}</td>
                  <td className="num">{money(d.tax)}</td>
                  <td className={`num ${d.realized_net >= 0 ? "text-up" : "text-down"}`}>{money(d.realized_net)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function Kpi({ label, value, colored }: { label: string; value: number; colored?: boolean }) {
  const cls = colored ? (value >= 0 ? "text-up" : "text-down") : "text-text";
  return (
    <div className="rounded-md border border-border bg-surface-1 p-3">
      <div className="text-xs text-faint">{label}</div>
      <div className={`num text-lg font-semibold ${cls}`}>{money(value)}</div>
    </div>
  );
}
```

- [ ] **Step 3: Page** — `frontend/app/(rooms)/portfolio/ledger/page.tsx`:

```tsx
import { LedgerPanel } from "@/components/LedgerPanel";

export default function LedgerPage() {
  return <LedgerPanel />;
}
```

- [ ] **Step 4: Typecheck** — `cd frontend && npx tsc --noEmit` → no errors.
- [ ] **Step 5: Commit** — `feat(ledger-ui): Realized Ledger page + 投組 nav (總覽 / 損益帳本)`

---

### Task 6: Build + visual verification

**Files:** none.

- [ ] **Step 1: Backend suite** — `cd backend && ./.venv/bin/python -m pytest -q` → all pass.
- [ ] **Step 2: Frontend build** — `cd frontend && npm run build` → `✓ Compiled successfully`, 0 type/lint errors, `/portfolio/ledger` route generates.
- [ ] **Step 3: Visual smoke (run-app skill).** Launch the stack; confirm:
  1. 投組 → 總覽: the cross-market 總權益（TWD）block renders with a crypto allocation row; `避vg_fallback` ⚠ shows on any stale-price position.
  2. 投組 → 損益帳本: KPIs (淨損益/毛損益 colored, 費用/稅) + a disposals table (or the empty state); 匯出 CSV downloads `realized_pnl.csv`.
  3. The nav 投組 group expands to 總覽 + 損益帳本.
- [ ] **Step 4: DESIGN check** — realized P&L uses `--up`/`--down`; `avg_fallback` uses `--warning`; no `--accent` in portfolio/ledger UI; `.num` on figures. Nothing to commit unless a fix was needed.

---

## Self-Review

**1. Spec coverage** (roadmap Now-7): cross-market FX aggregate → T1 (+T4 UI); realized ledger UI + tax CSV → T2 (base-currency fix) + T3/T5 (UI + download); price_source surfaced → T4. ✔
**2. Placeholder scan:** new components/endpoints have full code; T1/T4/main.py registration reference existing patterns explicitly. No "TBD".
**3. Type consistency:** `PortfolioSummary`/`MarketSummary` mirror `app/api/portfolio.py`; `RealizedPnLReport`/`RealizedDisposal` mirror `api/ledger.py:RealizedPnLReport` + `models.py:RealizedPnL`; `portfolioSummary`/`realizedLedger`/`downloadLedgerCsv` consistent between T3 (def) and T4/T5 (use).

**Deferred (noted):** equity curve / drawdown over time (needs a snapshot time-series → roadmap Now-7 follow-on / Vision V3); per-strategy attribution (needs `run_id`/`strategy_id` FKs on `RealizedPnL` → Vision V3); wiring the cross-market summary into the Context Bar's equity chip (its own follow-up from #60).

---

## Execution Handoff

**Suggested: subagent-driven, conflict-safe waves:**
- **Wave 1 (parallel):** T1 (backend summary; runs pytest) + T3 (frontend api.ts; no test) — disjoint, T3 no DB.
- **Wave 2 (parallel):** T2 (backend ledger; runs pytest after T1's is done) + T4 (portfolio panel) + T5 (ledger page + nav) — disjoint files; T4/T5 edit-only (no concurrent build), depend on T3.
- **Wave 3:** T6 (controller runs backend suite + `npm run build` + run-app visual).
