"""
Learned teaching-strategy selector (model-supported mode).

Trained sklearn models predict teaching view, difficulty, next action, and assessment group
from engineered evidence features. The rule-based selector in ``tutor.strategy.selector`` remains
the safety baseline; this module never replaces it when artifacts are missing or confidence is low.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd

FEATURE_COLUMNS: List[str] = [
    "mastery_score",
    "behaviour_risk",
    "behaviour_confidence",
    "fused_score",
    "fusion_confidence",
    "mistake_count",
    "high_severity_mistake_count",
    "wrong_output_count",
    "syntax_mistake_count",
    "debug_score",
    "output_prediction_score",
    "weakest_skill_encoded",
    "dominant_mistake_type_encoded",
    "rag_support_score",
    "review_priority",
    "hint_usage",
    "reward_xp",
    "anomaly_score",
    "previous_score",
    "current_difficulty_encoded",
]

TEACHING_VIEW_LABELS: Tuple[str, ...] = (
    "definition_view",
    "step_by_step_view",
    "code_view",
    "debug_view",
    "output_prediction_view",
    "misconception_view",
    "revision_view",
    "challenge_view",
    "transfer_view",
)

DIFFICULTY_LABELS: Tuple[str, ...] = ("easy", "medium", "hard")

NEXT_ACTION_LABELS: Tuple[str, ...] = (
    "continue",
    "practice",
    "reteach",
    "review",
    "challenge",
    "next_concept",
)

ASSESSMENT_GROUP_LABELS: Tuple[str, ...] = (
    "mcq_basic",
    "code_practice",
    "debug_practice",
    "output_prediction_practice",
    "explanation_transfer",
    "challenge_mix",
    "revision_mix",
)

MODEL_FILES = {
    "teaching_view": "teaching_strategy_view_model.joblib",
    "difficulty": "teaching_strategy_difficulty_model.joblib",
    "next_action": "teaching_strategy_next_action_model.joblib",
    "assessment_type_group": "teaching_strategy_assessment_group_model.joblib",
}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _safe_json(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return default


def _encode_label(s: Any, salt: int = 0) -> float:
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return float(salt)
    return float(abs(hash(str(s).lower())) % 997) / 997.0


def _difficulty_encode(d: Any) -> float:
    m = str(d or "medium").lower().strip()
    if m == "easy":
        return 0.0
    if m == "hard":
        return 2.0
    return 1.0


def evidence_to_feature_row(evidence: Dict[str, Any]) -> Dict[str, float]:
    """
    Map a loose evidence dict (pipeline / JSON) onto FEATURE_COLUMNS.
    Missing keys become safe numeric defaults.
    """
    e = evidence or {}
    nested = e.get("evidence") if isinstance(e.get("evidence"), dict) else {}
    fusion = e.get("evaluation_fusion") if isinstance(e.get("evaluation_fusion"), dict) else {}
    mistake = e.get("mistake_analysis") if isinstance(e.get("mistake_analysis"), dict) else {}

    def pick(*keys: str, default: float = 0.0) -> float:
        for src in (e, nested, fusion, mistake):
            if not isinstance(src, dict):
                continue
            for k in keys:
                if k in src and src[k] is not None:
                    return _safe_float(src[k], default)
        return default

    mastery = pick("mastery_score", "mastery_before", "mastery", default=0.5)
    beh_risk = pick("behaviour_risk", "behavior_risk", default=0.5)
    beh_conf = pick("behaviour_confidence", "behavior_confidence", default=max(0.0, 1.0 - beh_risk))
    fused = pick("fused_score", "evaluation_score", default=pick("evaluation_score", default=0.5))
    fus_conf = pick("fusion_confidence", "fusion_confidence_label", default=0.75)
    if fus_conf > 1.0:
        fus_conf = min(1.0, fus_conf / 100.0) if fus_conf > 2 else 1.0

    row = {
        "mastery_score": mastery,
        "behaviour_risk": beh_risk,
        "behaviour_confidence": beh_conf,
        "fused_score": fused,
        "fusion_confidence": float(np.clip(fus_conf, 0.0, 1.0)),
        "mistake_count": pick("mistake_count", default=float(mistake.get("mistake_type_counts", {}) != {})),
        "high_severity_mistake_count": float(
            mistake.get("high_severity_count")
            or mistake.get("high_severity_mistake_count")
            or 0.0
        ),
        "wrong_output_count": pick("wrong_output_count", default=0.0),
        "syntax_mistake_count": pick("syntax_mistake_count", default=0.0),
        "debug_score": pick("debug_score", default=0.1),
        "output_prediction_score": pick("output_prediction_score", default=fused),
        "weakest_skill_encoded": _encode_label(pick("weakest_skill", default=nested.get("weakest_skill")), 1),
        "dominant_mistake_type_encoded": _encode_label(
            mistake.get("dominant_mistake_type") or e.get("dominant_mistake_type"),
            2,
        ),
        "rag_support_score": pick("rag_support_score", default=0.55),
        "review_priority": pick("review_priority", "forgetting_priority", default=0.0),
        "hint_usage": pick("hint_usage", "hint_rate", default=0.0),
        "reward_xp": pick("reward_xp", "xp", default=0.0),
        "anomaly_score": pick("anomaly_score", default=beh_risk),
        "previous_score": pick("previous_score", default=fused),
        "current_difficulty_encoded": _difficulty_encode(
            e.get("difficulty") or e.get("base_difficulty") or nested.get("adaptive_path_difficulty")
        ),
    }

    if isinstance(mistake.get("mistake_type_counts"), dict):
        row["mistake_count"] = float(sum(mistake["mistake_type_counts"].values()))

    return {k: float(np.clip(row.get(k, 0.0), -1e6, 1e6)) for k in FEATURE_COLUMNS}


def normalize_teaching_view_label(raw: Any) -> str:
    s = str(raw or "").strip().lower().replace("-", "_").replace(" ", "_")
    allowed = set(TEACHING_VIEW_LABELS)
    if not s:
        return "definition_view"
    if "output" in s and "prediction" in s:
        return "output_prediction_view"
    if s in allowed:
        return s
    aliases = {
        "definition": "definition_view",
        "revision": "revision_view",
        "simple_code_view": "code_view",
        "analogy_view": "step_by_step_view",
        "flashcard_view": "revision_view",
        "mindmap_view": "transfer_view",
    }
    if s in aliases:
        return aliases[s]
    if "def" in s:
        return "definition_view"
    if "code" in s and "debug" not in s:
        return "code_view"
    if "debug" in s:
        return "debug_view"
    if "misconception" in s:
        return "misconception_view"
    if "revision" in s:
        return "revision_view"
    if "challenge" in s:
        return "challenge_view"
    if "transfer" in s:
        return "transfer_view"
    return "step_by_step_view"


def normalize_difficulty_label(raw: Any) -> str:
    s = str(raw or "medium").lower().strip()
    return s if s in DIFFICULTY_LABELS else "medium"


def map_next_action_label(progression: Any, next_activity: Any) -> str:
    p = str(progression or "").lower()
    n = str(next_activity or "").lower()
    if "advance" in p or "next_concept" in n or "level_up" in p:
        return "next_concept"
    if "reteach" in p or "reteach" in n:
        return "reteach"
    if "review" in p or "review" in n:
        return "review"
    if "challenge" in n or "challenge" in p:
        return "challenge"
    if "practice" in p or "practice" in n:
        return "practice"
    return "continue"


def infer_assessment_group_label(assessment_types: Any) -> str:
    if not isinstance(assessment_types, list):
        assessment_types = []
    types = {str(t).lower() for t in assessment_types}
    if not types:
        return "mcq_basic"
    if "revision" in str(assessment_types).lower():
        return "revision_mix"
    if types & {"debug", "debug_task"}:
        return "debug_practice"
    if "output_prediction" in types:
        return "output_prediction_practice"
    if types & {"challenge", "challenge_question"}:
        return "challenge_mix"
    if types & {"transfer", "transfer_question"}:
        return "explanation_transfer"
    if types & {"coding_question", "code_tracing", "syntax_completion"}:
        return "code_practice"
    if types & {"explanation_check", "explanation", "short_explanation"}:
        return "explanation_transfer"
    return "mcq_basic"


@dataclass
class LearnedTeachingStrategySelector:
    """Loads per-target sklearn models from ``models/strategy/``."""

    model_dir: Optional[Path] = None
    _bundles: Dict[str, Any] = field(default_factory=dict, repr=False)
    _meta: Dict[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self.model_dir = Path(self.model_dir) if self.model_dir else _project_root() / "models" / "strategy"

    def load(self) -> bool:
        self._bundles.clear()
        self._meta = {}
        meta_path = self.model_dir / "teaching_strategy_model_meta.json"
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

    def _predict_one(self, key: str, X: np.ndarray) -> Tuple[Optional[str], float]:
        bundle = self._bundles.get(key)
        if not bundle:
            return None, 0.0
        model = bundle.get("model")
        le: Any = bundle.get("label_encoder")
        if model is None or le is None:
            return None, 0.0
        try:
            pred = model.predict(X)
            label = le.inverse_transform(np.asarray(pred).astype(int).ravel())[0]
            conf = 0.55
            if hasattr(model, "predict_proba"):
                proba = model.predict_proba(X)[0]
                conf = float(np.max(proba))
            return str(label), conf
        except Exception:
            return None, 0.0

    def predict_strategy(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        feats = evidence_to_feature_row(evidence)
        X = pd.DataFrame([[feats[c] for c in FEATURE_COLUMNS]], columns=FEATURE_COLUMNS)

        if len(self._bundles) < len(MODEL_FILES):
            return {
                "status": "warning",
                "module": "LearnedTeachingStrategySelector",
                "model_used": False,
                "fallback_used": True,
                "teaching_view": "definition_view",
                "difficulty": "medium",
                "next_action": "continue",
                "assessment_type_group": "mcq_basic",
                "confidence": 0.0,
                "model_versions": {k: "missing" for k in MODEL_FILES},
                "top_features": [],
                "limitations": ["One or more model artifacts are missing under models/strategy/."],
            }

        out: Dict[str, Any] = {
            "status": "success",
            "module": "LearnedTeachingStrategySelector",
            "model_used": True,
            "fallback_used": False,
            "model_versions": {
                k: (self._meta.get("best_model_per_target", {}) or {}).get(k, "unknown")
                for k in MODEL_FILES
            },
            "limitations": list(self._meta.get("limitations", []))[:12],
        }
        confs = []
        for key in ("teaching_view", "difficulty", "next_action", "assessment_type_group"):
            lab, c = self._predict_one(key, X)
            out[key] = lab or ("medium" if key == "difficulty" else "continue")
            confs.append(c)
        out["confidence"] = round(float(np.mean(confs)) if confs else 0.0, 4)
        out["top_features"] = self._local_top_features(feats)
        return out

    def predict_with_fallback(
        self,
        evidence: Dict[str, Any],
        fallback_strategy: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        pred = self.predict_strategy(evidence)
        fb = fallback_strategy or {}
        low_conf = pred.get("confidence", 0.0) < 0.35
        need_fallback = (
            pred.get("status") != "success"
            or pred.get("model_used") is not True
            or low_conf
        )
        if not need_fallback:
            pred["fallback_used"] = False
            return pred

        pred["fallback_used"] = True
        pred["model_used"] = False
        pred["status"] = "warning"
        lims = list(dict.fromkeys(pred.get("limitations") or []))
        if low_conf:
            lims.append("Learned confidence below threshold; using rule-based fallback outputs.")
        else:
            lims.append("Model artifacts missing or unavailable; using rule-based fallback outputs.")
        pred["limitations"] = lims

        pred["teaching_view"] = normalize_teaching_view_label(
            fb.get("teaching_view") or pred.get("teaching_view")
        )
        pred["difficulty"] = normalize_difficulty_label(fb.get("difficulty") or pred.get("difficulty"))
        pred["next_action"] = map_next_action_label(fb.get("progression_action"), fb.get("next_activity"))
        pred["assessment_type_group"] = infer_assessment_group_label(fb.get("assessment_types") or [])
        return pred

    def explain_prediction(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        pred = self.predict_strategy(evidence)
        pred["explanation"] = {
            "top_features": pred.get("top_features", []),
            "note": "Local feature magnitudes on the evidence vector (single-row diagnostic).",
        }
        return pred

    @staticmethod
    def _local_top_features(feats: Dict[str, float], top_k: int = 8) -> List[Dict[str, Any]]:
        ranked = sorted(feats.items(), key=lambda kv: abs(kv[1]), reverse=True)[:top_k]
        return [{"feature": k, "importance": round(abs(v), 6), "rank": i + 1} for i, (k, v) in enumerate(ranked)]


def merge_pipeline_evidence(
    evidence_aware_output: Optional[Dict[str, Any]],
    evaluation_fusion_output: Optional[Dict[str, Any]],
    mistake_analysis_output: Optional[Dict[str, Any]],
    policy_output: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Flatten common pipeline outputs into one dict for ``evidence_to_feature_row``."""
    ev: Dict[str, Any] = {}
    if isinstance(evidence_aware_output, dict):
        ev.update(evidence_aware_output.get("evidence_used") or {})
        ev.update(evidence_aware_output.get("evidence") or {})
        ev["difficulty"] = evidence_aware_output.get("difficulty") or ev.get("base_difficulty")
    if isinstance(evaluation_fusion_output, dict):
        fs = evaluation_fusion_output.get("fused_score")
        fc = evaluation_fusion_output.get("fusion_confidence") or evaluation_fusion_output.get("confidence")
        if fs is not None:
            ev["fused_score"] = fs
        if fc is not None:
            ev["fusion_confidence"] = fc
        ev["evaluation_fusion"] = {
            "fused_score": fs,
            "fusion_confidence": fc,
        }
        if evaluation_fusion_output.get("fused_label") is not None:
            ev["fused_label"] = evaluation_fusion_output.get("fused_label")
    if isinstance(mistake_analysis_output, dict):
        ev["mistake_analysis"] = mistake_analysis_output
    if isinstance(policy_output, dict):
        pdata = policy_output.get("data", policy_output)
        if isinstance(pdata, dict):
            ev.setdefault("difficulty", pdata.get("difficulty"))
    return ev
