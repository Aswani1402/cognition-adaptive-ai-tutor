import sqlite3
import json
from pathlib import Path


DB_PATH = Path("external/core_data/tutor.db")
TABLE_NAME = "teaching_strategy_training_log"


def safe_json(value):
    if value is None:
        return None

    try:
        return json.loads(value)
    except Exception:
        return value


def get_columns(cur):
    cur.execute(f"PRAGMA table_info({TABLE_NAME})")
    return [row[1] for row in cur.fetchall()]


def pick_column(columns, candidates):
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
    count = cur.fetchone()[0]

    print("\nTEACHING STRATEGY TRAINING LOG COUNT:", count)

    columns = get_columns(cur)

    print("\nTABLE COLUMNS")
    print(columns)

    learner_col = pick_column(columns, ["learner_id", "student_id"])
    concept_col = pick_column(columns, ["concept_id"])
    concept_name_col = pick_column(columns, ["concept_name"])
    view_col = pick_column(columns, ["selected_teaching_view", "teaching_view", "selected_view"])
    assessment_types_col = pick_column(columns, ["assessment_types_json", "assessment_types"])
    evaluation_col = pick_column(columns, ["evaluation_score", "score"])
    view_reward_col = pick_column(columns, ["view_reward", "reward"])
    progression_col = pick_column(columns, ["progression_action", "progression"])
    success_col = pick_column(columns, ["success_label", "outcome_label"])
    created_col = pick_column(columns, ["created_at", "timestamp", "generated_at"])

    selected_cols = [
        col
        for col in [
            learner_col,
            concept_col,
            concept_name_col,
            view_col,
            assessment_types_col,
            evaluation_col,
            view_reward_col,
            progression_col,
            success_col,
            created_col,
        ]
        if col is not None
    ]

    if not selected_cols:
        print("\nNo matching columns found.")
        conn.close()
        return

    query = f"""
        SELECT {", ".join(selected_cols)}
        FROM {TABLE_NAME}
        ORDER BY id DESC
        LIMIT 10
    """

    cur.execute(query)
    rows = cur.fetchall()

    print("\nLATEST LOGS")

    for row in rows:
        item = dict(zip(selected_cols, row))

        for key in list(item.keys()):
            if key.endswith("_json") or key in {"assessment_types", "assessment_types_json"}:
                item[key] = safe_json(item[key])

        print(item)

    conn.close()


if __name__ == "__main__":
    main()