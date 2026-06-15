"""Lazily-constructed Anthropic client.

Reads the API key from settings (which loads ``.env``). Fails loud if the key is missing so AI
nodes never silently degrade.
"""

from __future__ import annotations

import anthropic

from app.config import settings

_client: anthropic.Anthropic | None = None


def get_claude_client() -> anthropic.Anthropic:
    if not settings.anthropic_api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set — AI signal/explanation nodes require it"
        )
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client
