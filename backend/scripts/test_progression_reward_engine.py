from tutor.progression.progression_reward_engine import build_progression_reward_output


def main():
    evaluation_output = {
        "overall_score": 0.9,
        "verdict": "strong",
        "results": [
            {"assessment_type": "mcq", "score": 1.0},
            {"assessment_type": "debug", "score": 0.9},
            {"assessment_type": "output_prediction", "score": 0.9},
            {"assessment_type": "explanation", "score": 0.9},
        ],
    }

    structured_evaluation_output = {
        "status": "success",
        "evaluation": {
            "overall_score": 0.9,
            "verdict": "strong",
        },
    }

    behaviour_state = {
        "data": {
            "behavior_label": "stable",
            "behavior_score": 0.85,
            "wrong_rate": 0.1,
            "low_confidence_rate": 0.1,
        }
    }

    view_performance_output = {
        "logged": {
            "teaching_view": "code_view",
            "reward": 0.82,
        }
    }

    output = build_progression_reward_output(
        learner_id="14",
        concept_id="1",
        concept_name="Variables",
        current_difficulty="medium",
        evaluation_output=evaluation_output,
        structured_evaluation_output=structured_evaluation_output,
        behaviour_state=behaviour_state,
        view_performance_output=view_performance_output,
        next_concept_name="Data Types",
        guess_probability=0.1,
    )

    print("\nPROGRESSION REWARD ENGINE TEST")
    print("Status:", output.get("status"))
    print("Module:", output.get("module"))

    progression = output.get("progression_result", {})
    promotion = output.get("promotion_confidence_output", {})
    celebration = output.get("celebration", {})
    reward = output.get("reward_state", {})


    print("\nMODEL COMPARISON")
    print("status:", output.get("model_comparison_status"))

    model_output = output.get("model_comparison_output", {})
    print("model module:", model_output.get("module"))
    print("model status:", model_output.get("status"))
    print("comparison only:", model_output.get("comparison_only"))
    print("model promotion allowed:", model_output.get("model_promotion_allowed"))
    print(
        "model promotion confidence:",
        round(model_output.get("model_promotion_allowed_confidence", 0.0), 4),
    )
    print("model progression action:", model_output.get("model_progression_action"))
    print(
        "model progression confidence:",
        round(model_output.get("model_progression_action_confidence", 0.0), 4),
    )

    print("\nPROGRESSION")
    print("promotion_allowed:", progression.get("promotion_allowed"))
    print("level_up_allowed:", progression.get("level_up_allowed"))
    print("concept_cleared:", progression.get("concept_cleared"))
    print("next_difficulty:", progression.get("next_difficulty"))
    print("progression_action:", progression.get("progression_action"))

    print("\nPROMOTION")
    print("confidence:", promotion.get("promotion_confidence"))
    print("label:", promotion.get("promotion_confidence_label"))
    print("blocking:", promotion.get("blocking_reasons"))
    print("model_status:", promotion.get("model_status"))

    print("\nREWARD")
    print("xp_awarded:", reward.get("xp_awarded"))
    print("streak_updated:", reward.get("streak_updated"))

    print("\nCELEBRATION")
    print("show:", celebration.get("show"))
    print("type:", celebration.get("type"))
    print("message:", celebration.get("message"))
    print("mascot_emotion:", celebration.get("mascot_emotion"))
    print("animation:", celebration.get("animation"))

    assert output.get("status") == "success"
    assert progression.get("promotion_allowed") is True
    assert progression.get("level_up_allowed") is True
    assert progression.get("next_difficulty") == "hard"
    assert celebration.get("show") is True
    assert reward.get("xp_awarded") > 0

    print("\nSTATUS: success")
    print("MODULE: progression_reward_engine")


if __name__ == "__main__":
    main()