"""Provider-agnostic structured completion.

Routes a (system, content, output_model) request to either Claude or a local
LM Studio model (both via Instructor, JSON mode), selected by
``settings.ai_provider``. Fail loud: a missing key, unreachable endpoint,
unparseable output, or unknown provider raises — never silently degrade.

Both providers go through Instructor's JSON mode (client-side schema +
validation) rather than the provider's native structured-output validator:
``StrategySpec`` has a self-referencing condition tree (Combinator -> Combinator)
and Anthropic's native ``messages.parse``/``output_format`` rejects recursive
schemas ("Circular reference detected"). Instructor JSON mode handles recursion.
"""
from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from app.ai.claude_client import get_claude_client
from app.config import settings

T = TypeVar("T", bound=BaseModel)

_lmstudio_client = None
_anthropic_client = None


def _get_anthropic_client():
    """Lazily build + cache the Instructor-wrapped Anthropic client (JSON mode).

    Uses ANTHROPIC_JSON (not native output_format) so the recursive StrategySpec
    schema is validated client-side. ``get_claude_client`` fails loud if the key
    is missing.
    """
    global _anthropic_client
    if _anthropic_client is None:
        import instructor

        _anthropic_client = instructor.from_anthropic(
            get_claude_client(), mode=instructor.Mode.JSON
        )
    return _anthropic_client


def _get_lmstudio_client():
    """Lazily build + cache the Instructor-wrapped OpenAI client (mirrors claude_client)."""
    global _lmstudio_client
    if _lmstudio_client is None:
        import instructor
        from openai import OpenAI

        # JSON_SCHEMA mode: LM Studio rejects Instructor's default TOOLS mode
        # (it sends tool_choice as an object) and instead enforces output via
        # response_format=json_schema — grammar-constrained, ideal for nested specs.
        _lmstudio_client = instructor.from_openai(
            OpenAI(base_url=settings.ai_base_url, api_key=settings.ai_local_api_key),
            mode=instructor.Mode.JSON_SCHEMA,
        )
    return _lmstudio_client


def structured_completion(
    *,
    system: str,
    content: str,
    output_model: type[T],
    model: str | None = None,
    max_tokens: int = 2048,
    max_retries: int | None = None,
) -> T:
    model = model or settings.ai_model
    # Local models emit malformed JSON more often than Claude; default to the
    # configured retry budget so structured output survives transient glitches.
    max_retries = settings.ai_max_retries if max_retries is None else max_retries
    provider = settings.ai_provider

    if provider == "anthropic":
        client = _get_anthropic_client()
        return client.messages.create(
            model=model,
            max_tokens=max_tokens,
            max_retries=max_retries,
            system=system,
            messages=[{"role": "user", "content": content}],
            response_model=output_model,
        )

    if provider == "lmstudio":
        client = _get_lmstudio_client()
        return client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            max_retries=max_retries,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": content},
            ],
            response_model=output_model,
        )

    raise RuntimeError(f"Unknown ai_provider: {provider!r}")
