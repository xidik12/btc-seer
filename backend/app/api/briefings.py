"""Daily Briefing API — latest and historical briefings."""

import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc

from app.database import async_session, DailyBriefing
from app.dependencies import relaxed_rate_limit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/briefings", tags=["briefings"], dependencies=[Depends(relaxed_rate_limit)])


@router.get("/latest")
async def get_latest_briefing():
    """Get the most recent daily briefing."""
    async with async_session() as session:
        result = await session.execute(
            select(DailyBriefing).order_by(desc(DailyBriefing.date)).limit(1)
        )
        briefing = result.scalar_one_or_none()

    if not briefing:
        return {"briefing": None}

    return {
        "briefing": {
            "date": briefing.date,
            "timestamp": briefing.timestamp.isoformat() if briefing.timestamp else None,
            "summary_html": briefing.summary_html,
            "summary_text": briefing.summary_text,
            "data_snapshot": briefing.data_snapshot,
            "btc_price": briefing.btc_price,
            "btc_24h_change": briefing.btc_24h_change,
            "overall_sentiment": briefing.overall_sentiment,
            "confidence": briefing.confidence,
            "generation_method": briefing.generation_method,
        },
    }


@router.get("/history")
async def get_briefing_history(days: int = 7):
    """Get briefing metadata for the last N days."""
    async with async_session() as session:
        result = await session.execute(
            select(DailyBriefing)
            .order_by(desc(DailyBriefing.date))
            .limit(days)
        )
        briefings = result.scalars().all()

    return {
        "briefings": [
            {
                "date": b.date,
                "btc_price": b.btc_price,
                "btc_24h_change": b.btc_24h_change,
                "overall_sentiment": b.overall_sentiment,
                "confidence": b.confidence,
            }
            for b in briefings
        ],
    }


@router.get("/{date}")
async def get_briefing_by_date(date: str):
    """Get a specific day's briefing."""
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD.")

    async with async_session() as session:
        result = await session.execute(
            select(DailyBriefing).where(DailyBriefing.date == date)
        )
        briefing = result.scalar_one_or_none()

    if not briefing:
        return {"briefing": None}

    return {
        "briefing": {
            "date": briefing.date,
            "timestamp": briefing.timestamp.isoformat() if briefing.timestamp else None,
            "summary_html": briefing.summary_html,
            "summary_text": briefing.summary_text,
            "data_snapshot": briefing.data_snapshot,
            "btc_price": briefing.btc_price,
            "btc_24h_change": briefing.btc_24h_change,
            "overall_sentiment": briefing.overall_sentiment,
            "confidence": briefing.confidence,
            "generation_method": briefing.generation_method,
        },
    }
