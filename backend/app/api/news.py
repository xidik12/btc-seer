from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, News

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("/latest")
async def get_latest_news(
    limit: int = Query(20, ge=1, le=100),
    source: str = Query(None),
    language: str = Query(None, description="Filter by language code (en, ru, zh-cn, es)"),
    session: AsyncSession = Depends(get_session),
):
    """Get latest crypto news with sentiment scores."""
    query = select(News).order_by(desc(News.timestamp)).limit(limit)

    if source:
        query = query.where(News.source == source)
    if language:
        query = query.where(News.language == language)

    result = await session.execute(query)
    news = result.scalars().all()

    return {
        "count": len(news),
        "news": [
            {
                "id": n.id,
                "source": n.source,
                "title": n.title,
                "url": n.url,
                "sentiment_score": n.sentiment_score,
                "raw_sentiment": n.raw_sentiment,
                "language": getattr(n, "language", None) or "en",
                "timestamp": n.timestamp.isoformat(),
            }
            for n in news
        ],
    }


@router.get("/sentiment")
async def get_news_sentiment(
    hours: int = Query(24, ge=1, le=168),
    session: AsyncSession = Depends(get_session),
):
    """Get aggregated news sentiment over a time period, with per-language breakdown."""
    since = datetime.utcnow() - timedelta(hours=hours)

    result = await session.execute(
        select(News)
        .where(News.timestamp >= since)
        .where(News.sentiment_score.isnot(None))
    )
    news = result.scalars().all()

    if not news:
        return {
            "hours": hours,
            "count": 0,
            "avg_sentiment": None,
            "bullish_count": 0,
            "bearish_count": 0,
            "neutral_count": 0,
            "by_language": {},
        }

    scores = [n.sentiment_score for n in news]
    bullish = sum(1 for s in scores if s > 0.1)
    bearish = sum(1 for s in scores if s < -0.1)
    neutral = len(scores) - bullish - bearish

    # Per-language sentiment breakdown
    by_language = {}
    for n in news:
        lang = getattr(n, "language", None) or "en"
        if lang not in by_language:
            by_language[lang] = {"scores": [], "count": 0}
        by_language[lang]["scores"].append(n.sentiment_score)
        by_language[lang]["count"] += 1

    lang_summary = {}
    for lang, data in by_language.items():
        lang_scores = data["scores"]
        lang_bullish = sum(1 for s in lang_scores if s > 0.1)
        lang_bearish = sum(1 for s in lang_scores if s < -0.1)
        lang_summary[lang] = {
            "count": data["count"],
            "avg_sentiment": round(sum(lang_scores) / len(lang_scores), 4),
            "bullish_count": lang_bullish,
            "bearish_count": lang_bearish,
            "neutral_count": len(lang_scores) - lang_bullish - lang_bearish,
        }

    return {
        "hours": hours,
        "count": len(scores),
        "avg_sentiment": round(sum(scores) / len(scores), 4),
        "bullish_count": bullish,
        "bearish_count": bearish,
        "neutral_count": neutral,
        "bullish_pct": round(bullish / len(scores) * 100, 1),
        "bearish_pct": round(bearish / len(scores) * 100, 1),
        "by_language": lang_summary,
    }
