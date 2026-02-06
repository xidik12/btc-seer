"""
Backtesting Script for BTC Oracle predictions.

Runs historical predictions and evaluates accuracy.

Usage:
    python -m ml.backtest --data ml/data/btc_hourly.csv --days 90
"""

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.features.technical import TechnicalFeatures
from app.features.builder import FeatureBuilder
from app.models.lstm import LSTMPredictor
from app.models.xgboost_model import XGBoostPredictor


def backtest(args):
    builder = FeatureBuilder()
    num_features = len(builder.ALL_FEATURES)

    # Load data
    df = pd.read_csv(args.data)
    logger.info(f"Loaded {len(df)} candles")

    # Calculate features
    tech_df = TechnicalFeatures.calculate_all(df)

    # Load models
    lstm = LSTMPredictor(
        input_size=num_features,
        model_path=args.lstm_model if Path(args.lstm_model).exists() else None,
    )
    xgb = XGBoostPredictor(
        model_path=args.xgb_model if Path(args.xgb_model).exists() else None,
    )

    # Backtest period
    test_start = max(200, len(df) - args.days * 24)  # Need 200 for features
    results = []

    for i in range(test_start, len(df) - 1):
        # Build feature vector
        row = tech_df.iloc[i]
        features = {}
        for f in builder.TECHNICAL_FEATURES:
            val = row.get(f, 0)
            features[f] = float(val) if not pd.isna(val) else 0.0
        for f in builder.ALL_FEATURES:
            if f not in features:
                features[f] = 0.0

        feature_array = builder.features_to_array(features)

        # Build sequence (simplified)
        sequence = np.tile(feature_array, (168, 1))

        # Predict
        lstm_pred = lstm.predict(sequence)
        xgb_pred = xgb.predict(feature_array)

        # Ensemble
        lstm_prob = lstm_pred.get("1h", {}).get("bullish_prob", 0.5)
        xgb_prob = xgb_pred.get("bullish_prob", 0.5)
        ensemble_prob = 0.5 * lstm_prob + 0.5 * xgb_prob

        predicted_dir = "bullish" if ensemble_prob > 0.5 else "bearish"

        # Actual
        actual_change = df["close"].iloc[i + 1] - df["close"].iloc[i]
        actual_dir = "bullish" if actual_change > 0 else "bearish"

        results.append({
            "index": i,
            "predicted": predicted_dir,
            "actual": actual_dir,
            "correct": predicted_dir == actual_dir,
            "confidence": abs(ensemble_prob - 0.5) * 200,
            "lstm_prob": lstm_prob,
            "xgb_prob": xgb_prob,
            "ensemble_prob": ensemble_prob,
        })

    # Analyze results
    results_df = pd.DataFrame(results)
    total = len(results_df)
    correct = results_df["correct"].sum()
    accuracy = correct / total * 100

    logger.info(f"\n{'='*50}")
    logger.info(f"BACKTEST RESULTS ({total} predictions)")
    logger.info(f"{'='*50}")
    logger.info(f"Overall Accuracy: {accuracy:.1f}%")
    logger.info(f"Correct: {correct}/{total}")

    # By confidence
    for label, low, high in [("High (>60%)", 60, 100), ("Medium (30-60%)", 30, 60), ("Low (<30%)", 0, 30)]:
        mask = (results_df["confidence"] >= low) & (results_df["confidence"] < high)
        subset = results_df[mask]
        if len(subset) > 0:
            acc = subset["correct"].mean() * 100
            logger.info(f"  {label}: {acc:.1f}% ({len(subset)} predictions)")

    logger.info(f"\nLSTM mean prob: {results_df['lstm_prob'].mean():.3f}")
    logger.info(f"XGBoost mean prob: {results_df['xgb_prob'].mean():.3f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backtest BTC Oracle predictions")
    parser.add_argument("--data", type=str, default="ml/data/btc_hourly.csv")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--lstm-model", type=str, default="app/models/weights/lstm_model.pt")
    parser.add_argument("--xgb-model", type=str, default="app/models/weights/xgboost_model.json")

    backtest(parser.parse_args())
