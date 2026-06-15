"""Business-logic tests for the paper broker, risk guard, and portfolio valuation."""

from __future__ import annotations

import pytest

from app.brokers.paper import PaperBroker
from app.schemas import OrderRequest, OrderSide
from app.tests.helpers import StubBroker
from app.trading.portfolio import build_portfolio
from app.trading.risk import RiskError, RiskGuard


def make_paper(cash: float = 10_000.0, price: float = 100.0) -> PaperBroker:
    return PaperBroker(data_provider=StubBroker({"BTC/USDT": price}), starting_cash=cash)


class TestPaperBroker:
    def test_buy_reduces_cash_and_opens_position(self):
        broker = make_paper(cash=10_000.0, price=100.0)
        result = broker.create_order(OrderRequest(symbol="BTC/USDT", side=OrderSide.buy, quantity=10))
        assert result.status == "filled"
        assert broker.cash == pytest.approx(9_000.0)  # 10 * 100
        pos = broker.get_positions()[0]
        assert pos.quantity == 10 and pos.avg_price == pytest.approx(100.0)

    def test_sell_realizes_cash_and_closes_position(self):
        broker = make_paper(cash=10_000.0, price=100.0)
        broker.create_order(OrderRequest(symbol="BTC/USDT", side=OrderSide.buy, quantity=10))
        broker._data.set_price("BTC/USDT", 120.0)
        broker.create_order(OrderRequest(symbol="BTC/USDT", side=OrderSide.sell, quantity=10))
        # bought at 100 (-1000), sold at 120 (+1200) -> net +200 over starting cash
        assert broker.cash == pytest.approx(10_200.0)
        assert broker.get_positions() == []

    def test_weighted_average_cost_basis(self):
        broker = make_paper(cash=10_000.0, price=100.0)
        broker.create_order(OrderRequest(symbol="BTC/USDT", side=OrderSide.buy, quantity=10))
        broker._data.set_price("BTC/USDT", 200.0)
        broker.create_order(OrderRequest(symbol="BTC/USDT", side=OrderSide.buy, quantity=10))
        pos = broker.get_positions()[0]
        assert pos.quantity == 20 and pos.avg_price == pytest.approx(150.0)

    def test_insufficient_cash_fails_loud(self):
        broker = make_paper(cash=500.0, price=100.0)
        with pytest.raises(RuntimeError):
            broker.create_order(OrderRequest(symbol="BTC/USDT", side=OrderSide.buy, quantity=10))

    def test_oversell_fails_loud(self):
        broker = make_paper(cash=10_000.0, price=100.0)
        with pytest.raises(RuntimeError):
            broker.create_order(OrderRequest(symbol="BTC/USDT", side=OrderSide.sell, quantity=1))


class TestRiskGuard:
    def test_blocks_oversized_order(self):
        guard = RiskGuard(max_order_value=1_000.0)
        with pytest.raises(RiskError):
            guard.check(OrderRequest(symbol="BTC/USDT", side=OrderSide.buy, quantity=20), fill_price=100.0)

    def test_blocks_oversized_position(self):
        guard = RiskGuard(max_order_value=10_000.0, max_position_value=1_500.0)
        with pytest.raises(RiskError):
            guard.check(
                OrderRequest(symbol="BTC/USDT", side=OrderSide.buy, quantity=10),
                fill_price=100.0,
                current_position_qty=10,
            )

    def test_allows_within_limits(self):
        guard = RiskGuard(max_order_value=10_000.0, max_position_value=10_000.0)
        guard.check(OrderRequest(symbol="BTC/USDT", side=OrderSide.buy, quantity=5), fill_price=100.0)


class TestPortfolio:
    def test_equity_and_unrealized_pnl(self):
        broker = make_paper(cash=10_000.0, price=100.0)
        broker.create_order(OrderRequest(symbol="BTC/USDT", side=OrderSide.buy, quantity=10))
        broker._data.set_price("BTC/USDT", 130.0)
        view = build_portfolio(broker)
        assert view.cash == pytest.approx(9_000.0)
        assert view.positions_value == pytest.approx(1_300.0)  # 10 * 130
        assert view.equity == pytest.approx(10_300.0)
        assert view.positions[0].unrealized_pnl == pytest.approx(300.0)
        assert view.positions[0].price_source == "live"
