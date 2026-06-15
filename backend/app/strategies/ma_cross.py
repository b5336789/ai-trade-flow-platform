"""Moving-average crossover strategy.

Buy when the fast SMA crosses above the slow SMA; sell on the reverse cross; hold otherwise.
"""

from __future__ import annotations

from app.schemas import Candle, Signal, SignalAction
from app.strategies.base import Strategy
from app.strategies.indicators import candles_to_df, sma


class MaCrossStrategy(Strategy):
    name = "ma_cross"

    def __init__(self, fast: int = 10, slow: int = 20) -> None:
        if fast >= slow:
            raise ValueError(f"fast window ({fast}) must be < slow window ({slow})")
        self.fast = fast
        self.slow = slow

    def generate(self, candles: list[Candle]) -> Signal:
        df = candles_to_df(candles)
        if len(df) < self.slow + 1:
            raise ValueError(
                f"ma_cross needs at least {self.slow + 1} candles, got {len(df)}"
            )
        fast = sma(df["close"], self.fast)
        slow = sma(df["close"], self.slow)
        fast_prev, fast_now = fast.iloc[-2], fast.iloc[-1]
        slow_prev, slow_now = slow.iloc[-2], slow.iloc[-1]

        if fast_prev <= slow_prev and fast_now > slow_now:
            return Signal(
                action=SignalAction.buy,
                confidence=0.7,
                reason=f"Fast SMA({self.fast})={fast_now:.2f} crossed above slow SMA({self.slow})={slow_now:.2f}",
                source=self.name,
            )
        if fast_prev >= slow_prev and fast_now < slow_now:
            return Signal(
                action=SignalAction.sell,
                confidence=0.7,
                reason=f"Fast SMA({self.fast})={fast_now:.2f} crossed below slow SMA({self.slow})={slow_now:.2f}",
                source=self.name,
            )
        return Signal(
            action=SignalAction.hold,
            confidence=0.5,
            reason=f"No crossover (fast={fast_now:.2f}, slow={slow_now:.2f})",
            source=self.name,
        )
