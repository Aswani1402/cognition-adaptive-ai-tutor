from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from tutor.utils.sklearn_safe_loader import safe_joblib_load, safe_model_call

MODEL_PATH = Path("models/policy/policy_model.joblib")


class PolicyModel:
    def __init__(self):
        self.model = None
        self.metadata = {
            "model_status": "unavailable_missing",
            "model_loaded": False,
            "fallback_used": True,
            "fallback_reason": "model_file_missing",
            "model_path": str(MODEL_PATH),
        }
        if MODEL_PATH.exists():
            loaded = safe_joblib_load(MODEL_PATH)
            self.model = loaded["model"]
            self.metadata = loaded["metadata"]

    def is_available(self) -> bool:
        return self.model is not None

    def predict_next_concept(self, features: dict[str, Any]) -> str:
        if self.model is None:
            raise ValueError("Policy model not loaded")

        row = {
            "mastery_score": features.get("mastery_score"),
            "behavior_label": features.get("behavior_label"),
            "behavior_score": features.get("behavior_score"),
            "review_due": int(bool(features.get("review_due"))),
            "evaluation_score": features.get("evaluation_score"),
            "learning_signal": features.get("learning_signal"),
            "final_action": features.get("final_action"),
            "recommended_strategy": features.get("recommended_strategy"),
            "recommended_difficulty": features.get("recommended_difficulty"),
        }

        df = pd.DataFrame([row])
        result = safe_model_call(self.model, MODEL_PATH, lambda: self.model.predict(df))
        if not result["ok"]:
            self.metadata = result["metadata"]
            raise RuntimeError(result["metadata"].get("error_message") or result["metadata"].get("fallback_reason"))
        self.metadata = result["metadata"]
        pred = result["value"][0]
        return str(pred)
