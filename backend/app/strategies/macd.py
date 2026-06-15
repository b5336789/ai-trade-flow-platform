"""MACD strategy: buy when the MACD line crosses above its signal line, sell on the reverse."""

from __future__ import annotations

import pandas as pd

from app.schemas import Candle, Signal, SignalAction
from app.strategies.base import Strategy
from app.strategies.indicators import candles_to_df, macd


class MacdStrategy(Strategy):
    name = "macd"

    def __init__(self, window_fast: int = 12, window_slow: int = 26, window_sign: int = 9) -> None:
        if window_fast >= window_slow:
            raise ValueError(f"window_fast ({window_fast}) must be < window_slow ({window_slow})")
        self.window_fast = window_fast
        self.window_slow = window_slow
        self.window_sign = window_sign

    def generate(self, candles: list[Candle]) -> Signal:
        df = candles_to_df(candles)
        line, signal_line, _ = macd(
            df["close"],
            window_slow=self.window_slow,
            window_fast=self.window_fast,
            window_sign=self.window_sign,
        )
        if len(line) < 2 or pd.isna(line.iloc[-2]) or pd.isna(signal_line.iloc[-2]):
            raise ValueError("macd needs more candles before signal/line are defined")

        m_prev, m_now = line.iloc[-2], line.iloc[-1]
        s_prev, s_now = signal_line.iloc[-2], signal_line.iloc[-1]

        if m_prev <= s_prev and m_now > s_now:
            return Signal(
                action=SignalAction.buy,
                confidence=0.65,
                reason=f"MACD {m_now:.4f} crossed above signal {s_now:.4f}",
                source=self.name,
            )
        if m_prev >= s_prev and m_now < s_now:
            return Signal(
                action=SignalAction.sell,
                confidence=0.65,
                reason=f"MACD {m_now:.4f} crossed below signal {s_now:.4f}",
                source=self.name,
            )
        return Signal(
            action=SignalAction.hold,
            confidence=0.5,
            reason=f"MACD {m_now:.4f} vs signal {s_now:.4f} (no cross)",
            source=self.name,
        )
