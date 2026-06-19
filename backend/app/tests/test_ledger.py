"""FIFO realized-P&L ledger tests (M1.3) — deterministic, offline.

The headline acceptance identity uses crypto (tax=0) so the gross number is clean:
buy 100@10, buy 100@12, sell 150@15 -> FIFO gross = (15-10)*100 + (15-12)*50 = 650.
A tw_stock case additionally exercises sell 證交稅. All costs come from CostModel (M0.1).
"""

from __future__ import annotations

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from app.db import engine
from app.models import Lot, RealizedPnL
from app.schemas import MarketKind, OrderSide
from app.trading.costs import CostModel
from app.trading.ledger import FifoLedger


@pytest.fixture()
def isolated_session():
    """A fresh in-memory DB for the execute_order integration tests.

    execute_order runs the PortfolioGuard, which persists per-day equity baselines / order counts
    to RuntimeFlag. Using an isolated engine keeps that bookkeeping out of the shared dev DB so it
    can't leak into other tests (the same pattern as test_risk_portfolio).
    """
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False})
    import app.models  # noqa: F401  (register tables)

    SQLModel.metadata.create_all(eng)
    with Session(eng) as s:
        yield s


def _ledger(session: Session, cost: CostModel | None = None) -> FifoLedger:
    return FifoLedger(session, cost_model=cost or CostModel.zero())


def test_fifo_gross_realized_pnl_crypto():
    """buy 100@10, buy 100@12, sell 150@15 -> gross 650 (crypto: tax=0, net==gross with zero cost)."""
    with Session(engine) as session:
        led = _ledger(session, CostModel.zero())
        sym = "ACC/USDT"
        led.record_buy(MarketKind.crypto, sym, quantity=100, price=10.0, fee=0.0)
        led.record_buy(MarketKind.crypto, sym, quantity=100, price=12.0, fee=0.0)
        disposals = led.record_sell(MarketKind.crypto, sym, quantity=150, price=15.0)
        session.commit()

        gross = sum(d.gross_pnl for d in disposals)
        net = sum(d.realized_net for d in disposals)
        assert gross == pytest.approx(650.0)
        assert net == pytest.approx(650.0)  # zero-cost model -> no fees/tax

        # FIFO ordering: first lot (100@10) fully consumed, second lot (100@12) half consumed.
        lots = session.exec(select(Lot).where(Lot.symbol == sym).order_by(Lot.opened_at, Lot.id)).all()
        assert lots[0].remaining_quantity == pytest.approx(0.0)
        assert lots[1].remaining_quantity == pytest.approx(50.0)


def test_fifo_net_with_crypto_fees():
    """Net = gross - apportioned buy fee - sell fee (crypto tax=0). Fees from CostModel."""
    cost = CostModel.from_settings()  # default crypto taker 7.5 bps
    with Session(engine) as session:
        led = _ledger(session, cost)
        sym = "FEE/USDT"
        # Buy fees as CostModel computes them, recorded into the lot cost basis.
        f1 = cost.fill_cost(MarketKind.crypto, OrderSide.buy, 10.0, 100).fee
        f2 = cost.fill_cost(MarketKind.crypto, OrderSide.buy, 12.0, 100).fee
        led.record_buy(MarketKind.crypto, sym, quantity=100, price=10.0, fee=f1)
        led.record_buy(MarketKind.crypto, sym, quantity=100, price=12.0, fee=f2)
        disposals = led.record_sell(MarketKind.crypto, sym, quantity=150, price=15.0)
        session.commit()

        gross = sum(d.gross_pnl for d in disposals)
        assert gross == pytest.approx(650.0)

        # Apportioned buy fees: lot1 fully consumed (f1), lot2 half consumed (f2 * 50/100).
        buy_fee_portion = f1 + f2 * 0.5
        sell_fee = cost.fill_cost(MarketKind.crypto, OrderSide.sell, 15.0, 150).fee
        expected_net = 650.0 - buy_fee_portion - sell_fee
        net = sum(d.realized_net for d in disposals)
        assert net == pytest.approx(expected_net)
        assert sum(d.tax for d in disposals) == pytest.approx(0.0)


def test_fifo_tw_stock_applies_sell_tax():
    """tw_stock disposal includes 證交稅 (0.3% of sell proceeds) in the net."""
    cost = CostModel.from_settings()
    with Session(engine) as session:
        led = _ledger(session, cost)
        sym = "2330"
        led.record_buy(MarketKind.tw_stock, sym, quantity=100, price=10.0, fee=0.0)
        disposals = led.record_sell(MarketKind.tw_stock, sym, quantity=100, price=15.0)
        session.commit()

        assert len(disposals) == 1
        d = disposals[0]
        assert d.gross_pnl == pytest.approx(500.0)  # (15-10)*100
        expected_tax = 15.0 * 100 * cost.tw_tax_rate
        assert d.tax == pytest.approx(expected_tax)
        assert d.tax > 0.0
        expected_sell_fee = cost.fill_cost(MarketKind.tw_stock, OrderSide.sell, 15.0, 100).fee
        assert d.realized_net == pytest.approx(500.0 - expected_sell_fee - expected_tax)


def test_partial_lot_disposal_leaves_remainder():
    """Selling less than the oldest lot leaves the lot open with reduced remaining_quantity."""
    with Session(engine) as session:
        led = _ledger(session, CostModel.zero())
        sym = "PARTIAL/USDT"
        led.record_buy(MarketKind.crypto, sym, quantity=100, price=10.0, fee=0.0)
        disposals = led.record_sell(MarketKind.crypto, sym, quantity=30, price=12.0)
        session.commit()

        assert len(disposals) == 1
        assert disposals[0].quantity == pytest.approx(30.0)
        assert disposals[0].gross_pnl == pytest.approx(60.0)  # (12-10)*30
        lot = session.exec(select(Lot).where(Lot.symbol == sym)).one()
        assert lot.remaining_quantity == pytest.approx(70.0)


def test_oversell_fails_loud():
    """Selling more than the open lots can cover raises (fail loud — no negative lots)."""
    with Session(engine) as session:
        led = _ledger(session, CostModel.zero())
        sym = "SHORT/USDT"
        led.record_buy(MarketKind.crypto, sym, quantity=10, price=10.0, fee=0.0)
        with pytest.raises(ValueError, match="exceeds open lots"):
            led.record_sell(MarketKind.crypto, sym, quantity=20, price=12.0)


# --- Integration: wired into execute_order (the chosen seam) ---


def test_execute_order_records_lots_and_disposals(isolated_session):
    """A paper buy then sell through execute_order populates Lot and RealizedPnL."""
    from app.brokers import registry
    from app.brokers.paper import PaperBroker
    from app.schemas import OrderRequest
    from app.tests.helpers import StubBroker
    from app.trading.execution import execute_order

    registry.reset_paper_brokers()
    registry._paper_cache[MarketKind.crypto] = PaperBroker(
        data_provider=StubBroker({"LDG/USDT": 100.0}), starting_cash=1_000_000.0
    )
    try:
        execute_order(
            OrderRequest(symbol="LDG/USDT", side=OrderSide.buy, quantity=10),
            market=MarketKind.crypto,
            session=isolated_session,
        )
        registry._paper_cache[MarketKind.crypto]._data.set_price("LDG/USDT", 120.0)
        execute_order(
            OrderRequest(symbol="LDG/USDT", side=OrderSide.sell, quantity=10),
            market=MarketKind.crypto,
            session=isolated_session,
        )
        lots = isolated_session.exec(select(Lot).where(Lot.symbol == "LDG/USDT")).all()
        disposals = isolated_session.exec(
            select(RealizedPnL).where(RealizedPnL.symbol == "LDG/USDT")
        ).all()
        assert len(lots) == 1
        assert lots[0].remaining_quantity == pytest.approx(0.0)
        assert len(disposals) == 1
        # gross ~ (120-100)*10 = 200 (default test settings have zero slippage).
        assert disposals[0].gross_pnl == pytest.approx(200.0, abs=1.0)
    finally:
        registry.reset_paper_brokers()


def test_idempotent_skip_does_not_double_count(isolated_session):
    """A duplicate client_order_id (M0.5 skip) must not create extra lots."""
    import uuid

    from app.brokers import registry
    from app.brokers.paper import PaperBroker
    from app.schemas import OrderRequest
    from app.tests.helpers import StubBroker
    from app.trading.execution import execute_order

    registry.reset_paper_brokers()
    registry._paper_cache[MarketKind.crypto] = PaperBroker(
        data_provider=StubBroker({"IDEM/USDT": 50.0}), starting_cash=1_000_000.0
    )
    coid = f"ledger-coid-{uuid.uuid4().hex}"
    try:
        req = OrderRequest(symbol="IDEM/USDT", side=OrderSide.buy, quantity=4)
        execute_order(req, market=MarketKind.crypto, session=isolated_session, client_order_id=coid)
        execute_order(req, market=MarketKind.crypto, session=isolated_session, client_order_id=coid)
        lots = isolated_session.exec(select(Lot).where(Lot.symbol == "IDEM/USDT")).all()
        assert len(lots) == 1  # the skipped rerun added no lot
    finally:
        registry.reset_paper_brokers()
