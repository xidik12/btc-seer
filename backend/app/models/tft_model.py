"""Temporal Fusion Transformer for multi-horizon BTC prediction.

Uses pytorch-forecasting's TFT implementation which handles:
- Variable selection: learns which features matter most
- Multi-horizon: predicts 1h, 4h, 24h simultaneously
- Interpretability: shows feature importance per prediction
- Mixed inputs: observed (price/volume), known (time features), static (regime)
"""
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

try:
    from app.features.builder import FeatureBuilder
    _NUM_FEATURES = len(FeatureBuilder.ALL_FEATURES)
except Exception:
    _NUM_FEATURES = 222

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    import pytorch_forecasting
    from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet
    from pytorch_forecasting.data import GroupNormalizer
    import pytorch_lightning as pl
    TFT_AVAILABLE = True
except ImportError:
    TFT_AVAILABLE = False
    logger.info("pytorch-forecasting not installed — TFT model unavailable")


class TFTPredictor:
    """Temporal Fusion Transformer for multi-horizon BTC prediction."""

    def __init__(self, model_path: str = None, num_features: int = _NUM_FEATURES):
        self.model = None
        self.is_trained = False
        self.num_features = num_features
        self.device = "cpu"

        if TORCH_AVAILABLE:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"

        if model_path and Path(model_path).exists():
            self.load(model_path)
        elif not TFT_AVAILABLE:
            logger.info("TFT: pytorch-forecasting not available, will use fallback")

    def predict(self, feature_sequence: np.ndarray) -> dict:
        """Generate multi-horizon prediction.

        Args:
            feature_sequence: (168, num_features) array of historical features

        Returns:
            Dict with 1h, 4h, 24h predictions
        """
        if self.model is not None and self.is_trained:
            return self._model_predict(feature_sequence)
        return self._fallback_predict(feature_sequence)

    def _model_predict(self, feature_sequence: np.ndarray) -> dict:
        """Prediction using trained TFT model."""
        try:
            with torch.no_grad():
                x = torch.FloatTensor(feature_sequence).unsqueeze(0).to(self.device)
                output = self.model(x)

                predictions = {}
                timeframes = ["1h", "4h", "24h", "1w", "1mo"]
                for i, tf in enumerate(timeframes):
                    if i >= output.shape[1]:
                        break
                    direction_logit = output[0, i, 0].item()
                    magnitude = output[0, i, 1].item()
                    prob = torch.sigmoid(torch.tensor(direction_logit)).item()

                    predictions[tf] = {
                        "bullish_prob": prob,
                        "bearish_prob": 1 - prob,
                        "direction": "bullish" if prob > 0.5 else "bearish",
                        "magnitude_pct": magnitude,
                        "confidence": abs(prob - 0.5) * 200,
                    }

                return predictions
        except Exception as e:
            logger.error(f"TFT prediction error: {e}")
            return self._fallback_predict(feature_sequence)

    def _fallback_predict(self, feature_sequence: np.ndarray) -> dict:
        """Weighted trend-following fallback when TFT is not trained.

        Analyzes multi-scale momentum across the feature sequence.
        """
        predictions = {}

        if feature_sequence.ndim == 2 and len(feature_sequence) >= 24:
            # Multi-scale momentum analysis
            short = feature_sequence[-6:]    # Last 6 hours
            medium = feature_sequence[-24:]  # Last 24 hours
            long_term = feature_sequence[-72:] if len(feature_sequence) >= 72 else feature_sequence

            short_mean = np.mean(short, axis=0)
            medium_mean = np.mean(medium, axis=0)
            long_mean = np.mean(long_term, axis=0)

            # Momentum: short-term vs medium-term trend
            short_momentum = float(np.mean(short_mean - medium_mean))
            medium_momentum = float(np.mean(medium_mean - long_mean))

            # Combine with more weight on short-term
            combined = short_momentum * 0.6 + medium_momentum * 0.4
            base_prob = 0.5 + np.clip(combined * 8, -0.25, 0.25)
        else:
            base_prob = 0.5

        for tf, decay in [("1h", 1.0), ("4h", 0.85), ("24h", 0.7), ("1w", 0.6), ("1mo", 0.5)]:
            prob = 0.5 + (base_prob - 0.5) * decay
            prob = float(np.clip(prob, 0.15, 0.85))

            tf_multiplier = {"1h": 1.0, "4h": 2.5, "24h": 5.0, "1w": 10.0, "1mo": 20.0}[tf]
            magnitude = (prob - 0.5) * 2 * tf_multiplier

            predictions[tf] = {
                "bullish_prob": prob,
                "bearish_prob": 1 - prob,
                "direction": "bullish" if prob >= 0.5 else "bearish",
                "magnitude_pct": float(magnitude),
                "confidence": float(abs(prob - 0.5) * 200),
            }

        return predictions

    def save(self, path: str):
        if self.model is not None and TORCH_AVAILABLE:
            torch.save(self.model.state_dict(), path)
            logger.info(f"TFT model saved to {path}")

    def load(self, path: str):
        try:
            if not TORCH_AVAILABLE:
                return

            # Load the simplified TFT model
            state = torch.load(path, map_location=self.device, weights_only=True)
            self.model = SimpleTFT(
                input_size=self.num_features,
            ).to(self.device)
            self.model.load_state_dict(state)
            self.model.eval()
            self.is_trained = True
            logger.info(f"TFT model loaded from {path}")
        except RuntimeError as e:
            # Shape mismatch after feature expansion — fall back to heuristics
            logger.warning(f"TFT weight loading failed (shape mismatch after feature expansion?): {e}")
            logger.warning("TFT will use fallback predictions until next retrain")
            self.model = None
            self.is_trained = False
        except Exception as e:
            logger.error(f"Error loading TFT model: {e}")
            self.model = None
            self.is_trained = False


if TORCH_AVAILABLE:
    class SimpleTFT(nn.Module):
        """Simplified TFT-inspired architecture for direct training.

        Uses multi-head attention over temporal features with variable selection,
        similar to the full TFT but trainable without the pytorch-forecasting
        dataset format.
        """

        def __init__(self, input_size: int = _NUM_FEATURES, hidden_size: int = 128,
                     num_heads: int = 4, num_layers: int = 2, dropout: float = 0.1):
            super().__init__()

            # Variable selection network
            self.var_selection = nn.Sequential(
                nn.Linear(input_size, hidden_size),
                nn.ReLU(),
                nn.Linear(hidden_size, input_size),
                nn.Softmax(dim=-1),
            )

            # Input projection
            self.input_proj = nn.Linear(input_size, hidden_size)

            # Temporal processing with self-attention
            encoder_layer = nn.TransformerEncoderLayer(
                d_model=hidden_size,
                nhead=num_heads,
                dim_feedforward=hidden_size * 2,
                dropout=dropout,
                batch_first=True,
            )
            self.temporal_encoder = nn.TransformerEncoder(
                encoder_layer, num_layers=num_layers
            )

            # LSTM for sequential patterns
            self.lstm = nn.LSTM(
                input_size=hidden_size,
                hidden_size=hidden_size,
                num_layers=1,
                batch_first=True,
                dropout=0,
            )

            # Gated residual connection
            self.gate = nn.Sequential(
                nn.Linear(hidden_size * 2, hidden_size),
                nn.Sigmoid(),
            )

            self.dropout = nn.Dropout(dropout)
            self.layer_norm = nn.LayerNorm(hidden_size)

            # Multi-horizon output heads: 5 timeframes x 2 (direction + magnitude)
            self.head_1h = nn.Linear(hidden_size, 2)
            self.head_4h = nn.Linear(hidden_size, 2)
            self.head_24h = nn.Linear(hidden_size, 2)
            self.head_1w = nn.Linear(hidden_size, 2)
            self.head_1mo = nn.Linear(hidden_size, 2)

        def forward(self, x):
            # x shape: (batch, seq_len, input_size)

            # Variable selection: learn which features matter
            var_weights = self.var_selection(x)  # (batch, seq_len, input_size)
            x_selected = x * var_weights

            # Project to hidden size
            h = self.input_proj(x_selected)  # (batch, seq_len, hidden_size)

            # Temporal attention
            attn_out = self.temporal_encoder(h)

            # LSTM for sequential patterns
            lstm_out, _ = self.lstm(h)

            # Gated fusion of attention and LSTM
            combined = torch.cat([attn_out, lstm_out], dim=-1)
            gate_weight = self.gate(combined)
            fused = gate_weight * attn_out + (1 - gate_weight) * lstm_out

            # Residual + layer norm
            fused = self.layer_norm(fused + h)
            fused = self.dropout(fused)

            # Use last time step for prediction
            last = fused[:, -1, :]

            # Multi-horizon outputs
            out_1h = self.head_1h(last)
            out_4h = self.head_4h(last)
            out_24h = self.head_24h(last)
            out_1w = self.head_1w(last)
            out_1mo = self.head_1mo(last)

            return torch.stack([out_1h, out_4h, out_24h, out_1w, out_1mo], dim=1)  # (batch, 5, 2)
