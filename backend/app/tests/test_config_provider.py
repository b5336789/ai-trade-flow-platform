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


def test_fx_provider_defaults():
    s = Settings(_env_file=None)

    assert s.fx_provider == "static"
    assert s.fx_rate_cache_ttl_seconds == 3600
    assert s.fx_live_currencies == ["USD", "USDT"]
    assert s.fx_static_fallback_enabled is False
    assert s.fx_open_er_api_base_url == "https://open.er-api.com/v6/latest"


def test_fx_live_currencies_accepts_comma_separated_env_string():
    s = Settings(_env_file=None, fx_live_currencies="USD, USDT, TWD")

    assert s.fx_live_currencies == ["USD", "USDT", "TWD"]
