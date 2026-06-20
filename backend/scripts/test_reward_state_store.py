from tutor.progression.progression_reward_engine import build_progression_reward_output
from tutor.progression.reward_state_store import persist_reward_state


def main() -> None:
    progression_reward_output = build_progression_reward_output(
        learner_id="14",
        concept_id="1",
        concept_name="Variables",
        current_difficulty="medium",
        evaluation_output={
            "overall_score": 0.86,
            "verdict": "strong",
            "results": [
                {
                    "assessment_type": "debug",
                    "score": 0.85,
                },
                {
                    "assessment_type": "output_prediction",
                    "score": 0.84,
                },
            ],
        },
        structured_evaluation_output={
            "evaluation": {
                "overall_score": 0.86,
            }
        },
        behaviour_state={
            "data": {
                "behavior_score": 0.89,
                "wrong_rate": 0.08,
                "low_confidence_rate": 0.1,
            }
        },
        view_performance_output={
            "logged": {
                "reward": 0.84,
            }
        },
        guess_probability=0.08,
    )

    store_output = persist_reward_state(
        progression_reward_output,
        dry_run=True,
    )

    print("\nREWARD STATE STORE TEST")
    print("status:", store_output.get("status"))
    print("module:", store_output.get("module"))
    print("learner_id:", store_output.get("learner_id"))
    print("xp_awarded:", store_output.get("xp_awarded"))
    print("total_xp:", store_output.get("total_xp"))
    print("daily_xp:", store_output.get("daily_xp"))
    print("weekly_xp:", store_output.get("weekly_xp"))
    print("current_level:", store_output.get("current_level"))
    print("current_streak:", store_output.get("current_streak"))
    print("longest_streak:", store_output.get("longest_streak"))
    print("event_logged:", store_output.get("event_logged"))

    assert store_output["status"] == "success"
    assert store_output["event_logged"] is False
    assert store_output["mode"] == "dry_run"

    print("\nSTATUS: success")
    print("MODULE: reward_state_store")
    print("mode:", store_output.get("mode"))

if __name__ == "__main__":
    main()