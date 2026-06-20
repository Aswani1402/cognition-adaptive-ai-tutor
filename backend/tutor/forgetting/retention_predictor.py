"""
Model-supported retention / forgetting predictions with rule-based fallback.

Artifacts live under ``models/forgetting/``. When artifacts or evidence are
insufficient, callers should keep using the existing revision scheduler output.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd

FEATURE_NAMES: Tuple[str, ...] = (
    "mastery_score",
    "previous_mastery_score",
    "recent_score",
    "average_recent_score",
    "correctness_rate",
    "wrong_streak",
    "attempt_count",
    "time_gap_hours",
    "time_gap_days",
    "days_since_last_practice",
    "behaviour_risk",
    "behaviour_confidence",
    "confidence",
    "hint_usage",
    "mistake_count",
    "high_severity_mistake_count",
    "review_count",
    "last_review_score",
    "revision_due_existing",
    "difficulty_encoded",
    "concept_position",
    "reward_xp",
    "anomaly_score",
)

def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


def _bool01(value: Any) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return 1.0 if float(value) >= 0.5 else 0.0
    if isinstance(value, str):
        return 1.0 if value.strip().lower() in {"1", "true", "yes", "due"} else 0.0
    return 0.0


def _recent_scores_list(evidence: Dict[str, Any]) -> List[float]:
    raw = evidence.get("recent_scores")
    if isinstance(raw, list) and raw:
        out: List[float] = []
        for x in raw:
            try:
                out.append(float(x))
            except Exception:
                continue
        return out[-12:]
    return []


def _first_present(*values: Any, default: Any = None) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return default


def evidence_to_feature_vector(evidence: Dict[str, Any]) -> Dict[str, float]:
    """Map free-form evidence into the fixed training feature schema."""
    scores = _recent_scores_list(evidence)
    recent = float(scores[-1]) if scores else _safe_float(evidence.get("recent_score"), 0.0)
    avg_recent = (
        float(sum(scores) / len(scores)) if scores else _safe_float(evidence.get("average_recent_score"), recent)
    )
    streak = 0.0
    if scores:
        for s in reversed(scores):
            if s < 0.55:
                streak += 1.0
            else:
                break
    else:
        streak = _safe_float(evidence.get("wrong_streak"), 0.0)

    mastery = _safe_float(
        _first_present(
            evidence.get("mastery_score"),
            evidence.get("predicted_mastery_last"),
            default=0.5,
        ),
        0.5,
    )
    prev_m = _safe_float(
        evidence.get("previous_mastery_score"),
        max(0.0, min(1.0, mastery - 0.05)),
    )
    raw_days = _first_present(evidence.get("days_since_last_practice"), evidence.get("time_gap_days"))
    days_gap = _safe_float(raw_days, 0.0)
    if days_gap <= 0 and evidence.get("time_gap_hours") is not None:
        days_gap = _safe_float(evidence.get("time_gap_hours"), 0.0) / 24.0
    hours_gap = _safe_float(evidence.get("time_gap_hours"), days_gap * 24.0)

    diff_raw = str(evidence.get("difficulty") or "medium").lower()
    diff_map = {"easy": 0.0, "medium": 1.0, "hard": 2.0}
    diff_enc = diff_map.get(diff_raw, 1.0)

    concept_pos = _safe_float(evidence.get("concept_position"), 0.0)
    if concept_pos == 0.0 and evidence.get("concept_id") is not None:
        try:
            concept_pos = min(1.0, abs(int(str(evidence.get("concept_id")).strip() or "0")) / 50.0)
        except Exception:
            concept_pos = 0.1

    return {
        "mastery_score": mastery,
        "previous_mastery_score": prev_m,
        "recent_score": recent,
        "average_recent_score": avg_recent,
        "correctness_rate": _safe_float(evidence.get("correctness_rate"), avg_recent),
        "wrong_streak": streak,
        "attempt_count": float(_safe_int(evidence.get("attempt_count"), len(scores) or 1)),
        "time_gap_hours": hours_gap,
        "time_gap_days": days_gap,
        "days_since_last_practice": days_gap,
        "behaviour_risk": _safe_float(evidence.get("behaviour_risk"), 0.0),
        "behaviour_confidence": _safe_float(evidence.get("behaviour_confidence"), 0.5),
        "confidence": _safe_float(evidence.get("confidence"), 0.5),
        "hint_usage": _safe_float(
            _first_present(evidence.get("hint_usage"), evidence.get("hint_count_used"), default=0.0),
            0.0,
        ),
        "mistake_count": float(_safe_int(evidence.get("mistake_count"), 0)),
        "high_severity_mistake_count": float(_safe_int(evidence.get("high_severity_mistake_count"), 0)),
        "review_count": float(_safe_int(evidence.get("review_count"), 0)),
        "last_review_score": _safe_float(evidence.get("last_review_score"), 0.0),
        "revision_due_existing": _bool01(evidence.get("revision_due_existing", evidence.get("review_due"))),
        "difficulty_encoded": diff_enc,
        "concept_position": concept_pos,
        "reward_xp": float(_safe_int(evidence.get("reward_xp"), 0)),
        "anomaly_score": _safe_float(evidence.get("anomaly_score"), 0.0),
    }


def _evidence_sufficient(evidence: Dict[str, Any]) -> bool:
    if not str(evidence.get("learner_id") or "").strip():
        return False
    signals = (
        "mastery_score",
        "recent_score",
        "average_recent_score",
        "fused_score",
        "attempt_count",
        "days_since_last_practice",
        "time_gap_days",
        "correctness_rate",
    )
    if any(evidence.get(k) is not None for k in signals):
        return True
    if _recent_scores_list(evidence):
        return True
    if str(evidence.get("concept_id") or "").strip():
        return True
    return False


def _fallback_from_evidence(evidence: Dict[str, Any]) -> Dict[str, Any]:
    feats = evidence_to_feature_vector(evidence)
    mastery = feats["mastery_score"]
    avg_r = feats["average_recent_score"]
    days = feats["days_since_last_practice"]
    streak = int(feats["wrong_streak"])
    rev_due = bool(feats["revision_due_existing"] >= 0.5 or _bool01(evidence.get("review_due")) >= 0.5)

    high = (
        mastery < 0.35
        or (avg_r < 0.4 and feats["attempt_count"] >= 2)
        or days >= 14
        or streak >= 4
        or rev_due
    )
    low = mastery >= 0.78 and days <= 3 and avg_r >= 0.7 and streak == 0 and not rev_due
    if high:
        risk = "high"
    elif low:
        risk = "low"
    else:
        risk = "medium"

    review_due = bool(
        rev_due
        or (days >= 7 and mastery < 0.65)
        or (days >= 3 and mastery < 0.45)
        or streak >= 3
    )

    if risk == "high" or (review_due and mastery < 0.5):
        prio = "high_priority"
    elif risk == "low" and not review_due:
        prio = "low_priority"
    else:
        prio = "medium_priority"

    if mastery >= 0.85 and avg_r >= 0.85 and not review_due:
        interval = "one_week"
    elif mastery >= 0.65 and days < 2:
        interval = "three_days"
    elif review_due or mastery < 0.5:
        interval = "same_day"
    else:
        interval = "next_day"

    conf = 0.55
    return {
        "retention_risk_label": risk,
        "review_due": review_due,
        "revision_priority": prio,
        "recommended_review_interval": interval,
        "confidence": conf,
        "top_features": ["time_gap_days", "recent_score", "mastery_score"],
    }


def _top_features_from_model(model: Any, feature_names: List[str], k: int = 5) -> List[str]:
    try:
        est = model
        if hasattr(model, "named_steps"):
            est = model.named_steps.get("clf", model)
        if hasattr(est, "feature_importances_"):
            imp = np.asarray(est.feature_importances_, dtype=float)
            idx = np.argsort(imp)[::-1][:k]
            return [feature_names[i] for i in idx if i < len(feature_names)]
        if hasattr(est, "coef_"):
            coef = np.asarray(est.coef_, dtype=float)
            if coef.ndim == 2:
                mag = np.mean(np.abs(coef), axis=0)
            else:
                mag = np.abs(coef).ravel()
            idx = np.argsort(mag)[::-1][:k]
            return [feature_names[i] for i in idx if i < len(feature_names)]
    except Exception:
        pass
    return list(feature_names[:k])


class RetentionPredictor:
    """Loads supervised retention models and predicts with optional fallback."""

    def __init__(self, model_dir: Optional[Path] = None) -> None:
        self.model_dir = Path(model_dir) if model_dir else _root() / "models" / "forgetting"
        self.meta: Dict[str, Any] = {}
        self._bundles: Dict[str, Any] = {}
        self._loaded = False

    def load(self) -> bool:
        meta_path = self.model_dir / "retention_predictor_meta.json"
        if not meta_path.exists():
            self._loaded = False
            self.meta = {}
            self._bundles = {}
            return False
        try:
            self.meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            self._loaded = False
            self.meta = {}
            self._bundles = {}
            return False

        names = {
            "retention_risk": "retention_risk_model.joblib",
            "review_due": "review_due_model.joblib",
            "revision_priority": "revision_priority_model.joblib",
            "review_interval": "review_interval_model.joblib",
        }
        bundles: Dict[str, Any] = {}
        ok = True
        for key, fname in names.items():
            path = self.model_dir / fname
            if not path.exists():
                ok = False
                continue
            try:
                bundles[key] = joblib.load(path)
            except Exception:
                ok = False
        self._bundles = bundles
        self._loaded = ok and len(bundles) == 4
        return self._loaded

    def _row_matrix(self, evidence: Dict[str, Any]) -> pd.DataFrame:
        feats = evidence_to_feature_vector(evidence)
        fn = list(self.meta.get("feature_names") or FEATURE_NAMES)
        vec = {c: float(feats.get(c, 0.0) or 0.0) for c in fn}
        return pd.DataFrame([vec], columns=fn)

    def _predict_one(
        self,
        key: str,
        X: pd.DataFrame,
    ) -> Tuple[Any, float, List[str]]:
        bundle = self._bundles.get(key) or {}
        model = bundle.get("model")
        le: Any = bundle.get("label_encoder")
        fn = list(bundle.get("feature_names") or self.meta.get("feature_names") or FEATURE_NAMES)
        if model is None or le is None:
            raise RuntimeError(f"missing bundle for {key}")
        proba = None
        try:
            proba = model.predict_proba(X)
        except Exception:
            proba = None
        pred = model.predict(X)[0]
        pred_idx = int(np.asarray(pred).ravel()[0])
        conf = 0.0
        if proba is not None and proba.size:
            conf = float(np.max(proba))
        else:
            conf = 0.55
        label = le.inverse_transform(np.asarray([pred_idx]))[0]
        tops = _top_features_from_model(model, fn, k=5)
        return label, conf, tops

    def predict_retention(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        if not self._loaded:
            fb = _fallback_from_evidence(evidence)
            return {
                "status": "warning",
                "module": "RetentionPredictor",
                "model_used": False,
                "fallback_used": True,
                "retention_risk_label": fb["retention_risk_label"],
                "review_due": fb["review_due"],
                "revision_priority": fb["revision_priority"],
                "recommended_review_interval": fb["recommended_review_interval"],
                "confidence": fb["confidence"],
                "top_features": fb["top_features"],
                "frontend_component": "RetentionRiskCard",
                "limitations": ["Retention model artifact unavailable; fallback revision logic used."],
            }

        if not _evidence_sufficient(evidence):
            fb = _fallback_from_evidence(evidence)
            return {
                "status": "warning",
                "module": "RetentionPredictor",
                "model_used": False,
                "fallback_used": True,
                **fb,
                "frontend_component": "RetentionRiskCard",
                "limitations": [
                    "Evidence insufficient for model input; used rule-based fallback mapping.",
                ],
            }

        X = self._row_matrix(evidence)
        labels: Dict[str, Any] = {}
        confs: List[float] = []
        all_tops: List[str] = []

        try:
            risk, c0, t0 = self._predict_one("retention_risk", X)
            labels["retention_risk_label"] = str(risk)
            confs.append(c0)
            all_tops.extend(t0)

            rd, c1, t1 = self._predict_one("review_due", X)
            rd_str = str(rd).lower()
            if rd_str in {"1", "true", "yes"}:
                labels["review_due"] = True
            elif rd_str in {"0", "false", "no"}:
                labels["review_due"] = False
            else:
                try:
                    labels["review_due"] = bool(int(float(rd_str)))
                except Exception:
                    labels["review_due"] = bool(rd)
            confs.append(c1)
            all_tops.extend(t1)

            prio, c2, t2 = self._predict_one("revision_priority", X)
            labels["revision_priority"] = str(prio)
            confs.append(c2)
            all_tops.extend(t2)

            interval, c3, t3 = self._predict_one("review_interval", X)
            labels["recommended_review_interval"] = str(interval)
            confs.append(c3)
            all_tops.extend(t3)
        except Exception as exc:
            fb = _fallback_from_evidence(evidence)
            return {
                "status": "warning",
                "module": "RetentionPredictor",
                "model_used": False,
                "fallback_used": True,
                **fb,
                "frontend_component": "RetentionRiskCard",
                "limitations": [f"Prediction error: {type(exc).__name__}: {exc}"],
            }

        conf_mean = float(sum(confs) / max(1, len(confs)))
        top_unique: List[str] = []
        for name in all_tops:
            if name not in top_unique:
                top_unique.append(name)
            if len(top_unique) >= 5:
                break

        return {
            "status": "success",
            "module": "RetentionPredictor",
            "model_used": True,
            "fallback_used": False,
            **labels,
            "confidence": round(conf_mean, 4),
            "top_features": top_unique[:5],
            "frontend_component": "RetentionRiskCard",
            "limitations": [],
        }

    def predict_with_fallback(
        self,
        evidence: Dict[str, Any],
        fallback_revision: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        out = self.predict_retention(evidence)
        if out.get("model_used"):
            return out

        fb = fallback_revision or {}
        sched_prio = str(fb.get("revision_priority") or "")
        if sched_prio in {"low", "medium", "high"}:
            mapped = {"low": "low_priority", "medium": "medium_priority", "high": "high_priority"}
            out["revision_priority"] = mapped.get(sched_prio, out.get("revision_priority"))

        if "review_due" in fb and fb.get("review_due") is not None:
            out["review_due"] = bool(fb.get("review_due"))

        tag = "Merged scheduler fallback fields where available."
        lims = list(out.get("limitations") or [])
        if tag not in lims:
            lims.append(tag)
        out["limitations"] = lims
        return out

    def explain_prediction(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        base = self.predict_retention(evidence)
        explanations: Dict[str, Any] = {}
        fn = list(self.meta.get("feature_names") or FEATURE_NAMES)
        vec = evidence_to_feature_vector(evidence)
        for key, title in (
            ("retention_risk", "retention_risk_label"),
            ("review_due", "review_due"),
            ("revision_priority", "revision_priority"),
            ("review_interval", "recommended_review_interval"),
        ):
            bundle = self._bundles.get(key) or {}
            model = bundle.get("model")
            if model is None:
                explanations[title] = {"reason": "model_not_loaded", "top_features": []}
                continue
            tops = _top_features_from_model(model, list(bundle.get("feature_names") or fn), k=8)
            explanations[title] = {
                "top_features": tops,
                "feature_values": {k: vec.get(k, 0.0) for k in tops[:5]},
            }
        return {
            "status": base.get("status"),
            "module": "RetentionPredictor",
            "model_used": base.get("model_used"),
            "fallback_used": base.get("fallback_used"),
            "prediction": {k: base.get(k) for k in ("retention_risk_label", "review_due", "revision_priority", "recommended_review_interval", "confidence")},
            "per_target": explanations,
            "limitations": base.get("limitations", []),
        }

    def recommend_review_interval(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        pred = self.predict_retention(evidence)
        return {
            "status": pred.get("status"),
            "module": "RetentionPredictor",
            "recommended_review_interval": pred.get("recommended_review_interval"),
            "model_used": pred.get("model_used"),
            "fallback_used": pred.get("fallback_used"),
            "confidence": pred.get("confidence"),
            "limitations": pred.get("limitations", []),
        }
