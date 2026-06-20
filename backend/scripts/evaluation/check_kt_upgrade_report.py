from __future__ import annotations

import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tutor.knowledge_state.update import update_knowledge_state


DB_PATH = Path("external/core_data/tutor.db")
DKT_INFERENCE_PATH = Path("tutor/knowledge_state/dkt/dkt_inference.py")
UPDATE_PATH = Path("tutor/knowledge_state/update.py")
OUTPUT_JSON = Path("evaluation_outputs/json/kt_upgrade_report.json")
OUTPUT_MD = Path("evaluation_outputs/reports/kt_upgrade_report.md")
LEARNER_ID = "14"


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


def _detect_state_schema(raw_state: Any) -> str:
    if raw_state is None or str(raw_state).strip() == "":
        return "empty_state"

    try:
        state = json.loads(str(raw_state))
    except Exception:
        return "invalid_json"

    if not isinstance(state, dict) or not state:
        return "empty_state"

    if state.get("schema_version") == "kt_v2" and isinstance(state.get("concepts"), dict):
        return "kt_v2_format"

    values = []
    for value in state.values():
        try:
            values.append(float(value))
        except Exception:
            values = []
            break

    if values and all(0.0 <= value <= 1.0 for value in values):
        return "old_direct_mastery_format"

    return "unknown_format"


def _code_status() -> dict[str, Any]:
    dkt_text = DKT_INFERENCE_PATH.read_text(encoding="utf-8", errors="ignore") if DKT_INFERENCE_PATH.exists() else ""
    update_text = UPDATE_PATH.read_text(encoding="utf-8", errors="ignore") if UPDATE_PATH.exists() else ""

    return {
        "dkt_inference_exists": DKT_INFERENCE_PATH.exists(),
        "dkt_inference_path": str(DKT_INFERENCE_PATH),
        "public_function_found": "predict_mastery_dkt_or_fallback" in dkt_text,
        "fallback_source_found": "fallback_cumulative" in dkt_text,
        "update_path": str(UPDATE_PATH),
        "update_uses_dkt_fallback_inference": "predict_mastery_dkt_or_fallback" in update_text,
        "update_writes_kt_v2": '"schema_version": "kt_v2"' in update_text,
    }


def _knowledge_state_schema_status() -> dict[str, Any]:
    report = {
        "db_exists": DB_PATH.exists(),
        "knowledge_state_exists": False,
        "row_count": 0,
        "schema_counts": {},
        "kt_v2_row_count": 0,
        "old_direct_mastery_row_count": 0,
        "latest_learner_14_row": None,
        "status": "warning",
        "notes": [],
    }

    if not DB_PATH.exists():
        report["status"] = "error"
        report["notes"].append("tutor.db is missing.")
        return report

    try:
        with _connect_readonly(DB_PATH) as conn:
            cursor = conn.cursor()
            if not _table_exists(cursor, "knowledge_state"):
                report["status"] = "error"
                report["notes"].append("knowledge_state table is missing.")
                return report

            report["knowledge_state_exists"] = True
            rows = cursor.execute("SELECT student_id, state_json, updated_at FROM knowledge_state").fetchall()
            counts: Counter[str] = Counter()
            for row in rows:
                counts[_detect_state_schema(row["state_json"])] += 1

            report["row_count"] = len(rows)
            report["schema_counts"] = dict(counts)
            report["kt_v2_row_count"] = int(counts.get("kt_v2_format", 0))
            report["old_direct_mastery_row_count"] = int(counts.get("old_direct_mastery_format", 0))

            latest = cursor.execute(
                """
                SELECT student_id, state_json, updated_at
                FROM knowledge_state
                WHERE student_id = ?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (LEARNER_ID,),
            ).fetchone()
            report["latest_learner_14_row"] = _row_to_dict(latest)

            warnings = []
            if report["kt_v2_row_count"] < 1:
                warnings.append("No kt_v2_format rows found.")
            if report["old_direct_mastery_row_count"] > 0:
                warnings.append("Old direct mastery rows still exist; safe migration is partial.")
            report["notes"].extend(warnings)
            report["status"] = "warning" if warnings else "success"
    except Exception as exc:
        report["status"] = "error"
        report["notes"].append(f"knowledge_state schema inspection failed: {exc}")

    return report


def _runtime_kt_status() -> dict[str, Any]:
    report = {
        "status": "warning",
        "learner_id": LEARNER_ID,
        "runtime_call_attempted": False,
        "runtime_call_can_write": True,
        "required_fields_present": False,
        "old_compatible_written_state_exists": False,
        "runtime_output_fields": {},
        "notes": [],
    }

    if not DB_PATH.exists():
        report["status"] = "error"
        report["notes"].append("Runtime KT check skipped because tutor.db is missing.")
        return report

    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            output = update_knowledge_state(conn, LEARNER_ID)
        report["runtime_call_attempted"] = True

        data = output.get("data", {}) if isinstance(output, dict) else {}
        runtime_fields = {
            "status": output.get("status") if isinstance(output, dict) else None,
            "learner_id": output.get("learner_id") if isinstance(output, dict) else None,
            "schema_version": data.get("schema_version"),
            "source": data.get("source"),
            "model_used": data.get("model_used"),
            "fallback_used": data.get("fallback_used"),
            "sequence_length": data.get("sequence_length"),
            "predicted_mastery_last": data.get("predicted_mastery_last"),
            "written_state": data.get("written_state"),
            "inference_error": data.get("inference_error"),
        }
        report["runtime_output_fields"] = runtime_fields

        required = [
            "schema_version",
            "source",
            "model_used",
            "fallback_used",
            "sequence_length",
            "predicted_mastery_last",
            "written_state",
        ]
        report["required_fields_present"] = all(runtime_fields.get(field) is not None for field in required)
        written_state = runtime_fields.get("written_state")
        report["old_compatible_written_state_exists"] = isinstance(written_state, dict) and bool(written_state)

        if output.get("status") == "success" and report["required_fields_present"] and report["old_compatible_written_state_exists"]:
            report["status"] = "success"
        else:
            report["notes"].append("Runtime output is missing one or more required KT upgrade fields.")
    except Exception as exc:
        report["status"] = "error"
        report["notes"].append(f"Runtime KT check failed: {exc}")

    return report


def _integrated_pipeline_status() -> dict[str, Any]:
    report = {
        "status": "warning",
        "called": False,
        "reward_dry_run": True,
        "pipeline_status": None,
        "mastery_read_correctly": False,
        "mastery_score": None,
        "knowledge_state_schema_version": None,
        "knowledge_state_source": None,
        "knowledge_state_fallback_used": None,
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

        kt_data = (
            output.get("knowledge_state", {})
            .get("data", {})
            .get("data", {})
        )
        report["knowledge_state_schema_version"] = kt_data.get("schema_version")
        report["knowledge_state_source"] = kt_data.get("source")
        report["knowledge_state_fallback_used"] = kt_data.get("fallback_used")
        report["mastery_score"] = kt_data.get("predicted_mastery_last")

        try:
            mastery = float(report["mastery_score"])
            report["mastery_read_correctly"] = 0.0 <= mastery <= 1.0
        except Exception:
            report["mastery_read_correctly"] = False

        report["status"] = "success" if output.get("status") == "success" and report["mastery_read_correctly"] else "warning"
        if report["status"] != "success":
            report["notes"].append("Integrated pipeline did not expose a valid KT mastery score.")
    except Exception as exc:
        report["status"] = "warning"
        report["notes"].append(f"Integrated pipeline check failed but report continued: {exc}")

    return report


def _artifact_status(runtime_status: dict[str, Any]) -> dict[str, Any]:
    artifact_paths = [
        Path("models/dkt/model.pt"),
        Path("models/dkt/id_map.json"),
        Path("external/models/dkt/skillbuilder_v1/model.pt"),
        Path("external/models/dkt/skillbuilder_v1/id_map.json"),
        Path("external/models/dkt/model.pt"),
        Path("external/models/dkt/id_map.json"),
    ]
    found = [str(path) for path in artifact_paths if path.exists()]
    runtime_fields = runtime_status.get("runtime_output_fields", {})
    return {
        "artifact_paths_checked": [str(path) for path in artifact_paths],
        "artifacts_found": found,
        "dkt_model_artifact_missing": not found,
        "current_source": runtime_fields.get("source"),
        "fallback_cumulative_currently_used": runtime_fields.get("source") == "fallback_cumulative",
    }


def _overall_status(parts: list[dict[str, Any]]) -> str:
    statuses = [part.get("status") for part in parts]
    if "error" in statuses:
        return "error"
    if "warning" in statuses:
        return "warning"
    return "success"


def _limitations(artifact_status: dict[str, Any], schema_status: dict[str, Any]) -> list[str]:
    limitations = []
    if artifact_status["dkt_model_artifact_missing"]:
        limitations.append("DKT model artifact is missing.")
    if artifact_status["fallback_cumulative_currently_used"]:
        limitations.append("fallback_cumulative is currently used at runtime.")
    if schema_status.get("old_direct_mastery_row_count", 0) > 0:
        limitations.append("Old knowledge_state rows still use old_direct_mastery_format.")
    if not limitations:
        limitations.append("No current KT upgrade limitations detected by this audit.")
    return limitations


def _recommended_next_steps(report: dict[str, Any]) -> list[str]:
    steps = []
    artifact_status = report["artifact_status"]
    schema_status = report["knowledge_state_schema_status"]

    if artifact_status["dkt_model_artifact_missing"]:
        steps.append("Train or place DKT artifacts at a supported model path before enabling model-backed KT.")
    if schema_status.get("old_direct_mastery_row_count", 0) > 0:
        steps.append("Keep old-reader compatibility until a deliberate migration converts old state_json rows to kt_v2.")
    if report["runtime_kt_status"].get("status") != "success":
        steps.append("Fix runtime KT output before using it as the DKT comparison baseline.")
    if report["integrated_pipeline_status"].get("status") != "success":
        steps.append("Inspect integrated pipeline KT mastery extraction before proceeding to wider rollout.")
    if not steps:
        steps.append("Proceed to DKT training artifact preparation and comparison runs.")
    return steps


def _build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# KT Upgrade Report",
        "",
        f"Generated at: {report['generated_at']}",
        "",
        f"Overall status: `{report['overall_status']}`",
        "",
        "## Code Checks",
        "",
    ]

    code = report["code_status"]
    for key, value in code.items():
        lines.append(f"- {key}: {value}")

    schema = report["knowledge_state_schema_status"]
    runtime = report["runtime_kt_status"]
    integrated = report["integrated_pipeline_status"]
    artifacts = report["artifact_status"]

    lines.extend(
        [
            "",
            "## knowledge_state Schema",
            "",
            f"- Status: `{schema.get('status')}`",
            f"- Row count: {schema.get('row_count')}",
            f"- Schema counts: {schema.get('schema_counts')}",
            f"- KT v2 rows: {schema.get('kt_v2_row_count')}",
            f"- Old direct mastery rows: {schema.get('old_direct_mastery_row_count')}",
            "",
            "## Runtime KT Output",
            "",
            f"- Status: `{runtime.get('status')}`",
            f"- Required fields present: {runtime.get('required_fields_present')}",
            f"- Old-compatible written_state exists: {runtime.get('old_compatible_written_state_exists')}",
            f"- Runtime output fields: {runtime.get('runtime_output_fields')}",
            "",
            "## Integrated Pipeline Check",
            "",
            f"- Status: `{integrated.get('status')}`",
            f"- Called: {integrated.get('called')}",
            f"- Pipeline status: {integrated.get('pipeline_status')}",
            f"- Mastery read correctly: {integrated.get('mastery_read_correctly')}",
            f"- Mastery score: {integrated.get('mastery_score')}",
            f"- KT schema version: {integrated.get('knowledge_state_schema_version')}",
            f"- KT source: {integrated.get('knowledge_state_source')}",
            f"- KT fallback used: {integrated.get('knowledge_state_fallback_used')}",
            "",
            "## Artifact Status",
            "",
            f"- Artifacts found: {artifacts.get('artifacts_found')}",
            f"- DKT model artifact missing: {artifacts.get('dkt_model_artifact_missing')}",
            f"- Current source: {artifacts.get('current_source')}",
            f"- fallback_cumulative currently used: {artifacts.get('fallback_cumulative_currently_used')}",
            "",
            "## Current Limitations",
            "",
        ]
    )

    for limitation in report["current_limitations"]:
        lines.append(f"- {limitation}")

    lines.extend(["", "## Recommended Next Steps", ""])
    for step in report["recommended_next_steps"]:
        lines.append(f"- {step}")

    lines.extend(
        [
            "",
            "## Status",
            "",
            "```text",
            f"STATUS: {report['overall_status']}",
            "MODULE: kt_upgrade_report",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def build_report() -> dict[str, Any]:
    code_status = _code_status()
    schema_status = _knowledge_state_schema_status()
    runtime_status = _runtime_kt_status()
    integrated_status = _integrated_pipeline_status()
    artifact_status = _artifact_status(runtime_status)

    report = {
        "overall_status": _overall_status([schema_status, runtime_status, integrated_status]),
        "module": "kt_upgrade_report",
        "generated_at": _now_iso(),
        "code_status": code_status,
        "knowledge_state_schema_status": schema_status,
        "runtime_kt_status": runtime_status,
        "integrated_pipeline_status": integrated_status,
        "artifact_status": artifact_status,
        "current_limitations": _limitations(artifact_status, schema_status),
        "recommended_next_steps": [],
    }
    report["recommended_next_steps"] = _recommended_next_steps(report)
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
    print("MODULE: kt_upgrade_report")
    print(f"JSON_REPORT: {OUTPUT_JSON}")
    print(f"MD_REPORT: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
