"""Event Learning Post-Mortem System for BTC Seer.

After event impacts are evaluated, this module:
1. Links events to the prediction that was active at that time
2. Determines if the event-based prediction was correct
3. Logs a causal chain entry (event → mechanism → predicted → actual → lesson)
4. Updates category-level accuracy statistics
5. Discovers event-specific patterns (e.g., "war events >severity 7 always cause -2% in 1h")

This is the "analyze why and how bitcoin moves and remember" step.
"""
import logging
import statistics
from datetime import datetime, timedelta

from sqlalchemy import select, desc, func

from app.database import (
    async_session, EventImpact, EventCausalChain, EventCategoryStats,
    Prediction, Price,
)
from app.models.event_memory import EventPatternMatcher

logger = logging.getLogger(__name__)

matcher = EventPatternMatcher()


async def run_event_post_mortem():
    """Main entry point: run post-mortem on recently evaluated events.

    Scheduled to run every 30 minutes, after evaluate_event_impacts().

    Flow:
    1. Find events that were evaluated (1h) but don't have a causal chain entry yet
    2. For each, find the prediction that was active at the time
    3. Log the causal chain: event → mechanism → expected impact → actual impact
    4. Determine if the event-based reasoning was correct
    5. Update category-level statistics
    """
    try:
        processed = 0

        async with async_session() as session:
            # Find events evaluated at 1h that don't have a causal chain yet
            result = await session.execute(
                select(EventImpact)
                .where(EventImpact.evaluated_1h == True)
                .where(EventImpact.change_pct_1h.isnot(None))
                .order_by(desc(EventImpact.timestamp))
                .limit(100)
            )
            evaluated_events = result.scalars().all()

            if not evaluated_events:
                return

            # Get existing causal chain event IDs to skip
            event_ids = [e.id for e in evaluated_events]
            result = await session.execute(
                select(EventCausalChain.event_impact_id)
                .where(EventCausalChain.event_impact_id.in_(event_ids))
            )
            already_processed = {row[0] for row in result.all()}

            # Get all historical events for pattern matching
            result = await session.execute(
                select(EventImpact)
                .where(EventImpact.evaluated_1h == True)
                .order_by(desc(EventImpact.timestamp))
                .limit(500)
            )
            all_historical = result.scalars().all()
            historical_dicts = [
                {
                    "category": e.category,
                    "keywords": e.keywords,
                    "severity": e.severity,
                    "sentiment_score": e.sentiment_score,
                    "change_pct_1h": e.change_pct_1h,
                    "change_pct_4h": e.change_pct_4h,
                    "change_pct_24h": e.change_pct_24h,
                    "sentiment_was_predictive": e.sentiment_was_predictive,
                    "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                }
                for e in all_historical
            ]

            for event in evaluated_events:
                if event.id in already_processed:
                    continue

                # 1. Find the prediction that was active at event time
                pred_result = await session.execute(
                    select(Prediction)
                    .where(Prediction.timeframe == "1h")
                    .where(Prediction.timestamp <= event.timestamp)
                    .order_by(desc(Prediction.timestamp))
                    .limit(1)
                )
                active_prediction = pred_result.scalar_one_or_none()

                # 2. Find similar historical events and what was expected
                similar = matcher.find_similar_events(
                    category=event.category,
                    keywords=event.keywords or "",
                    past_events=historical_dicts,
                    severity=event.severity,
                )
                expected = matcher.get_expected_impact(similar, current_severity=event.severity)

                # 3. Determine mechanism
                mechanism = matcher.CATEGORY_MECHANISMS.get(
                    event.category,
                    f"{event.category} event → market reaction"
                )

                # 4. Compare expected vs actual
                expected_direction = "bullish" if expected["expected_1h"] > 0 else ("bearish" if expected["expected_1h"] < 0 else "neutral")
                actual_direction = "bullish" if (event.change_pct_1h or 0) > 0 else ("bearish" if (event.change_pct_1h or 0) < 0 else "neutral")
                direction_correct = (expected_direction == actual_direction) if expected["sample_size"] > 0 else None

                magnitude_error = None
                if expected["expected_1h"] != 0 and event.change_pct_1h is not None:
                    magnitude_error = abs(event.change_pct_1h - expected["expected_1h"])

                # 5. Generate lesson
                lesson = _generate_lesson(
                    event, expected, direction_correct, magnitude_error
                )

                # 6. Log causal chain
                chain = EventCausalChain(
                    timestamp=datetime.utcnow(),
                    event_impact_id=event.id,
                    prediction_id=active_prediction.id if active_prediction else None,
                    category=event.category,
                    subcategory=event.subcategory,
                    severity=event.severity,
                    event_title=event.title,
                    mechanism=mechanism,
                    expected_direction=expected_direction,
                    expected_magnitude_pct=expected["expected_1h"],
                    actual_direction=actual_direction,
                    actual_change_1h=event.change_pct_1h,
                    actual_change_4h=event.change_pct_4h,
                    actual_change_24h=event.change_pct_24h,
                    direction_correct=direction_correct,
                    magnitude_error_pct=magnitude_error,
                    lesson=lesson,
                    similar_event_count=expected["sample_size"],
                    pattern_accuracy=expected.get("directional_consistency"),
                )
                session.add(chain)

                # 7. Update event's prediction attribution
                if active_prediction:
                    event.prediction_id = active_prediction.id
                    event.prediction_was_correct = active_prediction.was_correct

                processed += 1

            await session.commit()

        # 8. Update category-level statistics
        if processed > 0:
            await _update_category_stats()
            logger.info(f"Event post-mortem: processed {processed} events, updated category stats")

    except Exception as e:
        logger.error(f"Event post-mortem error: {e}", exc_info=True)


def _generate_lesson(
    event, expected: dict, direction_correct: bool | None, magnitude_error: float | None
) -> str:
    """Generate a human-readable lesson from the event outcome."""
    parts = []
    cat = event.category.replace("_", " ").title()

    if expected["sample_size"] == 0:
        return f"First {cat} event of this type — no historical data to compare. Actual 1h change: {event.change_pct_1h:+.2f}%."

    if direction_correct is True:
        parts.append(f"Direction correctly predicted for {cat} event (severity {event.severity}).")
        if magnitude_error is not None and magnitude_error < 0.5:
            parts.append(f"Magnitude was close (error: {magnitude_error:.2f}%).")
        elif magnitude_error is not None:
            parts.append(f"Magnitude was off by {magnitude_error:.2f}% — adjust impact model.")
    elif direction_correct is False:
        parts.append(
            f"Direction WRONG for {cat} event (severity {event.severity}): "
            f"expected {expected['expected_1h']:+.2f}% but got {event.change_pct_1h:+.2f}%."
        )
        # Try to explain why
        if event.severity >= 7 and abs(event.change_pct_1h or 0) < 0.3:
            parts.append("High-severity event had minimal impact — market may have already priced it in.")
        elif abs(expected["expected_1h"]) < 0.2:
            parts.append("Expected impact was near zero — low-confidence prediction.")
    else:
        parts.append(f"No directional prediction available for {cat} event.")

    # Add severity insight
    if event.severity >= 7:
        parts.append(f"High-severity ({event.severity}/10) — should track if high-sev events consistently over/underperform.")
    elif event.severity <= 3:
        parts.append(f"Low-severity ({event.severity}/10) — may not warrant attention in future.")

    return " ".join(parts)


async def _update_category_stats():
    """Rebuild category-level statistics from all evaluated events.

    This is the system's persistent knowledge about how each event type
    affects BTC across different timeframes.
    """
    try:
        async with async_session() as session:
            # Get all evaluated events
            result = await session.execute(
                select(EventImpact)
                .where(EventImpact.evaluated_1h == True)
            )
            all_events = result.scalars().all()

            if not all_events:
                return

            # Group by category
            by_category: dict[str, list] = {}
            for e in all_events:
                if e.category not in by_category:
                    by_category[e.category] = []
                by_category[e.category].append(e)

            for category, events in by_category.items():
                for timeframe, attr, eval_attr in [
                    ("1h", "change_pct_1h", "evaluated_1h"),
                    ("4h", "change_pct_4h", "evaluated_4h"),
                    ("24h", "change_pct_24h", "evaluated_24h"),
                    ("7d", "change_pct_7d", "evaluated_7d"),
                ]:
                    impacts = [
                        getattr(e, attr)
                        for e in events
                        if getattr(e, eval_attr) and getattr(e, attr) is not None
                    ]
                    if len(impacts) < 3:
                        continue

                    avg_impact = sum(impacts) / len(impacts)
                    median_impact = statistics.median(impacts)
                    std_impact = statistics.stdev(impacts) if len(impacts) >= 2 else 0.0
                    bullish_count = sum(1 for x in impacts if x > 0)
                    bullish_ratio = bullish_count / len(impacts)
                    predictive_power = abs(bullish_ratio - 0.5) * 2

                    # Severity-band stats
                    high_sev = [getattr(e, attr) for e in events if e.severity >= 7 and getattr(e, eval_attr) and getattr(e, attr) is not None]
                    low_sev = [getattr(e, attr) for e in events if e.severity <= 4 and getattr(e, eval_attr) and getattr(e, attr) is not None]

                    # Sentiment predictive ratio
                    sent_events = [e for e in events if e.sentiment_was_predictive is not None]
                    sent_ratio = sum(1 for e in sent_events if e.sentiment_was_predictive) / len(sent_events) if sent_events else 0.5

                    # Upsert
                    existing_result = await session.execute(
                        select(EventCategoryStats)
                        .where(EventCategoryStats.category == category)
                        .where(EventCategoryStats.timeframe == timeframe)
                    )
                    stats = existing_result.scalar_one_or_none()

                    if stats:
                        stats.sample_count = len(impacts)
                        stats.avg_impact_pct = round(avg_impact, 4)
                        stats.median_impact_pct = round(median_impact, 4)
                        stats.std_impact_pct = round(std_impact, 4)
                        stats.max_positive_pct = round(max(impacts), 4)
                        stats.max_negative_pct = round(min(impacts), 4)
                        stats.bullish_ratio = round(bullish_ratio, 4)
                        stats.predictive_power = round(predictive_power, 4)
                        stats.high_severity_avg = round(sum(high_sev) / len(high_sev), 4) if high_sev else None
                        stats.low_severity_avg = round(sum(low_sev) / len(low_sev), 4) if low_sev else None
                        stats.sentiment_predictive_ratio = round(sent_ratio, 4)
                        stats.updated_at = datetime.utcnow()
                    else:
                        session.add(EventCategoryStats(
                            category=category,
                            timeframe=timeframe,
                            sample_count=len(impacts),
                            avg_impact_pct=round(avg_impact, 4),
                            median_impact_pct=round(median_impact, 4),
                            std_impact_pct=round(std_impact, 4),
                            max_positive_pct=round(max(impacts), 4),
                            max_negative_pct=round(min(impacts), 4),
                            bullish_ratio=round(bullish_ratio, 4),
                            predictive_power=round(predictive_power, 4),
                            high_severity_avg=round(sum(high_sev) / len(high_sev), 4) if high_sev else None,
                            low_severity_avg=round(sum(low_sev) / len(low_sev), 4) if low_sev else None,
                            sentiment_predictive_ratio=round(sent_ratio, 4),
                        ))

            await session.commit()
            logger.info(f"Updated category stats for {len(by_category)} categories")

    except Exception as e:
        logger.error(f"Category stats update error: {e}", exc_info=True)


async def get_category_knowledge(category: str) -> dict:
    """Get the system's accumulated knowledge about an event category.

    Used by the prediction system to make informed decisions when
    new events of this category appear.
    """
    try:
        async with async_session() as session:
            result = await session.execute(
                select(EventCategoryStats)
                .where(EventCategoryStats.category == category)
            )
            stats = result.scalars().all()

            if not stats:
                return {"known": False, "category": category}

            knowledge = {
                "known": True,
                "category": category,
                "mechanism": matcher.CATEGORY_MECHANISMS.get(category, ""),
                "timeframes": {},
            }

            for s in stats:
                knowledge["timeframes"][s.timeframe] = {
                    "sample_count": s.sample_count,
                    "avg_impact": s.avg_impact_pct,
                    "median_impact": s.median_impact_pct,
                    "std_impact": s.std_impact_pct,
                    "bullish_ratio": s.bullish_ratio,
                    "predictive_power": s.predictive_power,
                    "high_severity_avg": s.high_severity_avg,
                    "low_severity_avg": s.low_severity_avg,
                    "sentiment_predictive": s.sentiment_predictive_ratio,
                }

            return knowledge

    except Exception as e:
        logger.debug(f"Category knowledge lookup error: {e}")
        return {"known": False, "category": category}
