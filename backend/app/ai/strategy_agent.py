# backend/app/ai/strategy_agent.py
"""LLM strategy designer: natural language -> validated StrategySpec (structured output).

Claude returns ONLY the spec + explanation. The spec->python render and all validation
happen in code (CLAUDE.md: keep mechanical work out of the model). The spec is never executed.
"""
from __future__ import annotations

from pydantic import BaseModel

from app.ai.claude_client import get_claude_client
from app.config import settings
from app.strategies.spec import StrategySpec
from app.strategies.spec_render import render_python

_SYSTEM_PROMPT = (
    "You design trading strategies as a STRICT declarative spec. Output only a StrategySpec "
    "(whitelisted indicators rsi/sma/ema/macd/bollinger_hi/bollinger_lo/close/volume; condition "
    "trees of comparisons and and/or/not) plus a one-paragraph explanation. Expose tunable numbers "
    "as params with sensible default/min/max. Do not write Python; do not invent indicators."
)


class StrategyDesignResponse(BaseModel):
    spec: StrategySpec
    explanation: str


def design_strategy(message: str, prior_spec: StrategySpec | None = None,
                    model: str | None = None) -> dict:
    model = model or settings.ai_model
    client = get_claude_client()
    content = message
    if prior_spec is not None:
        content = (
            f"Current strategy spec (JSON):\n{prior_spec.model_dump_json()}\n\n"
            f"Requested change: {message}"
        )
    response = client.messages.parse(
        model=model,
        max_tokens=2048,
        thinking={"type": "adaptive"},
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
        output_format=StrategyDesignResponse,
    )
    out = response.parsed_output
    if out is None:
        raise RuntimeError("AI strategy could not be parsed from the model response")
    return {
        "spec": out.spec,
        "rendered_python": render_python(out.spec),
        "explanation": out.explanation,
    }
