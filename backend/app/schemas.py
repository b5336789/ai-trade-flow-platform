"""Shared domain types used across brokers, strategies, AI agents and the API.

Centralising these enums/models is deliberate (CLAUDE.md: avoid premature abstraction but
maximise reuse): a strategy node and an AI node both emit the same ``Signal``, and every broker
(paper or live, crypto or stock) speaks the same ``OrderRequest`` / ``OrderResult`` language.
"""

from __future__ import annotations

import enum
from datetime import datetime

from pydantic import BaseModel, Field


class MarketKind(str, enum.Enum):
    crypto = "crypto"
    tw_stock = "tw_stock"  # 台股 — 元大證券 (planned)
    us_stock = "us_stock"  # 美股 — 元大複委託 / Firstrade (planned)


class TradingMode(str, enum.Enum):
    paper = "paper"
    live = "live"


class OrderSide(str, enum.Enum):
    buy = "buy"
    sell = "sell"


class OrderType(str, enum.Enum):
    market = "market"
    limit = "limit"


class SignalAction(str, enum.Enum):
    buy = "buy"
    sell = "sell"
    hold = "hold"


class Candle(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class Ticker(BaseModel):
    symbol: str
    price: float
    timestamp: datetime


class Signal(BaseModel):
    """Output of a strategy or an AI signal node. Indicator and LLM nodes are interchangeable."""

    action: SignalAction
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    reason: str = ""
    source: str = ""  # which strategy / agent produced it


class OrderRequest(BaseModel):
    symbol: str
    side: OrderSide
    quantity: float = Field(gt=0)
    type: OrderType = OrderType.market
    limit_price: float | None = None


class OrderResult(BaseModel):
    id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float  # fill price (market) or limit price
    status: str  # "filled" | "open" | "rejected"
    mode: TradingMode
    broker: str
    timestamp: datetime
    info: dict = Field(default_factory=dict)


class Balance(BaseModel):
    asset: str
    free: float
    total: float


class Position(BaseModel):
    symbol: str
    quantity: float
    avg_price: float
