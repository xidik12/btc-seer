import logging
from datetime import datetime

import numpy as np
import pandas as pd

from app.features.technical import TechnicalFeatures
from app.features.sentiment import SentimentAnalyzer
from app.features.macro import MacroFeatures

logger = logging.getLogger(__name__)


class FeatureBuilder:
    """Combines all features into a unified feature vector for ML models."""

    # Features expected by the ML models
    TECHNICAL_FEATURES = [
        "ema_9", "ema_21", "ema_50", "ema_200", "sma_20",
        "rsi", "macd", "macd_signal", "macd_hist",
        "bb_upper", "bb_lower", "bb_width", "bb_position",
        "atr", "obv", "vwap",
        "roc_1", "roc_6", "roc_12", "roc_24",
        "momentum_10", "momentum_20",
        "volume_ratio", "volatility_24h",
        "price_vs_ema9", "price_vs_ema21", "price_vs_ema50",
        "body_size", "upper_shadow", "lower_shadow",
    ]

    SENTIMENT_FEATURES = [
        "news_sentiment_1h", "news_sentiment_4h", "news_sentiment_24h",
        "news_volume_1h", "news_bullish_pct", "news_bearish_pct",
        "reddit_sentiment", "reddit_volume",
        "social_sentiment_1h", "social_volume_1h",  # Influencer social media
        "social_bullish_pct", "social_bearish_pct",
        "fear_greed_value",
    ]

    MACRO_FEATURES = [
        "dxy_change_1h", "dxy_change_24h",
        "gold_change_1h", "gold_change_24h",
        "sp500_change_1h", "sp500_change_24h",
        "treasury_10y", "treasury_change_1h",
    ]

    ONCHAIN_FEATURES = [
        "hash_rate", "mempool_size", "mempool_fees",
        "tx_volume", "active_addresses",
    ]

    EVENT_MEMORY_FEATURES = [
        "event_expected_impact_1h",  # Expected % change from similar past events
        "event_expected_impact_4h",
        "event_expected_impact_24h",
        "event_memory_confidence",   # How confident the memory match is (0-1)
        "event_severity",            # Current event severity (0-10)
        "event_sentiment_predictive", # How often sentiment predicted direction correctly
        "active_event_count",        # Number of significant events in last hour
    ]

    DERIVATIVES_FEATURES = [
        "funding_rate",        # Binance perpetual funding rate
        "open_interest",       # Open interest in BTC
        "mark_index_spread",   # mark_price - index_price (premium)
    ]

    DOMINANCE_FEATURES = [
        "btc_dominance",       # BTC market cap %
        "eth_dominance",       # ETH market cap %
        "total_market_cap",    # Total crypto market cap USD (log-scaled)
        "market_cap_change",   # 24h market cap change %
    ]

    PHRASE_FEATURES = [
        "top_bullish_phrase_score",   # Strongest bullish phrase correlation in recent headlines
        "top_bearish_phrase_score",   # Strongest bearish phrase correlation in recent headlines
        "phrase_sentiment_signal",     # Net phrase-based sentiment signal
    ]

    ALL_FEATURES = (
        TECHNICAL_FEATURES + SENTIMENT_FEATURES + MACRO_FEATURES
        + ONCHAIN_FEATURES + EVENT_MEMORY_FEATURES
        + DERIVATIVES_FEATURES + DOMINANCE_FEATURES
        + PHRASE_FEATURES
    )

    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()

    def build_features(
        self,
        price_df: pd.DataFrame,
        news_data: list[dict] = None,
        reddit_data: list[dict] = None,
        influencer_data: list[dict] = None,  # Social media from influencers
        macro_data: dict = None,
        onchain_data: dict = None,
        fear_greed: dict = None,
        event_memory: dict = None,
        funding_data: dict = None,
        dominance_data: dict = None,
        phrase_data: dict = None,
    ) -> dict:
        """Build complete feature vector from all data sources (including social media)."""

        features = {}

        # Technical features from price data
        if price_df is not None and not price_df.empty:
            tech_df = TechnicalFeatures.calculate_all(price_df)
            latest = tech_df.iloc[-1]
            for feat in self.TECHNICAL_FEATURES:
                val = latest.get(feat)
                features[feat] = float(val) if val is not None and not pd.isna(val) else 0.0

            # Add current price info
            features["current_price"] = float(latest["close"])
            features["current_volume"] = float(latest["volume"])

        # Sentiment features (news + reddit + influencer social media)
        features.update(self._build_sentiment_features(news_data, reddit_data, influencer_data))

        # Macro features
        if macro_data:
            macro_feats = MacroFeatures.calculate_features(macro_data)
            for feat in self.MACRO_FEATURES:
                features[feat] = macro_feats.get(feat, 0.0) or 0.0

        # On-chain features
        if onchain_data:
            for feat in self.ONCHAIN_FEATURES:
                val = onchain_data.get(feat)
                features[feat] = float(val) if val is not None else 0.0

        # Fear & Greed
        if fear_greed:
            features["fear_greed_value"] = fear_greed.get("value", 50)

        # Event memory features
        if event_memory:
            features["event_expected_impact_1h"] = event_memory.get("expected_1h", 0.0)
            features["event_expected_impact_4h"] = event_memory.get("expected_4h", 0.0)
            features["event_expected_impact_24h"] = event_memory.get("expected_24h", 0.0)
            features["event_memory_confidence"] = event_memory.get("confidence", 0.0)
            features["event_severity"] = event_memory.get("severity", 0.0)
            features["event_sentiment_predictive"] = event_memory.get("avg_sentiment_predictive", 0.5)
            features["active_event_count"] = event_memory.get("active_event_count", 0.0)

        # Derivatives features (funding rate, open interest)
        if funding_data:
            features["funding_rate"] = float(funding_data.get("funding_rate", 0) or 0)
            features["open_interest"] = float(funding_data.get("open_interest", 0) or 0)
            mark = float(funding_data.get("mark_price", 0) or 0)
            index = float(funding_data.get("index_price", 0) or 0)
            features["mark_index_spread"] = (mark - index) if mark and index else 0.0

        # Dominance features (BTC dominance, market cap)
        if dominance_data:
            features["btc_dominance"] = float(dominance_data.get("btc_dominance", 0) or 0)
            features["eth_dominance"] = float(dominance_data.get("eth_dominance", 0) or 0)
            total_mcap = float(dominance_data.get("total_market_cap", 0) or 0)
            # Log-scale total market cap to keep it in a reasonable range
            features["total_market_cap"] = float(np.log10(total_mcap)) if total_mcap > 0 else 0.0
            features["market_cap_change"] = float(dominance_data.get("market_cap_change_24h", 0) or 0)

        # Phrase correlation features
        if phrase_data:
            features["top_bullish_phrase_score"] = float(phrase_data.get("top_bullish_score", 0))
            features["top_bearish_phrase_score"] = float(phrase_data.get("top_bearish_score", 0))
            features["phrase_sentiment_signal"] = float(phrase_data.get("net_signal", 0))

        # Normalize features
        features = self._normalize(features)

        return features

    def _build_sentiment_features(
        self,
        news_data: list[dict] = None,
        reddit_data: list[dict] = None,
        influencer_data: list[dict] = None,
    ) -> dict:
        """Build sentiment features from news, reddit, and influencer social media."""
        result = {feat: 0.0 for feat in self.SENTIMENT_FEATURES}

        if news_data:
            titles = [n.get("title", "") for n in news_data if n.get("title")]

            if titles:
                agg = self.sentiment_analyzer.get_aggregate_sentiment(titles)
                result["news_sentiment_1h"] = agg["mean_score"]
                result["news_sentiment_4h"] = agg["mean_score"]  # Needs historical for real 4h
                result["news_sentiment_24h"] = agg["mean_score"]  # Needs historical for real 24h
                result["news_volume_1h"] = float(agg["volume"])
                result["news_bullish_pct"] = agg["bullish_pct"]
                result["news_bearish_pct"] = agg["bearish_pct"]

        if reddit_data:
            posts = reddit_data if isinstance(reddit_data, list) else reddit_data.get("posts", [])
            titles = [p.get("title", "") for p in posts if p.get("title")]

            if titles:
                agg = self.sentiment_analyzer.get_aggregate_sentiment(titles)
                result["reddit_sentiment"] = agg["mean_score"]
                result["reddit_volume"] = float(agg["volume"])

        # Influencer social media (tweets/posts from key crypto figures)
        if influencer_data:
            texts = [t.get("text", "") for t in influencer_data if t.get("text")]

            if texts:
                agg = self.sentiment_analyzer.get_aggregate_sentiment(texts)
                result["social_sentiment_1h"] = agg["mean_score"]
                result["social_volume_1h"] = float(agg["volume"])
                result["social_bullish_pct"] = agg["bullish_pct"]
                result["social_bearish_pct"] = agg["bearish_pct"]

        return result

    def _normalize(self, features: dict) -> dict:
        """Basic feature normalization."""
        normalized = {}
        for key, val in features.items():
            if val is None or (isinstance(val, float) and np.isnan(val)):
                normalized[key] = 0.0
            else:
                normalized[key] = float(val)
        return normalized

    def features_to_array(self, features: dict) -> np.ndarray:
        """Convert feature dict to ordered numpy array for ML input."""
        return np.array([features.get(f, 0.0) for f in self.ALL_FEATURES], dtype=np.float32)

    def build_sequence(self, feature_history: list[dict], lookback: int = 168) -> np.ndarray:
        """Build a sequence of feature vectors for LSTM input.

        Args:
            feature_history: List of feature dicts (oldest first)
            lookback: Number of time steps

        Returns:
            numpy array of shape (lookback, num_features)
        """
        if len(feature_history) < lookback:
            # Pad with zeros if not enough history
            padding = [
                {f: 0.0 for f in self.ALL_FEATURES}
                for _ in range(lookback - len(feature_history))
            ]
            feature_history = padding + feature_history

        # Take last `lookback` entries
        recent = feature_history[-lookback:]
        matrix = np.array(
            [[entry.get(f, 0.0) for f in self.ALL_FEATURES] for entry in recent],
            dtype=np.float32,
        )
        return matrix
