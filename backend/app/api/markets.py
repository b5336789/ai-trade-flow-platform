"""Market-data endpoints (ticker + OHLCV candlesticks)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.brokers.registry import get_data_broker
from app.schemas import Candle, MarketKind, Ticker

router = APIRouter(prefix="/api/markets", tags=["markets"])


@router.get("/ticker", response_model=Ticker)
def get_ticker(symbol: str, market: MarketKind = MarketKind.crypto) -> Ticker:
    try:
        return get_data_broker(market).get_ticker(symbol)
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    except Exception as exc:  # surface upstream/exchange errors loudly
        raise HTTPException(status_code=502, detail=f"{type(exc).__name__}: {exc}")


@router.get("/ohlcv", response_model=list[Candle])
def get_ohlcv(
    symbol: str,
    market: MarketKind = MarketKind.crypto,
    timeframe: str = "1h",
    limit: int = Query(100, ge=1, le=1000),
) -> list[Candle]:
    try:
        return get_data_broker(market).get_ohlcv(symbol, timeframe, limit)
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"{type(exc).__name__}: {exc}")
