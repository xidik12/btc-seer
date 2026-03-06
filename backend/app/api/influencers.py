from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, InfluencerTweet
from app.cache import cache_get, cache_set

router = APIRouter(prefix="/api/influencers", tags=["influencers"])


@router.get("/latest")
async def get_latest_tweets(
    limit: int = Query(20, ge=1, le=100),
    category: str = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """Get latest tweets from influential crypto people."""
    # Cache only unfiltered requests
    cache_key = f"influencers:latest:{limit}" if not category else None
    if cache_key:
        cached = await cache_get(cache_key)
        if cached is not None:
            return cached

    query = select(InfluencerTweet).order_by(desc(InfluencerTweet.timestamp)).limit(limit)

    if category:
        query = query.where(InfluencerTweet.category == category)

    result = await session.execute(query)
    tweets = result.scalars().all()

    data = {
        "count": len(tweets),
        "tweets": [
            {
                "id": t.id,
                "influencer": t.influencer_name,
                "username": t.username,
                "role": t.role,
                "category": t.category,
                "weight": t.weight,
                "text": t.text,
                "url": t.url,
                "sentiment_score": t.sentiment_score,
                "timestamp": t.timestamp.isoformat(),
                "published_at": t.published_at,
            }
            for t in tweets
        ],
    }
    if cache_key:
        await cache_set(cache_key, data, 60)
    return data


@router.get("/sentiment")
async def get_influencer_sentiment(
    hours: int = Query(24, ge=1, le=168),
    session: AsyncSession = Depends(get_session),
):
    """Get aggregated sentiment from influential people over time period."""
    cached = await cache_get(f"influencers:sentiment:{hours}")
    if cached is not None:
        return cached

    since = datetime.utcnow() - timedelta(hours=hours)

    # Use SQL aggregation instead of loading all rows into Python
    bullish_case = func.sum(case((InfluencerTweet.sentiment_score > 0.1, 1), else_=0))
    bearish_case = func.sum(case((InfluencerTweet.sentiment_score < -0.1, 1), else_=0))

    # Global aggregates
    result = await session.execute(
        select(
            func.count(InfluencerTweet.id).label("total"),
            func.avg(InfluencerTweet.sentiment_score).label("avg_score"),
            func.sum(InfluencerTweet.sentiment_score * InfluencerTweet.weight).label("weighted_sum"),
            func.sum(InfluencerTweet.weight).label("weight_sum"),
            bullish_case.label("bull"),
            bearish_case.label("bear"),
        )
        .where(InfluencerTweet.timestamp >= since)
        .where(InfluencerTweet.sentiment_score.isnot(None))
    )
    row = result.one()
    total = row.total or 0

    if total == 0:
        return {
            "hours": hours,
            "count": 0,
            "avg_sentiment": None,
            "weighted_sentiment": None,
            "bullish_count": 0,
            "bearish_count": 0,
            "by_category": {},
        }

    avg_score = round(float(row.avg_score), 4) if row.avg_score else None
    weight_sum = float(row.weight_sum) if row.weight_sum else 0
    weighted_avg = round(float(row.weighted_sum) / weight_sum, 4) if weight_sum else 0

    # Per-category breakdown via SQL GROUP BY
    cat_result = await session.execute(
        select(
            InfluencerTweet.category,
            func.avg(InfluencerTweet.sentiment_score).label("avg_s"),
        )
        .where(InfluencerTweet.timestamp >= since)
        .where(InfluencerTweet.sentiment_score.isnot(None))
        .group_by(InfluencerTweet.category)
    )
    category_sentiment = {
        cr.category: round(float(cr.avg_s), 4) if cr.avg_s else None
        for cr in cat_result.all()
    }

    data = {
        "hours": hours,
        "count": total,
        "avg_sentiment": avg_score,
        "weighted_sentiment": weighted_avg,
        "bullish_count": int(row.bull or 0),
        "bearish_count": int(row.bear or 0),
        "by_category": category_sentiment,
    }
    await cache_set(f"influencers:sentiment:{hours}", data, 120)
    return data


@router.get("/top-influencers")
async def get_top_influencers(
    hours: int = Query(24, ge=1, le=168),
    session: AsyncSession = Depends(get_session),
):
    """Get most active influencers in time period."""
    since = datetime.utcnow() - timedelta(hours=hours)

    result = await session.execute(
        select(
            InfluencerTweet.influencer_name,
            InfluencerTweet.username,
            InfluencerTweet.category,
            func.count(InfluencerTweet.id).label("tweet_count"),
            func.avg(InfluencerTweet.sentiment_score).label("avg_sentiment"),
        )
        .where(InfluencerTweet.timestamp >= since)
        .group_by(
            InfluencerTweet.influencer_name,
            InfluencerTweet.username,
            InfluencerTweet.category,
        )
        .order_by(desc("tweet_count"))
        .limit(20)
    )

    influencers = result.all()

    return {
        "hours": hours,
        "influencers": [
            {
                "name": inf.influencer_name,
                "username": inf.username,
                "category": inf.category,
                "tweet_count": inf.tweet_count,
                "avg_sentiment": round(inf.avg_sentiment, 4) if inf.avg_sentiment else None,
            }
            for inf in influencers
        ],
    }
