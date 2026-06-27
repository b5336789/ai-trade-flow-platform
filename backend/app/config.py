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

    # AI provider selection: "anthropic" (Claude, native SDK) or "lmstudio" (local, OpenAI-compatible)
    ai_provider: str = "anthropic"

    # Anthropic / Claude
    anthropic_api_key: str = ""
    ai_model: str = "claude-opus-4-8"

    # Local LLM (LM Studio, OpenAI-compatible). api_key is required-non-empty by the OpenAI SDK but unused by LM Studio.
    ai_base_url: str = "http://localhost:1234/v1"
    ai_local_api_key: str = "lm-studio"

    # OpenRouter (cloud demo, OpenAI-compatible). Used when AI_PROVIDER=openrouter.
    # AI_MODEL=openrouter/free routes to a free model and filters for structured-output support.
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Structured-output retries when the model returns malformed/invalid JSON (lmstudio path).
    # Local models need more attempts than Claude; bump via AI_MAX_RETRIES if validation keeps failing.
    ai_max_retries: int = 5

    @field_validator("anthropic_api_key", mode="before")
    @classmethod
    def _normalize_anthropic_api_key(cls, value: object) -> object:
        """Treat the deploy sentinel as "unset" so AI stays disabled cleanly."""
        if value == "__disabled__":
            return ""
        return value

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

    # FX seam. All portfolio-level risk is judged in BASE_CURRENCY. ``fx_provider=static`` uses
    # the explicit ``fx_rates`` map; ``fx_provider=open_er_api`` fetches live USD/TWD-backed rates
    # through Open ExchangeRate-API with the TTL below. The static map remains the safe local-dev
    # provider and can be enabled as an explicit fallback for provider outages.
    base_currency: str = "TWD"
    fx_provider: str = "static"
    fx_rate_cache_ttl_seconds: int = 3600
    fx_live_currencies: Annotated[list[str], NoDecode] = ["USD", "USDT"]
    fx_static_fallback_enabled: bool = False
    fx_open_er_api_base_url: str = "https://open.er-api.com/v6/latest"
    fx_rates: Annotated[dict[str, float], NoDecode] = {"TWD": 1.0, "USD": 31.5, "USDT": 31.5}

    @field_validator("fx_provider")
    @classmethod
    def _validate_fx_provider(cls, value: str) -> str:
        provider = value.lower()
        if provider not in {"static", "open_er_api"}:
            raise ValueError("FX_PROVIDER must be one of: static, open_er_api")
        return provider

    @field_validator("fx_rate_cache_ttl_seconds")
    @classmethod
    def _validate_fx_cache_ttl(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("FX_RATE_CACHE_TTL_SECONDS must be positive")
        return value

    @field_validator("fx_live_currencies", mode="before")
    @classmethod
    def _split_fx_live_currencies(cls, value: object) -> object:
        """Allow a comma-separated live-currency string from the env var."""
        if isinstance(value, str):
            return [currency.strip().upper() for currency in value.split(",") if currency.strip()]
        if isinstance(value, list):
            return [str(currency).upper() for currency in value]
        return value

    @field_validator("fx_rates", mode="before")
    @classmethod
    def _parse_fx_rates(cls, value: object) -> object:
        """Parse a comma-separated "CCY:rate" env string; pass real dicts through unchanged."""
        if isinstance(value, str):
            parsed: dict[str, float] = {}
            for pair in value.split(","):
                pair = pair.strip()
                if not pair:
                    continue
                ccy, _, rate = pair.partition(":")
                ccy = ccy.strip()
                if not ccy or not rate.strip():
                    raise ValueError(f"invalid FX_RATES entry '{pair}'; expected 'CCY:rate'")
                parsed[ccy.upper()] = float(rate)
            return parsed
        if isinstance(value, dict):
            return {str(ccy).upper(): float(rate) for ccy, rate in value.items()}
        return value

    # Portfolio-level risk (M0.6), all in BASE_CURRENCY (TWD). See trading/risk.py PortfolioGuard.
    max_total_exposure_value: float = 1_000_000.0  # cap on total position market value
    max_daily_loss: float = 100_000.0  # day-start equity minus current equity; breach -> halt
    max_orders_per_day: int = 50  # max orders placed per UTC day
    kill_switch: bool = False  # config-level kill switch (also a runtime DB flag)

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
    cost_slippage_bps: float = 5.0  # 固定滑價 (買進成交較高、賣出較低). 保守非零預設 — 零滑價會高估成交品質; Next 階段升級為 size/liquidity-aware 模型.

    # Backtest metrics (M0.3): annual risk-free rate for Sharpe/Sortino (0 = ignore).
    backtest_risk_free_rate: float = 0.0


settings = Settings()
