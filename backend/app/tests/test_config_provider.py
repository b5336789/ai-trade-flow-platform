"""Defaults for the AI provider settings."""
from __future__ import annotations

from app.config import Settings


def test_provider_defaults():
    s = Settings()
    assert s.ai_provider == "anthropic"
    assert s.ai_base_url == "http://localhost:1234/v1"
    assert s.ai_local_api_key == "lm-studio"
