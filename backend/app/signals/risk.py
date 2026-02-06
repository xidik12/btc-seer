import logging

logger = logging.getLogger(__name__)


class RiskAssessor:
    """Provides risk assessment and position sizing suggestions."""

    @staticmethod
    def assess(
        signal: dict,
        portfolio_value: float = 10000,
        max_risk_pct: float = 2.0,
    ) -> dict:
        """
        Assess risk and suggest position sizing.

        Args:
            signal: Signal dict from SignalGenerator
            portfolio_value: Total portfolio value in USD
            max_risk_pct: Maximum risk per trade as percentage

        Returns:
            Risk assessment dict
        """
        entry = signal.get("entry_price", 0)
        stop = signal.get("stop_loss", 0)
        target = signal.get("target_price", 0)
        risk_rating = signal.get("risk_rating", 5)
        confidence = signal.get("confidence", 0)

        # Calculate risk per unit
        risk_per_unit = abs(entry - stop)
        if risk_per_unit == 0:
            risk_per_unit = entry * 0.02  # Default 2% risk

        # Maximum loss allowed
        max_loss = portfolio_value * (max_risk_pct / 100)

        # Position size (how much BTC to trade)
        position_size_btc = max_loss / risk_per_unit if risk_per_unit > 0 else 0
        position_value = position_size_btc * entry

        # Adjust for risk rating and confidence
        risk_multiplier = max(0.3, 1 - (risk_rating - 5) * 0.1)
        confidence_multiplier = max(0.3, confidence / 100)
        adjusted_position = position_value * risk_multiplier * confidence_multiplier

        # Risk/reward ratio
        reward = abs(target - entry)
        rr_ratio = reward / risk_per_unit if risk_per_unit > 0 else 0

        # Warnings
        warnings = []
        if risk_rating >= 8:
            warnings.append("Very high risk — consider reducing position or skipping")
        if confidence < 30:
            warnings.append("Low confidence — models disagree or lack data")
        if rr_ratio < 1.5:
            warnings.append("Unfavorable risk/reward ratio (below 1.5:1)")
        if position_value > portfolio_value * 0.5:
            warnings.append("Position would exceed 50% of portfolio")

        # Conflicting signals
        model_outputs = signal.get("model_outputs", {})
        if model_outputs:
            directions = set()
            for model in model_outputs.values():
                if isinstance(model, dict):
                    prob = model.get("bullish_prob", 0.5)
                    if prob > 0.6:
                        directions.add("bullish")
                    elif prob < 0.4:
                        directions.add("bearish")
                    else:
                        directions.add("neutral")
            if len(directions) > 1:
                warnings.append(f"Conflicting signals between models: {', '.join(directions)}")

        return {
            "position_size_btc": round(position_size_btc, 6),
            "position_value_usd": round(adjusted_position, 2),
            "max_loss_usd": round(max_loss, 2),
            "risk_per_unit": round(risk_per_unit, 2),
            "risk_reward_ratio": round(rr_ratio, 2),
            "risk_rating": risk_rating,
            "risk_level": RiskAssessor._risk_label(risk_rating),
            "warnings": warnings,
            "recommendation": RiskAssessor._recommendation(signal, rr_ratio, risk_rating),
        }

    @staticmethod
    def _risk_label(rating: int) -> str:
        if rating <= 3:
            return "low"
        elif rating <= 6:
            return "medium"
        elif rating <= 8:
            return "high"
        return "very_high"

    @staticmethod
    def _recommendation(signal: dict, rr_ratio: float, risk_rating: int) -> str:
        action = signal.get("action", "hold")
        confidence = signal.get("confidence", 0)

        if action == "hold":
            return "No clear signal — wait for better setup"
        if risk_rating >= 9:
            return "Extreme risk — strongly advise against trading"
        if confidence < 25:
            return "Very low confidence — consider waiting"
        if rr_ratio < 1:
            return "Poor risk/reward — not recommended"
        if rr_ratio >= 2 and risk_rating <= 5 and confidence >= 60:
            return "Favorable setup — good risk/reward with decent confidence"
        return "Proceed with caution — use proper position sizing"
