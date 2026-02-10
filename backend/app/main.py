import asyncio
import logging
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
from app.api import predictions, signals, news, market, history, influencers, events, quant, coins
from app.api import advisor as advisor_api
from app.api import admin as admin_api
from app.api import powerlaw, public_api, liquidations, elliott_wave, subscription
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
    generate_quant_prediction,
    evaluate_predictions,
    evaluate_quant_predictions,
    classify_news_events,
    evaluate_event_impacts,
    cleanup_old_data,
    auto_retrain_models,
    run_advisor_check,
    run_trade_management,
    check_subscription_expiry,
)
from app.collectors.coins import collect_coin_prices, seed_tracked_coins
from app.models.phrase_analyzer import analyze_news_phrases
from app.models.continuous_learner import run_continuous_learning
from app.models.ab_tester import evaluate_candidates

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    # Startup
    logger.info("🔮 BTC Seer starting up...")

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

    # Prediction jobs
    scheduler.add_job(generate_prediction, "interval", minutes=settings.prediction_interval_minutes, id="predict")
    scheduler.add_job(generate_quant_prediction, "interval", minutes=settings.prediction_interval_minutes, id="predict_quant")

    # Evaluation jobs
    scheduler.add_job(evaluate_predictions, "interval", hours=1, id="evaluate")
    scheduler.add_job(evaluate_quant_predictions, "interval", hours=1, id="evaluate_quant")
    scheduler.add_job(classify_news_events, "interval", minutes=5, id="classify_events")
    scheduler.add_job(evaluate_event_impacts, "interval", minutes=30, id="evaluate_events")

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

    # Advisor jobs
    scheduler.add_job(run_advisor_check, "interval", minutes=settings.prediction_interval_minutes, id="advisor_check")
    scheduler.add_job(run_trade_management, "interval", minutes=5, id="trade_management")

    # Subscription expiry check (daily)
    scheduler.add_job(check_subscription_expiry, "interval", hours=24, id="check_subs")

    scheduler.start()
    logger.info("Scheduler started")

    # Start Telegram bot if token is set
    bot = None
    dp = None
    bot_task = None

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

        # Clear stale webhooks before polling (avoids 409 Conflict)
        try:
            await bot.delete_webhook(drop_pending_updates=False)
            logger.info("Cleared webhook, starting polling")
        except Exception as e:
            logger.warning(f"delete_webhook failed: {e}")

        # Start polling in background with error handling
        async def _run_bot_polling():
            try:
                logger.info("Bot polling starting...")
                await dp.start_polling(bot)
            except Exception as e:
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

        # Step 3: Wait briefly for data to settle, then generate first prediction
        await asyncio.sleep(30)
        await _safe_run(generate_prediction(), "generate_prediction")
        await _safe_run(generate_quant_prediction(), "generate_quant_prediction")
        await _safe_run(classify_news_events(), "classify_news_events")
        await _safe_run(save_indicator_snapshot(), "save_indicator_snapshot")

    asyncio.create_task(startup_data_pipeline())

    yield

    # Shutdown
    scheduler.shutdown()
    logger.info("Scheduler stopped")

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
app.include_router(public_api.router)


@app.get("/health")
async def health():
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
        return FileResponse(WEBAPP_DIST / "index.html")
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
            return FileResponse(WEBAPP_DIST / "index.html")
        # Re-raise the exception for API routes
        raise exc
