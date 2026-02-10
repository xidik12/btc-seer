import logging
import time
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, Price, MacroData, OnChainData, FundingRate, BtcDominance, IndicatorSnapshot
from app.collectors.market import MarketCollector
from app.collectors.onchain import OnChainCollector
from app.collectors.macro import MacroCollector

logger = logging.getLogger(__name__)

# ── Simple TTL cache for expensive endpoints ──
_cache: dict[str, tuple[dict, float]] = {}


def _get_cached(key: str) -> dict | None:
    if key in _cache:
        data, expires = _cache[key]
        if time.monotonic() < expires:
            return data
        del _cache[key]
    return None


def _set_cache(key: str, data: dict, ttl: int) -> None:
    _cache[key] = (data, time.monotonic() + ttl)

router = APIRouter(prefix="/api/market", tags=["market"])

# Shared collectors for live API fallback
_market_collector = MarketCollector()
_onchain_collector = OnChainCollector()
_macro_collector = MacroCollector()

# Minimum candles needed per timeframe to consider local data sufficient
_MIN_CANDLES = {"1m": 2, "5m": 2, "15m": 2, "1h": 5, "4h": 5, "1d": 10, "1w": 20, "1mo": 20, "1y": 50, "all": 50}

# Binance interval + limit for each timeframe (used as fallback)
_BINANCE_FALLBACK = {
    "1d": ("1h", 24),
    "1w": ("1h", 168),
    "1mo": ("4h", 180),
    "1y": ("1d", 365),
    "all": ("1d", 1000),
}


@router.get("/price")
async def get_current_price(session: AsyncSession = Depends(get_session)):
    """Get latest BTC price data."""
    result = await session.execute(
        select(Price).order_by(desc(Price.timestamp)).limit(1)
    )
    price = result.scalar_one_or_none()

    if not price:
        return {"price": None, "message": "No price data available"}

    # Get 24h ago price for change calculation
    yesterday = price.timestamp - timedelta(hours=24)
    result_24h = await session.execute(
        select(Price)
        .where(Price.timestamp <= yesterday)
        .order_by(desc(Price.timestamp))
        .limit(1)
    )
    price_24h = result_24h.scalar_one_or_none()

    change_24h = None
    change_24h_pct = None
    if price_24h:
        change_24h = price.close - price_24h.close
        change_24h_pct = (change_24h / price_24h.close) * 100

    return {
        "price": price.close,
        "open": price.open,
        "high": price.high,
        "low": price.low,
        "volume": price.volume,
        "change_24h": round(change_24h, 2) if change_24h else None,
        "change_24h_pct": round(change_24h_pct, 2) if change_24h_pct else None,
        "timestamp": price.timestamp.isoformat(),
    }


@router.get("/stats")
async def get_price_stats(
    timeframe: str = Query("1d", pattern="^(1m|5m|15m|1h|4h|1d|1w|1mo|1y|all)$"),
    session: AsyncSession = Depends(get_session),
):
    """Get price statistics for a specific timeframe.

    Timeframes: 1m, 5m, 15m, 1h, 4h, 1d (day), 1w (week), 1mo (month), 1y (year), all (lifetime)
    """
    cached = _get_cached(f"stats:{timeframe}")
    if cached is not None:
        return cached

    # Map timeframe to timedelta
    timeframe_map = {
        "1m": timedelta(minutes=1),
        "5m": timedelta(minutes=5),
        "15m": timedelta(minutes=15),
        "1h": timedelta(hours=1),
        "4h": timedelta(hours=4),
        "1d": timedelta(days=1),
        "1w": timedelta(weeks=1),
        "1mo": timedelta(days=30),
        "1y": timedelta(days=365),
        "all": None,  # All time
    }

    # Get current price
    result_current = await session.execute(
        select(Price).order_by(desc(Price.timestamp)).limit(1)
    )
    current = result_current.scalar_one_or_none()

    if not current:
        return {"error": "No price data available"}

    # Get historical data for timeframe
    delta = timeframe_map[timeframe]
    if delta:
        since = current.timestamp - delta
        result_historical = await session.execute(
            select(Price)
            .where(Price.timestamp >= since)
            .order_by(Price.timestamp)
        )
    else:
        # All time
        result_historical = await session.execute(
            select(Price).order_by(Price.timestamp)
        )

    prices = result_historical.scalars().all()

    min_needed = _MIN_CANDLES.get(timeframe, 5)

    # Fallback to Binance API if local data is insufficient
    if len(prices) < min_needed and timeframe in _BINANCE_FALLBACK:
        logger.info(f"Stats: Local data insufficient ({len(prices)} candles) for {timeframe}, fetching from Binance")
        try:
            binance_interval, binance_limit = _BINANCE_FALLBACK[timeframe]
            klines = await _market_collector.get_historical_klines(
                interval=binance_interval, limit=binance_limit
            )
            if klines and len(klines) > min_needed:
                current_price = current.close
                first_k = klines[0]
                open_price = first_k["open"]
                high_price = max(k["high"] for k in klines)
                low_price = min(k["low"] for k in klines)
                total_volume = sum(k["volume"] for k in klines)
                last_k = klines[-1]

                price_change = last_k["close"] - open_price
                price_change_pct = (price_change / open_price * 100) if open_price else 0

                max_candles = 500
                step = max(1, len(klines) // max_candles)
                candles = [
                    {
                        "timestamp": k["timestamp"].isoformat() if hasattr(k["timestamp"], "isoformat") else str(k["timestamp"]),
                        "open": k["open"],
                        "high": k["high"],
                        "low": k["low"],
                        "close": k["close"],
                        "volume": k["volume"],
                    }
                    for k in klines[::step]
                ]

                result = {
                    "timeframe": timeframe,
                    "current_price": current_price,
                    "open": open_price,
                    "high": high_price,
                    "low": low_price,
                    "volume": total_volume,
                    "change": round(price_change, 2),
                    "change_pct": round(price_change_pct, 2),
                    "num_candles": len(klines),
                    "candles": candles,
                    "timestamp": current.timestamp.isoformat(),
                    "period_start": candles[0]["timestamp"],
                    "period_end": candles[-1]["timestamp"],
                    "source": "binance_api",
                }
                _set_cache(f"stats:{timeframe}", result, 30)
                return result
        except Exception as e:
            logger.warning(f"Binance fallback failed: {e}")

    if not prices:
        return {"error": "No historical data available"}

    # Calculate stats from local DB data
    first_price = prices[0]
    current_price = current.close
    open_price = first_price.close
    high_price = max(p.high for p in prices)
    low_price = min(p.low for p in prices)
    total_volume = sum(p.volume for p in prices)

    price_change = current_price - open_price
    price_change_pct = (price_change / open_price * 100) if open_price else 0

    # Get candle data for chart (limit to reasonable number of points)
    max_candles = 1000
    step = max(1, len(prices) // max_candles)
    candles = [
        {
            "timestamp": p.timestamp.isoformat(),
            "open": p.open,
            "high": p.high,
            "low": p.low,
            "close": p.close,
            "volume": p.volume,
        }
        for p in prices[::step]
    ]

    result = {
        "timeframe": timeframe,
        "current_price": current_price,
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "volume": total_volume,
        "change": round(price_change, 2),
        "change_pct": round(price_change_pct, 2),
        "num_candles": len(prices),
        "candles": candles,
        "timestamp": current.timestamp.isoformat(),
        "period_start": first_price.timestamp.isoformat(),
        "period_end": current.timestamp.isoformat(),
    }
    _set_cache(f"stats:{timeframe}", result, 30)
    return result


@router.get("/indicators")
async def get_indicators(
    session: AsyncSession = Depends(get_session),
):
    """Get current technical indicators calculated from recent price data."""
    cached = _get_cached("indicators")
    if cached is not None:
        return cached

    import pandas as pd
    from app.features.technical import TechnicalFeatures

    # Need at least 350 candles for long SMAs
    since = datetime.utcnow() - timedelta(hours=400)
    result = await session.execute(
        select(Price).where(Price.timestamp >= since).order_by(Price.timestamp)
    )
    prices = result.scalars().all()

    if len(prices) < 30:
        return {"error": "Not enough price data for indicators", "candle_count": len(prices)}

    df = pd.DataFrame([
        {"open": p.open, "high": p.high, "low": p.low, "close": p.close, "volume": p.volume}
        for p in prices
    ])

    df = TechnicalFeatures.calculate_all(df)

    # Get latest row
    latest = df.iloc[-1]

    def safe(val):
        if pd.isna(val):
            return None
        return round(float(val), 4)

    current_price = safe(latest["close"])

    # Fetch BTC dominance
    btc_dom = None
    try:
        btc_dom = await _market_collector.get_btc_dominance()
    except Exception:
        pass

    result = {
        "timestamp": prices[-1].timestamp.isoformat(),
        "current_price": current_price,
        "candle_count": len(prices),
        "btc_dominance": btc_dom,
        "moving_averages": {
            "ema_9": safe(latest.get("ema_9")),
            "ema_21": safe(latest.get("ema_21")),
            "ema_50": safe(latest.get("ema_50")),
            "ema_200": safe(latest.get("ema_200")),
            "sma_20": safe(latest.get("sma_20")),
            "sma_111": safe(latest.get("sma_111")),
            "sma_200": safe(latest.get("sma_200")),
            "sma_350": safe(latest.get("sma_350")),
        },
        "momentum": {
            "rsi": safe(latest.get("rsi")),
            "rsi_7": safe(latest.get("rsi_7")),
            "rsi_30": safe(latest.get("rsi_30")),
            "macd": safe(latest.get("macd")),
            "macd_signal": safe(latest.get("macd_signal")),
            "macd_histogram": safe(latest.get("macd_hist")),
            "adx": safe(latest.get("adx")),
            "momentum_10": safe(latest.get("momentum_10")),
            "momentum_20": safe(latest.get("momentum_20")),
            "roc_1": safe(latest.get("roc_1")),
            "roc_6": safe(latest.get("roc_6")),
            "roc_12": safe(latest.get("roc_12")),
            "roc_24": safe(latest.get("roc_24")),
        },
        "volatility": {
            "bb_upper": safe(latest.get("bb_upper")),
            "bb_middle": safe(latest.get("bb_middle")),
            "bb_lower": safe(latest.get("bb_lower")),
            "bb_width": safe(latest.get("bb_width")),
            "bb_position": safe(latest.get("bb_position")),
            "atr": safe(latest.get("atr")),
            "volatility_24h": safe(latest.get("volatility_24h")),
        },
        "volume": {
            "obv": safe(latest.get("obv")),
            "vwap": safe(latest.get("vwap")),
            "volume_sma_20": safe(latest.get("volume_sma_20")),
            "volume_ratio": safe(latest.get("volume_ratio")),
        },
        "levels": {
            "pivot": safe(latest.get("pivot")),
            "support_1": safe(latest.get("support_1")),
            "resistance_1": safe(latest.get("resistance_1")),
        },
        "advanced": {
            "mayer_multiple": safe(latest.get("mayer_multiple")),
            "pi_cycle_ratio": safe(latest.get("pi_cycle_ratio")),
            "ema_cross": safe(latest.get("ema_cross")),
            "zscore_20": safe(latest.get("zscore_20")),
            "price_vs_ema9": safe(latest.get("price_vs_ema9")),
            "price_vs_ema21": safe(latest.get("price_vs_ema21")),
            "price_vs_ema50": safe(latest.get("price_vs_ema50")),
        },
        "candle": {
            "body_size": safe(latest.get("body_size")),
            "upper_shadow": safe(latest.get("upper_shadow")),
            "lower_shadow": safe(latest.get("lower_shadow")),
        },
        "stochastic_rsi": {
            "k": safe(latest.get("stoch_rsi_k")),
            "d": safe(latest.get("stoch_rsi_d")),
        },
        "williams_r": safe(latest.get("williams_r")),
        "ichimoku": {
            "tenkan": safe(latest.get("ichimoku_tenkan")),
            "kijun": safe(latest.get("ichimoku_kijun")),
            "senkou_a": safe(latest.get("ichimoku_senkou_a")),
            "senkou_b": safe(latest.get("ichimoku_senkou_b")),
        },
        "candlestick_patterns": {
            "doji": int(latest.get("candle_doji", 0)),
            "hammer": int(latest.get("candle_hammer", 0)),
            "inverted_hammer": int(latest.get("candle_inverted_hammer", 0)),
            "bullish_engulfing": int(latest.get("candle_bullish_engulfing", 0)),
            "bearish_engulfing": int(latest.get("candle_bearish_engulfing", 0)),
            "morning_star": int(latest.get("candle_morning_star", 0)),
            "evening_star": int(latest.get("candle_evening_star", 0)),
        },
        "trend": {
            "short_term": int(latest.get("trend_short", 0)),
            "medium_term": int(latest.get("trend_medium", 0)),
            "long_term": int(latest.get("trend_long", 0)),
        },
    }
    _set_cache("indicators", result, 60)
    return result


@router.get("/candles")
async def get_candles(
    hours: int = Query(168, ge=1, le=720),
    session: AsyncSession = Depends(get_session),
):
    """Get historical candle data."""
    since = datetime.utcnow() - timedelta(hours=hours)

    result = await session.execute(
        select(Price)
        .where(Price.timestamp >= since)
        .order_by(Price.timestamp)
    )
    prices = result.scalars().all()

    return {
        "count": len(prices),
        "candles": [
            {
                "timestamp": p.timestamp.isoformat(),
                "open": p.open,
                "high": p.high,
                "low": p.low,
                "close": p.close,
                "volume": p.volume,
            }
            for p in prices
        ],
    }


@router.get("/macro")
async def get_macro_data(session: AsyncSession = Depends(get_session)):
    """Get latest macro market data with price changes."""
    cached = _get_cached("macro")
    if cached is not None:
        return cached

    macro = None
    try:
        result = await session.execute(
            select(MacroData).order_by(desc(MacroData.timestamp)).limit(1)
        )
        macro = result.scalar_one_or_none()
    except Exception as e:
        logger.warning(f"Macro DB query failed: {e}")

    if not macro:
        # Live fallback: fetch directly from APIs when DB is empty
        try:
            live = await _macro_collector.collect()
            return {
                "dxy": live.get("dxy"),
                "gold": live.get("gold"),
                "sp500": live.get("sp500"),
                "treasury_10y": live.get("treasury_10y"),
                "nasdaq": live.get("nasdaq"),
                "vix": live.get("vix"),
                "eurusd": live.get("eurusd"),
                "fear_greed_index": None,
                "fear_greed_label": None,
                "timestamp": live.get("timestamp"),
            }
        except Exception as e:
            logger.warning(f"Live macro fallback failed: {e}")
            return {
                "dxy": None, "gold": None, "sp500": None, "treasury_10y": None,
                "nasdaq": None, "vix": None, "eurusd": None,
                "fear_greed_index": None, "fear_greed_label": None, "timestamp": None,
            }

    # Get macro data from ~1 hour ago for change calculation
    prev_result = await session.execute(
        select(MacroData)
        .where(MacroData.timestamp <= macro.timestamp - timedelta(minutes=50))
        .order_by(desc(MacroData.timestamp))
        .limit(1)
    )
    prev_macro = prev_result.scalar_one_or_none()

    # Get macro data from ~24 hours ago for daily change
    daily_result = await session.execute(
        select(MacroData)
        .where(MacroData.timestamp <= macro.timestamp - timedelta(hours=23))
        .order_by(desc(MacroData.timestamp))
        .limit(1)
    )
    daily_macro = daily_result.scalar_one_or_none()

    def build_macro_item(current_val, prev_val, daily_val):
        """Build macro item with price and change data."""
        if current_val is None:
            return None
        item = {"price": current_val}
        if prev_val and prev_val > 0:
            item["change_1h"] = round((current_val - prev_val) / prev_val * 100, 4)
        if daily_val and daily_val > 0:
            item["change_24h"] = round((current_val - daily_val) / daily_val * 100, 4)
        return item

    result = {
        "dxy": build_macro_item(
            macro.dxy,
            prev_macro.dxy if prev_macro else None,
            daily_macro.dxy if daily_macro else None,
        ),
        "gold": build_macro_item(
            macro.gold,
            prev_macro.gold if prev_macro else None,
            daily_macro.gold if daily_macro else None,
        ),
        "sp500": build_macro_item(
            macro.sp500,
            prev_macro.sp500 if prev_macro else None,
            daily_macro.sp500 if daily_macro else None,
        ),
        "treasury_10y": build_macro_item(
            macro.treasury_10y,
            prev_macro.treasury_10y if prev_macro else None,
            daily_macro.treasury_10y if daily_macro else None,
        ),
        "nasdaq": build_macro_item(
            macro.nasdaq,
            prev_macro.nasdaq if prev_macro else None,
            daily_macro.nasdaq if daily_macro else None,
        ),
        "vix": build_macro_item(
            macro.vix,
            prev_macro.vix if prev_macro else None,
            daily_macro.vix if daily_macro else None,
        ),
        "eurusd": build_macro_item(
            macro.eurusd,
            prev_macro.eurusd if prev_macro else None,
            daily_macro.eurusd if daily_macro else None,
        ),
        "fear_greed_index": macro.fear_greed_index,
        "fear_greed_label": macro.fear_greed_label,
        "timestamp": macro.timestamp.isoformat(),
    }
    _set_cache("macro", result, 300)
    return result


@router.get("/onchain")
async def get_onchain_data(session: AsyncSession = Depends(get_session)):
    """Get latest on-chain metrics."""
    cached = _get_cached("onchain")
    if cached is not None:
        return cached

    onchain = None
    try:
        result = await session.execute(
            select(OnChainData).order_by(desc(OnChainData.timestamp)).limit(1)
        )
        onchain = result.scalar_one_or_none()
    except Exception as e:
        logger.warning(f"OnChain DB query failed: {e}")

    if not onchain:
        # Live fallback: fetch directly from blockchain APIs when DB is empty
        try:
            live = await _onchain_collector.collect()
            return {
                "hash_rate": live.get("hash_rate"),
                "difficulty": live.get("difficulty"),
                "mempool_size": live.get("mempool_size"),
                "mempool_fees": live.get("mempool_fees"),
                "tx_volume": live.get("tx_volume"),
                "active_addresses": live.get("active_addresses"),
                "exchange_reserve": live.get("exchange_reserve"),
                "reserve_change_24h": None,
                "large_tx_count": live.get("large_tx_count"),
                "timestamp": live.get("timestamp"),
            }
        except Exception as e:
            logger.warning(f"Live onchain fallback failed: {e}")
            return {"onchain": None, "message": "No on-chain data available"}

    # Compute 24h reserve change
    reserve_change_24h = None
    if onchain.exchange_reserve is not None:
        prev_result = await session.execute(
            select(OnChainData)
            .where(OnChainData.timestamp <= onchain.timestamp - timedelta(hours=23))
            .order_by(desc(OnChainData.timestamp))
            .limit(1)
        )
        prev = prev_result.scalar_one_or_none()
        if prev and prev.exchange_reserve and prev.exchange_reserve > 0:
            reserve_change_24h = round(
                (onchain.exchange_reserve - prev.exchange_reserve) / prev.exchange_reserve * 100, 2
            )

    result = {
        "hash_rate": onchain.hash_rate,
        "difficulty": onchain.difficulty,
        "mempool_size": onchain.mempool_size,
        "mempool_fees": onchain.mempool_fees,
        "tx_volume": onchain.tx_volume,
        "active_addresses": onchain.active_addresses,
        "exchange_reserve": onchain.exchange_reserve,
        "reserve_change_24h": reserve_change_24h,
        "large_tx_count": onchain.large_tx_count,
        "timestamp": onchain.timestamp.isoformat(),
    }
    _set_cache("onchain", result, 300)
    return result


@router.get("/funding")
async def get_funding_data(
    hours: int = Query(168, ge=1, le=720),
    session: AsyncSession = Depends(get_session),
):
    """Get historical funding rate and open interest data."""
    cached = _get_cached(f"funding:{hours}")
    if cached is not None:
        return cached

    since = datetime.utcnow() - timedelta(hours=hours)

    result = await session.execute(
        select(FundingRate)
        .where(FundingRate.timestamp >= since)
        .order_by(FundingRate.timestamp)
    )
    records = result.scalars().all()

    if not records:
        return {"funding": None, "message": "No funding data available"}

    latest = records[-1]

    result = {
        "current": {
            "funding_rate": latest.funding_rate,
            "mark_price": latest.mark_price,
            "index_price": latest.index_price,
            "open_interest": latest.open_interest,
            "timestamp": latest.timestamp.isoformat(),
        },
        "history": [
            {
                "timestamp": r.timestamp.isoformat(),
                "funding_rate": r.funding_rate,
                "open_interest": r.open_interest,
            }
            for r in records
        ],
        "count": len(records),
    }
    _set_cache(f"funding:{hours}", result, 120)
    return result


@router.get("/dominance")
async def get_dominance_data(
    days: int = Query(30, ge=1, le=180),
    session: AsyncSession = Depends(get_session),
):
    """Get historical BTC dominance data."""
    cached = _get_cached(f"dominance:{days}")
    if cached is not None:
        return cached

    since = datetime.utcnow() - timedelta(days=days)

    records = []
    try:
        result = await session.execute(
            select(BtcDominance)
            .where(BtcDominance.timestamp >= since)
            .order_by(BtcDominance.timestamp)
        )
        records = result.scalars().all()
    except Exception as e:
        logger.warning(f"Dominance DB query failed: {e}")

    if not records:
        # Live fallback: fetch directly from CoinGecko when DB is empty
        try:
            live = await _market_collector.get_btc_dominance()
            if live:
                return {
                    "current": {
                        "btc_dominance": live.get("btc_dominance"),
                        "eth_dominance": live.get("eth_dominance"),
                        "total_market_cap": live.get("total_market_cap"),
                        "total_volume": live.get("total_volume"),
                        "market_cap_change_24h": live.get("market_cap_change_24h"),
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                    "history": [],
                    "count": 0,
                }
        except Exception as e:
            logger.warning(f"Live dominance fallback failed: {e}")
        return {"dominance": None, "message": "No dominance data available"}

    latest = records[-1]

    result = {
        "current": {
            "btc_dominance": latest.btc_dominance,
            "eth_dominance": latest.eth_dominance,
            "total_market_cap": latest.total_market_cap,
            "total_volume": latest.total_volume,
            "market_cap_change_24h": latest.market_cap_change_24h,
            "timestamp": latest.timestamp.isoformat(),
        },
        "history": [
            {
                "timestamp": r.timestamp.isoformat(),
                "btc_dominance": r.btc_dominance,
                "eth_dominance": r.eth_dominance,
                "total_market_cap": r.total_market_cap,
            }
            for r in records
        ],
        "count": len(records),
    }
    _set_cache(f"dominance:{days}", result, 300)
    return result


@router.get("/fear-greed")
async def get_fear_greed(
    days: int = Query(30, ge=1, le=365),
):
    """Get Fear & Greed Index from alternative.me (free API)."""
    cached = _get_cached(f"fear_greed:{days}")
    if cached is not None:
        return cached

    import aiohttp

    url = f"https://api.alternative.me/fng/?limit={days}&format=json"
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return {"error": "Failed to fetch Fear & Greed data"}
                raw = await resp.json(content_type=None)

        data_list = raw.get("data", [])
        if not data_list:
            return {"current": None, "history": []}

        current = data_list[0]
        history = [
            {
                "value": int(d["value"]),
                "label": d["value_classification"],
                "timestamp": int(d["timestamp"]),
            }
            for d in data_list
        ]

        result = {
            "current": {
                "value": int(current["value"]),
                "label": current["value_classification"],
                "timestamp": int(current["timestamp"]),
            },
            "history": history,
        }
        _set_cache(f"fear_greed:{days}", result, 300)
        return result
    except Exception as e:
        logger.warning(f"Fear & Greed fetch failed: {e}")
        return {"current": None, "history": [], "error": str(e)}


@router.get("/indicator-history")
async def get_indicator_history(
    hours: int = Query(168, ge=1, le=720),
    session: AsyncSession = Depends(get_session),
):
    """Get historical indicator snapshots for trend analysis."""
    since = datetime.utcnow() - timedelta(hours=hours)

    result = await session.execute(
        select(IndicatorSnapshot)
        .where(IndicatorSnapshot.timestamp >= since)
        .order_by(IndicatorSnapshot.timestamp)
    )
    snapshots = result.scalars().all()

    if not snapshots:
        return {"snapshots": [], "count": 0}

    return {
        "snapshots": [
            {
                "timestamp": s.timestamp.isoformat(),
                "price": s.price,
                "indicators": s.indicators,
            }
            for s in snapshots
        ],
        "count": len(snapshots),
    }


@router.get("/supply")
async def get_btc_supply():
    """Get Bitcoin supply data: total mined, remaining, halving info, milestones."""
    cached = _get_cached("supply")
    if cached is not None:
        return cached

    import aiohttp

    MAX_SUPPLY = 21_000_000
    BLOCK_REWARD = 3.125
    BLOCKS_PER_DAY = 144
    NEXT_HALVING_BLOCK = 1_050_000

    # Defaults
    total_mined = 19_800_000
    current_block_height = None
    blocks_until_halving = None

    # Fetch live data from blockchain.info
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.get(
                "https://api.blockchain.info/stats",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    stats = await resp.json(content_type=None)
                    total_btc = stats.get("totalbc", 0) / 1e8
                    if total_btc > 0:
                        total_mined = total_btc
                    n_blocks = stats.get("n_blocks_total", 0)
                    if n_blocks > 0:
                        current_block_height = n_blocks
                        blocks_until_halving = max(0, NEXT_HALVING_BLOCK - n_blocks)
    except Exception as e:
        logger.debug(f"blockchain.info supply fetch error: {e}")

    remaining = MAX_SUPPLY - total_mined
    percent_mined = round(total_mined / MAX_SUPPLY * 100, 2)
    btc_mined_per_day = BLOCKS_PER_DAY * BLOCK_REWARD

    result = {
        "total_mined": round(total_mined, 2),
        "max_supply": MAX_SUPPLY,
        "remaining": round(remaining, 2),
        "percent_mined": percent_mined,
        "block_reward": BLOCK_REWARD,
        "blocks_per_day": BLOCKS_PER_DAY,
        "btc_mined_per_day": btc_mined_per_day,
        "next_halving_block": NEXT_HALVING_BLOCK,
        "current_block_height": current_block_height,
        "blocks_until_halving": blocks_until_halving,
        "estimated_halving_date": "2028-04-23",
        "supply_schedule": [
            {"year": 2028, "reward": 1.5625, "total_mined_approx": 20_475_000},
            {"year": 2032, "reward": 0.78125, "total_mined_approx": 20_737_500},
            {"year": 2036, "reward": 0.390625, "total_mined_approx": 20_868_750},
            {"year": 2140, "reward": 0, "total_mined_approx": 21_000_000},
        ],
    }
    _set_cache("supply", result, 600)
    return result