import logging
from functools import lru_cache

import numpy as np

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """Analyzes sentiment from news headlines and social media text."""

    def __init__(self):
        self._vader = None
        self._finbert = None
        self._finbert_tokenizer = None

    @property
    def vader(self):
        if self._vader is None:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            self._vader = SentimentIntensityAnalyzer()
        return self._vader

    def load_finbert(self):
        """Load FinBERT model (lazy, only when needed)."""
        if self._finbert is None:
            try:
                from transformers import AutoModelForSequenceClassification, AutoTokenizer
                model_name = "ProsusAI/finbert"
                self._finbert_tokenizer = AutoTokenizer.from_pretrained(model_name)
                self._finbert = AutoModelForSequenceClassification.from_pretrained(model_name)
                self._finbert.eval()
                logger.info("FinBERT loaded successfully")
            except Exception as e:
                logger.warning(f"Could not load FinBERT: {e}. Using VADER only.")

    def analyze_text(self, text: str, use_finbert: bool = False) -> dict:
        """Analyze sentiment of a text string."""
        vader_score = self._vader_score(text)

        result = {
            "text": text[:200],
            "vader_score": vader_score,
            "finbert_score": None,
            "combined_score": vader_score,
        }

        if use_finbert and self._finbert is not None:
            finbert_score = self._finbert_score(text)
            result["finbert_score"] = finbert_score
            # Weighted combination: FinBERT is better for financial text
            result["combined_score"] = 0.6 * finbert_score + 0.4 * vader_score

        return result

    def analyze_batch(self, texts: list[str], use_finbert: bool = False) -> list[dict]:
        """Analyze sentiment of multiple texts."""
        return [self.analyze_text(t, use_finbert) for t in texts]

    def get_aggregate_sentiment(self, texts: list[str], use_finbert: bool = False) -> dict:
        """Get aggregate sentiment metrics from a batch of texts."""
        if not texts:
            return {
                "mean_score": 0.0,
                "median_score": 0.0,
                "bullish_pct": 0.0,
                "bearish_pct": 0.0,
                "neutral_pct": 0.0,
                "volume": 0,
                "std_dev": 0.0,
            }

        results = self.analyze_batch(texts, use_finbert)
        scores = [r["combined_score"] for r in results]

        bullish = sum(1 for s in scores if s > 0.1)
        bearish = sum(1 for s in scores if s < -0.1)
        neutral = len(scores) - bullish - bearish

        return {
            "mean_score": float(np.mean(scores)),
            "median_score": float(np.median(scores)),
            "bullish_pct": bullish / len(scores) * 100,
            "bearish_pct": bearish / len(scores) * 100,
            "neutral_pct": neutral / len(scores) * 100,
            "volume": len(scores),
            "std_dev": float(np.std(scores)),
        }

    def detect_volume_spike(self, current_count: int, historical_avg: float) -> bool:
        """Detect unusual news volume (potential high-impact event)."""
        if historical_avg <= 0:
            return False
        return current_count > historical_avg * 2

    def _vader_score(self, text: str) -> float:
        """Get VADER compound sentiment score (-1 to 1)."""
        scores = self.vader.polarity_scores(text)
        return scores["compound"]

    def _finbert_score(self, text: str) -> float:
        """Get FinBERT sentiment score (-1 to 1)."""
        try:
            import torch

            inputs = self._finbert_tokenizer(
                text, return_tensors="pt", truncation=True, max_length=512, padding=True
            )
            with torch.no_grad():
                outputs = self._finbert(** inputs)

            probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
            # FinBERT: [positive, negative, neutral]
            positive = probs[0][0].item()
            negative = probs[0][1].item()
            return positive - negative  # Range: -1 to 1

        except Exception as e:
            logger.error(f"FinBERT error: {e}")
            return self._vader_score(text)

    # Crypto-specific keyword sentiment modifiers
    BULLISH_KEYWORDS = [
        "etf approved", "institutional", "adoption", "partnership",
        "bullish", "rally", "surge", "breakout", "all-time high",
        "accumulation", "halving", "upgrade", "support",
    ]

    BEARISH_KEYWORDS = [
        "hack", "exploit", "crash", "ban", "regulation", "tariff",
        "bearish", "dump", "sell-off", "bankruptcy", "fraud",
        "lawsuit", "sec", "crackdown", "investigation",
    ]

    def keyword_modifier(self, text: str) -> float:
        """Additional sentiment modifier based on crypto-specific keywords."""
        text_lower = text.lower()
        score = 0.0

        for kw in self.BULLISH_KEYWORDS:
            if kw in text_lower:
                score += 0.1

        for kw in self.BEARISH_KEYWORDS:
            if kw in text_lower:
                score -= 0.1

        return max(-0.5, min(0.5, score))
