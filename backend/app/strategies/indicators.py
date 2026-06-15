"""Technical-indicator helpers (thin wrappers over the ``ta`` library — not hand-rolled).

We use ``ta`` rather than ``pandas-ta`` because it is stable under NumPy 2.x; see README.
"""

from __future__ import annotations

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator
from ta.volatility import BollingerBands

from app.schemas import Candle


def candles_to_df(candles: list[Candle]) -> pd.DataFrame:
    """Convert a list of Candle into a time-indexed OHLCV DataFrame (fail loud if empty)."""
    if not candles:
        raise ValueError("candles_to_df received no candles")
    df = pd.DataFrame([c.model_dump() for c in candles])
    return df.set_index("timestamp").sort_index()


def sma(close: pd.Series, window: int) -> pd.Series:
    return SMAIndicator(close, window=window).sma_indicator()


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    return RSIIndicator(close, window=window).rsi()


def macd(close: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Returns (macd_line, signal_line, histogram)."""
    indicator = MACD(close)
    return indicator.macd(), indicator.macd_signal(), indicator.macd_diff()


def bollinger(
    close: pd.Series, window: int = 20, window_dev: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Returns (upper_band, middle_band, lower_band)."""
    bands = BollingerBands(close, window=window, window_dev=window_dev)
    return bands.bollinger_hband(), bands.bollinger_mavg(), bands.bollinger_lband()
