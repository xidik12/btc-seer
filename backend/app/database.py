import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Text, Float, Integer, String, JSON, DateTime, Boolean, func, text, inspect
from datetime import datetime

_db_logger = logging.getLogger(__name__)

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Price(Base):
    __tablename__ = "prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(50), default="binance")


class News(Base):
    __tablename__ = "news"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    source: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text, nullable=True)
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=True)
    raw_sentiment: Mapped[str] = mapped_column(String(20), nullable=True)


class Feature(Base):
    __tablename__ = "features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    feature_data: Mapped[dict] = mapped_column(JSON)


class Prediction(Base):
    __tablename__ = "predictions"

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


class Signal(Base):
    __tablename__ = "signals"

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
    fear_greed_index: Mapped[int] = mapped_column(Integer, nullable=True)
    fear_greed_label: Mapped[str] = mapped_column(String(30), nullable=True)


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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    influencer_name: Mapped[str] = mapped_column(String(100))
    username: Mapped[str] = mapped_column(String(100), index=True)
    role: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(50))  # ceo, investor, analyst, etc.
    weight: Mapped[int] = mapped_column(Integer)  # Influence weight 1-10
    text: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text, nullable=True)
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=True)
    published_at: Mapped[str] = mapped_column(String(100), nullable=True)


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
    next_funding_time: Mapped[int] = mapped_column(Integer, nullable=True)  # Unix ms
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
    telegram_id: Mapped[int] = mapped_column(Integer, index=True)
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
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=True)
    subscribed: Mapped[bool] = mapped_column(Boolean, default=True)
    alert_interval: Mapped[str] = mapped_column(String(10), default="1h")  # 1h, 4h, 24h
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Subscription fields
    subscription_tier: Mapped[str] = mapped_column(String(20), nullable=True, default="free")
    trial_end: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    subscription_end: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    stars_payment_id: Mapped[str] = mapped_column(String(200), nullable=True)

    # Admin / ban
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    ban_reason: Mapped[str] = mapped_column(String(500), nullable=True)


class PortfolioState(Base):
    """Tracks user portfolio balance, risk settings, and trading stats."""
    __tablename__ = "portfolio_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(Integer, index=True)
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
    telegram_id: Mapped[int] = mapped_column(Integer, index=True)
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


class ApiKey(Base):
    """API keys for monetization."""
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    key_prefix: Mapped[str] = mapped_column(String(8))  # First 8 chars for identification
    owner: Mapped[str] = mapped_column(String(200))
    telegram_id: Mapped[int] = mapped_column(Integer, nullable=True, index=True)
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


def _add_missing_columns(connection):
    """Add any columns defined in models but missing from existing SQLite tables."""
    inspector = inspect(connection)
    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            continue  # Table doesn't exist yet — create_all will handle it
        existing_cols = {c["name"] for c in inspector.get_columns(table.name)}
        for col in table.columns:
            if col.name not in existing_cols:
                col_type = col.type.compile(connection.dialect)
                nullable = "NULL" if col.nullable else "NOT NULL DEFAULT ''"
                if col.nullable:
                    nullable = "NULL"
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
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_add_missing_columns)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
