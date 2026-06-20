"""
Learned / model-supported adaptive hint selection.

Trains supervised models for ``hint_type``, ``hint_level`` (low/medium/high), and hint success.
:class:`AdaptiveHintPolicy` remains the deterministic fallback when artifacts are missing or confidence is low.

Contextual bandit exploration is noted as future work; this module uses supervised sklearn models only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd

from tutor.evaluation.hint_generator import HintGenerator

FEATURE_COLUMNS: List[str] = [
    "score",
    "mastery_score",
    "behaviour_risk",
    "behaviour_confidence",
    "hint_count_used",
    "previous_hint_success",
    "question_type_encoded",
    "mistake_type_encoded",
    "weakest_skill_encoded",
    "difficulty_encoded",
    "time_taken_sec",
    "confidence",
    "wrong_streak",
    "previous_score",
    "anomaly_score",
]

HINT_TYPE_LABELS: Tuple[str, ...] = (
    "small_hint",
    "guided_hint",
    "worked_example",
    "misconception_hint",
    "debug_hint",
    "output_prediction_hint",
    "syntax_hint",
    "next_step_hint",
)

HINT_LEVEL_LABELS: Tuple[str, ...] = ("low", "medium", "high")

MODEL_FILES = {
    "hint_type": "learned_hint_type_model.joblib",
    "hint_level": "learned_hint_level_model.joblib",
    "hint_success": "hint_success_predictor.joblib",
}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _encode_str(s: Any, salt: int = 0) -> float:
    if s is None:
        return float(salt) / 17.0
    return float(abs(hash(str(s).lower())) % 991) / 991.0


def _difficulty_encode(d: Any) -> float:
    m = str(d or "medium").lower().strip()
    if m == "easy":
        return 0.0
    if m == "hard":
        return 2.0
    return 1.0


def evidence_to_feature_row(evidence: Dict[str, Any]) -> Dict[str, float]:
    """Map loose evidence dict to FEATURE_COLUMNS (numeric only)."""
    e = evidence or {}
    score = _safe_float(e.get("score"), 0.5)
    mastery = _safe_float(e.get("mastery_score"), 0.5)
    beh_r = _safe_float(e.get("behaviour_risk"), 0.3)
    beh_c = _safe_float(
        e.get("behaviour_confidence"),
        max(0.0, 1.0 - beh_r),
    )
    return {
        "score": float(np.clip(score, 0.0, 1.0)),
        "mastery_score": float(np.clip(mastery, 0.0, 1.0)),
        "behaviour_risk": float(np.clip(beh_r, 0.0, 1.0)),
        "behaviour_confidence": float(np.clip(beh_c, 0.0, 1.0)),
        "hint_count_used": float(max(0.0, _safe_float(e.get("hint_count_used"), 0.0))),
        "previous_hint_success": float(np.clip(_safe_float(e.get("previous_hint_success"), 0.5), 0.0, 1.0)),
        "question_type_encoded": _encode_str(e.get("question_type"), 1),
        "mistake_type_encoded": _encode_str(e.get("mistake_type"), 2),
        "weakest_skill_encoded": _encode_str(e.get("weakest_skill"), 3),
        "difficulty_encoded": _difficulty_encode(e.get("difficulty")),
        "time_taken_sec": float(np.clip(_safe_float(e.get("time_taken_sec"), 45.0), 1.0, 600.0)) / 600.0,
        "confidence": float(np.clip(_safe_float(e.get("confidence"), 0.6), 0.0, 1.0)),
        "wrong_streak": float(np.clip(_safe_float(e.get("wrong_streak"), 0.0), 0.0, 10.0)) / 10.0,
        "previous_score": float(np.clip(_safe_float(e.get("previous_score"), score), 0.0, 1.0)),
        "anomaly_score": float(
            np.clip(_safe_float(e.get("anomaly_score"), beh_r), 0.0, 1.0)
        ),
    }


def support_need_to_level(support_need: float) -> str:
    if support_need < 0.35:
        return "low"
    if support_need < 0.65:
        return "medium"
    return "high"


def normalize_hint_type(raw: Any) -> str:
    s = str(raw or "").strip()
    if s in HINT_TYPE_LABELS:
        return s
    if s in {"small_hint", "guided_hint", "worked_example"}:
        return "next_step_hint"
    return "guided_hint"


def normalize_hint_level(raw: Any) -> str:
    s = str(raw or "").strip().lower()
    if s in HINT_LEVEL_LABELS:
        return s
    if s in {"small_hint"}:
        return "low"
    if s in {"guided_hint"}:
        return "medium"
    if s in {"worked_example"}:
        return "high"
    return "medium"


@dataclass
class LearnedHintPolicy:
    """Loads sklearn hint models from ``models/hints/``."""

    model_dir: Optional[Path] = None
    confidence_threshold: float = 0.38
    _bundles: Dict[str, Any] = field(default_factory=dict, repr=False)
    _meta: Dict[str, Any] = field(default_factory=dict, repr=False)
    hint_generator: HintGenerator = field(default_factory=HintGenerator)

    def __post_init__(self) -> None:
        self.model_dir = Path(self.model_dir) if self.model_dir else _project_root() / "models" / "hints"

    def load(self) -> bool:
        self._bundles.clear()
        self._meta = {}
        meta_path = self.model_dir / "learned_hint_policy_meta.json"
        if meta_path.exists():
            try:
                self._meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                self._meta = {}
        ok = True
        for key, fname in MODEL_FILES.items():
            path = self.model_dir / fname
            if not path.exists():
                ok = False
                continue
            try:
                self._bundles[key] = joblib.load(path)
            except Exception:
                ok = False
        return ok and len(self._bundles) == len(MODEL_FILES)

    def _predict_one(self, key: str, X: pd.DataFrame) -> Tuple[Optional[str], float]:
        b = self._bundles.get(key)
        if not b:
            return None, 0.0
        model = b.get("model")
        le: Any = b.get("label_encoder")
        if model is None or le is None:
            return None, 0.0
        try:
            pred = model.predict(X)
            lab = le.inverse_transform(np.asarray(pred).astype(int).ravel())[0]
            conf = 0.55
            if hasattr(model, "predict_proba"):
                conf = float(np.max(model.predict_proba(X)[0]))
            return str(lab), conf
        except Exception:
            return None, 0.0

    def predict_hint_success(self, evidence: Dict[str, Any], hint_type: str) -> Dict[str, Any]:
        feats = evidence_to_feature_row({**evidence, "question_type": evidence.get("question_type")})
        X = pd.DataFrame([[feats[c] for c in FEATURE_COLUMNS]], columns=FEATURE_COLUMNS)
        b = self._bundles.get("hint_success")
        if not b:
            return {"predicted_success_probability": 0.5, "status": "warning"}
        model = b.get("model")
        le: Any = b.get("label_encoder")
        if model is None or not hasattr(model, "predict_proba"):
            return {"predicted_success_probability": 0.55, "status": "success"}
        try:
            proba = model.predict_proba(X)[0]
            classes = list(le.classes_)
            pos_idx = None
            for i, c in enumerate(classes):
                if str(c) in ("1", "True", "true") or c == 1:
                    pos_idx = i
                    break
            if pos_idx is None:
                pos_idx = int(np.argmax(proba))
            p = float(proba[pos_idx] if pos_idx < len(proba) else max(proba))
            return {"predicted_success_probability": round(p, 4), "status": "success", "hint_type": hint_type}
        except Exception:
            return {"predicted_success_probability": 0.5, "status": "warning"}

    def predict_hint(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        feats = evidence_to_feature_row(evidence)
        X = pd.DataFrame([[feats[c] for c in FEATURE_COLUMNS]], columns=FEATURE_COLUMNS)

        if len(self._bundles) < len(MODEL_FILES):
            return {
                "status": "warning",
                "module": "LearnedHintPolicy",
                "model_used": False,
                "fallback_used": True,
                "hint_type": "guided_hint",
                "hint_level": "medium",
                "hint_text": "Review the main idea, then try one small step before answering again.",
                "predicted_success_probability": 0.5,
                "confidence": 0.0,
                "top_features": [],
                "model_versions": {},
                "frontend_component": "AdaptiveHintCard",
                "limitations": ["Learned hint model artifact unavailable; fallback policy used."],
            }

        ht, c1 = self._predict_one("hint_type", X)
        hl, c2 = self._predict_one("hint_level", X)
        ht = normalize_hint_type(ht)
        hl = normalize_hint_level(hl)
        succ = self.predict_hint_success(evidence, ht)
        p_succ = float(succ.get("predicted_success_probability", 0.5))
        conf = float(np.mean([c1, c2, p_succ]))

        norm_evidence = {**evidence, "question_type": evidence.get("question_type", "general")}
        hint_text = self.hint_generator.generate(hint_type=ht, evidence=norm_evidence)

        top = sorted(feats.items(), key=lambda kv: abs(kv[1]), reverse=True)[:6]
        top_features = [k for k, _ in top]

        return {
            "status": "success",
            "module": "LearnedHintPolicy",
            "model_used": True,
            "fallback_used": False,
            "hint_type": ht,
            "hint_level": hl,
            "hint_text": hint_text,
            "predicted_success_probability": round(p_succ, 4),
            "confidence": round(conf, 4),
            "top_features": top_features,
            "model_versions": dict(self._meta.get("best_model_per_target", {})),
            "frontend_component": "AdaptiveHintCard",
            "limitations": list(self._meta.get("limitations", []))[:10],
        }

    def predict_with_fallback(
        self,
        evidence: Dict[str, Any],
        fallback_hint: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        pred = self.predict_hint(evidence)
        fb = fallback_hint or {}
        low = pred.get("confidence", 0.0) < self.confidence_threshold
        if pred.get("model_used") is True and pred.get("status") == "success" and not low:
            pred["fallback_used"] = False
            return pred

        pred["fallback_used"] = True
        pred["model_used"] = False
        pred["status"] = "warning"
        lims = list(dict.fromkeys(pred.get("limitations") or []))
        if low:
            lims.append("Learned confidence below threshold; merged deterministic AdaptiveHintPolicy output.")
        else:
            lims.append("Learned hint model artifact unavailable; fallback policy used.")
        pred["limitations"] = lims

        pred["hint_type"] = normalize_hint_type(fb.get("hint_type") or pred.get("hint_type"))
        pred["hint_text"] = fb.get("hint_text") or pred.get("hint_text")
        sn = _safe_float(fb.get("support_need"), 0.5)
        pred["hint_level"] = support_need_to_level(sn)
        pred["predicted_success_probability"] = round(
            float(pred.get("predicted_success_probability", 0.5)) * 0.85,
            4,
        )
        pred["confidence"] = round(min(pred.get("confidence", 0.0), 0.45), 4)
        if "evidence" in fb:
            pred["evidence"] = fb.get("evidence")
        if "support_need" in fb:
            pred["support_need"] = fb.get("support_need")
        return pred

    def explain_prediction(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        feats = evidence_to_feature_row(evidence)
        ranked = sorted(feats.items(), key=lambda kv: abs(kv[1]), reverse=True)[:8]
        return {
            "status": "success",
            "module": "LearnedHintPolicy",
            "top_features": [{"feature": k, "value": round(v, 4)} for k, v in ranked],
            "note": "Feature magnitudes on normalized evidence vector (diagnostic).",
        }
