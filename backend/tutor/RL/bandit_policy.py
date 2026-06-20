import pandas as pd
from pathlib import Path
from typing import Any, Dict

from tutor.utils.sklearn_safe_loader import safe_model_call, safe_pickle_load


MODEL_PATH = Path("models/rl/bandit_policy_model.pkl")
ENCODER_PATH = Path("models/rl/bandit_label_encoders.pkl")


class BanditPolicy:
    def __init__(self):
        self.model = None
        self.encoders = None
        self.available = False
        self.model_metadata = {}
        self.encoder_metadata = {}
        self.load()

    def load(self) -> None:
        if not MODEL_PATH.exists() or not ENCODER_PATH.exists():
            self.available = False
            return

        model_loaded = safe_pickle_load(MODEL_PATH)
        encoder_loaded = safe_pickle_load(ENCODER_PATH)
        self.model = model_loaded["model"]
        self.encoders = encoder_loaded["model"]
        self.model_metadata = model_loaded["metadata"]
        self.encoder_metadata = encoder_loaded["metadata"]
        self.available = self.model is not None and self.encoders is not None

    def is_available(self) -> bool:
        return self.available

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

    def _encode_value(self, column: str, value: Any) -> int:
        encoder = self.encoders.get(column)
        value = str(value)

        if encoder is None:
            return 0

        if value in encoder.classes_:
            return int(encoder.transform([value])[0])

        # fallback for unseen values
        return 0

    def predict(self, state: Dict[str, Any]) -> Dict[str, Any]:
        if not self.available:
            return {
                "status": "error",
                "reason": "Bandit policy model not available",
            }

        row = pd.DataFrame([{
            "mastery_score": self._safe_float(state.get("mastery_score")),
            "behavior_score": self._safe_float(state.get("behavior_score")),
            "review_due": self._encode_value("review_due", state.get("review_due")),
            "evaluation_score": self._safe_float(state.get("evaluation_score")),
            "learning_signal": self._encode_value("learning_signal", state.get("learning_signal")),
        }])

        predict_result = safe_model_call(self.model, MODEL_PATH, lambda: self.model.predict(row))
        if not predict_result["ok"]:
            self.available = False
            return {
                "status": "error",
                "reason": predict_result["metadata"].get("fallback_reason", "model_prediction_error"),
                "model_metadata": predict_result["metadata"],
            }
        predicted_encoded = predict_result["value"][0]
        action_label = self.encoders["action_label"].inverse_transform([predicted_encoded])[0]

        if "_" in action_label:
            strategy, difficulty = action_label.rsplit("_", 1)
        else:
            strategy = action_label
            difficulty = "medium"

        return {
            "status": "success",
            "action_label": action_label,
            "strategy": strategy,
            "difficulty": difficulty,
        }
