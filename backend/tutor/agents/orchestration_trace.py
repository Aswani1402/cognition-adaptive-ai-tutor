from __future__ import annotations

from typing import Any


FINAL_FLOW = "Teach -> Ask -> Evaluate -> Diagnose -> Adapt -> Remember -> Revise -> Progress"


def _get(payload: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return default if current is None else current


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _summary_text(value: Any, max_len: int = 220) -> str:
    text = str(value or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


class AgenticOrchestrationTrace:
    """Builds a report/dashboard trace from an integrated tutor pipeline output.

    This is intentionally observational. It does not alter decisions or run
    agents; it converts existing module outputs into an agentic chain.
    """

    def build_trace(self, pipeline_output: dict[str, Any]) -> dict[str, Any]:
        demo = pipeline_output.get("demo_summary", {}) if isinstance(pipeline_output, dict) else {}
        learner_id = str(
            pipeline_output.get("learner_id")
            or _get(pipeline_output, "demo_output", "learner_id")
            or _get(pipeline_output, "knowledge_state", "data", "learner_id")
            or "14"
        )
        concept_id = str(
            demo.get("adaptive_path_resolved_concept_id")
            or demo.get("final_concept")
            or _get(pipeline_output, "concept_resolution_output", "concept_id")
            or "1"
        )
        concept_name = str(
            demo.get("adaptive_path_resolved_concept_name")
            or demo.get("concept_name")
            or _get(pipeline_output, "concept_resolution_output", "concept_name")
            or _get(pipeline_output, "current_teaching_content", "concept_name")
            or "Variables"
        )

        steps = [
            self._teaching_step(pipeline_output, demo, concept_id, concept_name),
            self._assessment_step(pipeline_output, demo),
            self._evaluator_step(pipeline_output, demo),
            self._diagnosis_step(pipeline_output, demo),
            self._learner_state_step(pipeline_output, demo),
            self._policy_step(pipeline_output, demo),
            self._memory_revision_step(pipeline_output, demo),
            self._rag_grounding_step(pipeline_output),
            self._xai_reflection_step(pipeline_output, demo),
            self._reward_step(pipeline_output, demo),
        ]

        frontend_cards = [self._to_frontend_card(step) for step in steps]
        successful = sum(1 for step in steps if step["status"] == "success")
        report_summary = (
            f"Agentic tutor trace for learner {learner_id} on {concept_name}: "
            f"{successful}/{len(steps)} stages produced usable evidence. "
            "The pipeline teaches, asks, evaluates, diagnoses, adapts, remembers, revises, and progresses with safe fallbacks."
        )

        return {
            "status": "success",
            "module": "AgenticOrchestrationTrace",
            "learner_id": learner_id,
            "concept_id": concept_id,
            "concept_name": concept_name,
            "final_flow": FINAL_FLOW,
            "trace_steps": steps,
            "agent_dependencies": [
                "KT -> TeachingStrategy",
                "Behaviour -> TeachingStrategy",
                "EvaluationFusion -> Policy",
                "MistakeAnalysis -> Memory",
                "Forgetting -> RevisionScheduler",
                "RAGGrounding -> ContentSafety",
                "XAI -> FrontendExplanation",
                "Reward -> Progression",
            ],
            "frontend_trace_cards": frontend_cards,
            "report_summary": report_summary,
        }

    def _teaching_step(self, payload: dict[str, Any], demo: dict[str, Any], concept_id: str, concept_name: str) -> dict[str, Any]:
        strategy = payload.get("evidence_aware_teaching_strategy_output") or payload.get("baseline_teaching_strategy") or {}
        frontend_view = payload.get("frontend_teaching_view_output") or {}
        selected_view = frontend_view.get("selected_view") if isinstance(frontend_view, dict) else {}
        return self._step(
            1,
            "TeachingAgent",
            input_evidence={
                "mastery": demo.get("predicted_mastery_last"),
                "behaviour_risk": demo.get("behavior_risk"),
                "review_queue": demo.get("review_queue"),
                "weakest_skill": demo.get("weakest_skill"),
            },
            decision={
                "teaching_view": demo.get("teaching_view") or demo.get("frontend_selected_view") or strategy.get("teaching_view"),
                "difficulty": strategy.get("difficulty") or demo.get("difficulty"),
                "content_focus": strategy.get("content_focus"),
                "current_concept": {"concept_id": concept_id, "concept_name": concept_name},
            },
            output={
                "frontend_selected_view": demo.get("frontend_selected_view"),
                "selected_view_title": _get(selected_view or {}, "title"),
                "display_type": demo.get("frontend_selected_display_type") or _get(selected_view or {}, "display_type"),
            },
            reason=strategy.get("reason") or "Teaching content selected from available learner evidence.",
        )

    def _assessment_step(self, payload: dict[str, Any], demo: dict[str, Any]) -> dict[str, Any]:
        assessment = payload.get("assessment_output") or {}
        return self._step(
            2,
            "AssessmentAgent",
            input_evidence={
                "teaching_view": demo.get("teaching_view"),
                "weakest_skill": demo.get("weakest_skill"),
                "difficulty": assessment.get("difficulty") or demo.get("assessment_difficulty"),
            },
            decision={
                "assessment_types": demo.get("assessment_types") or assessment.get("assessment_types"),
                "assessment_difficulty": assessment.get("difficulty") or demo.get("assessment_difficulty"),
            },
            output={
                "question_count": demo.get("assessment_question_count") or assessment.get("question_count"),
                "frontend_components": demo.get("assessment_frontend_components") or assessment.get("frontend_components_used"),
                "frontend_ready": demo.get("assessment_frontend_ready") or assessment.get("frontend_ready"),
            },
            reason="Assessment types target the selected teaching view and current weak skills.",
        )

    def _evaluator_step(self, payload: dict[str, Any], demo: dict[str, Any]) -> dict[str, Any]:
        return self._step(
            3,
            "EvaluatorAgent",
            input_evidence={
                "assessment_types": demo.get("assessment_types"),
                "question_count": demo.get("assessment_question_count"),
            },
            decision={
                "baseline_evaluation": _get(payload, "evaluation_output", "verdict"),
                "rubric_evaluation": demo.get("rubric_verdict"),
                "debug_evaluation": demo.get("debug_evaluation_label"),
                "output_prediction_evaluation": demo.get("output_prediction_evaluation_label"),
                "evaluation_fusion": demo.get("fused_label"),
            },
            output={
                "fused_score": demo.get("fused_score"),
                "fused_label": demo.get("fused_label"),
                "recommended_learning_signal": demo.get("recommended_learning_signal"),
                "evaluator_agreement": demo.get("evaluator_agreement"),
            },
            reason="Evaluator modules combine answer correctness, rubric quality, debug quality, output prediction, and fusion evidence.",
        )

    def _diagnosis_step(self, payload: dict[str, Any], demo: dict[str, Any]) -> dict[str, Any]:
        mistake = payload.get("mistake_analysis_output") or {}
        return self._step(
            4,
            "DiagnosisAgent",
            input_evidence={
                "evaluation_fusion": demo.get("fused_label"),
                "evaluation_score": demo.get("fused_score"),
            },
            decision={
                "weakest_skill": demo.get("weakest_skill"),
                "dominant_mistake_type": demo.get("dominant_mistake_type") or mistake.get("dominant_mistake_type"),
            },
            output={
                "mistake_type_counts": demo.get("mistake_type_counts") or mistake.get("mistake_type_counts"),
                "high_severity_mistake_count": demo.get("high_severity_mistake_count") or mistake.get("high_severity_count"),
            },
            reason="Mistake analysis identifies the main skill gap and the type of remediation needed.",
        )

    def _learner_state_step(self, payload: dict[str, Any], demo: dict[str, Any]) -> dict[str, Any]:
        kt_data = _get(payload, "knowledge_state", "data", "data", default={}) or {}
        behaviour = _get(payload, "behaviour_state", "data", default={}) or {}
        review_queue = _get(payload, "forgetting_state", "data", "review_queue", default=[]) or demo.get("review_queue") or []
        return self._step(
            5,
            "LearnerStateAgent",
            input_evidence={
                "quiz_history_available": bool(_get(payload, "quiz_result")),
                "knowledge_state_status": _get(payload, "knowledge_state", "status"),
                "behaviour_status": _get(payload, "behaviour_state", "status"),
            },
            decision={
                "kt_mastery": kt_data.get("predicted_mastery_last") or demo.get("predicted_mastery_last"),
                "kt_source": kt_data.get("source") or demo.get("kt_source"),
                "behaviour_label": behaviour.get("behavior_label") or demo.get("behavior_label"),
                "behaviour_risk": behaviour.get("behavior_risk") or demo.get("behavior_risk"),
                "review_due": bool(review_queue),
            },
            output={
                "kt_schema_version": kt_data.get("schema_version") or demo.get("schema_version"),
                "behaviour_risk_label": behaviour.get("behavior_risk_label") or demo.get("behavior_risk_label"),
                "review_queue": review_queue,
            },
            reason="Learner state merges KT mastery, behaviour risk, and forgetting review evidence.",
        )

    def _policy_step(self, payload: dict[str, Any], demo: dict[str, Any]) -> dict[str, Any]:
        policy = _get(payload, "policy_output", "data", default={}) or _get(payload, "baseline_policy_output", "data", default={}) or {}
        bridge = payload.get("adaptive_policy_bridge_output") or {}
        adaptive = payload.get("adaptive_path_output") or {}
        validation = payload.get("adaptive_path_validation_output") or adaptive.get("validation") or {}
        return self._step(
            6,
            "DecisionPolicyAgent",
            input_evidence={
                "evaluation_fusion": demo.get("fused_label"),
                "mastery": demo.get("predicted_mastery_last"),
                "behaviour_risk": demo.get("behavior_risk"),
                "adaptive_path_original": demo.get("adaptive_path_original_selected"),
            },
            decision={
                "policy_strategy": policy.get("strategy"),
                "adaptive_path_selected": demo.get("adaptive_path_selected") or adaptive.get("selected_next_concept"),
                "promotion_allowed": demo.get("promotion_allowed"),
                "progression_action": demo.get("progression_action") or policy.get("progression_action"),
                "model_comparison_status": demo.get("model_comparison_status"),
            },
            output={
                "adaptive_path_validation_status": demo.get("adaptive_path_validation_status"),
                "adaptive_path_fallback_used": demo.get("adaptive_path_fallback_used") or validation.get("fallback_used"),
                "bridge_agreement": bridge.get("agreement") or demo.get("bridge_agreement"),
                "bridge_override_allowed": bridge.get("override_allowed") or demo.get("bridge_override_allowed"),
                "safe_action_mask_status": self._load_report_status("rl_safe_action_masking_report.json"),
            },
            reason=validation.get("reason") or bridge.get("reason") or "Policy and adaptive path decisions are checked before progression.",
        )

    def _memory_revision_step(self, payload: dict[str, Any], demo: dict[str, Any]) -> dict[str, Any]:
        memory = payload.get("learner_notebook_memory_output") or {}
        revision_report = self._load_report("notebook_memory_revision_report.json")
        scheduler = revision_report.get("revision_scheduler_output", {}) if isinstance(revision_report, dict) else {}
        packet = scheduler.get("frontend_revision_packet", {}) if isinstance(scheduler, dict) else {}
        return self._step(
            7,
            "MemoryRevisionAgent",
            input_evidence={
                "mistake_patterns": memory.get("mistake_patterns"),
                "weak_assessment_types": memory.get("weak_assessment_types"),
                "review_queue": demo.get("review_queue"),
            },
            decision={
                "revision_priority": scheduler.get("revision_priority"),
                "recommended_revision_views": scheduler.get("recommended_revision_views"),
                "next_revision_action": packet.get("next_revision_action"),
            },
            output={
                "notebook_summary": memory.get("notebook_summary") or demo.get("notebook_summary"),
                "spaced_repetition_card_count": len(packet.get("cards", [])),
                "next_practice_queue": memory.get("next_practice_queue") or demo.get("next_practice_queue"),
            },
            reason=scheduler.get("revision_reason") or "Learner memory records mistakes and builds a revision queue.",
        )

    def _rag_grounding_step(self, payload: dict[str, Any]) -> dict[str, Any]:
        rag_report = self._load_report("rag_grounding_report.json")
        retrieval_report = self._load_report("rag_retrieval_comparison_report.json")
        summaries = retrieval_report.get("method_summaries", []) if isinstance(retrieval_report, dict) else []
        option_c = next((item for item in summaries if item.get("method") == "option_c_plus_rag"), {})
        return self._step(
            8,
            "RAGGroundingAgent",
            input_evidence={
                "rag_grounding_report_exists": bool(rag_report),
                "retrieval_comparison_exists": bool(retrieval_report),
            },
            decision={
                "grounding_status": rag_report.get("status"),
                "active_rag_source": retrieval_report.get("current_active_source"),
                "fallback_needed": retrieval_report.get("status") == "warning",
            },
            output={
                "safe_to_generate_rate": option_c.get("safe_to_generate_rate"),
                "average_grounding_score": option_c.get("average_grounding_score"),
                "context_found_rate": option_c.get("context_found_rate"),
            },
            reason="RAG grounding checks whether generated content is supported by retrieved local chunks.",
        )

    def _xai_reflection_step(self, payload: dict[str, Any], demo: dict[str, Any]) -> dict[str, Any]:
        xai_report = self._load_report("xai_model_explanation_report.json")
        reflection = payload.get("reflection_output") or {}
        insight = payload.get("learner_insight_output") or {}
        return self._step(
            9,
            "XAIReflectionAgent",
            input_evidence={
                "xai_pressure": demo.get("xai_pressure"),
                "reflection_status": reflection.get("status"),
                "learner_insight_status": insight.get("status"),
            },
            decision={
                "top_factors": demo.get("xai_top_factors"),
                "decision_explanation": _summary_text(_get(xai_report, "dashboard_ready_xai", "decision_summary") or _get(payload, "xai", "data", "reason")),
            },
            output={
                "reflection": _summary_text(_get(reflection, "reflection", "diagnosis") or reflection.get("reflection")),
                "counterfactuals": _get(xai_report, "teaching_strategy_explanation", "counterfactuals", default=[]),
                "learner_friendly_explanation": _summary_text(_get(xai_report, "teaching_strategy_explanation", "learner_friendly_explanation")),
                "teacher_dashboard_explanation": _summary_text(_get(xai_report, "teaching_strategy_explanation", "teacher_dashboard_explanation")),
            },
            reason="XAI and reflection convert model evidence into learner and teacher explanations.",
        )

    def _reward_step(self, payload: dict[str, Any], demo: dict[str, Any]) -> dict[str, Any]:
        reward = payload.get("progression_reward_output") or {}
        progression = reward.get("progression_result", {}) if isinstance(reward, dict) else {}
        reward_state = reward.get("reward_state", {}) if isinstance(reward, dict) else {}
        return self._step(
            10,
            "RewardProgressionAgent",
            input_evidence={
                "promotion_confidence": demo.get("promotion_confidence") or progression.get("promotion_confidence"),
                "fused_score": demo.get("fused_score"),
                "mastery": demo.get("predicted_mastery_last"),
            },
            decision={
                "promotion_allowed": demo.get("promotion_allowed") or progression.get("promotion_allowed"),
                "concept_cleared": demo.get("concept_cleared") or progression.get("concept_cleared"),
                "progression_action": demo.get("progression_action") or progression.get("progression_action"),
            },
            output={
                "xp_awarded": demo.get("reward_xp_awarded") or reward_state.get("xp_awarded"),
                "reward_reason": reward_state.get("reason") or reward.get("reason"),
                "current_level": reward_state.get("current_level"),
                "current_streak": reward_state.get("current_streak"),
            },
            reason="Reward and progression apply XP, promotion confidence, and safe advancement rules.",
        )

    def _step(
        self,
        step: int,
        agent: str,
        *,
        input_evidence: dict[str, Any],
        decision: dict[str, Any],
        output: dict[str, Any],
        reason: str,
    ) -> dict[str, Any]:
        has_any = any(value not in (None, "", [], {}) for section in [input_evidence, decision, output] for value in section.values())
        return {
            "step": step,
            "agent": agent,
            "input_evidence": input_evidence,
            "decision": decision,
            "output": output,
            "status": "success" if has_any else "warning",
            "reason": reason,
        }

    def _to_frontend_card(self, step: dict[str, Any]) -> dict[str, Any]:
        decision_values = [value for value in step.get("decision", {}).values() if value not in (None, "", [], {})]
        output_values = [value for value in step.get("output", {}).values() if value not in (None, "", [], {})]
        return {
            "step": step["step"],
            "agent": step["agent"],
            "title": step["agent"].replace("Agent", " Agent"),
            "status": step["status"],
            "primary_decision": _summary_text(decision_values[0] if decision_values else ""),
            "primary_output": _summary_text(output_values[0] if output_values else ""),
            "reason": _summary_text(step.get("reason")),
        }

    def _load_report_status(self, filename: str) -> str | None:
        report = self._load_report(filename)
        if not report:
            return None
        return str(report.get("status") or report.get("overall_status") or "")

    def _load_report(self, filename: str) -> dict[str, Any]:
        path = __import__("pathlib").Path("evaluation_outputs/json") / filename
        if not path.exists():
            return {}
        try:
            return __import__("json").loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}


def build_agentic_orchestration_trace(pipeline_output: dict[str, Any]) -> dict[str, Any]:
    return AgenticOrchestrationTrace().build_trace(pipeline_output)
