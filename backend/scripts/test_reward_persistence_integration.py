import sqlite3
from pathlib import Path

from tutor.progression.progression_reward_engine import build_progression_reward_output
from tutor.progression.reward_state_store import persist_reward_state


DB_PATH = Path("external/core_data/tutor.db")
TEST_LEARNER_ID = "reward_test_learner"


def _fetch_xp_state(learner_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT total_xp, daily_xp, weekly_xp, current_level
        FROM learner_xp_state
        WHERE learner_id = ?
        """,
        (learner_id,),
    )

    row = cursor.fetchone()
    conn.close()
    return row


def _fetch_event_count(learner_id: str) -> int:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM reward_event_log
        WHERE learner_id = ?
        """,
        (learner_id,),
    )

    count = cursor.fetchone()[0]
    conn.close()
    return int(count)


def main() -> None:
    before_xp_state = _fetch_xp_state(TEST_LEARNER_ID)
    before_event_count = _fetch_event_count(TEST_LEARNER_ID)

    progression_reward_output = build_progression_reward_output(
        learner_id=TEST_LEARNER_ID,
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
                {
                    "assessment_type": "explanation",
                    "score": 0.90,
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
        dry_run=False,
    )

    after_xp_state = _fetch_xp_state(TEST_LEARNER_ID)
    after_event_count = _fetch_event_count(TEST_LEARNER_ID)

    print("\nREWARD PERSISTENCE INTEGRATION TEST")
    print("learner_id:", TEST_LEARNER_ID)

    print("\nBEFORE")
    print("xp_state:", before_xp_state)
    print("event_count:", before_event_count)

    print("\nSTORE OUTPUT")
    print("status:", store_output.get("status"))
    print("module:", store_output.get("module"))
    print("xp_awarded:", store_output.get("xp_awarded"))
    print("total_xp:", store_output.get("total_xp"))
    print("daily_xp:", store_output.get("daily_xp"))
    print("weekly_xp:", store_output.get("weekly_xp"))
    print("current_level:", store_output.get("current_level"))
    print("current_streak:", store_output.get("current_streak"))
    print("longest_streak:", store_output.get("longest_streak"))
    print("event_logged:", store_output.get("event_logged"))

    print("\nAFTER")
    print("xp_state:", after_xp_state)
    print("event_count:", after_event_count)

    assert store_output["status"] == "success"
    assert store_output["event_logged"] is True
    assert store_output["xp_awarded"] > 0
    assert after_event_count == before_event_count + 1
    assert after_xp_state is not None

    print("\nSTATUS: success")
    print("MODULE: reward_persistence_integration")
    print("RESULT: real reward persistence works for test learner without modifying learner 14")


if __name__ == "__main__":
    main()