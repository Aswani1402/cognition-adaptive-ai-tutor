import json
import sqlite3
from typing import Dict


def get_mastery_map(tutor_conn: sqlite3.Connection, student_id: str) -> Dict[str, float]:
    """
    Returns mastery dict {concept_id/skill_id (str): mastery (float)} from knowledge_state.state_json.
    """
    row = tutor_conn.execute(
        "SELECT state_json FROM knowledge_state WHERE student_id = ?",
        (student_id,),
    ).fetchone()

    if not row or not row[0]:
        return {}

    try:
        state = json.loads(row[0])
    except Exception:
        return {}

    if state.get("schema_version") == "kt_v2" and isinstance(state.get("concepts"), dict):
        mastery = {
            concept_id: concept_state.get("mastery")
            for concept_id, concept_state in state["concepts"].items()
            if isinstance(concept_state, dict)
        }
    else:
        mastery = state.get("mastery", state)

    if not isinstance(mastery, dict):
        return {}

    # ensure float values
    out = {}
    for k, v in mastery.items():
        try:
            out[str(k)] = float(v)
        except Exception:
            continue
    return out
