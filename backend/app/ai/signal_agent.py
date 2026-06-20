"""LLM-based trading signal.

A compact, *deterministic* market summary is computed in code (CLAUDE.md: keep mechanical work
out of the model, manage token budget) and handed to Claude, which returns a structured
buy/sell/hold decision with a natural-language rationale via structured outputs.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.ai.structured import structured_completion
from app.config import settings
from app.schemas import Candle, Signal, SignalAction
from app.strategies.indicators import candles_to_df, rsi

_SYSTEM_PROMPT = (
    "You are a disciplined trading assistant. Given a compact market summary, decide whether to "
    "buy, sell, or hold. Be conservative: prefer 'hold' when the signal is weak or ambiguous. "
    "Base your decision only on the data provided; do not invent prices or news."
)


class AISignalResponse(BaseModel):
    """Structured output schema for the LLM (kept minimal for reliable parsing)."""

    action: SignalAction
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str


def _market_summary(symbol: str, candles: list[Candle]) -> str:
    df = candles_to_df(candles)
    closes = df["close"]
    last = float(closes.iloc[-1])
    first = float(closes.iloc[0])
    change_pct = (last / first - 1.0) * 100 if first else 0.0
    recent = [round(float(c), 4) for c in closes.iloc[-15:]]

    line = f"Symbol: {symbol}\nLatest close: {last}\nChange over window: {change_pct:.2f}%\n"
    if len(closes) >= 15:
        line += f"RSI(14): {float(rsi(closes, 14).iloc[-1]):.1f}\n"
    line += f"Recent closes (oldest->newest): {recent}"
    return line


def generate_ai_signal(
    symbol: str,
    candles: list[Candle],
    model: str | None = None,
    extra_context: str = "",
) -> Signal:
    if not candles:
        raise ValueError("generate_ai_signal requires candle data")

    model = model or settings.ai_model
    summary = _market_summary(symbol, candles)
    if extra_context:
        summary += f"\nAdditional context: {extra_context}"

    out = structured_completion(
        system=_SYSTEM_PROMPT,
        content=summary,
        output_model=AISignalResponse,
        model=model,
        max_tokens=1024,
    )

    return Signal(
        action=out.action,
        confidence=max(0.0, min(1.0, out.confidence)),
        reason=out.rationale,
        source=f"ai:{model}",
    )
