"""
Learned / model-supported adaptive path ranking.

Prerequisite unlock rules from ``run_dependency_module_final`` / graph logic are **never** bypassed:
candidates are filtered to safe unlocked nodes before any model scores them. If models are missing
or confidence is low, use :class:`tutor.path.adaptive_path_selector.AdaptivePathSelector` output as fallback.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd

PATH_ACTION_LABELS: Tuple[str, ...] = (
    "continue_current",
    "review_current",
    "practice_weak",
    "next_unlocked_concept",
    "challenge_current",
    "remediation_previous",
    "wait_locked_prerequisite",
)

NODE_TYPE_LABELS: Tuple[str, ...] = (
    "lesson",
    "practice",
    "quiz",
    "challenge",
    "revision",
    "boss_test",
)

RANK_BUCKET_LABELS: Tuple[str, ...] = ("low_priority", "medium_priority", "high_priority")

FEATURE_COLUMNS: List[str] = [
    "current_mastery",
    "prerequisite_mastery",
    "behaviour_risk",
    "behaviour_confidence",
    "fused_score",
    "recent_score",
    "wrong_streak",
    "review_due",
    "time_gap_days",
    "attempts_on_concept",
    "hint_usage",
    "mistake_count",
    "weak_concept_flag",
    "concept_unlock_status_encoded",
    "difficulty_encoded",
    "reward_xp",
    "anomaly_score",
    "path_position",
    "candidate_is_prerequisite_satisfied",
    "candidate_is_review_due",
    "candidate_is_next_concept",
    "candidate_is_challenge",
]

MODEL_FILES = {
    "path_action": "adaptive_path_action_model.joblib",
    "node_type": "adaptive_path_node_type_model.joblib",
    "rank_score_bucket": "adaptive_path_rank_bucket_model.joblib",
}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except (TypeError, ValueError):
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


def evidence_and_candidate_to_row(
    evidence: Dict[str, Any],
    candidate: Dict[str, Any],
    *,
    current_concept_id: str,
) -> Dict[str, float]:
    """Build numeric feature row for one candidate + global evidence."""
    e = evidence or {}
    c = candidate or {}
    beh_r = float(np.clip(_safe_float(e.get("behaviour_risk"), 0.3), 0.0, 1.0))
    beh_c = float(
        np.clip(
            _safe_float(e.get("behaviour_confidence"), max(0.0, 1.0 - beh_r)),
            0.0,
            1.0,
        )
    )
    return {
        "current_mastery": float(np.clip(_safe_float(e.get("current_mastery"), 0.5), 0.0, 1.0)),
        "prerequisite_mastery": float(np.clip(_safe_float(e.get("prerequisite_mastery"), 0.5), 0.0, 1.0)),
        "behaviour_risk": beh_r,
        "behaviour_confidence": beh_c,
        "fused_score": float(np.clip(_safe_float(e.get("fused_score"), 0.5), 0.0, 1.0)),
        "recent_score": float(np.clip(_safe_float(e.get("recent_score"), e.get("fused_score", 0.5)), 0.0, 1.0)),
        "wrong_streak": float(np.clip(_safe_float(e.get("wrong_streak"), 0.0), 0.0, 1.0)) / 10.0,
        "review_due": float(np.clip(_safe_float(e.get("review_due"), 0.0), 0.0, 1.0)),
        "time_gap_days": float(np.clip(_safe_float(e.get("time_gap_days"), 1.0), 0.0, 365.0)) / 365.0,
        "attempts_on_concept": float(np.clip(_safe_float(e.get("attempts_on_concept"), 0.0), 0.0, 50.0)) / 50.0,
        "hint_usage": float(np.clip(_safe_float(e.get("hint_usage"), 0.0), 0.0, 30.0)) / 30.0,
        "mistake_count": float(np.clip(_safe_float(e.get("mistake_count"), 0.0), 0.0, 50.0)) / 50.0,
        "weak_concept_flag": 1.0 if bool(e.get("weak_concept_flag")) else 0.0,
        "concept_unlock_status_encoded": _encode_str(e.get("concept_unlock_status"), 1),
        "difficulty_encoded": _difficulty_encode(e.get("difficulty")),
        "reward_xp": float(np.clip(_safe_float(e.get("reward_xp"), 0.0), 0.0, 5000.0)) / 5000.0,
        "anomaly_score": float(np.clip(_safe_float(e.get("anomaly_score"), beh_r), 0.0, 1.0)),
        "path_position": float(np.clip(_safe_float(e.get("path_position"), 0.5), 0.0, 1.0)),
        "candidate_is_prerequisite_satisfied": 1.0 if c.get("prerequisite_satisfied", True) is not False else 0.0,
        "candidate_is_review_due": 1.0 if c.get("is_review_due") or c.get("review_due") else 0.0,
        "candidate_is_next_concept": 1.0
        if str(c.get("concept_id", "")) == str(e.get("recommended_next_concept", ""))
        else 0.0,
        "candidate_is_challenge": 1.0 if c.get("is_challenge") or e.get("difficulty") == "hard" else 0.0,
    }


def derive_teacher_labels(row: Dict[str, float]) -> Tuple[str, str, str]:
    """Rule-based teacher for training labels (imitation); respects safety flags."""
    if row.get("candidate_is_prerequisite_satisfied", 1.0) < 0.5:
        return "wait_locked_prerequisite", "lesson", "low_priority"
    if row.get("review_due", 0.0) > 0.55 and row.get("current_mastery", 0.5) > 0.35:
        return "review_current", "revision", "high_priority"
    if row.get("wrong_streak", 0.0) > 0.35 or row.get("weak_concept_flag", 0.0) > 0.5:
        return "practice_weak", "practice", "high_priority"
    if row.get("fused_score", 0.5) < 0.35 and row.get("behaviour_risk", 0.0) < 0.55:
        return "remediation_previous", "lesson", "medium_priority"
    if row.get("current_mastery", 0.5) > 0.82 and row.get("candidate_is_challenge", 0.0) > 0.5:
        return "challenge_current", "challenge", "medium_priority"
    if row.get("candidate_is_next_concept", 0.0) > 0.5:
        return "next_unlocked_concept", "quiz", "medium_priority"
    if row.get("fused_score", 0.5) > 0.75 and row.get("behaviour_risk", 0.0) < 0.35:
        return "continue_current", "lesson", "low_priority"
    return "next_unlocked_concept", "practice", "medium_priority"


@dataclass
class LearnedAdaptivePathRanker:
    """Loads sklearn models from ``models/path/``; ranks only after prerequisite-safe filtering."""

    model_dir: Optional[Path] = None
    confidence_threshold: float = 0.36
    _bundles: Dict[str, Any] = field(default_factory=dict, repr=False)
    _meta: Dict[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self.model_dir = Path(self.model_dir) if self.model_dir else _project_root() / "models" / "path"

    def load(self) -> bool:
        self._bundles.clear()
        self._meta = {}
        meta_path = self.model_dir / "adaptive_path_ranker_meta.json"
        if meta_path.exists():
            try:
                self._meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                self._meta = {}
        ok = True
        for key, fname in MODEL_FILES.items():
            p = self.model_dir / fname
            if not p.exists():
                ok = False
                continue
            try:
                self._bundles[key] = joblib.load(p)
            except Exception:
                ok = False
        return ok and len(self._bundles) == len(MODEL_FILES)

    def filter_safe_candidates(
        self,
        learner_id: str,
        candidates: List[Dict[str, Any]],
        dependency_output: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Block any candidate not in ``unlocked_concepts`` or listed in ``blocked_concepts``."""
        dep = dependency_output or {}
        unlocked = {str(x) for x in (dep.get("unlocked_concepts") or [])}
        blocked_ids = {
            str(b.get("concept_id"))
            for b in (dep.get("blocked_concepts") or [])
            if isinstance(b, dict) and b.get("concept_id") is not None
        }
        safe: List[Dict[str, Any]] = []
        blocked: List[Dict[str, Any]] = []
        violations = 0
        for raw in candidates:
            c = dict(raw) if isinstance(raw, dict) else {}
            cid = str(c.get("concept_id", "")).strip()
            if not cid:
                blocked.append({**c, "_block_reason": "missing_concept_id"})
                continue
            if cid in blocked_ids:
                violations += 1
                blocked.append({**c, "_block_reason": "in_blocked_concepts"})
                continue
            if unlocked and cid not in unlocked:
                violations += 1
                blocked.append({**c, "_block_reason": "not_unlocked"})
                continue
            if c.get("prerequisite_satisfied") is False:
                violations += 1
                blocked.append({**c, "_block_reason": "prerequisite_satisfied_false"})
                continue
            c.setdefault("prerequisite_satisfied", True)
            safe.append(c)
        return {
            "learner_id": str(learner_id),
            "safe_candidates": safe,
            "blocked_candidates": blocked,
            "safe_candidates_count": len(safe),
            "blocked_candidates_count": len(blocked),
            "safety_violation": violations > 0,
        }

    def _predict_bundle(self, key: str, X: pd.DataFrame) -> Tuple[Optional[str], float]:
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

    def _ranking_score(self, X: pd.DataFrame) -> float:
        """Higher is better: emphasize high-priority bucket probability."""
        b = self._bundles.get("rank_score_bucket")
        if not b or not hasattr(b.get("model"), "predict_proba"):
            return 0.5
        model = b["model"]
        le: Any = b["label_encoder"]
        proba = model.predict_proba(X)[0]
        classes = list(le.classes_)
        score = 0.0
        for i, cls in enumerate(classes):
            w = 0.25
            if str(cls) == "high_priority":
                w = 1.0
            elif str(cls) == "medium_priority":
                w = 0.55
            elif str(cls) == "low_priority":
                w = 0.2
            if i < len(proba):
                score += w * float(proba[i])
        return float(score)

    def rank_candidates(
        self,
        learner_id: str,
        current_concept_id: str,
        candidates: List[Dict[str, Any]],
        evidence: Dict[str, Any],
        dependency_output: Dict[str, Any],
    ) -> Dict[str, Any]:
        seen: set[str] = set()
        deduped: List[Dict[str, Any]] = []
        for raw in candidates:
            if not isinstance(raw, dict):
                continue
            cid = str(raw.get("concept_id", "")).strip()
            if not cid or cid in seen:
                continue
            seen.add(cid)
            deduped.append(raw)
        filt = self.filter_safe_candidates(learner_id, deduped, dependency_output)
        safe = filt["safe_candidates"]
        if not safe:
            return {
                **filt,
                "ranked": [],
                "best": None,
                "status": "no_safe_candidates",
            }
        scored = []
        ev = dict(evidence or {})
        ev.setdefault("recommended_next_concept", dependency_output.get("recommended_next_concept"))
        for cand in safe:
            row = evidence_and_candidate_to_row(ev, cand, current_concept_id=str(current_concept_id))
            X = pd.DataFrame([[row[c] for c in FEATURE_COLUMNS]], columns=FEATURE_COLUMNS)
            rs = self._ranking_score(X) if len(self._bundles) == len(MODEL_FILES) else 0.0
            scored.append({"candidate": cand, "rank_score": rs, "features": row})
        scored.sort(key=lambda x: x["rank_score"], reverse=True)
        return {**filt, "ranked": scored, "best": scored[0] if scored else None, "status": "success"}

    def recommend_next_node(
        self,
        learner_id: str,
        current_concept_id: str,
        evidence: Dict[str, Any],
        dependency_output: Dict[str, Any],
    ) -> Dict[str, Any]:
        if len(self._bundles) < len(MODEL_FILES):
            return {
                "status": "warning",
                "module": "LearnedAdaptivePathRanker",
                "model_used": False,
                "fallback_used": True,
                "recommended_action": "review_current",
                "recommended_node_type": "lesson",
                "recommended_concept_id": str(current_concept_id or ""),
                "rank_score_bucket": "low_priority",
                "confidence": 0.0,
                "safe_candidates_count": 0,
                "blocked_candidates_count": 0,
                "safety_violation": False,
                "top_features": [],
                "frontend_component": "AdaptivePathRecommendationCard",
                "limitations": ["Learned path ranker model artifact unavailable."],
            }
        unlocked = list(dependency_output.get("unlocked_concepts") or [])
        candidates: List[Dict[str, Any]] = []
        rec = dependency_output.get("recommended_next_concept")
        review_set = set(str(x) for x in (evidence.get("review_queue_concept_ids") or []))
        for cid in unlocked:
            cid = str(cid)
            candidates.append(
                {
                    "concept_id": cid,
                    "prerequisite_satisfied": True,
                    "is_review_due": cid in review_set,
                    "is_next_concept": rec is not None and str(rec) == cid,
                    "is_challenge": str(evidence.get("difficulty", "")).lower() == "hard",
                }
            )
        if current_concept_id:
            candidates.append(
                {
                    "concept_id": str(current_concept_id),
                    "prerequisite_satisfied": True,
                    "is_review_due": str(current_concept_id) in review_set,
                    "is_next_concept": False,
                    "is_challenge": False,
                }
            )
        ranked = self.rank_candidates(
            learner_id, current_concept_id, candidates, evidence, dependency_output
        )
        if ranked.get("status") != "success" or not ranked.get("best"):
            return self._empty_recommendation(
                ranked,
                current_concept_id,
                reason="no_safe_candidates",
            )
        best = ranked["best"]
        cand = best["candidate"]
        row = best["features"]
        X = pd.DataFrame([[row[c] for c in FEATURE_COLUMNS]], columns=FEATURE_COLUMNS)
        pa, c1 = self._predict_bundle("path_action", X)
        nt, c2 = self._predict_bundle("node_type", X)
        bk, c3 = self._predict_bundle("rank_score_bucket", X)
        pa = pa if pa in PATH_ACTION_LABELS else "next_unlocked_concept"
        nt = nt if nt in NODE_TYPE_LABELS else "practice"
        bk = bk if bk in RANK_BUCKET_LABELS else "medium_priority"
        conf = float(np.mean([c1, c2, c3])) if (c1 + c2 + c3) > 0 else 0.0
        top = sorted(row.items(), key=lambda kv: abs(kv[1]), reverse=True)[:6]
        return {
            "status": "success",
            "module": "LearnedAdaptivePathRanker",
            "model_used": True,
            "fallback_used": False,
            "recommended_action": pa,
            "recommended_node_type": nt,
            "recommended_concept_id": str(cand.get("concept_id", current_concept_id or "")),
            "rank_score_bucket": bk,
            "confidence": round(conf, 4),
            "safe_candidates_count": int(ranked.get("safe_candidates_count", 0)),
            "blocked_candidates_count": int(ranked.get("blocked_candidates_count", 0)),
            "safety_violation": bool(ranked.get("safety_violation")),
            "top_features": [k for k, _ in top],
            "frontend_component": "AdaptivePathRecommendationCard",
            "limitations": list(self._meta.get("limitations", []))[:8],
        }

    def _empty_recommendation(
        self,
        filt: Dict[str, Any],
        current_concept_id: str,
        *,
        reason: str,
    ) -> Dict[str, Any]:
        return {
            "status": "warning",
            "module": "LearnedAdaptivePathRanker",
            "model_used": True,
            "fallback_used": False,
            "recommended_action": "wait_locked_prerequisite"
            if reason == "no_safe_candidates"
            else "review_current",
            "recommended_node_type": "lesson",
            "recommended_concept_id": str(current_concept_id or ""),
            "rank_score_bucket": "low_priority",
            "confidence": 0.25,
            "safe_candidates_count": int(filt.get("safe_candidates_count", 0)),
            "blocked_candidates_count": int(filt.get("blocked_candidates_count", 0)),
            "safety_violation": bool(filt.get("safety_violation")),
            "top_features": [],
            "frontend_component": "AdaptivePathRecommendationCard",
            "limitations": [reason, "No safe candidate remained after prerequisite filter."],
        }

    def _fallback_payload(
        self,
        current_concept_id: str,
        dependency_output: Dict[str, Any],
        fallback_path: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        fb = fallback_path or {}
        sel = fb.get("selected_next_concept") or dependency_output.get("recommended_next_concept")
        strat = str(fb.get("recommended_strategy") or "practice").lower()
        node = "practice"
        if "revision" in strat:
            node = "revision"
        elif "remedial" in strat:
            node = "revision"
        elif "advanced" in strat:
            node = "challenge"
        action = "next_unlocked_concept" if sel else "review_current"
        if strat == "revision":
            action = "review_current"
        elif "remedial" in strat:
            action = "remediation_previous"
        elif "advanced" in strat:
            action = "challenge_current"
        elif not sel:
            action = "wait_locked_prerequisite"
        return {
            "status": "warning",
            "module": "LearnedAdaptivePathRanker",
            "model_used": False,
            "fallback_used": True,
            "recommended_action": action,
            "recommended_node_type": node,
            "recommended_concept_id": str(sel or current_concept_id or ""),
            "rank_score_bucket": "medium_priority",
            "confidence": 0.35,
            "safe_candidates_count": len(dependency_output.get("unlocked_concepts") or []),
            "blocked_candidates_count": len(dependency_output.get("blocked_concepts") or []),
            "safety_violation": False,
            "top_features": [],
            "frontend_component": "AdaptivePathRecommendationCard",
            "limitations": ["Learned path ranker artifact unavailable or low confidence; AdaptivePathSelector output used."],
        }

    def predict_with_fallback(
        self,
        learner_id: str,
        current_concept_id: str,
        dependency_output: Dict[str, Any],
        evidence: Dict[str, Any],
        fallback_path: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if len(self._bundles) < len(MODEL_FILES):
            return self._fallback_payload(str(current_concept_id), dependency_output, fallback_path)
        pred = self.recommend_next_node(learner_id, current_concept_id, evidence, dependency_output)
        if pred.get("status") != "success":
            out = self._fallback_payload(str(current_concept_id), dependency_output, fallback_path)
            out["limitations"] = list(
                dict.fromkeys((pred.get("limitations") or []) + (out.get("limitations") or []))
            )
            return out
        low = pred.get("confidence", 0.0) < self.confidence_threshold
        if low:
            out = self._fallback_payload(str(current_concept_id), dependency_output, fallback_path)
            out["fallback_used"] = True
            out["model_used"] = False
            out["status"] = "warning"
            lims = list(dict.fromkeys(["Learned path confidence below threshold; merged AdaptivePathSelector recommendation."] + (out.get("limitations") or [])))
            out["limitations"] = lims
            out["safe_candidates_count"] = pred.get("safe_candidates_count", out.get("safe_candidates_count"))
            out["blocked_candidates_count"] = pred.get("blocked_candidates_count", out.get("blocked_candidates_count"))
            return out
        return pred
