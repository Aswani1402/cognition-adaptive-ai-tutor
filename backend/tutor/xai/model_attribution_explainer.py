"""
Model-level attribution explainer for Cognition-Adaptive AI Tutor.

Default method:
- sklearn permutation importance

Optional:
- SHAP only if installed

This module does NOT replace the existing XAI dashboard.
It adds model-level feature attribution where trained sklearn models/datasets are available.
"""

from __future__ import annotations

import json
import pickle
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class AttributionResult:
    status: str
    module: str
    target_name: str
    model_type: str
    method_used: str
    shap_available: bool
    feature_importances: List[Dict[str, Any]]
    top_features: List[str]
    explanation_text: str
    limitations: List[str]


class ModelAttributionExplainer:
    """
    Explains trained sklearn-like models using dependency-safe attribution.

    Main method:
    - permutation_importance

    Fallbacks:
    - builtin feature_importances_ for tree models
    - coef_ for linear models
    - safe warning output if model/dataset missing
    """

    def __init__(self, random_state: int = 42, n_repeats: int = 5):
        self.random_state = random_state
        self.n_repeats = n_repeats
        self.shap_available = self._check_shap_available()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def explain_model(
        self,
        model_path: Optional[str] = None,
        dataset_path: Optional[str] = None,
        target_name: str = "model",
        feature_names: Optional[List[str]] = None,
        target_column: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not model_path:
            return self._warning_result(
                target_name=target_name,
                reason="model_path_missing",
                missing_path=None,
            )

        model_file = Path(model_path)
        if not model_file.exists():
            return self._warning_result(
                target_name=target_name,
                reason="model_file_not_found",
                missing_path=str(model_file),
            )

        if not dataset_path:
            return self._warning_result(
                target_name=target_name,
                reason="dataset_path_missing",
                missing_path=None,
            )

        data_file = Path(dataset_path)
        if not data_file.exists():
            return self._warning_result(
                target_name=target_name,
                reason="dataset_file_not_found",
                missing_path=str(data_file),
            )

        try:
            model = self._load_model(model_file)
            X, y, inferred_features = self._load_dataset(
                data_file,
                target_column=target_column,
                feature_names=feature_names,
            )
            final_feature_names = feature_names or inferred_features

            return self.explain_model_object(
                model=model,
                X=X,
                y=y,
                target_name=target_name,
                feature_names=final_feature_names,
            )

        except Exception as exc:
            return self._warning_result(
                target_name=target_name,
                reason=f"explain_model_failed: {exc}",
                missing_path=None,
            )

    def explain_model_object(
        self,
        model: Any,
        X: Any,
        y: Any,
        target_name: str = "model",
        feature_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        feature_names = feature_names or self._infer_feature_names(X)

        model_type = type(model).__name__
        method_used = "permutation_importance"
        limitations = [
            "Permutation importance depends on the evaluation dataset.",
            "Correlated features can share or hide importance.",
            "This does not replace the existing XAI dashboard; it complements it.",
        ]

        try:
            importances = self.compute_permutation_importance(
                model=model,
                X=X,
                y=y,
                feature_names=feature_names,
            )
            method_used = "permutation_importance"
        except Exception as exc:
            warnings.warn(f"Permutation importance failed: {exc}")
            importances = self.compute_builtin_importance(
                model=model,
                feature_names=feature_names,
            )
            method_used = "builtin_importance"

        if not importances:
            return self._warning_result(
                target_name=target_name,
                reason="no_importance_available",
                missing_path=None,
            )

        importances = self._rank_importances(importances)
        top_features = self.summarize_top_features(importances, top_k=5)

        explanation_text = self._make_explanation_text(
            target_name=target_name,
            top_features=top_features,
            method_used=method_used,
        )

        result = AttributionResult(
            status="success",
            module="ModelAttributionExplainer",
            target_name=target_name,
            model_type=model_type,
            method_used=method_used,
            shap_available=self.shap_available,
            feature_importances=importances,
            top_features=top_features,
            explanation_text=explanation_text,
            limitations=limitations,
        )
        return result.__dict__

    def explain_prediction(
        self,
        model: Any,
        sample_features: Any,
        feature_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        feature_names = feature_names or self._infer_feature_names(sample_features)

        try:
            prediction = model.predict(sample_features)
            proba = None
            if hasattr(model, "predict_proba"):
                proba = model.predict_proba(sample_features).tolist()

            return {
                "status": "success",
                "module": "ModelAttributionExplainer",
                "prediction": prediction.tolist() if hasattr(prediction, "tolist") else prediction,
                "prediction_probability": proba,
                "feature_names": feature_names,
                "note": "Prediction explanation requires dataset-level attribution for feature importance.",
            }
        except Exception as exc:
            return {
                "status": "warning",
                "module": "ModelAttributionExplainer",
                "reason": f"prediction_failed: {exc}",
            }

    def explain_synthetic_demo(self) -> Dict[str, Any]:
        """
        Always available demo attribution to prove module works even when
        real model artifacts are missing.
        """
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split

        rng = np.random.default_rng(self.random_state)
        n = 240

        mastery_score = rng.uniform(0, 1, n)
        behaviour_risk = rng.uniform(0, 1, n)
        fused_score = rng.uniform(0, 1, n)
        hint_rate = rng.uniform(0, 1, n)
        wrong_rate = rng.uniform(0, 1, n)

        X = pd.DataFrame(
            {
                "mastery_score": mastery_score,
                "behaviour_risk": behaviour_risk,
                "fused_score": fused_score,
                "hint_rate": hint_rate,
                "wrong_rate": wrong_rate,
            }
        )

        y = (
            (mastery_score > 0.55)
            & (fused_score > 0.50)
            & (behaviour_risk < 0.60)
            & (wrong_rate < 0.55)
        ).astype(int)

        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=0.25,
            random_state=self.random_state,
            stratify=y,
        )

        model = RandomForestClassifier(
            n_estimators=80,
            random_state=self.random_state,
            max_depth=5,
        )
        model.fit(X_train, y_train)

        result = self.explain_model_object(
            model=model,
            X=X_test,
            y=y_test,
            target_name="synthetic_promotion_readiness_demo",
            feature_names=list(X.columns),
        )
        result["demo_accuracy"] = float(model.score(X_test, y_test))
        return result

    # ------------------------------------------------------------------
    # Attribution methods
    # ------------------------------------------------------------------

    def compute_permutation_importance(
        self,
        model: Any,
        X: Any,
        y: Any,
        feature_names: List[str],
    ) -> List[Dict[str, Any]]:
        from sklearn.inspection import permutation_importance

        scoring = "accuracy"
        result = permutation_importance(
            model,
            X,
            y,
            n_repeats=self.n_repeats,
            random_state=self.random_state,
            scoring=scoring,
        )

        importances = []
        for idx, feature in enumerate(feature_names):
            value = float(result.importances_mean[idx])
            importances.append(
                {
                    "feature": str(feature),
                    "importance": round(value, 6),
                    "importance_std": round(float(result.importances_std[idx]), 6),
                }
            )
        return importances

    def summarize_top_features(
        self,
        importances: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[str]:
        ranked = self._rank_importances(list(importances))
        return [str(item["feature"]) for item in ranked[:top_k]]

    def compute_builtin_importance(
        self,
        model: Any,
        feature_names: List[str],
    ) -> List[Dict[str, Any]]:
        estimator = self._extract_final_estimator(model)

        values = None

        if hasattr(estimator, "feature_importances_"):
            values = estimator.feature_importances_
        elif hasattr(estimator, "coef_"):
            coef = estimator.coef_
            values = np.mean(np.abs(coef), axis=0) if len(coef.shape) > 1 else np.abs(coef)

        if values is None:
            return []

        values = np.asarray(values).flatten()

        length = min(len(values), len(feature_names))
        importances = []
        for idx in range(length):
            importances.append(
                {
                    "feature": str(feature_names[idx]),
                    "importance": round(float(values[idx]), 6),
                    "importance_std": 0.0,
                }
            )
        return importances

    def compute_model_builtin_importance(
        self,
        model: Any,
        feature_names: List[str],
    ) -> List[Dict[str, Any]]:
        """Backward-compatible alias for :meth:`compute_builtin_importance`."""
        return self.compute_builtin_importance(model=model, feature_names=feature_names)

    def compute_shap_importance(
        self,
        model: Any,
        X: Any,
        feature_names: List[str],
    ) -> Dict[str, Any]:
        if not self.shap_available:
            return {
                "status": "warning",
                "reason": "shap_not_available",
            }

        try:
            import shap  # type: ignore

            explainer = shap.Explainer(model, X)
            shap_values = explainer(X)

            values = np.abs(shap_values.values).mean(axis=0)
            importances = []
            for idx, feature in enumerate(feature_names):
                importances.append(
                    {
                        "feature": str(feature),
                        "importance": round(float(values[idx]), 6),
                    }
                )

            return {
                "status": "success",
                "method": "shap",
                "feature_importances": self._rank_importances(importances),
            }
        except Exception as exc:
            return {
                "status": "warning",
                "reason": f"shap_failed: {exc}",
            }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_model(self, model_file: Path) -> Any:
        try:
            import joblib

            return joblib.load(model_file)
        except Exception:
            with model_file.open("rb") as f:
                return pickle.load(f)

    def _load_dataset(
        self,
        data_file: Path,
        target_column: Optional[str] = None,
        feature_names: Optional[List[str]] = None,
    ) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
        df = pd.read_csv(data_file)

        if target_column is None:
            target_column = self._infer_target_column(df)

        if target_column not in df.columns:
            raise ValueError(f"Target column not found: {target_column}")

        y = df[target_column]

        if feature_names:
            available = [c for c in feature_names if c in df.columns]
            if not available:
                raise ValueError("None of the supplied feature names exist in dataset.")
            X = df[available].copy()
        else:
            drop_cols = {target_column}
            for c in ["learner_id", "user_id", "timestamp", "created_at", "updated_at"]:
                if c in df.columns:
                    drop_cols.add(c)

            X = df.drop(columns=list(drop_cols), errors="ignore")

        # keep simple and safe: numeric only for attribution
        X = self._make_numeric_frame(X)
        return X, y, list(X.columns)

    def _make_numeric_frame(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X.copy()

        for col in X.columns:
            if X[col].dtype == "object":
                try:
                    X[col] = pd.to_numeric(X[col])
                except Exception:
                    X[col] = X[col].astype(str).factorize()[0]

        X = X.replace([np.inf, -np.inf], np.nan).fillna(0.0)
        return X

    def _infer_target_column(self, df: pd.DataFrame) -> str:
        candidates = [
            "target",
            "label",
            "correct",
            "is_correct",
            "promotion_allowed",
            "progression_action",
            "behaviour_label",
            "doubt_type",
            "intent",
            "class",
            "y",
        ]
        for col in candidates:
            if col in df.columns:
                return col
        raise ValueError("Could not infer target column.")

    def _infer_feature_names(self, X: Any) -> List[str]:
        if hasattr(X, "columns"):
            return list(X.columns)
        if hasattr(X, "shape"):
            return [f"feature_{i}" for i in range(X.shape[1])]
        return []

    def _extract_final_estimator(self, model: Any) -> Any:
        if hasattr(model, "steps") and model.steps:
            return model.steps[-1][1]
        if hasattr(model, "named_steps") and model.named_steps:
            return list(model.named_steps.values())[-1]
        return model

    def _rank_importances(self, importances: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        ranked = sorted(
            importances,
            key=lambda item: abs(float(item.get("importance", 0.0))),
            reverse=True,
        )
        for idx, item in enumerate(ranked, start=1):
            item["rank"] = idx
        return ranked

    def _make_explanation_text(
        self,
        target_name: str,
        top_features: List[str],
        method_used: str,
    ) -> str:
        if not top_features:
            return f"No dominant features were identified for {target_name}."

        return (
            f"For {target_name}, the {method_used} attribution indicates that "
            f"the strongest contributing features are: {', '.join(top_features[:5])}."
        )

    def _check_shap_available(self) -> bool:
        try:
            import shap  # noqa: F401

            return True
        except Exception:
            return False

    def _warning_result(
        self,
        target_name: str,
        reason: str,
        missing_path: Optional[str],
    ) -> Dict[str, Any]:
        return {
            "status": "warning",
            "module": "ModelAttributionExplainer",
            "target_name": target_name,
            "model_type": "unknown",
            "method_used": "none",
            "shap_available": self.shap_available,
            "feature_importances": [],
            "top_features": [],
            "explanation_text": f"Attribution unavailable for {target_name}: {reason}.",
            "missing_path": missing_path,
            "limitations": [
                "Model attribution requires a trained model artifact and compatible evaluation dataset.",
                "This warning does not affect the existing XAI dashboard.",
            ],
        }


def save_json(path: str | Path, data: Dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2), encoding="utf-8")


if __name__ == "__main__":
    explainer = ModelAttributionExplainer()
    demo = explainer.explain_synthetic_demo()
    print(json.dumps(demo, indent=2))