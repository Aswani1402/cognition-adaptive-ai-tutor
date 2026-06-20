# tutor/utils/concept_mapper.py

import sqlite3

DB_PATH = "external/core_data/tutor.db"


def normalize_domain(domain):
    if not domain:
        return None

    domain = domain.strip().lower()

    mapping = {
        "python": "python",
        "sql": "sql",
        "html": "html",
        "git": "git",
        "data structures": "ds",
        "data_structures": "ds",
        "datastructures": "ds",
    }

    return mapping.get(domain, domain)


def map_system_to_content(system_concept_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT content_concept_id, domain
        FROM concept_id_map
        WHERE system_concept_id = ?
    """, (system_concept_id,))

    row = cur.fetchone()
    conn.close()

    if row:
        content_id = row["content_concept_id"]
        domain = normalize_domain(row["domain"])
        return content_id, domain

    return None, None