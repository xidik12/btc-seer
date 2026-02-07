import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import async_session, TradeAdvice, PortfolioState

logger = logging.getLogger(__name__)


async def check_open_trades(
    current_price: float,
    latest_prediction: dict | None = None,
) -> list[dict]:
    """Check all open trades for SL/TP hits, reversals, and expiry.

    Runs every 5 minutes. Returns a list of alert dicts to send.

    Args:
        current_price: Current BTC price
        latest_prediction: Latest ensemble prediction (for reversal detection)

    Returns:
        List of alert dicts: {telegram_id, trade_id, alert_type, message}
    """
    alerts = []

    async with async_session() as session:
        result = await session.execute(
            select(TradeAdvice).where(
                TradeAdvice.status.in_(["opened", "partial_tp"])
            )
        )
        open_trades = result.scalars().all()

        if not open_trades:
            return alerts

        for trade in open_trades:
            trade_alerts = _evaluate_trade(trade, current_price, latest_prediction)

            for alert in trade_alerts:
                alert["telegram_id"] = trade.telegram_id
                alert["trade_id"] = trade.id
                alerts.append(alert)

                # Update trade flags
                if alert["alert_type"] == "breakeven":
                    trade.breakeven_alert_sent = True
                elif alert["alert_type"] == "partial_tp":
                    trade.partial_tp_alert_sent = True
                    trade.status = "partial_tp"
                elif alert["alert_type"] in ("stop_loss", "take_profit_3", "reversal", "expired"):
                    trade.close_alert_sent = True

        await session.commit()

    return alerts


def _evaluate_trade(
    trade: TradeAdvice,
    price: float,
    prediction: dict | None,
) -> list[dict]:
    """Evaluate a single open trade against current conditions.

    Returns list of alerts for this trade.
    """
    alerts = []
    entry = trade.entry_price
    sl = trade.stop_loss
    tp1 = trade.take_profit_1
    tp2 = trade.take_profit_2 or tp1
    tp3 = trade.take_profit_3 or tp2

    is_long = trade.direction == "LONG"
    risk_distance = abs(entry - sl)

    # Current P&L
    if is_long:
        current_r = (price - entry) / risk_distance if risk_distance > 0 else 0
    else:
        current_r = (entry - price) / risk_distance if risk_distance > 0 else 0

    # --- Check 1: Stop Loss hit ---
    sl_hit = (is_long and price <= sl) or (not is_long and price >= sl)
    if sl_hit and not trade.close_alert_sent:
        pnl_pct = ((price - entry) / entry * 100) if is_long else ((entry - price) / entry * 100)
        leveraged = pnl_pct * trade.leverage
        alerts.append({
            "alert_type": "stop_loss",
            "message": (
                f"STOP LOSS HIT — Trade #{trade.id}\n\n"
                f"{trade.direction} BTC/USDT\n"
                f"Entry: ${entry:,.0f} | SL: ${sl:,.0f}\n"
                f"Current: ${price:,.0f}\n"
                f"PnL: {leveraged:+.2f}% (leveraged)\n\n"
                f"Close this trade now and record the result."
            ),
        })
        return alerts  # SL is terminal, no further checks

    # --- Check 2: +1R profit -> Move SL to breakeven ---
    if current_r >= 1.0 and not trade.breakeven_alert_sent:
        alerts.append({
            "alert_type": "breakeven",
            "message": (
                f"MOVE SL TO BREAKEVEN — Trade #{trade.id}\n\n"
                f"{trade.direction} BTC/USDT at +{current_r:.1f}R\n"
                f"Entry: ${entry:,.0f} | Current: ${price:,.0f}\n\n"
                f"Move your stop-loss to entry (${entry:,.0f}) to secure a risk-free trade."
            ),
        })

    # --- Check 3: TP1 hit -> Take 40% partial profit ---
    tp1_hit = (is_long and price >= tp1) or (not is_long and price <= tp1)
    if tp1_hit and not trade.partial_tp_alert_sent:
        alerts.append({
            "alert_type": "partial_tp",
            "message": (
                f"TP1 HIT — Take 40% Profit — Trade #{trade.id}\n\n"
                f"{trade.direction} BTC/USDT\n"
                f"Entry: ${entry:,.0f} | TP1: ${tp1:,.0f}\n"
                f"Current: ${price:,.0f} (+{current_r:.1f}R)\n\n"
                f"Close 40% of your position now.\n"
                f"Remaining targets: TP2 ${tp2:,.0f} | TP3 ${tp3:,.0f}"
            ),
        })

    # --- Check 4: TP2 hit ---
    tp2_hit = (is_long and price >= tp2) or (not is_long and price <= tp2)
    if tp2_hit and trade.partial_tp_alert_sent and not trade.close_alert_sent:
        alerts.append({
            "alert_type": "take_profit_2",
            "message": (
                f"TP2 HIT — Take Another 40% — Trade #{trade.id}\n\n"
                f"{trade.direction} BTC/USDT\n"
                f"Entry: ${entry:,.0f} | TP2: ${tp2:,.0f}\n"
                f"Current: ${price:,.0f} (+{current_r:.1f}R)\n\n"
                f"Close another 40%. Let remaining 20% ride to TP3 ${tp3:,.0f}."
            ),
        })

    # --- Check 5: TP3 hit ---
    tp3_hit = (is_long and price >= tp3) or (not is_long and price <= tp3)
    if tp3_hit and not trade.close_alert_sent:
        alerts.append({
            "alert_type": "take_profit_3",
            "message": (
                f"TP3 HIT — CLOSE TRADE — Trade #{trade.id}\n\n"
                f"{trade.direction} BTC/USDT\n"
                f"Entry: ${entry:,.0f} | TP3: ${tp3:,.0f}\n"
                f"Current: ${price:,.0f} (+{current_r:.1f}R)\n\n"
                f"Full target reached! Close remaining position."
            ),
        })

    # --- Check 6: Reversal detection ---
    if prediction and not trade.close_alert_sent:
        pred_dir = prediction.get("direction", "neutral")
        pred_conf = prediction.get("confidence", 0)

        opposing = (
            (is_long and pred_dir == "bearish") or
            (not is_long and pred_dir == "bullish")
        )

        if opposing and pred_conf >= 70:
            alerts.append({
                "alert_type": "reversal",
                "message": (
                    f"REVERSAL DETECTED — Consider Closing — Trade #{trade.id}\n\n"
                    f"{trade.direction} BTC/USDT\n"
                    f"Entry: ${entry:,.0f} | Current: ${price:,.0f}\n\n"
                    f"New prediction: {pred_dir} with {pred_conf:.0f}% confidence.\n"
                    f"This opposes your {trade.direction} position.\n"
                    f"Consider closing to protect profits/limit losses."
                ),
            })

    # --- Check 7: Trade expired (open > 2x timeframe) ---
    tf_hours = {"1h": 1, "4h": 4, "24h": 24}.get(trade.timeframe, 1)
    max_duration = timedelta(hours=tf_hours * 2)
    opened_at = trade.opened_at or trade.timestamp

    if datetime.utcnow() - opened_at > max_duration and not trade.close_alert_sent:
        alerts.append({
            "alert_type": "expired",
            "message": (
                f"SETUP EXPIRED — Consider Closing — Trade #{trade.id}\n\n"
                f"{trade.direction} BTC/USDT\n"
                f"Entry: ${entry:,.0f} | Current: ${price:,.0f}\n"
                f"Open for {(datetime.utcnow() - opened_at).total_seconds() / 3600:.1f}h "
                f"(setup was {trade.timeframe})\n\n"
                f"The original setup timeframe has passed. Consider closing."
            ),
        })

    return alerts
