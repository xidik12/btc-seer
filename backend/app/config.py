from pydantic_settings import BaseSettings
from pathlib import Path


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

    # Database — /data/ path is a Railway persistent volume
    # Set DATABASE_URL to a postgresql:// URL to use PostgreSQL (e.g. Railway PG plugin)
    database_url: str = "sqlite+aiosqlite:////data/btc_oracle.db"

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
    bot_username: str = "BTCSeerBot"

    # API Monetization (disabled by default — all free)
    api_key_enabled: bool = False
    api_free_rate_limit: int = 60       # requests/hr
    api_basic_rate_limit: int = 300
    api_pro_rate_limit: int = 1000
    api_enterprise_rate_limit: int = 5000

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
