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
from app.scheduler._singletons import (
    get_market_collector, get_fear_greed_collector, get_macro_collector,
    get_onchain_collector, get_feature_builder,
)

logger = logging.getLogger(__name__)


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
            # Only load timestamps within the range of incoming data
            if all_prices:
                min_date = min(p["timestamp"] for p in all_prices) - timedelta(days=1)
                max_date = max(p["timestamp"] for p in all_prices) + timedelta(days=1)
                result = await session.execute(
                    select(Price.timestamp).where(
                        Price.timestamp.between(min_date, max_date)
                    )
                )
            else:
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
        mc = get_market_collector()

        # Fetch hourly klines (1000 = ~41 days) for short/medium timeframes
        hourly_klines = await mc.get_historical_klines(
            interval="1h", limit=1000
        )
        if hourly_klines:
            count = await _insert_klines(hourly_klines, source="binance_backfill_1h")
            logger.info(f"Backfill: Inserted {count} hourly candles")

        # Fetch daily klines (1000 = ~2.7 years) for long timeframes
        daily_klines = await mc.get_historical_klines(
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
    if not klines:
        return 0
    async with async_session() as session:
        # Compute time range of incoming klines for bounded dedup query
        kline_timestamps = []
        for k in klines:
            ts = k["timestamp"]
            if hasattr(ts, 'tzinfo') and ts.tzinfo is not None:
                ts = ts.replace(tzinfo=None)
            kline_timestamps.append(ts)
        min_ts = min(kline_timestamps) - timedelta(minutes=1)
        max_ts = max(kline_timestamps) + timedelta(minutes=1)

        # Only load existing timestamps within the kline range (not full table)
        result = await session.execute(
            select(Price.timestamp).where(
                Price.timestamp.between(min_ts, max_ts)
            )
        )
        existing_ts_minutes = set()
        for row in result.all():
            existing_ts_minutes.add(row[0].replace(second=0, microsecond=0))

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
        mc = get_market_collector()
        kline_data = await mc.fetch_json(
            mc.BINANCE_KLINES_URL,
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
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            stmt = pg_insert(Price).values(
                timestamp=candle_ts,
                open=float(k[1]),
                high=float(k[2]),
                low=float(k[3]),
                close=float(k[4]),
                volume=float(k[5]),
                source="binance",
            ).on_conflict_do_update(
                index_elements=[Price.timestamp],
                set_={
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                },
            )
            await session.execute(stmt)
            await session.commit()

        logger.info(f"Price collected: ${k[4]} (kline OHLC)")

        # Invalidate caches so next request gets fresh data
        from app.cache import cache_delete
        await cache_delete("price")
        await cache_delete("dashboard_summary")
        # Invalidate Elliott Wave caches so wave analysis reflects new price data
        for tf in ["1h", "4h", "1d", "1w", "1mo"]:
            await cache_delete(f"ew:current:{tf}")
            await cache_delete(f"ew:hist:{tf}")

    except Exception as e:
        logger.error(f"Price collection error: {e}")


async def collect_macro_data():
    """Collect and store macro market data (runs every hour)."""
    try:
        macro_collector = get_macro_collector()
        macro_data = await macro_collector.collect()
        fear_greed = await get_fear_greed_collector().collect()

        def _price(key):
            val = macro_data.get(key)
            return val.get("price") if isinstance(val, dict) else None

        dxy = _price("dxy")
        gold = _price("gold")
        sp500 = _price("sp500")
        treasury_10y = _price("treasury_10y")
        nasdaq = _price("nasdaq")
        vix = _price("vix")
        eurusd = _price("eurusd")
        # New forex
        gbpusd = _price("gbpusd")
        usdjpy = _price("usdjpy")
        usdchf = _price("usdchf")
        audusd = _price("audusd")
        usdcad = _price("usdcad")
        nzdusd = _price("nzdusd")
        # New commodities
        wti_oil = _price("wti_oil")
        silver = _price("silver")
        copper = _price("copper")
        natural_gas = _price("natural_gas")
        # New indices
        dow_jones = _price("dow_jones")
        russell_2000 = _price("russell_2000")
        dax = _price("dax")
        nikkei_225 = _price("nikkei_225")
        ftse_100 = _price("ftse_100")

        fear_greed_index = fear_greed.get("value")
        fear_greed_label = fear_greed.get("label")

        # Don't save a row where ALL values are None
        all_prices = [dxy, gold, sp500, treasury_10y, nasdaq, vix, eurusd,
                      gbpusd, usdjpy, usdchf, audusd, usdcad, nzdusd,
                      wti_oil, silver, copper, natural_gas,
                      dow_jones, russell_2000, dax, nikkei_225, ftse_100]
        if all(v is None for v in all_prices) and fear_greed_index is None:
            logger.warning("Macro collection returned all None values, skipping DB save")
            return

        # Fetch M2 money supply
        m2_supply = None
        try:
            m2_supply = await macro_collector.fetch_m2_supply()
        except Exception as e:
            logger.debug(f"M2 supply fetch error: {e}")

        # Fetch treasury yields from FRED
        treasury_yields = {}
        try:
            treasury_yields = await macro_collector.fetch_treasury_yields()
        except Exception as e:
            logger.debug(f"Treasury yields fetch error: {e}")

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
                # New forex
                gbpusd=gbpusd,
                usdjpy=usdjpy,
                usdchf=usdchf,
                audusd=audusd,
                usdcad=usdcad,
                nzdusd=nzdusd,
                # New commodities
                wti_oil=wti_oil,
                silver=silver,
                copper=copper,
                natural_gas=natural_gas,
                # New indices
                dow_jones=dow_jones,
                russell_2000=russell_2000,
                dax=dax,
                nikkei_225=nikkei_225,
                ftse_100=ftse_100,
                # Treasury yields from FRED
                treasury_2y=treasury_yields.get("treasury_2y"),
                treasury_5y=treasury_yields.get("treasury_5y"),
                treasury_30y=treasury_yields.get("treasury_30y"),
            )
            session.add(macro)
            await session.commit()

        logger.info(f"Macro data collected: DXY={dxy}, Gold={gold}, SP500={sp500}, 10Y={treasury_10y}, NDQ={nasdaq}, VIX={vix}, EUR={eurusd}, DJI={dow_jones}, OIL={wti_oil}")

    except Exception as e:
        logger.error(f"Macro collection error: {e}")


async def collect_onchain_data():
    """Collect and store on-chain data (runs every hour)."""
    try:
        data = await get_onchain_collector().collect()

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
        mc = get_market_collector()
        funding = await mc.get_funding_rate()
        oi_data = await mc.get_open_interest()

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
        data = await get_market_collector().get_btc_dominance()

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


async def collect_liquidation_feed():
    """Collect live liquidation events from Binance (runs every 30 seconds)."""
    import json
    from app.collectors.liquidation_feed import LiquidationFeedCollector

    collector = LiquidationFeedCollector()
    try:
        data = await collector.collect(limit=100)
        new_events = data.get("events", [])
        if not new_events:
            return

        # Merge with existing Redis data, dedup by timestamp+price+qty, keep latest 200
        from app.redis_client import get_redis
        r = await get_redis()
        existing_raw = await r.get("c:liq:live_feed")
        existing_events = []
        if existing_raw:
            try:
                existing_events = json.loads(existing_raw).get("events", [])
            except Exception:
                pass

        # Dedup key: timestamp + price + qty_btc + position
        seen = set()
        merged = []
        for event in new_events + existing_events:
            key = (event.get("timestamp"), event.get("price"), event.get("qty_btc"), event.get("position"))
            if key not in seen:
                seen.add(key)
                merged.append(event)

        # Sort newest first, keep 200
        merged.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
        merged = merged[:200]

        cache_data = {"events": merged, "timestamp": datetime.utcnow().isoformat()}
        await r.set("c:liq:live_feed", json.dumps(cache_data, default=str), ex=300)

        logger.info(f"Liquidation feed updated: {len(new_events)} new, {len(merged)} total")
    except Exception as e:
        logger.error(f"Liquidation feed collection error: {e}")
    finally:
        await collector.close()


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

        import asyncio
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(None, TechnicalFeatures.calculate_all, df)
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
