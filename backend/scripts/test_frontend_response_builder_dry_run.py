from tutor.system.frontend_response_builder import build_frontend_response
from tutor.system.run_integrated_tutor_once import run_integrated_tutor_once


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

    print("\nFRONTEND RESPONSE BUILDER DRY-RUN TEST")
    print("status:", frontend_output.get("status"))
    print("teaching_view:", frontend_output["summary"]["teaching_view"])
    print("assessment_types:", frontend_output["summary"]["assessment_types"])
    print(
        "teaching_strategy_training_log_output:",
        frontend_output["logging"]["teaching_strategy_training_log"]["status"],
    )

    progression_reward_output = frontend_output.get("progression_reward_output", {})
    model_output = progression_reward_output.get("model_comparison_output", {})
    persistent_reward_state = frontend_output.get("persistent_reward_state", {})

    print("\nMODEL COMPARISON")
    print("model_comparison_status:", progression_reward_output.get("model_comparison_status"))
    print("model_comparison_output:", model_output.get("status"))
    print("model_progression_action:", model_output.get("model_progression_action"))

    print("\nPERSISTENT REWARD STATE")
    print("reward_persistence_status:", persistent_reward_state.get("status"))
    print("reward_persistence_mode:", persistent_reward_state.get("mode"))
    print("event_logged:", persistent_reward_state.get("event_logged"))
    print("xp_awarded:", persistent_reward_state.get("xp_awarded"))
    print("total_xp:", persistent_reward_state.get("total_xp"))
    print("daily_xp:", persistent_reward_state.get("daily_xp"))
    print("weekly_xp:", persistent_reward_state.get("weekly_xp"))
    print("current_level:", persistent_reward_state.get("current_level"))
    print("current_streak:", persistent_reward_state.get("current_streak"))
    print("longest_streak:", persistent_reward_state.get("longest_streak"))

    assert progression_reward_output.get("model_comparison_status") == (
        "comparison_only_not_used_for_final_decision"
    )
    assert model_output.get("status") == "success"

    assert persistent_reward_state.get("status") == "success"
    assert persistent_reward_state.get("mode") == "dry_run"
    assert persistent_reward_state.get("event_logged") is False
    assert persistent_reward_state.get("xp_awarded") is not None

    print("\nSTATUS: success")
    print("MODULE: frontend_response_builder_dry_run")
    print("RESULT: frontend response works without writing reward state to DB")


if __name__ == "__main__":
    main()