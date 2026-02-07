from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc

from app.database import async_session, PortfolioState, TradeAdvice, TradeResult, Price

router = APIRouter(prefix="/api/advisor", tags=["advisor"])


class BalanceUpdate(BaseModel):
    balance: float


class TradeClose(BaseModel):
    exit_price: float
    reason: str = "manual_close"


@router.get("/portfolio/{telegram_id}")
async def get_portfolio(telegram_id: int):
    """Get portfolio state for a user."""
    from app.advisor.portfolio import get_or_create_portfolio, get_stats

    portfolio = await get_or_create_portfolio(telegram_id)
    stats = await get_stats(telegram_id)
    return stats


@router.post("/portfolio/{telegram_id}/balance")
async def set_balance(telegram_id: int, body: BalanceUpdate):
    """Manually set portfolio balance."""
    from app.advisor.portfolio import update_balance

    if body.balance < 0:
        raise HTTPException(400, "Balance must be non-negative")

    portfolio = await update_balance(telegram_id, body.balance)
    return {"balance": portfolio.balance_usdt}


@router.get("/trades/{telegram_id}")
async def get_trades(telegram_id: int):
    """Get open/pending trades for a user."""
    async with async_session() as session:
        result = await session.execute(
            select(TradeAdvice).where(
                TradeAdvice.telegram_id == telegram_id,
                TradeAdvice.status.in_(["pending", "opened", "partial_tp"]),
            ).order_by(desc(TradeAdvice.timestamp))
        )
        trades = result.scalars().all()

        # Current price
        result = await session.execute(
            select(Price).order_by(desc(Price.timestamp)).limit(1)
        )
        price_row = result.scalar_one_or_none()
        current_price = price_row.close if price_row else 0

    return {
        "trades": [
            {
                "id": t.id,
                "direction": t.direction,
                "entry_price": t.entry_price,
                "stop_loss": t.stop_loss,
                "take_profit_1": t.take_profit_1,
                "take_profit_2": t.take_profit_2,
                "take_profit_3": t.take_profit_3,
                "leverage": t.leverage,
                "position_size_usdt": t.position_size_usdt,
                "confidence": t.confidence,
                "status": t.status,
                "urgency": t.urgency,
                "reasoning": t.reasoning,
                "models_agreeing": t.models_agreeing,
                "timestamp": t.timestamp.isoformat(),
                "current_price": current_price,
                "unrealized_pnl_pct": (
                    ((current_price - t.entry_price) / t.entry_price * 100 * t.leverage)
                    if t.direction == "LONG"
                    else ((t.entry_price - current_price) / t.entry_price * 100 * t.leverage)
                ) if current_price > 0 and t.status in ("opened", "partial_tp") else None,
            }
            for t in trades
        ],
        "current_price": current_price,
    }


@router.get("/trades/{telegram_id}/history")
async def get_trade_history(telegram_id: int, limit: int = 20):
    """Get trade result history."""
    async with async_session() as session:
        result = await session.execute(
            select(TradeResult)
            .where(TradeResult.telegram_id == telegram_id)
            .order_by(desc(TradeResult.timestamp))
            .limit(limit)
        )
        results = result.scalars().all()

    return {
        "results": [
            {
                "id": r.id,
                "trade_advice_id": r.trade_advice_id,
                "direction": r.direction,
                "entry_price": r.entry_price,
                "exit_price": r.exit_price,
                "leverage": r.leverage,
                "position_size_usdt": r.position_size_usdt,
                "pnl_usdt": r.pnl_usdt,
                "pnl_pct": r.pnl_pct,
                "pnl_pct_leveraged": r.pnl_pct_leveraged,
                "was_winner": r.was_winner,
                "close_reason": r.close_reason,
                "duration_minutes": r.duration_minutes,
                "balance_before": r.balance_before,
                "balance_after": r.balance_after,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in results
        ]
    }


@router.post("/trades/{trade_id}/opened")
async def mark_trade_opened(trade_id: int):
    """Mark a trade as opened by the user."""
    async with async_session() as session:
        result = await session.execute(
            select(TradeAdvice).where(TradeAdvice.id == trade_id)
        )
        trade = result.scalar_one_or_none()

        if not trade:
            raise HTTPException(404, "Trade not found")
        if trade.status != "pending":
            raise HTTPException(400, f"Trade is already {trade.status}")

        trade.status = "opened"
        trade.opened_at = datetime.utcnow()
        await session.commit()

    return {"status": "opened", "trade_id": trade_id}


@router.post("/trades/{trade_id}/close")
async def close_trade(trade_id: int, body: TradeClose):
    """Close a trade with exit price."""
    async with async_session() as session:
        result = await session.execute(
            select(TradeAdvice).where(TradeAdvice.id == trade_id)
        )
        trade = result.scalar_one_or_none()

    if not trade:
        raise HTTPException(404, "Trade not found")
    if trade.status in ("closed", "cancelled"):
        raise HTTPException(400, f"Trade is already {trade.status}")

    from app.advisor.portfolio import record_trade_result

    trade_result = await record_trade_result(
        telegram_id=trade.telegram_id,
        trade_id=trade_id,
        exit_price=body.exit_price,
        reason=body.reason,
    )

    if not trade_result:
        raise HTTPException(500, "Failed to record trade result")

    return {
        "trade_id": trade_id,
        "pnl_usdt": trade_result.pnl_usdt,
        "pnl_pct_leveraged": trade_result.pnl_pct_leveraged,
        "was_winner": trade_result.was_winner,
        "balance_after": trade_result.balance_after,
    }


@router.get("/stats/{telegram_id}")
async def get_stats_endpoint(telegram_id: int):
    """Get comprehensive trading stats."""
    from app.advisor.portfolio import get_stats
    return await get_stats(telegram_id)
