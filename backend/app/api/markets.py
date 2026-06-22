"""Market-data endpoints (ticker + OHLCV candlesticks)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.brokers import market_data
from app.brokers.registry import get_data_broker
from app.schemas import Candle, MarketKind, Ticker

router = APIRouter(prefix="/api/markets", tags=["markets"])


class ImportRequest(BaseModel):
    market: MarketKind
    symbol: str
    csv: str  # OHLCV CSV: header timestamp,open,high,low,close[,volume]


@router.post("/import")
def import_history(req: ImportRequest) -> dict:
    """Import OHLCV CSV for a symbol so 台股/美股 can be paper-traded & backtested offline."""
    try:
        candles = market_data.parse_csv(req.csv)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    market_data.set_candles(req.market, req.symbol, candles)
    return {"market": req.market.value, "symbol": req.symbol, "imported": len(candles)}


@router.get("/imported")
def list_imported(market: MarketKind) -> dict:
    return {"market": market.value, "symbols": market_data.list_symbols(market)}


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
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
) -> list[Candle]:
    try:
        broker = get_data_broker(market)
        if start is not None and end is not None:
            if start >= end:
                raise ValueError("start must be before end")
            return broker.get_ohlcv_range(symbol, timeframe, start, end)
        return broker.get_ohlcv(symbol, timeframe, limit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"{type(exc).__name__}: {exc}")
