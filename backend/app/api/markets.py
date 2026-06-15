"""Market-data endpoints (ticker + OHLCV candlesticks)."""

from __future__ import annotations

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
) -> list[Candle]:
    try:
        return get_data_broker(market).get_ohlcv(symbol, timeframe, limit)
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"{type(exc).__name__}: {exc}")
