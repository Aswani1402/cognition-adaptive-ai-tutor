import json
import sqlite3
from typing import Dict, Any

from tutor.forgetting.profile import get_decay_profile


def compute_and_store_decay(conn: sqlite3.Connection, learner_id: str) -> Dict[str, Any]:
    """
    Computes Module 6 decay profile (read-only from knowledge_state + quiz_results),
    then stores it into decay_state for Module 4 to consume.
    """
    profile = get_decay_profile(learner_id, conn)

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
    return profile