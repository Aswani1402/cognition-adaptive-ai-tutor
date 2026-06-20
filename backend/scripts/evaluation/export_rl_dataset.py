import csv
import json
import sqlite3
from pathlib import Path


DB_PATH = Path("external/core_data/tutor.db")
OUTPUT_DIR = Path("evaluation_outputs/csv")
OUTPUT_PATH = OUTPUT_DIR / "rl_experience_dataset.csv"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            learner_id,
            concept_id,
            state_json,
            action_json,
            reward,
            next_state_json,
            created_at
        FROM rl_experience_log
        ORDER BY id ASC
    """)

    rows = cursor.fetchall()
    conn.close()

    fieldnames = [
        "learner_id",
        "concept_id",
        "mastery_score",
        "behavior_label",
        "behavior_score",
        "review_due",
        "evaluation_score",
        "learning_signal",
        "next_concept_id",
        "strategy",
        "difficulty",
        "content_type",
        "decision_type",
        "reward",
        "next_mastery_score",
        "next_behavior_label",
        "next_behavior_score",
        "next_review_due",
        "next_evaluation_score",
        "next_learning_signal",
        "created_at",
    ]

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            learner_id, concept_id, state_json, action_json, reward, next_state_json, created_at = row

            state = json.loads(state_json)
            action = json.loads(action_json)
            next_state = json.loads(next_state_json)

            writer.writerow({
                "learner_id": learner_id,
                "concept_id": concept_id,
                "mastery_score": state.get("mastery_score"),
                "behavior_label": state.get("behavior_label"),
                "behavior_score": state.get("behavior_score"),
                "review_due": state.get("review_due"),
                "evaluation_score": state.get("evaluation_score"),
                "learning_signal": state.get("learning_signal"),
                "next_concept_id": action.get("next_concept_id"),
                "strategy": action.get("strategy"),
                "difficulty": action.get("difficulty"),
                "content_type": action.get("content_type"),
                "decision_type": action.get("decision_type"),
                "reward": reward,
                "next_mastery_score": next_state.get("mastery_score"),
                "next_behavior_label": next_state.get("behavior_label"),
                "next_behavior_score": next_state.get("behavior_score"),
                "next_review_due": next_state.get("review_due"),
                "next_evaluation_score": next_state.get("evaluation_score"),
                "next_learning_signal": next_state.get("learning_signal"),
                "created_at": created_at,
            })

    print("RL dataset exported successfully")
    print("Rows:", len(rows))
    print("Path:", OUTPUT_PATH)


if __name__ == "__main__":
    main()