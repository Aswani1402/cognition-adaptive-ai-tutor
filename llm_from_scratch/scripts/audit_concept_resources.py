import sqlite3
from pathlib import Path
from collections import defaultdict


ROOT_DIR = Path(__file__).resolve().parents[1]

DB_PATHS = [
    ROOT_DIR / "data" / "raw" / "python_learning.db",
    ROOT_DIR / "data" / "raw" / "database_sql.db",
    ROOT_DIR / "data" / "raw" / "html_web_basics.db",
    ROOT_DIR / "data" / "raw" / "git_version_control.db",
    ROOT_DIR / "data" / "raw" / "data_structures.db",
]

REQUIRED_COLUMNS = [
    "concept_id",
    "topic",
    "base_content",
    "examples",
    "key_points",
    "misconceptions",
    "real_world_use",
    "next_concept_link",
]

QUALITY_FIELDS = [
    "base_content",
    "examples",
    "key_points",
    "misconceptions",
    "real_world_use",
]


def table_exists(conn, table_name):
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    return cur.fetchone() is not None


def get_columns(conn, table_name):
    cur = conn.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cur.fetchall()]


def safe_len(value):
    if value is None:
        return 0
    return len(str(value).strip())


def preview(value, max_chars=120):
    text = "" if value is None else str(value).replace("\n", " ").strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


def audit_db(db_path):
    result = {
        "db": str(db_path),
        "exists": db_path.exists(),
        "table_exists": False,
        "columns": [],
        "missing_columns": [],
        "row_count": 0,
        "empty_counts": defaultdict(int),
        "short_counts": defaultdict(int),
        "rows_with_issues": [],
    }

    if not db_path.exists():
        return result

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    if not table_exists(conn, "concept_resources"):
        conn.close()
        return result

    result["table_exists"] = True
    columns = get_columns(conn, "concept_resources")
    result["columns"] = columns
    result["missing_columns"] = [c for c in REQUIRED_COLUMNS if c not in columns]

    if result["missing_columns"]:
        conn.close()
        return result

    rows = conn.execute(
        """
        SELECT concept_id, topic, base_content, examples, key_points,
               misconceptions, real_world_use, next_concept_link
        FROM concept_resources
        ORDER BY concept_id
        """
    ).fetchall()

    result["row_count"] = len(rows)

    for row in rows:
        row_issues = []

        for field in QUALITY_FIELDS:
            length = safe_len(row[field])

            if length == 0:
                result["empty_counts"][field] += 1
                row_issues.append(f"{field}=EMPTY")

            if field == "base_content" and length < 120:
                result["short_counts"][field] += 1
                row_issues.append(f"{field}=SHORT({length})")

            if field in {"examples", "key_points"} and length < 40:
                result["short_counts"][field] += 1
                row_issues.append(f"{field}=SHORT({length})")

            if field in {"misconceptions", "real_world_use"} and length < 30:
                result["short_counts"][field] += 1
                row_issues.append(f"{field}=SHORT({length})")

        if row_issues:
            result["rows_with_issues"].append(
                {
                    "concept_id": row["concept_id"],
                    "topic": row["topic"],
                    "issues": row_issues,
                    "base_content_preview": preview(row["base_content"]),
                    "examples_preview": preview(row["examples"]),
                    "key_points_preview": preview(row["key_points"]),
                    "misconceptions_preview": preview(row["misconceptions"]),
                    "real_world_use_preview": preview(row["real_world_use"]),
                }
            )

    conn.close()
    return result


def main():
    print("\nCONCEPT RESOURCES DB AUDIT")
    print("=" * 80)

    all_results = []
    total_rows = 0

    for db_path in DB_PATHS:
        result = audit_db(db_path)
        all_results.append(result)

        print(f"\nDB: {db_path.name}")
        print("-" * 80)
        print(f"exists: {result['exists']}")
        print(f"concept_resources table: {result['table_exists']}")

        if not result["exists"] or not result["table_exists"]:
            continue

        print(f"columns: {result['columns']}")
        print(f"missing_columns: {result['missing_columns']}")
        print(f"row_count: {result['row_count']}")

        total_rows += result["row_count"]

        print("\nEmpty field counts:")
        for field in QUALITY_FIELDS:
            print(f"  {field}: {result['empty_counts'][field]}")

        print("\nShort field counts:")
        for field in QUALITY_FIELDS:
            print(f"  {field}: {result['short_counts'][field]}")

        issue_count = len(result["rows_with_issues"])
        print(f"\nRows with issues: {issue_count}")

        for item in result["rows_with_issues"][:5]:
            print("\n  Issue row:")
            print(f"  concept_id: {item['concept_id']}")
            print(f"  topic: {item['topic']}")
            print(f"  issues: {item['issues']}")
            print(f"  base_content: {item['base_content_preview']}")
            print(f"  examples: {item['examples_preview']}")
            print(f"  key_points: {item['key_points_preview']}")
            print(f"  misconceptions: {item['misconceptions_preview']}")
            print(f"  real_world_use: {item['real_world_use_preview']}")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total concept_resources rows across DBs: {total_rows}")

    if total_rows >= 38:
        print("STATUS: PASS — expected concept coverage is present or higher.")
    else:
        print("STATUS: CHECK — concept count is lower than expected.")

    print("\nNext:")
    print("If any fields are EMPTY or SHORT, improve those DB rows before retraining CogniTutorLM.")


if __name__ == "__main__":
    main()