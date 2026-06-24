"""Defaults for the AI provider settings."""
from __future__ import annotations

from app.config import Settings


def test_provider_defaults():
    # _env_file=None: test the code defaults, not whatever a local .env (e.g. a dev
    # machine running against LM Studio) happens to set.
    s = Settings(_env_file=None)
    assert s.ai_provider == "anthropic"
    assert s.ai_base_url == "http://localhost:1234/v1"
    assert s.ai_local_api_key == "lm-studio"
    # OpenRouter (cloud demo) defaults: key unset (fail-loud at call time), public base URL.
    assert s.openrouter_api_key == ""
    assert s.openrouter_base_url == "https://openrouter.ai/api/v1"
