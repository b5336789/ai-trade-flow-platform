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
