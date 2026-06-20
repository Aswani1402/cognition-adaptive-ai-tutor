import os
import numpy as np
from tensorflow.keras.models import load_model

from tutor.utils.sklearn_safe_loader import safe_joblib_load, safe_model_call

# Correct base path according to your folder structure:
# external/models/behavior/ednet_lstm_v1/{model.h5, preproc.pkl}
_BASE = os.path.join("models", "behavior")

_MODELS = {}

class LSTMBehaviourModel:
    def __init__(self, dataset_key: str = "ednet"):
        """
        dataset_key: 'ednet' or 'oulad'
        """
        if dataset_key not in ("ednet", "oulad"):
            raise ValueError("dataset_key must be 'ednet' or 'oulad'")

        self.dataset_key = dataset_key
        model_dir = os.path.join(_BASE, f"{dataset_key}_lstm_v1")

        if not os.path.exists(model_dir):
            raise FileNotFoundError(f"Missing behavior model folder: {model_dir}")

        scaler_path = os.path.join(model_dir, "preproc.pkl")
        loaded = safe_joblib_load(scaler_path)
        self.scaler = loaded["model"]
        self.scaler_metadata = loaded["metadata"]
        if self.scaler is None:
            raise RuntimeError(self.scaler_metadata.get("fallback_reason", "scaler_unavailable"))
        self.model = load_model(os.path.join(model_dir, "model.h5"))

    def predict_anomaly(self, sequence):
        """
        sequence: list of 20 feature vectors (shape: 20 x F)
        returns: reconstruction MSE
        """
        if len(sequence) != 20:
            raise ValueError(f"Expected sequence length 20, got {len(sequence)}")

        X = np.array(sequence, dtype=float)
        if X.ndim != 2:
            raise ValueError(f"Expected shape (20, F), got {X.shape}")

        X = X.reshape(1, 20, -1)

        transform_result = safe_model_call(
            self.scaler,
            os.path.join(_BASE, f"{self.dataset_key}_lstm_v1", "preproc.pkl"),
            lambda: self.scaler.transform(X.reshape(-1, X.shape[-1])),
        )
        if not transform_result["ok"]:
            raise RuntimeError(transform_result["metadata"].get("fallback_reason", "scaler_prediction_error"))
        X_scaled = transform_result["value"].reshape(X.shape)

        X_recon = self.model.predict(X_scaled, verbose=0)
        mse = float(np.mean((X_scaled - X_recon) ** 2))
        return mse

    def predict_behavior_state(self, sequence, threshold=0.01):
        mse = self.predict_anomaly(sequence)
        label = "anomaly" if mse > threshold else "normal"
        confidence = float(1.0 - np.exp(-mse))
        return {
            "label": label,
            "confidence": confidence,
            "source": "lstm",
            "dataset": self.dataset_key,
            "mse": mse
        }


def predict_behavior(sequence, dataset_key="ednet", threshold=0.01):
    """
    sequence: list of 20 feature vectors
    dataset_key: 'ednet' or 'oulad'
    """
    if dataset_key not in _MODELS:
        _MODELS[dataset_key] = LSTMBehaviourModel(dataset_key)

    return _MODELS[dataset_key].predict_behavior_state(sequence, threshold=threshold)
