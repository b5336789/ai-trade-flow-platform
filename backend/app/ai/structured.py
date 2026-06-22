"""Provider-agnostic structured completion.

Routes a (system, content, output_model) request to either Claude (native
Anthropic SDK, preserving adaptive thinking + messages.parse) or a local
LM Studio model (OpenAI-compatible endpoint via Instructor), selected by
``settings.ai_provider``. Fail loud: a missing key, unreachable endpoint,
unparseable output, or unknown provider raises — never silently degrade.
"""
from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from app.ai.claude_client import get_claude_client
from app.config import settings

T = TypeVar("T", bound=BaseModel)

_lmstudio_client = None


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
        client = get_claude_client()
        response = client.messages.parse(
            model=model,
            max_tokens=max_tokens,
            thinking={"type": "adaptive"},
            system=system,
            messages=[{"role": "user", "content": content}],
            output_format=output_model,
        )
        out = response.parsed_output
        if out is None:
            raise RuntimeError("AI response could not be parsed from the model")
        return out

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
