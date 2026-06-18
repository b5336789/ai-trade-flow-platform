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
from app.marketdata.fx import FxConverter, quote_currency_for
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

    def test_market_quote_currency_map(self):
        assert quote_currency_for(MarketKind.crypto) == "USDT"
        assert quote_currency_for(MarketKind.tw_stock) == "TWD"
        assert quote_currency_for(MarketKind.us_stock) == "USD"


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
