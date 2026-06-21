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
    sim.rebalance({"BTC/USDT": 500.0}, prices, ts="t0")  # target 500 BTC @ $100 = $50k deployed
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


def test_costs_applied_on_buy_and_sell():
    """Round-trip buy→sell at the same price must lose money equal to both fees."""
    cost_model = CostModel(crypto_taker_bps=10.0)
    sim = PortfolioSim(starting_cash=100_000.0, market=MarketKind.crypto, cost_model=cost_model)
    price = 100.0
    qty = 500.0  # notional = 50,000
    # Expected fee per leg: notional * 10bps = 50,000 * 0.001 = 50.0
    expected_fee_per_leg = qty * price * (10.0 / 10_000)
    expected_total_fee = 2 * expected_fee_per_leg

    sim.rebalance({"BTC/USDT": qty}, {"BTC/USDT": price}, ts="t0")
    sim.rebalance({"BTC/USDT": 0.0}, {"BTC/USDT": price}, ts="t1")

    assert len(sim.trades) == 1
    trade = sim.trades[0]
    # pnl must be negative (fees consumed capital)
    assert trade.pnl < 0
    # total cost must equal buy fee + sell fee within floating-point tolerance
    assert abs(trade.cost - expected_total_fee) < 1e-6


def test_buy_scaled_to_available_cash():
    """Rebalance must never let cash go negative when target notional exceeds available cash."""
    cost_model = CostModel.zero()
    starting_cash = 1_000.0
    price = 100.0
    # Request 500 units @ $100 = $50,000 — far exceeds $1,000 starting cash
    sim = PortfolioSim(starting_cash=starting_cash, market=MarketKind.crypto, cost_model=cost_model)
    sim.rebalance({"BTC/USDT": 500.0}, {"BTC/USDT": price}, ts="t0")

    acquired_qty = sim.positions["BTC/USDT"].quantity
    # Must have bought something but strictly less than the requested 500 units
    assert acquired_qty > 0.0
    assert acquired_qty < 500.0
    # Cash must never go negative
    assert sim.cash >= -1e-9

def test_buy_with_dust_negative_cash_does_not_raise():
    """Regression: a prior exact-fit buy can leave cash at tiny float-negative dust
    (e.g. -7e-15). The next buy must be a safe no-op, not crash via fill_cost(qty<0)."""
    sim = _sim()
    sim.cash = -7.105427357601002e-15  # observed float dust from an exact cash-cap buy
    sim.rebalance({"BTC/USDT": 1.0}, {"BTC/USDT": 50.0}, ts="t")
    # no spendable cash -> nothing bought, and crucially: no ValueError raised
    assert "BTC/USDT" not in sim.positions or sim.positions["BTC/USDT"].quantity == 0.0


def test_equal_weight_two_long_churn_over_bars_never_raises():
    """Two symbols both long, rebalanced every bar with moving prices — the equal-weight
    churn path. After full deployment cash sits at ~0, and continued rebalancing must not
    drive a buy with non-positive cash into fill_cost. Completes cleanly; cash never negative."""
    sim = _sim()
    longs = {"BTC/USDT", "ETH/USDT"}
    btc, eth = 100.0, 50.0
    for i in range(20):
        # oscillate prices so targets shift each bar and the cap fires repeatedly
        btc *= 1.03 if i % 2 == 0 else 0.97
        eth *= 0.98 if i % 2 == 0 else 1.04
        prices = {"BTC/USDT": btc, "ETH/USDT": eth}
        targets = sim.target_quantities(longs, prices)
        sim.rebalance(targets, prices, ts=f"t{i}")  # must not raise
        assert sim.cash >= -1e-6, f"cash went negative at bar {i}: {sim.cash}"
