# tutor/utils/content_fetcher.py

import sqlite3
from pathlib import Path

DB_MAP = {
    "python": "external/core_data/python_learning.db",
    "sql": "external/core_data/database_sql.db",
    "html": "external/core_data/html_web_basics.db",
    "git": "external/core_data/git_version_control.db",
    "ds": "external/core_data/data_structures.db",
}


def get_db_path(domain):
    path = DB_MAP.get(domain)
    if not path:
        raise ValueError(f"Unknown domain: {domain}")
    return Path(path)


def fetch_concept_resource(domain, concept_id):
    db_path = get_db_path(domain)

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