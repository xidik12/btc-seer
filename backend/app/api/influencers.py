from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, InfluencerTweet

router = APIRouter(prefix="/api/influencers", tags=["influencers"])


@router.get("/latest")
async def get_latest_tweets(
    limit: int = Query(20, ge=1, le=100),
    category: str = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """Get latest tweets from influential crypto people."""
    query = select(InfluencerTweet).order_by(desc(InfluencerTweet.timestamp)).limit(limit)

    if category:
        query = query.where(InfluencerTweet.category == category)

    result = await session.execute(query)
    tweets = result.scalars().all()

    return {
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


@router.get("/sentiment")
async def get_influencer_sentiment(
    hours: int = Query(24, ge=1, le=168),
    session: AsyncSession = Depends(get_session),
):
    """Get aggregated sentiment from influential people over time period."""
    since = datetime.utcnow() - timedelta(hours=hours)

    result = await session.execute(
        select(InfluencerTweet)
        .where(InfluencerTweet.timestamp >= since)
        .where(InfluencerTweet.sentiment_score.isnot(None))
    )
    tweets = result.scalars().all()

    if not tweets:
        return {
            "hours": hours,
            "count": 0,
            "avg_sentiment": None,
            "weighted_sentiment": None,
            "bullish_count": 0,
            "bearish_count": 0,
        }

    # Calculate weighted average sentiment
    total_weighted = sum(t.sentiment_score * t.weight for t in tweets)
    total_weight = sum(t.weight for t in tweets)
    weighted_avg = total_weighted / total_weight if total_weight else 0

    # Simple average
    simple_avg = sum(t.sentiment_score for t in tweets) / len(tweets)

    # Bullish/bearish counts
    bullish = sum(1 for t in tweets if t.sentiment_score > 0.1)
    bearish = sum(1 for t in tweets if t.sentiment_score < -0.1)

    # By category
    by_category = {}
    for tweet in tweets:
        cat = tweet.category
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(tweet.sentiment_score)

    category_sentiment = {
        cat: round(sum(scores) / len(scores), 4)
        for cat, scores in by_category.items()
    }

    return {
        "hours": hours,
        "count": len(tweets),
        "avg_sentiment": round(simple_avg, 4),
        "weighted_sentiment": round(weighted_avg, 4),
        "bullish_count": bullish,
        "bearish_count": bearish,
        "by_category": category_sentiment,
    }


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
