import logging
from datetime import datetime, timedelta

from sqlalchemy import select, desc
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database import async_session, PortfolioState, TradeAdvice, TradeResult

logger = logging.getLogger(__name__)


async def get_or_create_portfolio(telegram_id: int) -> PortfolioState:
    """Get existing portfolio or create with default $10 balance.

    Uses with_for_update() to prevent race conditions, and catches
    IntegrityError in case of concurrent INSERT attempts.
    """
    async with async_session() as session:
        result = await session.execute(
            select(PortfolioState)
            .where(PortfolioState.telegram_id == telegram_id)
            .with_for_update()
        )
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            try:
                portfolio = PortfolioState(
                    telegram_id=telegram_id,
                    balance_usdt=settings.advisor_default_balance,
                    initial_balance=settings.advisor_default_balance,
                )
                session.add(portfolio)
                await session.commit()
                await session.refresh(portfolio)
            except IntegrityError:
                await session.rollback()
                # Another request created it concurrently — fetch the existing row
                result = await session.execute(
                    select(PortfolioState)
                    .where(PortfolioState.telegram_id == telegram_id)
                )
                portfolio = result.scalar_one_or_none()

        return portfolio


async def update_balance(telegram_id: int, amount: float) -> PortfolioState:
    """Manually set portfolio balance."""
    async with async_session() as session:
        result = await session.execute(
            select(PortfolioState).where(PortfolioState.telegram_id == telegram_id)
        )
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            portfolio = PortfolioState(
                telegram_id=telegram_id,
                balance_usdt=amount,
                initial_balance=amount,
            )
            session.add(portfolio)
        else:
            portfolio.balance_usdt = amount

        await session.commit()
        await session.refresh(portfolio)
        return portfolio


async def record_trade_result(
    telegram_id: int,
    trade_id: int,
    exit_price: float,
    reason: str = "manual_close",
) -> TradeResult | None:
    """Record trade close: calculate PnL, update balance, apply cooldown logic."""
    async with async_session() as session:
        # Get trade advice (lock row to prevent concurrent close)
        result = await session.execute(
            select(TradeAdvice).where(
                TradeAdvice.id == trade_id,
                TradeAdvice.telegram_id == telegram_id,
            ).with_for_update()
        )
        trade = result.scalar_one_or_none()
        if not trade or trade.status in ("closed", "cancelled"):
            return None

        # Get portfolio (lock row to prevent concurrent balance updates)
        result = await session.execute(
            select(PortfolioState)
            .where(PortfolioState.telegram_id == telegram_id)
            .with_for_update()
        )
        portfolio = result.scalar_one_or_none()
        if not portfolio:
            return None

        # Calculate PnL
        entry = trade.entry_price
        if trade.direction == "LONG":
            pnl_pct = ((exit_price - entry) / entry) * 100
        else:
            pnl_pct = ((entry - exit_price) / entry) * 100

        pnl_pct_leveraged = pnl_pct * trade.leverage
        pnl_usdt = trade.position_size_usdt * (pnl_pct_leveraged / 100)
        was_winner = pnl_usdt > 0

        # Duration
        opened_at = trade.opened_at or trade.timestamp
        duration = int((datetime.utcnow() - opened_at).total_seconds() / 60)

        balance_before = portfolio.balance_usdt
        balance_after = balance_before + pnl_usdt

        # Create trade result
        trade_result = TradeResult(
            trade_advice_id=trade_id,
            telegram_id=telegram_id,
            direction=trade.direction,
            entry_price=entry,
            exit_price=exit_price,
            leverage=trade.leverage,
            position_size_usdt=trade.position_size_usdt,
            pnl_usdt=round(pnl_usdt, 4),
            pnl_pct=round(pnl_pct, 4),
            pnl_pct_leveraged=round(pnl_pct_leveraged, 4),
            was_winner=was_winner,
            close_reason=reason,
            duration_minutes=duration,
            balance_before=round(balance_before, 4),
            balance_after=round(balance_after, 4),
        )
        session.add(trade_result)

        # Update portfolio
        portfolio.balance_usdt = max(0, round(balance_after, 4))
        portfolio.total_pnl = round(portfolio.total_pnl + pnl_usdt, 4)
        if portfolio.initial_balance > 0:
            portfolio.total_pnl_pct = round(
                (portfolio.balance_usdt - portfolio.initial_balance) / portfolio.initial_balance * 100, 2
            )
        portfolio.total_trades += 1

        if was_winner:
            portfolio.winning_trades += 1
            portfolio.consecutive_wins += 1
            portfolio.consecutive_losses = 0
        else:
            portfolio.losing_trades += 1
            portfolio.consecutive_losses += 1
            portfolio.consecutive_wins = 0

            # Track daily loss
            today = datetime.utcnow().strftime("%Y-%m-%d")
            if portfolio.daily_loss_date != today:
                portfolio.daily_loss_today = 0.0
                portfolio.daily_loss_date = today

            portfolio.daily_loss_today += abs(pnl_usdt)

            # Check daily loss limit -> cooldown
            # Use start-of-day balance (current balance + losses today) as denominator
            # to stay consistent with entry_detector.py
            start_of_day_balance = max(portfolio.balance_usdt + portfolio.daily_loss_today, 0.01)
            daily_loss_pct = (portfolio.daily_loss_today / start_of_day_balance) * 100
            if daily_loss_pct >= portfolio.daily_max_loss_pct:
                portfolio.cooldown_until = datetime.utcnow() + timedelta(
                    hours=settings.advisor_cooldown_hours
                )
                logger.warning(
                    f"Portfolio {telegram_id}: daily loss limit hit "
                    f"({daily_loss_pct:.1f}%), cooldown until {portfolio.cooldown_until}"
                )

            # Cooldown after 3 consecutive losses
            if portfolio.consecutive_losses >= 3:
                portfolio.cooldown_until = datetime.utcnow() + timedelta(
                    hours=settings.advisor_cooldown_hours
                )

        # Close the trade advice
        trade.status = "closed"
        trade.closed_at = datetime.utcnow()
        trade.close_reason = reason

        await session.commit()
        await session.refresh(trade_result)

        logger.info(
            f"Trade #{trade_id} closed: {trade.direction} "
            f"PnL=${pnl_usdt:+.4f} ({pnl_pct_leveraged:+.2f}%) "
            f"Balance: ${balance_before:.2f} -> ${portfolio.balance_usdt:.2f}"
        )

        return trade_result


async def get_stats(telegram_id: int) -> dict:
    """Get comprehensive trading stats for a user."""
    async with async_session() as session:
        result = await session.execute(
            select(PortfolioState).where(PortfolioState.telegram_id == telegram_id)
        )
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            return {"error": "No portfolio found"}

        result = await session.execute(
            select(TradeResult)
            .where(TradeResult.telegram_id == telegram_id)
            .order_by(desc(TradeResult.timestamp))
        )
        results = result.scalars().all()

        # Count active trades
        active_result = await session.execute(
            select(TradeAdvice).where(
                TradeAdvice.telegram_id == telegram_id,
                TradeAdvice.status.in_(["opened", "partial_tp"]),
                TradeAdvice.is_mock == False,
            )
        )
        active_trades_count = len(active_result.scalars().all())

    win_rate = 0.0
    avg_win = 0.0
    avg_loss = 0.0
    profit_factor = 0.0
    best_trade = 0.0
    worst_trade = 0.0

    if results:
        winners = [r for r in results if r.was_winner]
        losers = [r for r in results if not r.was_winner]

        if portfolio.total_trades > 0:
            win_rate = portfolio.winning_trades / portfolio.total_trades * 100

        if winners:
            avg_win = sum(r.pnl_usdt for r in winners) / len(winners)
            best_trade = max(r.pnl_usdt for r in winners)

        if losers:
            avg_loss = sum(r.pnl_usdt for r in losers) / len(losers)
            worst_trade = min(r.pnl_usdt for r in losers)

        total_wins = sum(r.pnl_usdt for r in winners) if winners else 0
        total_losses = abs(sum(r.pnl_usdt for r in losers)) if losers else 0
        if total_losses > 0:
            profit_factor = total_wins / total_losses

    # Progress to $10K
    target = 10_000.0
    progress_pct = min(100.0, (portfolio.balance_usdt / target) * 100)

    return {
        "balance": round(portfolio.balance_usdt, 4),
        "initial_balance": portfolio.initial_balance,
        "total_pnl": round(portfolio.total_pnl, 4),
        "total_pnl_pct": round(portfolio.total_pnl_pct, 2),
        "total_trades": portfolio.total_trades,
        "winning_trades": portfolio.winning_trades,
        "losing_trades": portfolio.losing_trades,
        "win_rate": round(win_rate, 1),
        "avg_win": round(avg_win, 4),
        "avg_loss": round(avg_loss, 4),
        "best_trade": round(best_trade, 4),
        "worst_trade": round(worst_trade, 4),
        "profit_factor": round(profit_factor, 2),
        "consecutive_wins": portfolio.consecutive_wins,
        "consecutive_losses": portfolio.consecutive_losses,
        "progress_to_10k": round(progress_pct, 2),
        "target": target,
        "active_trades": active_trades_count,
        "is_active": portfolio.is_active,
        "cooldown_until": portfolio.cooldown_until.isoformat() if portfolio.cooldown_until else None,
    }
