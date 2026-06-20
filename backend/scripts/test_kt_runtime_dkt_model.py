from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from tutor.knowledge_state.update import update_knowledge_state
from tutor.knowledge_state.dkt.dkt_inference import predict_mastery_dkt_or_fallback


DB_PATH = Path("external/core_data/tutor.db")
MODEL_PATH = Path("models/dkt/model.pt")
ID_MAP_PATH = Path("models/dkt/id_map.json")
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
    return dict(row)


def main() -> None:
    if not MODEL_PATH.exists() or not ID_MAP_PATH.exists():
        raise AssertionError("Current tutor DKT artifacts are missing. Run python -m scripts.training.kt.train_dkt_runtime_model first.")
    if not DB_PATH.exists():
        raise FileNotFoundError(f"DB not found: {DB_PATH}")

    id_map = json.loads(ID_MAP_PATH.read_text(encoding="utf-8"))
    if id_map.get("schema_version") != "current_tutor_kt_v1":
        raise AssertionError("id_map schema_version is not current_tutor_kt_v1.")
    if not isinstance(id_map.get("concept_to_idx"), dict) or not id_map["concept_to_idx"]:
        raise AssertionError("id_map concept_to_idx is missing or empty.")

    with sqlite3.connect(DB_PATH) as conn:
        output = update_knowledge_state(conn, LEARNER_ID)

    data = output.get("data", {}) if isinstance(output, dict) else {}
    if output.get("status") != "success":
        raise AssertionError(f"KT update failed: {output}")
    if data.get("source") != "dkt_current_tutor_runtime":
        raise AssertionError(f"Expected DKT runtime source, got {data.get('source')}: {data.get('inference_error')}")
    if data.get("model_used") is not True:
        raise AssertionError("Expected model_used true.")
    if data.get("fallback_used") is not False:
        raise AssertionError("Expected fallback_used false.")
    if data.get("schema_version") != "kt_v2":
        raise AssertionError("Expected kt_v2 runtime schema.")
    if not data.get("written_state"):
        raise AssertionError("Expected written_state values.")
    mastery_last = float(data.get("predicted_mastery_last"))
    if not 0.0 <= mastery_last <= 1.0:
        raise AssertionError("predicted_mastery_last is outside [0, 1].")

    with sqlite3.connect(DB_PATH) as conn:
        latest = _latest_state_for_learner(conn, LEARNER_ID)
    state = json.loads(latest["state_json"])
    if state.get("schema_version") != "kt_v2":
        raise AssertionError("Persisted state_json schema_version is not kt_v2.")
    if state.get("source") != "dkt_current_tutor_runtime":
        raise AssertionError("Persisted state_json source is not dkt_current_tutor_runtime.")
    if not state.get("model_path") or not state.get("id_map_path"):
        raise AssertionError("Persisted state_json is missing model/id_map path.")

    temp_path = MODEL_PATH.with_suffix(".pt.tmp")
    if temp_path.exists():
        temp_path.unlink()
    try:
        MODEL_PATH.rename(temp_path)
        fallback_output = predict_mastery_dkt_or_fallback(
            learner_id=LEARNER_ID,
            interactions=[
                {"raw_concept_id": "1", "concept_id": 1, "correct": 1},
                {"raw_concept_id": "1", "concept_id": 1, "correct": 0},
            ],
        )
        if fallback_output.get("source") != "bkt_baseline":
            raise AssertionError(f"Expected BKT fallback when DKT is missing, got {fallback_output}")
        if fallback_output.get("model_used") is not True:
            raise AssertionError("Expected BKT fallback to use a model artifact.")
    finally:
        if temp_path.exists():
            temp_path.rename(MODEL_PATH)

    print("status:", output.get("status"))
    print("source:", data.get("source"))
    print("model_used:", data.get("model_used"))
    print("fallback_used:", data.get("fallback_used"))
    print("sequence_length:", data.get("sequence_length"))
    print("predicted_mastery_last:", data.get("predicted_mastery_last"))
    print("written_state:", data.get("written_state"))
    print("bkt_fallback_source:", fallback_output.get("source"))
    print("STATUS: success")
    print("MODULE: kt_runtime_dkt_model_test")


if __name__ == "__main__":
    main()
