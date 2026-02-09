"""A/B Testing for Model Versions.

Runs shadow predictions with candidate models alongside production models.
Promotes candidates to production if they outperform over a testing period.
"""
import logging
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from sqlalchemy import select, desc, update

from app.config import settings
from app.database import async_session, ModelVersion, Prediction

logger = logging.getLogger(__name__)

# Minimum predictions before considering promotion
MIN_TEST_PREDICTIONS = 50
# Candidate must beat production by this margin
PROMOTION_THRESHOLD = 0.03  # 3% better accuracy


async def register_candidate(model_type: str, weights_path: str, metrics: dict):
    """Register a newly trained model as a candidate for A/B testing."""
    try:
        async with async_session() as session:
            # Get current active version number
            result = await session.execute(
                select(ModelVersion)
                .where(ModelVersion.model_type == model_type)
                .where(ModelVersion.is_active == True)
                .order_by(desc(ModelVersion.timestamp))
                .limit(1)
            )
            active = result.scalar_one_or_none()
            next_version = (active.version + 1) if active else 1

            candidate = ModelVersion(
                timestamp=datetime.utcnow(),
                model_type=model_type,
                version=next_version,
                test_accuracy=metrics.get("avg_accuracy"),
                train_samples=metrics.get("train_samples"),
                feature_count=metrics.get("feature_count"),
                weights_path=weights_path,
                is_active=False,
                is_candidate=True,
                ab_test_accuracy=None,
            )
            session.add(candidate)
            await session.commit()

        logger.info(f"Registered candidate {model_type} v{next_version} for A/B testing")

    except Exception as e:
        logger.error(f"Candidate registration error: {e}")


async def evaluate_candidates():
    """Evaluate all candidate models and promote if they outperform production.

    This should run periodically (e.g., every 6h after enough predictions).
    """
    try:
        async with async_session() as session:
            # Get all candidates
            result = await session.execute(
                select(ModelVersion).where(ModelVersion.is_candidate == True)
            )
            candidates = result.scalars().all()

        if not candidates:
            return {"status": "no_candidates"}

        promoted = []
        for candidate in candidates:
            result = await _evaluate_single_candidate(candidate)
            if result == "promoted":
                promoted.append(candidate.model_type)

        if promoted:
            logger.info(f"Promoted candidates: {promoted}")

        return {"status": "evaluated", "promoted": promoted}

    except Exception as e:
        logger.error(f"Candidate evaluation error: {e}")
        return {"status": "error", "error": str(e)}


async def _evaluate_single_candidate(candidate: ModelVersion) -> str:
    """Evaluate a single candidate model.

    Returns: "promoted", "rejected", or "testing"
    """
    try:
        # Get production model for same type
        async with async_session() as session:
            result = await session.execute(
                select(ModelVersion)
                .where(ModelVersion.model_type == candidate.model_type)
                .where(ModelVersion.is_active == True)
                .where(ModelVersion.is_candidate == False)
                .limit(1)
            )
            production = result.scalar_one_or_none()

        if not production:
            # No production model — auto-promote
            await _promote_candidate(candidate)
            return "promoted"

        # Compare live accuracies
        prod_accuracy = production.live_accuracy_1h or production.test_accuracy or 0.5
        candidate_accuracy = candidate.ab_test_accuracy or candidate.test_accuracy or 0.5

        # Need enough testing data
        candidate_age_hours = (datetime.utcnow() - candidate.timestamp).total_seconds() / 3600
        if candidate_age_hours < 24:
            return "testing"

        # Check if candidate outperforms
        if candidate_accuracy > prod_accuracy + PROMOTION_THRESHOLD:
            await _promote_candidate(candidate)
            logger.info(
                f"Promoted {candidate.model_type} v{candidate.version}: "
                f"{candidate_accuracy:.1%} > {prod_accuracy:.1%} + {PROMOTION_THRESHOLD:.1%}"
            )
            return "promoted"
        elif candidate_age_hours > 72 and candidate_accuracy <= prod_accuracy:
            # Tested for 3+ days and not better — reject
            async with async_session() as session:
                await session.execute(
                    update(ModelVersion)
                    .where(ModelVersion.id == candidate.id)
                    .values(is_candidate=False)
                )
                await session.commit()
            logger.info(f"Rejected candidate {candidate.model_type} v{candidate.version}")
            return "rejected"

        return "testing"

    except Exception as e:
        logger.error(f"Candidate evaluation error for {candidate.model_type}: {e}")
        return "error"


async def _promote_candidate(candidate: ModelVersion):
    """Promote a candidate to active production model."""
    try:
        async with async_session() as session:
            # Deactivate current production model
            await session.execute(
                update(ModelVersion)
                .where(ModelVersion.model_type == candidate.model_type)
                .where(ModelVersion.is_active == True)
                .values(is_active=False)
            )

            # Promote candidate
            await session.execute(
                update(ModelVersion)
                .where(ModelVersion.id == candidate.id)
                .values(is_active=True, is_candidate=False)
            )

            await session.commit()

    except Exception as e:
        logger.error(f"Candidate promotion error: {e}")
