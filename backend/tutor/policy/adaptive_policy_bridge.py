"""
AdaptivePolicyBridge

Purpose:
- Safely connect final policy/RL output with AdaptivePathSelector output.
- Does NOT blindly override policy/RL.
- Produces a comparison and safe recommendation.
- Later this bridge can become the input layer for improved RL policy.

Current role:
    policy_output = final decision
    adaptive_path_output = smarter path evidence
    bridge_output = agreement/disagreement + safe suggested action
"""

from __future__ import annotations

from typing import Dict, Any, Optional


class AdaptivePolicyBridge:
    def __init__(self) -> None:
        self.override_score_threshold = 0.65
        self.low_view_reward_threshold = 0.50
        self.low_evaluation_threshold = 0.60

    def reconcile(
        self,
        policy_output: Dict[str, Any],
        adaptive_path_output: Dict[str, Any],
        view_performance_output: Optional[Dict[str, Any]] = None,
        evaluation_output: Optional[Dict[str, Any]] = None,
        multi_evidence_output: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        policy_data = policy_output.get("data", {}) if isinstance(policy_output, dict) else {}

        policy_concept = str(policy_data.get("next_concept_id", ""))
        policy_difficulty = policy_data.get("difficulty", "medium")
        policy_strategy = policy_data.get("strategy", "practice")
        policy_decision_type = policy_data.get("decision_type", "")

        adaptive_status = adaptive_path_output.get("status") if isinstance(adaptive_path_output, dict) else "missing"

        if adaptive_status != "success":
            return {
                "status": "fallback_policy_only",
                "module": "AdaptivePolicyBridge",
                "final_recommendation": {
                    "next_concept_id": policy_concept,
                    "difficulty": policy_difficulty,
                    "strategy": policy_strategy,
                    "source": "policy_only",
                },
                "agreement": False,
                "override_allowed": False,
                "reason": "Adaptive path output is not successful, so policy output remains final.",
                "policy_summary": {
                    "concept": policy_concept,
                    "difficulty": policy_difficulty,
                    "strategy": policy_strategy,
                    "decision_type": policy_decision_type,
                },
                "adaptive_summary": {
                    "status": adaptive_status,
                },
            }

        adaptive_concept = str(adaptive_path_output.get("selected_next_concept", ""))
        adaptive_difficulty = adaptive_path_output.get("recommended_difficulty", "medium")
        adaptive_strategy = adaptive_path_output.get("recommended_strategy", "practice")
        adaptive_score = self._safe_float(adaptive_path_output.get("selected_score"), 0.0)

        agreement = policy_concept == adaptive_concept

        view_reward = self._extract_view_reward(view_performance_output or {})
        evaluation_score = self._extract_evaluation_score(evaluation_output or {})
        final_action = ""
        if isinstance(multi_evidence_output, dict):
            final_action = str(multi_evidence_output.get("final_action", ""))

        evidence_flags = {
            "low_view_reward": view_reward < self.low_view_reward_threshold,
            "low_evaluation_score": evaluation_score < self.low_evaluation_threshold,
            "adaptive_score_strong": adaptive_score >= self.override_score_threshold,
            "policy_is_rl": "rl" in str(policy_decision_type).lower(),
            "final_action_review": "review" in final_action.lower() or "reinforce" in final_action.lower(),
        }

        override_allowed = self._decide_override_allowed(
            agreement=agreement,
            evidence_flags=evidence_flags,
        )

        if agreement:
            final_recommendation = {
                "next_concept_id": policy_concept,
                "difficulty": policy_difficulty or adaptive_difficulty,
                "strategy": policy_strategy or adaptive_strategy,
                "source": "policy_and_adaptive_path_agree",
            }
            reason = (
                f"Policy and adaptive path agree on concept {policy_concept}. "
                f"Keeping policy output as final."
            )

        elif override_allowed:
            final_recommendation = {
                "next_concept_id": adaptive_concept,
                "difficulty": adaptive_difficulty,
                "strategy": adaptive_strategy,
                "source": "adaptive_path_suggested_override",
            }
            reason = (
                f"Adaptive path suggests concept {adaptive_concept} with strong evidence. "
                f"Override is marked as allowed, but integration can still keep policy final until review."
            )

        else:
            final_recommendation = {
                "next_concept_id": policy_concept,
                "difficulty": policy_difficulty,
                "strategy": policy_strategy,
                "source": "policy_kept_adaptive_logged",
            }
            reason = (
                f"Policy selected concept {policy_concept}, while adaptive path suggested {adaptive_concept}. "
                f"Keeping policy final and logging adaptive path as evidence."
            )

        return {
            "status": "success",
            "module": "AdaptivePolicyBridge",
            "agreement": agreement,
            "override_allowed": override_allowed,
            "final_recommendation": final_recommendation,
            "reason": reason,
            "policy_summary": {
                "concept": policy_concept,
                "difficulty": policy_difficulty,
                "strategy": policy_strategy,
                "decision_type": policy_decision_type,
            },
            "adaptive_summary": {
                "concept": adaptive_concept,
                "difficulty": adaptive_difficulty,
                "strategy": adaptive_strategy,
                "score": adaptive_score,
                "reason": adaptive_path_output.get("selected_reason", ""),
            },
            "evidence_flags": evidence_flags,
            "view_reward": view_reward,
            "evaluation_score": evaluation_score,
            "final_action": final_action,
        }

    def _decide_override_allowed(
        self,
        agreement: bool,
        evidence_flags: Dict[str, bool],
    ) -> bool:
        if agreement:
            return False

        # Safe rule:
        # adaptive path can be considered only when it is strong
        # and the learner still needs review/support.
        if (
            evidence_flags.get("adaptive_score_strong")
            and evidence_flags.get("low_evaluation_score")
            and evidence_flags.get("low_view_reward")
        ):
            return True

        if (
            evidence_flags.get("adaptive_score_strong")
            and evidence_flags.get("final_action_review")
            and evidence_flags.get("low_view_reward")
        ):
            return True

        return False

    def _extract_view_reward(self, view_performance_output: Dict[str, Any]) -> float:
        try:
            logged = view_performance_output.get("logged", {})
            return float(logged.get("reward", view_performance_output.get("reward", 0.5)))
        except Exception:
            return 0.5

    def _extract_evaluation_score(self, evaluation_output: Dict[str, Any]) -> float:
        try:
            return float(
                evaluation_output.get("overall_score", 0.5)
                or evaluation_output.get("score", 0.5)
                or 0.5
            )
        except Exception:
            return 0.5

    def _safe_float(self, value: Any, default: float) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default