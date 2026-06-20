from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from tutor.knowledge_state.update import update_knowledge_state


DB_PATH = Path("external/core_data/tutor.db")
LEARNER_ID = "14"


def _latest_state_for_learner(conn: sqlite3.Connection, learner_id: str) -> dict[str, Any]:
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        """
        SELECT student_id, state_json, updated_at
        FROM knowledge_state
        WHERE student_id = ?
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        (learner_id,),
    ).fetchone()

    if not row:
        raise AssertionError(f"No knowledge_state row found for learner {learner_id}.")

    return {
        "student_id": row["student_id"],
        "state_json": row["state_json"],
        "updated_at": row["updated_at"],
    }


def _assert_kt_v2_state(state: dict[str, Any]) -> None:
    if state.get("schema_version") != "kt_v2":
        raise AssertionError("state_json schema_version is not kt_v2.")

    concepts = state.get("concepts")
    if not isinstance(concepts, dict) or not concepts:
        raise AssertionError("state_json concepts is missing or empty.")

    has_mastery = False
    for concept_state in concepts.values():
        if isinstance(concept_state, dict) and concept_state.get("mastery") is not None:
            float(concept_state["mastery"])
            has_mastery = True
            break

    if not has_mastery:
        raise AssertionError("No concept mastery value found in state_json concepts.")


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"DB not found: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        output = update_knowledge_state(conn, LEARNER_ID)

    data = output.get("data", {}) if isinstance(output, dict) else {}
    written_state = data.get("written_state")

    if output.get("status") != "success":
        raise AssertionError(f"KT update failed: {output}")

    if data.get("schema_version") != "kt_v2":
        raise AssertionError("Runtime output schema_version is not kt_v2.")

    if not isinstance(written_state, dict) or not written_state:
        raise AssertionError("Old-compatible written_state is missing or empty.")

    for value in written_state.values():
        float(value)

    with sqlite3.connect(DB_PATH) as conn:
        latest_row = _latest_state_for_learner(conn, LEARNER_ID)

    try:
        state = json.loads(latest_row["state_json"])
    except Exception as exc:
        raise AssertionError(f"state_json is not valid JSON: {exc}") from exc

    _assert_kt_v2_state(state)

    print("status:", output.get("status"))
    print("schema_version:", data.get("schema_version"))
    print("source:", data.get("source"))
    print("model_used:", data.get("model_used"))
    print("fallback_used:", data.get("fallback_used"))
    print("sequence_length:", data.get("sequence_length"))
    print("predicted_mastery_last:", data.get("predicted_mastery_last"))
    print("written_state:", written_state)
    print("latest_state_updated_at:", latest_row.get("updated_at"))
    print("STATUS: success")
    print("MODULE: kt_runtime_inference_test")


if __name__ == "__main__":
    main()
