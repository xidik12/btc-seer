"""
Scheduler jobs — re-export hub.

All job functions have been split into domain-specific modules under
app/scheduler/domain_*.py. This file re-exports every public function
so that existing imports like:

    from app.scheduler.jobs import collect_price_data, run_ml_predictions, ...

continue to work without changes.
"""

# ── Market data collection ───────────────────────────────────────
from app.scheduler.domain_market import (  # noqa: F401
    market_collector,
    fear_greed_collector,
    macro_collector,
    onchain_collector,
    feature_builder,
    deep_backfill_historical_prices,
    backfill_historical_prices,
    collect_price_data,
    collect_macro_data,
    collect_onchain_data,
    collect_funding_data,
    collect_dominance_data,
    save_indicator_snapshot,
)

# ── ML predictions & evaluation ─────────────────────────────────
from app.scheduler.domain_ml import (  # noqa: F401
    get_ensemble,
    generate_prediction,
    generate_prediction_1h,
    generate_prediction_4h,
    generate_prediction_24h,
    generate_quant_prediction,
    generate_quant_prediction_1h,
    generate_quant_prediction_4h,
    generate_quant_prediction_24h,
    evaluate_predictions,
    evaluate_quant_predictions,
    deduplicate_predictions,
    auto_retrain_models,
)

# ── News, sentiment, events ─────────────────────────────────────
from app.scheduler.domain_news import (  # noqa: F401
    news_collector,
    reddit_collector,
    binance_news_collector,
    influencer_collector,
    event_classifier,
    collect_news_data,
    collect_influencer_tweets,
    classify_news_events,
    evaluate_event_impacts,
    aggregate_coin_sentiments,
)

# ── On-chain / whale tracking ───────────────────────────────────
from app.scheduler.domain_onchain import (  # noqa: F401
    whale_collector,
    collect_whale_transactions,
    monitor_entity_wallets,
    evaluate_whale_impacts,
    backfill_whale_transactions,
    resolve_unknown_whale_addresses,
)

# ── User-facing: advisor, trades, subscriptions ─────────────────
from app.scheduler.domain_user import (  # noqa: F401
    run_advisor_check,
    run_trade_management,
    check_subscription_expiry,
)

# ── Marketing, game, metrics, cleanup ───────────────────────────
from app.scheduler.domain_marketing import (  # noqa: F401
    cleanup_old_data,
    snapshot_daily_metrics,
    evaluate_game_predictions,
    reset_game_periods,
)
