import asyncio
import logging
from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.database import init_db
from app.api import predictions, signals, news, market, history, influencers, events, quant
from app.api import advisor as advisor_api
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
)

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
    logger.info("🔮 BTC Oracle starting up...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Ensure model weights dir exists on persistent volume
    # Copy bundled weights if persistent dir is empty
    import shutil
    weights_dir = Path(settings.model_dir)
    bundled_weights = Path("app/models/weights")
    weights_dir.mkdir(parents=True, exist_ok=True)
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

    # Auto-retrain: check daily if models need retraining
    scheduler.add_job(auto_retrain_models, "interval", hours=24, id="auto_retrain")

    # Advisor jobs
    scheduler.add_job(run_advisor_check, "interval", minutes=settings.prediction_interval_minutes, id="advisor_check")
    scheduler.add_job(run_trade_management, "interval", minutes=5, id="trade_management")

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

        # Start polling in background
        bot_task = asyncio.create_task(dp.start_polling(bot))
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
        await _safe_run(collect_influencer_tweets(), "collect_influencer_tweets")
        await _safe_run(collect_funding_data(), "collect_funding_data")
        await _safe_run(collect_dominance_data(), "collect_dominance_data")

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

    logger.info("BTC Oracle shut down")


app = FastAPI(
    title="BTC Oracle",
    description="Bitcoin Price Prediction System with ML-powered signals",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for Mini App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Telegram Web App needs this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.get("/health")
async def health():
    return {"status": "ok"}


# Serve Mini App frontend (production build)
# Check both local dev path and Docker path
_local_dist = Path(__file__).parent.parent.parent / "webapp" / "dist"
_docker_dist = Path("/webapp/dist")
WEBAPP_DIST = _local_dist if _local_dist.exists() else _docker_dist

if WEBAPP_DIST.exists():
    app.mount("/assets", StaticFiles(directory=WEBAPP_DIST / "assets"), name="static")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """Serve the React SPA — all non-API routes return index.html."""
        file_path = WEBAPP_DIST / full_path
        if full_path and file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(WEBAPP_DIST / "index.html")
else:
    @app.get("/")
    async def root():
        return {
            "name": "BTC Oracle",
            "version": "1.0.0",
            "status": "running",
            "description": "Bitcoin Price Prediction System",
        }
