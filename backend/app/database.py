import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Text, Float, Integer, BigInteger, String, JSON, DateTime, Boolean, Index, UniqueConstraint, func, text, inspect
from sqlalchemy.sql import extract
from datetime import datetime

_db_logger = logging.getLogger(__name__)

from app.config import settings


def _create_engine():
    """Create async engine with dialect-appropriate settings."""
    url = settings.async_database_url
    if settings.is_postgres:
        _db_logger.info("Using PostgreSQL backend")
        return create_async_engine(
            url,
            echo=False,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=1800,
            connect_args={"command_timeout": 30},
        )
    _db_logger.info("Using SQLite backend")
    return create_async_engine(url, echo=False)


engine = _create_engine()
async_session = async_sessionmaker(engine, expire_on_commit=False)


def timestamp_diff_order(column, target_time):
    """Return an ORDER BY expression for 'closest to target_time'.

    Uses EXTRACT(EPOCH ...) on PostgreSQL, julianday() on SQLite.
    """
    if settings.is_postgres:
        return func.abs(extract("epoch", column) - extract("epoch", target_time))
    return func.abs(func.julianday(column) - func.julianday(target_time))


class Base(DeclarativeBase):
    pass


class Price(Base):
    __tablename__ = "prices"
    __table_args__ = (
        UniqueConstraint("timestamp", name="uq_prices_timestamp"),
        Index("ix_prices_timestamp", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(50), default="binance")


class News(Base):
    __tablename__ = "news"
    __table_args__ = (
        Index("ix_news_published_at", "timestamp"),
        Index("ix_news_coin_created", "coin_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    source: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text, nullable=True)
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=True)
    raw_sentiment: Mapped[str] = mapped_column(String(20), nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=True, default="en")
    coin_id: Mapped[str] = mapped_column(String(100), nullable=True, index=True)


class Feature(Base):
    __tablename__ = "features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    feature_data: Mapped[dict] = mapped_column(JSON)


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        Index("ix_predictions_timestamp_timeframe", "timestamp", "timeframe"),
        Index("ix_predictions_timeframe_created", "timeframe", "created_at"),
        Index("ix_predictions_was_correct_timeframe", "was_correct", "timeframe"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    timeframe: Mapped[str] = mapped_column(String(10))  # 1h, 4h, 24h
    direction: Mapped[str] = mapped_column(String(20))  # bullish, bearish, neutral
    confidence: Mapped[float] = mapped_column(Float)
    predicted_price: Mapped[float] = mapped_column(Float, nullable=True)
    predicted_change_pct: Mapped[float] = mapped_column(Float, nullable=True)
    current_price: Mapped[float] = mapped_column(Float)
    actual_price: Mapped[float] = mapped_column(Float, nullable=True)
    actual_direction: Mapped[str] = mapped_column(String(20), nullable=True)
    was_correct: Mapped[bool] = mapped_column(Boolean, nullable=True)
    model_outputs: Mapped[dict] = mapped_column(JSON, nullable=True)

    # Self-learning fields (auto-migrated)
    error_pct: Mapped[float] = mapped_column(Float, nullable=True)              # (actual - predicted) / predicted * 100
    volatility_regime: Mapped[str] = mapped_column(String(20), nullable=True)  # low, normal, high, extreme
    trend_state: Mapped[str] = mapped_column(String(20), nullable=True)        # trending_up, trending_down, ranging
    evaluation_notes: Mapped[dict] = mapped_column(JSON, nullable=True)        # analysis summary


class Signal(Base):
    __tablename__ = "signals"
    __table_args__ = (
        Index("ix_signals_timestamp_timeframe", "timestamp", "timeframe"),
        Index("ix_signals_timeframe_created", "timeframe", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    action: Mapped[str] = mapped_column(String(20))  # strong_buy, buy, hold, sell, strong_sell
    direction: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[float] = mapped_column(Float)
    entry_price: Mapped[float] = mapped_column(Float)
    target_price: Mapped[float] = mapped_column(Float)
    stop_loss: Mapped[float] = mapped_column(Float)
    risk_rating: Mapped[int] = mapped_column(Integer)  # 1-10
    timeframe: Mapped[str] = mapped_column(String(10))
    reasoning: Mapped[str] = mapped_column(Text, nullable=True)


class MacroData(Base):
    __tablename__ = "macro_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    dxy: Mapped[float] = mapped_column(Float, nullable=True)
    gold: Mapped[float] = mapped_column(Float, nullable=True)
    sp500: Mapped[float] = mapped_column(Float, nullable=True)
    treasury_10y: Mapped[float] = mapped_column(Float, nullable=True)
    nasdaq: Mapped[float] = mapped_column(Float, nullable=True)
    vix: Mapped[float] = mapped_column(Float, nullable=True)
    eurusd: Mapped[float] = mapped_column(Float, nullable=True)
    fear_greed_index: Mapped[int] = mapped_column(Integer, nullable=True)
    fear_greed_label: Mapped[str] = mapped_column(String(30), nullable=True)
    m2_supply: Mapped[float] = mapped_column(Float, nullable=True)  # M2 money supply (trillions USD)


class OnChainData(Base):
    __tablename__ = "onchain_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    hash_rate: Mapped[float] = mapped_column(Float, nullable=True)
    difficulty: Mapped[float] = mapped_column(Float, nullable=True)
    mempool_size: Mapped[int] = mapped_column(Integer, nullable=True)
    mempool_fees: Mapped[float] = mapped_column(Float, nullable=True)
    tx_volume: Mapped[float] = mapped_column(Float, nullable=True)
    active_addresses: Mapped[int] = mapped_column(Integer, nullable=True)
    exchange_reserve: Mapped[float] = mapped_column(Float, nullable=True)
    large_tx_count: Mapped[int] = mapped_column(Integer, nullable=True)


class InfluencerTweet(Base):
    __tablename__ = "influencer_tweets"
    __table_args__ = (
        Index("ix_influencer_tweets_timestamp", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    influencer_name: Mapped[str] = mapped_column(String(100))
    username: Mapped[str] = mapped_column(String(100), index=True)
    role: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(50))  # ceo, investor, analyst, etc.
    weight: Mapped[int] = mapped_column(Integer)  # Influence weight 1-10
    text: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text, nullable=True)
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=True)
    published_at: Mapped[str] = mapped_column(String(100), nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=True, default="en")


class EventImpact(Base):
    """Tracks how specific news events impacted BTC price historically.

    This is the system's 'memory' — it remembers what happened after similar events
    and uses that knowledge to improve predictions.
    """
    __tablename__ = "event_impacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    news_id: Mapped[int] = mapped_column(Integer, nullable=True)  # FK to news table
    title: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(100))

    # Event classification
    category: Mapped[str] = mapped_column(String(50), index=True)  # war, politics, regulation, etc.
    subcategory: Mapped[str] = mapped_column(String(50), nullable=True)
    keywords: Mapped[str] = mapped_column(Text, nullable=True)  # comma-separated matched keywords
    severity: Mapped[int] = mapped_column(Integer, default=5)  # 1-10

    # Sentiment at time of event
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=True)

    # BTC price at time of event
    price_at_event: Mapped[float] = mapped_column(Float)

    # Measured price impacts (filled in over time by evaluator)
    price_1h: Mapped[float] = mapped_column(Float, nullable=True)
    price_4h: Mapped[float] = mapped_column(Float, nullable=True)
    price_24h: Mapped[float] = mapped_column(Float, nullable=True)
    price_7d: Mapped[float] = mapped_column(Float, nullable=True)

    change_pct_1h: Mapped[float] = mapped_column(Float, nullable=True)
    change_pct_4h: Mapped[float] = mapped_column(Float, nullable=True)
    change_pct_24h: Mapped[float] = mapped_column(Float, nullable=True)
    change_pct_7d: Mapped[float] = mapped_column(Float, nullable=True)

    # Was the sentiment predictive of the direction?
    sentiment_was_predictive: Mapped[bool] = mapped_column(Boolean, nullable=True)

    # Evaluation status
    evaluated_1h: Mapped[bool] = mapped_column(Boolean, default=False)
    evaluated_4h: Mapped[bool] = mapped_column(Boolean, default=False)
    evaluated_24h: Mapped[bool] = mapped_column(Boolean, default=False)
    evaluated_7d: Mapped[bool] = mapped_column(Boolean, default=False)


class QuantPrediction(Base):
    """Quant Theory-based predictions (separate from ML ensemble)."""
    __tablename__ = "quant_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    current_price: Mapped[float] = mapped_column(Float)
    composite_score: Mapped[float] = mapped_column(Float)  # -100 to +100
    action: Mapped[str] = mapped_column(String(20))  # STRONG_BUY, BUY, LEAN_BULLISH, etc.
    direction: Mapped[str] = mapped_column(String(20))  # bullish / bearish
    confidence: Mapped[float] = mapped_column(Float)

    # Per-timeframe predictions
    pred_1h_price: Mapped[float] = mapped_column(Float, nullable=True)
    pred_1h_change_pct: Mapped[float] = mapped_column(Float, nullable=True)
    pred_4h_price: Mapped[float] = mapped_column(Float, nullable=True)
    pred_4h_change_pct: Mapped[float] = mapped_column(Float, nullable=True)
    pred_24h_price: Mapped[float] = mapped_column(Float, nullable=True)
    pred_24h_change_pct: Mapped[float] = mapped_column(Float, nullable=True)

    # Signal counts
    active_signals: Mapped[int] = mapped_column(Integer, nullable=True)
    bullish_signals: Mapped[int] = mapped_column(Integer, nullable=True)
    bearish_signals: Mapped[int] = mapped_column(Integer, nullable=True)
    agreement_ratio: Mapped[float] = mapped_column(Float, nullable=True)

    # Full breakdown stored as JSON
    signal_breakdown: Mapped[dict] = mapped_column(JSON, nullable=True)

    # 1-week and 1-month predictions
    pred_1w_price: Mapped[float] = mapped_column(Float, nullable=True)
    pred_1w_change_pct: Mapped[float] = mapped_column(Float, nullable=True)
    pred_1mo_price: Mapped[float] = mapped_column(Float, nullable=True)
    pred_1mo_change_pct: Mapped[float] = mapped_column(Float, nullable=True)

    # Evaluation (filled later)
    actual_price_1h: Mapped[float] = mapped_column(Float, nullable=True)
    actual_price_24h: Mapped[float] = mapped_column(Float, nullable=True)
    actual_price_1w: Mapped[float] = mapped_column(Float, nullable=True)
    actual_price_1mo: Mapped[float] = mapped_column(Float, nullable=True)
    was_correct_1h: Mapped[bool] = mapped_column(Boolean, nullable=True)
    was_correct_24h: Mapped[bool] = mapped_column(Boolean, nullable=True)
    was_correct_1w: Mapped[bool] = mapped_column(Boolean, nullable=True)
    was_correct_1mo: Mapped[bool] = mapped_column(Boolean, nullable=True)


class FundingRate(Base):
    """Persists Binance perpetual funding rates and open interest."""
    __tablename__ = "funding_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    funding_rate: Mapped[float] = mapped_column(Float, nullable=True)
    mark_price: Mapped[float] = mapped_column(Float, nullable=True)
    index_price: Mapped[float] = mapped_column(Float, nullable=True)
    next_funding_time: Mapped[int] = mapped_column(BigInteger, nullable=True)  # Unix ms
    open_interest: Mapped[float] = mapped_column(Float, nullable=True)  # BTC


class BtcDominance(Base):
    """Persists BTC dominance and global crypto market data."""
    __tablename__ = "btc_dominance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    btc_dominance: Mapped[float] = mapped_column(Float, nullable=True)
    eth_dominance: Mapped[float] = mapped_column(Float, nullable=True)
    total_market_cap: Mapped[float] = mapped_column(Float, nullable=True)  # USD
    total_volume: Mapped[float] = mapped_column(Float, nullable=True)  # USD 24h
    market_cap_change_24h: Mapped[float] = mapped_column(Float, nullable=True)  # %


class IndicatorSnapshot(Base):
    """Hourly snapshot of all computed technical indicators."""
    __tablename__ = "indicator_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    price: Mapped[float] = mapped_column(Float)
    indicators: Mapped[dict] = mapped_column(JSON)  # Full indicator dict


class AlertLog(Base):
    """Logs every alert sent to users for audit and debugging."""
    __tablename__ = "alert_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    alert_type: Mapped[str] = mapped_column(String(30))  # hourly, breaking
    status: Mapped[str] = mapped_column(String(20))  # sent, failed
    error: Mapped[str] = mapped_column(Text, nullable=True)


class ModelVersion(Base):
    """Tracks trained model versions, training metrics, and weights paths."""
    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    model_type: Mapped[str] = mapped_column(String(30))  # tft, lstm, xgboost
    version: Mapped[int] = mapped_column(Integer)

    # Training metrics
    train_accuracy: Mapped[float] = mapped_column(Float, nullable=True)
    val_accuracy: Mapped[float] = mapped_column(Float, nullable=True)
    test_accuracy: Mapped[float] = mapped_column(Float, nullable=True)
    train_loss: Mapped[float] = mapped_column(Float, nullable=True)

    # Dataset info
    train_samples: Mapped[int] = mapped_column(Integer, nullable=True)
    feature_count: Mapped[int] = mapped_column(Integer, nullable=True)

    # Weights path
    weights_path: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)

    # Post-deployment accuracy (updated after running in prod)
    live_accuracy_1h: Mapped[float] = mapped_column(Float, nullable=True)
    live_accuracy_24h: Mapped[float] = mapped_column(Float, nullable=True)

    # A/B testing fields
    is_candidate: Mapped[bool] = mapped_column(Boolean, default=False)
    ab_test_accuracy: Mapped[float] = mapped_column(Float, nullable=True)
    ensemble_weight: Mapped[float] = mapped_column(Float, nullable=True)


class BotUser(Base):
    __tablename__ = "bot_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=True)
    subscribed: Mapped[bool] = mapped_column(Boolean, default=False)
    alert_interval: Mapped[str] = mapped_column(String(10), default="4h")  # 1h, 4h, 24h
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Subscription fields
    subscription_tier: Mapped[str] = mapped_column(String(20), nullable=True, default="free")
    trial_end: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    subscription_end: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    stars_payment_id: Mapped[str] = mapped_column(String(200), nullable=True)

    # Referral system
    referral_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=True, index=True)
    referred_by: Mapped[int] = mapped_column(BigInteger, nullable=True)
    referral_count: Mapped[int] = mapped_column(Integer, default=0)

    # Partner referral
    partner_code: Mapped[str] = mapped_column(String(50), nullable=True)

    # Activity tracking
    last_active: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=None)

    # Admin / ban
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    ban_reason: Mapped[str] = mapped_column(String(500), nullable=True)


class PaymentHistory(Base):
    """Logs every Telegram Stars payment for subscription tracking."""
    __tablename__ = "payment_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    tier: Mapped[str] = mapped_column(String(20))  # monthly, quarterly, yearly
    days: Mapped[int] = mapped_column(Integer)
    stars_amount: Mapped[int] = mapped_column(Integer)
    payment_id: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class Referral(Base):
    """Tracks referral relationships and bonus grants."""
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    referrer_telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    referee_telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    referrer_bonus_days: Mapped[int] = mapped_column(Integer, default=7)
    referee_bonus_days: Mapped[int] = mapped_column(Integer, default=7)


class PortfolioState(Base):
    """Tracks user portfolio balance, risk settings, and trading stats."""
    __tablename__ = "portfolio_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Balance
    balance_usdt: Mapped[float] = mapped_column(Float, default=10.0)
    initial_balance: Mapped[float] = mapped_column(Float, default=10.0)
    total_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    total_pnl_pct: Mapped[float] = mapped_column(Float, default=0.0)

    # Risk settings
    max_risk_per_trade_pct: Mapped[float] = mapped_column(Float, default=10.0)
    max_leverage: Mapped[int] = mapped_column(Integer, default=20)
    max_open_trades: Mapped[int] = mapped_column(Integer, default=2)
    daily_max_loss_pct: Mapped[float] = mapped_column(Float, default=30.0)

    # Stats
    consecutive_losses: Mapped[int] = mapped_column(Integer, default=0)
    consecutive_wins: Mapped[int] = mapped_column(Integer, default=0)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0)
    losing_trades: Mapped[int] = mapped_column(Integer, default=0)

    # Daily loss tracking & cooldown
    daily_loss_today: Mapped[float] = mapped_column(Float, default=0.0)
    daily_loss_date: Mapped[str] = mapped_column(String(10), nullable=True)  # YYYY-MM-DD
    cooldown_until: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class TradeAdvice(Base):
    """A complete trade plan generated by the advisor."""
    __tablename__ = "trade_advices"
    __table_args__ = (
        Index("ix_trade_advices_telegram_status", "telegram_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())

    # Plan
    direction: Mapped[str] = mapped_column(String(10))  # LONG / SHORT
    entry_price: Mapped[float] = mapped_column(Float)
    entry_zone_low: Mapped[float] = mapped_column(Float, nullable=True)
    entry_zone_high: Mapped[float] = mapped_column(Float, nullable=True)
    stop_loss: Mapped[float] = mapped_column(Float)
    take_profit_1: Mapped[float] = mapped_column(Float)
    take_profit_2: Mapped[float] = mapped_column(Float, nullable=True)
    take_profit_3: Mapped[float] = mapped_column(Float, nullable=True)

    # Sizing
    leverage: Mapped[int] = mapped_column(Integer)
    position_size_usdt: Mapped[float] = mapped_column(Float)
    position_size_pct: Mapped[float] = mapped_column(Float)
    risk_amount_usdt: Mapped[float] = mapped_column(Float)

    # Metrics
    risk_reward_ratio: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    risk_rating: Mapped[int] = mapped_column(Integer, nullable=True)

    # Context
    reasoning: Mapped[str] = mapped_column(Text, nullable=True)
    models_agreeing: Mapped[str] = mapped_column(Text, nullable=True)
    urgency: Mapped[str] = mapped_column(String(30), default="enter_now")  # enter_now, limit_order, wait_for_pullback
    timeframe: Mapped[str] = mapped_column(String(10), default="1h")

    # References
    prediction_id: Mapped[int] = mapped_column(Integer, nullable=True)
    signal_id: Mapped[int] = mapped_column(Integer, nullable=True)
    quant_prediction_id: Mapped[int] = mapped_column(Integer, nullable=True)

    # Lifecycle
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, opened, partial_tp, closed, cancelled, expired
    opened_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    close_reason: Mapped[str] = mapped_column(String(50), nullable=True)

    # Mock/Paper trading flag
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False)

    # Alert flags
    breakeven_alert_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    partial_tp_alert_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    close_alert_sent: Mapped[bool] = mapped_column(Boolean, default=False)


class TradeResult(Base):
    """Final result of a completed trade."""
    __tablename__ = "trade_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_advice_id: Mapped[int] = mapped_column(Integer, index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    direction: Mapped[str] = mapped_column(String(10))
    entry_price: Mapped[float] = mapped_column(Float)
    exit_price: Mapped[float] = mapped_column(Float)
    leverage: Mapped[int] = mapped_column(Integer)
    position_size_usdt: Mapped[float] = mapped_column(Float)

    pnl_usdt: Mapped[float] = mapped_column(Float)
    pnl_pct: Mapped[float] = mapped_column(Float)
    pnl_pct_leveraged: Mapped[float] = mapped_column(Float)
    was_winner: Mapped[bool] = mapped_column(Boolean)

    close_reason: Mapped[str] = mapped_column(String(50), nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=True)
    balance_before: Mapped[float] = mapped_column(Float, nullable=True)
    balance_after: Mapped[float] = mapped_column(Float, nullable=True)


class PredictionContext(Base):
    """Full snapshot of features, news, social, macro at each prediction for exact replay."""
    __tablename__ = "prediction_contexts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    prediction_id: Mapped[int] = mapped_column(Integer, nullable=True)
    current_price: Mapped[float] = mapped_column(Float)
    features: Mapped[dict] = mapped_column(JSON, nullable=True)
    news_headlines: Mapped[dict] = mapped_column(JSON, nullable=True)
    influencer_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    macro_snapshot: Mapped[dict] = mapped_column(JSON, nullable=True)
    onchain_snapshot: Mapped[dict] = mapped_column(JSON, nullable=True)
    funding_snapshot: Mapped[dict] = mapped_column(JSON, nullable=True)
    dominance_snapshot: Mapped[dict] = mapped_column(JSON, nullable=True)
    event_memory: Mapped[dict] = mapped_column(JSON, nullable=True)
    model_outputs: Mapped[dict] = mapped_column(JSON, nullable=True)


class NewsPriceCorrelation(Base):
    """Word/phrase-level tracking of headline correlations with price moves."""
    __tablename__ = "news_price_correlations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phrase: Mapped[str] = mapped_column(String(200), index=True)
    phrase_type: Mapped[str] = mapped_column(String(20))  # word, bigram, trigram
    occurrences: Mapped[int] = mapped_column(Integer, default=0)
    avg_change_1h: Mapped[float] = mapped_column(Float, default=0.0)
    avg_change_4h: Mapped[float] = mapped_column(Float, default=0.0)
    avg_change_24h: Mapped[float] = mapped_column(Float, default=0.0)
    bullish_ratio: Mapped[float] = mapped_column(Float, default=0.5)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    correlation_score: Mapped[float] = mapped_column(Float, default=0.0)


class ModelPerformanceLog(Base):
    """Per-model accuracy tracking per prediction."""
    __tablename__ = "model_performance_logs"
    __table_args__ = (
        Index("ix_model_perf_model_timeframe", "model_name", "timeframe"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    prediction_id: Mapped[int] = mapped_column(Integer, index=True)
    model_name: Mapped[str] = mapped_column(String(30), index=True)  # tft, lstm, xgboost, timesfm, ensemble
    timeframe: Mapped[str] = mapped_column(String(10))
    predicted_direction: Mapped[str] = mapped_column(String(20))
    predicted_prob: Mapped[float] = mapped_column(Float, nullable=True)
    actual_direction: Mapped[str] = mapped_column(String(20), nullable=True)
    was_correct: Mapped[bool] = mapped_column(Boolean, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=True)


class FeatureImportanceLog(Base):
    """Which features matter most, tracked over time."""
    __tablename__ = "feature_importance_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    model_type: Mapped[str] = mapped_column(String(30))
    feature_importances: Mapped[dict] = mapped_column(JSON)
    top_features: Mapped[dict] = mapped_column(JSON, nullable=True)


class CoinInfo(Base):
    """Tracked cryptocurrency coins (BTC, ETH, SOL, XRP, etc.)."""
    __tablename__ = "coin_info"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    coin_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)  # "ethereum", "solana"
    symbol: Mapped[str] = mapped_column(String(20))  # "ETH", "SOL"
    name: Mapped[str] = mapped_column(String(200))  # "Ethereum", "Solana"
    image_url: Mapped[str] = mapped_column(String(500), nullable=True)
    coingecko_id: Mapped[str] = mapped_column(String(100))
    is_tracked: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class CoinPrice(Base):
    """Price snapshots for tracked coins."""
    __tablename__ = "coin_prices"
    __table_args__ = (
        Index("ix_coin_prices_coin_timestamp", "coin_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    coin_id: Mapped[str] = mapped_column(String(100), index=True)
    price_usd: Mapped[float] = mapped_column(Float)
    market_cap: Mapped[float] = mapped_column(Float, nullable=True)
    volume_24h: Mapped[float] = mapped_column(Float, nullable=True)
    change_1h: Mapped[float] = mapped_column(Float, nullable=True)
    change_24h: Mapped[float] = mapped_column(Float, nullable=True)
    change_7d: Mapped[float] = mapped_column(Float, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())


class CoinReport(Base):
    """Cached reports for coin contract address lookups."""
    __tablename__ = "coin_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    address: Mapped[str] = mapped_column(String(200), index=True)
    chain: Mapped[str] = mapped_column(String(50))  # "ethereum", "solana", "bsc"
    coin_id: Mapped[str] = mapped_column(String(100), nullable=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=True)
    report_data: Mapped[str] = mapped_column(Text, nullable=True)  # JSON blob
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class WhaleTransaction(Base):
    """Large BTC transactions (>100 BTC) tracked for whale movement analysis."""
    __tablename__ = "whale_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tx_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    amount_btc: Mapped[float] = mapped_column(Float)
    amount_usd: Mapped[float] = mapped_column(Float, nullable=True)

    # Classification
    direction: Mapped[str] = mapped_column(String(20), default="unknown")  # exchange_in, exchange_out, whale_to_whale, unknown
    from_entity: Mapped[str] = mapped_column(String(100), default="unknown")
    to_entity: Mapped[str] = mapped_column(String(100), default="unknown")
    severity: Mapped[int] = mapped_column(Integer, default=5)  # 1-10 based on amount
    btc_price_at_tx: Mapped[float] = mapped_column(Float, nullable=True)

    # Impact tracking (mirrors EventImpact)
    change_pct_1h: Mapped[float] = mapped_column(Float, nullable=True)
    change_pct_4h: Mapped[float] = mapped_column(Float, nullable=True)
    change_pct_24h: Mapped[float] = mapped_column(Float, nullable=True)
    evaluated_1h: Mapped[bool] = mapped_column(Boolean, default=False)
    evaluated_4h: Mapped[bool] = mapped_column(Boolean, default=False)
    evaluated_24h: Mapped[bool] = mapped_column(Boolean, default=False)
    direction_was_predictive: Mapped[bool] = mapped_column(Boolean, nullable=True)

    # Entity identification
    entity_name: Mapped[str] = mapped_column(String(100), nullable=True)     # "BlackRock", "MicroStrategy", "Binance"
    entity_type: Mapped[str] = mapped_column(String(30), nullable=True)      # "exchange", "institution", "government", "individual", "unknown"
    entity_wallet: Mapped[str] = mapped_column(String(20), nullable=True)    # "cold", "hot", "custody", "treasury"

    # Actual Bitcoin addresses (for transaction chaining)
    from_address: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    to_address: Mapped[str] = mapped_column(String(100), nullable=True, index=True)

    source: Mapped[str] = mapped_column(String(50), default="blockchair")
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    chain: Mapped[str] = mapped_column(String(20), nullable=True, default="bitcoin")
    token_symbol: Mapped[str] = mapped_column(String(20), nullable=True)


class AddressLabel(Base):
    """Cached address-to-entity resolution results (from APIs and manual lookups)."""
    __tablename__ = "address_labels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    address: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    entity_name: Mapped[str] = mapped_column(String(100), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=True)    # exchange, institution, government, individual, mining_pool
    wallet_type: Mapped[str] = mapped_column(String(20), nullable=True)    # cold, hot, custody, treasury, seized
    source: Mapped[str] = mapped_column(String(50), default="manual")      # walletexplorer, blockchair, manual, api_miss
    confidence: Mapped[float] = mapped_column(Float, default=0.5)          # 0.0 - 1.0
    last_checked: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class ModelFeedback(Base):
    """Aggregated feedback from mock trade outcomes vs AI predictions."""
    __tablename__ = "model_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    period: Mapped[str] = mapped_column(String(20), default="daily")  # daily, weekly
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0)
    direction_accuracy: Mapped[float] = mapped_column(Float, default=0.0)
    avg_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    avg_predicted_rr: Mapped[float] = mapped_column(Float, default=0.0)
    avg_achieved_rr: Mapped[float] = mapped_column(Float, default=0.0)
    avg_pnl_pct: Mapped[float] = mapped_column(Float, default=0.0)
    feedback_json: Mapped[dict] = mapped_column(JSON, nullable=True)


class ApiKey(Base):
    """API keys for monetization."""
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    key_prefix: Mapped[str] = mapped_column(String(20))  # Prefix for identification
    owner: Mapped[str] = mapped_column(String(200))
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=True, index=True)
    tier: Mapped[str] = mapped_column(String(20), default="free")  # free, basic, pro, enterprise
    rate_limit: Mapped[int] = mapped_column(Integer, default=60)  # requests per hour
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class ApiUsageLog(Base):
    """Per-request API usage logging."""
    __tablename__ = "api_usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    api_key_id: Mapped[int] = mapped_column(Integer, nullable=True, index=True)
    endpoint: Mapped[str] = mapped_column(String(200))
    method: Mapped[str] = mapped_column(String(10))
    status_code: Mapped[int] = mapped_column(Integer)
    response_time_ms: Mapped[float] = mapped_column(Float, nullable=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    tier: Mapped[str] = mapped_column(String(20), nullable=True)


class PredictionAnalysis(Base):
    """Detailed post-mortem for each evaluated prediction."""
    __tablename__ = "prediction_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    prediction_id: Mapped[int] = mapped_column(Integer, index=True)
    timeframe: Mapped[str] = mapped_column(String(10))

    # Error metrics
    error_pct: Mapped[float] = mapped_column(Float, nullable=True)
    abs_error_pct: Mapped[float] = mapped_column(Float, nullable=True)
    direction_correct: Mapped[bool] = mapped_column(Boolean, nullable=True)

    # Per-model breakdown
    per_model_results: Mapped[dict] = mapped_column(JSON, nullable=True)  # {model: {predicted, correct, prob}}

    # Market regime at prediction time
    volatility_regime: Mapped[str] = mapped_column(String(20), nullable=True)  # low, normal, high, extreme
    trend_state: Mapped[str] = mapped_column(String(20), nullable=True)        # trending_up, trending_down, ranging
    rsi_at_prediction: Mapped[float] = mapped_column(Float, nullable=True)

    # Feature analysis
    top_features: Mapped[dict] = mapped_column(JSON, nullable=True)  # most influential features

    # Model agreement
    model_agreement_score: Mapped[float] = mapped_column(Float, nullable=True)  # 0-1
    dissenting_models: Mapped[str] = mapped_column(Text, nullable=True)  # comma-separated


class SupportTicket(Base):
    """User bug reports and questions."""
    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="general")  # bug, question, feature, billing, general
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open, in_progress, resolved, closed
    priority: Mapped[str] = mapped_column(String(20), default="normal")  # low, normal, high, urgent
    admin_notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    resolved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class UserFeedback(Base):
    """Thumbs up/down on trades and predictions."""
    __tablename__ = "user_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    feedback_type: Mapped[str] = mapped_column(String(30))  # trade, prediction, signal, general
    reference_id: Mapped[int] = mapped_column(Integer, nullable=True)  # trade_id, prediction_id, etc.
    is_positive: Mapped[bool] = mapped_column(Boolean)
    comment: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())


class MarketingMetrics(Base):
    """Daily snapshot of all business KPIs."""
    __tablename__ = "marketing_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[str] = mapped_column(String(10), unique=True, index=True)  # YYYY-MM-DD
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Users
    total_users: Mapped[int] = mapped_column(Integer, default=0)
    premium_users: Mapped[int] = mapped_column(Integer, default=0)
    trial_users: Mapped[int] = mapped_column(Integer, default=0)
    new_users_today: Mapped[int] = mapped_column(Integer, default=0)
    active_users_24h: Mapped[int] = mapped_column(Integer, default=0)

    # Revenue
    stars_revenue_today: Mapped[int] = mapped_column(Integer, default=0)
    trial_conversions_today: Mapped[int] = mapped_column(Integer, default=0)

    # Predictions
    predictions_made: Mapped[int] = mapped_column(Integer, default=0)
    predictions_correct: Mapped[int] = mapped_column(Integer, default=0)
    accuracy_pct: Mapped[float] = mapped_column(Float, default=0.0)

    # Signals
    signals_generated: Mapped[int] = mapped_column(Integer, default=0)
    signals_profitable: Mapped[int] = mapped_column(Integer, default=0)

    # Support
    tickets_opened: Mapped[int] = mapped_column(Integer, default=0)
    tickets_resolved: Mapped[int] = mapped_column(Integer, default=0)

    # Referrals
    referrals_today: Mapped[int] = mapped_column(Integer, default=0)
    total_referrals: Mapped[int] = mapped_column(Integer, default=0)

    # System
    api_requests: Mapped[int] = mapped_column(Integer, default=0)
    api_errors: Mapped[int] = mapped_column(Integer, default=0)


class GeneratedImage(Base):
    """PNG cache to avoid regenerating charts every request."""
    __tablename__ = "generated_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chart_type: Mapped[str] = mapped_column(String(50), index=True)  # prediction_card, price_chart, etc.
    params_hash: Mapped[str] = mapped_column(String(64), index=True)  # hash of generation params
    image_data: Mapped[bytes] = mapped_column(Text, nullable=True)  # base64 or path
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class CoinOHLCV(Base):
    """OHLCV candlesticks per coin from Binance."""
    __tablename__ = "coin_ohlcv"
    __table_args__ = (
        Index("ix_coin_ohlcv_symbol_interval_ts", "symbol", "interval", "timestamp"),
        Index("ix_coin_ohlcv_coin_timestamp", "coin_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    coin_id: Mapped[str] = mapped_column(String(100), index=True)
    symbol: Mapped[str] = mapped_column(String(20))  # BTCUSDT, ETHUSDT
    interval: Mapped[str] = mapped_column(String(10), default="1h")  # 1m, 5m, 1h, 4h, 1d
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(50), default="binance")


class CoinPrediction(Base):
    """ML predictions per coin."""
    __tablename__ = "coin_predictions"
    __table_args__ = (
        Index("ix_coin_pred_coin_tf_ts", "coin_id", "timeframe", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    coin_id: Mapped[str] = mapped_column(String(100), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    timeframe: Mapped[str] = mapped_column(String(10))  # 1h, 4h, 24h
    direction: Mapped[str] = mapped_column(String(20))  # bullish, bearish, neutral
    confidence: Mapped[float] = mapped_column(Float)
    predicted_price: Mapped[float] = mapped_column(Float, nullable=True)
    predicted_change_pct: Mapped[float] = mapped_column(Float, nullable=True)
    current_price: Mapped[float] = mapped_column(Float)
    actual_price: Mapped[float] = mapped_column(Float, nullable=True)
    actual_direction: Mapped[str] = mapped_column(String(20), nullable=True)
    was_correct: Mapped[bool] = mapped_column(Boolean, nullable=True)
    model_outputs: Mapped[dict] = mapped_column(JSON, nullable=True)
    error_pct: Mapped[float] = mapped_column(Float, nullable=True)


class CoinSignal(Base):
    """Trading signals per coin."""
    __tablename__ = "coin_signals"
    __table_args__ = (
        Index("ix_coin_sig_coin_tf_ts", "coin_id", "timeframe", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    coin_id: Mapped[str] = mapped_column(String(100), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    action: Mapped[str] = mapped_column(String(20))  # strong_buy, buy, hold, sell, strong_sell
    direction: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[float] = mapped_column(Float)
    entry_price: Mapped[float] = mapped_column(Float)
    target_price: Mapped[float] = mapped_column(Float)
    stop_loss: Mapped[float] = mapped_column(Float)
    risk_rating: Mapped[int] = mapped_column(Integer)
    timeframe: Mapped[str] = mapped_column(String(10))
    reasoning: Mapped[str] = mapped_column(Text, nullable=True)


class CoinFeature(Base):
    """Feature vectors per coin."""
    __tablename__ = "coin_features"
    __table_args__ = (
        Index("ix_coin_feat_coin_ts", "coin_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    coin_id: Mapped[str] = mapped_column(String(100), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    feature_data: Mapped[dict] = mapped_column(JSON)


class CoinSentiment(Base):
    """Aggregated sentiment per coin."""
    __tablename__ = "coin_sentiments"
    __table_args__ = (
        Index("ix_coin_sent_coin_ts", "coin_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    coin_id: Mapped[str] = mapped_column(String(100), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    news_sentiment_avg: Mapped[float] = mapped_column(Float, nullable=True)
    news_volume: Mapped[int] = mapped_column(Integer, default=0)
    social_sentiment_avg: Mapped[float] = mapped_column(Float, nullable=True)
    social_volume: Mapped[int] = mapped_column(Integer, default=0)
    reddit_sentiment_avg: Mapped[float] = mapped_column(Float, nullable=True)
    reddit_volume: Mapped[int] = mapped_column(Integer, default=0)
    overall_sentiment: Mapped[float] = mapped_column(Float, nullable=True)


class ExchangeTicker(Base):
    """Cached bid/ask/last per coin per exchange for arbitrage."""
    __tablename__ = "exchange_tickers"
    __table_args__ = (
        Index("ix_exchange_ticker_coin_ex_ts", "coin_id", "exchange", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    coin_id: Mapped[str] = mapped_column(String(100), index=True)
    exchange: Mapped[str] = mapped_column(String(50))
    bid: Mapped[float] = mapped_column(Float, nullable=True)
    ask: Mapped[float] = mapped_column(Float, nullable=True)
    last: Mapped[float] = mapped_column(Float, nullable=True)
    volume_24h: Mapped[float] = mapped_column(Float, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())


class ArbitrageOpportunity(Base):
    """Detected arbitrage opportunities across exchanges."""
    __tablename__ = "arbitrage_opportunities"
    __table_args__ = (
        Index("ix_arb_coin_ts", "coin_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    coin_id: Mapped[str] = mapped_column(String(100), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    buy_exchange: Mapped[str] = mapped_column(String(50))
    buy_price: Mapped[float] = mapped_column(Float)
    sell_exchange: Mapped[str] = mapped_column(String(50))
    sell_price: Mapped[float] = mapped_column(Float)
    spread_pct: Mapped[float] = mapped_column(Float)
    net_profit_pct: Mapped[float] = mapped_column(Float)
    estimated_fees_pct: Mapped[float] = mapped_column(Float, nullable=True)
    is_actionable: Mapped[bool] = mapped_column(Boolean, default=False)
    exchange_prices: Mapped[dict] = mapped_column(JSON, nullable=True)


class NewListing(Base):
    """Detected new coin listings on exchanges."""
    __tablename__ = "new_listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    exchange: Mapped[str] = mapped_column(String(50))
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    listing_type: Mapped[str] = mapped_column(String(30), default="spot")  # spot, futures, innovation
    announcement_url: Mapped[str] = mapped_column(Text, nullable=True)
    price_at_listing: Mapped[float] = mapped_column(Float, nullable=True)
    price_1h_after: Mapped[float] = mapped_column(Float, nullable=True)
    price_24h_after: Mapped[float] = mapped_column(Float, nullable=True)
    change_pct_1h: Mapped[float] = mapped_column(Float, nullable=True)
    change_pct_24h: Mapped[float] = mapped_column(Float, nullable=True)
    was_on_dex_first: Mapped[bool] = mapped_column(Boolean, nullable=True)


class DexToken(Base):
    """DEX tokens tracked for potential CEX listing."""
    __tablename__ = "dex_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    address: Mapped[str] = mapped_column(String(200), index=True)
    chain: Mapped[str] = mapped_column(String(50))  # ethereum, solana, bsc
    symbol: Mapped[str] = mapped_column(String(30), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=True)
    price_usd: Mapped[float] = mapped_column(Float, nullable=True)
    volume_24h: Mapped[float] = mapped_column(Float, nullable=True)
    liquidity: Mapped[float] = mapped_column(Float, nullable=True)
    holder_count: Mapped[int] = mapped_column(Integer, nullable=True)
    is_on_cex: Mapped[bool] = mapped_column(Boolean, default=False)
    boosts: Mapped[int] = mapped_column(Integer, default=0)
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class MemeToken(Base):
    """Memecoins with risk scoring."""
    __tablename__ = "meme_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    address: Mapped[str] = mapped_column(String(200), index=True)
    chain: Mapped[str] = mapped_column(String(50))
    symbol: Mapped[str] = mapped_column(String(30), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=True)
    price_usd: Mapped[float] = mapped_column(Float, nullable=True)
    volume_24h: Mapped[float] = mapped_column(Float, nullable=True)
    liquidity: Mapped[float] = mapped_column(Float, nullable=True)
    volume_acceleration: Mapped[float] = mapped_column(Float, nullable=True)
    rug_pull_score: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    top_holder_pct: Mapped[float] = mapped_column(Float, nullable=True)
    liquidity_locked: Mapped[bool] = mapped_column(Boolean, nullable=True)
    contract_verified: Mapped[bool] = mapped_column(Boolean, nullable=True)
    honeypot_risk: Mapped[bool] = mapped_column(Boolean, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, dead, graduated
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class MultichainOnchain(Base):
    """Per-chain on-chain metrics."""
    __tablename__ = "multichain_onchain"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chain: Mapped[str] = mapped_column(String(50), index=True)  # ethereum, solana, bsc
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    active_addresses: Mapped[int] = mapped_column(Integer, nullable=True)
    tx_count_24h: Mapped[int] = mapped_column(Integer, nullable=True)
    avg_gas_price: Mapped[float] = mapped_column(Float, nullable=True)
    defi_tvl: Mapped[float] = mapped_column(Float, nullable=True)
    stablecoin_volume: Mapped[float] = mapped_column(Float, nullable=True)
    new_contracts_24h: Mapped[int] = mapped_column(Integer, nullable=True)


class InstitutionalHolding(Base):
    """Tracks institutional BTC holdings from BitcoinTreasuries and SEC EDGAR."""
    __tablename__ = "institutional_holdings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_name: Mapped[str] = mapped_column(String(200))
    ticker: Mapped[str] = mapped_column(String(20), nullable=True)
    country: Mapped[str] = mapped_column(String(50), nullable=True)
    total_btc: Mapped[float] = mapped_column(Float)
    entry_value_usd: Mapped[float] = mapped_column(Float, nullable=True)
    current_value_usd: Mapped[float] = mapped_column(Float, nullable=True)
    change_btc: Mapped[float] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="bitcointreasuries")
    snapshot_date: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class Partner(Base):
    """Partner referral accounts for commission-based partnerships."""
    __tablename__ = "partners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200))
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    contact_email: Mapped[str] = mapped_column(String(200), nullable=True)
    contact_telegram: Mapped[str] = mapped_column(String(100), nullable=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=True, unique=True, index=True)
    commission_pct: Mapped[float] = mapped_column(Float, default=20.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    created_by: Mapped[int] = mapped_column(BigInteger, default=0)
    notes: Mapped[str] = mapped_column(Text, nullable=True)


class PartnerReferral(Base):
    """Tracks users referred by partners and their conversion/commission status."""
    __tablename__ = "partner_referrals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    partner_id: Mapped[int] = mapped_column(Integer, index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    signed_up_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    subscribed: Mapped[bool] = mapped_column(Boolean, default=False)
    subscription_tier: Mapped[str] = mapped_column(String(20), nullable=True)
    subscription_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    stars_paid: Mapped[int] = mapped_column(Integer, nullable=True)
    commission_amount: Mapped[float] = mapped_column(Float, nullable=True)
    commission_paid: Mapped[bool] = mapped_column(Boolean, default=False)


class LearnedPattern(Base):
    """Patterns discovered from error analysis for self-learning."""
    __tablename__ = "learned_patterns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Pattern definition
    pattern_type: Mapped[str] = mapped_column(String(50), index=True)  # model_disagreement, volatility_regime, feature_threshold, confidence_calibration, time_pattern
    timeframe: Mapped[str] = mapped_column(String(10), nullable=True)
    description: Mapped[str] = mapped_column(Text)

    # Machine-readable conditions
    conditions: Mapped[dict] = mapped_column(JSON)  # e.g. {"rsi_gt": 75, "direction": "bullish"}

    # Statistics
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    accuracy_when_pattern: Mapped[float] = mapped_column(Float, nullable=True)  # accuracy when pattern is active
    accuracy_when_not_pattern: Mapped[float] = mapped_column(Float, nullable=True)

    # Adjustments to apply
    confidence_modifier: Mapped[float] = mapped_column(Float, default=1.0)  # < 1.0 = reduce confidence
    direction_bias: Mapped[float] = mapped_column(Float, default=0.0)  # adjustment to bullish_prob

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class PriceAlert(Base):
    """User-defined price alerts for any tracked coin."""
    __tablename__ = "price_alerts"
    __table_args__ = (
        Index("ix_price_alerts_user_active", "telegram_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    coin_id: Mapped[str] = mapped_column(String(100), default="bitcoin")
    target_price: Mapped[float] = mapped_column(Float)
    direction: Mapped[str] = mapped_column(String(10))  # above, below
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_repeating: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    triggered_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    triggered_price: Mapped[float] = mapped_column(Float, nullable=True)


class DailyBriefing(Base):
    """AI-generated daily market briefing."""
    __tablename__ = "daily_briefings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[str] = mapped_column(String(10), unique=True, index=True)  # YYYY-MM-DD
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    summary_html: Mapped[str] = mapped_column(Text)
    summary_text: Mapped[str] = mapped_column(Text)
    data_snapshot: Mapped[dict] = mapped_column(JSON, nullable=True)
    btc_price: Mapped[float] = mapped_column(Float, nullable=True)
    btc_24h_change: Mapped[float] = mapped_column(Float, nullable=True)
    overall_sentiment: Mapped[str] = mapped_column(String(20), nullable=True)  # bullish, bearish, neutral
    confidence: Mapped[float] = mapped_column(Float, nullable=True)
    generation_method: Mapped[str] = mapped_column(String(30), default="template")


class UserPrediction(Base):
    """User predictions for the prediction game."""
    __tablename__ = "user_predictions"
    __table_args__ = (
        UniqueConstraint("telegram_id", "round_date", "timeframe", name="uq_user_prediction_round"),
        Index("ix_user_pred_user_ts", "telegram_id", "timestamp"),
        Index("ix_user_pred_round", "round_date", "timeframe"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    round_date: Mapped[str] = mapped_column(String(10))  # YYYY-MM-DD
    timeframe: Mapped[str] = mapped_column(String(10), default="24h")  # 24h, 4h, 1h
    direction: Mapped[str] = mapped_column(String(10))  # up, down
    lock_price: Mapped[float] = mapped_column(Float)
    resolve_price: Mapped[float] = mapped_column(Float, nullable=True)
    was_correct: Mapped[bool] = mapped_column(Boolean, nullable=True)
    points_earned: Mapped[int] = mapped_column(Integer, nullable=True)
    streak_at_prediction: Mapped[int] = mapped_column(Integer, default=0)
    multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, resolved


class GameProfile(Base):
    """Leaderboard profile for the prediction game."""
    __tablename__ = "game_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=True)
    total_points: Mapped[int] = mapped_column(Integer, default=0)
    total_predictions: Mapped[int] = mapped_column(Integer, default=0)
    correct_predictions: Mapped[int] = mapped_column(Integer, default=0)
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    best_streak: Mapped[int] = mapped_column(Integer, default=0)
    accuracy_pct: Mapped[float] = mapped_column(Float, default=0.0)
    weekly_points: Mapped[int] = mapped_column(Integer, default=0)
    monthly_points: Mapped[int] = mapped_column(Integer, default=0)
    weekly_reset_date: Mapped[str] = mapped_column(String(10), nullable=True)
    monthly_reset_date: Mapped[str] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


def _add_missing_columns(connection):
    """Add any columns defined in models but missing from existing tables (works on both SQLite and PostgreSQL)."""
    inspector = inspect(connection)
    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            continue  # Table doesn't exist yet — create_all will handle it
        existing_cols = {c["name"] for c in inspector.get_columns(table.name)}
        for col in table.columns:
            if col.name not in existing_cols:
                col_type = col.type.compile(connection.dialect)
                if col.nullable:
                    nullable = "NULL"
                else:
                    # Use dialect-appropriate defaults for NOT NULL columns
                    type_str = str(col_type).upper()
                    if any(t in type_str for t in ("INT", "FLOAT", "REAL", "NUMERIC", "DOUBLE")):
                        nullable = "NOT NULL DEFAULT 0"
                    elif "BOOL" in type_str:
                        nullable = "NOT NULL DEFAULT false"
                    else:
                        nullable = "NOT NULL DEFAULT ''"
                try:
                    connection.execute(
                        text(f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {col_type} {nullable}')
                    )
                    _db_logger.info(f"Added missing column: {table.name}.{col.name} ({col_type})")
                except Exception as e:
                    _db_logger.debug(f"Column add skipped {table.name}.{col.name}: {e}")


async def init_db():
    _db_logger.info(f"Connecting to database: {engine.url!s}")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.run_sync(_add_missing_columns)
        _db_logger.info("Database tables ready")
    except Exception as e:
        _db_logger.error(f"Database init failed: {e}", exc_info=True)
        raise


async def get_session() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
