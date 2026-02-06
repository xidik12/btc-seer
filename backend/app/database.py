from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Text, Float, Integer, String, JSON, DateTime, Boolean, func
from datetime import datetime

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

    # Evaluation (filled later)
    actual_price_1h: Mapped[float] = mapped_column(Float, nullable=True)
    actual_price_24h: Mapped[float] = mapped_column(Float, nullable=True)
    was_correct_1h: Mapped[bool] = mapped_column(Boolean, nullable=True)
    was_correct_24h: Mapped[bool] = mapped_column(Boolean, nullable=True)


class BotUser(Base):
    __tablename__ = "bot_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=True)
    subscribed: Mapped[bool] = mapped_column(Boolean, default=True)
    alert_interval: Mapped[str] = mapped_column(String(10), default="1h")  # 1h, 4h, 24h
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
