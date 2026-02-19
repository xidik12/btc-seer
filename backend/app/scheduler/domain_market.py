"""Market data collection jobs: price, macro, funding, dominance, indicators, backfill."""

import logging
from datetime import datetime, timedelta, timezone

import pandas as pd
from sqlalchemy import select, desc

from app.config import settings
from app.database import (
    async_session, Price, MacroData, OnChainData, FundingRate,
    BtcDominance, IndicatorSnapshot,
)
from app.collectors import (
    MarketCollector, FearGreedCollector, MacroCollector, OnChainCollector,
)
from app.features.builder import FeatureBuilder

logger = logging.getLogger(__name__)

# Global instances (initialized once)
market_collector = MarketCollector()
fear_greed_collector = FearGreedCollector()
macro_collector = MacroCollector()
onchain_collector = OnChainCollector()
feature_builder = FeatureBuilder()


async def deep_backfill_historical_prices():
    """Deep backfill: fetch full BTC price history from 2009 to present.

    Runs once on startup when oldest Price row > 2014.
    Uses HistoricalBTCCollector to fetch from early JSON + CoinGecko + Binance.
    """
    try:
        from app.collectors.historical_btc import HistoricalBTCCollector

        # Check if we need deep backfill
        async with async_session() as session:
            result = await session.execute(
                select(Price).order_by(Price.timestamp).limit(1)
            )
            oldest = result.scalar_one_or_none()

        if oldest and oldest.timestamp.year <= 2014:
            logger.info("Deep backfill: Already have pre-2014 data, skipping")
            return

        logger.info("Deep backfill: Starting comprehensive historical price fetch...")
        collector = HistoricalBTCCollector()

        try:
            all_prices = await collector.fetch_all_historical()
        finally:
            await collector.close()

        if not all_prices:
            logger.warning("Deep backfill: No historical prices fetched")
            return

        # Insert into Price table, skipping existing dates
        async with async_session() as session:
            result = await session.execute(select(Price.timestamp))
            existing_dates = set()
            for row in result.all():
                existing_dates.add(row[0].strftime("%Y-%m-%d"))

            inserted = 0
            for p in all_prices:
                day_key = p["timestamp"].strftime("%Y-%m-%d")
                if day_key in existing_dates:
                    continue

                price = Price(
                    timestamp=p["timestamp"],
                    open=p["open"],
                    high=p["high"],
                    low=p["low"],
                    close=p["close"],
                    volume=p["volume"],
                    source="historical_backfill",
                )
                session.add(price)
                existing_dates.add(day_key)
                inserted += 1

            await session.commit()

        logger.info(f"Deep backfill: Inserted {inserted} historical price records")

        # Trigger ML retrain with extended features after backfill
        if inserted > 100:
            try:
                from app.models.trainer import ModelTrainer
                trainer = ModelTrainer()
                result = await trainer.train_all()
                logger.info(f"Deep backfill: Post-backfill retrain result: {result.get('status')}")
            except Exception as e:
                logger.warning(f"Deep backfill: Post-backfill retrain failed (non-critical): {e}")

    except Exception as e:
        logger.error(f"Deep backfill error: {e}", exc_info=True)


async def backfill_historical_prices():
    """Backfill historical BTC price data from Binance on startup.

    Fetches hourly candles (1000 = ~41 days) and daily candles (1000 = ~2.7 years)
    so that charts have data for all timeframes immediately.
    Only runs if the DB has less than 7 days of data.
    """
    try:
        # Check how much data we already have
        async with async_session() as session:
            result = await session.execute(
                select(Price).order_by(Price.timestamp).limit(1)
            )
            oldest = result.scalar_one_or_none()

            result = await session.execute(
                select(Price).order_by(desc(Price.timestamp)).limit(1)
            )
            newest = result.scalar_one_or_none()

        # If we already have >7 days of data, skip backfill
        if oldest and newest:
            span = (newest.timestamp - oldest.timestamp).total_seconds()
            if span > 7 * 86400:
                logger.info(f"Backfill: DB already has {span / 86400:.1f} days of data, skipping")
                return

        logger.info("Backfill: Starting historical price data fetch from Binance...")

        # Fetch hourly klines (1000 = ~41 days) for short/medium timeframes
        hourly_klines = await market_collector.get_historical_klines(
            interval="1h", limit=1000
        )
        if hourly_klines:
            count = await _insert_klines(hourly_klines, source="binance_backfill_1h")
            logger.info(f"Backfill: Inserted {count} hourly candles")

        # Fetch daily klines (1000 = ~2.7 years) for long timeframes
        daily_klines = await market_collector.get_historical_klines(
            interval="1d", limit=1000
        )
        if daily_klines:
            count = await _insert_klines(daily_klines, source="binance_backfill_1d")
            logger.info(f"Backfill: Inserted {count} daily candles")

        total = (len(hourly_klines) if hourly_klines else 0) + (len(daily_klines) if daily_klines else 0)
        logger.info(f"Backfill: Complete — {total} total candles loaded")

    except Exception as e:
        logger.error(f"Backfill error: {e}", exc_info=True)


async def _insert_klines(klines: list[dict], source: str = "binance_backfill"):
    """Insert kline data into the Price table, skipping duplicates by timestamp."""
    async with async_session() as session:
        # Build set of existing timestamps (rounded to minute) for dedup
        result = await session.execute(select(Price.timestamp))
        existing_ts_minutes = set()
        for row in result.all():
            ts = row[0]
            # Round to nearest minute for comparison
            existing_ts_minutes.add(ts.replace(second=0, microsecond=0))

        inserted = 0
        for k in klines:
            ts = k["timestamp"]
            # Make naive UTC if timezone-aware
            if hasattr(ts, 'tzinfo') and ts.tzinfo is not None:
                ts = ts.replace(tzinfo=None)

            ts_minute = ts.replace(second=0, microsecond=0)
            if ts_minute in existing_ts_minutes:
                continue

            price = Price(
                timestamp=ts,
                open=k["open"],
                high=k["high"],
                low=k["low"],
                close=k["close"],
                volume=k["volume"],
                source=source,
            )
            session.add(price)
            existing_ts_minutes.add(ts_minute)
            inserted += 1

        await session.commit()
        return inserted


async def collect_price_data():
    """Collect and store BTC price data (runs every minute).

    Uses Binance klines endpoint for proper per-candle OHLC instead of the
    24hr ticker (which returns rolling 24h open/high/low — wrong for candle
    resampling in Elliott Wave etc.).
    """
    try:
        # Fetch latest closed 1-minute kline for proper OHLC
        kline_data = await market_collector.fetch_json(
            market_collector.BINANCE_KLINES_URL,
            params={"symbol": "BTCUSDT", "interval": "1m", "limit": 2},
        )

        if not kline_data or len(kline_data) < 2:
            logger.warning("No kline data received")
            return

        # Use the second-to-last candle (last closed candle)
        k = kline_data[-2]
        from datetime import timezone
        candle_ts = datetime.fromtimestamp(k[0] / 1000, tz=timezone.utc).replace(tzinfo=None)

        async with async_session() as session:
            price = Price(
                timestamp=candle_ts,
                open=float(k[1]),
                high=float(k[2]),
                low=float(k[3]),
                close=float(k[4]),
                volume=float(k[5]),
                source="binance",
            )
            session.add(price)
            await session.commit()

        logger.info(f"Price collected: ${k[4]} (kline OHLC)")

    except Exception as e:
        logger.error(f"Price collection error: {e}")


async def collect_macro_data():
    """Collect and store macro market data (runs every hour)."""
    try:
        macro_data = await macro_collector.collect()
        fear_greed = await fear_greed_collector.collect()

        dxy = macro_data.get("dxy", {}).get("price") if isinstance(macro_data.get("dxy"), dict) else None
        gold = macro_data.get("gold", {}).get("price") if isinstance(macro_data.get("gold"), dict) else None
        sp500 = macro_data.get("sp500", {}).get("price") if isinstance(macro_data.get("sp500"), dict) else None
        treasury_10y = macro_data.get("treasury_10y", {}).get("price") if isinstance(macro_data.get("treasury_10y"), dict) else None
        nasdaq = macro_data.get("nasdaq", {}).get("price") if isinstance(macro_data.get("nasdaq"), dict) else None
        vix = macro_data.get("vix", {}).get("price") if isinstance(macro_data.get("vix"), dict) else None
        eurusd = macro_data.get("eurusd", {}).get("price") if isinstance(macro_data.get("eurusd"), dict) else None
        fear_greed_index = fear_greed.get("value")
        fear_greed_label = fear_greed.get("label")

        # Don't save a row where ALL values are None
        if dxy is None and gold is None and sp500 is None and treasury_10y is None and nasdaq is None and vix is None and eurusd is None and fear_greed_index is None:
            logger.warning("Macro collection returned all None values, skipping DB save")
            return

        # Fetch M2 money supply
        m2_supply = None
        try:
            m2_supply = await macro_collector.fetch_m2_supply()
        except Exception as e:
            logger.debug(f"M2 supply fetch error: {e}")

        async with async_session() as session:
            macro = MacroData(
                timestamp=datetime.utcnow(),
                dxy=dxy,
                gold=gold,
                sp500=sp500,
                treasury_10y=treasury_10y,
                nasdaq=nasdaq,
                vix=vix,
                eurusd=eurusd,
                fear_greed_index=fear_greed_index,
                fear_greed_label=fear_greed_label,
                m2_supply=m2_supply,
            )
            session.add(macro)
            await session.commit()

        logger.info(f"Macro data collected: DXY={dxy}, Gold={gold}, SP500={sp500}, 10Y={treasury_10y}, NDQ={nasdaq}, VIX={vix}, EURUSD={eurusd}")

    except Exception as e:
        logger.error(f"Macro collection error: {e}")


async def collect_onchain_data():
    """Collect and store on-chain data (runs every hour)."""
    try:
        data = await onchain_collector.collect()

        async with async_session() as session:
            onchain = OnChainData(
                timestamp=datetime.utcnow(),
                hash_rate=data.get("hash_rate"),
                difficulty=data.get("difficulty"),
                mempool_size=data.get("mempool_size"),
                mempool_fees=data.get("mempool_fees"),
                tx_volume=data.get("tx_volume"),
                active_addresses=data.get("active_addresses"),
                large_tx_count=data.get("large_tx_count"),
            )
            session.add(onchain)
            await session.commit()

        logger.info("On-chain data collected")

    except Exception as e:
        logger.error(f"On-chain collection error: {e}")


async def collect_funding_data():
    """Collect and persist Binance perpetual funding rate & open interest (runs every 30 min)."""
    try:
        funding = await market_collector.get_funding_rate()
        oi_data = await market_collector.get_open_interest()

        if not funding and not oi_data:
            logger.debug("No funding/OI data received")
            return

        async with async_session() as session:
            record = FundingRate(
                timestamp=datetime.utcnow(),
                funding_rate=funding.get("funding_rate") if funding else None,
                mark_price=funding.get("mark_price") if funding else None,
                index_price=funding.get("index_price") if funding else None,
                next_funding_time=funding.get("next_funding_time") if funding else None,
                open_interest=oi_data.get("open_interest") if oi_data else None,
            )
            session.add(record)
            await session.commit()

        fr = funding.get("funding_rate", 0) if funding else 0
        oi = oi_data.get("open_interest", 0) if oi_data else 0
        logger.info(f"Funding data collected: rate={fr:.6f}, OI={oi:.2f} BTC")

    except Exception as e:
        logger.error(f"Funding data collection error: {e}")


async def collect_dominance_data():
    """Collect and persist BTC dominance & global market data (runs every hour)."""
    try:
        data = await market_collector.get_btc_dominance()

        if not data:
            logger.debug("No dominance data received")
            return

        async with async_session() as session:
            record = BtcDominance(
                timestamp=datetime.utcnow(),
                btc_dominance=data.get("btc_dominance"),
                eth_dominance=data.get("eth_dominance"),
                total_market_cap=data.get("total_market_cap"),
                total_volume=data.get("total_volume"),
                market_cap_change_24h=data.get("market_cap_change_24h"),
            )
            session.add(record)
            await session.commit()

        logger.info(f"BTC dominance collected: {data.get('btc_dominance', 0):.2f}%")

    except Exception as e:
        logger.error(f"Dominance collection error: {e}")


async def save_indicator_snapshot():
    """Compute and persist a full technical indicator snapshot (runs every hour).

    This saves the complete indicator state so historical indicator values
    are available for backtesting, model training, and trend analysis.
    """
    try:
        from app.features.technical import TechnicalFeatures

        async with async_session() as session:
            since = datetime.utcnow() - timedelta(hours=400)
            result = await session.execute(
                select(Price).where(Price.timestamp >= since).order_by(Price.timestamp)
            )
            prices = result.scalars().all()

        if len(prices) < 30:
            logger.debug(f"Not enough price data for indicator snapshot ({len(prices)} candles)")
            return

        df = pd.DataFrame([
            {"open": p.open, "high": p.high, "low": p.low, "close": p.close, "volume": p.volume}
            for p in prices
        ])

        df = TechnicalFeatures.calculate_all(df)
        latest = df.iloc[-1]

        def safe(val):
            if pd.isna(val):
                return None
            v = float(val)
            return round(v, 6) if abs(v) < 1e12 else v

        indicators = {
            # Moving averages
            "ema_9": safe(latest.get("ema_9")),
            "ema_21": safe(latest.get("ema_21")),
            "ema_50": safe(latest.get("ema_50")),
            "ema_200": safe(latest.get("ema_200")),
            "sma_20": safe(latest.get("sma_20")),
            "sma_111": safe(latest.get("sma_111")),
            "sma_200": safe(latest.get("sma_200")),
            "sma_350": safe(latest.get("sma_350")),
            # Momentum
            "rsi": safe(latest.get("rsi")),
            "rsi_7": safe(latest.get("rsi_7")),
            "rsi_30": safe(latest.get("rsi_30")),
            "macd": safe(latest.get("macd")),
            "macd_signal": safe(latest.get("macd_signal")),
            "macd_hist": safe(latest.get("macd_hist")),
            "adx": safe(latest.get("adx")),
            "stoch_rsi_k": safe(latest.get("stoch_rsi_k")),
            "stoch_rsi_d": safe(latest.get("stoch_rsi_d")),
            "williams_r": safe(latest.get("williams_r")),
            "momentum_10": safe(latest.get("momentum_10")),
            "momentum_20": safe(latest.get("momentum_20")),
            # Volatility
            "bb_upper": safe(latest.get("bb_upper")),
            "bb_middle": safe(latest.get("bb_middle")),
            "bb_lower": safe(latest.get("bb_lower")),
            "bb_width": safe(latest.get("bb_width")),
            "bb_position": safe(latest.get("bb_position")),
            "atr": safe(latest.get("atr")),
            "volatility_24h": safe(latest.get("volatility_24h")),
            # Volume
            "obv": safe(latest.get("obv")),
            "vwap": safe(latest.get("vwap")),
            "volume_sma_20": safe(latest.get("volume_sma_20")),
            "volume_ratio": safe(latest.get("volume_ratio")),
            # Levels
            "pivot": safe(latest.get("pivot")),
            "support_1": safe(latest.get("support_1")),
            "resistance_1": safe(latest.get("resistance_1")),
            # Advanced
            "mayer_multiple": safe(latest.get("mayer_multiple")),
            "pi_cycle_ratio": safe(latest.get("pi_cycle_ratio")),
            "ema_cross": safe(latest.get("ema_cross")),
            "zscore_20": safe(latest.get("zscore_20")),
            # Ichimoku
            "ichimoku_tenkan": safe(latest.get("ichimoku_tenkan")),
            "ichimoku_kijun": safe(latest.get("ichimoku_kijun")),
            "ichimoku_senkou_a": safe(latest.get("ichimoku_senkou_a")),
            "ichimoku_senkou_b": safe(latest.get("ichimoku_senkou_b")),
            # Trend
            "trend_short": int(latest.get("trend_short", 0)),
            "trend_medium": int(latest.get("trend_medium", 0)),
            "trend_long": int(latest.get("trend_long", 0)),
            # ROC
            "roc_1": safe(latest.get("roc_1")),
            "roc_6": safe(latest.get("roc_6")),
            "roc_12": safe(latest.get("roc_12")),
            "roc_24": safe(latest.get("roc_24")),
            # Candlestick patterns
            "candle_doji": int(latest.get("candle_doji", 0)),
            "candle_hammer": int(latest.get("candle_hammer", 0)),
            "candle_inverted_hammer": int(latest.get("candle_inverted_hammer", 0)),
            "candle_bullish_engulfing": int(latest.get("candle_bullish_engulfing", 0)),
            "candle_bearish_engulfing": int(latest.get("candle_bearish_engulfing", 0)),
            "candle_morning_star": int(latest.get("candle_morning_star", 0)),
            "candle_evening_star": int(latest.get("candle_evening_star", 0)),
        }

        current_price = float(prices[-1].close)

        async with async_session() as session:
            snapshot = IndicatorSnapshot(
                timestamp=datetime.utcnow(),
                price=current_price,
                indicators=indicators,
            )
            session.add(snapshot)
            await session.commit()

        logger.info(f"Indicator snapshot saved (RSI={indicators.get('rsi')}, MACD={indicators.get('macd')})")

    except Exception as e:
        logger.error(f"Indicator snapshot error: {e}")
