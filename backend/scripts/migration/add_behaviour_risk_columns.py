from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = Path("external/core_data/tutor.db")
TABLE_NAME = "behaviour_state"

NEW_COLUMNS = {
    "behavior_confidence": "REAL",
    "behavior_risk": "REAL",
    "behavior_risk_label": "TEXT",
    "model_used": "INTEGER",
    "sequence_length": "INTEGER",
    "behavior_source": "TEXT",
}


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name=?
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def _columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    return {
        str(row[1])
        for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }


def add_behaviour_risk_columns(db_path: Path = DB_PATH) -> dict:
    if not db_path.exists():
        return {
            "status": "error",
            "db_path": str(db_path),
            "error": "Database not found.",
            "added_columns": [],
            "already_present": [],
        }

    added_columns = []
    already_present = []

    with sqlite3.connect(str(db_path)) as conn:
        if not _table_exists(conn, TABLE_NAME):
            return {
                "status": "error",
                "db_path": str(db_path),
                "error": f"{TABLE_NAME} table not found.",
                "added_columns": [],
                "already_present": [],
            }

        existing = _columns(conn, TABLE_NAME)
        for column, column_type in NEW_COLUMNS.items():
            if column in existing:
                already_present.append(column)
                continue

            conn.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN {column} {column_type}")
            added_columns.append(column)

        conn.commit()

    return {
        "status": "success",
        "db_path": str(db_path),
        "table": TABLE_NAME,
        "added_columns": added_columns,
        "already_present": already_present,
    }


def main() -> None:
    result = add_behaviour_risk_columns()
    print("STATUS:", result["status"])
    print("MODULE: add_behaviour_risk_columns")
    print("DB_PATH:", result["db_path"])
    print("ADDED_COLUMNS:", result["added_columns"])
    print("ALREADY_PRESENT:", result["already_present"])
    if result.get("error"):
        print("ERROR:", result["error"])


if __name__ == "__main__":
    main()
