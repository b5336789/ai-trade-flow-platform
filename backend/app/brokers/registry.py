"""Broker selection by market + trading mode.

Paper brokers are cached per-market so simulated cash/positions persist across requests within
the process. Live stock brokers (元大 / Firstrade) are not implemented yet and fail loudly.
"""

from __future__ import annotations

from app.brokers.base import Broker
from app.brokers.crypto_ccxt import CcxtBroker
from app.brokers.paper import PaperBroker
from app.config import settings
from app.schemas import MarketKind, TradingMode

_paper_cache: dict[MarketKind, PaperBroker] = {}


def get_data_broker(market: MarketKind) -> Broker:
    """A broker usable for market data (and live trading where supported)."""
    if market == MarketKind.crypto:
        return CcxtBroker()
    raise NotImplementedError(
        f"Market '{market.value}' not implemented yet. "
        "Planned: 台股 元大證券, 美股 元大複委託 / Firstrade."
    )


def get_broker(market: MarketKind, mode: TradingMode | None = None) -> Broker:
    """The execution broker for the given market + mode (defaults to settings.trading_mode)."""
    mode = mode or settings.trading_mode
    if mode == TradingMode.paper:
        if market not in _paper_cache:
            _paper_cache[market] = PaperBroker(data_provider=get_data_broker(market))
        return _paper_cache[market]
    return get_data_broker(market)


def reset_paper_brokers() -> None:
    """Clear cached paper state (used by tests)."""
    _paper_cache.clear()
