import os
import sqlite3

DB_PATH = os.path.join("external", "core_data", "tutor.db")

DDL = """
CREATE TABLE IF NOT EXISTS concept_id_map (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    system_concept_id TEXT NOT NULL,     -- e.g., "37.0"
    content_concept_id TEXT NOT NULL,    -- e.g., "P4"
    content_domain TEXT,                 -- e.g., "python"
    source TEXT,                         -- e.g., "manual_v1"
    created_at INTEGER DEFAULT (strftime('%s','now')),
    UNIQUE(system_concept_id, content_concept_id)
);
"""

def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(DDL)
        conn.commit()
        print("concept_id_map table ready")
    finally:
        conn.close()

if __name__ == "__main__":
    main()