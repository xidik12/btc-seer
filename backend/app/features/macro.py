import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class MacroFeatures:
    """Processes macro market data into features for ML models."""

    @staticmethod
    def calculate_features(macro_data: dict, historical_macro: list[dict] = None) -> dict:
        """Calculate macro features from current and historical data."""
        features = {
            "dxy_price": None,
            "dxy_change_1h": None,
            "dxy_change_24h": None,
            "gold_price": None,
            "gold_change_1h": None,
            "gold_change_24h": None,
            "sp500_price": None,
            "sp500_change_1h": None,
            "sp500_change_24h": None,
            "treasury_10y": None,
            "treasury_change_1h": None,
            "fear_greed_value": None,
        }

        for key in ["dxy", "gold", "sp500"]:
            data = macro_data.get(key)
            if data and isinstance(data, dict):
                features[f"{key}_price"] = data.get("price")
                features[f"{key}_change_1h"] = data.get("change_1h", 0)
                features[f"{key}_change_24h"] = data.get("change_24h", 0)

        treasury = macro_data.get("treasury_10y")
        if treasury and isinstance(treasury, dict):
            features["treasury_10y"] = treasury.get("price")
            features["treasury_change_1h"] = treasury.get("change_1h", 0)

        fear_greed = macro_data.get("fear_greed")
        if fear_greed and isinstance(fear_greed, dict):
            features["fear_greed_value"] = fear_greed.get("value")

        # Calculate correlations if historical data available
        if historical_macro and len(historical_macro) >= 168:  # 7 days of hourly data
            features.update(MacroFeatures._calculate_correlations(historical_macro))

        return features

    @staticmethod
    def _calculate_correlations(historical: list[dict]) -> dict:
        """Calculate rolling correlations between BTC and macro assets."""
        try:
            df = pd.DataFrame(historical)

            correlations = {}
            btc_col = "btc_price" if "btc_price" in df.columns else None

            if btc_col:
                for col in ["dxy_price", "gold_price", "sp500_price"]:
                    if col in df.columns:
                        corr = df[btc_col].corr(df[col])
                        correlations[f"btc_{col}_corr_7d"] = float(corr) if not np.isnan(corr) else 0

            return correlations

        except Exception as e:
            logger.error(f"Error calculating correlations: {e}")
            return {}
