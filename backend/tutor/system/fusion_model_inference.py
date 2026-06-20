from __future__ import annotations

from pathlib import Path
from typing import Any

from tutor.utils.sklearn_safe_loader import safe_joblib_load, safe_model_call

MODEL_PATH = Path("models/fusion/fusion_model.joblib")


class FusionModel:
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

    def get_metadata(self) -> dict[str, Any]:
        return dict(self.metadata)

    def predict(self, evidence_summary: dict[str, Any]) -> str:
        if self.model is None:
            raise ValueError("Fusion model not loaded")

        import pandas as pd

        row = {
            "mastery_score": evidence_summary.get("mastery_score"),
            "behavior_label": evidence_summary.get("behavior_label"),
            "behavior_score": evidence_summary.get("behavior_score"),
            "review_due": int(bool(evidence_summary.get("review_due"))),
            "evaluation_score": evidence_summary.get("evaluation_score"),
            "evaluation_quality": evidence_summary.get("evaluation_quality"),
            "learning_signal": evidence_summary.get("learning_signal"),
        }

        df = pd.DataFrame([row])
        result = safe_model_call(
            self.model,
            MODEL_PATH,
            lambda: self.model.predict(df),
        )
        if not result["ok"]:
            self.metadata = result["metadata"]
            raise RuntimeError(result["metadata"].get("error_message") or result["metadata"].get("fallback_reason"))

        self.metadata = result["metadata"]
        pred = result["value"][0]
        return pred
