"""Prediction Game API — make predictions, leaderboard, consensus, history."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select, func, desc

from app.database import async_session, UserPrediction, GameProfile, BotUser, Price
from app.telegram_auth import _verify_telegram_init_data
from app.bot.subscription import is_premium
from app.dependencies import standard_rate_limit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/game", tags=["game"], dependencies=[Depends(standard_rate_limit)])

# Points config
CORRECT_POINTS = 10
WRONG_POINTS = -5
STREAK_MULTIPLIERS = {3: 2.0, 5: 3.0, 10: 5.0}


def _get_multiplier(streak: int) -> float:
    mult = 1.0
    for threshold, m in sorted(STREAK_MULTIPLIERS.items()):
        if streak >= threshold:
            mult = m
    return mult


class PredictBody(BaseModel):
    direction: str  # up, down
    timeframe: str = "24h"


def _get_user_data(request: Request):
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data:
        raise HTTPException(401, "Missing initData")
    user_data = _verify_telegram_init_data(init_data, max_age=86400)
    telegram_id = user_data.get("id")
    username = user_data.get("username")
    if not telegram_id:
        raise HTTPException(400, "Invalid user data")
    return telegram_id, username


@router.post("/predict")
async def make_prediction(body: PredictBody, request: Request):
    """Make a directional prediction for the current round."""
    telegram_id, username = _get_user_data(request)

    if body.direction not in ("up", "down"):
        raise HTTPException(400, "direction must be 'up' or 'down'")
    if body.timeframe not in ("24h", "4h", "1h"):
        raise HTTPException(400, "timeframe must be '24h', '4h', or '1h'")

    today = datetime.utcnow().strftime("%Y-%m-%d")

    async with async_session() as session:
        # Premium check for shorter timeframes
        if body.timeframe in ("4h", "1h"):
            result = await session.execute(
                select(BotUser).where(BotUser.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            if not user or not is_premium(user):
                raise HTTPException(403, f"{body.timeframe} predictions require Premium")

        # Check for existing prediction this round
        result = await session.execute(
            select(UserPrediction).where(
                UserPrediction.telegram_id == telegram_id,
                UserPrediction.round_date == today,
                UserPrediction.timeframe == body.timeframe,
                UserPrediction.status == "pending",
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(409, "Already predicted for this round")

        # Get current price
        result = await session.execute(
            select(Price).order_by(desc(Price.timestamp)).limit(1)
        )
        price_row = result.scalar_one_or_none()
        lock_price = price_row.close if price_row else 0

        # Get or create game profile
        result = await session.execute(
            select(GameProfile).where(GameProfile.telegram_id == telegram_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            profile = GameProfile(telegram_id=telegram_id, username=username)
            session.add(profile)
            await session.flush()

        multiplier = _get_multiplier(profile.current_streak)

        prediction = UserPrediction(
            telegram_id=telegram_id,
            round_date=today,
            timeframe=body.timeframe,
            direction=body.direction,
            lock_price=lock_price,
            streak_at_prediction=profile.current_streak,
            multiplier=multiplier,
        )
        session.add(prediction)

        # Update profile prediction count
        profile.total_predictions = (profile.total_predictions or 0) + 1
        if username:
            profile.username = username

        await session.commit()

    return {
        "prediction_id": prediction.id,
        "direction": body.direction,
        "timeframe": body.timeframe,
        "lock_price": lock_price,
        "multiplier": multiplier,
        "round_date": today,
    }


@router.get("/status")
async def get_game_status(request: Request):
    """Get user's current prediction, profile, and consensus."""
    telegram_id, username = _get_user_data(request)
    today = datetime.utcnow().strftime("%Y-%m-%d")

    async with async_session() as session:
        # Current prediction
        result = await session.execute(
            select(UserPrediction).where(
                UserPrediction.telegram_id == telegram_id,
                UserPrediction.round_date == today,
                UserPrediction.status == "pending",
            ).order_by(desc(UserPrediction.timestamp)).limit(1)
        )
        current = result.scalar_one_or_none()

        # Profile
        result = await session.execute(
            select(GameProfile).where(GameProfile.telegram_id == telegram_id)
        )
        profile = result.scalar_one_or_none()

        # Consensus for 24h
        result = await session.execute(
            select(
                UserPrediction.direction,
                func.count(UserPrediction.id),
            )
            .where(UserPrediction.round_date == today, UserPrediction.timeframe == "24h")
            .group_by(UserPrediction.direction)
        )
        consensus_rows = result.all()

    consensus = {"up": 0, "down": 0}
    total_votes = 0
    for direction, count in consensus_rows:
        consensus[direction] = count
        total_votes += count

    return {
        "current_prediction": {
            "id": current.id,
            "direction": current.direction,
            "timeframe": current.timeframe,
            "lock_price": current.lock_price,
            "multiplier": current.multiplier,
            "round_date": current.round_date,
        } if current else None,
        "profile": {
            "total_points": profile.total_points if profile else 0,
            "total_predictions": profile.total_predictions if profile else 0,
            "correct_predictions": profile.correct_predictions if profile else 0,
            "current_streak": profile.current_streak if profile else 0,
            "best_streak": profile.best_streak if profile else 0,
            "accuracy_pct": profile.accuracy_pct if profile else 0,
            "weekly_points": profile.weekly_points if profile else 0,
            "monthly_points": profile.monthly_points if profile else 0,
        } if profile else None,
        "consensus": consensus,
        "total_votes": total_votes,
    }


@router.get("/leaderboard")
async def get_leaderboard(period: str = "all_time", limit: int = Query(20, ge=1, le=100)):
    """Public leaderboard."""
    if period not in ("all_time", "weekly", "monthly"):
        raise HTTPException(400, "Invalid period")

    async with async_session() as session:
        if period == "weekly":
            order_col = GameProfile.weekly_points
        elif period == "monthly":
            order_col = GameProfile.monthly_points
        else:
            order_col = GameProfile.total_points

        result = await session.execute(
            select(GameProfile)
            .where(order_col > 0)
            .order_by(desc(order_col))
            .limit(limit)
        )
        profiles = result.scalars().all()

    return {
        "period": period,
        "leaderboard": [
            {
                "rank": i + 1,
                "username": p.username or "Anonymous",
                "total_points": p.total_points,
                "weekly_points": p.weekly_points,
                "monthly_points": p.monthly_points,
                "current_streak": p.current_streak,
                "best_streak": p.best_streak,
                "accuracy_pct": round(p.accuracy_pct, 1),
                "total_predictions": p.total_predictions,
            }
            for i, p in enumerate(profiles)
        ],
    }


@router.get("/consensus")
async def get_consensus(timeframe: str = "24h"):
    """Community vote distribution."""
    today = datetime.utcnow().strftime("%Y-%m-%d")

    async with async_session() as session:
        result = await session.execute(
            select(
                UserPrediction.direction,
                func.count(UserPrediction.id),
            )
            .where(
                UserPrediction.round_date == today,
                UserPrediction.timeframe == timeframe,
            )
            .group_by(UserPrediction.direction)
        )
        rows = result.all()

    consensus = {"up": 0, "down": 0}
    for direction, count in rows:
        consensus[direction] = count

    total = consensus["up"] + consensus["down"]
    return {
        "timeframe": timeframe,
        "up": consensus["up"],
        "down": consensus["down"],
        "total": total,
        "up_pct": round(consensus["up"] / total * 100, 1) if total else 50,
        "down_pct": round(consensus["down"] / total * 100, 1) if total else 50,
    }


@router.get("/history")
async def get_game_history(request: Request, limit: int = 30):
    """User's prediction history."""
    telegram_id, _ = _get_user_data(request)

    async with async_session() as session:
        result = await session.execute(
            select(UserPrediction)
            .where(UserPrediction.telegram_id == telegram_id)
            .order_by(desc(UserPrediction.timestamp))
            .limit(limit)
        )
        preds = result.scalars().all()

    return {
        "predictions": [
            {
                "id": p.id,
                "round_date": p.round_date,
                "timeframe": p.timeframe,
                "direction": p.direction,
                "lock_price": p.lock_price,
                "resolve_price": p.resolve_price,
                "was_correct": p.was_correct,
                "points_earned": p.points_earned,
                "multiplier": p.multiplier,
                "status": p.status,
                "timestamp": p.timestamp.isoformat() if p.timestamp else None,
            }
            for p in preds
        ],
    }
