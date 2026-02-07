import logging

from app.advisor.sizing import fractional_kelly, calculate_leverage, calculate_position_size
from app.database import PortfolioState

logger = logging.getLogger(__name__)


def build_trade_plan(
    entry: dict,
    portfolio: PortfolioState,
    current_price: float,
    atr: float,
) -> dict:
    """Generate a complete trade plan with entry, SL, TP, sizing, and reasoning.

    Args:
        entry: Dict from entry_detector.check_entry()
        portfolio: User's portfolio state
        current_price: Current BTC price
        atr: Current Average True Range

    Returns:
        Dict with complete trade plan ready to store as TradeAdvice.
    """
    direction = entry["direction"]
    confidence = entry["confidence"]
    signal = entry["signal"]
    prediction = entry["prediction"]
    quant = entry.get("quant")
    indicators = entry.get("indicators")
    models_agreeing = entry["models_agreeing"]

    # --- Entry Price ---
    # Use current price or slight pullback zone (0.3 * ATR)
    pullback = atr * 0.3
    if direction == "LONG":
        entry_price = current_price
        entry_zone_low = current_price - pullback
        entry_zone_high = current_price + pullback * 0.5
    else:
        entry_price = current_price
        entry_zone_low = current_price - pullback * 0.5
        entry_zone_high = current_price + pullback

    # --- Stop Loss ---
    # Use signal's stop_loss if available, ensure min 1*ATR away, max 5% from entry
    signal_sl = signal.get("stop_loss", 0)
    min_sl_distance = atr * 1.0
    max_sl_distance = entry_price * 0.05

    if direction == "LONG":
        sl = min(signal_sl, entry_price - min_sl_distance) if signal_sl > 0 else entry_price - min_sl_distance
        sl = max(sl, entry_price - max_sl_distance)  # Don't go beyond 5%
    else:
        sl = max(signal_sl, entry_price + min_sl_distance) if signal_sl > 0 else entry_price + min_sl_distance
        sl = min(sl, entry_price + max_sl_distance)

    # Distance to SL as percentage
    sl_distance_pct = abs(entry_price - sl) / entry_price * 100

    # --- Take Profits (3 levels) ---
    risk_distance = abs(entry_price - sl)

    if direction == "LONG":
        tp1 = entry_price + risk_distance * 1.5   # 1.5R
        tp2 = entry_price + risk_distance * 2.5   # 2.5R
        tp3 = entry_price + risk_distance * 4.0   # 4R
    else:
        tp1 = entry_price - risk_distance * 1.5
        tp2 = entry_price - risk_distance * 2.5
        tp3 = entry_price - risk_distance * 4.0

    # Risk/reward ratio (to TP2 which is main target)
    rr_ratio = 2.5  # By construction, TP2 is always 2.5R

    # --- Leverage ---
    leverage = calculate_leverage(
        confidence=confidence,
        consecutive_losses=portfolio.consecutive_losses,
        max_leverage=portfolio.max_leverage,
    )

    # --- Position Sizing (Kelly) ---
    win_rate = 0.55  # Default assumption
    if portfolio.total_trades >= 5:
        win_rate = max(0.3, portfolio.winning_trades / portfolio.total_trades)

    avg_win_loss_ratio = rr_ratio  # Approximate
    kelly_f = fractional_kelly(win_rate, avg_win_loss_ratio)

    sizing = calculate_position_size(
        balance=portfolio.balance_usdt,
        leverage=leverage,
        kelly_fraction=kelly_f,
        stop_loss_pct=sl_distance_pct,
    )

    # --- Urgency ---
    rsi = indicators.get("rsi") if indicators else None
    if rsi is not None:
        if direction == "LONG" and rsi > 65:
            urgency = "wait_for_pullback"
        elif direction == "SHORT" and rsi < 35:
            urgency = "wait_for_pullback"
        else:
            urgency = "enter_now"
    else:
        urgency = "enter_now"

    # --- Reasoning ---
    reasoning_parts = []

    model_outputs = prediction.get("model_outputs", {})
    for name, output in model_outputs.items():
        if isinstance(output, dict):
            bp = output.get("bullish_prob", 0.5)
            conf = output.get("confidence", 0)
            d = "bullish" if bp > 0.5 else "bearish"
            reasoning_parts.append(f"{name.upper()} {d} {conf:.0f}%")

    if quant:
        score = quant.get("composite_score", 0)
        action = quant.get("action", "HOLD")
        reasoning_parts.append(f"Quant {action} {score:+.0f}")

    if indicators:
        if rsi is not None:
            reasoning_parts.append(f"RSI {rsi:.0f}")
        funding = indicators.get("funding_rate")
        if funding is not None:
            fr_label = "positive" if funding > 0 else "negative" if funding < 0 else "neutral"
            reasoning_parts.append(f"Funding {fr_label}")

    reasoning = ". ".join(reasoning_parts) + "." if reasoning_parts else "Confluence signal detected."

    # --- Risk Rating ---
    risk_rating = signal.get("risk_rating", 5)

    return {
        "direction": direction,
        "entry_price": round(entry_price, 2),
        "entry_zone_low": round(entry_zone_low, 2),
        "entry_zone_high": round(entry_zone_high, 2),
        "stop_loss": round(sl, 2),
        "take_profit_1": round(tp1, 2),
        "take_profit_2": round(tp2, 2),
        "take_profit_3": round(tp3, 2),
        "leverage": leverage,
        "position_size_usdt": sizing["margin_usdt"],
        "position_size_pct": sizing["position_size_pct"],
        "risk_amount_usdt": sizing["risk_amount_usdt"],
        "risk_reward_ratio": round(rr_ratio, 2),
        "confidence": round(confidence, 1),
        "risk_rating": risk_rating,
        "reasoning": reasoning,
        "models_agreeing": ", ".join(models_agreeing),
        "urgency": urgency,
        "timeframe": "1h",
    }


def format_trade_plan_message(trade, plan_number: int = None) -> str:
    """Format a trade plan as a Telegram message.

    Args:
        trade: TradeAdvice ORM object or dict
        plan_number: Optional plan number for display

    Returns:
        Formatted HTML string for Telegram
    """
    # Support both ORM objects and dicts
    def g(key, default=None):
        if isinstance(trade, dict):
            return trade.get(key, default)
        return getattr(trade, key, default)

    tid = g("id", "?")
    header = f"TRADE PLAN #{tid}" if plan_number is None else f"TRADE PLAN #{plan_number}"

    direction = g("direction", "?")
    confidence = g("confidence", 0)
    models = g("models_agreeing", "")
    model_count = len(models.split(",")) if models else 0

    entry = g("entry_price", 0)
    leverage = g("leverage", 1)
    margin = g("position_size_usdt", 0)
    balance = margin / (g("position_size_pct", 1) / 100) if g("position_size_pct", 0) > 0 else 0
    pos_pct = g("position_size_pct", 0)
    risk_amt = g("risk_amount_usdt", 0)
    risk_pct = (risk_amt / balance * 100) if balance > 0 else 0

    tp1 = g("take_profit_1", 0)
    tp2 = g("take_profit_2", 0)
    tp3 = g("take_profit_3", 0)
    sl = g("stop_loss", 0)
    rr = g("risk_reward_ratio", 0)

    urgency_label = g("urgency", "enter_now").replace("_", " ")
    reasoning = g("reasoning", "")

    # Calculate approximate TP gains
    if direction == "LONG":
        tp1_gain = (tp1 - entry) / entry * leverage * margin / 100 if entry > 0 else 0
        tp2_gain = (tp2 - entry) / entry * leverage * margin / 100 if entry > 0 else 0
        tp3_gain = (tp3 - entry) / entry * leverage * margin / 100 if entry > 0 else 0
        sl_loss = (entry - sl) / entry * leverage * margin / 100 if entry > 0 else 0
    else:
        tp1_gain = (entry - tp1) / entry * leverage * margin / 100 if entry > 0 else 0
        tp2_gain = (entry - tp2) / entry * leverage * margin / 100 if entry > 0 else 0
        tp3_gain = (entry - tp3) / entry * leverage * margin / 100 if entry > 0 else 0
        sl_loss = (sl - entry) / entry * leverage * margin / 100 if entry > 0 else 0

    text = (
        f"<b>{header}</b>\n\n"
        f"<b>{direction} BTC/USDT</b> | {confidence:.0f}% confidence\n"
        f"{model_count}/5 models agree ({models})\n\n"
        f"<b>ENTRY:</b> <code>${entry:,.0f}</code> ({urgency_label})\n"
        f"<b>LEVERAGE:</b> {leverage}x\n\n"
        f"<b>POSITION</b>\n"
        f"Size: ${margin:.2f} margin ({pos_pct:.1f}% of ${balance:.2f})\n"
        f"Max risk: ${risk_amt:.2f} ({risk_pct:.1f}%)\n\n"
        f"<b>TARGETS</b>\n"
        f"TP1: <code>${tp1:,.0f}</code> (40%) +${tp1_gain:.2f}\n"
        f"TP2: <code>${tp2:,.0f}</code> (40%) +${tp2_gain:.2f}\n"
        f"TP3: <code>${tp3:,.0f}</code> (20%) +${tp3_gain:.2f}\n\n"
        f"<b>STOP LOSS:</b> <code>${sl:,.0f}</code> (-${sl_loss:.2f})\n"
        f"<b>R:R:</b> {rr:.1f}:1\n\n"
        f"<b>WHY:</b> {reasoning}\n"
    )

    return text
