"""Shared-cash multi-asset portfolio simulation with equal-weight targets (M-backtest).

One cash pool, long/flat only. Equal-weight: every symbol currently desired-long targets an equal
fraction (1/N) of current portfolio equity; rebalancing trades the delta to each target through the
CostModel. Mirrors the single-asset engine's cost handling so net numbers stay honest.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.backtest.engine import Trade
from app.schemas import MarketKind, OrderSide
from app.trading.costs import CostModel

_QTY_EPS = 1e-9


@dataclass
class _Pos:
    quantity: float = 0.0
    avg_price: float = 0.0
    entry_time: str = ""
    entry_fee: float = 0.0


@dataclass
class PortfolioSim:
    starting_cash: float
    market: MarketKind
    cost_model: CostModel
    cash: float = field(init=False)
    positions: dict[str, _Pos] = field(default_factory=dict)
    trades: list[Trade] = field(default_factory=list)
    traded_value: float = 0.0

    def __post_init__(self) -> None:
        self.cash = self.starting_cash

    def equity(self, prices: dict[str, float]) -> float:
        held = 0.0
        for sym, p in self.positions.items():
            if p.quantity > _QTY_EPS:
                if sym not in prices:
                    raise ValueError(f"equity() missing price for held symbol {sym!r}")
                held += p.quantity * prices[sym]
        return self.cash + held

    def target_quantities(self, desired_long: set[str], prices: dict[str, float]) -> dict[str, float]:
        equity = self.equity(prices)
        longs = [s for s in desired_long if prices.get(s, 0.0) > 0]
        n = len(longs)
        targets: dict[str, float] = {sym: 0.0 for sym in set(prices) | desired_long}
        if n == 0:
            return targets
        per = equity / n
        for sym in longs:
            targets[sym] = per / prices[sym]
        return targets

    def rebalance(self, targets: dict[str, float], prices: dict[str, float], ts: str) -> None:
        # Sells first (free up cash), then buys, so capital recycles within the bar.
        for sym, target in sorted(targets.items(), key=lambda kv: kv[1]):
            price = prices.get(sym)
            if price is None or price <= 0:
                continue
            pos = self.positions.setdefault(sym, _Pos())
            delta = target - pos.quantity
            if abs(delta) <= _QTY_EPS:
                continue
            if delta > 0:
                self._buy(sym, pos, delta, price, ts)
            else:
                self._sell(sym, pos, -delta, price, ts)

    def _buy(self, sym: str, pos: _Pos, qty: float, price: float, ts: str) -> None:
        # No spendable cash -> can't buy. This also guards the float-dust case where a prior
        # exact cash-cap buy left cash at a tiny negative (~-7e-15): without it, the scale below
        # would go negative and feed a negative quantity into fill_cost (which rejects it).
        if self.cash <= 0:
            return
        fill = self.cost_model.slippage_price(OrderSide.buy, price)
        fee = self.cost_model.fill_cost(self.market, OrderSide.buy, fill, qty).total
        outlay = qty * fill + fee
        if outlay > self.cash:  # never let cash go negative; scale the buy to fit
            scale = self.cash / outlay  # cash > 0 and outlay > 0 here, so scale is in (0, 1)
            qty *= scale
            if qty <= _QTY_EPS:  # scaled below the dust threshold -> skip before costing it
                return
            fee = self.cost_model.fill_cost(self.market, OrderSide.buy, fill, qty).total
            outlay = qty * fill + fee
        if qty <= _QTY_EPS:
            return
        # weighted-average cost basis across the combined position
        new_qty = pos.quantity + qty
        pos.avg_price = (pos.avg_price * pos.quantity + fill * qty) / new_qty if new_qty > 0 else 0.0
        if pos.quantity <= _QTY_EPS:
            pos.entry_time = ts
            pos.entry_fee = fee
        else:
            pos.entry_fee += fee
        pos.quantity = new_qty
        self.cash -= outlay
        self.traded_value += qty * fill

    def _sell(self, sym: str, pos: _Pos, qty: float, price: float, ts: str) -> None:
        qty = min(qty, pos.quantity)
        if qty <= _QTY_EPS:
            return
        fill = self.cost_model.slippage_price(OrderSide.sell, price)
        sell_cost = self.cost_model.fill_cost(self.market, OrderSide.sell, fill, qty).total
        self.cash += qty * fill - sell_cost
        self.traded_value += qty * fill
        gross = (fill - pos.avg_price) * qty
        # apportion the entry fee by the fraction of the position being closed
        frac = qty / pos.quantity if pos.quantity > 0 else 1.0
        entry_fee_share = pos.entry_fee * frac
        self.trades.append(
            Trade(
                entry_time=pos.entry_time,
                exit_time=ts,
                entry_price=pos.avg_price,
                exit_price=fill,
                quantity=qty,
                pnl=gross - entry_fee_share - sell_cost,
                gross_pnl=gross,
                cost=entry_fee_share + sell_cost,
                return_pct=(fill / pos.avg_price - 1) * 100 if pos.avg_price else 0.0,
            )
        )
        pos.quantity -= qty
        pos.entry_fee -= entry_fee_share
        if pos.quantity <= _QTY_EPS:
            pos.quantity = 0.0
            pos.avg_price = 0.0
            pos.entry_fee = 0.0
