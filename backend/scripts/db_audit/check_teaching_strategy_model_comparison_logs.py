import sqlite3
from pathlib import Path


DB_PATH = Path("external/core_data/tutor.db")
TABLE_NAME = "teaching_strategy_model_comparison_log"


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name=?
        """,
        (TABLE_NAME,),
    )

    if cur.fetchone() is None:
        print("Table not found:", TABLE_NAME)
        conn.close()
        return

    cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
    count = cur.fetchone()[0]

    print("\nMODEL COMPARISON LOG COUNT:", count)

    cur.execute(
        f"""
        SELECT
            learner_id,
            concept_id,
            concept_name,
            evidence_teaching_view,
            model_teaching_view,
            teaching_view_agreement,
            evidence_progression_action,
            model_progression_action,
            progression_agreement,
            model_teaching_view_confidence,
            created_at
        FROM {TABLE_NAME}
        ORDER BY id DESC
        LIMIT 10
        """
    )

    print("\nLATEST COMPARISON LOGS")
    for row in cur.fetchall():
        print(
            {
                "learner_id": row[0],
                "concept_id": row[1],
                "concept_name": row[2],
                "evidence_teaching_view": row[3],
                "model_teaching_view": row[4],
                "teaching_view_agreement": bool(row[5]) if row[5] is not None else None,
                "evidence_progression_action": row[6],
                "model_progression_action": row[7],
                "progression_agreement": bool(row[8]) if row[8] is not None else None,
                "model_teaching_view_confidence": row[9],
                "created_at": row[10],
            }
        )

    conn.close()


if __name__ == "__main__":
    main()