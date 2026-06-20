import json
import sqlite3
from typing import Any, Dict, Optional


def _get_columns(conn: sqlite3.Connection, table: str) -> set:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {r[1] for r in rows}  # column name is index 1


def log_xai(
    conn: sqlite3.Connection,
    learner_id: str,
    concept_id: str,
    event_type: str,
    payload: Dict[str, Any],
    timestamp: Optional[int] = None,
) -> None:
    """
    Logs XAI payload to xai_log without breaking if schema differs.
    It tries common JSON column names; if none exist, it will only log minimal fields.
    """
    cols = _get_columns(conn, "xai_log")

    json_col = None
    for c in ["payload_json", "details_json", "xai_json", "info_json", "meta_json", "state_json"]:
        if c in cols:
            json_col = c
            break

    # choose timestamp
    ts = timestamp
    if ts is None:
        # if DB has timestamp column, let SQL generate it; else we compute
        pass

    if json_col:
        if "timestamp" in cols:
            conn.execute(
                f"INSERT INTO xai_log(learner_id, concept_id, event_type, {json_col}, timestamp) VALUES(?,?,?,?, strftime('%s','now'))",
                (learner_id, concept_id, event_type, json.dumps(payload)),
            )
        else:
            conn.execute(
                f"INSERT INTO xai_log(learner_id, concept_id, event_type, {json_col}) VALUES(?,?,?,?)",
                (learner_id, concept_id, event_type, json.dumps(payload)),
            )
    else:
        # fallback: log only what schema supports
        base_cols = [c for c in ["learner_id", "concept_id", "event_type"] if c in cols]
        if not base_cols:
            return

        values = []
        for c in base_cols:
            if c == "learner_id":
                values.append(learner_id)
            elif c == "concept_id":
                values.append(concept_id)
            elif c == "event_type":
                values.append(event_type)

        placeholders = ",".join(["?"] * len(values))
        col_list = ",".join(base_cols)
        conn.execute(f"INSERT INTO xai_log({col_list}) VALUES({placeholders})", tuple(values))