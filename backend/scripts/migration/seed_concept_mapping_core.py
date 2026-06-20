import os
import sqlite3

DB_PATH = os.path.join("external", "core_data", "tutor.db")

# Map adaptive-path IDs -> content DB concept IDs (edit if you want different targets)
ROWS = [
    ("D1", "P2", "python", "manual_core_v1"),  # example mapping
    ("G1", "G1", "git", "manual_core_v1"),     # if your git DB uses G1.. then keep same
    ("H1", "H1", "html", "manual_core_v1"),    # same idea
    ("S1", "S1", "ds", "manual_core_v1"),      # same idea
]

def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executemany(
            "INSERT OR IGNORE INTO concept_id_map(system_concept_id, content_concept_id, content_domain, source) "
            "VALUES(?,?,?,?)",
            ROWS
        )
        conn.commit()
        print("Inserted mappings:", ROWS)
    finally:
        conn.close()

if __name__ == "__main__":
    main()