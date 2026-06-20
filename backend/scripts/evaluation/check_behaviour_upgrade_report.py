from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tutor.behaviour.behaviour_state_store import persist_behaviour_state
from tutor.behaviour.lstm_behaviour_model import run_behaviour_model
from tutor.system.multi_evidence_collector import MultiEvidenceCollector


DB_PATH = Path("external/core_data/tutor.db")
OUTPUT_JSON = Path("evaluation_outputs/json/behaviour_upgrade_report.json")
OUTPUT_MD = Path("evaluation_outputs/reports/behaviour_upgrade_report.md")
LEARNER_ID = "14"

REQUIRED_COLUMNS = [
    "behavior_confidence",
    "behavior_risk",
    "behavior_risk_label",
    "model_used",
    "sequence_length",
    "behavior_source",
]

REQUIRED_RUNTIME_FIELDS = [
    "behavior_label",
    "behavior_score",
    "behavior_confidence",
    "behavior_risk",
    "behavior_risk_label",
    "wrong_rate",
    "slow_rate",
    "low_confidence_rate",
    "hint_rate",
    "option_change_rate",
    "model_used",
    "sequence_length",
    "behavior_source",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect_readonly(db_path: Path) -> sqlite3.Connection:
    uri = f"file:{db_path.resolve().as_posix()}?mode=ro&immutable=1"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


def _table_exists(cursor: sqlite3.Cursor, table_name: str) -> bool:
    row = cursor.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name=?
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def _table_columns(cursor: sqlite3.Cursor, table_name: str) -> list[str]:
    if not _table_exists(cursor, table_name):
        return []
    rows = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [str(row[1]) for row in rows]


def _schema_status() -> dict[str, Any]:
    report = {
        "status": "warning",
        "db_exists": DB_PATH.exists(),
        "behaviour_state_exists": False,
        "columns": [],
        "required_columns": REQUIRED_COLUMNS,
        "missing_columns": [],
        "notes": [],
    }

    if not DB_PATH.exists():
        report["status"] = "error"
        report["notes"].append("tutor.db not found.")
        return report

    try:
        with _connect_readonly(DB_PATH) as conn:
            cursor = conn.cursor()
            if not _table_exists(cursor, "behaviour_state"):
                report["status"] = "error"
                report["notes"].append("behaviour_state table not found.")
                return report

            columns = _table_columns(cursor, "behaviour_state")
            report["behaviour_state_exists"] = True
            report["columns"] = columns
            report["missing_columns"] = [column for column in REQUIRED_COLUMNS if column not in columns]
            report["status"] = "success" if not report["missing_columns"] else "warning"
            if report["missing_columns"]:
                report["notes"].append("One or more behaviour risk columns are missing.")
    except Exception as exc:
        report["status"] = "error"
        report["notes"].append(f"Schema inspection failed: {exc}")

    return report


def _runtime_status() -> dict[str, Any]:
    report = {
        "status": "warning",
        "learner_id": LEARNER_ID,
        "runtime_output": {},
        "required_fields_present": False,
        "missing_fields": [],
        "notes": [],
    }

    try:
        output = run_behaviour_model(LEARNER_ID)
        report["runtime_output"] = output
        report["missing_fields"] = [
            field
            for field in REQUIRED_RUNTIME_FIELDS
            if field not in output or output.get(field) is None
        ]
        report["required_fields_present"] = not report["missing_fields"]
        report["status"] = "success" if output.get("status") == "success" and report["required_fields_present"] else "warning"
        if report["missing_fields"]:
            report["notes"].append("Runtime behaviour output is missing required fields.")
    except Exception as exc:
        report["status"] = "error"
        report["notes"].append(f"Runtime behaviour check failed: {exc}")

    return report


def _persistence_status(runtime_output: dict[str, Any]) -> dict[str, Any]:
    report = {
        "status": "warning",
        "persistence_output": {},
        "latest_row": None,
        "behavior_confidence_not_null": False,
        "behavior_risk_not_null": False,
        "behavior_risk_label_not_null": False,
        "behavior_score_available": False,
        "notes": [],
    }

    try:
        persistence = persist_behaviour_state(runtime_output)
        report["persistence_output"] = persistence

        with _connect_readonly(DB_PATH) as conn:
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
                (LEARNER_ID,),
            ).fetchone()

        latest = _row_to_dict(row)
        report["latest_row"] = latest
        if latest:
            report["behavior_confidence_not_null"] = latest.get("behavior_confidence") is not None
            report["behavior_risk_not_null"] = latest.get("behavior_risk") is not None
            report["behavior_risk_label_not_null"] = latest.get("behavior_risk_label") is not None
            report["behavior_score_available"] = latest.get("behavior_score") is not None

        checks_ok = all(
            [
                persistence.get("status") == "success",
                report["behavior_confidence_not_null"],
                report["behavior_risk_not_null"],
                report["behavior_risk_label_not_null"],
                report["behavior_score_available"],
            ]
        )
        report["status"] = "success" if checks_ok else "warning"
        if not checks_ok:
            report["notes"].append("Persistence validation did not satisfy all required checks.")
    except Exception as exc:
        report["status"] = "error"
        report["notes"].append(f"Persistence check failed: {exc}")

    return report


def _collector_status() -> dict[str, Any]:
    report = {
        "status": "warning",
        "collector_output": {},
        "behaviour_risk": None,
        "behaviour_confidence": None,
        "behaviour_risk_label": None,
        "reads_behaviour_risk": False,
        "reads_behaviour_confidence": False,
        "reads_behaviour_risk_label": False,
        "notes": [],
    }

    try:
        output = MultiEvidenceCollector(DB_PATH).collect(
            learner_id=LEARNER_ID,
            system_concept_id="1",
        )
        behaviour = output.get("evidence", {}).get("behaviour", {})
        report["collector_output"] = behaviour
        report["behaviour_risk"] = behaviour.get("risk_score")
        report["behaviour_confidence"] = behaviour.get("confidence")
        report["behaviour_risk_label"] = behaviour.get("risk_label")
        report["reads_behaviour_risk"] = behaviour.get("risk_score") is not None
        report["reads_behaviour_confidence"] = behaviour.get("confidence") is not None
        report["reads_behaviour_risk_label"] = behaviour.get("risk_label") is not None

        checks_ok = all(
            [
                behaviour.get("available"),
                report["reads_behaviour_risk"],
                report["reads_behaviour_confidence"],
                report["reads_behaviour_risk_label"],
            ]
        )
        report["status"] = "success" if checks_ok else "warning"
        if not checks_ok:
            report["notes"].append("MultiEvidenceCollector did not read all behaviour risk semantics.")
    except Exception as exc:
        report["status"] = "error"
        report["notes"].append(f"MultiEvidenceCollector check failed: {exc}")

    return report


def _integrated_status() -> dict[str, Any]:
    report = {
        "status": "warning",
        "called": False,
        "reward_dry_run": True,
        "pipeline_status": None,
        "behavior_score_available": False,
        "behavior_confidence_available": False,
        "behavior_risk_available": False,
        "behavior_risk_label_available": False,
        "behaviour_state_summary": {},
        "notes": [],
    }

    try:
        from tutor.system.run_integrated_tutor_once import run_integrated_tutor_once

        report["called"] = True
        output = run_integrated_tutor_once(
            learner_id=LEARNER_ID,
            reward_dry_run=True,
        )
        report["pipeline_status"] = output.get("status")
        behaviour_data = output.get("behaviour_state", {}).get("data", {})
        report["behaviour_state_summary"] = {
            "behavior_label": behaviour_data.get("behavior_label"),
            "behavior_score": behaviour_data.get("behavior_score"),
            "behavior_confidence": behaviour_data.get("behavior_confidence"),
            "behavior_risk": behaviour_data.get("behavior_risk"),
            "behavior_risk_label": behaviour_data.get("behavior_risk_label"),
            "model_used": behaviour_data.get("model_used"),
            "sequence_length": behaviour_data.get("sequence_length"),
            "behavior_source": behaviour_data.get("behavior_source"),
        }
        report["behavior_score_available"] = behaviour_data.get("behavior_score") is not None
        report["behavior_confidence_available"] = behaviour_data.get("behavior_confidence") is not None
        report["behavior_risk_available"] = behaviour_data.get("behavior_risk") is not None
        report["behavior_risk_label_available"] = behaviour_data.get("behavior_risk_label") is not None

        checks_ok = all(
            [
                output.get("status") == "success",
                report["behavior_score_available"],
                report["behavior_confidence_available"],
                report["behavior_risk_available"],
                report["behavior_risk_label_available"],
            ]
        )
        report["status"] = "success" if checks_ok else "warning"
        if not checks_ok:
            report["notes"].append("Integrated pipeline did not expose all behaviour compatibility fields.")
    except Exception as exc:
        report["status"] = "warning"
        report["notes"].append(f"Integrated pipeline check failed or was skipped safely: {exc}")

    return report


def _overall_status(parts: list[dict[str, Any]]) -> str:
    statuses = [part.get("status") for part in parts]
    if "error" in statuses:
        return "error"
    if "warning" in statuses:
        return "warning"
    return "success"


def _build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Behaviour Upgrade Report",
        "",
        f"Generated at: {report['generated_at']}",
        "",
        f"Overall status: `{report['overall_status']}`",
        "",
        "## Schema",
        "",
        f"- Status: `{report['schema_status']['status']}`",
        f"- Missing columns: {report['schema_status']['missing_columns']}",
        f"- Required columns: {report['schema_status']['required_columns']}",
        "",
        "## Runtime Output",
        "",
        f"- Status: `{report['runtime_status']['status']}`",
        f"- Required fields present: {report['runtime_status']['required_fields_present']}",
        f"- Missing fields: {report['runtime_status']['missing_fields']}",
        f"- Runtime output: {report['runtime_status']['runtime_output']}",
        "",
        "## Persistence",
        "",
        f"- Status: `{report['persistence_status']['status']}`",
        f"- behavior_confidence not null: {report['persistence_status']['behavior_confidence_not_null']}",
        f"- behavior_risk not null: {report['persistence_status']['behavior_risk_not_null']}",
        f"- behavior_risk_label not null: {report['persistence_status']['behavior_risk_label_not_null']}",
        f"- behavior_score available: {report['persistence_status']['behavior_score_available']}",
        "",
        "## MultiEvidenceCollector",
        "",
        f"- Status: `{report['multi_evidence_collector_status']['status']}`",
        f"- behaviour_risk: {report['multi_evidence_collector_status']['behaviour_risk']}",
        f"- behaviour_confidence: {report['multi_evidence_collector_status']['behaviour_confidence']}",
        f"- behaviour_risk_label: {report['multi_evidence_collector_status']['behaviour_risk_label']}",
        "",
        "## Integrated Compatibility",
        "",
        f"- Status: `{report['integrated_pipeline_status']['status']}`",
        f"- Called: {report['integrated_pipeline_status']['called']}",
        f"- Pipeline status: {report['integrated_pipeline_status']['pipeline_status']}",
        f"- behavior_score available: {report['integrated_pipeline_status']['behavior_score_available']}",
        f"- Summary: {report['integrated_pipeline_status']['behaviour_state_summary']}",
        "",
        "## Status",
        "",
        "```text",
        f"STATUS: {report['overall_status']}",
        "MODULE: behaviour_upgrade_report",
        "```",
        "",
    ]
    return "\n".join(lines)


def build_report() -> dict[str, Any]:
    schema = _schema_status()
    runtime = _runtime_status()
    persistence = _persistence_status(runtime.get("runtime_output", {}))
    collector = _collector_status()
    integrated = _integrated_status()

    report = {
        "overall_status": _overall_status([schema, runtime, persistence, collector, integrated]),
        "module": "behaviour_upgrade_report",
        "generated_at": _now_iso(),
        "schema_status": schema,
        "runtime_status": runtime,
        "persistence_status": persistence,
        "multi_evidence_collector_status": collector,
        "integrated_pipeline_status": integrated,
    }
    return report


def main() -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)

    report = build_report()
    OUTPUT_JSON.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    OUTPUT_MD.write_text(_build_markdown(report), encoding="utf-8")

    print(f"STATUS: {report['overall_status']}")
    print("MODULE: behaviour_upgrade_report")
    print(f"JSON_REPORT: {OUTPUT_JSON}")
    print(f"MD_REPORT: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
