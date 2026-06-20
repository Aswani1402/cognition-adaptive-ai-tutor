from __future__ import annotations

from fastapi import APIRouter

from tutor.api.dependencies import latest_session_state, safe_error
from tutor.api.schemas import api_response


router = APIRouter(prefix="/tutor", tags=["tutor"])


@router.get("/adaptive-session/{learner_id}")
def adaptive_session(learner_id: str, reward_dry_run: bool = True, full_trace: bool = False) -> dict:
    module = "TutorRoutes"
    if not full_trace:
        session = latest_session_state(learner_id)
        return api_response(
            module=module,
            data={
                "auto_flow": True,
                "learner_id": learner_id,
                "frontend_response_status": "fast_runtime_session",
                "frontend_response": session.get("last_frontend_packet", {}),
                "learner_session_state": session,
                "current_activity": {"type": "teaching", "frontend_component": "SelectedTeachingViewRenderer", "payload": {}},
                "next_recommended_activity": {
                    "type": "assessment",
                    "label": "Try a quick check",
                    "reason": "Check understanding after teaching",
                },
                "guide_message": "Let's learn this concept first.",
                "backend_connected": True,
                "runtime_source": "fast_session_route",
                "full_trace_available": True,
            },
        )
    try:
        from tutor.system.frontend_response_builder import build_frontend_response
        from tutor.system.run_integrated_tutor_once import run_integrated_tutor_once
        from tutor.system.agentic_orchestrator import SafeTutorOrchestrator

        integrated = run_integrated_tutor_once(learner_id=learner_id, reward_dry_run=reward_dry_run)
        compact = build_frontend_response(integrated)
        teaching = compact.get("teaching", {}) if isinstance(compact, dict) else {}
        concept = compact.get("concept", {}) if isinstance(compact, dict) else {}
        summary = compact.get("summary", {}) if isinstance(compact, dict) else {}
        orchestrator_output = SafeTutorOrchestrator().run(
            {
                "learner_id": learner_id,
                "subject": concept.get("domain") or teaching.get("domain") or "Python",
                "concept_id": teaching.get("concept_id") or concept.get("concept_id"),
                "concept_name": teaching.get("concept_name") or concept.get("concept_name"),
                "difficulty": teaching.get("difficulty") or summary.get("final_difficulty") or "easy",
                "activity_type": "lesson",
            },
            {
                "teaching_strategy": compact.get("teaching_plan", {}),
                "assessment": compact.get("assessment", {}),
                "evaluation": compact.get("evaluation", {}),
                "kt_update": {
                    "status": "warning",
                    "model_used": "integrated_runtime_or_fallback",
                    "fallback_used": False,
                    "mastery_after": summary.get("promotion_confidence") or 0.0,
                },
                "behaviour_update": {
                    "status": "warning",
                    "model_used": "integrated_runtime_or_fallback",
                    "fallback_used": False,
                    "behaviour_risk": summary.get("behaviour_risk") or 0.0,
                },
                "path_update": compact.get("path_update", {}),
                "policy_update": compact.get("decision", {}).get("policy_output", {}) if isinstance(compact.get("decision"), dict) else {},
                "rag_evidence": {"status": "success", "source": "adaptive_session_integrated_context", "sections_used": ["teaching", "assessment"]},
                "reward_update": compact.get("persistent_reward_state", {}),
                "xai": compact.get("xai", {}),
            },
        )
        agentic_trace = orchestrator_output.get("agentic_trace", {})
        final_decision = orchestrator_output.get("final_decision", {})
        return api_response(
            module=module,
            data={
                "auto_flow": True,
                "learner_id": learner_id,
                "concept_id": compact.get("teaching", {}).get("concept_id") if isinstance(compact, dict) else None,
                "concept_name": compact.get("teaching", {}).get("concept_name") if isinstance(compact, dict) else None,
                "frontend_response_status": compact.get("status", "success") if isinstance(compact, dict) else "success",
                "frontend_response": compact,
                "integrated_status": integrated.get("status", "success") if isinstance(integrated, dict) else "success",
                "reward_dry_run": reward_dry_run,
                "teaching_strategy": compact.get("teaching_plan", {}) if isinstance(compact, dict) else {},
                "rag_evidence": {"status": "success", "source": "adaptive_session_integrated_context", "sections_used": ["teaching", "assessment"]},
                "path_status": orchestrator_output.get("safety_checks", {}),
                "agentic_trace": agentic_trace,
                "agentic_orchestrator": {
                    "status": orchestrator_output.get("status"),
                    "orchestrator_type": orchestrator_output.get("orchestrator_type"),
                    "is_fully_autonomous": False,
                    "safety_controlled": True,
                    "final_decision": final_decision,
                },
                "current_activity": {
                    "type": final_decision.get("next_activity") or "teaching",
                    "frontend_component": final_decision.get("frontend_component") or "SelectedTeachingViewRenderer",
                    "payload": compact.get("teaching", {}) if isinstance(compact, dict) else {},
                },
                "next_recommended_activity": {
                    "type": final_decision.get("next_activity") or "assessment",
                    "label": "Try a quick check",
                    "reason": final_decision.get("reason") or "Check understanding after teaching",
                },
                "guide_message": "Let's learn this concept first.",
                "backend_connected": True,
            },
        )
    except Exception as exc:
        session = latest_session_state(learner_id)
        return api_response(
            status="warning",
            module=module,
            fallback_used=True,
            data={
                "auto_flow": True,
                "learner_id": learner_id,
                "frontend_response_status": "fallback",
                "frontend_response": session.get("last_frontend_packet", {}),
                "learner_session_state": session,
                "current_activity": {"type": "teaching", "frontend_component": "GuidedTutorJourney", "payload": {}},
                "next_recommended_activity": {"type": "assessment", "label": "Try a quick check", "reason": "Fallback session continues with local teaching content"},
                "guide_message": "Mock Mode: I will guide you with fallback content.",
                "backend_connected": False,
            },
            reason=f"{type(exc).__name__}: integrated tutor dry-run unavailable.",
        )
