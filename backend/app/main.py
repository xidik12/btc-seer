import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.database import init_db
from app.api import predictions, signals, news, market, history, influencers, events, quant, coins, whales, marketing
from app.api import charts as charts_api
from app.api import support as support_api
from app.api import advisor as advisor_api
from app.api import admin as admin_api
from app.api import powerlaw, public_api, liquidations, elliott_wave, subscription, auth as auth_api, referral as referral_api
from app.api import arbitrage as arbitrage_api, listings as listings_api, memecoins as memecoins_api
from app.api import partner_admin as partner_admin_api, partner_dashboard as partner_dashboard_api
from app.scheduler.jobs import (
    backfill_historical_prices,
    collect_price_data,
    collect_news_data,
    collect_macro_data,
    collect_onchain_data,
    collect_influencer_tweets,
    collect_funding_data,
    collect_dominance_data,
    save_indicator_snapshot,
    generate_prediction,
    generate_prediction_1h,
    generate_prediction_4h,
    generate_prediction_24h,
    deduplicate_predictions,
    generate_quant_prediction,
    generate_quant_prediction_1h,
    generate_quant_prediction_4h,
    generate_quant_prediction_24h,
    evaluate_predictions,
    evaluate_quant_predictions,
    classify_news_events,
    evaluate_event_impacts,
    cleanup_old_data,
    auto_retrain_models,
    run_advisor_check,
    run_trade_management,
    check_subscription_expiry,
    collect_whale_transactions,
    monitor_entity_wallets,
    evaluate_whale_impacts,
    backfill_whale_transactions,
    resolve_unknown_whale_addresses,
    snapshot_daily_metrics,
    aggregate_coin_sentiments,
)
from app.advisor.feedback import run_training_feedback, run_adaptive_weight_learning
from app.collectors.coins import collect_coin_prices, seed_tracked_coins
from app.collectors.coin_ohlcv import collect_coin_ohlcv, backfill_coin_ohlcv
from app.scheduler.coin_prediction_jobs import (
    generate_coin_predictions_1h,
    generate_coin_predictions_4h,
    generate_coin_predictions_24h,
    evaluate_coin_predictions,
)
from app.collectors.arbitrage import scan_arbitrage
from app.collectors.new_listings import check_new_listings, check_listing_announcements, evaluate_listing_performance
from app.collectors.dex_scanner import scan_dex_tokens, check_dex_to_cex_migrations
from app.collectors.memecoin import discover_memecoins, update_memecoin_risk_scores, cleanup_dead_memecoins
from app.collectors.eth_whale import collect_eth_whale_transactions
from app.collectors.sol_whale import collect_sol_whale_transactions
from app.collectors.eth_onchain import collect_multichain_onchain
from app.collectors.cryptopanic_v2 import collect_cryptopanic_v2
from app.collectors.sec_edgar import collect_sec_filings
from app.collectors.btc_treasuries import scrape_btc_treasuries
from app.collectors.arkham import collect_arkham_transfers
from app.models.phrase_analyzer import analyze_news_phrases
from app.models.continuous_learner import run_continuous_learning
from app.models.ab_tester import evaluate_candidates
from app.models.pattern_learner import run_pattern_discovery
from app.scheduler.backup import run_database_backup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="utc")


_startup_error: str | None = None
_data_ready = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    global _startup_error
    # Startup
    logger.info("🔮 BTC Seer starting up...")

    bot = None
    dp = None
    bot_task = None

    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized")

        # Seed tracked coins (BTC, ETH, SOL, XRP)
        await seed_tracked_coins()

        # Ensure model weights dir exists on persistent volume
        import shutil
        import os
        weights_dir = Path(settings.model_dir)
        bundled_weights = Path("app/models/weights")
        weights_dir.mkdir(parents=True, exist_ok=True)

        # Check if we should force retrain (env var FORCE_RETRAIN=1)
        force_retrain = os.getenv("FORCE_RETRAIN", "0") == "1"
        if force_retrain:
            logger.warning("FORCE_RETRAIN=1: Deleting existing model weights")
            for f in weights_dir.glob("*.pt"):
                f.unlink()
                logger.info(f"Deleted incompatible weight: {f.name}")

        # Copy bundled weights if persistent dir is empty
        if bundled_weights.exists() and not any(weights_dir.glob("*.pt")):
            for f in bundled_weights.iterdir():
                if f.is_file():
                    shutil.copy2(f, weights_dir / f.name)
                    logger.info(f"Copied bundled weight: {f.name} -> {weights_dir}")

        logger.info(f"Model weights dir: {weights_dir}")

        # Set up scheduled jobs
        # Data collection jobs
        scheduler.add_job(collect_price_data, "interval", seconds=60, id="collect_price")
        scheduler.add_job(collect_news_data, "interval", minutes=2, id="collect_news")
        scheduler.add_job(collect_macro_data, "interval", hours=1, id="collect_macro")
        scheduler.add_job(collect_onchain_data, "interval", hours=1, id="collect_onchain")
        scheduler.add_job(collect_influencer_tweets, "interval", minutes=10, id="collect_influencers")
        scheduler.add_job(collect_funding_data, "interval", minutes=30, id="collect_funding")
        scheduler.add_job(collect_dominance_data, "interval", hours=1, id="collect_dominance")
        scheduler.add_job(save_indicator_snapshot, "interval", hours=1, id="save_indicators")
        scheduler.add_job(collect_coin_prices, "interval", minutes=2, id="collect_coins")
        scheduler.add_job(collect_coin_ohlcv, "interval", minutes=2, id="collect_ohlcv")
        scheduler.add_job(aggregate_coin_sentiments, "interval", minutes=5, id="aggregate_sentiments")

        # Multi-coin predictions (offset from BTC predictions)
        scheduler.add_job(generate_coin_predictions_1h, "cron", minute=10, id="coin_predict_1h")
        scheduler.add_job(generate_coin_predictions_4h, "cron", hour="0,4,8,12,16,20", minute=12, id="coin_predict_4h")
        scheduler.add_job(generate_coin_predictions_24h, "cron", hour=0, minute=14, id="coin_predict_24h")
        scheduler.add_job(evaluate_coin_predictions, "cron", minute=15, id="coin_eval")

        # Arbitrage scanning (every 30 seconds)
        scheduler.add_job(scan_arbitrage, "interval", seconds=30, id="scan_arbitrage")

        # New listing detection
        scheduler.add_job(check_new_listings, "interval", seconds=30, id="check_listings")
        scheduler.add_job(check_listing_announcements, "interval", minutes=2, id="check_announcements")
        scheduler.add_job(evaluate_listing_performance, "interval", hours=1, id="eval_listings")

        # DEX scanner
        scheduler.add_job(scan_dex_tokens, "interval", minutes=5, id="scan_dex")
        scheduler.add_job(check_dex_to_cex_migrations, "interval", minutes=30, id="dex_to_cex")

        # Memecoin discovery
        scheduler.add_job(discover_memecoins, "interval", minutes=10, id="discover_memes")
        scheduler.add_job(update_memecoin_risk_scores, "interval", minutes=30, id="update_meme_risk")
        scheduler.add_job(cleanup_dead_memecoins, "interval", hours=24, id="cleanup_dead_memes")

        # Multi-chain whale tracking
        scheduler.add_job(collect_eth_whale_transactions, "interval", minutes=5, id="collect_eth_whales")
        scheduler.add_job(collect_sol_whale_transactions, "interval", minutes=5, id="collect_sol_whales",
                          next_run_time=datetime.utcnow() + timedelta(minutes=2))

        # Multi-chain on-chain analytics
        scheduler.add_job(collect_multichain_onchain, "interval", hours=1, id="collect_multichain")

        # CryptoPanic V2 (multi-coin news)
        scheduler.add_job(collect_cryptopanic_v2, "interval", minutes=5, id="cryptopanic_v2")

        scheduler.add_job(collect_whale_transactions, "interval", minutes=10, id="collect_whales")
        scheduler.add_job(monitor_entity_wallets, "interval", minutes=10, id="monitor_entities",
                          next_run_time=datetime.utcnow() + timedelta(minutes=5))  # offset by 5 min
        scheduler.add_job(resolve_unknown_whale_addresses, "interval", minutes=30, id="resolve_addresses",
                          next_run_time=datetime.utcnow() + timedelta(minutes=15))  # offset by 15 min

        # Institutional whale tracking
        scheduler.add_job(collect_sec_filings, "interval", minutes=30, id="collect_sec_filings")
        scheduler.add_job(scrape_btc_treasuries, "interval", hours=6, id="scrape_btc_treasuries")
        scheduler.add_job(collect_arkham_transfers, "interval", minutes=5, id="collect_arkham_transfers")

        # Prediction jobs — time-aligned cron schedules (UTC)
        # 1h: every hour at :00
        scheduler.add_job(generate_prediction_1h, "cron", minute=0, id="predict_1h")
        # 4h: at 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 (minute 2)
        scheduler.add_job(generate_prediction_4h, "cron", hour="0,4,8,12,16,20", minute=2, id="predict_4h")
        # 24h: once daily at 00:04
        scheduler.add_job(generate_prediction_24h, "cron", hour=0, minute=4, id="predict_24h")

        # Quant predictions — offset by 1 minute from ML predictions
        scheduler.add_job(generate_quant_prediction_1h, "cron", minute=1, id="predict_quant_1h")
        scheduler.add_job(generate_quant_prediction_4h, "cron", hour="0,4,8,12,16,20", minute=3, id="predict_quant_4h")
        scheduler.add_job(generate_quant_prediction_24h, "cron", hour=0, minute=5, id="predict_quant_24h")

        # Evaluation jobs — time-aligned
        # 1h: evaluate at :05 every hour
        scheduler.add_job(evaluate_predictions, "cron", minute=5, kwargs={"timeframe_filter": "1h"}, id="evaluate_1h")
        # 4h: evaluate at :07 on 4h boundaries
        scheduler.add_job(evaluate_predictions, "cron", hour="0,4,8,12,16,20", minute=7, kwargs={"timeframe_filter": "4h"}, id="evaluate_4h")
        # 24h: evaluate at 00:09 daily
        scheduler.add_job(evaluate_predictions, "cron", hour=0, minute=9, kwargs={"timeframe_filter": "24h"}, id="evaluate_24h")
        scheduler.add_job(evaluate_quant_predictions, "interval", hours=1, id="evaluate_quant")
        scheduler.add_job(classify_news_events, "interval", minutes=5, id="classify_events")
        scheduler.add_job(evaluate_event_impacts, "interval", minutes=30, id="evaluate_events")
        scheduler.add_job(evaluate_whale_impacts, "interval", minutes=30, id="evaluate_whales")

        # Cleanup
        scheduler.add_job(cleanup_old_data, "interval", hours=24, id="cleanup")

        # Auto-retrain: check every 6 hours if models need retraining (more frequent continuous learning)
        scheduler.add_job(auto_retrain_models, "interval", hours=6, id="auto_retrain")

        # Phrase analyzer: hourly news phrase correlation analysis
        scheduler.add_job(analyze_news_phrases, "interval", hours=1, id="analyze_phrases")

        # Continuous learner: adaptive ensemble weights + selective retrain (every 6h)
        scheduler.add_job(run_continuous_learning, "interval", hours=6, id="continuous_learning")

        # A/B testing: evaluate candidate models (every 6h)
        scheduler.add_job(evaluate_candidates, "interval", hours=6, id="ab_testing")

        # Pattern learning: discover accuracy patterns every 6h
        scheduler.add_job(run_pattern_discovery, "cron", hour="0,6,12,18", minute=30, id="pattern_learning")

        # Advisor jobs
        scheduler.add_job(run_advisor_check, "interval", minutes=30, id="advisor_check")
        scheduler.add_job(run_trade_management, "interval", minutes=5, id="trade_management")

        # Training feedback loop (daily)
        scheduler.add_job(run_training_feedback, "interval", hours=24, id="training_feedback")

        # Adaptive weight learning (daily, 1h after feedback)
        scheduler.add_job(run_adaptive_weight_learning, "interval", hours=24, id="adaptive_weights")

        # Subscription expiry check (daily)
        scheduler.add_job(check_subscription_expiry, "interval", hours=24, id="check_subs")

        # Daily metrics snapshot at 23:55 UTC
        scheduler.add_job(snapshot_daily_metrics, "cron", hour=23, minute=55, id="snapshot_metrics")

        # Database backup
        scheduler.add_job(run_database_backup, "interval", hours=settings.backup_interval_hours, id="database_backup")

        scheduler.start()
        logger.info("Scheduler started")

        # Start Telegram bot if token is set
        if settings.telegram_bot_token:
            from app.bot.bot import create_bot
            from app.bot.alerts import AlertSender

            bot, dp = create_bot()
            alert_sender = AlertSender(bot)

            # Add alert job
            scheduler.add_job(
                alert_sender.send_hourly_alerts,
                "interval",
                hours=1,
                id="send_alerts",
            )

            # Set bot description & command menu
            try:
                from aiogram.types import BotCommand

                await bot.set_my_description(
                    "BTC Seer — AI-powered Bitcoin predictions.\n\n"
                    "Hit /start to begin. I'll analyze 60+ market signals "
                    "every hour and give you clear price predictions, "
                    "trading signals, and real-time news sentiment.\n\n"
                    "Free 7-day trial included."
                )
                await bot.set_my_short_description(
                    "AI Bitcoin predictions, trading signals & whale tracking."
                )
                await bot.set_my_commands([
                    BotCommand(command="start", description="Start the bot & see the main menu"),
                    BotCommand(command="predict", description="Latest price predictions"),
                    BotCommand(command="signal", description="Trading signal with entry & stop-loss"),
                    BotCommand(command="advisor", description="AI trading advisor & portfolio"),
                    BotCommand(command="news", description="Real-time crypto news & sentiment"),
                    BotCommand(command="accuracy", description="Prediction track record"),
                    BotCommand(command="faq", description="Frequently asked questions"),
                    BotCommand(command="report", description="Report a bug or issue"),
                    BotCommand(command="settings", description="Alert frequency preferences"),
                    BotCommand(command="subscribe", description="View subscription plans"),
                ])
                logger.info("Bot description & commands set")
            except Exception as e:
                logger.warning(f"set_my_description/commands failed: {e}")

            # Clear stale webhooks + pending updates before polling
            try:
                await bot.delete_webhook(drop_pending_updates=True)
                logger.info("Cleared webhook, starting polling")
            except Exception as e:
                logger.warning(f"delete_webhook failed: {e}")

            # Brief delay to let previous Railway instance shut down
            await asyncio.sleep(3)

            # Start polling in background with conflict detection
            async def _run_bot_polling():
                try:
                    logger.info("Bot polling starting...")
                    await dp.start_polling(bot)
                except Exception as e:
                    err_str = str(e).lower()
                    if "conflict" in err_str or "409" in err_str:
                        logger.warning("Bot polling stopped: another instance is already running (409 Conflict)")
                    else:
                        logger.error(f"Bot polling crashed: {e}", exc_info=True)

            bot_task = asyncio.create_task(_run_bot_polling())
            logger.info("Telegram bot started")
        else:
            logger.warning("TELEGRAM_BOT_TOKEN not set — bot disabled")

        # Backfill historical prices from Binance, then collect fresh data + predict
        async def _safe_run(coro, name):
            """Run a coroutine safely — log errors but don't kill the pipeline."""
            try:
                await coro
                logger.info(f"Startup: {name} completed")
            except Exception as e:
                logger.error(f"Startup: {name} failed: {e}", exc_info=True)

        async def startup_data_pipeline():
            # Step 1: Backfill historical data so charts work immediately
            await _safe_run(backfill_historical_prices(), "backfill_historical_prices")

            # Step 2: Collect fresh data from all sources (each isolated)
            await _safe_run(collect_price_data(), "collect_price_data")
            await _safe_run(collect_news_data(), "collect_news_data")
            await _safe_run(collect_macro_data(), "collect_macro_data")
            await _safe_run(collect_onchain_data(), "collect_onchain_data")
            await _safe_run(collect_influencer_tweets(), "collect_influencer_tweets")
            await _safe_run(collect_funding_data(), "collect_funding_data")
            await _safe_run(collect_dominance_data(), "collect_dominance_data")
            await _safe_run(collect_coin_prices(), "collect_coin_prices")
            await _safe_run(backfill_coin_ohlcv(), "backfill_coin_ohlcv")
            await _safe_run(backfill_whale_transactions(), "backfill_whale_transactions")

            # Step 2b: Seed new listings, DEX, and memecoins
            await _safe_run(check_new_listings(), "check_new_listings")
            await _safe_run(scan_dex_tokens(), "scan_dex_tokens")
            await _safe_run(discover_memecoins(), "discover_memecoins")

            # Step 3: Clean up duplicate predictions from old 30-min scheduler
            await _safe_run(deduplicate_predictions(), "deduplicate_predictions")

            # Step 4: Wait briefly for data to settle, then generate predictions for all timeframes
            # so the dashboard has data immediately. Cron scheduler takes over after this.
            await asyncio.sleep(30)
            await _safe_run(generate_prediction(), "generate_prediction")
            await _safe_run(generate_quant_prediction(), "generate_quant_prediction")
            await _safe_run(classify_news_events(), "classify_news_events")
            await _safe_run(save_indicator_snapshot(), "save_indicator_snapshot")

        async def _startup_wrapper():
            global _data_ready
            await startup_data_pipeline()
            _data_ready = True
            logger.info("Data pipeline ready")

        asyncio.create_task(_startup_wrapper())
        logger.info("Startup complete — server ready, data pipeline loading in background")

    except Exception as e:
        _startup_error = f"{type(e).__name__}: {e}"
        logger.error(f"STARTUP FAILED: {_startup_error}", exc_info=True)

    yield

    # Shutdown
    try:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
    except Exception:
        pass

    if bot_task:
        bot_task.cancel()
        await bot.session.close()
        logger.info("Telegram bot stopped")

    logger.info("BTC Seer shut down")


app = FastAPI(
    title="BTC Seer",
    description="Bitcoin Price Prediction System with ML-powered signals",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for Mini App
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://web.telegram.org",
        "https://webk.telegram.org",
        "https://webz.telegram.org",
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key authentication middleware (for /api/v1/ public endpoints)
from app.middleware.auth import APIKeyMiddleware
app.add_middleware(APIKeyMiddleware)

# Include API routers
app.include_router(predictions.router)
app.include_router(signals.router)
app.include_router(news.router)
app.include_router(market.router)
app.include_router(history.router)
app.include_router(influencers.router)
app.include_router(events.router)
app.include_router(quant.router)
app.include_router(advisor_api.router)
app.include_router(admin_api.router)
app.include_router(powerlaw.router)
app.include_router(liquidations.router)
app.include_router(coins.router)
app.include_router(elliott_wave.router)
app.include_router(subscription.router)
app.include_router(auth_api.router)
app.include_router(referral_api.router)
app.include_router(whales.router)
app.include_router(marketing.router)
app.include_router(charts_api.router)
app.include_router(support_api.router)
app.include_router(public_api.router)
app.include_router(arbitrage_api.router)
app.include_router(listings_api.router)
app.include_router(memecoins_api.router)
app.include_router(partner_admin_api.router)
app.include_router(partner_dashboard_api.router)


@app.get("/health")
async def health():
    if _startup_error:
        return {"status": "degraded", "error": _startup_error}
    if not _data_ready:
        return {"status": "warming_up"}
    return {"status": "ok"}


# Serve Mini App frontend (production build)
# Check both local dev path and Docker path
_local_dist = Path(__file__).parent.parent.parent / "webapp" / "dist"
_docker_dist = Path("/webapp/dist")
WEBAPP_DIST = _local_dist if _local_dist.exists() else _docker_dist

# Serve webapp
@app.get("/")
async def serve_root():
    """Serve the React SPA root or API info."""
    if WEBAPP_DIST.exists():
        return FileResponse(
            WEBAPP_DIST / "index.html",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )
    return {
        "name": "BTC Seer",
        "version": "1.0.0",
        "status": "running",
        "description": "Bitcoin Price Prediction System",
    }


if WEBAPP_DIST.exists():
    # Mount static assets
    app.mount("/assets", StaticFiles(directory=WEBAPP_DIST / "assets"), name="static")

    # Handle 404s by serving static files or the SPA (for client-side routing)
    @app.exception_handler(StarletteHTTPException)
    async def spa_404_handler(request: Request, exc: StarletteHTTPException):
        """Serve static files from dist root, or SPA for 404s on non-API routes."""
        if exc.status_code == 404 and not request.url.path.startswith("/api"):
            # Try to serve static file from dist root (images, etc.)
            static_file = (WEBAPP_DIST / request.url.path.lstrip("/")).resolve()
            if (
                static_file.exists()
                and static_file.is_file()
                and str(static_file).startswith(str(WEBAPP_DIST.resolve()))
            ):
                return FileResponse(static_file)
            return FileResponse(
                WEBAPP_DIST / "index.html",
                headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
            )
        # Re-raise the exception for API routes
        raise exc
