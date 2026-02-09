import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not installed — LSTM model will use heuristic fallback")


if TORCH_AVAILABLE:
    class LSTMModel(nn.Module):
        """LSTM model for time-series BTC price prediction."""

        def __init__(self, input_size: int = 74, hidden_size: int = 128, num_layers: int = 2, dropout: float = 0.2):
            super().__init__()

            self.hidden_size = hidden_size
            self.num_layers = num_layers

            self.lstm = nn.LSTM(
                input_size=input_size,
                hidden_size=hidden_size,
                num_layers=num_layers,
                batch_first=True,
                dropout=dropout if num_layers > 1 else 0,
            )

            self.dropout = nn.Dropout(dropout)

            self.head_1h = nn.Sequential(
                nn.Linear(hidden_size, 64),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(64, 2),
            )

            self.head_4h = nn.Sequential(
                nn.Linear(hidden_size, 64),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(64, 2),
            )

            self.head_24h = nn.Sequential(
                nn.Linear(hidden_size, 64),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(64, 2),
            )

            self.head_1w = nn.Sequential(
                nn.Linear(hidden_size, 64),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(64, 2),
            )

            self.head_1mo = nn.Sequential(
                nn.Linear(hidden_size, 64),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(64, 2),
            )

        def forward(self, x):
            lstm_out, (h_n, c_n) = self.lstm(x)
            last_hidden = self.dropout(lstm_out[:, -1, :])
            return {
                "1h": self.head_1h(last_hidden),
                "4h": self.head_4h(last_hidden),
                "24h": self.head_24h(last_hidden),
                "1w": self.head_1w(last_hidden),
                "1mo": self.head_1mo(last_hidden),
            }


class LSTMPredictor:
    """Wrapper for LSTM model inference. Falls back to heuristics if torch is unavailable."""

    def __init__(self, input_size: int = 74, model_path: str = None):
        self._torch_model = None

        self.is_trained = False

        if TORCH_AVAILABLE:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self._torch_model = LSTMModel(input_size=input_size).to(self.device)

            if model_path and Path(model_path).exists():
                self.load(model_path)
                self.is_trained = True
                logger.info(f"LSTM model loaded from {model_path}")
            else:
                logger.warning("LSTM model weights not found, using random weights")

            self._torch_model.eval()

    def predict(self, sequence: np.ndarray) -> dict:
        if self._torch_model is not None:
            return self._torch_predict(sequence)
        return self._heuristic_predict(sequence)

    def _torch_predict(self, sequence: np.ndarray) -> dict:
        with torch.no_grad():
            x = torch.FloatTensor(sequence).unsqueeze(0).to(self.device)
            outputs = self._torch_model(x)

            predictions = {}
            for timeframe, output in outputs.items():
                direction_logit = output[0, 0].item()
                magnitude = output[0, 1].item()
                direction_prob = torch.sigmoid(torch.tensor(direction_logit)).item()

                predictions[timeframe] = {
                    "bullish_prob": direction_prob,
                    "bearish_prob": 1 - direction_prob,
                    "direction": "bullish" if direction_prob > 0.5 else "bearish",
                    "magnitude_pct": magnitude,
                    "confidence": abs(direction_prob - 0.5) * 200,
                }

            return predictions

    def _heuristic_predict(self, sequence: np.ndarray) -> dict:
        """Heuristic fallback: analyze recent price momentum from the sequence."""
        predictions = {}

        # Use last few rows of the sequence to detect momentum
        if sequence.ndim == 2 and len(sequence) >= 10:
            # Approximate: look at first feature column (likely close-related via EMA)
            recent = sequence[-24:]  # last 24 hours
            mean_recent = np.mean(recent, axis=0)
            mean_older = np.mean(sequence[-48:-24], axis=0) if len(sequence) >= 48 else mean_recent

            # Simple momentum signal from feature averages
            momentum = float(np.mean(mean_recent - mean_older))
            prob = 0.5 + np.clip(momentum * 10, -0.3, 0.3)
        else:
            prob = 0.5

        for tf, factor in [("1h", 1.0), ("4h", 0.9), ("24h", 0.8), ("1w", 0.7), ("1mo", 0.6)]:
            tf_prob = 0.5 + (prob - 0.5) * factor
            predictions[tf] = {
                "bullish_prob": float(tf_prob),
                "bearish_prob": float(1 - tf_prob),
                "direction": "bullish" if tf_prob > 0.5 else "bearish" if tf_prob < 0.5 else "neutral",
                "magnitude_pct": float((tf_prob - 0.5) * 4),
                "confidence": float(abs(tf_prob - 0.5) * 200),
            }

        return predictions

    def save(self, path: str):
        if self._torch_model and TORCH_AVAILABLE:
            torch.save(self._torch_model.state_dict(), path)

    def load(self, path: str):
        if self._torch_model and TORCH_AVAILABLE:
            self._torch_model.load_state_dict(torch.load(path, map_location=self.device, weights_only=True))
