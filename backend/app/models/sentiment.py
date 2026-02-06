import logging

from app.features.sentiment import SentimentAnalyzer

logger = logging.getLogger(__name__)


class SentimentModel:
    """Sentiment model wrapper that provides sentiment scores as prediction modifiers."""

    def __init__(self, use_finbert: bool = False):
        self.analyzer = SentimentAnalyzer()
        self.use_finbert = use_finbert

        if use_finbert:
            self.analyzer.load_finbert()

    def get_sentiment_signal(self, news_data: list[dict] = None, reddit_data: list[dict] = None) -> dict:
        """
        Generate a sentiment-based signal.

        Returns:
            Dict with sentiment score, direction, and confidence
        """
        all_texts = []

        if news_data:
            all_texts.extend([n.get("title", "") for n in news_data if n.get("title")])

        if reddit_data:
            posts = reddit_data if isinstance(reddit_data, list) else reddit_data.get("posts", [])
            all_texts.extend([p.get("title", "") for p in posts if p.get("title")])

        if not all_texts:
            return {
                "score": 0.0,
                "direction": "neutral",
                "confidence": 0.0,
                "modifier": 1.0,  # No modification
                "volume": 0,
            }

        agg = self.analyzer.get_aggregate_sentiment(all_texts, self.use_finbert)

        score = agg["mean_score"]
        confidence = min(abs(score) * 100, 100)

        # Sentiment modifier: amplifies or dampens ML predictions
        # Score range: -1 to 1 → modifier range: 0.5 to 1.5
        modifier = 1.0 + (score * 0.5)

        if score > 0.2:
            direction = "bullish"
        elif score < -0.2:
            direction = "bearish"
        else:
            direction = "neutral"

        return {
            "score": score,
            "direction": direction,
            "confidence": confidence,
            "modifier": modifier,
            "volume": agg["volume"],
            "bullish_pct": agg["bullish_pct"],
            "bearish_pct": agg["bearish_pct"],
        }
