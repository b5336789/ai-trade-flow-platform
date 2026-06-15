"""Bollinger Bands mean-reversion: buy below the lower band, sell above the upper band."""

from __future__ import annotations

import pandas as pd

from app.schemas import Candle, Signal, SignalAction
from app.strategies.base import Strategy
from app.strategies.indicators import bollinger, candles_to_df


class BollingerStrategy(Strategy):
    name = "bollinger"

    def __init__(self, window: int = 20, window_dev: float = 2.0) -> None:
        if window < 2:
            raise ValueError("window must be >= 2")
        self.window = window
        self.window_dev = window_dev

    def generate(self, candles: list[Candle]) -> Signal:
        df = candles_to_df(candles)
        if len(df) < self.window + 1:
            raise ValueError(f"bollinger needs at least {self.window + 1} candles, got {len(df)}")
        upper, _, lower = bollinger(df["close"], self.window, self.window_dev)
        price = float(df["close"].iloc[-1])
        u, l = upper.iloc[-1], lower.iloc[-1]
        if pd.isna(u) or pd.isna(l):
            raise ValueError("bollinger bands not yet defined")

        if price < l:
            return Signal(
                action=SignalAction.buy,
                confidence=0.6,
                reason=f"price {price:.4f} below lower band {l:.4f}",
                source=self.name,
            )
        if price > u:
            return Signal(
                action=SignalAction.sell,
                confidence=0.6,
                reason=f"price {price:.4f} above upper band {u:.4f}",
                source=self.name,
            )
        return Signal(
            action=SignalAction.hold,
            confidence=0.5,
            reason=f"price {price:.4f} within bands [{l:.4f}, {u:.4f}]",
            source=self.name,
        )
