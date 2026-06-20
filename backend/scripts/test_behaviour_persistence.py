from __future__ import annotations

import sqlite3
from pathlib import Path

from tutor.behaviour.behaviour_state_store import persist_behaviour_state
from tutor.behaviour.lstm_behaviour_model import run_behaviour_model
from tutor.system.multi_evidence_collector import MultiEvidenceCollector


DB_PATH = Path("external/core_data/tutor.db")
LEARNER_ID = "14"


def _latest_behaviour_row(learner_id: str) -> dict:
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT *
            FROM behaviour_state
            WHERE learner_id = ?
            ORDER BY
                CASE WHEN timestamp IS NULL THEN 1 ELSE 0 END,
                timestamp DESC,
                id DESC
            LIMIT 1
            """,
            (learner_id,),
        ).fetchone()

    if not row:
        raise AssertionError("No behaviour_state row found after persistence.")

    return {key: row[key] for key in row.keys()}


def _require_field(row: dict, field: str) -> None:
    if field not in row:
        raise AssertionError(f"{field} column missing from behaviour_state.")
    if row[field] is None:
        raise AssertionError(f"{field} is null in latest behaviour_state row.")


def main() -> None:
    output = run_behaviour_model(LEARNER_ID)
    if output.get("status") != "success":
        raise AssertionError(f"Behaviour model failed: {output}")

    persistence = persist_behaviour_state(output)
    if persistence.get("status") != "success":
        raise AssertionError(f"Behaviour persistence failed: {persistence}")

    row = _latest_behaviour_row(LEARNER_ID)

    for field in [
        "behavior_score",
        "behavior_confidence",
        "behavior_risk",
        "behavior_risk_label",
    ]:
        _require_field(row, field)

    collector_output = MultiEvidenceCollector(DB_PATH).collect(
        learner_id=LEARNER_ID,
        system_concept_id="1",
    )
    behaviour = collector_output.get("evidence", {}).get("behaviour", {})
    if not behaviour.get("available"):
        raise AssertionError(f"MultiEvidenceCollector behaviour evidence unavailable: {behaviour}")

    if behaviour.get("risk_score") is None:
        raise AssertionError("MultiEvidenceCollector did not expose behaviour risk_score.")

    print("behavior_label:", output.get("behavior_label"))
    print("behavior_score:", output.get("behavior_score"))
    print("behavior_confidence:", output.get("behavior_confidence"))
    print("behavior_risk:", output.get("behavior_risk"))
    print("behavior_risk_label:", output.get("behavior_risk_label"))
    print("persistence_status:", persistence.get("status"))
    print("row_id:", persistence.get("row_id"))
    print("collector_behaviour_risk:", behaviour.get("risk_score"))
    print("collector_behaviour_confidence:", behaviour.get("confidence"))
    print("collector_behaviour_risk_label:", behaviour.get("risk_label"))
    print("STATUS: success")
    print("MODULE: behaviour_persistence_test")


if __name__ == "__main__":
    main()
