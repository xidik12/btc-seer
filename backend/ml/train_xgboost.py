"""
XGBoost Model Training Script for BTC Oracle.

Usage:
    python -m ml.train_xgboost --data ml/data/btc_hourly.csv
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


def train(args):
    builder = FeatureBuilder()

    # Load data
    if not args.data or not Path(args.data).exists():
        logger.error("Please provide --data path. Run train_lstm.py first to fetch data.")
        return

    df = pd.read_csv(args.data, parse_dates=["timestamp"] if "timestamp" in pd.read_csv(args.data, nrows=1).columns else None)
    logger.info(f"Loaded {len(df)} candles")

    # Ensure required columns
    for col in ["open", "high", "low", "close", "volume"]:
        if col not in df.columns:
            logger.error(f"Missing column: {col}")
            return

    # Calculate technical features
    tech_df = TechnicalFeatures.calculate_all(df)

    # Build feature matrix
    feature_cols = [c for c in builder.TECHNICAL_FEATURES if c in tech_df.columns]
    X = tech_df[feature_cols].fillna(0).values.astype(np.float32)

    # Target: next candle direction (1 = up, 0 = down)
    y = (df["close"].shift(-1) > df["close"]).astype(int).values

    # Remove last row (no target) and initial rows (NaN features)
    valid_start = 200  # After longest MA
    X = X[valid_start:-1]
    y = y[valid_start:-1]
    logger.info(f"Feature matrix: {X.shape}, Target: {y.shape}")

    # Split
    n = len(X)
    train_end = int(n * 0.7)
    val_end = int(n * 0.85)

    X_train, y_train = X[:train_end], y[:train_end]
    X_val, y_val = X[train_end:val_end], y[train_end:val_end]
    X_test, y_test = X[val_end:], y[val_end:]

    logger.info(f"Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")

    import xgboost as xgb

    dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=feature_cols)
    dval = xgb.DMatrix(X_val, label=y_val, feature_names=feature_cols)
    dtest = xgb.DMatrix(X_test, label=y_test, feature_names=feature_cols)

    params = {
        "objective": "binary:logistic",
        "eval_metric": "logloss",
        "max_depth": args.max_depth,
        "learning_rate": args.lr,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_weight": 3,
        "gamma": 0.1,
        "seed": 42,
    }

    model = xgb.train(
        params,
        dtrain,
        num_boost_round=args.num_rounds,
        evals=[(dtrain, "train"), (dval, "val")],
        early_stopping_rounds=20,
        verbose_eval=10,
    )

    # Test evaluation
    y_pred_prob = model.predict(dtest)
    y_pred = (y_pred_prob > 0.5).astype(int)

    accuracy = np.mean(y_pred == y_test) * 100
    logger.info(f"\nTest Accuracy: {accuracy:.1f}%")

    # Feature importance
    importance = model.get_score(importance_type="gain")
    sorted_imp = sorted(importance.items(), key=lambda x: x[1], reverse=True)
    logger.info("\nTop 10 Features:")
    for feat, score in sorted_imp[:10]:
        logger.info(f"  {feat}: {score:.2f}")

    # Save model
    save_path = Path(args.output)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(str(save_path))
    logger.info(f"\nModel saved to {save_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train XGBoost model for BTC Oracle")
    parser.add_argument("--data", type=str, default="ml/data/btc_hourly.csv")
    parser.add_argument("--num-rounds", type=int, default=500)
    parser.add_argument("--max-depth", type=int, default=6)
    parser.add_argument("--lr", type=float, default=0.05)
    parser.add_argument("--output", type=str, default="app/models/weights/xgboost_model.json")

    train(parser.parse_args())
