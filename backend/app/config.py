from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Telegram
    telegram_bot_token: str = ""
    telegram_webapp_url: str = ""

    # API Keys
    cryptopanic_api_key: str = ""
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "btc-oracle/1.0"

    # Database
    database_url: str = "sqlite+aiosqlite:///./btc_oracle.db"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # ML
    model_dir: str = "app/models/weights"
    prediction_interval_minutes: int = 30  # Predict every 30 min for faster history buildup

    # Binance
    binance_base_url: str = "https://api.binance.com"

    # Data collection intervals (seconds)
    price_collection_interval: int = 60
    news_collection_interval: int = 120  # every 2 minutes
    macro_collection_interval: int = 3600
    onchain_collection_interval: int = 3600
    fear_greed_collection_interval: int = 3600

    @property
    def model_path(self) -> Path:
        return Path(self.model_dir)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
