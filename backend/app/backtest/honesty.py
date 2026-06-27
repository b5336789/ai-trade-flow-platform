"""Backtest assumptions → explicit honesty warnings (pure, deterministic, fully unit-testable).

Surfaces the silent assumptions a return number hides: zero slippage, tiny sample, too few bars,
optimistically-selected OOS results, and which annualization calendar was used.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas import MarketKind

_MIN_TRADES = 30
_MIN_BARS = 100


class BacktestAssumptions(BaseModel):
    slippage_bps: float
    cost_taker_bps: float
    bars: int
    num_trades: int
    timeframe: str
    market: str
    annualization_basis: str
    oos_selected: bool = False
    warnings: list[str] = Field(default_factory=list)


def representative_cost_bps(market: MarketKind, settings) -> float:
    """One-side representative transaction cost in bps, for display."""
    if market == MarketKind.crypto:
        return settings.cost_crypto_taker_bps
    if market == MarketKind.tw_stock:
        return settings.cost_tw_fee_rate * settings.cost_tw_fee_discount * 10_000
    return settings.cost_us_fee_rate * 10_000


def assess(
    *,
    slippage_bps: float,
    cost_taker_bps: float,
    bars: int,
    num_trades: int,
    timeframe: str,
    market: str,
    oos_selected: bool = False,
) -> BacktestAssumptions:
    warnings: list[str] = []
    if slippage_bps <= 0:
        warnings.append("零滑價:成交品質被系統性高估")
    if num_trades < _MIN_TRADES:
        warnings.append(f"樣本過少({num_trades} 筆 < {_MIN_TRADES}):績效統計不顯著")
    if bars < _MIN_BARS:
        warnings.append(f"K 線過少({bars} < {_MIN_BARS}):結論脆弱")
    if oos_selected:
        warnings.append("此為被挑選後的 OOS 結果:屬樂觀上界,非未來表現保證")
    basis = (
        "365.25 日 × 24h (crypto, 24/7)"
        if market == MarketKind.crypto.value
        else "252 交易日 (stock trading calendar)"
    )
    return BacktestAssumptions(
        slippage_bps=slippage_bps,
        cost_taker_bps=cost_taker_bps,
        bars=bars,
        num_trades=num_trades,
        timeframe=timeframe,
        market=market,
        annualization_basis=basis,
        oos_selected=oos_selected,
        warnings=warnings,
    )
