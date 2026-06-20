from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tutor.agents.orchestration_trace import FINAL_FLOW, build_agentic_orchestration_trace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_AGENTS = {
    "TeachingAgent",
    "AssessmentAgent",
    "EvaluatorAgent",
    "DiagnosisAgent",
    "LearnerStateAgent",
    "DecisionPolicyAgent",
    "MemoryRevisionAgent",
    "RAGGroundingAgent",
    "XAIReflectionAgent",
    "RewardProgressionAgent",
}


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _sample_pipeline_output() -> dict:
    return {
        "learner_id": "14",
        "demo_summary": {
            "final_concept": "1",
            "adaptive_path_resolved_concept_id": "1",
            "adaptive_path_resolved_concept_name": "Variables",
            "teaching_view": "revision_view",
            "frontend_selected_view": "revision_view",
            "assessment_types": ["mcq", "output_prediction", "debug"],
            "assessment_question_count": 3,
            "assessment_frontend_components": ["MCQQuestionCard", "OutputPredictionCard"],
            "fused_score": 0.32,
            "fused_label": "needs_reteaching",
            "weakest_skill": "output_prediction",
            "dominant_mistake_type": "wrong_output",
            "mistake_type_counts": {"wrong_output": 1},
            "high_severity_mistake_count": 1,
            "predicted_mastery_last": 0.6,
            "behavior_label": "stable",
            "behavior_risk": 0.24,
            "behavior_risk_label": "low_risk",
            "review_queue": ["1"],
            "adaptive_path_selected": "1",
            "adaptive_path_original_selected": "31",
            "adaptive_path_validation_status": "fallback",
            "adaptive_path_fallback_used": True,
            "promotion_allowed": False,
            "progression_action": "review",
            "model_comparison_status": "comparison_only_not_used_for_final_decision",
            "xai_top_factors": ["evaluation_need", "mastery_need"],
            "promotion_confidence": 0.39,
            "reward_xp_awarded": 5,
        },
        "evidence_aware_teaching_strategy_output": {
            "difficulty": "medium",
            "content_focus": "revision",
            "reason": "Review due and evaluation fusion needs reteaching.",
        },
        "frontend_teaching_view_output": {
            "selected_view": {"title": "Variables Review", "display_type": "revision"},
        },
        "assessment_output": {"frontend_ready": True},
        "knowledge_state": {"status": "success", "data": {"data": {"schema_version": "kt_v2", "source": "fallback_cumulative"}}},
        "behaviour_state": {"status": "success", "data": {"behavior_label": "stable", "behavior_risk": 0.24}},
        "forgetting_state": {"data": {"review_queue": ["1"]}},
        "adaptive_path_validation_output": {"fallback_used": True, "reason": "Domain mismatch fallback."},
        "learner_notebook_memory_output": {"notebook_summary": "Weak output prediction.", "next_practice_queue": []},
        "reflection_output": {"status": "success", "reflection": {"diagnosis": "Needs tracing practice."}},
        "progression_reward_output": {"reward_state": {"xp_awarded": 5}},
    }


def _extract_json(stdout: str) -> dict:
    start = stdout.find("{")
    end = stdout.rfind("}")
    if start == -1 or end == -1:
        return {}
    try:
        return json.loads(stdout[start : end + 1])
    except Exception:
        return {}


def test_sample_trace() -> None:
    trace = build_agentic_orchestration_trace(_sample_pipeline_output())
    _assert(trace["status"] == "success", "trace status should be success")
    _assert(trace["final_flow"] == FINAL_FLOW, "final flow mismatch")
    agents = {step["agent"] for step in trace["trace_steps"]}
    _assert(REQUIRED_AGENTS.issubset(agents), f"missing agents: {REQUIRED_AGENTS - agents}")
    _assert(len(trace["frontend_trace_cards"]) == len(trace["trace_steps"]), "frontend cards missing")


def test_missing_optional_fields() -> None:
    trace = build_agentic_orchestration_trace({"learner_id": "14", "demo_summary": {}})
    _assert(trace["status"] == "success", "missing optional fields should not crash")
    _assert(len(trace["trace_steps"]) == 10, "trace should still include all stages")


def test_integrated_pipeline_trace() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "tutor.system.run_integrated_tutor_once",
            "--learner_id",
            "14",
            "--reward_dry_run",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )
    _assert(completed.returncode == 0, "integrated pipeline failed")
    payload = _extract_json(completed.stdout)
    _assert(bool(payload), "integrated pipeline JSON payload could not be parsed")
    trace = build_agentic_orchestration_trace(payload)
    agents = {step["agent"] for step in trace["trace_steps"]}
    _assert(REQUIRED_AGENTS.issubset(agents), "integrated trace missing required agents")
    _assert(trace["frontend_trace_cards"], "integrated trace frontend cards missing")


def main() -> None:
    test_sample_trace()
    test_missing_optional_fields()
    test_integrated_pipeline_trace()
    print("STATUS: success")
    print("MODULE: agentic_orchestration_trace_test")


if __name__ == "__main__":
    main()
