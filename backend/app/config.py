import logging
import secrets

from pydantic_settings import BaseSettings
from pydantic import model_validator
from pathlib import Path

_config_logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Telegram
    telegram_bot_token: str = ""
    telegram_webapp_url: str = ""
    admin_telegram_id: int = 0

    # API Keys
    alpha_vantage_api_key: str = ""  # Free key from https://www.alphavantage.co/support/#api-key
    cryptopanic_api_key: str = ""
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "btc-oracle/1.0"

    # External data APIs
    fred_api_key: str = ""  # FRED API for M2 money supply (free from https://fred.stlouisfed.org/docs/api/api_key.html)
    etherscan_api_key: str = ""  # Etherscan V2 API (free from https://etherscan.io/apis)
    solscan_api_key: str = ""  # Solscan Pro API (free tier: 10M CU from https://pro-api.solscan.io)
    arkham_api_key: str = ""  # Arkham Intelligence API (apply at intel.arkm.com/api)
    coingecko_api_key: str = ""  # CoinGecko Demo API key (free: 30 req/min from https://www.coingecko.com/en/api/pricing)

    # Database — /data/ path is a Railway persistent volume
    # DATABASE_URL is required — set to postgresql:// for production or sqlite+aiosqlite:// for local dev
    database_url: str

    # Backup settings
    backup_enabled: bool = True
    backup_interval_hours: int = 6
    backup_dir: str = "/data/backups"
    backup_retention_days: int = 7
    backup_sqlite_snapshot: bool = True  # Create portable SQLite snapshot from PG

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # ML — /data/weights persists on Railway volume, fallback to bundled weights
    model_dir: str = "/data/weights"
    # Deprecated: predictions are now time-aligned (1h/4h/24h cron schedules)
    # Kept for backward compatibility with .env files
    prediction_interval_minutes: int = 30

    # ML Retrain thresholds
    retrain_accuracy_threshold: float = 0.55
    retrain_interval_hours: int = 12
    selective_retrain_accuracy: float = 0.50
    selective_retrain_window_hours: int = 72

    # Binance
    binance_base_url: str = "https://api.binance.com"

    # Data collection intervals (seconds)
    price_collection_interval: int = 60
    news_collection_interval: int = 120  # every 2 minutes
    macro_collection_interval: int = 3600
    onchain_collection_interval: int = 3600
    fear_greed_collection_interval: int = 3600

    # Advisor settings
    advisor_enabled: bool = True
    advisor_default_balance: float = 10.0
    advisor_min_confidence: int = 55
    advisor_min_models_agreeing: int = 2
    advisor_min_risk_reward: float = 1.5
    advisor_max_leverage: int = 20
    advisor_kelly_fraction: float = 0.25
    advisor_cooldown_hours: int = 4

    # Telegram Stars Subscription (disabled by default — all free during beta)
    subscription_enabled: bool = True        # Master switch — False = everything free
    trial_days: int = 7                      # Free trial duration
    premium_price_stars: int = 500           # ~$9.99 in Telegram Stars
    premium_price_stars_monthly: int = 500      # 30 days
    premium_price_stars_quarterly: int = 1250   # 90 days (save 17%)
    premium_price_stars_yearly: int = 4500      # 365 days (save 25%)

    # Referral system
    referral_bonus_days: int = 7
    referral_enabled: bool = True
    bot_username: str = ""  # Auto-resolved from Telegram API at startup

    # API Monetization (disabled by default — all free)
    api_key_enabled: bool = True
    api_free_rate_limit: int = 60       # requests/hr
    api_basic_rate_limit: int = 300
    api_pro_rate_limit: int = 1000
    api_enterprise_rate_limit: int = 5000

    # Sentry error tracking
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1

    # Redis (for rate limiting, caching)
    redis_url: str = "redis://localhost:6379/0"

    # JWT authentication
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    @model_validator(mode="after")
    def _ensure_jwt_secret(self) -> "Settings":
        if not self.jwt_secret_key:
            self.jwt_secret_key = secrets.token_urlsafe(32)
            _config_logger.warning(
                "JWT_SECRET_KEY not set — generated a random secret. "
                "Set JWT_SECRET_KEY in your environment for stable tokens across restarts."
            )
        return self

    @property
    def is_postgres(self) -> bool:
        """True when DATABASE_URL points to PostgreSQL."""
        url = self.database_url.lower()
        return any(x in url for x in ("postgresql", "asyncpg", "postgres://"))

    @property
    def async_database_url(self) -> str:
        """Return an asyncpg-compatible URL for SQLAlchemy."""
        url = self.database_url
        # Railway gives postgres:// but SQLAlchemy needs postgresql+asyncpg://
        if url.startswith("postgres://"):
            url = "postgresql+asyncpg://" + url[len("postgres://"):]
        elif url.startswith("postgresql://"):
            url = "postgresql+asyncpg://" + url[len("postgresql://"):]
        return url

    @property
    def model_path(self) -> Path:
        return Path(self.model_dir)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
