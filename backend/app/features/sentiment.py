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
        self._xlm_model = None
        self._xlm_tokenizer = None

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

    def load_multilingual(self):
        """Load XLM-RoBERTa multilingual sentiment model (lazy)."""
        if self._xlm_model is None:
            try:
                from transformers import AutoModelForSequenceClassification, AutoTokenizer
                model_name = "cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual"
                self._xlm_tokenizer = AutoTokenizer.from_pretrained(model_name)
                self._xlm_model = AutoModelForSequenceClassification.from_pretrained(model_name)
                self._xlm_model.eval()
                logger.info("XLM-RoBERTa multilingual sentiment model loaded")
            except Exception as e:
                logger.warning(f"Could not load XLM-RoBERTa: {e}. Non-English will use VADER fallback.")

    def detect_language(self, text: str) -> str:
        """Detect language of text. Returns ISO 639-1 code (e.g. 'en', 'ru', 'zh-cn', 'es')."""
        try:
            from langdetect import detect
            lang = detect(text)
            return lang
        except Exception:
            return "en"

    def analyze_text(self, text: str, use_finbert: bool = False, language: str = "en") -> dict:
        """Analyze sentiment of a text string.

        For English: uses VADER + optional FinBERT.
        For non-English: uses XLM-RoBERTa if loaded, else VADER fallback.
        """
        if language and language != "en":
            # Non-English path
            xlm_score = self._xlm_score(text)
            kw_mod = self.keyword_modifier(text, language=language)
            combined = max(-1.0, min(1.0, xlm_score + kw_mod))
            return {
                "text": text[:200],
                "vader_score": None,
                "finbert_score": None,
                "xlm_score": xlm_score,
                "combined_score": combined,
                "language": language,
            }

        # English path (original behavior)
        vader_score = self._vader_score(text)

        result = {
            "text": text[:200],
            "vader_score": vader_score,
            "finbert_score": None,
            "combined_score": vader_score,
            "language": "en",
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

    def _xlm_score(self, text: str) -> float:
        """Get XLM-RoBERTa multilingual sentiment score (-1 to 1)."""
        if self._xlm_model is None:
            # Fallback to VADER (works poorly for non-English but better than 0)
            return self._vader_score(text)
        try:
            import torch

            inputs = self._xlm_tokenizer(
                text, return_tensors="pt", truncation=True, max_length=512, padding=True
            )
            with torch.no_grad():
                outputs = self._xlm_model(**inputs)

            probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
            # XLM-RoBERTa sentiment: [negative, neutral, positive]
            negative = probs[0][0].item()
            positive = probs[0][2].item()
            return positive - negative  # Range: -1 to 1

        except Exception as e:
            logger.error(f"XLM-RoBERTa error: {e}")
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

    # Multilingual keyword modifiers
    MULTILINGUAL_BULLISH = {
        "ru": [
            "\u0440\u043e\u0441\u0442", "\u0431\u044b\u0447\u0438\u0439", "\u043f\u0440\u043e\u0440\u044b\u0432", "\u0438\u043d\u0441\u0442\u0438\u0442\u0443\u0446\u0438\u043e\u043d\u0430\u043b\u044c\u043d\u044b\u0439", "\u043f\u0430\u0440\u0442\u043d\u0435\u0440\u0441\u0442\u0432\u043e",
            "\u043f\u0440\u0438\u043d\u044f\u0442\u0438\u0435", "\u0440\u0430\u043b\u043b\u0438", "\u043f\u043e\u0434\u0434\u0435\u0440\u0436\u043a\u0430", "\u0440\u0435\u043a\u043e\u0440\u0434",
        ],
        "zh-cn": [
            "\u725b\u5e02", "\u7a81\u7834", "\u673a\u6784", "\u91c7\u7528", "\u4e0a\u6da8", "\u5229\u597d", "\u5408\u4f5c", "\u5347\u7ea7",
        ],
        "es": [
            "alcista", "ruptura", "institucional", "adopcion", "subida",
            "rally", "soporte", "maximo",
        ],
    }

    MULTILINGUAL_BEARISH = {
        "ru": [
            "\u0432\u0437\u043b\u043e\u043c", "\u043a\u0440\u0430\u0445", "\u0437\u0430\u043f\u0440\u0435\u0442", "\u043c\u0435\u0434\u0432\u0435\u0436\u0438\u0439", "\u043f\u0430\u0434\u0435\u043d\u0438\u0435",
            "\u0431\u0430\u043d\u043a\u0440\u043e\u0442\u0441\u0442\u0432\u043e", "\u0440\u0435\u0433\u0443\u043b\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435", "\u043c\u043e\u0448\u0435\u043d\u043d\u0438\u0447\u0435\u0441\u0442\u0432\u043e",
        ],
        "zh-cn": [
            "\u9ed1\u5ba2", "\u5d29\u76d8", "\u7981\u6b62", "\u718a\u5e02", "\u4e0b\u8dcc", "\u7206\u4ed3", "\u76d1\u7ba1", "\u8bc8\u9a97",
        ],
        "es": [
            "hackeo", "caida", "prohibicion", "bajista", "colapso",
            "bancarrota", "regulacion", "fraude",
        ],
    }

    def keyword_modifier(self, text: str, language: str = "en") -> float:
        """Additional sentiment modifier based on crypto-specific keywords."""
        text_lower = text.lower()
        score = 0.0

        # English keywords always checked
        for kw in self.BULLISH_KEYWORDS:
            if kw in text_lower:
                score += 0.1

        for kw in self.BEARISH_KEYWORDS:
            if kw in text_lower:
                score -= 0.1

        # Multilingual keywords
        lang_key = language if language in self.MULTILINGUAL_BULLISH else None
        if lang_key:
            for kw in self.MULTILINGUAL_BULLISH[lang_key]:
                if kw in text_lower:
                    score += 0.1
            for kw in self.MULTILINGUAL_BEARISH.get(lang_key, []):
                if kw in text_lower:
                    score -= 0.1

        return max(-0.5, min(0.5, score))
