"""On-demand AI signal endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.ai.signal_agent import generate_ai_signal
from app.brokers.registry import get_data_broker
from app.schemas import MarketKind, Signal

router = APIRouter(prefix="/api/ai", tags=["ai"])


class AISignalRequest(BaseModel):
    symbol: str
    market: MarketKind = MarketKind.crypto
    timeframe: str = "1h"
    limit: int = 100
    model: str | None = None


@router.post("/signal", response_model=Signal)
def ai_signal(req: AISignalRequest) -> Signal:
    try:
        candles = get_data_broker(req.market).get_ohlcv(req.symbol, req.timeframe, req.limit)
        return generate_ai_signal(req.symbol, candles, model=req.model)
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    except RuntimeError as exc:
        # missing API key, parse failure, or upstream data error
        raise HTTPException(status_code=502, detail=str(exc))
