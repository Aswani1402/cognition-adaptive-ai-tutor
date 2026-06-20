import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tutor.progression.progression_reward_engine import build_progression_reward_output
from tutor.progression.reward_state_store import persist_reward_state


DB_PATH = Path("external/core_data/tutor.db")
TEST_LEARNER_ID = "reward_reset_test_learner"


def _delete_test_learner() -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM learner_xp_state WHERE learner_id = ?", (TEST_LEARNER_ID,))
    cursor.execute("DELETE FROM learner_streak_state WHERE learner_id = ?", (TEST_LEARNER_ID,))
    cursor.execute("DELETE FROM reward_event_log WHERE learner_id = ?", (TEST_LEARNER_ID,))

    conn.commit()
    conn.close()


def _insert_old_xp_state() -> None:
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    old_week = (date.today() - timedelta(days=8)).isoformat()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO learner_xp_state (
            learner_id,
            total_xp,
            daily_xp,
            weekly_xp,
            current_level,
            last_daily_reset_date,
            last_weekly_reset_date,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            TEST_LEARNER_ID,
            100,
            80,
            90,
            2,
            yesterday,
            old_week,
        ),
    )

    cursor.execute(
        """
        INSERT INTO learner_streak_state (
            learner_id,
            current_streak,
            longest_streak,
            last_active_date,
            streak_updated_at
        )
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            TEST_LEARNER_ID,
            3,
            5,
            yesterday,
        ),
    )

    conn.commit()
    conn.close()


def _fetch_xp_state():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT total_xp,
               daily_xp,
               weekly_xp,
               current_level,
               last_daily_reset_date,
               last_weekly_reset_date
        FROM learner_xp_state
        WHERE learner_id = ?
        """,
        (TEST_LEARNER_ID,),
    )

    row = cursor.fetchone()
    conn.close()
    return row


def _fetch_event_count() -> int:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM reward_event_log
        WHERE learner_id = ?
        """,
        (TEST_LEARNER_ID,),
    )

    count = cursor.fetchone()[0]
    conn.close()
    return int(count)


def main() -> None:
    _delete_test_learner()
    _insert_old_xp_state()

    before_xp_state = _fetch_xp_state()
    before_event_count = _fetch_event_count()

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

    after_xp_state = _fetch_xp_state()
    after_event_count = _fetch_event_count()

    print("\nREWARD RESET LOGIC TEST")
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
    print("last_daily_reset_date:", store_output.get("last_daily_reset_date"))
    print("last_weekly_reset_date:", store_output.get("last_weekly_reset_date"))
    print("event_logged:", store_output.get("event_logged"))

    print("\nAFTER")
    print("xp_state:", after_xp_state)
    print("event_count:", after_event_count)

    assert store_output["status"] == "success"
    assert store_output["event_logged"] is True
    assert store_output["xp_awarded"] == 20

    assert after_event_count == before_event_count + 1
    assert after_xp_state is not None

    total_xp, daily_xp, weekly_xp, current_level, _, _ = after_xp_state

    assert total_xp == 120
    assert daily_xp == 20
    assert weekly_xp == 20
    assert current_level >= 2

    print("\nSTATUS: success")
    print("MODULE: reward_reset_logic")
    print("RESULT: daily/weekly XP reset logic works without modifying learner 14")


if __name__ == "__main__":
    main()
