from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, desc

from app.database import async_session, PortfolioState, TradeAdvice, TradeResult, Price

router = APIRouter(prefix="/api/advisor", tags=["advisor"])


class BalanceUpdate(BaseModel):
    balance: float


class TradeClose(BaseModel):
    exit_price: float
    reason: str = "manual_close"


class MockTradeCreate(BaseModel):
    direction: str  # LONG / SHORT
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: Optional[float] = None
    take_profit_3: Optional[float] = None
    leverage: int = 1
    position_size_usdt: float = 10.0


def _serialize_trade(t, current_price):
    """Serialize a TradeAdvice row to dict."""
    return {
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
        "is_mock": t.is_mock,
        "timestamp": t.timestamp.isoformat(),
        "current_price": current_price,
        "unrealized_pnl_pct": (
            ((current_price - t.entry_price) / t.entry_price * 100 * t.leverage)
            if t.direction == "LONG"
            else ((t.entry_price - current_price) / t.entry_price * 100 * t.leverage)
        ) if current_price > 0 and t.status in ("opened", "partial_tp") else None,
    }


async def _get_current_price():
    """Get latest BTC price from DB."""
    async with async_session() as session:
        result = await session.execute(
            select(Price).order_by(desc(Price.timestamp)).limit(1)
        )
        price_row = result.scalar_one_or_none()
        return price_row.close if price_row else 0


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
async def get_trades(telegram_id: int, mock: bool = Query(False)):
    """Get open/pending trades for a user. Use ?mock=true for paper trades."""
    async with async_session() as session:
        result = await session.execute(
            select(TradeAdvice).where(
                TradeAdvice.telegram_id == telegram_id,
                TradeAdvice.status.in_(["pending", "opened", "partial_tp"]),
                TradeAdvice.is_mock == mock,
            ).order_by(desc(TradeAdvice.timestamp))
        )
        trades = result.scalars().all()

    current_price = await _get_current_price()

    return {
        "trades": [_serialize_trade(t, current_price) for t in trades],
        "current_price": current_price,
    }


@router.get("/trades/{telegram_id}/history")
async def get_trade_history(telegram_id: int, limit: int = 20, mock: bool = Query(False)):
    """Get trade result history."""
    async with async_session() as session:
        # Get trade_advice_ids that match mock filter
        mock_advice_ids_q = select(TradeAdvice.id).where(
            TradeAdvice.telegram_id == telegram_id,
            TradeAdvice.is_mock == mock,
        )
        mock_ids_result = await session.execute(mock_advice_ids_q)
        mock_ids = {r[0] for r in mock_ids_result.all()}

        result = await session.execute(
            select(TradeResult)
            .where(TradeResult.telegram_id == telegram_id)
            .order_by(desc(TradeResult.timestamp))
            .limit(limit * 2)  # Over-fetch to filter
        )
        results = result.scalars().all()

    # Filter by mock status
    filtered = [r for r in results if r.trade_advice_id in mock_ids][:limit]

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
            for r in filtered
        ]
    }


@router.post("/trades/{telegram_id}/mock")
async def create_mock_trade(telegram_id: int, body: MockTradeCreate):
    """Create a paper/mock trade."""
    current_price = await _get_current_price()

    # Validate
    if body.leverage < 1 or body.leverage > 125:
        raise HTTPException(400, "Leverage must be 1-125")
    if body.position_size_usdt <= 0:
        raise HTTPException(400, "Position size must be positive")
    if body.direction not in ("LONG", "SHORT"):
        raise HTTPException(400, "Direction must be LONG or SHORT")

    # Calculate risk metrics
    risk_pct = abs(body.entry_price - body.stop_loss) / body.entry_price * 100
    reward_pct = abs(body.take_profit_1 - body.entry_price) / body.entry_price * 100
    rr_ratio = reward_pct / risk_pct if risk_pct > 0 else 0
    risk_amount = body.position_size_usdt * (risk_pct / 100) * body.leverage

    async with async_session() as session:
        trade = TradeAdvice(
            telegram_id=telegram_id,
            direction=body.direction,
            entry_price=body.entry_price,
            stop_loss=body.stop_loss,
            take_profit_1=body.take_profit_1,
            take_profit_2=body.take_profit_2,
            take_profit_3=body.take_profit_3,
            leverage=body.leverage,
            position_size_usdt=body.position_size_usdt,
            position_size_pct=(body.position_size_usdt / 10.0) * 100,
            risk_amount_usdt=risk_amount,
            risk_reward_ratio=rr_ratio,
            confidence=0,
            status="opened",
            opened_at=datetime.utcnow(),
            is_mock=True,
            reasoning="Paper trade (manual entry)",
            timeframe="manual",
        )
        session.add(trade)
        await session.commit()
        await session.refresh(trade)

    return _serialize_trade(trade, current_price)


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

    # For mock trades, record result directly without portfolio impact
    if trade.is_mock:
        async with async_session() as session:
            result = await session.execute(
                select(TradeAdvice).where(TradeAdvice.id == trade_id)
            )
            t = result.scalar_one()

            # Calculate PnL
            if t.direction == "LONG":
                pnl_pct = ((body.exit_price - t.entry_price) / t.entry_price) * 100
            else:
                pnl_pct = ((t.entry_price - body.exit_price) / t.entry_price) * 100
            pnl_pct_leveraged = pnl_pct * t.leverage
            pnl_usdt = t.position_size_usdt * (pnl_pct_leveraged / 100)

            trade_result = TradeResult(
                trade_advice_id=trade_id,
                telegram_id=t.telegram_id,
                direction=t.direction,
                entry_price=t.entry_price,
                exit_price=body.exit_price,
                leverage=t.leverage,
                position_size_usdt=t.position_size_usdt,
                pnl_usdt=pnl_usdt,
                pnl_pct=pnl_pct,
                pnl_pct_leveraged=pnl_pct_leveraged,
                was_winner=pnl_usdt > 0,
                close_reason=body.reason,
                duration_minutes=int((datetime.utcnow() - (t.opened_at or t.timestamp)).total_seconds() / 60) if t.opened_at else 0,
            )
            session.add(trade_result)

            t.status = "closed"
            t.closed_at = datetime.utcnow()
            t.close_reason = body.reason
            await session.commit()
            await session.refresh(trade_result)

        return {
            "trade_id": trade_id,
            "pnl_usdt": trade_result.pnl_usdt,
            "pnl_pct_leveraged": trade_result.pnl_pct_leveraged,
            "was_winner": trade_result.was_winner,
            "balance_after": None,
        }

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
