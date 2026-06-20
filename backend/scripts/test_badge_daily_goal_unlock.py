from __future__ import annotations

import sqlite3
from pathlib import Path

from scripts.migration.add_badge_goal_unlock_tables import run_migration
from tutor.progression.progression_reward_engine import build_progression_reward_output
from tutor.progression.reward_state_store import persist_reward_state
from tutor.reward.badge_engine import BadgeEngine
from tutor.reward.concept_unlock_store import ConceptUnlockStore
from tutor.reward.daily_goal_engine import DailyGoalEngine


DB_PATH = Path("external/core_data/tutor.db")
TEST_LEARNER_ID = "gamification_test_learner"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _unlock_row_exists(learner_id: str, concept_id: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            "SELECT id FROM concept_unlock_state WHERE learner_id = ? AND concept_id = ?",
            (learner_id, concept_id),
        ).fetchone()
        return bool(row)
    finally:
        conn.close()


def _seed_reward_event() -> None:
    output = build_progression_reward_output(
        learner_id=TEST_LEARNER_ID,
        concept_id="1",
        concept_name="Variables",
        current_difficulty="medium",
        evaluation_output={
            "overall_score": 0.86,
            "verdict": "strong",
            "results": [
                {"assessment_type": "debug", "score": 0.88},
                {"assessment_type": "output_prediction", "score": 0.84},
                {"assessment_type": "challenge", "score": 0.9},
            ],
        },
        structured_evaluation_output={"evaluation": {"overall_score": 0.86}},
        behaviour_state={"data": {"behavior_score": 0.91, "wrong_rate": 0.05, "low_confidence_rate": 0.05}},
        view_performance_output={"logged": {"reward": 0.9}},
        guess_probability=0.05,
    )
    persist_reward_state(output, dry_run=False)


def main() -> None:
    migration = run_migration(DB_PATH)
    _assert(migration["status"] == "success", f"migration failed: {migration}")
    _seed_reward_event()

    badge_engine = BadgeEngine(DB_PATH)
    first_badge_output = badge_engine.evaluate_and_award(TEST_LEARNER_ID)
    second_badge_output = badge_engine.evaluate_and_award(TEST_LEARNER_ID)
    _assert(first_badge_output["status"] == "success", f"badge failed: {first_badge_output}")
    _assert(isinstance(first_badge_output["new_badges"], list), f"badge list missing: {first_badge_output}")
    _assert(second_badge_output["new_badges"] == [], f"duplicate badges awarded: {second_badge_output}")

    daily_goal = DailyGoalEngine(DB_PATH).update_goal(
        learner_id=TEST_LEARNER_ID,
        target_xp=5,
        target_questions=1,
        target_revision_cards=1,
    )
    _assert(daily_goal["status"] == "success", f"daily goal failed: {daily_goal}")
    _assert(0.0 <= daily_goal["completion_rate"] <= 1.0, f"bad completion rate: {daily_goal}")

    unlock = ConceptUnlockStore(DB_PATH).update_unlock_state(
        learner_id=TEST_LEARNER_ID,
        concept_id="1",
        domain="Python",
        concept_name="Variables",
        mastery_score=0.82,
        promotion_confidence=0.78,
        prerequisites_met=True,
        fused_score=0.86,
        evidence={"source": "badge_daily_goal_unlock_test"},
    )
    _assert(unlock["status"] == "success", f"unlock failed: {unlock}")
    _assert(_unlock_row_exists(TEST_LEARNER_ID, "1"), f"unlock state not persisted: {unlock}")

    packet = {
        "xp": first_badge_output["evidence"].get("total_xp"),
        "badges": {
            "new_badges": first_badge_output["new_badges"],
            "badge_count": second_badge_output["badge_count"],
        },
        "daily_goal": daily_goal,
        "concept_unlock": unlock,
    }
    _assert("badges" in packet and "daily_goal" in packet and "concept_unlock" in packet, f"packet incomplete: {packet}")

    print("badge_count:", second_badge_output["badge_count"])
    print("daily_goal_completion_rate:", daily_goal["completion_rate"])
    print("concept_unlock_status:", unlock["unlock_status"])
    print("STATUS: success")
    print("MODULE: badge_daily_goal_unlock_test")


if __name__ == "__main__":
    main()
