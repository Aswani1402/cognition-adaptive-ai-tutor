from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

JSON_DIR = ROOT / "evaluation_outputs" / "json"
REPORT_DIR = ROOT / "evaluation_outputs" / "reports"

REQUIRED_KEYS = [
    "lesson",
    "question",
    "evaluation",
    "feedback",
    "next_activity",
    "mastery",
    "behaviour",
    "xai",
    "reward",
    "memory",
    "progress",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_sample_full_output() -> dict[str, Any]:
    from tutor.api.concept_content_resolver import assessment_payload, build_lesson_payload

    lesson = build_lesson_payload("Python", "P1", difficulty="easy", view="definition_view")
    assessment = assessment_payload("Python", "P1", difficulty="easy")
    question = assessment["questions"][0] if assessment.get("questions") else {}
    evaluation = {
        "status": "success",
        "overall_score": 1.0,
        "verdict": "ready_to_progress",
        "feedback_summary": "Correct. Continue with practice.",
        "results": [
            {
                "assessment_type": question.get("question_type", "mcq"),
                "score": 1.0,
                "feedback": "Correct.",
            }
        ],
    }
    return {
        "learner_id": "final_review_demo_learner",
        "demo_summary": {
            "final_concept": "1",
            "final_concept_name": "Variables",
            "final_strategy": "practice",
            "final_difficulty": "easy",
            "evaluation_score": 1.0,
            "next_activity": "practice_medium",
            "progression_action": "same_level_change_view_or_practice",
            "teaching_view": "definition_view",
            "frontend_selected_view": "definition_view",
            "assessment_question_count": len(assessment.get("questions", [])),
            "assessment_frontend_ready": True,
            "assessment_types": [q.get("question_type") for q in assessment.get("questions", [])],
            "reward_xp_awarded": 10,
            "notebook_summary": "Variables reviewed successfully.",
        },
        "demo_output": {
            "current_teaching_content": {
                "concept_id": "1",
                "concept_name": "Variables",
                "difficulty": "easy",
                "title": lesson.get("teaching_content", {}).get("title"),
                "content": lesson.get("adaptive_explanation"),
                "items": [
                    {
                        "content_id": "lesson-variables",
                        "content_type": "definition_view",
                        "strategy": "practice",
                        "difficulty": "easy",
                        "title": lesson.get("teaching_content", {}).get("title"),
                        "body": lesson.get("adaptive_explanation"),
                        "bullets": lesson.get("keyPoints", []),
                    }
                ],
                "available_views": lesson.get("available_views", []),
                "fallback_views": lesson.get("fallback_views", []),
            },
            "assessment": {
                **assessment,
                "status": "success",
                "frontend_ready": True,
                "frontend_components_used": sorted(
                    {q.get("frontend_component") for q in assessment.get("questions", []) if q.get("frontend_component")}
                ),
            },
            "evaluation": evaluation,
            "xai": {
                "status": "success",
                "data": {
                    "reason": "Selected practice because mastery and evaluation evidence are sufficient for another safe activity.",
                    "evidence": {
                        "feature_contributions": {
                            "top_factors": [
                                {"feature": "mastery_score", "contribution": 0.4},
                                {"feature": "fused_score", "contribution": 0.4},
                            ]
                        }
                    },
                },
            },
        },
        "learner_notebook_memory_output": {
            "notebook_summary": "Variables reviewed successfully.",
            "revision_plan": [{"task_type": "mixed_review", "concept_id": "1"}],
            "next_practice_queue": [{"concept_id": "1", "practice_type": "mcq"}],
            "weak_assessment_types": [],
            "strengths": ["mcq"],
        },
        "progression_reward_output": {
            "status": "success",
            "progression_result": {
                "learner_id": "final_review_demo_learner",
                "current_concept_id": "1",
                "current_concept": "Variables",
                "progression_action": "same_level_change_view_or_practice",
                "promotion_confidence": 0.82,
            },
            "reward_state": {
                "xp_awarded": 10,
                "streak_updated": True,
                "reward_reason": "encouragement",
            },
            "celebration": {"show": True, "message": "Continue practice."},
            "frontend_contract": {
                "show_celebration_modal": True,
                "show_xp_popup": True,
                "update_streak_widget": True,
            },
        },
        "policy_output": {
            "status": "success",
            "data": {
                "decision_type": "safe_policy_bridge",
                "strategy": "practice",
                "difficulty": "medium",
                "safe_mask_applied": True,
                "final_safe_action": "practice_medium",
            },
        },
    }


def compact_contract(frontend_response: dict[str, Any]) -> dict[str, Any]:
    assessment = frontend_response.get("assessment") or {}
    questions = assessment.get("questions") or []
    return {
        "lesson": frontend_response.get("teaching"),
        "question": questions[0] if questions else None,
        "evaluation": frontend_response.get("evaluation") or frontend_response.get("structured_evaluation"),
        "feedback": {
            "message": (frontend_response.get("evaluation") or {}).get("feedback_summary"),
        },
        "next_activity": (frontend_response.get("summary") or {}).get("next_activity")
        or (frontend_response.get("teaching_plan") or {}).get("next_activity"),
        "mastery": {
            "value": (frontend_response.get("summary") or {}).get("evaluation_score"),
            "source": "frontend_contract_demo_summary",
        },
        "behaviour": {
            "label": "low_risk",
            "source": "frontend_contract_sample",
        },
        "xai": frontend_response.get("xai"),
        "reward": frontend_response.get("reward_state") or frontend_response.get("persistent_reward_state"),
        "memory": frontend_response.get("notebook_memory"),
        "progress": frontend_response.get("progression_result"),
    }


def main() -> None:
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        from tutor.system.frontend_response_builder import build_frontend_response

        frontend_response = build_frontend_response(build_sample_full_output())
        learner_contract = compact_contract(frontend_response)
        errors = [
            key
            for key in REQUIRED_KEYS
            if key not in learner_contract or learner_contract.get(key) in (None, {}, [])
        ]
        status = "success" if not errors else "warning"
        reason = "All required learner-facing contract keys are present." if not errors else f"Missing/empty keys: {errors}"
    except Exception as exc:
        frontend_response = None
        learner_contract = {key: None for key in REQUIRED_KEYS}
        errors = REQUIRED_KEYS
        status = "error"
        reason = f"Frontend response builder failed: {type(exc).__name__}: {exc}"

    payload = {
        "status": status,
        "generated_at": now_iso(),
        "required_keys": REQUIRED_KEYS,
        "missing_or_empty": errors,
        "passed": not errors,
        "reason": reason,
        "learner_facing_response": learner_contract,
        "raw_frontend_response_keys": sorted(frontend_response.keys()) if isinstance(frontend_response, dict) else [],
    }
    json_path = JSON_DIR / "final_frontend_response_contract_check.json"
    report_path = REPORT_DIR / "final_frontend_response_contract_check_report.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Final Frontend Response Contract Check Report",
        "",
        f"Generated at: `{payload['generated_at']}`",
        "",
        f"- Status: `{payload['status']}`",
        f"- Passed: `{payload['passed']}`",
        f"- Reason: {payload['reason']}",
        "",
        "| Required key | Present and non-empty |",
        "|---|---:|",
    ]
    for key in REQUIRED_KEYS:
        lines.append(f"| {key} | {key not in errors} |")
    lines.extend(
        [
            "",
            "## Limitation",
            "",
            "- This is a backend contract simulation using the response builder; it does not run the frontend UI.",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("FINAL FRONTEND RESPONSE CONTRACT CHECK")
    print(f"status: {payload['status']}")
    print(f"passed: {payload['passed']}")
    print(f"json: {json_path}")
    print(f"report: {report_path}")


if __name__ == "__main__":
    main()
