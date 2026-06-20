from tutor.assessment.expanded_assessment_generator import attach_expanded_questions_to_bundle
from tutor.assessment.structured_question_types import FRONTEND_COMPONENT_MAP, PUZZLE_QUESTION_TYPES
from tutor.system.frontend_response_builder import build_frontend_response
from tutor.system.run_integrated_tutor_once import run_integrated_tutor_once


def _assert_puzzle_contract() -> None:
    concept_resource = {
        "concept_id": "1",
        "concept_name": "Variables",
        "domain": "Python",
        "definition": "A variable is a name linked to a value.",
        "key_points": [
            "Variables store values.",
            "Variable names should follow naming rules.",
        ],
    }
    assessment = attach_expanded_questions_to_bundle(
        assessment_bundle={
            "status": "success",
            "concept_id": "1",
            "concept_name": "Variables",
            "difficulty": "medium",
            "questions": [],
        },
        concept_resource=concept_resource,
        requested_types=PUZZLE_QUESTION_TYPES,
        difficulty="medium",
        max_extra_questions=5,
    )
    frontend_output = build_frontend_response(
        {
            "status": "success",
            "learner_id": "test_puzzle_learner",
            "current_teaching_content": concept_resource,
            "assessment": assessment,
        }
    )

    expected_mapping = {
        "fill_blank": "FillBlankCard",
        "arrange_steps": "ArrangeStepsCard",
        "match_pairs": "MatchPairsCard",
        "drag_order": "DragOrderCard",
        "code_puzzle": "CodePuzzleCard",
    }
    supported = set(frontend_output["assessment"]["supported_interactive_types"])
    puzzle_questions = frontend_output["assessment"]["puzzle_questions"]
    puzzle_types = {question["question_type"] for question in puzzle_questions}

    assert set(PUZZLE_QUESTION_TYPES).issubset(supported)
    assert set(PUZZLE_QUESTION_TYPES).issubset(puzzle_types)
    assert frontend_output["frontend_contract"]["show_puzzle_panel"] is True
    for question_type, component_name in expected_mapping.items():
        assert FRONTEND_COMPONENT_MAP[question_type] == component_name
        assert frontend_output["assessment"]["frontend_component_map"][question_type] == component_name

    fill_blank = next(q for q in puzzle_questions if q["question_type"] == "fill_blank")
    assert fill_blank["text_with_blank"]
    assert fill_blank["answer"]
    assert "hint" in fill_blank

    arrange_steps = next(q for q in puzzle_questions if q["question_type"] == "arrange_steps")
    assert arrange_steps["steps"]
    assert arrange_steps["correct_order"]

    match_pairs = next(q for q in puzzle_questions if q["question_type"] == "match_pairs")
    assert match_pairs["left_items"]
    assert match_pairs["right_items"]
    assert match_pairs["correct_pairs"]

    drag_order = next(q for q in puzzle_questions if q["question_type"] == "drag_order")
    assert drag_order["items"]
    assert drag_order["correct_order"]

    code_puzzle = next(q for q in puzzle_questions if q["question_type"] == "code_puzzle")
    assert code_puzzle["starter_code"]
    assert code_puzzle["answer"]
    assert code_puzzle["expected_output"]


def main() -> None:
    full_output = run_integrated_tutor_once(
        learner_id="14",
        reward_dry_run=True,
    )

    frontend_output = build_frontend_response(full_output)

    assert frontend_output["status"] == "success"
    assert frontend_output["summary"]["teaching_view"]
    assert frontend_output["summary"]["assessment_types"]
    assert frontend_output["teaching_plan"]["teaching_view"]
    assert frontend_output["teaching_plan"]["assessment_types"]
    assert frontend_output["logging"]["teaching_strategy_training_log"]["status"] == "success"
    assert frontend_output["concept"]["concept_name"] == "Variables"
    assert frontend_output["teaching"]["card"]
    assert frontend_output["teaching_card"]
    assert frontend_output["assessment"]["questions"]
    assert frontend_output["assessment_questions"]
    assert frontend_output["revision"]["flashcards"]
    assert frontend_output["revision"]["mindmap"]
    assert frontend_output["revision"]["notebook_summary"]
    assert frontend_output["tools"]["code_runner_enabled"] is True
    assert frontend_output["tools"]["doubt_handler_enabled"] is True
    assert frontend_output["tools"]["production_memory_enabled"] in {True, False}
    assert frontend_output["cognitutor_lm"]["status"] in {"success", "unavailable", "error"}
    assert frontend_output["frontend_contract"]["show_teaching_card"] is True
    assert frontend_output["frontend_contract"]["show_question_one_at_a_time"] is True
    assert frontend_output["frontend_contract"]["show_puzzle_panel"] is True
    assert frontend_output["frontend_contract"]["show_returning_learner_memory"] is True
    assert "learner_memory" in frontend_output
    assert frontend_output["learner_memory"]["status"] in {"success", "unavailable"}
    assert frontend_output["learner_memory"]["source"]
    assert "weak_concepts" in frontend_output["learner_memory"]
    assert "weak_question_types" in frontend_output["learner_memory"]
    assert "recommended_revision_views" in frontend_output["learner_memory"]
    assert "next_recommended_action" in frontend_output["learner_memory"]
    assert "returning_learner_context" in frontend_output["revision"]
    assert set(PUZZLE_QUESTION_TYPES).issubset(
        set(frontend_output["assessment"]["supported_interactive_types"])
    )
    assert "mcq" in frontend_output["assessment"]["supported_question_types"]
    assert "debug" in frontend_output["assessment"]["supported_question_types"]
    assert "output_prediction" in frontend_output["assessment"]["supported_question_types"]
    assert "transfer" in frontend_output["assessment"]["supported_question_types"]
    assert "challenge" in frontend_output["assessment"]["supported_question_types"]
    assert "short_explanation" in frontend_output["assessment"]["supported_question_types"]
    _assert_puzzle_contract()

    print("compact frontend response test success")
    print("teaching_view:", frontend_output["summary"]["teaching_view"])
    print("assessment_types:", frontend_output["summary"]["assessment_types"])
    print(
        "teaching_strategy_training_log_output:",
        frontend_output["logging"]["teaching_strategy_training_log"]["status"],
    )

    progression_reward_output = frontend_output.get("progression_reward_output", {})
    model_output = progression_reward_output.get("model_comparison_output", {})

    print("model_comparison_status:", progression_reward_output.get("model_comparison_status"))
    print("model_comparison_output:", model_output.get("status"))
    print("model_progression_action:", model_output.get("model_progression_action"))

    persistent_reward_state = frontend_output.get("persistent_reward_state", {})

    print("reward_persistence_status:", persistent_reward_state.get("status"))
    print("reward_persistence_mode:", persistent_reward_state.get("mode"))
    print("event_logged:", persistent_reward_state.get("event_logged"))
    print("xp_awarded:", persistent_reward_state.get("xp_awarded"))
    print("total_xp:", persistent_reward_state.get("total_xp"))
    print("daily_xp:", persistent_reward_state.get("daily_xp"))
    print("weekly_xp:", persistent_reward_state.get("weekly_xp"))
    print("current_level:", persistent_reward_state.get("current_level"))
    print("last_daily_reset_date:", persistent_reward_state.get("last_daily_reset_date"))
    print("last_weekly_reset_date:", persistent_reward_state.get("last_weekly_reset_date"))
    print("current_streak:", persistent_reward_state.get("current_streak"))
    print("longest_streak:", persistent_reward_state.get("longest_streak"))


    mistake_analysis = frontend_output.get("mistake_analysis", {})

    print("mistake_analysis_status:", mistake_analysis.get("status"))
    print("dominant_mistake_type:", mistake_analysis.get("dominant_mistake_type"))
    print("mistake_type_counts:", mistake_analysis.get("mistake_type_counts"))
    print("high_severity_mistake_count:", mistake_analysis.get("high_severity_count"))

    rubric_evaluation = frontend_output.get("rubric_evaluation", {})

    print("rubric_evaluation_status:", rubric_evaluation.get("status"))
    print("rubric_mode:", rubric_evaluation.get("mode"))
    print("rubric_overall_score:", rubric_evaluation.get("overall_score"))
    print("rubric_verdict:", rubric_evaluation.get("verdict"))
    print("rubric_weak_assessment_types:", rubric_evaluation.get("weak_assessment_types"))

    debug_evaluation = frontend_output.get("debug_evaluation", {})

    print("debug_evaluation_status:", debug_evaluation.get("status"))
    print("debug_evaluation_mode:", debug_evaluation.get("mode"))
    print("debug_evaluation_score:", debug_evaluation.get("overall_score"))
    print("debug_evaluation_label:", debug_evaluation.get("quality_label"))
    print("debug_question_count:", debug_evaluation.get("debug_question_count"))


    output_prediction_evaluation = frontend_output.get(
        "output_prediction_evaluation", {}
    )

    print(
        "output_prediction_evaluation_status:",
        output_prediction_evaluation.get("status"),
    )
    print(
        "output_prediction_evaluation_mode:",
        output_prediction_evaluation.get("mode"),
    )
    print(
        "output_prediction_evaluation_score:",
        output_prediction_evaluation.get("overall_score"),
    )
    print(
        "output_prediction_evaluation_label:",
        output_prediction_evaluation.get("quality_label"),
    )
    print(
        "dominant_output_error_type:",
        output_prediction_evaluation.get("dominant_output_error_type"),
    )
    print(
        "output_prediction_question_count:",
        output_prediction_evaluation.get("output_prediction_question_count"),
    )

    evaluation_fusion = frontend_output.get("evaluation_fusion", {})

    print("evaluation_fusion_status:", evaluation_fusion.get("status"))
    print("evaluation_fusion_mode:", evaluation_fusion.get("mode"))
    print("fused_score:", evaluation_fusion.get("fused_score"))
    print("fused_label:", evaluation_fusion.get("fused_label"))
    print(
        "recommended_learning_signal:",
        evaluation_fusion.get("recommended_learning_signal"),
    )
    print("evaluator_agreement:", evaluation_fusion.get("evaluator_agreement"))
    print("fusion_confidence:", evaluation_fusion.get("fusion_confidence"))
    print(
        "fusion_confidence_label:",
        evaluation_fusion.get("fusion_confidence_label"),
    )
    print(
        "weakest_skill:",
        evaluation_fusion.get("weakest_skill_signal", {}).get("weakest_skill"),
    )

    assert evaluation_fusion.get("status") == "success"
    assert (
            evaluation_fusion.get("mode")
            == "comparison_only_not_replacing_final_evaluation"
    )
    assert evaluation_fusion.get("fused_score") is not None
    assert evaluation_fusion.get("recommended_learning_signal")
    
    assert output_prediction_evaluation.get("status") == "success"
    assert (
        output_prediction_evaluation.get("mode")
        == "comparison_only_not_replacing_final_evaluation"
    )

    assert debug_evaluation.get("status") == "success"
    assert debug_evaluation.get("mode") == "comparison_only_not_replacing_final_evaluation"

    assert rubric_evaluation.get("status") == "success"
    assert rubric_evaluation.get("mode") == "comparison_only_not_replacing_final_evaluation"

    assert mistake_analysis.get("status") == "success"
    assert mistake_analysis.get("status") == "success"
    assert persistent_reward_state.get("status") == "success"
    assert persistent_reward_state.get("mode") == "dry_run"
    assert persistent_reward_state.get("event_logged") is False
    assert persistent_reward_state.get("xp_awarded") is not None


if __name__ == "__main__":
    main()
