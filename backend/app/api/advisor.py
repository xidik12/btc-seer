from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select, desc

from app.database import (
    async_session, PortfolioState, TradeAdvice, TradeResult, Price,
    Prediction, Signal, QuantPrediction, IndicatorSnapshot, EventImpact,
    WhaleTransaction,
)
from app.api.admin import _verify_telegram_init_data

router = APIRouter(prefix="/api/advisor", tags=["advisor"])


def _get_authenticated_user(request: Request) -> int:
    """Extract and verify telegram_id from initData (24h session for user routes)."""
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data:
        raise HTTPException(401, "Authentication required")
    user_data = _verify_telegram_init_data(init_data, max_age=86400)  # 24h for user-facing routes
    telegram_id = user_data.get("id")
    if not telegram_id:
        raise HTTPException(401, "Invalid authentication")
    return telegram_id


class BalanceUpdate(BaseModel):
    balance: float


class PortfolioSetup(BaseModel):
    balance: float = 10.0
    max_leverage: int = 20
    max_open_trades: int = 2
    max_risk_per_trade_pct: float = 10.0


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
async def get_portfolio(telegram_id: int, request: Request):
    """Get portfolio state for a user."""
    caller_id = _get_authenticated_user(request)
    if caller_id != telegram_id:
        raise HTTPException(403, "Not authorized to access this portfolio")

    from app.advisor.portfolio import get_stats

    return await get_stats(telegram_id)


@router.post("/portfolio/{telegram_id}/balance")
async def set_balance(telegram_id: int, body: BalanceUpdate, request: Request):
    """Manually set portfolio balance."""
    caller_id = _get_authenticated_user(request)
    if caller_id != telegram_id:
        raise HTTPException(403, "Not authorized to modify this portfolio")

    from app.advisor.portfolio import update_balance

    if body.balance < 0:
        raise HTTPException(400, "Balance must be non-negative")

    portfolio = await update_balance(telegram_id, body.balance)
    return {"balance": portfolio.balance_usdt}


@router.post("/portfolio/{telegram_id}/setup")
async def setup_portfolio(telegram_id: int, body: PortfolioSetup, request: Request):
    """Create or update portfolio with custom settings."""
    caller_id = _get_authenticated_user(request)
    if caller_id != telegram_id:
        raise HTTPException(403, "Not authorized to modify this portfolio")

    if body.balance < 0:
        raise HTTPException(400, "Balance must be non-negative")
    if body.max_leverage < 1 or body.max_leverage > 125:
        raise HTTPException(400, "Max leverage must be 1-125")
    if body.max_open_trades < 1 or body.max_open_trades > 20:
        raise HTTPException(400, "Max open trades must be 1-20")
    if body.max_risk_per_trade_pct < 1 or body.max_risk_per_trade_pct > 100:
        raise HTTPException(400, "Risk per trade must be 1-100%")

    async with async_session() as session:
        result = await session.execute(
            select(PortfolioState).where(PortfolioState.telegram_id == telegram_id)
        )
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            portfolio = PortfolioState(
                telegram_id=telegram_id,
                balance_usdt=body.balance,
                initial_balance=body.balance,
                max_leverage=body.max_leverage,
                max_open_trades=body.max_open_trades,
                max_risk_per_trade_pct=body.max_risk_per_trade_pct,
            )
            session.add(portfolio)
        else:
            portfolio.balance_usdt = body.balance
            portfolio.initial_balance = body.balance
            portfolio.max_leverage = body.max_leverage
            portfolio.max_open_trades = body.max_open_trades
            portfolio.max_risk_per_trade_pct = body.max_risk_per_trade_pct
            portfolio.total_pnl = 0.0
            portfolio.total_pnl_pct = 0.0

        await session.commit()
        await session.refresh(portfolio)

    return {
        "balance": portfolio.balance_usdt,
        "max_leverage": portfolio.max_leverage,
        "max_open_trades": portfolio.max_open_trades,
        "max_risk_per_trade_pct": portfolio.max_risk_per_trade_pct,
        "status": "created",
    }


@router.get("/trades/{telegram_id}")
async def get_trades(telegram_id: int, request: Request, mock: bool = Query(False)):
    """Get open/pending trades for a user. Use ?mock=true for paper trades."""
    caller_id = _get_authenticated_user(request)
    if caller_id != telegram_id:
        raise HTTPException(403, "Not authorized to access these trades")

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
async def get_trade_history(telegram_id: int, request: Request, limit: int = 20, mock: bool = Query(False)):
    """Get trade result history."""
    caller_id = _get_authenticated_user(request)
    if caller_id != telegram_id:
        raise HTTPException(403, "Not authorized to access this trade history")

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
async def create_mock_trade(telegram_id: int, body: MockTradeCreate, request: Request):
    """Create a paper/mock trade."""
    caller_id = _get_authenticated_user(request)
    if caller_id != telegram_id:
        raise HTTPException(403, "Not authorized to create trades for this user")

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
async def mark_trade_opened(trade_id: int, request: Request):
    """Mark a trade as opened by the user."""
    caller_id = _get_authenticated_user(request)

    async with async_session() as session:
        result = await session.execute(
            select(TradeAdvice).where(TradeAdvice.id == trade_id)
        )
        trade = result.scalar_one_or_none()

        if not trade:
            raise HTTPException(404, "Trade not found")
        if trade.telegram_id != caller_id:
            raise HTTPException(403, "Not authorized to modify this trade")
        if trade.status != "pending":
            raise HTTPException(400, f"Trade is already {trade.status}")

        trade.status = "opened"
        trade.opened_at = datetime.utcnow()
        await session.commit()

    return {"status": "opened", "trade_id": trade_id}


@router.post("/trades/{trade_id}/close")
async def close_trade(trade_id: int, body: TradeClose, request: Request):
    """Close a trade with exit price."""
    caller_id = _get_authenticated_user(request)

    async with async_session() as session:
        result = await session.execute(
            select(TradeAdvice).where(TradeAdvice.id == trade_id)
        )
        trade = result.scalar_one_or_none()

    if not trade:
        raise HTTPException(404, "Trade not found")
    if trade.telegram_id != caller_id:
        raise HTTPException(403, "Not authorized to close this trade")
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
async def get_stats_endpoint(telegram_id: int, request: Request):
    """Get comprehensive trading stats."""
    caller_id = _get_authenticated_user(request)
    if caller_id != telegram_id:
        raise HTTPException(403, "Not authorized to access these stats")

    from app.advisor.portfolio import get_stats
    return await get_stats(telegram_id)


@router.get("/feedback")
async def get_feedback(days: int = Query(30, ge=1, le=365)):
    """Get aggregated AI feedback stats from mock trade outcomes."""
    from app.advisor.feedback import get_feedback_stats
    return await get_feedback_stats(days=days)


@router.post("/portfolio/{telegram_id}/update")
async def update_portfolio(telegram_id: int, body: PortfolioSetup, request: Request):
    """Update portfolio settings without resetting PnL."""
    caller_id = _get_authenticated_user(request)
    if caller_id != telegram_id:
        raise HTTPException(403, "Not authorized to modify this portfolio")

    if body.max_leverage < 1 or body.max_leverage > 125:
        raise HTTPException(400, "Max leverage must be 1-125")
    if body.max_open_trades < 1 or body.max_open_trades > 20:
        raise HTTPException(400, "Max open trades must be 1-20")
    if body.max_risk_per_trade_pct < 1 or body.max_risk_per_trade_pct > 100:
        raise HTTPException(400, "Risk per trade must be 1-100%")

    async with async_session() as session:
        result = await session.execute(
            select(PortfolioState).where(PortfolioState.telegram_id == telegram_id)
        )
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            raise HTTPException(404, "Portfolio not found. Set up first.")

        portfolio.balance_usdt = body.balance
        portfolio.max_leverage = body.max_leverage
        portfolio.max_open_trades = body.max_open_trades
        portfolio.max_risk_per_trade_pct = body.max_risk_per_trade_pct
        await session.commit()

    return {"status": "updated"}


@router.post("/suggest/{telegram_id}")
async def suggest_trade(telegram_id: int, request: Request):
    """On-demand trade suggestion using full analysis pipeline.

    Integrates: ensemble prediction, quant theory (15 signals), Elliott Wave,
    Power Law, technical indicators, news/events — everything collected.
    Returns either a new trade suggestion or a detailed analysis explaining why not.
    """
    caller_id = _get_authenticated_user(request)
    if caller_id != telegram_id:
        raise HTTPException(403, "Not authorized to request suggestions for this user")

    from app.advisor.entry_detector import check_entry
    from app.advisor.trade_planner import build_trade_plan
    from app.advisor.portfolio import get_or_create_portfolio
    from app.config import settings

    # Get or create portfolio
    portfolio = await get_or_create_portfolio(telegram_id)
    current_price = await _get_current_price()
    if current_price <= 0:
        raise HTTPException(503, "No price data available")

    # Fetch all latest analysis data
    async with async_session() as session:
        # Latest prediction (1h)
        result = await session.execute(
            select(Prediction).where(Prediction.timeframe == "1h")
            .order_by(desc(Prediction.timestamp)).limit(1)
        )
        pred_row = result.scalar_one_or_none()

        # Latest signal (1h)
        result = await session.execute(
            select(Signal).where(Signal.timeframe == "1h")
            .order_by(desc(Signal.timestamp)).limit(1)
        )
        signal_row = result.scalar_one_or_none()

        # Latest quant prediction
        result = await session.execute(
            select(QuantPrediction).order_by(desc(QuantPrediction.timestamp)).limit(1)
        )
        quant_row = result.scalar_one_or_none()

        # Latest indicators
        result = await session.execute(
            select(IndicatorSnapshot).order_by(desc(IndicatorSnapshot.timestamp)).limit(1)
        )
        ind_row = result.scalar_one_or_none()

        # Recent high-severity events
        since_1h = datetime.utcnow() - timedelta(hours=1)
        result = await session.execute(
            select(EventImpact)
            .where(EventImpact.timestamp >= since_1h)
            .where(EventImpact.severity >= 7)
        )
        events = [
            {"severity": e.severity, "sentiment_score": e.sentiment_score, "category": e.category}
            for e in result.scalars().all()
        ]

        # Recent whale transactions (severity >= 7)
        since_24h = datetime.utcnow() - timedelta(hours=24)
        whale_result = await session.execute(
            select(WhaleTransaction)
            .where(WhaleTransaction.timestamp >= since_24h)
            .where(WhaleTransaction.severity >= 7)
            .order_by(desc(WhaleTransaction.timestamp))
            .limit(20)
        )
        whale_txs = whale_result.scalars().all()
        whale_activity = None
        if whale_txs:
            in_count = sum(1 for w in whale_txs if w.direction == "exchange_in")
            out_count = sum(1 for w in whale_txs if w.direction == "exchange_out")
            total_btc = sum(w.amount_btc for w in whale_txs)
            whale_activity = {
                "count": len(whale_txs),
                "total_btc": round(total_btc, 2),
                "exchange_in": in_count,
                "exchange_out": out_count,
                "bias": "bearish" if in_count > out_count else "bullish" if out_count > in_count else "neutral",
            }

    if not pred_row or not signal_row:
        raise HTTPException(503, "No prediction data yet. Wait for first analysis cycle.")

    # Build dicts for entry detector
    prediction = {
        "direction": pred_row.direction,
        "confidence": pred_row.confidence,
        "model_outputs": pred_row.model_outputs or {},
        "magnitude_pct": pred_row.predicted_change_pct,
    }

    signal = {
        "action": signal_row.action,
        "entry_price": signal_row.entry_price,
        "target_price": signal_row.target_price,
        "stop_loss": signal_row.stop_loss,
        "risk_rating": signal_row.risk_rating,
        "risk_reward_ratio": round(
            abs(signal_row.target_price - signal_row.entry_price)
            / max(abs(signal_row.entry_price - signal_row.stop_loss), 0.01), 2
        ),
    }

    quant = None
    quant_breakdown = {}
    if quant_row:
        quant = {
            "direction": quant_row.direction,
            "confidence": quant_row.confidence,
            "composite_score": quant_row.composite_score,
            "action": quant_row.action,
            "agreement_ratio": quant_row.agreement_ratio or 0,
        }
        quant_breakdown = quant_row.signal_breakdown or {}

    indicators = ind_row.indicators if ind_row else None
    atr_value = (indicators or {}).get("atr", current_price * 0.02)

    # Gather Elliott Wave analysis
    elliott_wave = None
    try:
        from app.api.elliott_wave import _analyze
        import pandas as pd
        async with async_session() as session:
            ew_since = datetime.utcnow() - timedelta(days=120)
            result = await session.execute(
                select(Price).where(Price.timestamp >= ew_since).order_by(Price.timestamp)
            )
            ew_prices = result.scalars().all()

        if ew_prices and len(ew_prices) >= 30:
            ew_df = pd.DataFrame([
                {"timestamp": p.timestamp, "open": p.open, "high": p.high,
                 "low": p.low, "close": p.close, "volume": p.volume}
                for p in ew_prices
            ])
            ew_df["timestamp"] = pd.to_datetime(ew_df["timestamp"])
            ew_df = ew_df.set_index("timestamp").resample("4h").agg({
                "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"
            }).dropna().reset_index()

            if len(ew_df) >= 30:
                ew_result = _analyze(ew_df, lookback=5)
                ew_result.pop("swings", None)
                elliott_wave = ew_result
    except Exception:
        pass

    # Gather Power Law analysis
    power_law = None
    try:
        from app.models.power_law_engine import PowerLawEngine
        engine = PowerLawEngine.from_early_prices()
        fair_value = engine.fair_value(datetime.utcnow())
        deviation = (current_price / fair_value - 1) * 100 if fair_value > 0 else 0
        corridor_pos = current_price / fair_value if fair_value > 0 else 1.0
        power_law = {
            "fair_value": round(fair_value, 2),
            "deviation_pct": round(deviation, 2),
            "corridor_position": round(corridor_pos, 3),
            "zone": (
                "undervalued" if corridor_pos < 0.7
                else "accumulate" if corridor_pos < 0.9
                else "fair_value" if corridor_pos < 1.2
                else "overvalued" if corridor_pos < 1.5
                else "extreme_overvalued"
            ),
        }
    except Exception:
        pass

    # Get user's open trades
    async with async_session() as session:
        result = await session.execute(
            select(TradeAdvice).where(
                TradeAdvice.telegram_id == telegram_id,
                TradeAdvice.status.in_(["opened", "partial_tp", "pending"]),
                TradeAdvice.is_mock == False,
            )
        )
        open_trades = result.scalars().all()

    # Run entry detector
    entry = check_entry(
        portfolio=portfolio,
        prediction=prediction,
        signal=signal,
        quant=quant,
        indicators=indicators,
        open_trades=open_trades,
        events=events,
    )

    # Build comprehensive analysis object (always returned)
    analysis = {
        "prediction": {
            "direction": prediction["direction"],
            "confidence": prediction["confidence"],
            "magnitude_pct": prediction.get("magnitude_pct"),
            "model_outputs": prediction.get("model_outputs", {}),
        },
        "quant": {
            "composite_score": quant["composite_score"] if quant else None,
            "action": quant["action"] if quant else None,
            "agreement_ratio": quant["agreement_ratio"] if quant else None,
            "breakdown": quant_breakdown,
        },
        "elliott_wave": {
            "pattern": elliott_wave["wave_count"]["pattern"] if elliott_wave else None,
            "current_wave": elliott_wave["wave_count"]["current_wave"] if elliott_wave else None,
            "direction": elliott_wave["wave_count"]["direction"] if elliott_wave else None,
            "confidence": elliott_wave.get("confidence") if elliott_wave else None,
            "summary": elliott_wave.get("summary") if elliott_wave else None,
            "fib_targets": elliott_wave.get("fibonacci_targets") if elliott_wave else None,
            "divergences": elliott_wave.get("divergences", []) if elliott_wave else [],
        },
        "power_law": power_law,
        "indicators": {
            "rsi": (indicators or {}).get("rsi"),
            "macd_hist": (indicators or {}).get("macd_hist"),
            "atr": atr_value,
            "funding_rate": (indicators or {}).get("funding_rate"),
            "fear_greed": (indicators or {}).get("fear_greed_value"),
        },
        "events": events,
        "whale_activity": whale_activity,
        "current_price": current_price,
    }

    if not entry:
        # No entry — return analysis with reason
        return {
            "suggestion": None,
            "reason": "No high-confidence entry detected. Filters not met — waiting for better confluence.",
            "analysis": analysis,
        }

    # Entry detected — build trade plan
    plan = build_trade_plan(
        entry=entry,
        portfolio=portfolio,
        current_price=current_price,
        atr=atr_value,
    )

    # Enrich reasoning with Elliott Wave and Power Law
    reasoning_parts = [plan["reasoning"]]
    if elliott_wave:
        ew_summary = elliott_wave.get("summary", "")
        if ew_summary:
            reasoning_parts.append(f"Elliott: {ew_summary}")
    if power_law:
        reasoning_parts.append(
            f"Power Law: {power_law['zone']} ({power_law['deviation_pct']:+.1f}% from fair value ${power_law['fair_value']:,.0f})"
        )
    plan["reasoning"] = " | ".join(reasoning_parts)

    # Save trade advice
    async with async_session() as session:
        trade_advice = TradeAdvice(
            telegram_id=telegram_id,
            direction=plan["direction"],
            entry_price=plan["entry_price"],
            entry_zone_low=plan["entry_zone_low"],
            entry_zone_high=plan["entry_zone_high"],
            stop_loss=plan["stop_loss"],
            take_profit_1=plan["take_profit_1"],
            take_profit_2=plan["take_profit_2"],
            take_profit_3=plan["take_profit_3"],
            leverage=plan["leverage"],
            position_size_usdt=plan["position_size_usdt"],
            position_size_pct=plan["position_size_pct"],
            risk_amount_usdt=plan["risk_amount_usdt"],
            risk_reward_ratio=plan["risk_reward_ratio"],
            confidence=plan["confidence"],
            risk_rating=plan["risk_rating"],
            reasoning=plan["reasoning"],
            models_agreeing=plan["models_agreeing"],
            urgency=plan["urgency"],
            timeframe=plan["timeframe"],
            prediction_id=pred_row.id,
            signal_id=signal_row.id,
            quant_prediction_id=quant_row.id if quant_row else None,
            status="pending",
        )
        session.add(trade_advice)
        await session.commit()
        await session.refresh(trade_advice)

    return {
        "suggestion": _serialize_trade(trade_advice, current_price),
        "reason": None,
        "analysis": analysis,
    }
