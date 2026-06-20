import sqlite3
from typing import List, Tuple

DB_PATH = "database/tutor.db"

def get_prereqs(concept_id: str) -> List[str]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT prereq_concept_id
        FROM concept_dependencies
        WHERE concept_id=?
    """, (concept_id,))
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_unlockables(mastered_concept_id: str) -> List[str]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT concept_id
        FROM concept_dependencies
        WHERE prereq_concept_id=?
    """, (mastered_concept_id,))
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]