"""Continuous Learning System for BTC Seer.

Dynamically adjusts ensemble weights based on rolling model accuracy,
selectively retrains degraded models, and logs feature importances.
"""
import logging
from datetime import datetime, timedelta

import numpy as np
from sqlalchemy import select, desc, func, update

from app.config import settings
from app.database import (
    async_session, Prediction, ModelPerformanceLog,
    FeatureImportanceLog, ModelVersion,
)

logger = logging.getLogger(__name__)


async def update_ensemble_weights():
    """Compute rolling accuracy per model and adjust ensemble weights dynamically.

    Uses last 48h of per-model performance logs to compute accuracy,
    then updates the ensemble weights proportionally.
    """
    try:
        async with async_session() as session:
            since = datetime.utcnow() - timedelta(hours=48)
            result = await session.execute(
                select(ModelPerformanceLog)
                .where(ModelPerformanceLog.was_correct.isnot(None))
                .where(ModelPerformanceLog.timestamp >= since)
                .where(ModelPerformanceLog.timeframe == "1h")
            )
            logs = result.scalars().all()

        if len(logs) < 20:
            logger.debug("Not enough performance logs for weight update")
            return None

        # Compute accuracy per model
        model_stats = {}
        for log in logs:
            name = log.model_name
            if name not in model_stats:
                model_stats[name] = {"correct": 0, "total": 0}
            model_stats[name]["total"] += 1
            if log.was_correct:
                model_stats[name]["correct"] += 1

        accuracies = {}
        for name, stats in model_stats.items():
            if stats["total"] >= 5:
                accuracies[name] = stats["correct"] / stats["total"]

        if not accuracies:
            return None

        # Map model names to ensemble weight keys
        name_map = {"tft": "tft", "lstm": "lstm", "xgboost": "xgb", "timesfm": "timesfm"}
        weights = {}
        for model_name, acc in accuracies.items():
            key = name_map.get(model_name)
            if key:
                # Weight = accuracy^2 (reward high accuracy disproportionately)
                weights[key] = max(acc ** 2, 0.05)

        # Ensure all 4 models have weights
        for key in ["tft", "lstm", "xgb", "timesfm"]:
            if key not in weights:
                weights[key] = 0.10

        # Normalize
        total = sum(weights.values())
        weights = {k: v / total for k, v in weights.items()}

        logger.info(f"Adaptive weights: {weights} (from {len(logs)} logs, accuracies={accuracies})")
        return weights

    except Exception as e:
        logger.error(f"Ensemble weight update error: {e}")
        return None


async def selective_retrain():
    """Retrain only models whose accuracy has degraded below threshold.

    Checks each model's rolling accuracy over the configured window;
    if below settings.selective_retrain_accuracy, triggers retrain for
    just that model (not the full pipeline).
    """
    try:
        async with async_session() as session:
            since = datetime.utcnow() - timedelta(hours=settings.selective_retrain_window_hours)
            result = await session.execute(
                select(
                    ModelPerformanceLog.model_name,
                    func.count().label("total"),
                    func.sum(
                        func.cast(ModelPerformanceLog.was_correct, type_=__import__('sqlalchemy').Integer)
                    ).label("correct"),
                )
                .where(ModelPerformanceLog.was_correct.isnot(None))
                .where(ModelPerformanceLog.timestamp >= since)
                .group_by(ModelPerformanceLog.model_name)
            )
            rows = result.all()

        degraded = []
        for row in rows:
            name, total, correct = row
            if total < 10:
                continue
            accuracy = (correct or 0) / total
            if accuracy < settings.selective_retrain_accuracy:
                degraded.append(name)
                logger.warning(f"Model {name} degraded: {accuracy:.1%} accuracy ({correct}/{total})")

        if not degraded:
            logger.info("All models performing adequately")
            return {"status": "ok", "degraded": []}

        # Trigger retrain for degraded models
        from app.models.trainer import ModelTrainer
        trainer = ModelTrainer(model_dir=settings.model_dir)
        dataset = await trainer.build_training_dataset()

        if dataset is None:
            return {"status": "insufficient_data", "degraded": degraded}

        results = {}
        for model_name in degraded:
            try:
                if model_name == "lstm":
                    results["lstm"] = trainer.train_lstm(dataset["X_seq"], dataset["y"])
                elif model_name == "tft":
                    results["tft"] = trainer.train_tft(dataset["X_seq"], dataset["y"])
                elif model_name == "xgboost":
                    results["xgboost"] = trainer.train_xgboost(dataset["X_feat"], dataset["y"])
                logger.info(f"Selectively retrained {model_name}")

                # Register retrained model as A/B candidate
                result = results.get(model_name, {})
                if result.get("status") == "trained" and result.get("weights_path"):
                    from app.models.ab_tester import register_candidate
                    await register_candidate(
                        model_type=model_name,
                        weights_path=result["weights_path"],
                        metrics=result,
                    )
            except Exception as e:
                logger.error(f"Selective retrain of {model_name} failed: {e}")
                results[model_name] = {"status": "failed", "error": str(e)}

        return {"status": "retrained", "degraded": degraded, "results": results}

    except Exception as e:
        logger.error(f"Selective retrain error: {e}")
        return {"status": "error", "error": str(e)}


async def log_feature_importance():
    """Extract and log XGBoost feature importances after training."""
    try:
        import xgboost as xgb
        from pathlib import Path

        model_path = Path(settings.model_dir) / "xgboost_model.json"
        if not model_path.exists():
            return

        model = xgb.Booster()
        model.load_model(str(model_path))

        # Get feature importances (gain-based)
        importance = model.get_score(importance_type="gain")

        if not importance:
            return

        # Sort by importance
        sorted_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)
        top_10 = dict(sorted_features[:10])

        async with async_session() as session:
            log = FeatureImportanceLog(
                timestamp=datetime.utcnow(),
                model_type="xgboost",
                feature_importances=importance,
                top_features=top_10,
            )
            session.add(log)
            await session.commit()

        logger.info(f"Feature importance logged: top features = {list(top_10.keys())}")

    except Exception as e:
        logger.debug(f"Feature importance logging error: {e}")


async def run_continuous_learning():
    """Main entry point for continuous learning (runs every 6h).

    1. Update ensemble weights based on rolling performance
    2. Check for degraded models and selectively retrain
    3. Log feature importances
    """
    logger.info("Running continuous learning cycle...")

    # 1. Adaptive weights
    weights = await update_ensemble_weights()
    if weights:
        # Hot-swap ensemble weights
        try:
            from app.scheduler.jobs import get_ensemble
            ensemble = get_ensemble()
            ensemble.update_weights(weights)
        except Exception as e:
            logger.debug(f"Could not hot-swap weights: {e}")

    # 2. Selective retrain
    retrain_result = await selective_retrain()
    if retrain_result.get("status") == "retrained":
        # Reset ensemble to reload new weights
        try:
            import app.scheduler.domain_ml as ml_module
            ml_module._ensemble = None
        except Exception:
            pass

    # 3. Feature importance
    await log_feature_importance()

    logger.info(f"Continuous learning complete: weights={'updated' if weights else 'unchanged'}, retrain={retrain_result.get('status', 'skipped')}")
