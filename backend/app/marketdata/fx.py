"""Minimal FX seam (Phase-0).

Converts an amount in some quote currency to the configured BASE CURRENCY (TWD) using
config-driven STATIC rates. All portfolio-level risk in M0.6 is judged in the base currency, so
this is the single place that knows how to convert per-market quote currencies (crypto -> USDT,
台股 -> TWD, 美股 -> USD) into a common unit.

This is deliberately a thin interface: M1.1 will swap in a live FX provider behind the same
``FxConverter`` shape without touching the risk code. FAIL LOUD on a missing rate (CLAUDE.md) —
silently treating an unknown currency as 1:1 would corrupt every risk number downstream.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas import MarketKind

# Quote currency each market settles in (single-market brokers => one quote ccy per broker).
MARKET_QUOTE_CURRENCY: dict[MarketKind, str] = {
    MarketKind.crypto: "USDT",
    MarketKind.tw_stock: "TWD",
    MarketKind.us_stock: "USD",
}


def quote_currency_for(market: MarketKind) -> str:
    """The quote currency a market's prices/values are denominated in."""
    try:
        return MARKET_QUOTE_CURRENCY[market]
    except KeyError as exc:  # pragma: no cover - all MarketKind members are mapped
        raise KeyError(f"no quote currency configured for market '{market}'") from exc


@dataclass
class FxConverter:
    """Convert amounts to the base currency using static, config-driven rates.

    ``rates`` maps a currency code to its value expressed in the base currency, e.g.
    ``{"TWD": 1.0, "USD": 31.5}`` means 1 USD = 31.5 TWD. The base currency MUST be present
    (and is normalised to 1.0).
    """

    base_currency: str = "TWD"
    rates: dict[str, float] = field(default_factory=lambda: {"TWD": 1.0})

    def __post_init__(self) -> None:
        # The base currency is by definition 1:1 with itself.
        self.rates[self.base_currency] = 1.0

    def to_base(self, amount: float, currency: str) -> float:
        """Convert ``amount`` (denominated in ``currency``) to the base currency.

        Raises (fail loud) if no rate is configured for ``currency``.
        """
        if currency == self.base_currency:
            return amount
        rate = self.rates.get(currency)
        if rate is None:
            raise ValueError(
                f"no FX rate for '{currency}' -> base '{self.base_currency}'; "
                f"configured rates: {sorted(self.rates)}"
            )
        return amount * rate

    @classmethod
    def from_settings(cls) -> "FxConverter":
        from app.config import settings

        return cls(base_currency=settings.base_currency, rates=dict(settings.fx_rates))
