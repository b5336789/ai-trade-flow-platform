"""FX conversion seam.

Converts an amount in some quote currency to the configured BASE CURRENCY (TWD) using
either config-driven static rates or a live FX provider. All portfolio-level risk is judged in the
base currency, so this is the single place that knows how to convert per-market quote currencies
(crypto -> USDT, 台股 -> TWD, 美股 -> USD) into a common unit.

This is deliberately a thin interface: live rates sit behind the same ``FxConverter.to_base``
shape, so risk code does not need to know whether rates are static or provider-backed. FAIL LOUD
on a missing or stale provider rate (CLAUDE.md) — silently treating an unknown currency as 1:1
would corrupt every risk number downstream.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any, Callable, Protocol

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


class FxRateProviderError(RuntimeError):
    """Raised when a live FX provider cannot return a usable rate snapshot."""


@dataclass(frozen=True)
class FxRateSnapshot:
    """Rates expressed as one unit of currency -> base currency value."""

    rates: dict[str, float]


class FxRateProvider(Protocol):
    """Provider boundary for live FX rates."""

    def latest_rates(self, *, base_currency: str, currencies: set[str]) -> FxRateSnapshot:
        """Return rates for the requested currencies expressed in ``base_currency``."""


class OpenErApiFxProvider:
    """Open ExchangeRate-API provider.

    Uses the no-key open endpoint documented at https://open.er-api.com/v6/latest/USD. The open
    endpoint updates daily and is rate limited, so the converter keeps a TTL cache in front of it.
    USDT is treated as a USD-pegged quote currency when the upstream table does not list it.
    """

    def __init__(
        self,
        *,
        base_url: str = "https://open.er-api.com/v6/latest",
        client: Any | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        if client is None:
            import httpx

            client = httpx.Client(timeout=timeout)
        self._client = client

    def latest_rates(self, *, base_currency: str, currencies: set[str]) -> FxRateSnapshot:
        url = f"{self.base_url}/USD"
        try:
            response = self._client.get(url)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise FxRateProviderError(f"open_er_api FX request failed: {exc}") from exc

        if payload.get("result") not in (None, "success"):
            raise FxRateProviderError(
                f"open_er_api FX response was not successful: {payload.get('error-type', payload)}"
            )

        table = payload.get("rates") or payload.get("conversion_rates")
        if not isinstance(table, dict):
            raise FxRateProviderError("open_er_api FX response missing rates")

        base = base_currency.upper()
        usd_to_base = _table_rate(table, base)
        if usd_to_base is None:
            raise FxRateProviderError(f"open_er_api FX response missing USD->{base} rate")

        rates = {base: 1.0}
        for currency in {ccy.upper() for ccy in currencies}:
            if currency == base:
                rates[currency] = 1.0
                continue

            usd_to_currency = _table_rate(table, currency)
            if usd_to_currency is None and currency == "USDT":
                usd_to_currency = 1.0
            if usd_to_currency is None:
                continue

            rates[currency] = usd_to_base / usd_to_currency

        return FxRateSnapshot(rates=rates)


def _table_rate(table: dict, currency: str) -> float | None:
    if currency == "USD":
        return 1.0
    value = table.get(currency)
    if value is None:
        return None
    return float(value)


@dataclass
class FxConverter:
    """Convert amounts to the base currency.

    ``rates`` maps a currency code to its value expressed in the base currency, e.g.
    ``{"TWD": 1.0, "USD": 31.5}`` means 1 USD = 31.5 TWD. The base currency MUST be present
    (and is normalised to 1.0). When ``provider`` is set, rates are refreshed through the provider
    and cached for ``cache_ttl_seconds``; expired provider rates fail loud unless an explicit static
    fallback was configured.
    """

    base_currency: str = "TWD"
    rates: dict[str, float] = field(default_factory=lambda: {"TWD": 1.0})
    provider: FxRateProvider | None = None
    live_currencies: set[str] = field(default_factory=set)
    cache_ttl_seconds: int = 3600
    static_fallback_rates: dict[str, float] | None = None
    time_fn: Callable[[], float] = time.monotonic
    _cache_loaded_at: float | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self.base_currency = self.base_currency.upper()
        self.rates = {ccy.upper(): float(rate) for ccy, rate in self.rates.items()}
        # The base currency is by definition 1:1 with itself.
        self.rates[self.base_currency] = 1.0
        self.live_currencies = {ccy.upper() for ccy in self.live_currencies}
        if self.static_fallback_rates is not None:
            self.static_fallback_rates = {
                ccy.upper(): float(rate) for ccy, rate in self.static_fallback_rates.items()
            }
            self.static_fallback_rates[self.base_currency] = 1.0

    def to_base(self, amount: float, currency: str) -> float:
        """Convert ``amount`` (denominated in ``currency``) to the base currency.

        Raises (fail loud) if no rate is configured for ``currency``.
        """
        currency = currency.upper()
        if currency == self.base_currency:
            return amount
        if self.provider is not None and (not self._cache_is_fresh() or currency not in self.rates):
            self._refresh_rates(currency)
        rate = self.rates.get(currency)
        if rate is None:
            raise ValueError(
                f"no FX rate for '{currency}' -> base '{self.base_currency}'; "
                f"configured rates: {sorted(self.rates)}"
            )
        return amount * rate

    def _cache_is_fresh(self) -> bool:
        return (
            self._cache_loaded_at is not None
            and self.time_fn() - self._cache_loaded_at <= self.cache_ttl_seconds
        )

    def _refresh_rates(self, requested_currency: str) -> None:
        if self.provider is None:  # pragma: no cover - guarded by caller
            return

        currencies = set(self.live_currencies)
        currencies.add(requested_currency.upper())
        currencies.discard(self.base_currency)
        try:
            snapshot = self.provider.latest_rates(
                base_currency=self.base_currency,
                currencies=set(currencies),
            )
        except Exception as exc:
            if self.static_fallback_rates is not None:
                self.rates = dict(self.static_fallback_rates)
                self._cache_loaded_at = self.time_fn()
                return
            raise FxRateProviderError(f"FX provider refresh failed: {exc}") from exc

        refreshed = {ccy.upper(): float(rate) for ccy, rate in snapshot.rates.items()}
        refreshed[self.base_currency] = 1.0
        missing = sorted(ccy for ccy in currencies if ccy not in refreshed)
        if missing:
            raise ValueError(
                f"missing FX rates for {missing} -> base '{self.base_currency}' from provider"
            )

        self.rates = refreshed
        self._cache_loaded_at = self.time_fn()

    @classmethod
    def from_settings(cls) -> "FxConverter":
        from app.config import settings

        provider_name = settings.fx_provider.lower()
        if provider_name == "static":
            return cls(base_currency=settings.base_currency, rates=dict(settings.fx_rates))
        if provider_name == "open_er_api":
            return cls(
                base_currency=settings.base_currency,
                rates={settings.base_currency: 1.0},
                provider=OpenErApiFxProvider(base_url=settings.fx_open_er_api_base_url),
                live_currencies=set(settings.fx_live_currencies),
                cache_ttl_seconds=settings.fx_rate_cache_ttl_seconds,
                static_fallback_rates=(
                    dict(settings.fx_rates) if settings.fx_static_fallback_enabled else None
                ),
            )
        raise ValueError(f"unsupported FX_PROVIDER '{settings.fx_provider}'")
