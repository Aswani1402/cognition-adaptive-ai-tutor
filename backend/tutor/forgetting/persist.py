import json
import sqlite3
from typing import Dict, Any

def save_decay_profile(conn: sqlite3.Connection, profile: Dict[str, Any]) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO decay_state
        (learner_id, decay_json, priority_json, queue_json, params_json, generated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            profile["learner_id"],
            json.dumps(profile.get("decay", {})),
            json.dumps(profile.get("review_priority", {})),
            json.dumps(profile.get("review_queue", [])),
            json.dumps(profile.get("params", {})),
            float(profile.get("generated_at", 0.0)),
        ),
    )
    conn.commit()