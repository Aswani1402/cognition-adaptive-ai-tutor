from __future__ import annotations

from typing import Any


CORE_MODULES = [
    "KT",
    "Behaviour",
    "Evaluation/Semantic",
    "Mistake analysis",
    "Teaching strategy",
    "RAG",
    "RL/policy",
    "Revision",
    "Doubt",
    "Reward",
    "Adaptive path",
]


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _clamp(value: Any) -> float:
    return max(0.0, min(1.0, _safe_float(value, 0.0)))


def _nested_get(data: dict[str, Any], *path: str, default: Any = None) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return default if current is None else current


def _first_present(*values: Any, default: Any = None) -> Any:
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return default


class XAIDashboardBuilder:
    def build(
        self,
        integrated_output: dict[str, Any],
        learner_id: str | None = None,
        concept_id: str | None = None,
        latest_report_summaries: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        integrated_output = _as_dict(integrated_output)
        evidence = self._extract_evidence(integrated_output, learner_id, concept_id)
        factor_contributions = self._factor_contributions(evidence)
        top_factors = sorted(
            [
                {"factor": name, "contribution": value, "evidence_value": self._factor_evidence_value(name, evidence)}
                for name, value in factor_contributions.items()
            ],
            key=lambda item: item["contribution"],
            reverse=True,
        )
        evidence_coverage = self._evidence_coverage(evidence, latest_report_summaries or {})
        counterfactuals = self._counterfactuals(evidence)
        cards = self._cards(evidence, top_factors, counterfactuals, evidence_coverage)
        explanation_quality = self._quality(cards, top_factors, counterfactuals, evidence_coverage)

        return {
            "status": "success",
            "module": "XAIDashboardBuilder",
            "learner_id": evidence.get("learner_id"),
            "decision_summary": {
                "concept_id": evidence.get("concept_id"),
                "concept_name": evidence.get("concept_name"),
                "selected_teaching_view": evidence.get("selected_teaching_view"),
                "selected_difficulty": evidence.get("selected_difficulty"),
                "selected_strategy": evidence.get("selected_strategy"),
                "next_activity": evidence.get("next_activity"),
                "progression_action": evidence.get("progression_action"),
            },
            "cards": cards,
            "top_factors": top_factors[:6],
            "factor_contributions": factor_contributions,
            "counterfactuals": counterfactuals,
            "evidence_coverage": evidence_coverage,
            "explanation_quality": explanation_quality,
        }

    def _extract_evidence(
        self,
        output: dict[str, Any],
        learner_id: str | None,
        concept_id: str | None,
    ) -> dict[str, Any]:
        demo = _as_dict(output.get("demo_summary"))
        kt_data = _as_dict(_nested_get(output, "knowledge_state", "data", "data", default={}))
        behaviour_wrap = _as_dict(_nested_get(output, "behaviour_state", "data", default={}))
        behaviour_data = _as_dict(behaviour_wrap.get("data") or behaviour_wrap)
        forgetting_data = _as_dict(_nested_get(output, "forgetting_state", "data", default={}))
        evaluation_fusion = _as_dict(output.get("evaluation_fusion_output"))
        mistake_analysis = _as_dict(output.get("mistake_analysis_output"))
        strategy = _as_dict(output.get("evidence_aware_teaching_strategy_output"))
        current_content = _as_dict(output.get("current_teaching_content"))
        progression = _as_dict(output.get("progression_reward_output"))
        progression_result = _as_dict(progression.get("progression_result"))
        reward_state = _as_dict(progression.get("reward_state"))
        reward_persistence = _as_dict(output.get("reward_persistence_output"))
        adaptive_path = _as_dict(output.get("adaptive_path_validation_output") or output.get("adaptive_path_output"))
        policy = _as_dict(output.get("policy_output"))
        rl_log = _as_dict(output.get("rl_log_output"))
        cognitutor = _as_dict(output.get("cognitutor_lm_output"))
        doubt = _as_dict(cognitutor.get("classifier_output") or output.get("doubt_classifier_output"))

        retrieved_chunks = _as_list(current_content.get("retrieved_chunks"))
        sections = sorted(
            {
                str(chunk.get("section"))
                for chunk in retrieved_chunks
                if isinstance(chunk, dict) and chunk.get("section")
            }
        )
        rag_score = self._rag_grounding_score(current_content, retrieved_chunks)
        review_priority = _as_dict(forgetting_data.get("review_priority"))
        review_queue = _as_list(forgetting_data.get("review_queue"))
        high_severity = _safe_float(
            _first_present(
                demo.get("high_severity_mistake_count"),
                mistake_analysis.get("high_severity_count"),
                evaluation_fusion.get("high_severity_mistake_count"),
                default=0.0,
            )
        )
        behaviour_risk = _clamp(
            _first_present(
                behaviour_data.get("behavior_risk"),
                behaviour_data.get("behaviour_risk"),
                1.0 - _safe_float(behaviour_data.get("behavior_score"), 0.5),
                default=0.0,
            )
        )

        return {
            "learner_id": learner_id or output.get("learner_id"),
            "concept_id": concept_id or demo.get("final_concept") or current_content.get("concept_id"),
            "concept_name": demo.get("final_concept_name") or current_content.get("concept_name") or current_content.get("topic"),
            "mastery_score": _clamp(_first_present(kt_data.get("predicted_mastery_last"), kt_data.get("mastery_score"), default=0.5)),
            "kt_source": kt_data.get("source") or kt_data.get("model_source") or "knowledge_state",
            "behaviour_label": _first_present(behaviour_data.get("behavior_label"), behaviour_data.get("behaviour_label"), default="unknown"),
            "behaviour_risk": behaviour_risk,
            "behaviour_confidence": _clamp(_first_present(behaviour_data.get("behavior_confidence"), behaviour_data.get("confidence"), default=0.5)),
            "fused_score": _clamp(_first_present(demo.get("fused_score"), evaluation_fusion.get("fused_score"), default=demo.get("evaluation_score", 0.5))),
            "fused_label": _first_present(demo.get("fused_label"), evaluation_fusion.get("fused_label"), default="unknown"),
            "weakest_skill": _first_present(demo.get("weakest_skill"), _nested_get(evaluation_fusion, "weakest_skill_signal", "weakest_skill"), default="unknown"),
            "dominant_mistake_type": _first_present(demo.get("dominant_mistake_type"), mistake_analysis.get("dominant_mistake_type"), evaluation_fusion.get("dominant_mistake_type"), default="unknown"),
            "mistake_type_counts": _as_dict(_first_present(demo.get("mistake_type_counts"), mistake_analysis.get("mistake_type_counts"), default={})),
            "high_severity_mistake_count": high_severity,
            "weak_assessment_types": _as_list(_first_present(_nested_get(output, "structured_evaluation_output", "evaluation", "weak_assessment_types"), output.get("rubric_evaluation_output", {}).get("weak_assessment_types"), default=[])),
            "selected_teaching_view": _first_present(strategy.get("teaching_view"), demo.get("teaching_view"), current_content.get("recommended_view"), default="definition_view"),
            "selected_difficulty": _first_present(strategy.get("assessment_difficulty"), demo.get("final_difficulty"), current_content.get("difficulty"), default="medium"),
            "selected_strategy": _first_present(demo.get("final_strategy"), strategy.get("strategy"), _nested_get(policy, "data", "strategy"), default="practice"),
            "assessment_types": _as_list(_first_present(strategy.get("assessment_types"), demo.get("assessment_types"), default=[])),
            "next_activity": _first_present(strategy.get("next_activity"), demo.get("next_activity"), default="targeted_practice"),
            "progression_action": _first_present(demo.get("progression_action"), progression_result.get("progression_action"), default="continue_practice"),
            "promotion_confidence": _clamp(_first_present(demo.get("promotion_confidence"), progression_result.get("promotion_confidence"), default=0.0)),
            "promotion_allowed": bool(_first_present(demo.get("promotion_allowed"), progression_result.get("promotion_allowed"), default=False)),
            "level_up_allowed": bool(_first_present(demo.get("level_up_allowed"), progression_result.get("level_up_allowed"), default=False)),
            "review_due_concepts": review_queue,
            "revision_priority": _clamp(max([_safe_float(value) for value in review_priority.values()] or [1.0 if review_queue else 0.0])),
            "review_priority": review_priority,
            "recommended_revision_views": _as_list(_first_present(strategy.get("fallback_views"), demo.get("fallback_views"), default=["revision_summary_view"])),
            "rag_grounding_score": rag_score,
            "rag_source_sections": sections,
            "rag_safe_to_generate": rag_score >= 0.55,
            "unsupported_terms": _as_list(current_content.get("unsupported_terms")),
            "doubt_intent": doubt.get("intent"),
            "doubt_confidence": doubt.get("confidence"),
            "doubt_fallback_used": doubt.get("fallback_used"),
            "doubt_recommended_route": doubt.get("recommended_route"),
            "policy_safety_status": _first_present(rl_log.get("status"), policy.get("status"), default="available"),
            "adaptive_path_valid": _first_present(adaptive_path.get("is_valid"), adaptive_path.get("valid"), adaptive_path.get("status") == "success", default=None),
            "adaptive_path_confidence": _clamp(_first_present(adaptive_path.get("confidence"), adaptive_path.get("selected_score"), default=0.5)),
            "reward_xp_awarded": _first_present(demo.get("reward_xp_awarded"), reward_state.get("xp_awarded"), reward_persistence.get("xp_awarded"), default=0),
            "view_reward": _clamp(_first_present(demo.get("view_reward"), _nested_get(output, "view_performance_output", "logged", "reward"), default=0.5)),
        }

    def _rag_grounding_score(self, current_content: dict[str, Any], chunks: list[Any]) -> float:
        direct = current_content.get("rag_grounding_score") or current_content.get("grounding_score")
        if direct is not None:
            return _clamp(direct)
        chunk_count = _safe_float(current_content.get("chunk_count"), len(chunks))
        section_count = len({chunk.get("section") for chunk in chunks if isinstance(chunk, dict) and chunk.get("section")})
        return _clamp(0.15 * min(chunk_count, 5.0) + 0.25 * min(section_count, 1.0))

    def _factor_contributions(self, evidence: dict[str, Any]) -> dict[str, float]:
        high_severity = min(_safe_float(evidence.get("high_severity_mistake_count")), 5.0) / 5.0
        raw = {
            "evaluation_need": _clamp(1.0 - _safe_float(evidence.get("fused_score"), 0.5)) * 1.25,
            "mastery_need": _clamp(1.0 - _safe_float(evidence.get("mastery_score"), 0.5)) * 1.05,
            "behaviour_pressure": _clamp(evidence.get("behaviour_risk")) * 0.95,
            "revision_pressure": _clamp(evidence.get("revision_priority")) * 0.90,
            "promotion_block": _clamp(1.0 - _safe_float(evidence.get("promotion_confidence"), 0.5)) * 1.00,
            "rag_risk": _clamp(1.0 - _safe_float(evidence.get("rag_grounding_score"), 0.5)) * 0.65,
            "mistake_pressure": _clamp(high_severity) * 0.85,
            "view_reward_need": _clamp(1.0 - _safe_float(evidence.get("view_reward"), 0.5)) * 0.55,
            "adaptive_path_uncertainty": _clamp(1.0 - _safe_float(evidence.get("adaptive_path_confidence"), 0.5)) * 0.45,
        }
        total = sum(max(0.0, value) for value in raw.values()) or 1.0
        return {name: round(max(0.0, value) / total, 6) for name, value in raw.items()}

    def _factor_evidence_value(self, factor_name: str, evidence: dict[str, Any]) -> Any:
        source_map = {
            "evaluation_need": "fused_score",
            "mastery_need": "mastery_score",
            "behaviour_pressure": "behaviour_risk",
            "revision_pressure": "revision_priority",
            "promotion_block": "promotion_confidence",
            "rag_risk": "rag_grounding_score",
            "mistake_pressure": "high_severity_mistake_count",
            "view_reward_need": "view_reward",
            "adaptive_path_uncertainty": "adaptive_path_confidence",
        }
        return evidence.get(source_map.get(factor_name, factor_name))

    def _evidence_coverage(self, evidence: dict[str, Any], summaries: dict[str, Any]) -> dict[str, Any]:
        coverage = {
            "KT": evidence.get("mastery_score") is not None,
            "Behaviour": evidence.get("behaviour_risk") is not None,
            "Evaluation/Semantic": evidence.get("fused_score") is not None,
            "Mistake analysis": bool(evidence.get("mistake_type_counts") or evidence.get("dominant_mistake_type") != "unknown"),
            "Teaching strategy": bool(evidence.get("selected_teaching_view")),
            "RAG": bool(evidence.get("rag_source_sections") or evidence.get("rag_grounding_score") > 0),
            "RL/policy": bool(evidence.get("policy_safety_status")),
            "Revision": bool(evidence.get("review_due_concepts") or evidence.get("revision_priority") > 0),
            "Doubt": bool(evidence.get("doubt_intent") or summaries.get("doubt_classifier_report")),
            "Reward": evidence.get("reward_xp_awarded") is not None,
            "Adaptive path": evidence.get("adaptive_path_valid") is not None,
        }
        covered = [name for name, present in coverage.items() if present]
        missing = [name for name in CORE_MODULES if not coverage.get(name)]
        return {
            "module_coverage": coverage,
            "covered_modules": covered,
            "missing_modules": missing,
            "evidence_source_count": len(covered),
            "missing_evidence_count": len(missing),
            "evidence_coverage_rate": round(len(covered) / len(CORE_MODULES), 6),
        }

    def _cards(
        self,
        evidence: dict[str, Any],
        top_factors: list[dict[str, Any]],
        counterfactuals: list[dict[str, Any]],
        coverage: dict[str, Any],
    ) -> dict[str, Any]:
        learner_text = (
            f"The tutor selected {evidence.get('selected_teaching_view')} because the strongest evidence is "
            f"{', '.join(item['factor'] for item in top_factors[:3])}."
        )
        cards = {
            "learner_state_card": {
                "mastery_score": evidence.get("mastery_score"),
                "behaviour_label": evidence.get("behaviour_label"),
                "behaviour_risk": evidence.get("behaviour_risk"),
                "fused_score": evidence.get("fused_score"),
                "weakest_skill": evidence.get("weakest_skill"),
                "dominant_mistake_type": evidence.get("dominant_mistake_type"),
            },
            "decision_reason_card": {
                "selected_teaching_view": evidence.get("selected_teaching_view"),
                "selected_difficulty": evidence.get("selected_difficulty"),
                "selected_strategy": evidence.get("selected_strategy"),
                "explanation": learner_text,
                "top_evidence_factors": top_factors[:3],
            },
            "weakness_diagnosis_card": {
                "weak_assessment_types": evidence.get("weak_assessment_types"),
                "mistake_type_counts": evidence.get("mistake_type_counts"),
                "weakest_skill": evidence.get("weakest_skill"),
                "recommended_practice_type": self._recommended_practice_type(evidence),
            },
            "promotion_explanation_card": {
                "promotion_confidence": evidence.get("promotion_confidence"),
                "promotion_allowed": evidence.get("promotion_allowed"),
                "level_up_allowed": evidence.get("level_up_allowed"),
                "reason": self._promotion_reason(evidence),
                "what_would_be_needed_to_promote": [
                    "Raise fused evaluation evidence above 0.75.",
                    "Keep behaviour risk low during practice.",
                    "Show fewer high-severity mistakes on the weakest skill.",
                ],
            },
            "revision_reason_card": {
                "review_due_concepts": evidence.get("review_due_concepts"),
                "revision_priority": evidence.get("revision_priority"),
                "forgetting_review_evidence": evidence.get("review_priority"),
                "recommended_revision_views": evidence.get("recommended_revision_views"),
            },
            "rag_grounding_card": {
                "rag_grounding_score": evidence.get("rag_grounding_score"),
                "source_sections": evidence.get("rag_source_sections"),
                "safe_to_generate": evidence.get("rag_safe_to_generate"),
                "unsupported_terms": evidence.get("unsupported_terms"),
            },
            "counterfactual_card": {
                "counterfactuals": counterfactuals,
            },
            "next_action_card": {
                "next_activity": evidence.get("next_activity"),
                "practice_queue": evidence.get("assessment_types"),
                "recommended_learner_action": self._recommended_learner_action(evidence),
            },
            "teacher_evidence_card": {
                "module_sources": coverage.get("module_coverage"),
                "confidence_labels": {
                    "mastery": self._confidence_label(evidence.get("mastery_score")),
                    "behaviour": self._inverse_confidence_label(evidence.get("behaviour_risk")),
                    "evaluation": self._confidence_label(evidence.get("fused_score")),
                    "promotion": self._confidence_label(evidence.get("promotion_confidence")),
                    "rag": self._confidence_label(evidence.get("rag_grounding_score")),
                },
                "compact_breakdown": top_factors[:6],
            },
        }
        if evidence.get("doubt_intent"):
            cards["doubt_route_card"] = {
                "doubt_intent": evidence.get("doubt_intent"),
                "confidence": evidence.get("doubt_confidence"),
                "fallback_used": evidence.get("doubt_fallback_used"),
                "recommended_route": evidence.get("doubt_recommended_route"),
            }
        return cards

    def _counterfactuals(self, evidence: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {
                "condition": "mastery_score and fused_score improve",
                "current_evidence": {
                    "mastery_score": evidence.get("mastery_score"),
                    "fused_score": evidence.get("fused_score"),
                },
                "possible_decision_change": "Next action could become challenge-level practice or advance_concept.",
            },
            {
                "condition": "behaviour_risk becomes high",
                "current_evidence": {"behaviour_risk": evidence.get("behaviour_risk")},
                "possible_decision_change": "The system would avoid hard/challenge routing and choose a more supportive view.",
            },
            {
                "condition": "RAG grounding becomes low",
                "current_evidence": {"rag_grounding_score": evidence.get("rag_grounding_score")},
                "possible_decision_change": "Generated explanation would be blocked, rewritten, or routed through fallback content.",
            },
            {
                "condition": "promotion_confidence increases",
                "current_evidence": {"promotion_confidence": evidence.get("promotion_confidence")},
                "possible_decision_change": "Promotion or level-up could be allowed after strong assessment evidence.",
            },
        ]

    def _quality(
        self,
        cards: dict[str, Any],
        top_factors: list[dict[str, Any]],
        counterfactuals: list[dict[str, Any]],
        coverage: dict[str, Any],
    ) -> dict[str, Any]:
        card_rate = len(cards) / 10.0
        factor_rate = min(1.0, len(top_factors) / 5.0)
        counterfactual_rate = min(1.0, len(counterfactuals) / 3.0)
        coverage_rate = _safe_float(coverage.get("evidence_coverage_rate"), 0.0)
        score = _clamp(0.45 * coverage_rate + 0.25 * card_rate + 0.20 * factor_rate + 0.10 * counterfactual_rate)
        return {
            "card_count": len(cards),
            "top_factor_count": len(top_factors),
            "counterfactual_count": len(counterfactuals),
            "evidence_coverage_rate": coverage_rate,
            "explanation_completeness_score": round(score, 6),
            "quality_label": self._confidence_label(score),
        }

    def _recommended_practice_type(self, evidence: dict[str, Any]) -> str:
        weakest = str(evidence.get("weakest_skill") or "").strip()
        if weakest and weakest != "unknown":
            return weakest
        assessment_types = _as_list(evidence.get("assessment_types"))
        return str(assessment_types[0]) if assessment_types else "targeted_practice"

    def _promotion_reason(self, evidence: dict[str, Any]) -> str:
        if evidence.get("promotion_allowed"):
            return "Promotion is allowed because mastery and evaluation evidence are strong enough."
        return "Promotion is blocked until evaluation, mastery, and mistake evidence are stronger."

    def _recommended_learner_action(self, evidence: dict[str, Any]) -> str:
        if _safe_float(evidence.get("fused_score"), 0.5) < 0.6:
            return "Review the weakest skill and answer one targeted practice question."
        if _safe_float(evidence.get("promotion_confidence"), 0.0) >= 0.7:
            return "Try a challenge question to confirm readiness for promotion."
        return "Continue guided practice and focus on the selected assessment type."

    def _confidence_label(self, value: Any) -> str:
        score = _safe_float(value, 0.0)
        if score >= 0.75:
            return "high"
        if score >= 0.45:
            return "medium"
        return "low"

    def _inverse_confidence_label(self, value: Any) -> str:
        return self._confidence_label(1.0 - _safe_float(value, 0.0))


def build_xai_dashboard(
    integrated_output: dict[str, Any],
    learner_id: str | None = None,
    concept_id: str | None = None,
    latest_report_summaries: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return XAIDashboardBuilder().build(
        integrated_output=integrated_output,
        learner_id=learner_id,
        concept_id=concept_id,
        latest_report_summaries=latest_report_summaries,
    )
