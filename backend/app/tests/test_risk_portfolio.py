"""M0.6 — portfolio-level risk: FX seam, PortfolioGuard gates, kill switch / halt entry-vs-exit.

Deterministic and offline: a StubBroker-backed PaperBroker provides prices and tracks positions;
each test injects an in-memory SQLite session so the persistent runtime flags / order counts are
isolated from the shared dev DB.
"""

from __future__ import annotations

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.brokers import registry
from app.brokers.paper import PaperBroker
from app.marketdata.fx import (
    FxConverter,
    FxRateProviderError,
    FxRateSnapshot,
    OpenErApiFxProvider,
    quote_currency_for,
)
from app.schemas import MarketKind, OrderRequest, OrderSide, TradingMode
from app.tests.helpers import StubBroker
from app.trading import runtime_state
from app.trading.execution import execute_order
from app.trading.risk import PortfolioGuard, RiskError


@pytest.fixture()
def session():
    """A fresh, isolated in-memory DB so runtime flags / order counts don't leak between tests."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    import app.models  # noqa: F401  (register tables)

    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _seed_broker(*, cash: float = 1_000_000.0, price: float = 100.0, held: float = 0.0) -> PaperBroker:
    """Crypto paper broker (quote USDT) with an optional pre-existing long position."""
    registry.reset_paper_brokers()
    broker = PaperBroker(data_provider=StubBroker({"BTC/USDT": price}), starting_cash=cash)
    if held > 0:
        broker.create_order(OrderRequest(symbol="BTC/USDT", side=OrderSide.buy, quantity=held))
    registry._paper_cache[MarketKind.crypto] = broker
    return broker


def _buy(qty: float) -> OrderRequest:
    return OrderRequest(symbol="BTC/USDT", side=OrderSide.buy, quantity=qty)


def _sell(qty: float) -> OrderRequest:
    return OrderRequest(symbol="BTC/USDT", side=OrderSide.sell, quantity=qty)


def _run(request, guard, session):
    # Generous per-order RiskGuard so only the PortfolioGuard is under test.
    from app.trading.risk import RiskGuard

    return execute_order(
        request,
        market=MarketKind.crypto,
        mode=TradingMode.paper,
        guard=RiskGuard(max_order_value=1e12, max_position_value=1e12),
        session=session,
        portfolio_guard=guard,
    )


# --- FxConverter ---


class TestFxConverter:
    def test_base_currency_is_identity(self):
        fx = FxConverter(base_currency="TWD", rates={"TWD": 1.0, "USD": 31.5})
        assert fx.to_base(1000.0, "TWD") == 1000.0

    def test_converts_quote_to_base(self):
        fx = FxConverter(base_currency="TWD", rates={"TWD": 1.0, "USD": 31.5})
        assert fx.to_base(100.0, "USD") == pytest.approx(3150.0)

    def test_missing_rate_fails_loud(self):
        fx = FxConverter(base_currency="TWD", rates={"TWD": 1.0})
        with pytest.raises(ValueError, match="no FX rate"):
            fx.to_base(100.0, "JPY")

    def test_from_settings_builds_default_map(self):
        fx = FxConverter.from_settings()
        assert fx.base_currency == "TWD"
        assert fx.to_base(1.0, "USD") == pytest.approx(31.5)

    def test_provider_rates_are_cached_until_ttl(self):
        now = 1000.0
        provider = _RecordingFxProvider(
            FxRateSnapshot(rates={"USD": 32.0, "USDT": 32.0}),
            FxRateSnapshot(rates={"USD": 33.0, "USDT": 33.0}),
        )
        fx = FxConverter(
            base_currency="TWD",
            provider=provider,
            live_currencies={"USD", "USDT"},
            cache_ttl_seconds=60,
            time_fn=lambda: now,
        )

        assert fx.to_base(10.0, "USD") == pytest.approx(320.0)
        now = 1059.0
        assert fx.to_base(10.0, "USD") == pytest.approx(320.0)
        now = 1061.0
        assert fx.to_base(10.0, "USD") == pytest.approx(330.0)
        assert provider.calls == [
            ("TWD", {"USD", "USDT"}),
            ("TWD", {"USD", "USDT"}),
        ]

    def test_expired_provider_failure_fails_loud_instead_of_using_stale_rate(self):
        now = 1000.0
        provider = _RecordingFxProvider(
            FxRateSnapshot(rates={"USD": 32.0}),
            RuntimeError("upstream unavailable"),
        )
        fx = FxConverter(
            base_currency="TWD",
            provider=provider,
            live_currencies={"USD"},
            cache_ttl_seconds=60,
            time_fn=lambda: now,
        )

        assert fx.to_base(1.0, "USD") == pytest.approx(32.0)
        now = 1061.0
        with pytest.raises(FxRateProviderError, match="FX provider refresh failed"):
            fx.to_base(1.0, "USD")

    def test_provider_missing_currency_fails_loud(self):
        provider = _RecordingFxProvider(FxRateSnapshot(rates={"USD": 32.0}))
        fx = FxConverter(
            base_currency="TWD",
            provider=provider,
            live_currencies={"USD", "USDT"},
            cache_ttl_seconds=60,
        )

        with pytest.raises(ValueError, match="missing FX rates.*USDT"):
            fx.to_base(1.0, "USDT")

    def test_from_settings_uses_live_provider_when_selected(self, monkeypatch):
        from app.config import Settings
        import app.config as config_module

        monkeypatch.setattr(
            config_module,
            "settings",
            Settings(_env_file=None, fx_provider="open_er_api", fx_rate_cache_ttl_seconds=123),
        )

        fx = FxConverter.from_settings()
        assert isinstance(fx.provider, OpenErApiFxProvider)
        assert fx.cache_ttl_seconds == 123

    def test_market_quote_currency_map(self):
        assert quote_currency_for(MarketKind.crypto) == "USDT"
        assert quote_currency_for(MarketKind.tw_stock) == "TWD"
        assert quote_currency_for(MarketKind.us_stock) == "USD"


class _RecordingFxProvider:
    def __init__(self, *results):
        self._results = list(results)
        self.calls: list[tuple[str, set[str]]] = []

    def latest_rates(self, *, base_currency: str, currencies: set[str]) -> FxRateSnapshot:
        self.calls.append((base_currency, set(currencies)))
        result = self._results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class _FakeResponse:
    def __init__(self, payload: dict, *, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> dict:
        return self._payload


class _FakeHttpClient:
    def __init__(self, response: _FakeResponse):
        self.response = response
        self.urls: list[str] = []

    def get(self, url: str) -> _FakeResponse:
        self.urls.append(url)
        return self.response


def test_open_er_api_provider_builds_usd_and_usdt_twd_rates():
    client = _FakeHttpClient(_FakeResponse({"result": "success", "rates": {"TWD": 32.25}}))
    provider = OpenErApiFxProvider(client=client)

    snapshot = provider.latest_rates(base_currency="TWD", currencies={"USD", "USDT"})

    assert snapshot.rates["TWD"] == 1.0
    assert snapshot.rates["USD"] == pytest.approx(32.25)
    assert snapshot.rates["USDT"] == pytest.approx(32.25)
    assert client.urls == ["https://open.er-api.com/v6/latest/USD"]


# --- PortfolioGuard caps reject ENTRIES (buys) ---


def _fx() -> FxConverter:
    # 1 USDT = 31.5 TWD so base-currency math is exercised (not a trivial 1:1).
    return FxConverter(base_currency="TWD", rates={"TWD": 1.0, "USDT": 31.5})


class TestPortfolioGuardEntries:
    def test_exposure_cap_rejects_buy(self, session):
        broker = _seed_broker(cash=1_000_000.0, price=100.0)
        # Buying 100 BTC @ 100 = 10_000 USDT = 315_000 TWD. Cap = 300_000 TWD -> reject.
        guard = PortfolioGuard(
            max_total_exposure_value=300_000.0, max_daily_loss=1e12,
            max_orders_per_day=1000, fx=_fx(),
        )
        with pytest.raises(RiskError, match="total exposure"):
            _run(_buy(100), guard, session)

    def test_daily_loss_breach_halts_and_rejects_buy(self, session):
        broker = _seed_broker(cash=1_000_000.0, price=100.0, held=10.0)
        # Snapshot today's baseline at the current (higher) equity, then crash the price.
        view0 = broker  # noqa: F841
        guard = PortfolioGuard(
            max_total_exposure_value=1e12, max_daily_loss=100_000.0,
            max_orders_per_day=1000, fx=_fx(),
        )
        # First, establish the day-start equity baseline at price 100.
        from app.trading.portfolio import build_portfolio
        equity0 = _fx().to_base(build_portfolio(broker).equity, "USDT")
        runtime_state.get_or_snapshot_day_start_equity(session, equity0)
        # Now crash the mark: equity drops by 10 BTC * 90 USDT * 31.5 = 28_350... make it big.
        broker._data.set_price("BTC/USDT", 10.0)  # -90/unit on 10 BTC = -900 USDT = -28_350 TWD
        # Loss 28_350 < 100_000, so widen by lowering the cap to force the breach.
        guard.max_daily_loss = 10_000.0
        with pytest.raises(RiskError, match="daily loss"):
            _run(_buy(1), guard, session)
        assert runtime_state.get_halted(session) is True

    def test_orders_per_day_cap_rejects_buy(self, session):
        broker = _seed_broker(cash=1_000_000.0, price=100.0)
        guard = PortfolioGuard(
            max_total_exposure_value=1e12, max_daily_loss=1e12,
            max_orders_per_day=2, fx=_fx(),
        )
        _run(_buy(1), guard, session)
        _run(_buy(1), guard, session)
        with pytest.raises(RiskError, match="max_orders_per_day"):
            _run(_buy(1), guard, session)

    def test_kill_switch_rejects_buy(self, session):
        broker = _seed_broker(cash=1_000_000.0, price=100.0)
        runtime_state.set_kill_switch(session, True)
        guard = PortfolioGuard(
            max_total_exposure_value=1e12, max_daily_loss=1e12,
            max_orders_per_day=1000, fx=_fx(),
        )
        with pytest.raises(RiskError, match="kill switch"):
            _run(_buy(1), guard, session)


# --- EXITS always allowed (the safety-critical semantic) ---


class TestPortfolioGuardExits:
    def test_sell_executes_while_kill_switched(self, session):
        broker = _seed_broker(cash=1_000_000.0, price=100.0, held=10.0)
        runtime_state.set_kill_switch(session, True)
        guard = PortfolioGuard(
            max_total_exposure_value=0.0, max_daily_loss=0.0,
            max_orders_per_day=0, fx=_fx(),
        )
        result = _run(_sell(5), guard, session)  # position-reducing exit
        assert result.status == "filled"
        assert result.side == OrderSide.sell

    def test_sell_executes_while_halted(self, session):
        broker = _seed_broker(cash=1_000_000.0, price=100.0, held=10.0)
        runtime_state.set_halted(session, True)
        guard = PortfolioGuard(
            max_total_exposure_value=0.0, max_daily_loss=0.0,
            max_orders_per_day=0, fx=_fx(),
        )
        result = _run(_sell(10), guard, session)  # full close
        assert result.status == "filled"
