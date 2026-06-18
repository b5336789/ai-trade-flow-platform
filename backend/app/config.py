"""Environment-driven application settings (pydantic-settings).

Field names map to UPPER_CASE env vars (case-insensitive), e.g. ``trading_mode`` -> ``TRADING_MODE``.
See ``.env.example`` at the repo root for the documented variables.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

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

    # API auth (M0.7). When ``api_token`` is empty, auth is DISABLED (open) so local dev and the
    # test suite work out of the box — deps.py logs a loud warning in that case. Real deployments
    # MUST set API_TOKEN. Clients authenticate via ``Authorization: Bearer <api_token>``.
    api_token: str = ""
    # CORS allowed origins (M0.7). Comma-separated in env, e.g.
    # "http://localhost:3000,https://app.example.com". Replaces the previous wide-open "*".
    # ``NoDecode`` disables pydantic-settings' default JSON decoding so the validator below can
    # accept a plain comma-separated string from the env var.
    api_cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    @field_validator("api_cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        """Allow a comma-separated string from the env var; pass real lists through unchanged."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    # Persistence
    database_url: str = "sqlite:///./trade_flow.db"

    # Notifications (optional outbound webhook, e.g. Slack/Discord incoming webhook URL)
    notify_webhook_url: str = ""

    # Paper trading
    paper_starting_cash: float = 100_000.0
    paper_quote_asset: str = "USDT"

    # Transaction costs (M0.1) — applied to every paper + backtest fill. Costs are ON by default;
    # zero-cost return numbers are dishonest. See trading/costs.py.
    cost_crypto_taker_bps: float = 7.5
    cost_crypto_maker_bps: float = 7.5
    cost_tw_fee_rate: float = 0.001425  # 台股手續費 0.1425% (買賣各一次)
    cost_tw_fee_discount: float = 1.0  # 券商折讓係數 (e.g. 0.6 = 六折)
    cost_tw_tax_rate: float = 0.003  # 證交稅 0.3% (僅賣出)
    cost_us_fee_rate: float = 0.0  # 複委託費率
    cost_us_fee_min: float = 0.0  # 複委託最低收費
    cost_slippage_bps: float = 0.0  # 固定滑價 (買進成交較高、賣出較低)

    # Backtest metrics (M0.3): annual risk-free rate for Sharpe/Sortino (0 = ignore).
    backtest_risk_free_rate: float = 0.0


settings = Settings()
