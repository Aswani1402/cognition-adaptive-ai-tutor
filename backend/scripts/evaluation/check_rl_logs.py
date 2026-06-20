import json
import sqlite3
from pathlib import Path


DB_PATH = Path("external/core_data/tutor.db")


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM rl_experience_log
    """)
    total = cursor.fetchone()[0]

    cursor.execute("""
        SELECT learner_id, concept_id, state_json, action_json, reward, next_state_json, created_at
        FROM rl_experience_log
        ORDER BY id DESC
        LIMIT 5
    """)
    rows = cursor.fetchall()

    print("\nRL LOG CHECK")
    print("Total RL experiences:", total)

    print("\nLatest 5 experiences:")
    for row in rows:
        learner_id, concept_id, state_json, action_json, reward, next_state_json, created_at = row

        state = json.loads(state_json)
        action = json.loads(action_json)
        next_state = json.loads(next_state_json)

        print("\n---")
        print("learner_id:", learner_id)
        print("concept_id:", concept_id)
        print("reward:", reward)
        print("created_at:", created_at)
        print("state:", state)
        print("action:", action)
        print("next_state:", next_state)

    conn.close()


if __name__ == "__main__":
    main()