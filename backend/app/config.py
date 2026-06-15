"""Environment-driven application settings (pydantic-settings).

Field names map to UPPER_CASE env vars (case-insensitive), e.g. ``trading_mode`` -> ``TRADING_MODE``.
See ``.env.example`` at the repo root for the documented variables.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.schemas import TradingMode


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # Trading
    trading_mode: TradingMode = TradingMode.paper

    # Anthropic / Claude
    anthropic_api_key: str = ""
    ai_model: str = "claude-opus-4-8"

    # Crypto (Binance via ccxt)
    binance_api_key: str = ""
    binance_api_secret: str = ""
    binance_testnet: bool = True

    # Persistence
    database_url: str = "sqlite:///./trade_flow.db"

    # Notifications (optional outbound webhook, e.g. Slack/Discord incoming webhook URL)
    notify_webhook_url: str = ""

    # Paper trading
    paper_starting_cash: float = 100_000.0
    paper_quote_asset: str = "USDT"


settings = Settings()
