from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = Path("external/core_data/tutor.db")


TABLE_COLUMNS: dict[str, dict[str, str]] = {
    "quiz_results": {
        "concept_name": "TEXT",
        "subject": "TEXT",
        "domain": "TEXT",
        "difficulty": "TEXT",
        "question_type": "TEXT",
        "answer": "TEXT",
        "option_change_count": "INTEGER DEFAULT 0",
        "answer_change_count": "INTEGER DEFAULT 0",
        "run_code_count": "INTEGER DEFAULT 0",
        "attempt_count": "INTEGER DEFAULT 1",
        "wrong_attempt_count": "INTEGER DEFAULT 0",
    },
    "behaviour_state": {
        "answer_change_rate": "REAL DEFAULT 0",
        "run_code_rate": "REAL DEFAULT 0",
        "retry_rate": "REAL DEFAULT 0",
        "state_json": "TEXT",
    },
}


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return bool(row)


def existing_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}


def add_columns(db_path: Path | str = DB_PATH) -> dict[str, list[str]]:
    db_path = Path(db_path)
    conn = sqlite3.connect(db_path)
    added: dict[str, list[str]] = {}
    try:
        for table_name, columns in TABLE_COLUMNS.items():
            if not table_exists(conn, table_name):
                added[table_name] = []
                continue
            present = existing_columns(conn, table_name)
            for column_name, column_type in columns.items():
                if column_name in present:
                    continue
                conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
                added.setdefault(table_name, []).append(column_name)
        conn.commit()
        return added
    finally:
        conn.close()


def main() -> None:
    added = add_columns()
    print("STATUS: success")
    print("MODULE: add_behaviour_payload_columns")
    print(f"DB: {DB_PATH}")
    for table_name, columns in added.items():
        print(f"{table_name}: {', '.join(columns) if columns else 'no new columns'}")


if __name__ == "__main__":
    main()
