from pathlib import Path
import pandas as pd

from tutor.utils.sklearn_safe_loader import safe_joblib_load, safe_model_call


MODEL_PATH = Path("models/generation/generation_model.pkl")
ENCODER_PATH = Path("models/generation/label_encoders.pkl")


class GenerationPolicy:
    def __init__(self):
        self.model = None
        self.encoder = None
        self.available = False
        self.model_metadata = {}
        self.encoder_metadata = {}
        self.load()

    def load(self):
        if not MODEL_PATH.exists():
            return

        model_loaded = safe_joblib_load(MODEL_PATH)
        encoder_loaded = safe_joblib_load(ENCODER_PATH)
        self.model = model_loaded["model"]
        self.encoder = encoder_loaded["model"]
        self.model_metadata = model_loaded["metadata"]
        self.encoder_metadata = encoder_loaded["metadata"]
        self.available = self.model is not None and self.encoder is not None

    def is_available(self):
        return self.available

    def build_features(self, state: dict):
        return pd.DataFrame(
            [
                {
                    "mastery": float(state.get("mastery_score", 0.0)),
                    "behavior": float(state.get("behavior_score", 0.0)),
                    "time_taken": float(state.get("time_taken", 20.0)),
                    "confidence": float(state.get("confidence", 2)),
                    "hint_used": float(state.get("hint_used", 0)),
                }
            ],
            columns=[
                "mastery",
                "behavior",
                "time_taken",
                "confidence",
                "hint_used",
            ],
        )

    def predict(self, state: dict):
        if not self.available:
            return None

        X = self.build_features(state)

        pred_result = safe_model_call(self.model, MODEL_PATH, lambda: self.model.predict(X))
        if not pred_result["ok"]:
            self.model_metadata = pred_result["metadata"]
            self.available = False
            return None
        pred = pred_result["value"][0]
        label_result = safe_model_call(self.encoder, ENCODER_PATH, lambda: self.encoder.inverse_transform([pred]))
        if not label_result["ok"]:
            self.encoder_metadata = label_result["metadata"]
            self.available = False
            return None
        label = label_result["value"][0]

        parts = label.split("_")

        difficulty = parts[-1]
        strategy = parts[0]
        content_type = "_".join(parts[1:-1])

        return {
            "strategy": strategy,
            "content_type": content_type,
            "difficulty": difficulty,
        }
