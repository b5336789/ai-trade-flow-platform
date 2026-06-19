"""M0.1 — transaction cost model: fees, sell-side tax, slippage; applied in paper + backtest.

These are business-logic tests: a buy→sell round trip must net out to
``gross_pnl − buy_cost − sell_cost − sell_tax``, and turning costs on must strictly reduce a
high-churn strategy's net return below its gross return.
"""

from __future__ import annotations

import pytest

from app.backtest.engine import run_backtest
from app.brokers.paper import PaperBroker
from app.schemas import MarketKind, OrderRequest, OrderSide
from app.strategies.ma_cross import MaCrossStrategy
from app.tests.helpers import StubBroker, make_candles
from app.trading.costs import CostModel


# --- cost model maths -------------------------------------------------------
def test_crypto_taker_fee_bps():
    cm = CostModel(crypto_taker_bps=7.5)
    cost = cm.fill_cost(MarketKind.crypto, OrderSide.buy, price=100.0, quantity=10.0)
    assert cost.fee == pytest.approx(0.75)  # 1000 notional * 7.5 bps
    assert cost.tax == 0.0
    assert cost.total == pytest.approx(0.75)


def test_tw_stock_fee_both_sides_and_sell_only_tax():
    cm = CostModel(tw_fee_rate=0.001425, tw_fee_discount=1.0, tw_tax_rate=0.003)
    notional = 100.0 * 10
    buy = cm.fill_cost(MarketKind.tw_stock, OrderSide.buy, 100.0, 10.0)
    sell = cm.fill_cost(MarketKind.tw_stock, OrderSide.sell, 100.0, 10.0)
    assert buy.fee == pytest.approx(notional * 0.001425)
    assert buy.tax == 0.0  # 證交稅 not charged on buy
    assert sell.fee == pytest.approx(notional * 0.001425)
    assert sell.tax == pytest.approx(notional * 0.003)


def test_tw_fee_discount_applies():
    cm = CostModel(tw_fee_rate=0.001425, tw_fee_discount=0.6)
    buy = cm.fill_cost(MarketKind.tw_stock, OrderSide.buy, 100.0, 10.0)
    assert buy.fee == pytest.approx(1000 * 0.001425 * 0.6)


def test_us_stock_minimum_charge():
    cm = CostModel(us_fee_rate=0.0005, us_fee_min=1.0)
    small = cm.fill_cost(MarketKind.us_stock, OrderSide.buy, 10.0, 10.0)  # 0.05 < 1.0
    assert small.fee == pytest.approx(1.0)
    big = cm.fill_cost(MarketKind.us_stock, OrderSide.buy, 1000.0, 100.0)  # 50.0 > 1.0
    assert big.fee == pytest.approx(100_000 * 0.0005)


def test_slippage_moves_price_against_the_taker():
    cm = CostModel(slippage_bps=10.0)
    assert cm.slippage_price(OrderSide.buy, 100.0) == pytest.approx(100.0 * 1.001)
    assert cm.slippage_price(OrderSide.sell, 100.0) == pytest.approx(100.0 * 0.999)


def test_from_settings_reads_overrides(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "cost_crypto_taker_bps", 20.0)
    cm = CostModel.from_settings()
    assert cm.crypto_taker_bps == 20.0


def test_unknown_market_fails_loud():
    cm = CostModel()
    with pytest.raises(ValueError):
        cm.fill_cost("forex", OrderSide.buy, 1.0, 1.0)  # type: ignore[arg-type]


# --- applied in the paper broker -------------------------------------------
def test_paper_buy_deducts_fee_from_cash():
    cm = CostModel(crypto_taker_bps=7.5)
    broker = PaperBroker(StubBroker({"BTC/USDT": 100.0}), starting_cash=10_000.0, cost_model=cm)
    broker.create_order(OrderRequest(symbol="BTC/USDT", side=OrderSide.buy, quantity=10))
    assert broker.cash == pytest.approx(10_000.0 - 1000.0 - 0.75)


def test_paper_round_trip_realized_net_identity():
    cm = CostModel(crypto_taker_bps=7.5)
    broker = PaperBroker(StubBroker({"BTC/USDT": 100.0}), starting_cash=10_000.0, cost_model=cm)
    broker.create_order(OrderRequest(symbol="BTC/USDT", side=OrderSide.buy, quantity=10))
    broker._data.set_price("BTC/USDT", 120.0)
    broker.create_order(OrderRequest(symbol="BTC/USDT", side=OrderSide.sell, quantity=10))

    gross_pnl = (120.0 - 100.0) * 10
    buy_cost = cm.fill_cost(MarketKind.crypto, OrderSide.buy, 100.0, 10).total
    sell = cm.fill_cost(MarketKind.crypto, OrderSide.sell, 120.0, 10)
    realized_net = broker.cash - 10_000.0
    assert realized_net == pytest.approx(gross_pnl - buy_cost - sell.fee - sell.tax)


# --- applied in the backtester ---------------------------------------------
def test_backtest_trade_net_identity():
    """Each Trade exposes gross_pnl and cost; pnl == gross_pnl − cost, with cost matching the model.

    Asserted via the recorded entry/exit prices so it stays valid regardless of fill timing (M0.2).
    """
    prices = [10, 10, 10, 10, 12, 16, 20, 20, 20, 20, 20, 20, 18, 14, 10]
    cm = CostModel(crypto_taker_bps=10.0)
    result = run_backtest(
        make_candles(prices),
        MaCrossStrategy(fast=2, slow=4),
        starting_cash=10_000.0,
        market=MarketKind.crypto,
        cost_model=cm,
    )
    assert result.num_trades >= 1
    t = result.trades[0]
    expected_buy = cm.fill_cost(MarketKind.crypto, OrderSide.buy, t.entry_price, t.quantity).total
    expected_sell = cm.fill_cost(MarketKind.crypto, OrderSide.sell, t.exit_price, t.quantity).total
    assert t.cost == pytest.approx(expected_buy + expected_sell)
    assert t.gross_pnl == pytest.approx((t.exit_price - t.entry_price) * t.quantity)
    assert t.pnl == pytest.approx(t.gross_pnl - t.cost)


def test_costs_reduce_net_return_below_gross():
    prices = [10, 10, 10, 10, 12, 16, 20, 20, 18, 14, 10, 12, 16, 20, 20, 18, 14, 10]
    base = dict(starting_cash=10_000.0, market=MarketKind.crypto)
    gross = run_backtest(make_candles(prices), MaCrossStrategy(fast=2, slow=4), cost_model=CostModel.zero(), **base)
    net = run_backtest(make_candles(prices), MaCrossStrategy(fast=2, slow=4), cost_model=CostModel(crypto_taker_bps=50.0), **base)
    assert net.num_trades >= 2
    assert net.total_return_pct < gross.total_return_pct
