from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, case, func as sa_func
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

    # Use SQL aggregation instead of loading all rows into Python
    result = await session.execute(
        select(
            sa_func.count(News.id).label("total"),
            sa_func.avg(News.sentiment_score).label("avg_score"),
        )
        .where(News.timestamp >= since)
        .where(News.sentiment_score.isnot(None))
    )
    row = result.one()
    total = row.total or 0
    avg_score = round(float(row.avg_score), 4) if row.avg_score else None

    if total == 0:
        return {
            "hours": hours,
            "count": 0,
            "avg_sentiment": None,
            "bullish_count": 0,
            "bearish_count": 0,
            "neutral_count": 0,
            "by_language": {},
        }

    # Conditional count approach — use case() for portable bullish/bearish counting
    bullish_case = sa_func.sum(case((News.sentiment_score > 0.1, 1), else_=0))
    bearish_case = sa_func.sum(case((News.sentiment_score < -0.1, 1), else_=0))

    # Per-language breakdown via SQL GROUP BY
    lang_result = await session.execute(
        select(
            sa_func.coalesce(News.language, "en").label("lang"),
            sa_func.count(News.id).label("cnt"),
            sa_func.avg(News.sentiment_score).label("avg_s"),
            bullish_case.label("bull"),
            bearish_case.label("bear"),
        )
        .where(News.timestamp >= since)
        .where(News.sentiment_score.isnot(None))
        .group_by(sa_func.coalesce(News.language, "en"))
    )
    lang_rows = lang_result.all()

    by_language = {}
    total_bullish = 0
    total_bearish = 0
    for lr in lang_rows:
        bull = int(lr.bull or 0)
        bear = int(lr.bear or 0)
        cnt = int(lr.cnt or 0)
        total_bullish += bull
        total_bearish += bear
        by_language[lr.lang] = {
            "count": cnt,
            "avg_sentiment": round(float(lr.avg_s), 4) if lr.avg_s else None,
            "bullish_count": bull,
            "bearish_count": bear,
            "neutral_count": cnt - bull - bear,
        }

    neutral = total - total_bullish - total_bearish

    return {
        "hours": hours,
        "count": total,
        "avg_sentiment": avg_score,
        "bullish_count": total_bullish,
        "bearish_count": total_bearish,
        "neutral_count": neutral,
        "bullish_pct": round(total_bullish / total * 100, 1) if total else 0,
        "bearish_pct": round(total_bearish / total * 100, 1) if total else 0,
        "by_language": by_language,
    }
