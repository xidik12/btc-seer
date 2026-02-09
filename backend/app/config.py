from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Telegram
    telegram_bot_token: str = ""
    telegram_webapp_url: str = ""

    # API Keys
    alpha_vantage_api_key: str = ""  # Free key from https://www.alphavantage.co/support/#api-key
    cryptopanic_api_key: str = ""
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "btc-oracle/1.0"

    # Database — /data/ path is a Railway persistent volume
    database_url: str = "sqlite+aiosqlite:////data/btc_oracle.db"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # ML — /data/weights persists on Railway volume, fallback to bundled weights
    model_dir: str = "/data/weights"
    prediction_interval_minutes: int = 30  # Predict every 30 min for faster history buildup

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
    advisor_min_confidence: int = 70
    advisor_min_models_agreeing: int = 3
    advisor_min_risk_reward: float = 2.0
    advisor_max_leverage: int = 20
    advisor_kelly_fraction: float = 0.25
    advisor_cooldown_hours: int = 4

    # API Monetization (disabled by default — all free)
    api_key_enabled: bool = False
    api_free_rate_limit: int = 60       # requests/hr
    api_basic_rate_limit: int = 300
    api_pro_rate_limit: int = 1000
    api_enterprise_rate_limit: int = 5000

    @property
    def model_path(self) -> Path:
        return Path(self.model_dir)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
