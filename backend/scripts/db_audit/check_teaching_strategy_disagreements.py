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
    total_count = cur.fetchone()[0]

    cur.execute(
        f"""
        SELECT COUNT(*)
        FROM {TABLE_NAME}
        WHERE teaching_view_agreement = 1
        """
    )
    teaching_agree_count = cur.fetchone()[0]

    cur.execute(
        f"""
        SELECT COUNT(*)
        FROM {TABLE_NAME}
        WHERE progression_agreement = 1
        """
    )
    progression_agree_count = cur.fetchone()[0]

    cur.execute(
        f"""
        SELECT COUNT(*)
        FROM {TABLE_NAME}
        WHERE progression_agreement = 0
        """
    )
    progression_disagree_count = cur.fetchone()[0]

    print("\nTEACHING STRATEGY MODEL COMPARISON SUMMARY")
    print("Total rows:", total_count)
    print("Teaching-view agreement rows:", teaching_agree_count)
    print("Progression agreement rows:", progression_agree_count)
    print("Progression disagreement rows:", progression_disagree_count)

    if total_count > 0:
        print("Teaching-view agreement rate:", round(teaching_agree_count / total_count, 4))
        print("Progression agreement rate:", round(progression_agree_count / total_count, 4))

    print("\nPROGRESSION DISAGREEMENT PAIRS")
    cur.execute(
        f"""
        SELECT
            evidence_progression_action,
            model_progression_action,
            COUNT(*)
        FROM {TABLE_NAME}
        WHERE progression_agreement = 0
        GROUP BY evidence_progression_action, model_progression_action
        ORDER BY COUNT(*) DESC
        """
    )

    for row in cur.fetchall():
        print(
            {
                "evidence_progression_action": row[0],
                "model_progression_action": row[1],
                "count": row[2],
            }
        )

    print("\nLATEST PROGRESSION DISAGREEMENT SAMPLES")
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
            model_progression_confidence,
            created_at
        FROM {TABLE_NAME}
        WHERE progression_agreement = 0
        ORDER BY id DESC
        LIMIT 20
        """
    )

    rows = cur.fetchall()

    if not rows:
        print("No progression disagreements found.")
    else:
        for row in rows:
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
                    "model_progression_confidence": row[10],
                    "created_at": row[11],
                }
            )

    conn.close()


if __name__ == "__main__":
    main()