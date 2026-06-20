from __future__ import annotations

import json
import re
import ast

from fastapi import APIRouter

from tutor.api.dependencies import column_exists, connect, now_iso, table_exists
from tutor.api.concept_content_resolver import build_feedback
from tutor.api.schemas import RunCodeRequest, SubmitAnswerRequest, api_response
from tutor.behaviour.behaviour_state_store import persist_behaviour_state
from tutor.behaviour.lstm_behaviour_model import run_behaviour_model
from tutor.evaluation.answer_evaluator import AnswerEvaluator
from tutor.evaluation.code_runner import SafeCodeRunner
from tutor.system.agentic_orchestrator import SafeTutorOrchestrator
from tutor.system.user_persistence_store import save_mistake_from_evaluation, save_revision_schedule, update_concept_progress


router = APIRouter(tags=["evaluation"])

BEHAVIOUR_PAYLOAD_FIELDS = [
    "time_taken_sec",
    "confidence",
    "hint_used",
    "hint_count",
    "option_change_count",
    "answer_change_count",
    "run_code_count",
    "attempt_count",
    "wrong_attempt_count",
]


@router.post("/answer/submit")
def submit_answer(payload: SubmitAnswerRequest) -> dict:
    module = "EvaluationRoutes"
    try:
        payload = _with_behaviour_defaults(payload)
        question = dict(payload.question or {})
        question.update(
            {
                "learner_id": payload.learner_id,
                "concept_id": payload.concept_id or question.get("concept_id"),
                "concept_name": payload.concept_name or question.get("concept_name"),
                "domain": payload.subject or payload.domain or question.get("subject") or question.get("domain"),
                "subject": payload.subject or payload.domain or question.get("subject") or question.get("domain"),
                "task_type": payload.question_type or question.get("task_type"),
                "learner_answer": payload.answer,
                "difficulty": payload.difficulty or question.get("difficulty") or "easy",
            }
        )
        strict = _strict_structured_evaluation(question, payload.answer)
        precheck = _equivalence_precheck(question, payload.answer) if strict is None else None
        if strict is not None:
            evaluation = strict
        elif precheck:
            evaluation = precheck
        elif _simple_print_equivalent(question, payload.answer):
            evaluation = {
                "score": 1.0,
                "label": "correct",
                "feedback": "Correct. The code prints the expected output; quote style differences are equivalent here.",
                "explanation": "The evaluator ran or normalized the answer and matched the expected output.",
                "mistake_type": "none",
                "correct": True,
            }
        else:
            evaluation = AnswerEvaluator().evaluate(question)
        evaluation = _polish_evaluation(question, evaluation, payload.answer)
        save_mistake_from_evaluation(payload.learner_id, "api_session", {**question, **evaluation})
        update_concept_progress(
            payload.learner_id,
            str(question.get("concept_id") or ""),
            {
                "domain": question.get("domain"),
                "concept_name": question.get("concept_name"),
                "status": "mastered" if float(evaluation.get("score") or 0.0) >= 0.85 else "current",
                "mastery": evaluation.get("score"),
                "last_score": evaluation.get("score"),
            },
        )
        revision_update = {}
        if float(evaluation.get("score") or 0.0) < 0.85:
            revision_update = save_revision_schedule(
                payload.learner_id,
                {
                    "domain": question.get("domain"),
                    "concept_id": question.get("concept_id"),
                    "concept_name": question.get("concept_name"),
                    "priority": "medium",
                    "revision_reason": evaluation.get("mistake_type") or "answer needs review",
                    "cards": [
                        {
                            "card_type": question.get("task_type") or "review",
                            "prompt": question.get("prompt") or "Review this concept.",
                            "answer": question.get("expected_answer") or question.get("correct_answer") or "",
                            "difficulty": "medium",
                            "source": "api_answer_submit",
                        }
                    ],
                },
            )
        score = float(evaluation.get("score") or 0.0)
        difficulty = str(question.get("difficulty") or payload.difficulty or "easy").lower()
        next_difficulty = difficulty
        difficulty_passed = score >= 0.8
        concept_completed = False
        next_concept_id = None
        if difficulty_passed:
            if difficulty == "easy":
                next_difficulty = "medium"
            elif difficulty == "medium":
                next_difficulty = "hard"
            else:
                concept_completed = True
                next_concept = _next_concept_for(str(question.get("subject") or question.get("domain") or ""), str(question.get("concept_id") or ""))
                next_concept_id = next_concept.get("id") if next_concept else None
        mistake_type = evaluation.get("mistake_type") or ("none" if score >= 0.8 else "needs_review")
        weakest_skill = "output_prediction" if mistake_type == "wrong_output" else ("syntax" if mistake_type == "syntax_misunderstanding" else str(question.get("task_type") or "current_skill"))
        if score >= 0.8:
            recommended = {"type": "next_concept" if concept_completed else "next_difficulty", "label": "Start next concept" if concept_completed else f"Move to {next_difficulty} level", "reason": "Hard cleared; unlock next concept." if concept_completed else f"{difficulty.title()} cleared; continue same concept at {next_difficulty}."}
            if concept_completed and next_concept_id:
                recommended["next_concept_id"] = next_concept_id
                recommended["next_concept_name"] = next_concept.get("name")
            guide = "This concept is complete. The next topic is now available." if concept_completed else ("Easy level is complete. Try medium next." if difficulty == "easy" else "Medium level is complete. Try hard next.")
        elif score >= 0.45:
            recommended = {"type": "flashcard_revision", "label": "Practice weak area", "reason": "Partial score benefits from recall practice."}
            guide = "Almost there. I'll show a quick revision before the next question."
        elif mistake_type == "syntax_misunderstanding":
            recommended = {"type": "misconception_review", "label": "Review this concept", "reason": "Learner struggled with syntax."}
            guide = "Let's fix the syntax step by step."
        elif mistake_type == "wrong_output":
            recommended = {"type": "mindmap_revision", "label": "Practice weak area", "reason": "Learner struggled with output prediction."}
            guide = "Let's trace the output line by line."
        else:
            recommended = {"type": "misconception_review", "label": "Review this concept", "reason": "Learner needs reteaching before the next question."}
            guide = "No worries. This mistake tells us what to practice next."
        next_teaching_view = _next_teaching_view_for(
            score=score,
            task_type=str(question.get("task_type") or payload.question_type),
            mistake_type=str(evaluation.get("mistake_type") or ""),
        )
        if next_teaching_view:
            recommended["next_teaching_view"] = next_teaching_view
            recommended["label"] = _teaching_view_label(next_teaching_view, score)
        persistence_update = _persist_answer_evidence(
            payload=payload,
            question=question,
            score=score,
            difficulty=difficulty,
            next_difficulty=next_difficulty,
            difficulty_passed=difficulty_passed,
            concept_completed=concept_completed,
            recommended=recommended,
        )
        signal_rates = _behaviour_signals(payload=payload, score=score)
        behaviour_risk = min(
            1.0,
            (
                signal_rates["wrong_rate"]
                + signal_rates["slow_rate"]
                + signal_rates["low_confidence_rate"]
                + signal_rates["hint_rate"]
                + signal_rates["option_change_rate"]
                + signal_rates["answer_change_rate"]
                + signal_rates["run_code_rate"]
                + signal_rates["retry_rate"]
            )
            / 8,
        )
        behaviour_label = "low_risk" if behaviour_risk < 0.4 else "needs_support"
        mastery_before = 0.0
        mastery_after = round(max(mastery_before, score), 4)
        mastery_label = "mastered" if mastery_after >= 0.85 else "developing" if mastery_after >= 0.45 else "weak"
        stable_score = round(max(0.0, 1.0 - behaviour_risk), 4)
        confused_score = round(min(1.0, (signal_rates["hint_rate"] + signal_rates["option_change_rate"] + signal_rates["answer_change_rate"]) / 3), 4)
        guessing_score = round(max(signal_rates["guessing_risk"], signal_rates["careless_risk"]), 4)
        struggling_score = round(min(1.0, (signal_rates["wrong_rate"] + signal_rates["slow_rate"] + signal_rates["retry_rate"]) / 3), 4)
        behaviour_interaction = {
            "learner_id": payload.learner_id,
            "concept_id": question.get("concept_id"),
            "domain": question.get("domain") or question.get("subject"),
            "question_type": question.get("task_type") or payload.question_type,
            "difficulty": difficulty,
            "score": score,
            "correctness": score,
            "time_taken_sec": payload.time_taken_sec,
            "confidence": payload.confidence,
            "hint_used": payload.hint_used,
            "hint_count": payload.hint_count,
            "option_change_count": payload.option_change_count,
            "answer_change_count": payload.answer_change_count,
            "run_code_count": payload.run_code_count,
            "attempt_count": payload.attempt_count,
            "wrong_attempt_count": payload.wrong_attempt_count,
        }
        behaviour_runtime_output = run_behaviour_model(payload.learner_id, interaction=behaviour_interaction)
        behaviour_persistence_output = persist_behaviour_state(behaviour_runtime_output)
        behaviour_runtime_output["persistence_output"] = behaviour_persistence_output
        behaviour_risk = float(behaviour_runtime_output.get("behaviour_risk", behaviour_runtime_output.get("behavior_risk", behaviour_risk)) or 0.0)
        behaviour_label = str(behaviour_runtime_output.get("behaviour_state") or behaviour_runtime_output.get("behavior_label") or behaviour_label)
        behaviour_model_source = str(behaviour_runtime_output.get("model_source") or behaviour_runtime_output.get("behavior_source") or "fallback_proxy_signal_scoring")
        path_update = {
            "current_concept_id": question.get("concept_id"),
            "current_difficulty": difficulty,
            "difficulty_passed": difficulty_passed,
            "concept_completed": concept_completed,
            "next_difficulty": next_difficulty,
            "next_concept_id": next_concept_id,
            "locked_reason": None if concept_completed else "Next concept unlocks only after hard level is passed.",
            "recommended_action": recommended.get("type"),
            "recommended_next_activity": recommended,
            "reason": recommended.get("reason"),
        }
        policy_update = {
            "status": "warning",
            "model_used": "safe_policy_bridge",
            "mode": "safe_policy_bridge",
            "recommended_action": recommended.get("type"),
            "model_recommendation": recommended.get("type"),
            "safe_action_applied": True,
            "safe_action_mask_applied": True,
            "safety_controlled": True,
            "safe_action_mask": {
                "teaching": True,
                "assessment": True,
                "hint": True,
                "revision": True,
                "next_concept": bool(concept_completed),
            },
            "final_action": recommended.get("type"),
            "final_safe_decision": recommended.get("type"),
            "reason": recommended.get("reason"),
        }
        rag_evidence = {
            "status": "warning",
            "source": "question_payload",
            "sections_used": ["concept_resources", "question_payload"],
            "source_sections": ["concept_resources", "question_payload"],
            "grounding_score": None,
            "safe_to_generate": True,
            "reason": "Answer submit uses the active question payload; lesson/doubt/flashcard/mindmap routes perform richer RAG grounding.",
        }
        feedback_packet = build_feedback(
            question.get("subject") or question.get("domain"),
            question.get("concept_id"),
            score >= 0.8,
            score,
            question.get("task_type") or payload.question_type,
        )
        llm_generation = {
            "status": "warning",
            "service": "artifact_or_fallback",
            "source": "concept_resource_fallback" if question.get("fallback_used") else "validated_bank",
            "generation_source": "concept_resource_fallback" if question.get("fallback_used") else "validated_bank",
            "task_type": str(question.get("task_type") or payload.question_type),
            "model_generated": "unknown",
            "fallback_used": bool(question.get("fallback_used")),
        }
        xai_packet = {
            "learner_reason": guide,
            "top_factors": [
                {"factor": "answer_score", "value": score, "direction": "higher score promotes progression"},
                {"factor": "difficulty", "value": difficulty, "direction": "difficulty gates next level"},
                {"factor": "behaviour_risk", "value": round(behaviour_risk, 4), "direction": "higher risk triggers support"},
            ],
            "reviewer_evidence": {
                "evaluation_score": score,
                "mistake_type": mistake_type,
                "kt_model_used": "fallback_cumulative",
                "behaviour_model_used": behaviour_model_source,
                "behaviour_inputs": behaviour_runtime_output.get("evidence_inputs", {}),
                "behaviour_output": {
                    "behaviour_state": behaviour_label,
                    "behaviour_risk": round(behaviour_risk, 4),
                    "confidence_score": behaviour_runtime_output.get("confidence_score"),
                    "model_source": behaviour_model_source,
                    "fallback_reason": behaviour_runtime_output.get("fallback_reason"),
                },
                "policy_mode": "safe_policy_bridge",
                "rag_grounding": rag_evidence,
            },
        }
        session_progress_preview = {
            "xp": 10 if score >= 0.8 else 5 if score >= 0.45 else 0,
            "streak": score >= 0.8,
            "daily_goal_progress": 10 if score >= 0.8 else 5 if score >= 0.45 else 0,
            "badge_status": "Not available",
            "concept_progress": {
                "concept_id": question.get("concept_id"),
                "mastery": mastery_after,
                "difficulty_passed": difficulty_passed,
            },
        }
        reward_update = {
            "status": "success" if persistence_update.get("tables", {}).get("reward_event_log") else "warning",
            "xp_awarded": 10 if score >= 0.8 else 5 if score >= 0.45 else 0,
            "xp": session_progress_preview["xp"],
            "streak": session_progress_preview["streak"],
            "daily_goal_progress": session_progress_preview["daily_goal_progress"],
            "badge_status": session_progress_preview["badge_status"],
            "concept_progress": session_progress_preview["concept_progress"],
            "reward_reason": "answer_submit",
            "reward_source": "backend_reward_state" if persistence_update.get("tables", {}).get("reward_event_log") else "session_progress_preview",
            "session_progress_preview": session_progress_preview,
            "concept_completed": concept_completed,
            "difficulty_passed": difficulty_passed,
            "fallback_used": not bool(persistence_update.get("tables", {}).get("reward_event_log")),
        }
        notebook_update = {
            "status": "success",
            "saved_to_notebook": True,
            "mistake_logged": score < 0.8,
            "revision_saved": bool(revision_update),
        }
        agentic_trace = {
            "status": "success",
            "representation": "orchestration_trace",
            "autonomous_agent": False,
            "steps": [
                {"name": "collect answer payload", "status": "complete"},
                {"name": "evaluate answer", "status": "complete"},
                {"name": "update KT fallback state", "status": "complete" if persistence_update.get("tables", {}).get("knowledge_state") else "warning"},
                {"name": "score behaviour signals", "status": "complete" if persistence_update.get("tables", {}).get("behaviour_state") else "warning"},
                {"name": "choose safe next activity", "status": "complete"},
                {"name": "persist memory/reward evidence", "status": "complete" if persistence_update.get("status") == "success" else "warning"},
                {"name": "build XAI evidence", "status": "complete"},
            ],
            "reason": "Agentic AI is represented as an orchestration trace across tutor modules, not a fully autonomous agent.",
        }
        orchestrator_output = SafeTutorOrchestrator().run(
            {
                "learner_id": payload.learner_id,
                "subject": question.get("subject") or question.get("domain"),
                "concept_id": question.get("concept_id"),
                "concept_name": question.get("concept_name"),
                "difficulty": difficulty,
                "activity_type": "answer_submit",
                "learner_answer": payload.answer,
                "question": question,
                "behaviour_payload": {
                    "confidence": payload.confidence,
                    "time_taken_sec": payload.time_taken_sec,
                    "hint_used": payload.hint_used,
                    "hint_count": payload.hint_count,
                    "option_change_count": payload.option_change_count,
                    "answer_change_count": payload.answer_change_count,
                    "run_code_count": payload.run_code_count,
                    "attempt_count": payload.attempt_count,
                    "wrong_attempt_count": payload.wrong_attempt_count,
                },
            },
            {
                "teaching_strategy": {
                    "selected_view": str(question.get("selected_view") or "code_view"),
                    "reason": "Answer submit preserves the current teaching view and chooses the next activity from evaluation evidence.",
                    "model_used": "current_view_context",
                    "signals_used": ["score", "difficulty", "mistake_type", "behaviour_risk"],
                },
                "evaluation": evaluation,
                "kt_update": {
                    "status": "success" if persistence_update.get("tables", {}).get("knowledge_state") else "warning",
                    "model_used": "fallback_cumulative",
                    "kt_source": "fallback_cumulative_mastery",
                    "concept_id": question.get("concept_id"),
                    "mastery_before": mastery_before,
                    "mastery_after": mastery_after,
                    "mastery_label": mastery_label,
                    "fallback_reason": "Answer submission updates cumulative mastery state; DKT sequence runtime runs in integrated tutor pipeline.",
                    "fallback_used": True,
                    "difficulty": difficulty,
                },
                "behaviour_update": {
                    "status": behaviour_runtime_output.get("status", "success"),
                    "model_used": behaviour_model_source,
                    "model_source": behaviour_model_source,
                    "fallback_used": behaviour_model_source != "lstm_runtime",
                    "fallback_reason": behaviour_runtime_output.get("fallback_reason"),
                    "signals_used": BEHAVIOUR_PAYLOAD_FIELDS,
                    "evidence_inputs": behaviour_runtime_output.get("evidence_inputs", {}),
                    "signal_rates": signal_rates,
                    "stable_score": stable_score,
                    "confused_score": confused_score,
                    "guessing_score": guessing_score,
                    "struggling_score": struggling_score,
                    "behaviour_state": behaviour_label,
                    "behaviour_label": behaviour_label,
                    "behaviour_risk": round(behaviour_risk, 4),
                    "confidence_score": behaviour_runtime_output.get("confidence_score"),
                    "behaviour_confidence": behaviour_runtime_output.get("confidence_score", payload.confidence or 0.6),
                },
                "path_update": path_update,
                "policy_update": policy_update,
                "rag_evidence": rag_evidence,
                "revision_update": revision_update,
                "reward_update": reward_update,
                "xai": xai_packet,
            },
        )
        agentic_trace = orchestrator_output.get("agentic_trace", agentic_trace)
        final_decision = orchestrator_output.get("final_decision", {})
        if final_decision:
            recommended = {
                **recommended,
                "type": final_decision.get("next_activity") or recommended.get("type"),
                "reason": final_decision.get("reason") or recommended.get("reason"),
                "frontend_component": final_decision.get("frontend_component"),
                "promotion_allowed": final_decision.get("promotion_allowed"),
            }
            policy_update["final_action"] = final_decision.get("next_activity") or policy_update.get("final_action")
            policy_update["final_safe_decision"] = final_decision.get("next_activity") or policy_update.get("final_safe_decision")
            policy_update["safe_action_applied"] = bool(final_decision.get("safe_action_applied", True))
            policy_update["safe_action_mask_applied"] = bool(final_decision.get("safe_action_applied", True))
            policy_update["safety_controlled"] = True
            path_update["recommended_next_activity"] = recommended
            path_update["recommended_action"] = recommended.get("type")
            path_update["reason"] = recommended.get("reason")
        return api_response(
            module=module,
            data={
                "auto_flow": True,
                "learner_id": payload.learner_id,
                "concept_id": question.get("concept_id"),
                "concept_name": question.get("concept_name"),
                "score": evaluation.get("score"),
                "label": evaluation.get("label") or ("correct" if score >= 0.8 else "partial" if score >= 0.45 else "wrong"),
                "is_correct": score >= 0.8,
                "correct": score >= 0.8,
                "correct_answer": _display_correct_answer(question),
                "source": llm_generation["source"],
                "generation_source": llm_generation["generation_source"],
                "feedback": evaluation.get("feedback"),
                "feedback_by_type": feedback_packet.get("feedback_by_type"),
                "feedback_type": feedback_packet.get("feedback_type"),
                "mascot_script": feedback_packet.get("voice_script"),
                "explanation": evaluation.get("explanation") or _answer_explanation(question, score),
                "learner_answer": payload.answer,
                "mistake_type": None if score >= 0.8 else mistake_type,
                "weakest_skill": weakest_skill,
                "difficulty": difficulty,
                "difficulty_passed": difficulty_passed,
                "concept_completed": concept_completed,
                "next_difficulty": next_difficulty,
                "next_concept_id": next_concept_id,
                "difficulty_progress": {
                    "easy": "passed" if difficulty in {"medium", "hard"} or (difficulty == "easy" and difficulty_passed) else ("retry" if difficulty == "easy" else "locked"),
                    "medium": "passed" if difficulty == "hard" or (difficulty == "medium" and difficulty_passed) else ("current" if next_difficulty == "medium" and difficulty_passed else "retry" if difficulty == "medium" else "locked"),
                    "hard": "passed" if difficulty == "hard" and difficulty_passed else ("current" if next_difficulty == "hard" and difficulty_passed else "retry" if difficulty == "hard" else "locked"),
                },
                "next_recommendation": "continue" if score >= 0.8 else "review_current_concept",
                "recommended_next_activity": recommended,
                "next_recommended_activity": recommended,
                "next_activity": recommended,
                "next_teaching_view": next_teaching_view,
                "recommended_teaching_view": next_teaching_view,
                "guide_message": guide,
                "reward_state": {},
                "xai_reason": {"reason": recommended["reason"]},
                "memory_update": notebook_update,
                "current_activity": {"type": "feedback", "frontend_component": "FeedbackCard", "payload": {}},
                "backend_connected": True,
                "evaluation": evaluation,
                "revision_update": revision_update,
                "reward_update": reward_update,
                "notebook_update": notebook_update,
                "persistence_update": persistence_update,
                "behaviour_update": {
                    "status": behaviour_runtime_output.get("status", "success"),
                    "model_used": behaviour_model_source,
                    "model_source": behaviour_model_source,
                    "fallback_used": behaviour_model_source != "lstm_runtime",
                    "fallback_reason": behaviour_runtime_output.get("fallback_reason"),
                    "signals_used": BEHAVIOUR_PAYLOAD_FIELDS,
                    "evidence_inputs": behaviour_runtime_output.get("evidence_inputs", {}),
                    "signal_rates": signal_rates,
                    "stable_score": stable_score,
                    "confused_score": confused_score,
                    "guessing_score": guessing_score,
                    "struggling_score": struggling_score,
                    "behaviour_state": behaviour_label,
                    "behaviour_label": behaviour_label,
                    "behaviour_risk": round(behaviour_risk, 4),
                    "confidence_score": behaviour_runtime_output.get("confidence_score"),
                    "behaviour_confidence": behaviour_runtime_output.get("confidence_score", payload.confidence or 0.6),
                    "runtime_output": behaviour_runtime_output,
                    "hint_used": payload.hint_used,
                    "hint_count": payload.hint_count,
                    "time_taken_sec": payload.time_taken_sec,
                    "confidence": payload.confidence,
                    "option_change_count": payload.option_change_count,
                    "answer_change_count": payload.answer_change_count,
                    "run_code_count": payload.run_code_count,
                    "attempt_count": payload.attempt_count,
                    "wrong_attempt_count": payload.wrong_attempt_count,
                },
                "kt_update": {
                    "status": "success" if persistence_update.get("tables", {}).get("knowledge_state") else "warning",
                    "model_used": "fallback_cumulative",
                    "kt_source": "fallback_cumulative_mastery",
                    "concept_id": question.get("concept_id"),
                    "mastery_before": mastery_before,
                    "mastery_after": mastery_after,
                    "mastery_label": mastery_label,
                    "fallback_reason": "Answer submission updates cumulative mastery state; DKT sequence runtime runs in integrated tutor pipeline.",
                    "fallback_used": True,
                    "difficulty": difficulty,
                },
                "path_update": path_update,
                "policy_update": policy_update,
                "rag_update": rag_evidence,
                "rag_evidence": rag_evidence,
                "llm_generation": llm_generation,
                "teaching_strategy": {
                    "selected_view": str(question.get("selected_view") or "code_view"),
                    "reason": "Answer submit preserves the current teaching view and chooses the next activity from evaluation evidence.",
                    "model_used": "current_view_context",
                    "signals_used": ["score", "difficulty", "mistake_type", "behaviour_risk"],
                },
                "xai": xai_packet,
                "agentic_trace": agentic_trace,
                "agentic_orchestrator": {
                    "status": orchestrator_output.get("status"),
                    "orchestrator_type": orchestrator_output.get("orchestrator_type"),
                    "is_fully_autonomous": False,
                    "safety_controlled": True,
                    "safety_checks": orchestrator_output.get("safety_checks", {}),
                    "final_decision": final_decision,
                },
            },
        )
    except Exception as exc:
        return api_response(status="warning", module=module, fallback_used=True, reason=f"{type(exc).__name__}: {exc}")


def _with_behaviour_defaults(payload: SubmitAnswerRequest) -> SubmitAnswerRequest:
    values = {
        "confidence": 0.5 if payload.confidence is None else payload.confidence,
        "time_taken_sec": 0 if payload.time_taken_sec is None else payload.time_taken_sec,
        "hint_used": bool(payload.hint_used),
        "hint_count": int(payload.hint_count or 0),
        "option_change_count": int(payload.option_change_count or 0),
        "answer_change_count": int(payload.answer_change_count or 0),
        "run_code_count": int(payload.run_code_count or 0),
        "attempt_count": int(payload.attempt_count or 1),
        "wrong_attempt_count": int(payload.wrong_attempt_count or 0),
    }
    if hasattr(payload, "model_copy"):
        return payload.model_copy(update=values)
    return payload.copy(update=values)


def _next_concept_for(subject: str, concept_id: str) -> dict:
    try:
        from tutor.api.integration_routes import _concepts

        nodes = _concepts(subject or "python")
        for idx, node in enumerate(nodes):
            if str(node.get("id")) == concept_id and idx + 1 < len(nodes):
                return nodes[idx + 1]
    except Exception:
        pass
    return {}


@router.post("/code/run")
def run_code(payload: RunCodeRequest) -> dict:
    module = "EvaluationRoutes"
    try:
        result = SafeCodeRunner().run(
            code=payload.code,
            expected_output=payload.expected_output,
            test_cases=payload.test_cases,
        )
        return api_response(
            module=module,
            fallback_used=bool(result.get("blocked_reason")),
            data={
                "learner_id": payload.learner_id,
                "concept_id": payload.concept_id,
                "question_id": payload.question_id,
                "stdout": result.get("stdout"),
                "stderr": result.get("stderr"),
                "status": result.get("execution_status") or result.get("status"),
                "score": result.get("score"),
                "safety_error": result.get("blocked_reason") or result.get("error"),
                "runner_output": result,
            },
        )
    except Exception as exc:
        return api_response(status="warning", module=module, fallback_used=True, reason=f"{type(exc).__name__}: {exc}")


def _behaviour_signals(*, payload: SubmitAnswerRequest, score: float) -> dict[str, float]:
    return {
        "wrong_rate": 0.0 if score >= 0.8 else 1.0,
        "slow_rate": 1.0 if (payload.time_taken_sec or 0) > 60 else 0.0,
        "low_confidence_rate": 1.0 if (payload.confidence or 0.6) < 0.5 else 0.0,
        "hint_rate": min(1.0, float(payload.hint_count or 0) / 3) if payload.hint_used else 0.0,
        "option_change_rate": min(1.0, float(payload.option_change_count or 0) / 3),
        "answer_change_rate": min(1.0, float(payload.answer_change_count or 0) / 5),
        "run_code_rate": min(1.0, float(payload.run_code_count or 0) / 5),
        "retry_rate": min(1.0, max(float(payload.attempt_count or 1) - 1, float(payload.wrong_attempt_count or 0)) / 3),
        "guessing_risk": 1.0 if (payload.confidence or 0.6) >= 0.8 and score < 0.8 else 0.0,
        "careless_risk": 1.0 if (payload.time_taken_sec or 0) < 5 and score < 0.8 else 0.0,
        "confusion_risk": 1.0 if (payload.hint_count or 0) > 1 or (payload.option_change_count or 0) > 2 else 0.0,
        "anomaly_score": 0.0,
    }


def _norm_answer(value: object) -> str:
    if isinstance(value, dict):
        value = " ".join(str(v) for v in value.values())
    text = str(value or "").strip().lower()
    text = text.replace('"', "'")
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .;:!?'\"")


def _display_correct_answer(question: dict) -> str:
    task = str(question.get("task_type") or question.get("question_type") or "").lower()
    options = question.get("options")
    if task in {"mcq", "multiple_choice", "true_or_false", "true_false"} and isinstance(options, list):
        indexed = question.get("correct_option_index")
        try:
            if indexed is not None and str(indexed).strip() != "":
                idx = int(indexed)
                if 0 <= idx < len(options):
                    return str(options[idx])
        except (TypeError, ValueError):
            pass
        for key in ("correct_option", "correct_answer", "correctAnswer"):
            value = question.get(key)
            if value is None:
                continue
            value_text = str(value).strip()
            for option in options:
                option_text = str(option).strip()
                if value_text == option_text or value_text in option_text or option_text in value_text:
                    return option_text
            if value_text and len(value_text) <= 300:
                return value_text
        if options:
            return str(options[0])
    for key in ("correct_answer", "correctAnswer", "expected_answer", "expectedOutput", "expected_output"):
        if question.get(key) is not None:
            value = question.get(key)
            if isinstance(value, dict):
                return _format_expected_dict(value)
            return _clip_text(str(value), max_sentences=3, max_chars=600)
    blanks = question.get("blanks")
    if isinstance(blanks, list) and blanks:
        return ", ".join(str(item.get("answer")) for item in blanks if isinstance(item, dict) and item.get("answer"))
    return ""


def _answer_explanation(question: dict, score: float) -> str:
    correct = _display_correct_answer(question)
    task = str(question.get("task_type") or question.get("question_type") or "").lower()
    if task in {"mcq", "multiple_choice", "true_or_false", "true_false"}:
        if score >= 0.8:
            return "This matches the core idea tested by the question."
        return "The correct option best matches the concept definition and the selected option does not."
    if score >= 0.8:
        return f"Your answer matches the expected idea: {correct}." if correct else "Your answer matches the expected idea."
    if score >= 0.45:
        return f"Your answer is close. Compare it with: {correct}." if correct else "Your answer is partially correct but needs more detail."
    return f"The expected answer is: {correct}." if correct else "Review the concept and try a similar question."


def _is_valid_assignment(answer: object) -> bool:
    text = str(answer or "").strip()
    if not text or "=" not in text or "==" in text:
        return False
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False
    if not tree.body:
        return False
    assignment_nodes = (ast.Assign, ast.AnnAssign, ast.AugAssign)
    return all(isinstance(node, assignment_nodes) for node in tree.body)


def _has_explanation(answer: object) -> bool:
    text = str(answer or "").lower()
    markers = ["because", "so that", "useful", "used to", "helps", "why", "explain", "means"]
    return any(marker in text for marker in markers) and len(text.split()) >= 8


def _open_ended_precheck(question: dict, answer: object) -> dict | None:
    task = str(question.get("task_type") or question.get("question_type") or "").lower()
    if task not in {"transfer", "transfer_question", "transfer_task", "real_world_application_question", "challenge", "challenge_question", "multi_step_challenge", "explanation", "explanation_check", "practice_question"}:
        return None
    prompt = _norm_answer(question.get("prompt"))
    concept = _norm_answer(question.get("concept_name"))
    asks_for_assignment = any(term in f"{prompt} {concept}" for term in ["variable", "assignment", "store", "code", "write two", "write or explain"])
    if asks_for_assignment and _is_valid_assignment(answer):
        if _has_explanation(answer):
            return _precheck_result(
                0.8,
                "Your assignment is valid and you added some explanation. Add every scenario detail from the prompt for a fully strong answer.",
                question,
                answer,
                mistake_type="minor_missing_requirement",
            )
        return _precheck_result(
            0.55,
            "Your assignment is syntactically valid. Missing: the scenario details and a short explanation of why the concept is useful.",
            question,
            answer,
            mistake_type="missing_explanation",
        )
    return None


def _polish_evaluation(question: dict, evaluation: dict, answer: object) -> dict:
    task_type = str(question.get("task_type") or question.get("question_type") or "").lower()
    score = float(evaluation.get("score") or 0.0)
    label = "strong" if score >= 0.8 else "partial" if score >= 0.45 else "weak"
    expected = _display_correct_answer(question) or "the expected idea in the prompt"
    learner = str(answer or "").strip()
    mistake_type = evaluation.get("mistake_type")
    if score >= 0.8:
        feedback = "Correct. Your answer matches the expected idea."
        mistake_type = None
    elif score >= 0.45:
        if task_type in {"transfer_question", "transfer_task", "real_world_application_question"}:
            feedback = "Partly correct. Your answer starts the scenario, but it needs a clearer link to the concept and the requested details."
        else:
            feedback = "Partly correct. Compare your answer with the expected idea, then retry one similar question."
        if not mistake_type or mistake_type in {"partial", "needs_review", "wrong"}:
            mistake_type = "missing_explanation" if "transfer" in task_type else "partial_understanding"
    else:
        if _is_valid_assignment(learner) and any(term in task_type for term in ["transfer", "challenge", "practice"]):
            score = 0.55
            label = "partial"
            feedback = "Partly correct. The syntax is valid, but the answer does not satisfy the full scenario or explain the concept rule."
            mistake_type = "missing_explanation"
        else:
            feedback = "Not quite right. Review the correct answer and the concept rule, then try one similar question."
            mistake_type = mistake_type or "weak_answer"
    return {
        **evaluation,
        "score": round(score, 4),
        "label": label,
        "feedback": _clip_feedback(feedback),
        "mistake_type": mistake_type,
        "correct": score >= 0.8,
    }


def _clip_feedback(text: str) -> str:
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", str(text or "")) if part.strip()]
    return " ".join(parts[:3])[:420]


def _clip_text(text: str, max_sentences: int = 3, max_chars: int = 300) -> str:
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", str(text or "")) if part.strip()]
    compact = " ".join(parts[:max_sentences]) if parts else str(text or "").strip()
    compact = re.sub(r"\s+", " ", compact).strip()
    if len(compact) > max_chars:
        compact = compact[: max_chars - 3].rsplit(" ", 1)[0].rstrip(",;:") + "..."
    return compact


def _format_expected_dict(value: dict) -> str:
    preferred_keys = ("expected_fix", "expected_output", "expected_behavior", "correct_order", "expected_points", "success_criteria", "requirements")
    parts: list[str] = []
    for key in preferred_keys:
        if key not in value:
            continue
        item = value.get(key)
        if isinstance(item, list):
            parts.extend(str(part) for part in item[:4] if part)
        elif item:
            parts.append(str(item))
    if not parts:
        parts = [str(v) for v in value.values() if v]
    return _clip_text("; ".join(parts), max_sentences=4, max_chars=600)


def _next_teaching_view_for(*, score: float, task_type: str, mistake_type: str) -> str | None:
    if score >= 0.8:
        return None
    key = f"{task_type} {mistake_type}".lower()
    if "transfer" in key:
        return "simple_example_view" if score < 0.45 else "step_by_step_view"
    if "syntax" in key:
        return "code_view"
    if "output" in key:
        return "output_prediction_view"
    if "debug" in key:
        return "debug_view"
    if "misconception" in key or "wrong_option" in key or "weak" in key:
        return "misconception_view"
    return "step_by_step_view"


def _teaching_view_label(view: str, score: float) -> str:
    if score >= 0.45:
        return "Practice weak area"
    return "Review this concept"


def _equivalence_precheck(question: dict, answer: object) -> dict | None:
    task = str(question.get("task_type") or question.get("question_type") or "").lower()
    prompt = _norm_answer(question.get("prompt"))
    learner = _norm_answer(answer)
    expected = _norm_answer(_display_correct_answer(question))
    if not learner:
        return None
    variable_context = "variable" in prompt or "variable" in _norm_answer(question.get("concept_name"))

    if task in {"mcq", "multiple_choice"}:
        if expected and (learner == expected or learner in expected or expected in learner):
            return _precheck_result(1.0, "Correct. That option matches the concept.", question, answer)
        if variable_context and (("refer" in learner and any(term in learner for term in ["value", "object"])) or ("store" in learner and any(term in learner for term in ["value", "object", "data"]))):
            return _precheck_result(1.0, "Correct. A variable is used to refer to a value or object.", question, answer)

    if task in {"fill_blank", "fill_in_the_blank", "syntax_completion"}:
        accepted = {expected} if expected else set()
        if variable_context:
            accepted.update({"value", "object", "value/object", "data"})
        if learner in accepted:
            return _precheck_result(1.0, "Correct. That word fits the blank.", question, answer)
        if expected and (learner in expected or expected in learner):
            return _precheck_result(0.85, "Mostly correct. Your answer matches the expected blank.", question, answer)

    if task in {"output_prediction", "code_tracing"}:
        expected_output = _norm_answer(question.get("expected_output") or question.get("expectedOutput") or question.get("correct_answer") or question.get("correctAnswer"))
        if expected_output and learner == expected_output:
            return _precheck_result(1.0, "Correct. The output prediction matches the printed value.", question, answer)
        code = str(question.get("code") or "")
        if code and "print(" in code:
            try:
                result = SafeCodeRunner().run(code=code, expected_output=str(answer).strip())
                stdout = _norm_answer(result.get("stdout"))
                if stdout and stdout == learner:
                    return _precheck_result(1.0, "Correct. Running the code produces that output.", question, answer)
            except Exception:
                pass
    open_ended = _open_ended_precheck(question, answer)
    if open_ended is not None:
        return open_ended
    return None


def _strict_structured_evaluation(question: dict, answer: object) -> dict | None:
    task = str(question.get("task_type") or question.get("question_type") or "").lower()
    learner = _norm_answer(answer)
    expected = _norm_answer(_display_correct_answer(question))
    if task in {"mcq", "multiple_choice", "true_or_false", "true_false", "fill_blank", "fill_in_the_blank", "syntax_completion", "output_prediction", "code_tracing"}:
        if not expected:
            return None
        correct = learner == expected
        if task in {"true_or_false", "true_false"}:
            correct = learner in {"true", "false"} and learner == expected
        if task in {"fill_blank", "fill_in_the_blank", "syntax_completion"}:
            synonyms = {
                item.strip().lower()
                for item in str(question.get("synonyms") or "").replace("|", ",").split(",")
                if item.strip()
            }
            correct = learner == expected or learner in synonyms
        score = 1.0 if correct else 0.0
        return _precheck_result(
            score,
            "Correct. Your answer matches the expected answer." if correct else "Incorrect. Review the expected answer and the concept evidence.",
            question,
            answer,
        )
    if task in {"debug_task", "debug_challenge", "coding_prompt"}:
        expected_output = str(question.get("expected_output") or question.get("expectedOutput") or "").strip()
        if expected_output and str(answer or "").strip():
            try:
                result = SafeCodeRunner().run(code=str(answer), expected_output=expected_output)
                correct = str(result.get("stdout") or "").strip() == expected_output and not result.get("stderr") and not result.get("blocked_reason")
                return _precheck_result(1.0 if correct else 0.0, "Code output matches." if correct else "Code output does not match the expected output.", question, answer)
            except Exception:
                return _precheck_result(0.0, "Code could not be evaluated against the expected output.", question, answer)
    return None


def _precheck_result(score: float, feedback: str, question: dict, answer: object, mistake_type: str | None = None) -> dict:
    return {
        "score": score,
        "label": "strong" if score >= 0.85 else "partial" if score >= 0.45 else "weak",
        "feedback": feedback,
        "explanation": _answer_explanation(question, score),
        "mistake_type": None if score >= 0.85 else mistake_type or ("partial_understanding" if score >= 0.45 else "needs_review"),
        "correct": score >= 0.85,
        "details": {"learner_answer": answer, "expected_answer": _display_correct_answer(question), "routed_to": "equivalence_precheck"},
    }


def _simple_print_equivalent(question: dict, answer: object) -> bool:
    code = str(answer or question.get("learner_answer") or question.get("code") or "")
    expected = str(question.get("expected_output") or question.get("correct_answer") or "").strip()
    if not code.strip() or not expected:
        return False
    if "print(" not in code:
        return False
    try:
        result = SafeCodeRunner().run(code=code, expected_output=expected)
        stdout = str(result.get("stdout") or "").strip()
        return stdout == expected and not result.get("stderr") and not result.get("blocked_reason")
    except Exception:
        compact = code.replace('"', "'").replace(" ", "")
        return compact in {f"print('{expected}')", f"print({expected!r})".replace('"', "'").replace(" ", "")}


def _persist_answer_evidence(
    *,
    payload: SubmitAnswerRequest,
    question: dict,
    score: float,
    difficulty: str,
    next_difficulty: str,
    difficulty_passed: bool,
    concept_completed: bool,
    recommended: dict,
) -> dict:
    now = now_iso()
    learner_id = payload.learner_id
    concept_id = str(question.get("concept_id") or "")
    concept_name = str(question.get("concept_name") or "")
    domain = str(question.get("domain") or question.get("subject") or "")
    question_id = str(payload.question_id or question.get("questionId") or question.get("question_id") or "")
    task_type = str(question.get("task_type") or payload.question_type)
    rows: dict[str, bool] = {}
    try:
        conn = connect()
        try:
            if table_exists(conn, "quiz_results"):
                _insert_available(
                    conn,
                    "quiz_results",
                    {
                        "learner_id": learner_id,
                        "concept_id": concept_id,
                        "concept_name": concept_name,
                        "subject": domain,
                        "domain": domain,
                        "difficulty": difficulty,
                        "question_id": question_id,
                        "question_type": task_type,
                        "selected_option": str(payload.answer),
                        "answer": str(payload.answer),
                        "is_correct": 1 if score >= 0.8 else 0,
                        "confidence": payload.confidence,
                        "time_taken_sec": payload.time_taken_sec,
                        "attempt_no": payload.attempt_count,
                        "attempt_count": payload.attempt_count,
                        "timestamp": now,
                        "hint_used": 1 if payload.hint_used else 0,
                        "hint_count": payload.hint_count,
                        "option_changes_count": payload.option_change_count,
                        "option_change_count": payload.option_change_count,
                        "answer_change_count": payload.answer_change_count,
                        "run_code_count": payload.run_code_count,
                        "wrong_attempt_count": payload.wrong_attempt_count,
                    },
                )
                rows["quiz_results"] = True
            if table_exists(conn, "knowledge_state"):
                existing_state = conn.execute(
                    "SELECT state_json FROM knowledge_state WHERE student_id = ? LIMIT 1",
                    (learner_id,),
                ).fetchone()
                state_json = _merged_knowledge_state_json(
                    existing_state[0] if existing_state else None,
                    subject=domain,
                    concept_id=concept_id,
                    concept_name=concept_name,
                    mastery=score,
                    difficulty=difficulty,
                    updated_at=now,
                )
                updated = conn.execute(
                    "UPDATE knowledge_state SET state_json = ?, updated_at = ? WHERE student_id = ?",
                    (state_json, now, learner_id),
                )
                if updated.rowcount == 0:
                    conn.execute(
                        "INSERT INTO knowledge_state (student_id, state_json, updated_at) VALUES (?, ?, ?)",
                        (learner_id, state_json, now),
                    )
                rows["knowledge_state"] = True
            if table_exists(conn, "behaviour_state"):
                slow_rate = 1.0 if (payload.time_taken_sec or 0) > 60 else 0.0
                low_conf = 1.0 if (payload.confidence or 0.6) < 0.5 else 0.0
                wrong_rate = 0.0 if score >= 0.8 else 1.0
                hint_rate = 1.0 if payload.hint_used else 0.0
                option_rate = min(1.0, payload.option_change_count / 3) if payload.option_change_count else 0.0
                answer_rate = min(1.0, float(payload.answer_change_count or 0) / 5)
                run_code_rate = min(1.0, float(payload.run_code_count or 0) / 5)
                retry_rate = min(1.0, max(float(payload.attempt_count or 1) - 1, float(payload.wrong_attempt_count or 0)) / 3)
                behaviour_risk = min(1.0, (wrong_rate + slow_rate + low_conf + hint_rate + option_rate + answer_rate + run_code_rate + retry_rate) / 8)
                behaviour_payload = {
                    "learner_id": learner_id,
                    "behavior_label": "low_risk" if behaviour_risk < 0.4 else "needs_support",
                    "behavior_score": 1.0 - behaviour_risk,
                    "wrong_rate": wrong_rate,
                    "slow_rate": slow_rate,
                    "low_confidence_rate": low_conf,
                    "hint_rate": hint_rate,
                    "option_change_rate": option_rate,
                    "answer_change_rate": answer_rate,
                    "run_code_rate": run_code_rate,
                    "retry_rate": retry_rate,
                    "timestamp": now,
                    "behavior_confidence": payload.confidence or 0.6,
                    "behavior_risk": behaviour_risk,
                    "behavior_risk_label": "low" if behaviour_risk < 0.4 else "medium",
                    "model_used": "frontend_evidence_fallback",
                    "sequence_length": payload.attempt_count,
                    "behavior_source": "answer_submit_payload",
                    "state_json": json.dumps({"question_type": task_type, "signals_used": BEHAVIOUR_PAYLOAD_FIELDS, "payload": _payload_dict(payload)}),
                }
                _insert_available(conn, "behaviour_state", behaviour_payload)
                rows["behaviour_state"] = True
            if table_exists(conn, "reward_event_log"):
                xp_awarded = 10 if score >= 0.8 else 5 if score >= 0.45 else 0
                conn.execute(
                    """
                    INSERT INTO reward_event_log (
                        learner_id, concept_id, concept_name, xp_awarded, reward_reason,
                        celebration_type, progression_action, promotion_allowed,
                        model_progression_action, model_promotion_allowed, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        learner_id,
                        concept_id,
                        concept_name,
                        xp_awarded,
                        "answer_submit",
                        "correct_answer" if score >= 0.8 else "practice",
                        recommended.get("type"),
                        1 if difficulty_passed else 0,
                        recommended.get("type"),
                        1 if difficulty_passed else 0,
                        now,
                    ),
                )
                rows["reward_event_log"] = True
            if table_exists(conn, "learner_session_log"):
                conn.execute(
                    """
                    INSERT INTO learner_session_log (
                        learner_id, session_id, event_type, domain, concept_id, concept_name,
                        teaching_view, difficulty, event_json, created_at, selected_view,
                        started_at, mode, metadata_json
                    )
                    VALUES (?, 'guided_session', 'answer_submitted', ?, ?, ?, ?, ?, ?, ?, ?, ?, 'guided', ?)
                    """,
                    (
                        learner_id,
                        domain,
                        concept_id,
                        concept_name,
                        str(question.get("selected_view") or "code_view"),
                        difficulty,
                        json.dumps({"score": score, "question_type": task_type, "recommended": recommended}),
                        now,
                        str(question.get("selected_view") or "code_view"),
                        now,
                        json.dumps({"behaviour_payload": payload.dict()}),
                    ),
                )
                rows["learner_session_log"] = True
            if table_exists(conn, "concept_unlock_state"):
                existing_unlock = conn.execute(
                    """
                    SELECT mastery_score, promotion_confidence, evidence_json, unlocked_at
                    FROM concept_unlock_state
                    WHERE learner_id = ? AND concept_id = ?
                    LIMIT 1
                    """,
                    (learner_id, concept_id),
                ).fetchone()
                existing_evidence = _safe_json_loads(existing_unlock["evidence_json"] if existing_unlock else None)
                existing_evidence.update(
                    {
                        "difficulty": difficulty,
                        "next_difficulty": next_difficulty,
                        "current_difficulty": next_difficulty if difficulty_passed and not concept_completed else difficulty,
                    }
                )
                previous_mastery = float(existing_unlock["mastery_score"] or 0.0) if existing_unlock else 0.0
                previous_confidence = float(existing_unlock["promotion_confidence"] or 0.0) if existing_unlock else 0.0
                conn.execute(
                    """
                    INSERT OR REPLACE INTO concept_unlock_state (
                        learner_id, concept_id, domain, concept_name, unlock_status,
                        mastery_score, promotion_confidence, prerequisites_met,
                        unlocked_at, evidence_json, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
                    """,
                    (
                        learner_id,
                        concept_id,
                        domain,
                        concept_name,
                        "mastered" if concept_completed else "current",
                        max(previous_mastery, score),
                        max(previous_confidence, 1.0 if difficulty_passed else 0.4),
                        existing_unlock["unlocked_at"] if existing_unlock and existing_unlock["unlocked_at"] else now,
                        json.dumps(existing_evidence),
                        now,
                    ),
                )
                rows["concept_unlock_state"] = True
                next_concept_id = recommended.get("next_concept_id")
                if concept_completed and next_concept_id:
                    next_concept_name = str(recommended.get("next_concept_name") or next_concept_id)
                    try:
                        from tutor.api.integration_routes import _concepts

                        for node in _concepts(domain or "python"):
                            if str(node.get("id")) == str(next_concept_id):
                                next_concept_name = str(node.get("name") or next_concept_name)
                                break
                    except Exception:
                        pass
                    next_evidence = {"source": "hard_pass_unlock", "current_difficulty": "easy", "unlocked_after": concept_id}
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO concept_unlock_state (
                            learner_id, concept_id, domain, concept_name, unlock_status,
                            mastery_score, promotion_confidence, prerequisites_met,
                            unlocked_at, evidence_json, updated_at
                        )
                        VALUES (?, ?, ?, ?, 'current', 0.0, 1.0, 1, ?, ?, ?)
                        """,
                        (learner_id, str(next_concept_id), domain, next_concept_name, now, json.dumps(next_evidence), now),
                    )
            conn.execute(
                """
                UPDATE learner_profile
                SET current_concept_id = ?, current_concept_name = ?, current_difficulty = ?, updated_at = ?
                WHERE learner_id = ?
                """,
                (
                    str(recommended.get("next_concept_id") or concept_id) if concept_completed and recommended.get("next_concept_id") else concept_id,
                    str(recommended.get("next_concept_name") or recommended.get("next_concept_id") or concept_name) if concept_completed and recommended.get("next_concept_id") else concept_name,
                    "easy" if concept_completed and recommended.get("next_concept_id") else next_difficulty if difficulty_passed and not concept_completed else difficulty,
                    now,
                    learner_id,
                ),
            )
            rows["learner_profile"] = True
            conn.commit()
        finally:
            conn.close()
        return {"status": "success", "tables": rows}
    except Exception as exc:
        return {"status": "warning", "reason": f"{type(exc).__name__}: {exc}", "tables": rows}


def _payload_dict(payload: SubmitAnswerRequest) -> dict:
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    return payload.dict()


def _safe_json_loads(value):
    if value in (None, ""):
        return {}
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(str(value))
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def _merged_knowledge_state_json(
    existing_state_json,
    *,
    subject: str,
    concept_id: str,
    concept_name: str,
    mastery: float,
    difficulty: str,
    updated_at: str,
) -> str:
    state = _safe_json_loads(existing_state_json)
    subjects = state.get("subjects")
    if not isinstance(subjects, dict):
        subjects = {}
    subject_state = subjects.get(subject)
    if not isinstance(subject_state, dict):
        subject_state = {}
    concepts = subject_state.get("concepts")
    if not isinstance(concepts, dict):
        concepts = {}
    prior_concept_state = concepts.get(concept_id)
    if not isinstance(prior_concept_state, dict):
        prior_concept_state = {}
    prior_mastery = float(prior_concept_state.get("mastery") or 0.0)
    concept_state = {
        **prior_concept_state,
        "concept_id": concept_id,
        "concept_name": concept_name,
        "mastery": max(prior_mastery, float(mastery or 0.0)),
        "last_score": float(mastery or 0.0),
        "difficulty": difficulty,
        "updated_at": updated_at,
        "updated_from": "answer_submit",
    }
    concepts[concept_id] = concept_state
    subject_state.update(
        {
            "subject": subject,
            "current_concept_id": concept_id,
            "current_difficulty": difficulty,
            "concepts": concepts,
            "updated_at": updated_at,
        }
    )
    subjects[subject] = subject_state
    state.update(
        {
            "concept_id": concept_id,
            "concept_name": concept_name,
            "mastery": float(mastery or 0.0),
            "difficulty": difficulty,
            "subject": subject,
            "updated_from": "answer_submit",
            "updated_at": updated_at,
            "subjects": subjects,
        }
    )
    return json.dumps(state)


def _insert_available(conn, table_name: str, values: dict) -> None:
    available = {key: value for key, value in values.items() if column_exists(conn, table_name, key)}
    if not available:
        return
    columns = list(available)
    placeholders = ", ".join("?" for _ in columns)
    column_sql = ", ".join(columns)
    conn.execute(
        f"INSERT INTO {table_name} ({column_sql}) VALUES ({placeholders})",
        [available[column] for column in columns],
    )
