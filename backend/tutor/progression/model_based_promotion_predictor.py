"""
Model-based promotion predictor.

Purpose:
- Load trained promotion confidence models.
- Predict promotion_allowed and progression_action.
- Run in comparison-only mode for now.
- Do NOT override ProgressionRewardEngine baseline decisions yet.

Inputs expected:
- mastery
- evaluation_score
- structured_score
- debug_score
- output_prediction_score
- explanation_score
- transfer_score
- behaviour_score
- wrong_rate
- low_confidence_rate
- view_reward
- forgetting_priority
- guess_probability
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from tutor.utils.sklearn_safe_loader import (
    merge_model_metadata,
    safe_joblib_load,
    safe_model_call,
)


FEATURE_COLUMNS: List[str] = [
    "mastery",
    "evaluation_score",
    "structured_score",
    "debug_score",
    "output_prediction_score",
    "explanation_score",
    "transfer_score",
    "behaviour_score",
    "wrong_rate",
    "low_confidence_rate",
    "view_reward",
    "forgetting_priority",
    "guess_probability",
]


DEFAULT_MODEL_DIR = Path("models/promotion_confidence")


@dataclass
class ModelPrediction:
    label: Any
    confidence: float
    probabilities: Dict[str, float]


class ModelBasedPromotionPredictor:
    """
    Loads trained promotion models and predicts:
    1. target_promotion_allowed
    2. target_progression_action

    Current mode:
    - comparison_only = True
    - The output is for analysis/reporting.
    - It should not yet replace baseline ProgressionRewardEngine.
    """

    def __init__(
        self,
        model_dir: Path | str = DEFAULT_MODEL_DIR,
        comparison_only: bool = True,
    ) -> None:
        self.model_dir = Path(model_dir)
        self.comparison_only = comparison_only

        self.promotion_allowed_model_path = (
            self.model_dir / "target_promotion_allowed_decision_tree.joblib"
        )
        self.progression_action_model_path = (
            self.model_dir / "target_progression_action_random_forest.joblib"
        )

        self.promotion_allowed_model = self._safe_load_model(
            self.promotion_allowed_model_path
        )
        self.progression_action_model = self._safe_load_model(
            self.progression_action_model_path
        )
        self.model_metadata = merge_model_metadata(
            getattr(self, "promotion_allowed_model_metadata", None),
            getattr(self, "progression_action_model_metadata", None),
        )

    def _safe_load_model(self, path: Path) -> Optional[Any]:
        if not path.exists():
            if "promotion_allowed" in path.name:
                self.promotion_allowed_model_metadata = safe_joblib_load(path)["metadata"]
            else:
                self.progression_action_model_metadata = safe_joblib_load(path)["metadata"]
            return None

        loaded_result = safe_joblib_load(path)
        loaded = loaded_result["model"]
        if "promotion_allowed" in path.name:
            self.promotion_allowed_model_metadata = loaded_result["metadata"]
        else:
            self.progression_action_model_metadata = loaded_result["metadata"]
        if loaded is None:
            return None

        # Some training scripts save a raw sklearn model.
        if hasattr(loaded, "predict"):
            return loaded

        # Some training scripts save a dictionary wrapper.
        if isinstance(loaded, dict):
            for key in ["model", "best_model", "classifier", "estimator"]:
                candidate = loaded.get(key)
                if hasattr(candidate, "predict"):
                    return candidate

            # Fallback: search any value inside the dict.
            for value in loaded.values():
                if hasattr(value, "predict"):
                    return value

        return None

    def _build_feature_row(self, evidence: Dict[str, Any]) -> pd.DataFrame:
        row = {}

        for col in FEATURE_COLUMNS:
            raw_value = evidence.get(col, 0.0)

            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                value = 0.0

            row[col] = value

        return pd.DataFrame([row], columns=FEATURE_COLUMNS)

    def _predict_with_confidence(
    self,
    model: Any,
    x: pd.DataFrame,
    model_path: Path,
    ) -> ModelPrediction:
        pred_result = safe_model_call(model, model_path, lambda: model.predict(x))
        if not pred_result["ok"]:
            raise RuntimeError(pred_result["metadata"].get("error_message") or pred_result["metadata"].get("fallback_reason"))
        label = pred_result["value"][0]

        probabilities: Dict[str, float] = {}
        confidence = 1.0

        if hasattr(model, "predict_proba"):
            proba_result = safe_model_call(model, model_path, lambda: model.predict_proba(x))
            if not proba_result["ok"]:
                raise RuntimeError(proba_result["metadata"].get("error_message") or proba_result["metadata"].get("fallback_reason"))
            prob_array = proba_result["value"][0]
            classes = list(model.classes_)

            probabilities = {
                str(cls): float(prob)
                for cls, prob in zip(classes, prob_array)
            }

            confidence = float(max(prob_array))

        return ModelPrediction(
            label=label,
            confidence=confidence,
            probabilities=probabilities,
        )

    def predict(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        x = self._build_feature_row(evidence)

        missing_models = []

        if self.promotion_allowed_model is None:
            missing_models.append(str(self.promotion_allowed_model_path))

        if self.progression_action_model is None:
            missing_models.append(str(self.progression_action_model_path))

        if missing_models:
            fallback_action = self._fallback_progression_action(evidence)
            return {
                "status": "success",
                "module": "ModelBasedPromotionPredictor",
                "reason": "One or more trained promotion models are unavailable; rule fallback used for comparison metadata.",
                "missing_models": missing_models,
                "comparison_only": self.comparison_only,
                "model_promotion_allowed": bool(evidence.get("mastery", 0.0) and float(evidence.get("mastery", 0.0) or 0.0) >= 0.75),
                "model_promotion_allowed_raw": int(float(evidence.get("mastery", 0.0) or 0.0) >= 0.75),
                "model_promotion_allowed_confidence": 0.0,
                "model_promotion_allowed_probabilities": {},
                "model_progression_action": fallback_action,
                "model_progression_action_confidence": 0.0,
                "model_progression_action_probabilities": {},
                "model_status": self.model_metadata.get("model_status", "unavailable_version_mismatch"),
                "model_loaded": False,
                "fallback_used": True,
                "fallback_reason": self.model_metadata.get("fallback_reason", "model_unavailable"),
                "current_sklearn_version": self.model_metadata.get("current_sklearn_version"),
                "warning_count": self.model_metadata.get("warning_count", 0),
                "recommendation": self.model_metadata.get("recommendation", "retrain_or_resave_model_with_current_sklearn"),
            }

        try:
            promotion_prediction = self._predict_with_confidence(
                self.promotion_allowed_model,
                x,
                self.promotion_allowed_model_path,
            )

            action_prediction = self._predict_with_confidence(
                self.progression_action_model,
                x,
                self.progression_action_model_path,
            )
        except Exception as exc:
            fallback_action = self._fallback_progression_action(evidence)
            metadata = {
                **self.model_metadata,
                "model_status": "unavailable_runtime_error",
                "model_loaded": False,
                "fallback_used": True,
                "fallback_reason": "model_prediction_error",
                "error_message": str(exc),
                "recommendation": "retrain_or_resave_model_with_current_sklearn",
            }
            return {
                "status": "success",
                "module": "ModelBasedPromotionPredictor",
                "comparison_only": self.comparison_only,
                "feature_columns": FEATURE_COLUMNS,
                "input_features": {
                    col: float(evidence.get(col, 0.0) or 0.0)
                    for col in FEATURE_COLUMNS
                },
                "model_promotion_allowed": bool(float(evidence.get("mastery", 0.0) or 0.0) >= 0.75),
                "model_promotion_allowed_raw": int(float(evidence.get("mastery", 0.0) or 0.0) >= 0.75),
                "model_promotion_allowed_confidence": 0.0,
                "model_promotion_allowed_probabilities": {},
                "model_progression_action": fallback_action,
                "model_progression_action_confidence": 0.0,
                "model_progression_action_probabilities": {},
                **metadata,
            }

        return {
            "status": "success",
            "module": "ModelBasedPromotionPredictor",
            "comparison_only": self.comparison_only,
            "feature_columns": FEATURE_COLUMNS,
            "input_features": {
                col: float(evidence.get(col, 0.0) or 0.0)
                for col in FEATURE_COLUMNS
            },
            "model_promotion_allowed": bool(int(promotion_prediction.label)),
            "model_promotion_allowed_raw": int(promotion_prediction.label),
            "model_promotion_allowed_confidence": promotion_prediction.confidence,
            "model_promotion_allowed_probabilities": promotion_prediction.probabilities,
            "model_progression_action": str(action_prediction.label),
            "model_progression_action_confidence": action_prediction.confidence,
            "model_progression_action_probabilities": action_prediction.probabilities,
            "model_status": "comparison_only_not_overriding_baseline",
            "model_loaded": True,
            "fallback_used": False,
            "fallback_reason": None,
            "current_sklearn_version": self.model_metadata.get("current_sklearn_version"),
            "warning_count": self.model_metadata.get("warning_count", 0),
            "recommendation": "model_available",
        }

    def _fallback_progression_action(self, evidence: Dict[str, Any]) -> str:
        mastery = float(evidence.get("mastery", 0.0) or 0.0)
        evaluation_score = float(evidence.get("evaluation_score", 0.0) or 0.0)
        if mastery >= 0.75 and evaluation_score >= 0.8:
            return "promote_next"
        if evaluation_score < 0.45:
            return "stay_same_level"
        return "same_level_change_view_or_practice"


def predict_promotion_with_model(evidence: Dict[str, Any]) -> Dict[str, Any]:
    predictor = ModelBasedPromotionPredictor()
    return predictor.predict(evidence)
