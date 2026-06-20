"""
AdaptivePathSelector

Purpose:
- Upgrade adaptive path from simple threshold/lowest-mastery selection
  to multi-factor concept scoring.
- Uses existing dependency module output safely.
- Does not replace run_dependency_module_final yet.

Inputs:
- dependency_output from run_dependency_module_final
- mastery / behaviour / forgetting / evaluation / view performance evidence

Output:
- ranked candidate concepts
- selected next concept
- path reasoning
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional


class AdaptivePathSelector:
    def __init__(self) -> None:
        self.default_weights = {
            "low_mastery": 0.30,
            "review_priority": 0.25,
            "evaluation_need": 0.20,
            "behaviour_risk": 0.15,
            "view_reward_need": 0.10,
        }

    def select_next_path(
        self,
        dependency_output: Dict[str, Any],
        mastery: Optional[Dict[str, float]] = None,
        forgetting_priority: Optional[Dict[str, float]] = None,
        evaluation_evidence: Optional[Dict[str, Any]] = None,
        behaviour_evidence: Optional[Dict[str, Any]] = None,
        view_performance: Optional[Dict[str, Any]] = None,
        current_concept_id: Optional[str] = None,
        weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        mastery = mastery or {}
        forgetting_priority = forgetting_priority or {}
        evaluation_evidence = evaluation_evidence or {}
        behaviour_evidence = behaviour_evidence or {}
        view_performance = view_performance or {}
        weights = weights or self.default_weights

        unlocked = dependency_output.get("unlocked_concepts", []) or []
        blocked = dependency_output.get("blocked_concepts", []) or []

        if current_concept_id:
            candidates = [cid for cid in unlocked if str(cid) != str(current_concept_id)]
            if not candidates:
                candidates = unlocked[:]
        else:
            candidates = unlocked[:]

        if not candidates:
            return {
                "status": "no_candidates",
                "module": "AdaptivePathSelector",
                "selected_next_concept": None,
                "ranked_candidates": [],
                "reason": "No unlocked candidate concepts were available.",
                "blocked_concepts": blocked,
            }

        ranked = []

        for concept_id in candidates:
            concept_id = str(concept_id)

            m = self._safe_float(mastery.get(concept_id), 0.0)
            review_priority = self._safe_float(forgetting_priority.get(concept_id), 0.0)

            evaluation_need = self._evaluation_need(evaluation_evidence)
            behaviour_risk = self._behaviour_risk(behaviour_evidence)
            view_reward_need = self._view_reward_need(view_performance)

            low_mastery_score = 1.0 - m

            score = (
                weights.get("low_mastery", 0.30) * low_mastery_score
                + weights.get("review_priority", 0.25) * review_priority
                + weights.get("evaluation_need", 0.20) * evaluation_need
                + weights.get("behaviour_risk", 0.15) * behaviour_risk
                + weights.get("view_reward_need", 0.10) * view_reward_need
            )

            difficulty = self._recommend_difficulty(
                mastery_score=m,
                behaviour_risk=behaviour_risk,
                evaluation_need=evaluation_need,
            )

            strategy = self._recommend_strategy(
                mastery_score=m,
                review_priority=review_priority,
                evaluation_need=evaluation_need,
                behaviour_risk=behaviour_risk,
            )

            ranked.append(
                {
                    "concept_id": concept_id,
                    "path_score": round(score, 4),
                    "features": {
                        "mastery": round(m, 4),
                        "low_mastery_score": round(low_mastery_score, 4),
                        "review_priority": round(review_priority, 4),
                        "evaluation_need": round(evaluation_need, 4),
                        "behaviour_risk": round(behaviour_risk, 4),
                        "view_reward_need": round(view_reward_need, 4),
                    },
                    "recommended_difficulty": difficulty,
                    "recommended_strategy": strategy,
                    "reason": self._build_reason(
                        concept_id=concept_id,
                        mastery_score=m,
                        review_priority=review_priority,
                        evaluation_need=evaluation_need,
                        behaviour_risk=behaviour_risk,
                        view_reward_need=view_reward_need,
                    ),
                }
            )

        ranked = sorted(
            ranked,
            key=lambda item: item["path_score"],
            reverse=True,
        )

        selected = ranked[0]

        return {
            "status": "success",
            "module": "AdaptivePathSelector",
            "selected_next_concept": selected["concept_id"],
            "recommended_difficulty": selected["recommended_difficulty"],
            "recommended_strategy": selected["recommended_strategy"],
            "selected_score": selected["path_score"],
            "selected_reason": selected["reason"],
            "ranked_candidates": ranked,
            "blocked_concepts": blocked,
            "weights_used": weights,
        }

    def _evaluation_need(self, evaluation_evidence: Dict[str, Any]) -> float:
        score = self._safe_float(
            evaluation_evidence.get("overall_score")
            or evaluation_evidence.get("evaluation_score")
            or evaluation_evidence.get("score"),
            0.5,
        )

        weak_count = self._safe_float(
            evaluation_evidence.get("weak_item_count"),
            0.0,
        )

        item_count = self._safe_float(
            evaluation_evidence.get("item_count"),
            5.0,
        )

        score_need = 1.0 - score

        if item_count > 0:
            weak_ratio = min(1.0, weak_count / item_count)
        else:
            weak_ratio = 0.0

        return self._clamp(0.7 * score_need + 0.3 * weak_ratio)

    def _behaviour_risk(self, behaviour_evidence: Dict[str, Any]) -> float:
        label = str(
            behaviour_evidence.get("behavior_label")
            or behaviour_evidence.get("behaviour_label")
            or ""
        ).lower()

        behavior_score = self._safe_float(
            behaviour_evidence.get("behavior_score")
            or behaviour_evidence.get("behaviour_score"),
            0.5,
        )

        wrong_rate = self._safe_float(behaviour_evidence.get("wrong_rate"), 0.0)
        slow_rate = self._safe_float(behaviour_evidence.get("slow_rate"), 0.0)
        low_confidence_rate = self._safe_float(
            behaviour_evidence.get("low_confidence_rate"),
            0.0,
        )
        hint_rate = self._safe_float(behaviour_evidence.get("hint_rate"), 0.0)

        label_risk = 0.0
        if "struggling" in label:
            label_risk = 0.8
        elif "confused" in label:
            label_risk = 0.7
        elif "unstable" in label:
            label_risk = 0.6
        elif "stable" in label:
            label_risk = 0.25

        score_risk = 1.0 - behavior_score

        risk = (
            0.30 * label_risk
            + 0.25 * score_risk
            + 0.20 * wrong_rate
            + 0.10 * slow_rate
            + 0.10 * low_confidence_rate
            + 0.05 * hint_rate
        )

        return self._clamp(risk)

    def _view_reward_need(self, view_performance: Dict[str, Any]) -> float:
        if not view_performance:
            return 0.5

        logged = view_performance.get("logged", {})
        reward = logged.get("reward")

        if reward is None:
            reward = view_performance.get("reward")

        reward = self._safe_float(reward, 0.5)

        return self._clamp(1.0 - reward)

    def _recommend_difficulty(
        self,
        mastery_score: float,
        behaviour_risk: float,
        evaluation_need: float,
    ) -> str:
        if mastery_score < 0.45 or behaviour_risk > 0.65 or evaluation_need > 0.65:
            return "easy"

        if mastery_score > 0.78 and behaviour_risk < 0.35 and evaluation_need < 0.35:
            return "hard"

        return "medium"

    def _recommend_strategy(
        self,
        mastery_score: float,
        review_priority: float,
        evaluation_need: float,
        behaviour_risk: float,
    ) -> str:
        if review_priority > 0.55:
            return "revision"

        if mastery_score < 0.45 or behaviour_risk > 0.60:
            return "remedial"

        if evaluation_need > 0.55:
            return "practice"

        if mastery_score > 0.78:
            return "advanced"

        return "practice"

    def _build_reason(
        self,
        concept_id: str,
        mastery_score: float,
        review_priority: float,
        evaluation_need: float,
        behaviour_risk: float,
        view_reward_need: float,
    ) -> str:
        reasons = []

        if mastery_score < 0.5:
            reasons.append("mastery is low")

        if review_priority > 0.4:
            reasons.append("forgetting/review priority is high")

        if evaluation_need > 0.5:
            reasons.append("recent evaluation shows weakness")

        if behaviour_risk > 0.5:
            reasons.append("behaviour risk is elevated")

        if view_reward_need > 0.5:
            reasons.append("previous teaching view reward can improve")

        if not reasons:
            reasons.append("concept is unlocked and suitable for continued practice")

        return f"Selected {concept_id} because " + ", ".join(reasons) + "."

    def _safe_float(self, value: Any, default: float) -> float:
        if value is None:
            return default

        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, float(value)))