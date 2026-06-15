"""RSI mean-reversion strategy: buy when oversold, sell when overbought."""

from __future__ import annotations

from app.schemas import Candle, Signal, SignalAction
from app.strategies.base import Strategy
from app.strategies.indicators import candles_to_df, rsi


class RsiStrategy(Strategy):
    name = "rsi"

    def __init__(self, window: int = 14, oversold: float = 30.0, overbought: float = 70.0) -> None:
        if not 0 < oversold < overbought < 100:
            raise ValueError("require 0 < oversold < overbought < 100")
        self.window = window
        self.oversold = oversold
        self.overbought = overbought

    def generate(self, candles: list[Candle]) -> Signal:
        df = candles_to_df(candles)
        if len(df) < self.window + 1:
            raise ValueError(f"rsi needs at least {self.window + 1} candles, got {len(df)}")
        value = float(rsi(df["close"], self.window).iloc[-1])

        if value <= self.oversold:
            return Signal(
                action=SignalAction.buy,
                confidence=min(1.0, (self.oversold - value) / self.oversold + 0.5),
                reason=f"RSI({self.window})={value:.1f} <= {self.oversold} (oversold)",
                source=self.name,
            )
        if value >= self.overbought:
            return Signal(
                action=SignalAction.sell,
                confidence=min(1.0, (value - self.overbought) / (100 - self.overbought) + 0.5),
                reason=f"RSI({self.window})={value:.1f} >= {self.overbought} (overbought)",
                source=self.name,
            )
        return Signal(
            action=SignalAction.hold,
            confidence=0.5,
            reason=f"RSI({self.window})={value:.1f} in neutral band",
            source=self.name,
        )
