"""Broker selection by market + trading mode.

- crypto: ccxt (live) / PaperBroker over ccxt (paper)
- 台股 / 美股: live = 元大 / Firstrade scaffolds (fail loud until wired); paper/backtest = CsvDataBroker
  over user-imported history (offline). Paper brokers are cached per-market so simulated state
  persists across requests.
"""

from __future__ import annotations

from app.brokers import market_data
from app.brokers.base import Broker
from app.brokers.crypto_ccxt import CcxtBroker
from app.brokers.csv_data import CsvDataBroker
from app.brokers.firstrade import FirstradeBroker
from app.brokers.paper import PaperBroker
from app.brokers.yuanta import YuantaBroker
from app.config import settings
from app.schemas import MarketKind, TradingMode
from app.trading.paper_store import PaperStore

_paper_cache: dict[MarketKind, PaperBroker] = {}

_STOCK_MARKETS = {MarketKind.tw_stock, MarketKind.us_stock}


def get_data_broker(market: MarketKind) -> Broker:
    """A broker usable for market data (and live trading where supported)."""
    if market == MarketKind.crypto:
        return CcxtBroker()
    if market in _STOCK_MARKETS:
        if market_data.has_market_data(market):
            return CsvDataBroker(market)
        raise NotImplementedError(
            f"'{market.value}': live brokers (台股 元大 / 美股 元大複委託・Firstrade) are not "
            "implemented yet. Import CSV history via POST /api/markets/import to "
            "paper-trade/backtest offline."
        )
    raise NotImplementedError(f"market '{market.value}' is not supported")


def get_live_broker(market: MarketKind) -> Broker:
    if market == MarketKind.crypto:
        return CcxtBroker()
    if market == MarketKind.tw_stock:
        return YuantaBroker(MarketKind.tw_stock)
    if market == MarketKind.us_stock:
        # 美股: default to Firstrade scaffold; 元大複委託 available via YuantaBroker(us_stock).
        return FirstradeBroker()
    raise NotImplementedError(f"market '{market.value}' is not supported")


def get_broker(market: MarketKind, mode: TradingMode | None = None) -> Broker:
    """The execution broker for the given market + mode (defaults to settings.trading_mode)."""
    mode = mode or settings.trading_mode
    if mode == TradingMode.paper:
        if market not in _paper_cache:
            _paper_cache[market] = PaperBroker(
                data_provider=get_data_broker(market), store=PaperStore(market)
            )
        return _paper_cache[market]
    return get_live_broker(market)


def reset_paper_brokers() -> None:
    """Clear cached paper brokers (used by tests; does not touch persisted state)."""
    _paper_cache.clear()


def reset_paper_account(market: MarketKind) -> None:
    """Wipe persisted paper state for a market and drop its cached broker."""
    PaperStore(market).reset()
    _paper_cache.pop(market, None)
