"""
LSTM Model Training Script for BTC Oracle.

Usage:
    python -m ml.train_lstm --epochs 50 --lookback 168 --batch-size 32

Requires historical data in ml/data/ or fetches from Binance.
"""

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.lstm import LSTMModel
from app.features.technical import TechnicalFeatures
from app.features.builder import FeatureBuilder


def load_data(csv_path: str = None) -> pd.DataFrame:
    """Load OHLCV data from CSV or fetch from Binance."""
    if csv_path and Path(csv_path).exists():
        logger.info(f"Loading data from {csv_path}")
        return pd.read_csv(csv_path, parse_dates=["timestamp"])

    logger.info("Fetching historical data from Binance...")
    import asyncio
    from app.collectors.market import MarketCollector

    async def fetch():
        collector = MarketCollector()
        all_klines = []
        # Fetch 2 years of hourly data in chunks
        import time
        end_time = int(time.time() * 1000)
        for _ in range(18):  # ~18 months
            klines = await collector.get_historical_klines(
                interval="1h", end_time=end_time, limit=1000
            )
            if not klines:
                break
            all_klines = klines + all_klines
            end_time = int(klines[0]["timestamp"].timestamp() * 1000) - 1
            logger.info(f"Fetched {len(all_klines)} candles so far...")
        await collector.close()
        return all_klines

    klines = asyncio.run(fetch())
    df = pd.DataFrame(klines)

    # Save for future use
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)
    df.to_csv(data_dir / "btc_hourly.csv", index=False)
    logger.info(f"Saved {len(df)} candles to ml/data/btc_hourly.csv")

    return df


def prepare_features(df: pd.DataFrame, builder: FeatureBuilder) -> np.ndarray:
    """Calculate technical features and return feature matrix."""
    tech_df = TechnicalFeatures.calculate_all(df)
    features = []
    for _, row in tech_df.iterrows():
        feat = {}
        for f in builder.TECHNICAL_FEATURES:
            val = row.get(f, 0)
            feat[f] = float(val) if not pd.isna(val) else 0.0
        # Pad remaining features with 0
        for f in builder.ALL_FEATURES:
            if f not in feat:
                feat[f] = 0.0
        features.append(builder.features_to_array(feat))

    return np.array(features, dtype=np.float32)


def create_sequences(features: np.ndarray, targets: np.ndarray, lookback: int):
    """Create input sequences and corresponding targets."""
    X, y = [], []
    for i in range(lookback, len(features)):
        X.append(features[i - lookback:i])
        y.append(targets[i])
    return np.array(X), np.array(y)


def calculate_targets(df: pd.DataFrame) -> np.ndarray:
    """Calculate target variables: direction and magnitude for 1h ahead."""
    close = df["close"].values
    targets = np.zeros((len(close), 2), dtype=np.float32)

    for i in range(len(close) - 1):
        change = (close[i + 1] - close[i]) / close[i]
        direction = 1.0 if change > 0 else 0.0
        magnitude = change * 100  # Percentage
        targets[i] = [direction, magnitude]

    return targets


def train(args):
    builder = FeatureBuilder()
    num_features = len(builder.ALL_FEATURES)

    # Load data
    df = load_data(args.data)
    logger.info(f"Loaded {len(df)} candles")

    # Prepare features and targets
    features = prepare_features(df, builder)
    targets = calculate_targets(df)
    logger.info(f"Feature matrix shape: {features.shape}")

    # Normalize features (z-score)
    mean = features.mean(axis=0)
    std = features.std(axis=0)
    std[std == 0] = 1  # Avoid division by zero
    features = (features - mean) / std

    # Create sequences
    X, y = create_sequences(features, targets, args.lookback)
    logger.info(f"Sequences: X={X.shape}, y={y.shape}")

    # Train/val/test split (70/15/15)
    n = len(X)
    train_end = int(n * 0.7)
    val_end = int(n * 0.85)

    X_train, y_train = X[:train_end], y[:train_end]
    X_val, y_val = X[train_end:val_end], y[train_end:val_end]
    X_test, y_test = X[val_end:], y[val_end:]

    logger.info(f"Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")

    # DataLoaders
    train_ds = TensorDataset(torch.FloatTensor(X_train), torch.FloatTensor(y_train))
    val_ds = TensorDataset(torch.FloatTensor(X_val), torch.FloatTensor(y_val))

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size)

    # Model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = LSTMModel(input_size=num_features).to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    bce_loss = nn.BCEWithLogitsLoss()
    mse_loss = nn.MSELoss()

    # Training loop
    best_val_loss = float("inf")

    for epoch in range(args.epochs):
        model.train()
        train_loss = 0

        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)

            optimizer.zero_grad()
            outputs = model(X_batch)

            # Use 1h head
            pred = outputs["1h"]
            loss_dir = bce_loss(pred[:, 0], y_batch[:, 0])
            loss_mag = mse_loss(pred[:, 1], y_batch[:, 1])
            loss = loss_dir + 0.5 * loss_mag

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_loss += loss.item()

        # Validation
        model.eval()
        val_loss = 0
        correct = 0
        total = 0

        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                outputs = model(X_batch)
                pred = outputs["1h"]

                loss_dir = bce_loss(pred[:, 0], y_batch[:, 0])
                loss_mag = mse_loss(pred[:, 1], y_batch[:, 1])
                val_loss += (loss_dir + 0.5 * loss_mag).item()

                predicted_dir = (torch.sigmoid(pred[:, 0]) > 0.5).float()
                correct += (predicted_dir == y_batch[:, 0]).sum().item()
                total += y_batch.size(0)

        avg_train = train_loss / len(train_loader)
        avg_val = val_loss / len(val_loader)
        accuracy = correct / total * 100

        logger.info(
            f"Epoch {epoch + 1}/{args.epochs} — "
            f"Train Loss: {avg_train:.4f}, Val Loss: {avg_val:.4f}, "
            f"Direction Acc: {accuracy:.1f}%"
        )

        if avg_val < best_val_loss:
            best_val_loss = avg_val
            save_path = Path(args.output)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            torch.save(model.state_dict(), save_path)
            logger.info(f"Model saved to {save_path}")

    # Test evaluation
    logger.info("\n--- Test Set Evaluation ---")
    model.load_state_dict(torch.load(args.output, map_location=device, weights_only=True))
    model.eval()

    X_test_t = torch.FloatTensor(X_test).to(device)
    y_test_t = torch.FloatTensor(y_test).to(device)

    with torch.no_grad():
        outputs = model(X_test_t)
        pred = outputs["1h"]
        predicted_dir = (torch.sigmoid(pred[:, 0]) > 0.5).float()
        test_acc = (predicted_dir == y_test_t[:, 0]).float().mean().item() * 100

    logger.info(f"Test Direction Accuracy: {test_acc:.1f}%")

    # Save normalization params
    np.savez(
        str(Path(args.output).with_suffix(".npz")),
        mean=mean,
        std=std,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train LSTM model for BTC Oracle")
    parser.add_argument("--data", type=str, default=None, help="Path to OHLCV CSV")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lookback", type=int, default=168)
    parser.add_argument("--lr", type=float, default=0.001)
    parser.add_argument("--output", type=str, default="app/models/weights/lstm_model.pt")

    train(parser.parse_args())
