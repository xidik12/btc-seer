"""Auto-training pipeline for BTC Oracle ML models.

Pulls training data from the database (Feature + Price tables),
builds proper sequences, trains all models with walk-forward validation,
saves versioned weights, and tracks performance metrics.
"""
import logging
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from sqlalchemy import select, desc, func

from app.config import settings
from app.database import async_session, Feature, Price, Prediction, ModelVersion

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, TensorDataset
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class ModelTrainer:
    """Auto-training pipeline that trains models from accumulated DB data."""

    LOOKBACK = 168  # 7 days of hourly data
    MIN_SAMPLES = 168  # Minimum feature snapshots needed (1 week)
    HORIZONS = {"1h": 1, "4h": 4, "24h": 24, "1w": 168, "1mo": 720}
    TIMEFRAMES = ["1h", "4h", "24h", "1w", "1mo"]
    NUM_HORIZONS = 5

    def __init__(self, model_dir: str = None):
        self.model_dir = Path(model_dir or settings.model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

    async def build_training_dataset(self) -> dict:
        """Pull features from Feature table, prices from Price table.

        Returns:
            dict with:
                X_seq: (N, 168, num_features) sequences for LSTM/TFT
                X_feat: (N, num_features) current features for XGBoost
                y: (N, 10) targets — [dir_1h, mag_1h, dir_4h, mag_4h, dir_24h, mag_24h, dir_1w, mag_1w, dir_1mo, mag_1mo]
                feature_names: list of feature names
                price_history: list of close prices for TimesFM
        """
        from app.features.builder import FeatureBuilder
        builder = FeatureBuilder()
        feature_names = builder.ALL_FEATURES
        num_features = len(feature_names)

        async with async_session() as session:
            # Get all feature snapshots ordered by time
            result = await session.execute(
                select(Feature).order_by(Feature.timestamp)
            )
            features = result.scalars().all()

            # Get all prices for label generation
            result = await session.execute(
                select(Price).order_by(Price.timestamp)
            )
            prices = result.scalars().all()

        if len(features) < self.MIN_SAMPLES:
            logger.warning(
                f"Not enough feature data for training: {len(features)} < {self.MIN_SAMPLES}"
            )
            return None

        logger.info(f"Building dataset from {len(features)} feature snapshots and {len(prices)} price records")

        # Build price lookup: timestamp -> close price
        price_map = {}
        for p in prices:
            ts = p.timestamp.replace(second=0, microsecond=0)
            price_map[ts] = p.close

        # Also collect raw close prices for TimesFM
        price_history = [p.close for p in prices]

        # Convert features to numpy arrays
        feature_vectors = []
        feature_timestamps = []
        for f in features:
            vec = np.array(
                [f.feature_data.get(name, 0.0) for name in feature_names],
                dtype=np.float32,
            )
            feature_vectors.append(vec)
            feature_timestamps.append(f.timestamp)

        feature_matrix = np.array(feature_vectors)  # (total_snapshots, num_features)

        # Build sequences and labels using sliding window
        X_seq_list = []
        X_feat_list = []
        y_list = []

        for i in range(self.LOOKBACK, len(feature_vectors)):
            ts = feature_timestamps[i]
            current_price = self._find_price(ts, price_map)
            if current_price is None:
                continue

            # Build labels: actual price change at +1h, +4h, +24h
            labels = []
            valid = True
            for _, hours in self.HORIZONS.items():
                target_ts = ts + timedelta(hours=hours)
                target_price = self._find_price(target_ts, price_map)
                if target_price is None:
                    valid = False
                    break

                change_pct = (target_price - current_price) / current_price * 100
                direction = 1.0 if target_price > current_price else 0.0
                labels.extend([direction, change_pct])

            if not valid:
                continue

            # Sequence: last LOOKBACK feature vectors
            seq = feature_matrix[i - self.LOOKBACK:i]  # (168, num_features)
            X_seq_list.append(seq)
            X_feat_list.append(feature_matrix[i])
            y_list.append(labels)

        if not X_seq_list:
            logger.warning("No valid training samples could be constructed")
            return None

        X_seq = np.array(X_seq_list, dtype=np.float32)
        X_feat = np.array(X_feat_list, dtype=np.float32)
        y = np.array(y_list, dtype=np.float32)

        logger.info(
            f"Dataset built: {len(X_seq)} samples, "
            f"sequence shape {X_seq.shape}, "
            f"features {X_feat.shape}, "
            f"labels {y.shape}"
        )

        return {
            "X_seq": X_seq,
            "X_feat": X_feat,
            "y": y,
            "feature_names": feature_names,
            "num_features": num_features,
            "price_history": price_history,
        }

    async def prepare_extended_features(self, dataset: dict) -> dict:
        """Enrich dataset with long-term features computed from daily price history.

        Computes: sma_200d_ratio, high_52w_distance, low_52w_distance,
        log_price_zscore_365d, yearly_return_pct — features that require
        months/years of daily data rather than just hourly snapshots.
        """
        async with async_session() as session:
            result = await session.execute(
                select(Price).order_by(Price.timestamp)
            )
            all_prices = result.scalars().all()

        if len(all_prices) < 200:
            logger.info(f"Only {len(all_prices)} prices, skipping extended features")
            return dataset

        # Build daily price series
        daily = {}
        for p in all_prices:
            day = p.timestamp.strftime("%Y-%m-%d")
            daily[day] = p.close
        days_sorted = sorted(daily.keys())
        closes = [daily[d] for d in days_sorted]

        if len(closes) < 200:
            return dataset

        # Precompute daily metrics
        import math
        closes_arr = np.array(closes, dtype=np.float64)
        log_closes = np.log(closes_arr[closes_arr > 0])

        # 200-day SMA at the latest point
        sma_200d = np.mean(closes_arr[-200:]) if len(closes_arr) >= 200 else closes_arr.mean()
        current = closes_arr[-1]
        sma_200d_ratio = current / sma_200d if sma_200d > 0 else 1.0

        # 52-week (365-day) high/low
        window = min(365, len(closes_arr))
        high_52w = np.max(closes_arr[-window:])
        low_52w = np.min(closes_arr[-window:])
        high_52w_distance = (high_52w - current) / high_52w if high_52w > 0 else 0
        low_52w_distance = (current - low_52w) / current if current > 0 else 0

        # Log price z-score over 365 days
        if len(log_closes) >= 365:
            recent_log = np.log(closes_arr[-365:][closes_arr[-365:] > 0])
            mean_log = recent_log.mean()
            std_log = recent_log.std()
            log_price_zscore = (math.log(current) - mean_log) / std_log if std_log > 0 else 0
        else:
            log_price_zscore = 0

        # Yearly return
        if len(closes_arr) >= 365:
            yearly_return = (current - closes_arr[-365]) / closes_arr[-365] * 100
        else:
            yearly_return = 0

        # Apply to all feature vectors in dataset
        from app.features.builder import FeatureBuilder
        builder = FeatureBuilder()
        feature_names = builder.ALL_FEATURES

        extended_indices = {}
        for name in ["sma_200d_ratio", "high_52w_distance", "low_52w_distance",
                      "log_price_zscore_365d", "yearly_return_pct"]:
            if name in feature_names:
                extended_indices[name] = feature_names.index(name)

        extended_values = {
            "sma_200d_ratio": sma_200d_ratio,
            "high_52w_distance": high_52w_distance,
            "low_52w_distance": low_52w_distance,
            "log_price_zscore_365d": log_price_zscore,
            "yearly_return_pct": yearly_return / 100,  # normalize
        }

        # Update X_feat and X_seq with computed values
        X_feat = dataset["X_feat"]
        X_seq = dataset["X_seq"]
        for name, idx in extended_indices.items():
            if idx < X_feat.shape[1]:
                X_feat[:, idx] = extended_values.get(name, 0)
            if idx < X_seq.shape[2]:
                X_seq[:, :, idx] = extended_values.get(name, 0)

        dataset["X_feat"] = X_feat
        dataset["X_seq"] = X_seq

        logger.info(
            f"Extended features applied: sma_200d_ratio={sma_200d_ratio:.3f}, "
            f"52w_high_dist={high_52w_distance:.3f}, yearly_return={yearly_return:.1f}%"
        )
        return dataset

    def _find_price(self, ts: datetime, price_map: dict, tolerance_minutes: int = 10) -> float | None:
        """Find closest price to a timestamp within tolerance."""
        ts_rounded = ts.replace(second=0, microsecond=0)

        # Try exact match first
        if ts_rounded in price_map:
            return price_map[ts_rounded]

        # Search within tolerance
        for delta in range(1, tolerance_minutes + 1):
            for sign in [1, -1]:
                candidate = ts_rounded + timedelta(minutes=delta * sign)
                if candidate in price_map:
                    return price_map[candidate]

        return None

    def _walk_forward_split(self, n: int) -> tuple[range, range, range]:
        """Walk-forward split: 70% train, 15% val, 15% test."""
        train_end = int(n * 0.70)
        val_end = int(n * 0.85)
        return range(0, train_end), range(train_end, val_end), range(val_end, n)

    def _normalize_data(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Z-score normalize features, returning (normalized, mean, std)."""
        mean = X.mean(axis=0)
        std = X.std(axis=0)
        std[std == 0] = 1  # Avoid division by zero
        return (X - mean) / std, mean, std

    def train_lstm(self, X_seq: np.ndarray, y: np.ndarray) -> dict:
        """Train LSTM with real historical sequences."""
        if not TORCH_AVAILABLE:
            logger.warning("PyTorch not available, skipping LSTM training")
            return {"status": "skipped", "reason": "pytorch_unavailable"}

        from app.models.lstm import LSTMModel

        n = len(X_seq)
        train_idx, val_idx, test_idx = self._walk_forward_split(n)

        # Normalize sequences (flatten, normalize, reshape)
        orig_shape = X_seq.shape
        flat = X_seq.reshape(-1, orig_shape[-1])
        flat_norm, mean, std = self._normalize_data(flat)
        X_norm = flat_norm.reshape(orig_shape)

        num_features = X_seq.shape[-1]

        # Create data loaders
        X_train = torch.FloatTensor(X_norm[train_idx.start:train_idx.stop])
        y_train = torch.FloatTensor(y[train_idx.start:train_idx.stop])
        X_val = torch.FloatTensor(X_norm[val_idx.start:val_idx.stop])
        y_val = torch.FloatTensor(y[val_idx.start:val_idx.stop])
        X_test = torch.FloatTensor(X_norm[test_idx.start:test_idx.stop])
        y_test = torch.FloatTensor(y[test_idx.start:test_idx.stop])

        train_loader = DataLoader(
            TensorDataset(X_train, y_train), batch_size=32, shuffle=True
        )

        # Initialize model
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = LSTMModel(input_size=num_features).to(device)
        optimizer = optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-5)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)

        # Loss: BCE for direction + MSE for magnitude
        bce = nn.BCEWithLogitsLoss()
        mse = nn.MSELoss()

        best_val_loss = float("inf")
        patience_counter = 0
        max_patience = 15
        num_epochs = 100

        logger.info(f"Training LSTM: {len(train_idx)} train, {len(val_idx)} val, {len(test_idx)} test")

        for epoch in range(num_epochs):
            model.train()
            total_loss = 0
            for X_batch, y_batch in train_loader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                optimizer.zero_grad()

                outputs = model(X_batch)
                loss = 0
                for i, tf in enumerate(self.TIMEFRAMES):
                    out = outputs[tf]
                    dir_target = y_batch[:, i * 2]       # direction (0 or 1)
                    mag_target = y_batch[:, i * 2 + 1]   # magnitude %

                    loss += bce(out[:, 0], dir_target)
                    loss += mse(out[:, 1], mag_target) * 0.1  # Scale magnitude loss

                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                total_loss += loss.item()

            # Validation
            model.eval()
            with torch.no_grad():
                X_v, y_v = X_val.to(device), y_val.to(device)
                val_outputs = model(X_v)
                val_loss = 0
                for i, tf in enumerate(self.TIMEFRAMES):
                    out = val_outputs[tf]
                    val_loss += bce(out[:, 0], y_v[:, i * 2]).item()
                    val_loss += mse(out[:, 1], y_v[:, i * 2 + 1]).item() * 0.1

            scheduler.step(val_loss)

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                # Save best model
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            else:
                patience_counter += 1
                if patience_counter >= max_patience:
                    logger.info(f"LSTM early stopping at epoch {epoch + 1}")
                    break

            if (epoch + 1) % 10 == 0:
                logger.info(
                    f"LSTM epoch {epoch + 1}: train_loss={total_loss / len(train_loader):.4f}, "
                    f"val_loss={val_loss:.4f}"
                )

        # Load best model and evaluate on test set
        model.load_state_dict(best_state)
        model.eval()

        with torch.no_grad():
            X_t, y_t = X_test.to(device), y_test.to(device)
            test_outputs = model(X_t)

            correct = {tf: 0 for tf in self.TIMEFRAMES}
            total = len(test_idx)
            for i, tf in enumerate(self.TIMEFRAMES):
                out = test_outputs[tf]
                predicted_dir = (torch.sigmoid(out[:, 0]) > 0.5).float()
                actual_dir = y_t[:, i * 2]
                correct[tf] = (predicted_dir == actual_dir).sum().item()

        # Save model and normalization params
        weights_path = str(self.model_dir / "lstm_model.pt")
        torch.save(model.state_dict(), weights_path)
        np.savez(
            str(self.model_dir / "lstm_norm_params.npz"),
            mean=mean, std=std,
        )

        accuracies = {tf: c / total for tf, c in correct.items()}
        avg_accuracy = sum(accuracies.values()) / self.NUM_HORIZONS

        logger.info(f"LSTM training complete: accuracy={accuracies}, avg={avg_accuracy:.4f}")

        return {
            "status": "trained",
            "model_type": "lstm",
            "weights_path": weights_path,
            "train_samples": len(train_idx),
            "val_loss": best_val_loss,
            "test_accuracy": accuracies,
            "avg_accuracy": avg_accuracy,
            "feature_count": num_features,
        }

    def train_tft(self, X_seq: np.ndarray, y: np.ndarray) -> dict:
        """Train Temporal Fusion Transformer."""
        if not TORCH_AVAILABLE:
            logger.warning("PyTorch not available, skipping TFT training")
            return {"status": "skipped", "reason": "pytorch_unavailable"}

        from app.models.tft_model import SimpleTFT

        n = len(X_seq)
        train_idx, val_idx, test_idx = self._walk_forward_split(n)

        # Normalize
        orig_shape = X_seq.shape
        flat = X_seq.reshape(-1, orig_shape[-1])
        flat_norm, mean, std = self._normalize_data(flat)
        X_norm = flat_norm.reshape(orig_shape)

        num_features = X_seq.shape[-1]

        # Create tensors
        X_train = torch.FloatTensor(X_norm[train_idx.start:train_idx.stop])
        y_train = torch.FloatTensor(y[train_idx.start:train_idx.stop])
        X_val = torch.FloatTensor(X_norm[val_idx.start:val_idx.stop])
        y_val = torch.FloatTensor(y[val_idx.start:val_idx.stop])
        X_test = torch.FloatTensor(X_norm[test_idx.start:test_idx.stop])
        y_test = torch.FloatTensor(y[test_idx.start:test_idx.stop])

        train_loader = DataLoader(
            TensorDataset(X_train, y_train), batch_size=32, shuffle=True
        )

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = SimpleTFT(input_size=num_features).to(device)
        optimizer = optim.Adam(model.parameters(), lr=5e-4, weight_decay=1e-5)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)

        bce = nn.BCEWithLogitsLoss()
        mse = nn.MSELoss()

        best_val_loss = float("inf")
        patience_counter = 0
        max_patience = 15
        num_epochs = 80

        logger.info(f"Training TFT: {len(train_idx)} train, {len(val_idx)} val, {len(test_idx)} test")

        for epoch in range(num_epochs):
            model.train()
            total_loss = 0
            for X_batch, y_batch in train_loader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                optimizer.zero_grad()

                outputs = model(X_batch)  # (batch, 5, 2)

                loss = 0
                for i in range(self.NUM_HORIZONS):
                    dir_target = y_batch[:, i * 2]
                    mag_target = y_batch[:, i * 2 + 1]
                    loss += bce(outputs[:, i, 0], dir_target)
                    loss += mse(outputs[:, i, 1], mag_target) * 0.1

                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                total_loss += loss.item()

            # Validation
            model.eval()
            with torch.no_grad():
                X_v, y_v = X_val.to(device), y_val.to(device)
                val_out = model(X_v)
                val_loss = 0
                for i in range(self.NUM_HORIZONS):
                    val_loss += bce(val_out[:, i, 0], y_v[:, i * 2]).item()
                    val_loss += mse(val_out[:, i, 1], y_v[:, i * 2 + 1]).item() * 0.1

            scheduler.step(val_loss)

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            else:
                patience_counter += 1
                if patience_counter >= max_patience:
                    logger.info(f"TFT early stopping at epoch {epoch + 1}")
                    break

            if (epoch + 1) % 10 == 0:
                logger.info(
                    f"TFT epoch {epoch + 1}: train_loss={total_loss / len(train_loader):.4f}, "
                    f"val_loss={val_loss:.4f}"
                )

        # Load best and evaluate
        model.load_state_dict(best_state)
        model.eval()

        with torch.no_grad():
            X_t, y_t = X_test.to(device), y_test.to(device)
            test_out = model(X_t)

            correct = {tf: 0 for tf in self.TIMEFRAMES}
            total = len(test_idx)
            for i, tf in enumerate(self.TIMEFRAMES):
                predicted_dir = (torch.sigmoid(test_out[:, i, 0]) > 0.5).float()
                actual_dir = y_t[:, i * 2]
                correct[tf] = (predicted_dir == actual_dir).sum().item()

        weights_path = str(self.model_dir / "tft_model.pt")
        torch.save(model.state_dict(), weights_path)
        np.savez(
            str(self.model_dir / "tft_norm_params.npz"),
            mean=mean, std=std,
        )

        accuracies = {tf: c / total for tf, c in correct.items()}
        avg_accuracy = sum(accuracies.values()) / self.NUM_HORIZONS

        logger.info(f"TFT training complete: accuracy={accuracies}, avg={avg_accuracy:.4f}")

        return {
            "status": "trained",
            "model_type": "tft",
            "weights_path": weights_path,
            "train_samples": len(train_idx),
            "val_loss": best_val_loss,
            "test_accuracy": accuracies,
            "avg_accuracy": avg_accuracy,
            "feature_count": num_features,
        }

    def train_xgboost(self, X_feat: np.ndarray, y: np.ndarray) -> dict:
        """Train XGBoost on current feature vectors for direction classification."""
        try:
            import xgboost as xgb
        except ImportError:
            logger.warning("xgboost not available, skipping training")
            return {"status": "skipped", "reason": "xgboost_unavailable"}

        n = len(X_feat)
        train_idx, val_idx, test_idx = self._walk_forward_split(n)

        # Train separate models for each timeframe
        results = {}
        models = {}

        for i, tf in enumerate(self.TIMEFRAMES):
            dir_labels = y[:, i * 2]  # Binary direction labels

            X_train = X_feat[train_idx.start:train_idx.stop]
            y_train = dir_labels[train_idx.start:train_idx.stop]
            X_val = X_feat[val_idx.start:val_idx.stop]
            y_val = dir_labels[val_idx.start:val_idx.stop]
            X_test = X_feat[test_idx.start:test_idx.stop]
            y_test = dir_labels[test_idx.start:test_idx.stop]

            dtrain = xgb.DMatrix(X_train, label=y_train)
            dval = xgb.DMatrix(X_val, label=y_val)
            dtest = xgb.DMatrix(X_test, label=y_test)

            params = {
                "max_depth": 6,
                "eta": 0.05,
                "objective": "binary:logistic",
                "eval_metric": "logloss",
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "min_child_weight": 5,
                "verbosity": 0,
            }

            model = xgb.train(
                params,
                dtrain,
                num_boost_round=300,
                evals=[(dtrain, "train"), (dval, "val")],
                early_stopping_rounds=20,
                verbose_eval=False,
            )

            # Test accuracy
            test_pred = model.predict(dtest)
            test_correct = ((test_pred > 0.5) == y_test).sum()
            accuracy = test_correct / len(y_test)

            models[tf] = model
            results[tf] = accuracy

            logger.info(f"XGBoost {tf}: test accuracy = {accuracy:.4f}")

        # Save the 1h model as primary (used in ensemble for current features)
        # Also save all three for per-timeframe predictions
        weights_path = str(self.model_dir / "xgboost_model.json")
        models["1h"].save_model(weights_path)

        for tf, m in models.items():
            m.save_model(str(self.model_dir / f"xgboost_{tf}.json"))

        avg_accuracy = sum(results.values()) / len(results)

        logger.info(f"XGBoost training complete: accuracy={results}, avg={avg_accuracy:.4f}")

        return {
            "status": "trained",
            "model_type": "xgboost",
            "weights_path": weights_path,
            "train_samples": len(train_idx),
            "test_accuracy": results,
            "avg_accuracy": avg_accuracy,
            "feature_count": X_feat.shape[1],
        }

    async def train_all(self) -> dict:
        """Run full training pipeline.

        1. Build dataset from DB
        2. Train each model
        3. Save versioned weights
        4. Record metrics in ModelVersion table
        5. Return performance report
        """
        logger.info("Starting full model training pipeline...")

        # 1. Build dataset
        dataset = await self.build_training_dataset()
        if dataset is None:
            return {
                "status": "insufficient_data",
                "improved": False,
                "message": "Not enough data for training",
            }

        # 1b. Enrich with long-term features from daily price history
        try:
            dataset = await self.prepare_extended_features(dataset)
        except Exception as e:
            logger.warning(f"Extended feature enrichment failed (continuing): {e}")

        X_seq = dataset["X_seq"]
        X_feat = dataset["X_feat"]
        y = dataset["y"]

        # 2. Train each model
        results = {}

        # TFT (primary model)
        try:
            results["tft"] = self.train_tft(X_seq, y)
        except Exception as e:
            logger.error(f"TFT training failed: {e}", exc_info=True)
            results["tft"] = {"status": "failed", "error": str(e)}

        # LSTM
        try:
            results["lstm"] = self.train_lstm(X_seq, y)
        except Exception as e:
            logger.error(f"LSTM training failed: {e}", exc_info=True)
            results["lstm"] = {"status": "failed", "error": str(e)}

        # XGBoost
        try:
            results["xgboost"] = self.train_xgboost(X_feat, y)
        except Exception as e:
            logger.error(f"XGBoost training failed: {e}", exc_info=True)
            results["xgboost"] = {"status": "failed", "error": str(e)}

        # 3. Save normalization params (use LSTM's since it processes sequences)
        if results.get("lstm", {}).get("status") == "trained":
            # Already saved during training
            pass

        # 4. Record metrics in ModelVersion table
        await self._save_model_versions(results)

        # 5. Check if any model improved
        improved = any(
            r.get("status") == "trained" and r.get("avg_accuracy", 0) > 0.50
            for r in results.values()
        )

        summary = {
            "status": "completed",
            "improved": improved,
            "models": {
                k: {
                    "status": v.get("status"),
                    "accuracy": v.get("avg_accuracy"),
                    "samples": v.get("train_samples"),
                }
                for k, v in results.items()
            },
            "total_samples": len(X_seq),
            "timestamp": datetime.utcnow().isoformat(),
        }

        logger.info(f"Training pipeline complete: {summary}")
        return summary

    async def _save_model_versions(self, results: dict):
        """Record training results in the ModelVersion table."""
        try:
            async with async_session() as session:
                for model_type, result in results.items():
                    if result.get("status") != "trained":
                        continue

                    # Get next version number
                    ver_result = await session.execute(
                        select(func.max(ModelVersion.version))
                        .where(ModelVersion.model_type == model_type)
                    )
                    max_ver = ver_result.scalar() or 0

                    # Deactivate old versions
                    from sqlalchemy import update
                    await session.execute(
                        update(ModelVersion)
                        .where(ModelVersion.model_type == model_type)
                        .values(is_active=False)
                    )

                    avg_acc = result.get("avg_accuracy", 0)
                    test_acc = result.get("test_accuracy", {})

                    version = ModelVersion(
                        timestamp=datetime.utcnow(),
                        model_type=model_type,
                        version=max_ver + 1,
                        train_accuracy=None,
                        val_accuracy=None,
                        test_accuracy=avg_acc,
                        train_loss=result.get("val_loss"),
                        train_samples=result.get("train_samples"),
                        feature_count=result.get("feature_count"),
                        weights_path=result.get("weights_path", ""),
                        is_active=True,
                    )
                    session.add(version)

                await session.commit()
                logger.info("Model versions saved to database")

        except Exception as e:
            logger.error(f"Error saving model versions: {e}")

    async def evaluate_and_retrain_if_needed(self) -> dict:
        """Check model accuracy; retrain if degraded.

        Checks recent prediction accuracy and triggers retraining
        if accuracy drops below threshold.
        """
        try:
            async with async_session() as session:
                # Get recent evaluated predictions (last 48 hours)
                since = datetime.utcnow() - timedelta(hours=48)
                result = await session.execute(
                    select(Prediction)
                    .where(Prediction.was_correct.isnot(None))
                    .where(Prediction.timestamp >= since)
                )
                recent_preds = result.scalars().all()

                if len(recent_preds) < 10:
                    return {"status": "insufficient_eval_data", "retrain": False}

                correct = sum(1 for p in recent_preds if p.was_correct)
                accuracy = correct / len(recent_preds)

                logger.info(
                    f"Recent prediction accuracy: {accuracy:.2%} "
                    f"({correct}/{len(recent_preds)})"
                )

                # Check if we have enough training data
                result = await session.execute(
                    select(func.count()).select_from(Feature)
                )
                feature_count = result.scalar()

                # Check last training time
                result = await session.execute(
                    select(ModelVersion.timestamp)
                    .order_by(desc(ModelVersion.timestamp))
                    .limit(1)
                )
                last_trained = result.scalar()

            hours_since_training = None
            if last_trained:
                hours_since_training = (datetime.utcnow() - last_trained).total_seconds() / 3600

            should_retrain = (
                # Accuracy dropped below 52% (barely better than random)
                accuracy < 0.52
                # Or it's been more than 24 hours since last training
                or (hours_since_training is not None and hours_since_training > 24)
                # Or never trained and have enough data
                or (last_trained is None and feature_count >= self.MIN_SAMPLES)
            )

            if should_retrain:
                logger.info(
                    f"Triggering retrain: accuracy={accuracy:.2%}, "
                    f"hours_since_training={hours_since_training}, "
                    f"feature_count={feature_count}"
                )
                result = await self.train_all()
                return {"status": "retrained", "retrain": True, "result": result}

            return {
                "status": "ok",
                "retrain": False,
                "accuracy": accuracy,
                "hours_since_training": hours_since_training,
            }

        except Exception as e:
            logger.error(f"Retrain evaluation error: {e}", exc_info=True)
            return {"status": "error", "retrain": False, "error": str(e)}
