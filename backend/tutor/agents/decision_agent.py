from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from tutor.system.multi_evidence_fusion import fuse_evidence
from tutor.system.policy_model_inference import PolicyModel
from tutor.RL.dqn.dqn_policy import DQNPolicy
from tutor.policy.rl_safe_action_mask import apply_rl_safe_action_mask


class DecisionAgent:
    def __init__(self, conn: Optional[sqlite3.Connection] = None) -> None:
        self.conn = conn

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _get_next_concept_from_db(self, current_concept_id: str) -> Optional[str]:
        if self.conn is None:
            return None

        try:
            rows = self.conn.execute(
                """
                SELECT system_concept_id
                FROM concept_id_map
                ORDER BY CAST(system_concept_id AS INTEGER)
                """
            ).fetchall()

            ids = [str(r[0]) for r in rows if r[0] is not None]

            if current_concept_id in ids:
                idx = ids.index(current_concept_id)
                if idx + 1 < len(ids):
                    return ids[idx + 1]

            return None

        except Exception:
            return None

    def build_rl_state(self, multi_evidence_output: Dict[str, Any]) -> Dict[str, Any]:
        evidence = multi_evidence_output.get("evidence_summary", {})

        return {
            "mastery_score": evidence.get("mastery_score", 0.0),
            "behavior_score": evidence.get("behavior_score", 0.0),
            "review_due": evidence.get("review_due", False),
            "evaluation_score": evidence.get("evaluation_score", 0.0),
            "learning_signal": evidence.get("learning_signal", "weak"),
        }

    def run(
        self,
        current_policy_output: Dict[str, Any],
        knowledge_state: Dict[str, Any],
        behaviour_state: Dict[str, Any],
        forgetting_state: Dict[str, Any],
        evaluation_output: Dict[str, Any],
        learning_signal: str,
    ) -> Dict[str, Any]:

        multi_evidence_output = fuse_evidence(
            knowledge_state=knowledge_state,
            behaviour_state=behaviour_state,
            forgetting_state=forgetting_state,
            evaluation_output={
                "score": evaluation_output.get("overall_score", 0.0),
                "quality_label": evaluation_output.get("verdict", ""),
                "feedback_summary": evaluation_output.get("feedback_summary", ""),
            },
            learning_signal=learning_signal,
        )

        final_policy_output = json.loads(json.dumps(current_policy_output))
        final_policy_data = final_policy_output.get("data", {})
        current_concept_id = str(final_policy_data.get("next_concept_id"))

        fusion_action = multi_evidence_output.get("final_action", "")

        if fusion_action in {"progress_with_review_later", "promote_next"}:
            next_concept = self._get_next_concept_from_db(current_concept_id)
            if next_concept:
                final_policy_data["next_concept_id"] = next_concept
                final_policy_data["decision_type"] = "overridden_by_fusion_progress"

        elif fusion_action == "light_review":
            final_policy_data["decision_type"] = "light_review_adjustment"

        final_policy_data["strategy"] = multi_evidence_output.get(
            "recommended_strategy",
            final_policy_data.get("strategy"),
        )

        final_policy_data["difficulty"] = multi_evidence_output.get(
            "recommended_difficulty",
            final_policy_data.get("difficulty"),
        )

        policy_model = PolicyModel()

        if policy_model.is_available():
            try:
                evidence = multi_evidence_output.get("evidence_summary", {})

                policy_features = {
                    "mastery_score": evidence.get("mastery_score"),
                    "behavior_label": evidence.get("behavior_label"),
                    "behavior_score": evidence.get("behavior_score"),
                    "review_due": evidence.get("review_due"),
                    "evaluation_score": evidence.get("evaluation_score"),
                    "learning_signal": evidence.get("learning_signal"),
                    "final_action": multi_evidence_output.get("final_action"),
                    "recommended_strategy": multi_evidence_output.get("recommended_strategy"),
                    "recommended_difficulty": multi_evidence_output.get("recommended_difficulty"),
                }

                predicted_next = policy_model.predict_next_concept(policy_features)

                final_policy_data["next_concept_id"] = predicted_next
                final_policy_data["strategy"] = multi_evidence_output.get(
                    "recommended_strategy",
                    final_policy_data.get("strategy"),
                )
                final_policy_data["difficulty"] = multi_evidence_output.get(
                    "recommended_difficulty",
                    final_policy_data.get("difficulty"),
                )
                final_policy_data["decision_type"] = "predicted_by_policy_model"

            except Exception:
                pass

        dqn_output = None
        safe_policy_packet = {
            "label": "Policy/RL safe decision support",
            "policy_source": "safe_rule_fallback",
            "raw_policy_recommendation": {
                "next_concept_id": final_policy_data.get("next_concept_id"),
                "strategy": final_policy_data.get("strategy"),
                "difficulty": final_policy_data.get("difficulty"),
                "decision_type": final_policy_data.get("decision_type"),
            },
            "safe_mask_applied": False,
            "final_safe_action": f"{final_policy_data.get('strategy', 'practice')}_{final_policy_data.get('difficulty', 'medium')}",
            "reason": "No RL runtime recommendation was available; safe rule policy remained final.",
        }

        try:
            dqn_policy = DQNPolicy()

            if dqn_policy.is_available():
                rl_state = self.build_rl_state(multi_evidence_output)
                dqn_output = dqn_policy.predict(rl_state)

                if dqn_output.get("status") == "success":
                    mask_state = {
                        **rl_state,
                        "behaviour_risk": multi_evidence_output.get("evidence_summary", {}).get("behaviour_risk"),
                        "fused_score": multi_evidence_output.get("evidence_summary", {}).get("evaluation_score"),
                        "fused_label": evaluation_output.get("verdict"),
                        "weakest_skill": evaluation_output.get("weakest_skill"),
                    }
                    safe_mask = apply_rl_safe_action_mask(mask_state, dqn_output)
                    final_policy_data["strategy"] = safe_mask.get(
                        "strategy",
                        dqn_output.get("strategy", final_policy_data.get("strategy")),
                    )
                    final_policy_data["difficulty"] = safe_mask.get(
                        "difficulty",
                        dqn_output.get("difficulty", final_policy_data.get("difficulty")),
                    )
                    final_policy_data["decision_type"] = "dqn_rl_policy_safe_support"
                    safe_policy_packet = {
                        "label": "Policy/RL safe decision support",
                        "policy_source": "rl_runtime",
                        "raw_policy_recommendation": dqn_output,
                        "safe_mask_applied": True,
                        "final_safe_action": safe_mask.get("masked_action"),
                        "reason": safe_mask.get("reason"),
                        "safe_mask": safe_mask,
                    }

        except Exception as e:
            dqn_output = {
                "status": "error",
                "reason": str(e),
            }
            safe_policy_packet["policy_source"] = "safe_rule_fallback"
            safe_policy_packet["reason"] = f"RL runtime unavailable; safe rule policy remained final. Error: {e}"

        final_policy_data["policy_source"] = safe_policy_packet.get("policy_source")
        final_policy_data["raw_policy_recommendation"] = safe_policy_packet.get("raw_policy_recommendation")
        final_policy_data["safe_mask_applied"] = safe_policy_packet.get("safe_mask_applied")
        final_policy_data["final_safe_action"] = safe_policy_packet.get("final_safe_action")
        final_policy_data["policy_reason"] = safe_policy_packet.get("reason")


        if learning_signal == "weak":
            adapted_decision = {"strategy": "remedial", "difficulty": "easy"}
        elif learning_signal == "partial":
            adapted_decision = {"strategy": "practice", "difficulty": "medium"}
        else:
            adapted_decision = {"strategy": "advanced", "difficulty": "hard"}

        # 🔥 NEW — Explanation Mode Decision (CRITICAL)

        mastery = multi_evidence_output.get("evidence_summary", {}).get("mastery_score", 0.0)
        confidence = multi_evidence_output.get("evidence_summary", {}).get("confidence_score", 0.5)
        behavior = multi_evidence_output.get("evidence_summary", {}).get("behavior_label", "stable")

        if mastery < 0.4:
            explanation_mode = "simple"

        elif behavior in ["confused", "struggling"] or confidence < 0.4:
            explanation_mode = "step_by_step"

        elif 0.4 <= mastery < 0.75:
            explanation_mode = "code"

        elif mastery >= 0.75 and confidence >= 0.7:
            explanation_mode = "challenge"

        else:
            explanation_mode = "analogy"

        final_policy_data["explanation_mode"] = explanation_mode

        return {
            "status": "success",
            "agent": "DecisionAgent",
            "multi_evidence_output": multi_evidence_output,
            "policy_output": final_policy_output,
            "adapted_decision": adapted_decision,
            "dqn_output": dqn_output,
            "safe_policy_output": safe_policy_packet,
            "explanation_mode": final_policy_data.get("explanation_mode")
        }
