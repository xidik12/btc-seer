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

    # ═══════════════════════════════════════════════════════════
    #  FEATURE LISTS
    # ═══════════════════════════════════════════════════════════

    TECHNICAL_FEATURES = [
        # ── Original 30 (indices 0-29) ──
        "ema_9", "ema_21", "ema_50", "ema_200", "sma_20",
        "rsi", "macd", "macd_signal", "macd_hist",
        "bb_upper", "bb_lower", "bb_width", "bb_position",
        "atr", "obv", "vwap",
        "roc_1", "roc_6", "roc_12", "roc_24",
        "momentum_10", "momentum_20",
        "volume_ratio", "volatility_24h",
        "price_vs_ema9", "price_vs_ema21", "price_vs_ema50",
        "body_size", "upper_shadow", "lower_shadow",
        # ── Promoted already-computed indicators (29) ──
        "sma_111", "sma_200", "sma_350",
        "rsi_7", "rsi_30",
        "adx", "momentum_30", "mayer_multiple", "pi_cycle_ratio",
        "ema_cross", "zscore_20",
        "stoch_rsi_k", "stoch_rsi_d", "williams_r",
        "ichimoku_tenkan", "ichimoku_kijun",
        "ichimoku_senkou_a", "ichimoku_senkou_b", "ichimoku_chikou",
        "candle_doji", "candle_hammer", "candle_inverted_hammer",
        "candle_bullish_engulfing", "candle_bearish_engulfing",
        "candle_morning_star", "candle_evening_star",
        "trend_short", "trend_medium", "trend_long",
        # ── pandas-ta indicators (45) ──
        "ao", "cci_20", "cmo_14", "fisher_9", "fisher_signal",
        "kst", "kst_signal", "ppo", "ppo_signal", "ppo_hist",
        "stoch_k", "stoch_d", "tsi", "uo",
        "aroon_osc", "chop_14", "dpo_20", "supertrend_dir",
        "vortex_diff", "mass_index", "plus_di", "minus_di",
        "donchian_upper", "donchian_lower", "donchian_mid", "donchian_width",
        "kc_upper", "kc_lower", "kc_position", "natr", "ui",
        "ad", "cmf", "efi_13", "mfi", "nvi", "pvi",
        "entropy_10", "kurtosis_20", "skew_20", "variance_20",
        "zscore_14", "stdev_20", "linreg_slope", "linreg_r2",
        # ── Advanced quantitative indicators (37) ──
        # Adaptive MAs (3)
        "kama_10", "t3_10", "dema_21",
        # Additional momentum (4)
        "trix_14", "bop", "psar", "psar_dir",
        # Additional candlestick patterns (7)
        "candle_three_white", "candle_three_black", "candle_dark_cloud",
        "candle_piercing", "candle_harami", "candle_kicking", "candle_three_line_strike",
        # Price transforms (3)
        "typical_price", "weighted_close", "median_price",
        # Return-based statistics (6)
        "return_1h", "return_skew_24", "return_kurtosis_24",
        "return_autocorr_1", "return_autocorr_6", "return_autocorr_24",
        # Hurst exponent (1)
        "hurst_exponent",
        # GARCH volatility (2)
        "garch_vol_forecast", "vol_risk_premium",
        # Wavelet features (3)
        "wavelet_trend", "wavelet_detail_1", "wavelet_detail_2",
        # Calendar features (4)
        "hour_sin", "hour_cos", "day_of_week_sin", "day_of_week_cos",
        # Hash Ribbon (1)
        "hash_ribbon",
        # Cross-feature interactions (3)
        "rsi_macd_divergence", "volume_price_trend", "atr_ratio_50_14",
    ]

    SENTIMENT_FEATURES = [
        "news_sentiment_1h", "news_sentiment_4h", "news_sentiment_24h",
        "news_volume_1h", "news_bullish_pct", "news_bearish_pct",
        "reddit_sentiment", "reddit_volume",
        "social_sentiment_1h", "social_volume_1h",
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
        # Promoted from already-collected data
        "difficulty", "large_tx_count",
    ]

    EVENT_MEMORY_FEATURES = [
        "event_expected_impact_1h",
        "event_expected_impact_4h",
        "event_expected_impact_24h",
        "event_memory_confidence",
        "event_severity",
        "event_sentiment_predictive",
        "active_event_count",
    ]

    DERIVATIVES_FEATURES = [
        "funding_rate",
        "open_interest",
        "mark_index_spread",
    ]

    DOMINANCE_FEATURES = [
        "btc_dominance",
        "eth_dominance",
        "total_market_cap",
        "market_cap_change",
    ]

    PHRASE_FEATURES = [
        "top_bullish_phrase_score",
        "top_bearish_phrase_score",
        "phrase_sentiment_signal",
    ]

    SUPPLY_FEATURES = [
        "btc_mined_pct",
        "daily_issuance_rate",
        "blocks_until_halving",
        "halving_cycle_pct",
    ]

    # ── NEW FEATURE CATEGORIES ──

    DERIVATIVES_EXTENDED_FEATURES = [
        "long_short_ratio",        # Global long/short account ratio
        "long_account_pct",        # % of accounts that are long
        "short_account_pct",       # % of accounts that are short
        "top_trader_long_short",   # Top trader position ratio
        "top_long_pct",
        "top_short_pct",
        "taker_buy_sell_ratio",    # Taker buy vs sell volume
        "dvol",                    # Deribit BTC implied volatility index
        "liquidation_24h_usd",     # Total liquidations in 24h
        "long_liquidation_24h",    # Long liquidations
        "short_liquidation_24h",   # Short liquidations
        "estimated_leverage_ratio", # OI / exchange reserve
    ]

    ETF_FEATURES = [
        "etf_net_flow_usd",       # Daily ETF net inflow/outflow
        "etf_total_holdings_btc", # Total BTC in all ETFs
        "etf_ibit_flow",          # BlackRock IBIT flow
        "etf_fbtc_flow",          # Fidelity FBTC flow
        "etf_gbtc_flow",          # Grayscale GBTC flow
        "etf_volume_usd",         # Daily ETF trading volume
    ]

    EXCHANGE_FLOW_FEATURES = [
        "exchange_reserve_btc",    # Total BTC on exchanges
        "exchange_netflow_btc",    # Net in - out (positive = selling pressure)
        "nvt_signal",              # NVT Signal (smoothed)
        "mvrv_zscore",             # MVRV Z-Score
        "sopr",                    # Spent Output Profit Ratio
        "puell_multiple",          # Miner revenue / 365d avg
        "supply_in_profit_pct",    # % of supply in profit
        "long_term_holder_supply", # BTC held by LTH (>155 days)
        "coin_days_destroyed",     # CDD (dormancy weighted)
    ]

    STABLECOIN_FEATURES = [
        "usdt_market_cap",              # USDT circulating supply
        "usdc_market_cap",              # USDC circulating supply
        "total_stablecoin_supply",      # Total stablecoin market cap
        "stablecoin_supply_change_7d",  # 7-day change %
        "defi_tvl_usd",                # Total DeFi TVL
    ]

    ALL_FEATURES = (
        TECHNICAL_FEATURES + SENTIMENT_FEATURES + MACRO_FEATURES
        + ONCHAIN_FEATURES + EVENT_MEMORY_FEATURES
        + DERIVATIVES_FEATURES + DOMINANCE_FEATURES
        + PHRASE_FEATURES + SUPPLY_FEATURES
        + DERIVATIVES_EXTENDED_FEATURES + ETF_FEATURES
        + EXCHANGE_FLOW_FEATURES + STABLECOIN_FEATURES
    )

    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()

    def build_features(
        self,
        price_df: pd.DataFrame,
        news_data: list[dict] = None,
        reddit_data: list[dict] = None,
        influencer_data: list[dict] = None,
        macro_data: dict = None,
        onchain_data: dict = None,
        fear_greed: dict = None,
        event_memory: dict = None,
        funding_data: dict = None,
        dominance_data: dict = None,
        phrase_data: dict = None,
        supply_data: dict = None,
        # New data sources
        derivatives_extended: dict = None,
        etf_data: dict = None,
        exchange_flow_data: dict = None,
        stablecoin_data: dict = None,
    ) -> dict:
        """Build complete feature vector from all data sources."""

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

        # On-chain features (now includes difficulty + large_tx_count)
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
            features["total_market_cap"] = float(np.log10(total_mcap)) if total_mcap > 0 else 0.0
            features["market_cap_change"] = float(dominance_data.get("market_cap_change_24h", 0) or 0)

        # Phrase correlation features
        if phrase_data:
            features["top_bullish_phrase_score"] = float(phrase_data.get("top_bullish_score", 0))
            features["top_bearish_phrase_score"] = float(phrase_data.get("top_bearish_score", 0))
            features["phrase_sentiment_signal"] = float(phrase_data.get("net_signal", 0))

        # Supply/mining features
        if supply_data:
            features["btc_mined_pct"] = supply_data.get("percent_mined", 94.0) / 100.0
            features["daily_issuance_rate"] = supply_data.get("btc_mined_per_day", 450) / max(supply_data.get("total_mined", 19_800_000), 1)
            blocks_left = supply_data.get("blocks_until_halving", 169_000)
            features["blocks_until_halving"] = blocks_left / 210_000
            features["halving_cycle_pct"] = 1.0 - (blocks_left / 210_000)

        # ── NEW: Extended derivatives (long/short, DVOL, liquidations) ──
        if derivatives_extended:
            for feat in self.DERIVATIVES_EXTENDED_FEATURES:
                val = derivatives_extended.get(feat)
                features[feat] = float(val) if val is not None else 0.0

        # ── NEW: ETF flow data ──
        if etf_data:
            features["etf_net_flow_usd"] = float(etf_data.get("net_flow_usd", 0) or 0)
            features["etf_total_holdings_btc"] = float(etf_data.get("total_holdings_btc", 0) or 0)
            features["etf_ibit_flow"] = float(etf_data.get("ibit_flow", 0) or 0)
            features["etf_fbtc_flow"] = float(etf_data.get("fbtc_flow", 0) or 0)
            features["etf_gbtc_flow"] = float(etf_data.get("gbtc_flow", 0) or 0)
            features["etf_volume_usd"] = float(etf_data.get("etf_volume_usd", 0) or 0)

        # ── NEW: Exchange flow and on-chain valuation ──
        if exchange_flow_data:
            for feat in self.EXCHANGE_FLOW_FEATURES:
                val = exchange_flow_data.get(feat)
                features[feat] = float(val) if val is not None else 0.0

        # ── NEW: Stablecoin supply ──
        if stablecoin_data:
            for feat in self.STABLECOIN_FEATURES:
                val = stablecoin_data.get(feat)
                if feat in ("usdt_market_cap", "usdc_market_cap", "total_stablecoin_supply", "defi_tvl_usd"):
                    # Log-scale large dollar values
                    fval = float(val) if val else 0.0
                    features[feat] = float(np.log10(fval)) if fval > 0 else 0.0
                else:
                    features[feat] = float(val) if val is not None else 0.0

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
                result["news_sentiment_4h"] = agg["mean_score"]
                result["news_sentiment_24h"] = agg["mean_score"]
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
        """Build a sequence of feature vectors for LSTM input."""
        if len(feature_history) < lookback:
            padding = [
                {f: 0.0 for f in self.ALL_FEATURES}
                for _ in range(lookback - len(feature_history))
            ]
            feature_history = padding + feature_history

        recent = feature_history[-lookback:]
        matrix = np.array(
            [[entry.get(f, 0.0) for f in self.ALL_FEATURES] for entry in recent],
            dtype=np.float32,
        )
        return matrix
