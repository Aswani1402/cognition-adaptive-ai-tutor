import sqlite3
from pathlib import Path


DB_PATH = Path("external/core_data/tutor.db")


def row_to_dict(cursor, row):
    if row is None:
        return None
    columns = [col[0] for col in cursor.description]
    return dict(zip(columns, row))


def main() -> None:
    learner_id = "14"

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("\nREWARD STATE TABLE AUDIT")
    print("DB:", DB_PATH)
    print("learner_id:", learner_id)

    cursor.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name IN (
            'learner_xp_state',
            'learner_streak_state',
            'reward_event_log'
          )
        ORDER BY name
        """
    )
    tables = [row[0] for row in cursor.fetchall()]

    print("\nTABLES FOUND")
    for table in tables:
        print("-", table)

    required_tables = {
        "learner_xp_state",
        "learner_streak_state",
        "reward_event_log",
    }

    missing_tables = sorted(required_tables - set(tables))

    cursor.execute(
        """
        SELECT *
        FROM learner_xp_state
        WHERE learner_id = ?
        """,
        (learner_id,),
    )
    xp_row = row_to_dict(cursor, cursor.fetchone())

    cursor.execute(
        """
        SELECT *
        FROM learner_streak_state
        WHERE learner_id = ?
        """,
        (learner_id,),
    )
    streak_row = row_to_dict(cursor, cursor.fetchone())

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM reward_event_log
        WHERE learner_id = ?
        """,
        (learner_id,),
    )
    reward_event_count = cursor.fetchone()[0]

    cursor.execute(
        """
        SELECT *
        FROM reward_event_log
        WHERE learner_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (learner_id,),
    )
    latest_event = row_to_dict(cursor, cursor.fetchone())

    conn.close()

    checks = {
        "required_tables_exist": not missing_tables,
        "xp_state_exists": xp_row is not None,
        "streak_state_exists": streak_row is not None,
        "reward_events_exist": reward_event_count > 0,
        "latest_event_exists": latest_event is not None,
        "latest_event_has_progression_action": bool(
            latest_event and latest_event.get("progression_action")
        ),
        "latest_event_has_model_progression_action": bool(
            latest_event and latest_event.get("model_progression_action")
        ),
    }

    print("\nCHECKS")
    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    print("\nXP STATE")
    print(xp_row)

    print("\nSTREAK STATE")
    print(streak_row)

    print("\nREWARD EVENT SUMMARY")
    print("reward_event_count:", reward_event_count)

    print("\nLATEST REWARD EVENT")
    print(latest_event)

    failed = [name for name, passed in checks.items() if not passed]

    if failed:
        print("\nSTATUS: failed")
        print("MODULE: reward_state_table_audit")
        print("FAILED CHECKS:", failed)
        raise SystemExit(1)

    print("\nSTATUS: success")
    print("MODULE: reward_state_table_audit")
    print("RESULT: reward DB persistence tables are valid")


if __name__ == "__main__":
    main()