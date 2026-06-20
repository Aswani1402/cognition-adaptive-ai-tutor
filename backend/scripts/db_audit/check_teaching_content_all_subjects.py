from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORE_DATA_DIR = PROJECT_ROOT / "external" / "core_data"

SUBJECT_DBS = [
    "python_learning.db",
    "html_web_basics.db",
    "database_sql.db",
    "git_version_control.db",
    "data_structures.db",
]


def get_conn(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def get_columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [str(r["name"]) for r in rows]


def print_rows(title: str, rows: Iterable[sqlite3.Row | dict], limit: int | None = None) -> None:
    print(f"\n--- {title} ---")
    count = 0
    for row in rows:
        print(dict(row) if not isinstance(row, dict) else row)
        count += 1
        if limit is not None and count >= limit:
            break
    if count == 0:
        print("(no rows)")


def audit_db(db_name: str) -> None:
    db_path = CORE_DATA_DIR / db_name
    print("\n" + "=" * 100)
    print(f"DB: {db_name}")
    print(f"PATH: {db_path}")

    if not db_path.exists():
        print("Status: FILE NOT FOUND")
        return

    conn = get_conn(db_path)
    try:
        if not table_exists(conn, "teaching_content"):
            print("Status: teaching_content table NOT FOUND")
            return

        columns = get_columns(conn, "teaching_content")
        print(f"teaching_content columns: {columns}")

        total_rows = conn.execute(
            "SELECT COUNT(*) AS total_rows FROM teaching_content"
        ).fetchone()
        print(f"total_rows: {total_rows['total_rows']}")

        if "concept_id" in columns:
            by_concept = conn.execute(
                """
                SELECT concept_id, COUNT(*) AS row_count
                FROM teaching_content
                GROUP BY concept_id
                ORDER BY concept_id
                """
            ).fetchall()
            print_rows("Rows per concept", by_concept)

        if {"concept_id", "strategy", "difficulty", "content_type"}.issubset(set(columns)):
            combo_rows = conn.execute(
                """
                SELECT concept_id, strategy, difficulty, content_type
                FROM teaching_content
                ORDER BY concept_id, strategy, difficulty, content_type
                LIMIT 200
                """
            ).fetchall()
            print_rows("Strategy / difficulty / content_type sample", combo_rows)

        sample_rows = conn.execute(
            "SELECT * FROM teaching_content LIMIT 10"
        ).fetchall()
        print_rows("Sample teaching_content rows", sample_rows)

        # quick diagnosis
        has_strategy = "strategy" in columns
        has_difficulty = "difficulty" in columns
        has_content_type = "content_type" in columns

        if has_strategy and has_difficulty and has_content_type:
            print("\nDiagnosis: OLD multi-variant style table detected "
                  "(strategy + difficulty + content_type stored directly in DB).")
        else:
            print("\nDiagnosis: Simpler/base-content style or partial schema.")

    finally:
        conn.close()


def main() -> None:
    print("Checking teaching_content in all subject DBs...\n")
    for db_name in SUBJECT_DBS:
        audit_db(db_name)


if __name__ == "__main__":
    main()