import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "This is not financial advice. Predictions are ML-generated and may be incorrect. "
    "Always do your own research. Past accuracy does not guarantee future results."
)


class SignalGenerator:
    """Generates trading signals from ensemble predictions."""

    # Action thresholds
    STRONG_BUY_THRESHOLD = 0.75
    BUY_THRESHOLD = 0.60
    SELL_THRESHOLD = 0.40
    STRONG_SELL_THRESHOLD = 0.25

    # ATR multipliers for targets and stops
    TARGET_ATR_MULTIPLIER = 2.5
    STOP_ATR_MULTIPLIER = 1.5

    def generate(
        self,
        predictions: dict,
        current_price: float,
        atr: float,
        volatility: float = None,
    ) -> dict:
        """
        Generate trading signals from predictions.

        Args:
            predictions: Dict from EnsemblePredictor with timeframe predictions
            current_price: Current BTC price
            atr: Current Average True Range
            volatility: Current 24h volatility percentage

        Returns:
            Dict with signal for each timeframe
        """
        signals = {}

        for timeframe, pred in predictions.items():
            bullish_prob = pred.get("bullish_prob", 0.5)
            confidence = pred.get("confidence", 0)
            magnitude = pred.get("magnitude_pct", 0)

            # Determine action
            action = self._determine_action(bullish_prob, confidence)

            # Calculate prices
            direction_mult = 1 if bullish_prob > 0.5 else -1
            atr_buffer = atr * 0.1  # Small buffer for entry

            entry_price = current_price + (atr_buffer * direction_mult * -1)  # Slightly better entry
            target_price = current_price + (atr * self.TARGET_ATR_MULTIPLIER * direction_mult)
            stop_loss = current_price - (atr * self.STOP_ATR_MULTIPLIER * direction_mult)

            # If magnitude prediction available, use it for target (capped to sane range)
            magnitude = max(-30, min(30, magnitude))
            if abs(magnitude) > 0.1:
                target_price = current_price * (1 + magnitude / 100)

            # Risk rating (1-10)
            risk_rating = self._calculate_risk(confidence, volatility, atr, current_price)

            # Generate reasoning
            reasoning = self._generate_reasoning(pred, action, volatility)

            signals[timeframe] = {
                "action": action,
                "direction": pred.get("direction", "neutral"),
                "confidence": round(confidence, 1),
                "entry_price": round(entry_price, 2),
                "target_price": round(target_price, 2),
                "stop_loss": round(stop_loss, 2),
                "current_price": round(current_price, 2),
                "risk_rating": risk_rating,
                "risk_reward_ratio": round(
                    abs(target_price - entry_price) / max(abs(entry_price - stop_loss), 0.01), 2
                ),
                "timeframe": timeframe,
                "reasoning": reasoning,
                "model_outputs": pred.get("model_outputs", {}),
                "timestamp": datetime.utcnow().isoformat(),
                "disclaimer": DISCLAIMER,
            }

        return signals

    def _determine_action(self, bullish_prob: float, confidence: float) -> str:
        """Map probability to action."""
        if confidence < 20:
            return "hold"

        if bullish_prob >= self.STRONG_BUY_THRESHOLD:
            return "strong_buy"
        elif bullish_prob >= self.BUY_THRESHOLD:
            return "buy"
        elif bullish_prob <= self.STRONG_SELL_THRESHOLD:
            return "strong_sell"
        elif bullish_prob <= self.SELL_THRESHOLD:
            return "sell"
        else:
            return "hold"

    def _calculate_risk(
        self,
        confidence: float,
        volatility: float | None,
        atr: float,
        price: float,
    ) -> int:
        """Calculate risk rating from 1 (lowest) to 10 (highest)."""
        risk = 5  # Base risk

        # Lower confidence = higher risk
        if confidence < 30:
            risk += 2
        elif confidence < 50:
            risk += 1
        elif confidence > 70:
            risk -= 1

        # Higher volatility = higher risk
        if volatility is not None:
            if volatility > 5:
                risk += 2
            elif volatility > 3:
                risk += 1
            elif volatility < 1:
                risk -= 1

        # ATR as % of price
        atr_pct = (atr / price) * 100 if price > 0 else 0
        if atr_pct > 3:
            risk += 1
        elif atr_pct < 1:
            risk -= 1

        return max(1, min(10, risk))

    def _generate_reasoning(self, pred: dict, action: str, volatility: float | None) -> str:
        """Generate human-readable reasoning for the signal."""
        model_outputs = pred.get("model_outputs", {})
        parts = []

        # LSTM signal
        lstm = model_outputs.get("lstm", {})
        if lstm:
            lstm_dir = "bullish" if lstm.get("bullish_prob", 0.5) > 0.5 else "bearish"
            parts.append(f"LSTM model is {lstm_dir} ({lstm.get('confidence', 0):.0f}% conf)")

        # XGBoost signal
        xgb = model_outputs.get("xgboost", {})
        if xgb:
            xgb_dir = "bullish" if xgb.get("bullish_prob", 0.5) > 0.5 else "bearish"
            parts.append(f"XGBoost is {xgb_dir} ({xgb.get('confidence', 0):.0f}% conf)")

        # Sentiment
        sent = model_outputs.get("sentiment", {})
        if sent:
            parts.append(f"Sentiment: {sent.get('direction', 'neutral')} (score: {sent.get('score', 0):.2f})")

        # Volatility warning
        if volatility and volatility > 4:
            parts.append(f"High volatility ({volatility:.1f}%) - increased risk")

        action_text = action.replace("_", " ").title()
        return f"Signal: {action_text}. " + ". ".join(parts) + "."
