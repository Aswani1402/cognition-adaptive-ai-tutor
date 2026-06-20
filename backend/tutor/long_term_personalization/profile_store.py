import json
import sqlite3
from typing import Any, Dict, Optional

from tutor.long_term_personalization.utils import now_iso


def ensure_profile_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS learner_profile (
            learner_id TEXT PRIMARY KEY,
            profile_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()


def save_profile(conn: sqlite3.Connection, learner_id: str, profile: Dict[str, Any]) -> Dict[str, Any]:
    ensure_profile_table(conn)
    updated_at = now_iso()
    profile_to_save = dict(profile)
    profile_to_save["last_updated"] = updated_at
    conn.execute(
        """
        INSERT OR REPLACE INTO learner_profile (learner_id, profile_json, updated_at)
        VALUES (?, ?, ?)
        """,
        (str(learner_id), json.dumps(profile_to_save, ensure_ascii=True), updated_at),
    )
    conn.commit()
    return profile_to_save


def load_profile(conn: sqlite3.Connection, learner_id: str) -> Optional[Dict[str, Any]]:
    ensure_profile_table(conn)
    row = conn.execute(
        """
        SELECT profile_json
        FROM learner_profile
        WHERE learner_id = ?
        """,
        (str(learner_id),),
    ).fetchone()
    if not row or not row[0]:
        return None
    try:
        parsed = json.loads(row[0])
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None

