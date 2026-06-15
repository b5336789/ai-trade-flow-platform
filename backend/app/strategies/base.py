"""Strategy abstraction. A strategy turns OHLCV history into a single ``Signal``.

AI signal agents emit the same ``Signal`` type, so the workflow engine treats indicator
strategies and LLM agents interchangeably.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas import Candle, Signal


class Strategy(ABC):
    name: str

    @abstractmethod
    def generate(self, candles: list[Candle]) -> Signal:
        """Produce a buy/sell/hold signal from candle history. Fail loud on insufficient data."""
