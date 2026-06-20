import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tutor.system.run_integrated_tutor_once import run_integrated_tutor_once

DB_PATH = "external/core_data/tutor.db"

conn = sqlite3.connect(DB_PATH)
rows = conn.execute("SELECT DISTINCT learner_id FROM quiz_results").fetchall()
conn.close()

learner_ids = [str(r[0]) for r in rows if r[0] is not None]

profiles = ["weak", "average", "strong"]

count = 0

for learner_id in learner_ids[:100]:  # limit first
    for profile in profiles:
        try:
            run_integrated_tutor_once(
                learner_id=learner_id,
                learner_profile=profile,
            )
            count += 1
        except Exception:
            pass

print(f"Generated runs: {count}")
