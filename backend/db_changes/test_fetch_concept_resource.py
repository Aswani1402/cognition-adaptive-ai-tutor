# db_changes/test_fetch_concept_resource.py

import sqlite3
from pathlib import Path

DB_MAP = {
    "python": "external/core_data/python_learning.db",
    "sql": "external/core_data/database_sql.db",
    "html": "external/core_data/html_web_basics.db",
    "git": "external/core_data/git_version_control.db",
    "ds": "external/core_data/data_structures.db",
}


def fetch_concept_resource(db_path, concept_id):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT concept_id, topic, base_content, examples, key_points,
               misconceptions, real_world_use, next_concept_link
        FROM concept_resources
        WHERE concept_id = ?
    """, (concept_id,))

    row = cur.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def main():
    db_path = DB_MAP["python"]   # change later if needed
    concept_id = "P1"

    result = fetch_concept_resource(db_path, concept_id)

    if result:
        print("Concept fetched successfully.\n")
        print("concept_id:", result["concept_id"])
        print("topic:", result["topic"])
        print("base_content preview:", (result["base_content"][:300] + "...") if result["base_content"] else None)
        print("examples preview:", (result["examples"][:200] + "...") if result["examples"] else None)
        print("key_points preview:", (result["key_points"][:200] + "...") if result["key_points"] else None)
    else:
        print("No concept found.")


if __name__ == "__main__":
    main()