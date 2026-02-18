import logging

from app.config import settings

logger = logging.getLogger(__name__)


def fractional_kelly(win_rate: float, avg_win_loss_ratio: float) -> float:
    """Calculate fractional Kelly criterion position size.

    f* = (p * b - q) / b
    Then apply kelly_fraction multiplier and clamp.

    Args:
        win_rate: Historical win rate (0-1)
        avg_win_loss_ratio: Average win / average loss (b)

    Returns:
        Position size as fraction of portfolio (0-1)
    """
    p = max(0.01, min(0.99, win_rate))
    q = 1.0 - p
    b = max(0.01, avg_win_loss_ratio)

    f_star = (p * b - q) / b

    if f_star <= 0:
        return 0.0  # No edge — don't trade

    f = settings.advisor_kelly_fraction * f_star

    # Clamp to [2%, max_risk_per_trade_pct]
    return max(0.02, min(f, 0.10))  # max 10% default


def calculate_leverage(
    confidence: float,
    consecutive_losses: int,
    max_leverage: int = None,
) -> int:
    """Calculate leverage from confidence + anti-martingale adjustment.

    Args:
        confidence: Prediction confidence (0-100)
        consecutive_losses: Number of consecutive losing trades
        max_leverage: Maximum allowed leverage

    Returns:
        Leverage multiplier (integer)
    """
    if max_leverage is None:
        max_leverage = settings.advisor_max_leverage

    # Base leverage from confidence
    if confidence >= 85:
        base = 18
    elif confidence >= 70:
        base = 14
    elif confidence >= 55:
        base = 10
    else:
        base = 7

    # Anti-martingale: reduce after consecutive losses
    loss_factor = max(0.5, 1.0 - consecutive_losses * 0.25)
    final = int(base * loss_factor)

    return max(5, min(final, max_leverage))


def calculate_position_size(
    balance: float,
    leverage: int,
    kelly_fraction: float,
    stop_loss_pct: float,
) -> dict:
    """Calculate full position sizing.

    Args:
        balance: Available USDT balance
        leverage: Leverage multiplier
        kelly_fraction: Kelly criterion fraction (0-1)
        stop_loss_pct: Distance to stop-loss as percentage of entry

    Returns:
        Dict with margin, notional, risk_amount, position_size_pct
    """
    # Margin = balance * kelly_fraction
    margin = balance * kelly_fraction

    # Notional position = margin * leverage
    notional = margin * leverage

    # Risk amount = margin * (stop_loss_pct / 100) * leverage
    # But capped at margin (can't lose more than margin without liquidation)
    risk_amount = min(margin, notional * (stop_loss_pct / 100))

    return {
        "margin_usdt": round(margin, 4),
        "notional_usdt": round(notional, 4),
        "risk_amount_usdt": round(risk_amount, 4),
        "position_size_pct": round(kelly_fraction * 100, 2),
    }
