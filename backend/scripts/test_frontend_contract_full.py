from __future__ import annotations

import sys
from typing import Any

from tutor.system.frontend_response_builder import (
    QUESTION_COMPONENTS,
    TEACHING_COMPONENTS,
    build_frontend_response,
)


PATCH_TARGETS = [
    "tutor/system/frontend_response_builder.py",
    "docs/frontend_api_contract_cognitutor_lm.md",
]

REQUIRED_TOP_LEVEL_FIELDS = [
    "status",
    "learner_id",
    "concept",
    "teaching",
    "assessment",
    "revision",
    "tools",
    "reward",
    "progress",
    "xai",
    "cognitutor_lm",
    "frontend_contract",
    "learner_memory",
]

REQUIRED_CONCEPT_FIELDS = [
    "concept_id",
    "concept_name",
    "domain",
    "difficulty",
]

REQUIRED_TEACHING_FIELDS = [
    "selected_view",
    "component",
    "card",
]

REQUIRED_ASSESSMENT_FIELDS = [
    "questions",
    "question_count",
    "components",
    "supported_question_types",
    "puzzle_questions",
    "supported_interactive_types",
]

REQUIRED_REVISION_FIELDS = [
    "notebook_summary",
    "flashcards",
    "mindmap",
    "revision_summary",
]

REQUIRED_TOOLS_FIELDS = [
    "code_runner_enabled",
    "doubt_handler_enabled",
    "returning_learner_available",
]

REQUIRED_FRONTEND_CONTRACT_FLAGS = [
    "show_teaching_card",
    "show_question_one_at_a_time",
    "show_flashcards_tab",
    "show_mindmap_tab",
    "show_doubt_panel",
    "show_code_runner",
    "show_xai_panel",
    "show_reward_widget",
    "show_puzzle_panel",
    "show_returning_learner_memory",
]

REQUIRED_LEARNER_MEMORY_FIELDS = [
    "status",
    "source",
    "weak_concepts",
    "weak_question_types",
    "recommended_revision_views",
    "next_recommended_action",
]

REQUIRED_TEACHING_VIEW_MAPPINGS = [
    "definition_view",
    "simple_example_view",
    "step_by_step_view",
    "code_view",
    "analogy_view",
    "misconception_view",
    "debug_view",
    "output_prediction_view",
    "transfer_view",
    "challenge_view",
    "revision_summary_view",
    "flashcard_view",
    "mindmap_view",
]

REQUIRED_ASSESSMENT_TYPE_MAPPINGS = [
    "mcq",
    "debug_task",
    "output_prediction",
    "transfer_question",
    "challenge_question",
    "explanation_check",
]

REQUIRED_PUZZLE_TYPE_MAPPINGS = [
    "fill_blank",
    "arrange_steps",
    "match_pairs",
    "drag_order",
    "code_puzzle",
    "syntax_completion",
]


def _question(question_type: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    question = {
        "question_id": f"q_{question_type}",
        "assessment_type": question_type,
        "question_type": question_type,
        "concept_id": "py_variables",
        "concept_name": "Variables",
        "domain": "Python",
        "prompt": f"Validate {question_type}.",
        "expected_answer": "expected",
        "frontend_component": QUESTION_COMPONENTS.get(question_type, "QuestionCard"),
        "metadata": {"render_mode": question_type},
    }
    if extra:
        question.update(extra)
    return question


def _build_full_output() -> dict[str, Any]:
    all_question_types = (
        REQUIRED_ASSESSMENT_TYPE_MAPPINGS + REQUIRED_PUZZLE_TYPE_MAPPINGS
    )
    questions = [
        _question("mcq", {"options": ["A", "B"], "correct_option_index": 0}),
        _question("debug_task", {"metadata": {"render_mode": "code_debug"}}),
        _question(
            "output_prediction",
            {"metadata": {"render_mode": "code_output_prediction"}},
        ),
        _question("transfer_question"),
        _question("challenge_question"),
        _question("explanation_check"),
        _question(
            "fill_blank",
            {
                "text_with_blank": "A variable stores ____.",
                "answer": "a value",
                "hint": "Think storage.",
                "metadata": {
                    "render_mode": "fill_blank",
                    "text_with_blank": "A variable stores ____.",
                    "answer": "a value",
                    "hint": "Think storage.",
                },
            },
        ),
        _question(
            "arrange_steps",
            {
                "steps": [{"id": "s1", "text": "Assign"}, {"id": "s2", "text": "Print"}],
                "correct_order": ["s1", "s2"],
            },
        ),
        _question(
            "match_pairs",
            {
                "left_items": [{"id": "l1", "text": "name"}],
                "right_items": [{"id": "r1", "text": "variable"}],
                "correct_pairs": [["l1", "r1"]],
            },
        ),
        _question(
            "drag_order",
            {
                "items": [{"id": "i1", "text": "name = 'Ada'"}],
                "correct_order": ["i1"],
            },
        ),
        _question(
            "code_puzzle",
            {
                "starter_code": "name = ____",
                "answer": "'Ada'",
                "expected_output": "Ada",
            },
        ),
        _question(
            "syntax_completion",
            {
                "metadata": {
                    "render_mode": "code_fill",
                    "incomplete_code": "print(____)",
                    "missing_part": "name",
                }
            },
        ),
    ]

    return {
        "status": "success",
        "learner_id": "kp_contract_learner",
        "timestamp": "2026-05-09T00:00:00Z",
        "demo_summary": {
            "frontend_selected_view": "definition_view",
            "notebook_summary": "Variables need short revision.",
            "revision_summary": "Review assignment and naming rules.",
            "promotion_confidence": 0.72,
            "promotion_allowed": False,
            "level_up_allowed": False,
            "concept_cleared": False,
            "progression_action": "practice_same_concept",
        },
        "current_teaching_content": {
            "concept_id": "py_variables",
            "concept_name": "Variables",
            "domain": "Python",
            "difficulty": "easy",
            "title": "Variables",
            "content": "A variable is a name bound to a value.",
            "available_views": REQUIRED_TEACHING_VIEW_MAPPINGS,
            "fallback_views": ["simple_example_view", "step_by_step_view"],
            "flashcards": [
                {"front": "What is a variable?", "back": "A named value."}
            ],
            "mindmap": {
                "nodes": [{"id": "variables", "label": "Variables"}],
                "edges": [],
            },
        },
        "frontend_teaching_view_output": {
            "selected_teaching_view": "definition_view",
            "selected_view": {
                "title": "Variables",
                "content": "Variables let code reuse values.",
                "display_type": "teaching_card",
            },
            "available_view_names": REQUIRED_TEACHING_VIEW_MAPPINGS,
            "fallback_view_names": ["simple_example_view", "step_by_step_view"],
        },
        "assessment": {
            "status": "success",
            "concept_id": "py_variables",
            "concept_name": "Variables",
            "difficulty": "easy",
            "question_count": len(questions),
            "frontend_ready": True,
            "supported_question_types": all_question_types,
            "supported_interactive_types": REQUIRED_PUZZLE_TYPE_MAPPINGS,
            "frontend_component_map": QUESTION_COMPONENTS,
            "questions": questions,
        },
        "learner_notebook_memory_output": {
            "notebook_summary": "Variables need short revision.",
            "revision_summary": "Review assignment and naming rules.",
        },
        "cognitutor_lm_output": {
            "status": "success",
            "mode": "optional_connector_demo",
            "source": "cognitutor_lm_connector",
            "adaptive_session": {
                "selected_view": "definition_view",
                "assessment_count": len(questions),
            },
        },
        "xai": {
            "data": {
                "reason": "Definition view selected because mastery is still forming.",
                "evidence": {
                    "source_evidence": [
                        {
                            "source": "local_rag",
                            "section": "variables_definition",
                        }
                    ],
                    "feature_contributions": {
                        "top_factors": ["mastery_need", "recent_errors"]
                    },
                },
            }
        },
        "progression_reward_output": {
            "progression_result": {
                "progression_action": "practice_same_concept",
                "promotion_allowed": False,
                "level_up_allowed": False,
                "concept_cleared": False,
                "promotion_confidence": 0.72,
            },
            "promotion_confidence_output": {"confidence": 0.72},
            "reward_state": {"xp_awarded": 5, "reason": "contract_validation"},
            "celebration": {"type": "small", "message": "Keep practicing."},
            "frontend_contract": {},
        },
        "reward_persistence_output": {
            "status": "success",
            "mode": "dry_run",
            "total_xp": 100,
            "daily_xp": 5,
            "weekly_xp": 20,
            "current_level": 2,
            "current_streak": 3,
            "longest_streak": 4,
        },
    }


def _missing_keys(payload: dict[str, Any], keys: list[str]) -> list[str]:
    return [key for key in keys if key not in payload]


def _missing_truthy_keys(payload: dict[str, Any], keys: list[str]) -> list[str]:
    return [key for key in keys if payload.get(key) in (None, "", [], {})]


def _validate_contract(response: dict[str, Any]) -> dict[str, list[str]]:
    teaching = response.get("teaching", {})
    assessment = response.get("assessment", {})

    missing_teaching_fields = _missing_truthy_keys(
        teaching,
        REQUIRED_TEACHING_FIELDS,
    )
    if "available_views" not in teaching and "fallback_views" not in teaching:
        missing_teaching_fields.append("available_views or fallback_views")

    supported_question_types = set(assessment.get("supported_question_types", []))
    supported_interactive_types = set(assessment.get("supported_interactive_types", []))
    puzzle_question_types = {
        question.get("question_type")
        for question in assessment.get("puzzle_questions", [])
        if isinstance(question, dict)
    }

    missing_assessment_fields = _missing_keys(
        assessment,
        REQUIRED_ASSESSMENT_FIELDS,
    )
    missing_assessment_fields.extend(
        f"supported_question_types.{question_type}"
        for question_type in REQUIRED_ASSESSMENT_TYPE_MAPPINGS
        if question_type not in supported_question_types
    )
    missing_assessment_fields.extend(
        f"supported_interactive_types.{question_type}"
        for question_type in REQUIRED_PUZZLE_TYPE_MAPPINGS
        if question_type not in supported_interactive_types
    )
    missing_assessment_fields.extend(
        f"puzzle_questions.{question_type}"
        for question_type in REQUIRED_PUZZLE_TYPE_MAPPINGS
        if question_type != "syntax_completion" and question_type not in puzzle_question_types
    )

    frontend_component_map = assessment.get("frontend_component_map", {})
    missing_component_mappings = [
        f"teaching.{view_name}"
        for view_name in REQUIRED_TEACHING_VIEW_MAPPINGS
        if view_name not in TEACHING_COMPONENTS
    ]
    missing_component_mappings.extend(
        f"assessment.{question_type}"
        for question_type in REQUIRED_ASSESSMENT_TYPE_MAPPINGS
        if question_type not in frontend_component_map
        and question_type not in QUESTION_COMPONENTS
    )
    missing_component_mappings.extend(
        f"puzzle.{question_type}"
        for question_type in REQUIRED_PUZZLE_TYPE_MAPPINGS
        if question_type not in frontend_component_map
        and question_type not in QUESTION_COMPONENTS
    )

    return {
        "missing_top_level_fields": _missing_keys(response, REQUIRED_TOP_LEVEL_FIELDS),
        "missing_concept_fields": _missing_truthy_keys(
            response.get("concept", {}),
            REQUIRED_CONCEPT_FIELDS,
        ),
        "missing_teaching_fields": missing_teaching_fields,
        "missing_assessment_fields": missing_assessment_fields,
        "missing_revision_fields": _missing_truthy_keys(
            response.get("revision", {}),
            REQUIRED_REVISION_FIELDS,
        ),
        "missing_tool_fields": _missing_keys(
            response.get("tools", {}),
            REQUIRED_TOOLS_FIELDS,
        ),
        "missing_frontend_contract_flags": _missing_keys(
            response.get("frontend_contract", {}),
            REQUIRED_FRONTEND_CONTRACT_FLAGS,
        ),
        "missing_learner_memory_fields": _missing_keys(
            response.get("learner_memory", {}),
            REQUIRED_LEARNER_MEMORY_FIELDS,
        ),
        "missing_component_mappings": missing_component_mappings,
    }


def _print_summary(missing: dict[str, list[str]]) -> None:
    has_missing = any(missing.values())
    status = "FAIL" if has_missing else "PASS"

    print(f"status: {status}")
    for label in [
        "missing_top_level_fields",
        "missing_concept_fields",
        "missing_teaching_fields",
        "missing_assessment_fields",
        "missing_revision_fields",
        "missing_tool_fields",
        "missing_frontend_contract_flags",
        "missing_learner_memory_fields",
        "missing_component_mappings",
    ]:
        print(f"{label}: {missing[label]}")

    if has_missing:
        print("likely_needs_patching:")
        for path in PATCH_TARGETS:
            print(f"- {path}")

    print(f"final_result: {status}")


def main() -> None:
    response = build_frontend_response(_build_full_output())
    missing = _validate_contract(response)
    _print_summary(missing)

    if any(missing.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
