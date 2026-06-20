import json
import sqlite3
import time
from typing import Dict, Any, Optional

from .decay_model import decay_score
from .review_priority import build_review_queue


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
        (name,),
    )
    return cur.fetchone() is not None


def load_latest_mastery(learner_id: str, conn: sqlite3.Connection) -> Dict[str, float]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT state_json
        FROM knowledge_state
        WHERE student_id = ?
        ORDER BY updated_at DESC
        LIMIT 1;
        """,
        (learner_id,),
    )

    row = cur.fetchone()
    if not row or not row[0]:
        return {}

    try:
        data = json.loads(row[0])
        if data.get("schema_version") == "kt_v2" and isinstance(data.get("concepts"), dict):
            mastery = {
                concept_id: concept_state.get("mastery")
                for concept_id, concept_state in data["concepts"].items()
                if isinstance(concept_state, dict)
            }
        else:
            mastery = data.get("mastery") or data.get("mastery_raw") or data
        return {k: float(v) for k, v in mastery.items()}
    except Exception:
        return {}
    



def _get_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table});")
    return {row[1] for row in cur.fetchall()}  # row[1] = column name


def _pick_time_column(cols: set[str]) -> Optional[str]:
    # try common timestamp names in order
    for c in ["timestamp", "updated_at", "created_at", "attempted_at", "time", "date", "datetime"]:
        if c in cols:
            return c
    return None




def load_last_practice(learner_id: str, conn: sqlite3.Connection) -> Dict[str, str]:
    cols = _get_columns(conn, "quiz_results")
    time_col = _pick_time_column(cols)

    # if schema not usable, safe fallback (no crash)
    if "concept_id" not in cols or "learner_id" not in cols or not time_col:
        return {}

    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT concept_id, MAX({time_col})
        FROM quiz_results
        WHERE learner_id = ?
        GROUP BY concept_id;
        """,
        (learner_id,),
    )
    rows = cur.fetchall()
    return {cid: ts for cid, ts in rows if cid and ts}



def get_decay_profile(
    learner_id: str,
    conn: sqlite3.Connection,
    lam: float = 0.03,
    review_threshold: float = 0.40,
    top_k: int = 5,
) -> Dict[str, Any]:

    now_ts = time.time()

    mastery = load_latest_mastery(learner_id, conn)
    last_practice = load_last_practice(learner_id, conn)

    if not mastery:
        return {
            "learner_id": learner_id,
            "generated_at": now_ts,
            "decay": {},
            "review_priority": {},
            "review_queue": [],
            "params": {
                "lambda": lam,
                "review_threshold": review_threshold,
                "top_k": top_k,
            },
            "notes": {"fallback_used": True, "reason": "no_mastery_found"},
        }

    decay_map = {
        cid: decay_score(last_practice.get(cid), lam)
        for cid in mastery.keys()
    }

    queue, extra_notes, priority_map = build_review_queue(
        mastery_map=mastery,
        decay_map=decay_map,
        top_k=top_k,
        review_threshold=review_threshold,
    )

    return {
        "learner_id": learner_id,
        "generated_at": now_ts,
        "decay": decay_map,
        "review_priority": priority_map,
        "review_queue": queue,
        "params": {
            "lambda": lam,
            "review_threshold": review_threshold,
            "top_k": top_k,
        },
        "notes": {"fallback_used": False, **extra_notes},
    }
