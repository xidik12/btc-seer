import logging
from datetime import datetime

from app.config import settings
from app.database import PortfolioState, TradeAdvice

logger = logging.getLogger(__name__)


def check_entry(
    portfolio: PortfolioState,
    prediction: dict,
    signal: dict,
    quant: dict | None,
    indicators: dict | None,
    open_trades: list[TradeAdvice],
    events: list | None = None,
) -> dict | None:
    """Smart entry detection — filters for high-confidence confluence setups.

    All filters must pass for an entry signal.

    Args:
        portfolio: User's portfolio state
        prediction: Latest ensemble prediction (1h timeframe preferred)
        signal: Latest trading signal
        quant: Latest quant prediction (or None)
        indicators: Latest indicator snapshot (or None)
        open_trades: List of currently open TradeAdvice records
        events: Recent high-severity events (or None)

    Returns:
        Dict with entry details if all filters pass, or None to skip.
    """
    reasons_skipped = []

    # --- Filter 1: Not in cooldown, daily loss limit not reached ---
    if portfolio.cooldown_until and datetime.utcnow() < portfolio.cooldown_until:
        reasons_skipped.append("cooldown active")
        logger.info(f"Entry skip: {', '.join(reasons_skipped)}")
        return None

    today = datetime.utcnow().strftime("%Y-%m-%d")
    if portfolio.daily_loss_date == today and portfolio.balance_usdt > 0:
        # Use start-of-day balance as denominator (balance + losses accumulated today)
        # to stay consistent with the close trigger in portfolio.py
        start_of_day_balance = max(portfolio.balance_usdt + portfolio.daily_loss_today, 0.01)
        daily_loss_pct = (portfolio.daily_loss_today / start_of_day_balance) * 100
        if daily_loss_pct >= portfolio.daily_max_loss_pct:
            reasons_skipped.append(f"daily loss limit ({daily_loss_pct:.1f}%)")
            logger.info(f"Entry skip: {', '.join(reasons_skipped)}")
            return None

    # --- Filter 2: Max open trades not exceeded ---
    active_open = [t for t in open_trades if t.status in ("opened", "partial_tp")]
    if len(active_open) >= portfolio.max_open_trades:
        reasons_skipped.append(f"max open trades ({len(active_open)}/{portfolio.max_open_trades})")
        logger.info(f"Entry skip: {', '.join(reasons_skipped)}")
        return None

    # --- Filter 3: Ensemble confidence >= min ---
    confidence = prediction.get("confidence", 0)
    if confidence < settings.advisor_min_confidence:
        reasons_skipped.append(f"low confidence ({confidence:.0f}% < {settings.advisor_min_confidence}%)")
        logger.info(f"Entry skip: {', '.join(reasons_skipped)}")
        return None

    # --- Filter 4: At least N models agree ---
    model_outputs = prediction.get("model_outputs", {})
    direction = prediction.get("direction", "neutral")
    if direction == "neutral":
        reasons_skipped.append("neutral direction")
        logger.info(f"Entry skip: {', '.join(reasons_skipped)}")
        return None

    models_agreeing = []
    for name, output in model_outputs.items():
        model_dir = None
        if isinstance(output, dict):
            bp = output.get("bullish_prob", 0.5)
            if bp > 0.55:
                model_dir = "bullish"
            elif bp < 0.45:
                model_dir = "bearish"
            else:
                model_dir = "neutral"
        if model_dir == direction:
            models_agreeing.append(name.upper())

    # Check quant agreement
    quant_agrees = False
    if quant:
        quant_dir = quant.get("direction", "neutral")
        if quant_dir == direction:
            quant_agrees = True
            models_agreeing.append("Quant")

    if len(models_agreeing) < settings.advisor_min_models_agreeing:
        reasons_skipped.append(f"insufficient model agreement ({len(models_agreeing)}/{settings.advisor_min_models_agreeing})")
        logger.info(f"Entry skip: {', '.join(reasons_skipped)}")
        return None

    # --- Filter 5: Risk/reward >= min ---
    rr = signal.get("risk_reward_ratio", 0)
    if rr < settings.advisor_min_risk_reward:
        reasons_skipped.append(f"low R:R ({rr:.1f} < {settings.advisor_min_risk_reward})")
        logger.info(f"Entry skip: {', '.join(reasons_skipped)}")
        return None

    # --- Filter 6: RSI sanity check ---
    if indicators:
        rsi = indicators.get("rsi")
        if rsi is not None:
            if direction == "bullish" and rsi > 80:
                reasons_skipped.append(f"RSI overbought ({rsi:.0f})")
                logger.info(f"Entry skip: {', '.join(reasons_skipped)}")
                return None
            if direction == "bearish" and rsi < 20:
                reasons_skipped.append(f"RSI oversold ({rsi:.0f})")
                logger.info(f"Entry skip: {', '.join(reasons_skipped)}")
                return None

    # --- Filter 7: High-severity negative event opposes direction ---
    if events:
        for event in events:
            severity = event.get("severity", 0)
            sent = event.get("sentiment_score", 0)
            if severity >= 7:
                if direction == "bullish" and sent < -0.3:
                    reasons_skipped.append("high-severity bearish event active")
                    logger.info(f"Entry skip: {', '.join(reasons_skipped)}")
                    return None
                if direction == "bearish" and sent > 0.3:
                    reasons_skipped.append("high-severity bullish event active")
                    logger.info(f"Entry skip: {', '.join(reasons_skipped)}")
                    return None

    # --- Filter 8: Quant agreement ratio >= 0.6 (skip if quant unavailable) ---
    if quant and quant.get("agreement_ratio") is not None:
        agreement_ratio = quant.get("agreement_ratio", 0)
        if agreement_ratio < 0.6:
            reasons_skipped.append(f"low quant agreement ({agreement_ratio:.2f})")
            logger.info(f"Entry skip: {', '.join(reasons_skipped)}")
            return None

    # --- Filter 9: No duplicate open trade in same direction ---
    trade_direction = "LONG" if direction == "bullish" else "SHORT"
    for t in active_open:
        if t.direction == trade_direction:
            reasons_skipped.append(f"duplicate {trade_direction} already open")
            logger.info(f"Entry skip: {', '.join(reasons_skipped)}")
            return None

    # All filters passed!
    logger.info(
        f"Entry DETECTED: {trade_direction} | confidence={confidence:.0f}% | "
        f"models={','.join(models_agreeing)} | R:R={rr:.1f}"
    )

    return {
        "direction": trade_direction,
        "confidence": confidence,
        "models_agreeing": models_agreeing,
        "risk_reward": rr,
        "prediction": prediction,
        "signal": signal,
        "quant": quant,
        "indicators": indicators,
    }
