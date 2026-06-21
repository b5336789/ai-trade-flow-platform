from __future__ import annotations

from app.backtest.portfolio import PortfolioSim
from app.schemas import MarketKind
from app.trading.costs import CostModel


def _sim() -> PortfolioSim:
    return PortfolioSim(starting_cash=100_000.0, market=MarketKind.crypto, cost_model=CostModel.zero())


def test_equal_weight_two_symbols_split_5050():
    sim = _sim()
    prices = {"BTC/USDT": 100.0, "ETH/USDT": 50.0}
    targets = sim.target_quantities({"BTC/USDT", "ETH/USDT"}, prices)
    # 100k / 2 = 50k each -> 500 BTC, 1000 ETH
    assert round(targets["BTC/USDT"], 6) == 500.0
    assert round(targets["ETH/USDT"], 6) == 1000.0


def test_rebalance_buys_then_exit_to_cash():
    sim = _sim()
    prices = {"BTC/USDT": 100.0}
    sim.rebalance({"BTC/USDT": 500.0}, prices, ts="t0")  # deploy 50k? no — single symbol target=500
    assert round(sim.positions["BTC/USDT"].quantity, 6) == 500.0
    assert round(sim.equity(prices), 2) == 100_000.0  # zero-cost: equity unchanged
    sim.rebalance({"BTC/USDT": 0.0}, {"BTC/USDT": 120.0}, ts="t1")  # exit at higher price
    assert sim.positions["BTC/USDT"].quantity == 0.0
    assert len(sim.trades) == 1
    assert round(sim.trades[0].pnl, 2) == round((120.0 - 100.0) * 500.0, 2)


def test_single_active_long_targets_full_equity():
    sim = _sim()
    prices = {"BTC/USDT": 100.0, "ETH/USDT": 50.0}
    targets = sim.target_quantities({"BTC/USDT"}, prices)  # only BTC long -> 100% to BTC
    assert round(targets["BTC/USDT"], 6) == 1000.0
    assert targets["ETH/USDT"] == 0.0
