"""Transaction-cost model (M0.1).

Every simulated fill — in the paper broker (``brokers/paper.py``) and the backtester
(``backtest/engine.py``) — must pass through this model. Zero-cost return numbers are dishonest
(they overstate performance and bias the optimizer towards high-churn strategies), so a configured
``CostModel`` is applied by default; ``CostModel.zero()`` exists only for explicit gross-vs-net
comparisons in tests.

Conventions:
- Fees and taxes are returned as **cash amounts** in the instrument's quote currency.
- 台股 證交稅 (transaction tax) applies on the **sell** side only.
- Slippage is applied to the **fill price** (buys fill higher, sells fill lower), not as a fee.

Parameters are configurable via ``Settings`` (see ``.env.example``).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas import MarketKind, OrderSide


@dataclass(frozen=True)
class FillCost:
    """Per-fill cost breakdown in the instrument's quote currency."""

    fee: float = 0.0  # broker commission (both sides)
    tax: float = 0.0  # transaction tax (台股 證交稅 — sell only)

    @property
    def total(self) -> float:
        return self.fee + self.tax


@dataclass(frozen=True)
class CostModel:
    """Market-aware transaction costs.

    crypto:   taker/maker commission in basis points (default taker 7.5 bps).
    tw_stock: 手續費 0.1425% × 買賣各一次 × 券商折讓係數;證交稅 0.3% 僅賣出。
    us_stock: rate + minimum charge (複委託).
    common:   fixed-bps slippage (interface leaves room for a spread/volume model later).
    """

    crypto_taker_bps: float = 7.5
    crypto_maker_bps: float = 7.5
    tw_fee_rate: float = 0.001425
    tw_fee_discount: float = 1.0
    tw_tax_rate: float = 0.003
    us_fee_rate: float = 0.0
    us_fee_min: float = 0.0
    slippage_bps: float = 0.0

    @classmethod
    def from_settings(cls, s=None) -> "CostModel":
        """Build the configured cost model from ``Settings`` (the production default)."""
        if s is None:
            from app.config import settings as s
        return cls(
            crypto_taker_bps=s.cost_crypto_taker_bps,
            crypto_maker_bps=s.cost_crypto_maker_bps,
            tw_fee_rate=s.cost_tw_fee_rate,
            tw_fee_discount=s.cost_tw_fee_discount,
            tw_tax_rate=s.cost_tw_tax_rate,
            us_fee_rate=s.cost_us_fee_rate,
            us_fee_min=s.cost_us_fee_min,
            slippage_bps=s.cost_slippage_bps,
        )

    @classmethod
    def zero(cls) -> "CostModel":
        """A frictionless model — for measuring gross vs net only, never production."""
        return cls(
            crypto_taker_bps=0.0,
            crypto_maker_bps=0.0,
            tw_fee_rate=0.0,
            tw_tax_rate=0.0,
            us_fee_rate=0.0,
            us_fee_min=0.0,
            slippage_bps=0.0,
        )

    def slippage_price(self, side: OrderSide, price: float) -> float:
        """Adverse fill price after slippage (buy fills higher, sell fills lower)."""
        adj = self.slippage_bps / 10_000.0
        return price * (1.0 + adj) if side == OrderSide.buy else price * (1.0 - adj)

    def fill_cost(
        self,
        market: MarketKind,
        side: OrderSide,
        price: float,
        quantity: float,
        *,
        liquidity: str = "taker",
    ) -> FillCost:
        if price < 0 or quantity < 0:
            raise ValueError("price and quantity must be non-negative")
        notional = price * quantity
        if market == MarketKind.crypto:
            bps = self.crypto_maker_bps if liquidity == "maker" else self.crypto_taker_bps
            return FillCost(fee=notional * bps / 10_000.0, tax=0.0)
        if market == MarketKind.tw_stock:
            fee = notional * self.tw_fee_rate * self.tw_fee_discount
            tax = notional * self.tw_tax_rate if side == OrderSide.sell else 0.0
            return FillCost(fee=fee, tax=tax)
        if market == MarketKind.us_stock:
            fee = max(notional * self.us_fee_rate, self.us_fee_min) if notional > 0 else 0.0
            return FillCost(fee=fee, tax=0.0)
        raise ValueError(f"unknown market for cost model: {market!r}")
