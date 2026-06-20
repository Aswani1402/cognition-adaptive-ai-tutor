from tutor.system.run_integrated_tutor_once import run_integrated_tutor_once


def _get_nested(data, *keys, default=None):
    current = data

    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)

    return current if current is not None else default


def main() -> None:
    learner_id = "14"

    output = run_integrated_tutor_once(learner_id=learner_id)

    progression_reward_output = output.get("progression_reward_output", {})
    progression_result = progression_reward_output.get("progression_result", {})
    promotion_confidence_output = progression_reward_output.get(
        "promotion_confidence_output", {}
    )
    model_comparison_output = progression_reward_output.get(
        "model_comparison_output", {}
    )
    reward_state = progression_reward_output.get("reward_state", {})
    celebration = progression_reward_output.get("celebration", {})
    frontend_contract = progression_reward_output.get("frontend_contract", {})

    required_checks = {
        "pipeline_status_success": output.get("status") == "success",
        "progression_reward_output_present": bool(progression_reward_output),
        "progression_engine_success": progression_reward_output.get("status") == "success",
        "progression_result_present": bool(progression_result),
        "promotion_confidence_present": bool(promotion_confidence_output),
        "model_comparison_status_present": bool(
            progression_reward_output.get("model_comparison_status")
        ),
        "model_comparison_output_present": bool(model_comparison_output),
        "model_comparison_success": model_comparison_output.get("status") == "success",
        "reward_state_present": bool(reward_state),
        "celebration_present": bool(celebration),
        "frontend_contract_present": bool(frontend_contract),
    }

    failed = [name for name, passed in required_checks.items() if not passed]

    print("\nFULL PIPELINE REWARD + ML MODEL AUDIT")
    print("learner_id:", learner_id)
    print("pipeline_status:", output.get("status"))

    print("\nCHECKS")
    for name, passed in required_checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    print("\nBASELINE PROGRESSION")
    print("promotion_allowed:", progression_result.get("promotion_allowed"))
    print("level_up_allowed:", progression_result.get("level_up_allowed"))
    print("concept_cleared:", progression_result.get("concept_cleared"))
    print("progression_action:", progression_result.get("progression_action"))
    print("promotion_confidence:", progression_result.get("promotion_confidence"))
    print("promotion_label:", progression_result.get("promotion_confidence_label"))
    print("blocking_reasons:", progression_result.get("blocking_reasons"))

    print("\nML COMPARISON")
    print(
        "model_comparison_status:",
        progression_reward_output.get("model_comparison_status"),
    )
    print("model_module:", model_comparison_output.get("module"))
    print("model_status:", model_comparison_output.get("status"))
    print("comparison_only:", model_comparison_output.get("comparison_only"))
    print("model_promotion_allowed:", model_comparison_output.get("model_promotion_allowed"))
    print(
        "model_promotion_confidence:",
        round(model_comparison_output.get("model_promotion_allowed_confidence", 0.0), 4),
    )
    print("model_progression_action:", model_comparison_output.get("model_progression_action"))
    print(
        "model_progression_confidence:",
        round(model_comparison_output.get("model_progression_action_confidence", 0.0), 4),
    )

    print("\nREWARD")
    print("xp_awarded:", reward_state.get("xp_awarded"))
    print("streak_updated:", reward_state.get("streak_updated"))
    print("reward_reason:", reward_state.get("reward_reason"))

    print("\nCELEBRATION")
    print("show:", celebration.get("show"))
    print("type:", celebration.get("type"))
    print("message:", celebration.get("message"))
    print("mascot_emotion:", celebration.get("mascot_emotion"))
    print("animation:", celebration.get("animation"))

    print("\nFRONTEND CONTRACT")
    print("show_celebration_modal:", frontend_contract.get("show_celebration_modal"))
    print("show_xp_popup:", frontend_contract.get("show_xp_popup"))
    print("update_streak_widget:", frontend_contract.get("update_streak_widget"))
    print("update_path_node:", frontend_contract.get("update_path_node"))
    print("mascot_emotion:", frontend_contract.get("mascot_emotion"))

    if failed:
        print("\nSTATUS: failed")
        print("MODULE: full_pipeline_reward_model_audit")
        print("FAILED CHECKS:", failed)
        raise SystemExit(1)

    print("\nSTATUS: success")
    print("MODULE: full_pipeline_reward_model_audit")
    print("RESULT: full pipeline reward + ML comparison output is valid")


if __name__ == "__main__":
    main()