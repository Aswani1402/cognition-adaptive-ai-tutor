from __future__ import annotations

import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DB_PATH = Path("external/core_data/tutor.db")
OUTPUT_JSON = Path("evaluation_outputs/json/kt_state_schema_runtime_report.json")
OUTPUT_MD = Path("evaluation_outputs/reports/kt_state_schema_runtime_report.md")
RUNTIME_LEARNER_ID = "14"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect_readonly(db_path: Path) -> sqlite3.Connection:
    uri = f"file:{db_path.resolve().as_posix()}?mode=ro&immutable=1"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _connect_writable(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
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


def _latest_rows(
    cursor: sqlite3.Cursor,
    table_name: str,
    columns: list[str],
    limit: int = 5,
) -> list[dict[str, Any]]:
    if not columns:
        return []

    order_column = None
    for candidate in ["updated_at", "timestamp", "created_at", "quiz_id", "id", "student_id"]:
        if candidate in columns:
            order_column = candidate
            break

    if order_column:
        query = f"SELECT * FROM {table_name} ORDER BY {order_column} DESC LIMIT ?"
    else:
        query = f"SELECT * FROM {table_name} LIMIT ?"

    return [_row_to_dict(row) or {} for row in cursor.execute(query, (limit,)).fetchall()]


def _latest_knowledge_state_row(cursor: sqlite3.Cursor) -> dict[str, Any] | None:
    columns = _table_columns(cursor, "knowledge_state")
    if not columns:
        return None

    order_column = "updated_at" if "updated_at" in columns else columns[0]
    row = cursor.execute(
        f"SELECT * FROM knowledge_state ORDER BY {order_column} DESC LIMIT 1"
    ).fetchone()
    return _row_to_dict(row)


def _json_preview(value: Any, max_chars: int = 500) -> str:
    text = json.dumps(value, ensure_ascii=False, default=str)
    return text[:max_chars]


def _detect_state_json_schema(raw_state: Any) -> str:
    if raw_state is None or str(raw_state).strip() == "":
        return "empty_state"

    try:
        parsed = json.loads(str(raw_state))
    except Exception:
        return "invalid_json"

    if parsed in [None, "", {}, []]:
        return "empty_state"

    if isinstance(parsed, dict):
        version = str(parsed.get("version") or parsed.get("schema_version") or "").lower()
        if "kt_v2" in version or version in {"2", "v2"}:
            return "kt_v2_format"
        if "kt_v1" in version or version in {"1", "v1"}:
            return "kt_v1_format"

        kt_v2_keys = {"schema_version", "learner_id", "concept_states", "mastery_by_concept", "updated_at"}
        kt_v1_keys = {"mastery", "confidence", "last_interaction", "concept_id"}
        if kt_v2_keys.intersection(parsed.keys()) and (
            "concept_states" in parsed or "mastery_by_concept" in parsed
        ):
            return "kt_v2_format"
        if kt_v1_keys.intersection(parsed.keys()) and (
            "mastery" in parsed or "confidence" in parsed
        ):
            return "kt_v1_format"

        mastery_values = []
        for value in parsed.values():
            try:
                mastery_values.append(float(value))
            except Exception:
                mastery_values = []
                break

        if mastery_values and all(0.0 <= item <= 1.0 for item in mastery_values):
            return "old_direct_mastery_format"

    return "invalid_json"


def _inspect_state_json(cursor: sqlite3.Cursor, columns: list[str]) -> dict[str, Any]:
    if "state_json" not in columns:
        return {
            "state_json_exists": False,
            "schema_counts": {},
            "sample_parsed_states": [],
            "notes": ["knowledge_state.state_json column does not exist."],
        }

    schema_counts: Counter[str] = Counter()
    samples = []
    rows = cursor.execute(
        """
        SELECT state_json
        FROM knowledge_state
        LIMIT 1000
        """
    ).fetchall()

    for row in rows:
        schema_type = _detect_state_json_schema(row["state_json"])
        schema_counts[schema_type] += 1
        if len(samples) < 5:
            preview: dict[str, Any] = {
                "schema_type": schema_type,
                "raw_preview": str(row["state_json"])[:500],
            }
            try:
                preview["parsed_preview"] = _json_preview(json.loads(row["state_json"]))
            except Exception:
                preview["parsed_preview"] = None
            samples.append(preview)

    return {
        "state_json_exists": True,
        "schema_counts": dict(schema_counts),
        "sample_parsed_states": samples,
        "notes": [],
    }


def _inspect_direct_mastery_columns(columns: list[str]) -> dict[str, Any]:
    expected = ["learner_id", "student_id", "concept_id", "mastery", "updated_at", "timestamp", "confidence"]
    present = [column for column in expected if column in columns]
    return {
        "present_columns": present,
        "learner_id_available": "learner_id" in columns or "student_id" in columns,
        "concept_id_available": "concept_id" in columns,
        "mastery_available": "mastery" in columns,
        "timestamp_available": "updated_at" in columns or "timestamp" in columns,
        "confidence_available": "confidence" in columns,
        "direct_mastery_format_available": bool(
            ("learner_id" in columns or "student_id" in columns)
            and "concept_id" in columns
            and "mastery" in columns
        ),
    }


def _audit_knowledge_state_table() -> dict[str, Any]:
    report: dict[str, Any] = {
        "db_path": str(DB_PATH),
        "db_exists": DB_PATH.exists(),
        "knowledge_state_exists": False,
        "status": "warning",
        "row_count": 0,
        "columns": [],
        "sample_rows": [],
        "direct_mastery_columns": {},
        "notes": [],
    }

    if not DB_PATH.exists():
        report["status"] = "error"
        report["notes"].append("tutor.db not found.")
        return report

    try:
        with _connect_readonly(DB_PATH) as conn:
            cursor = conn.cursor()
            if not _table_exists(cursor, "knowledge_state"):
                report["status"] = "error"
                report["notes"].append("knowledge_state table not found.")
                return report

            columns = _table_columns(cursor, "knowledge_state")
            report["knowledge_state_exists"] = True
            report["columns"] = columns
            report["row_count"] = int(
                cursor.execute("SELECT COUNT(*) FROM knowledge_state").fetchone()[0] or 0
            )
            report["sample_rows"] = _latest_rows(cursor, "knowledge_state", columns, limit=5)
            report["direct_mastery_columns"] = _inspect_direct_mastery_columns(columns)
            report.update(_inspect_state_json(cursor, columns))

            warnings = []
            if report["row_count"] == 0:
                warnings.append("knowledge_state table exists but has no rows.")
            if "state_json" not in columns and not report["direct_mastery_columns"]["direct_mastery_format_available"]:
                warnings.append("No state_json or direct mastery schema found.")
            report["notes"].extend(warnings)
            report["status"] = "warning" if warnings else "success"
    except Exception as exc:
        report["status"] = "error"
        report["notes"].append(f"knowledge_state audit failed: {exc}")

    return report


def _summarize_runtime_output(output: Any) -> dict[str, Any]:
    if not isinstance(output, dict):
        return {
            "status": "error",
            "error": "Runtime KT output was not a dictionary.",
            "output_type": type(output).__name__,
            "raw_output": str(output),
        }

    data = output.get("data") if isinstance(output.get("data"), dict) else {}
    return {
        "status": output.get("status"),
        "module": output.get("module") or "knowledge_state",
        "source": output.get("source") or "tutor.knowledge_state.update.update_knowledge_state",
        "fallback_used": output.get("fallback_used") or data.get("fallback_used"),
        "predicted_mastery_last": output.get("predicted_mastery_last") or data.get("predicted_mastery_last"),
        "written_state": output.get("written_state") or data.get("written_state"),
        "sequence_length": data.get("sequence_length"),
        "error": output.get("error"),
        "raw_output": output,
    }


def _runtime_kt_check() -> dict[str, Any]:
    report: dict[str, Any] = {
        "status": "warning",
        "learner_id": RUNTIME_LEARNER_ID,
        "runtime_call_attempted": False,
        "runtime_call_can_write": True,
        "write_note": (
            "This audit calls the active KT update for learner 14. The active updater "
            "uses an upsert into knowledge_state, so this optional runtime check may write "
            "or refresh that learner's KT state."
        ),
        "before": {},
        "after": {},
        "runtime_output_fields": {},
        "notes": [],
    }

    if not DB_PATH.exists():
        report["status"] = "error"
        report["notes"].append("Runtime KT check skipped because tutor.db is missing.")
        return report

    try:
        with _connect_readonly(DB_PATH) as conn:
            cursor = conn.cursor()
            report["before"] = {
                "knowledge_state_row_count": int(
                    cursor.execute("SELECT COUNT(*) FROM knowledge_state").fetchone()[0] or 0
                )
                if _table_exists(cursor, "knowledge_state")
                else None,
                "latest_row": _latest_knowledge_state_row(cursor)
                if _table_exists(cursor, "knowledge_state")
                else None,
            }
    except Exception as exc:
        report["before_error"] = str(exc)

    try:
        from tutor.knowledge_state.update import update_knowledge_state

        report["runtime_call_attempted"] = True
        with _connect_writable(DB_PATH) as conn:
            output = update_knowledge_state(conn, RUNTIME_LEARNER_ID)
        report["runtime_output_fields"] = _summarize_runtime_output(output)
    except Exception as exc:
        report["runtime_output_fields"] = {
            "status": "error",
            "module": "knowledge_state",
            "source": "tutor.knowledge_state.update.update_knowledge_state",
            "error": str(exc),
        }

    try:
        with _connect_readonly(DB_PATH) as conn:
            cursor = conn.cursor()
            report["after"] = {
                "knowledge_state_row_count": int(
                    cursor.execute("SELECT COUNT(*) FROM knowledge_state").fetchone()[0] or 0
                )
                if _table_exists(cursor, "knowledge_state")
                else None,
                "latest_row": _latest_knowledge_state_row(cursor)
                if _table_exists(cursor, "knowledge_state")
                else None,
            }
    except Exception as exc:
        report["after_error"] = str(exc)

    output_status = report["runtime_output_fields"].get("status")
    if output_status == "success":
        report["status"] = "success"
    else:
        report["status"] = "warning"
        report["notes"].append("Runtime KT call failed or returned non-success; main audit continued.")

    return report


def _audit_concept_mapping() -> dict[str, Any]:
    report: dict[str, Any] = {
        "status": "warning",
        "concept_id_map_exists": False,
        "mapping_count": 0,
        "quiz_results_concept_count": None,
        "mapped_quiz_concept_count": None,
        "unmapped_quiz_concept_count": None,
        "unmapped_quiz_concept_samples": [],
        "notes": [],
    }

    if not DB_PATH.exists():
        report["status"] = "error"
        report["notes"].append("tutor.db not found.")
        return report

    try:
        with _connect_readonly(DB_PATH) as conn:
            cursor = conn.cursor()
            if not _table_exists(cursor, "concept_id_map"):
                report["status"] = "warning"
                report["notes"].append("concept_id_map table not found.")
                return report

            report["concept_id_map_exists"] = True
            report["mapping_count"] = int(
                cursor.execute("SELECT COUNT(*) FROM concept_id_map").fetchone()[0] or 0
            )

            if not _table_exists(cursor, "quiz_results"):
                report["notes"].append("quiz_results table not found; cannot check mapping coverage.")
                return report

            quiz_values = {
                str(row[0]).strip()
                for row in cursor.execute(
                    "SELECT DISTINCT concept_id FROM quiz_results WHERE concept_id IS NOT NULL"
                ).fetchall()
                if str(row[0]).strip()
            }
            system_ids = {
                str(row[0]).strip()
                for row in cursor.execute(
                    "SELECT system_concept_id FROM concept_id_map WHERE system_concept_id IS NOT NULL"
                ).fetchall()
                if str(row[0]).strip()
            }
            content_ids = {
                str(row[0]).strip().upper()
                for row in cursor.execute(
                    "SELECT content_concept_id FROM concept_id_map WHERE content_concept_id IS NOT NULL"
                ).fetchall()
                if str(row[0]).strip()
            }

            mapped = {
                value
                for value in quiz_values
                if value in system_ids or value.upper() in content_ids
            }
            unmapped = sorted(quiz_values - mapped)

            report["quiz_results_concept_count"] = len(quiz_values)
            report["mapped_quiz_concept_count"] = len(mapped)
            report["unmapped_quiz_concept_count"] = len(unmapped)
            report["unmapped_quiz_concept_samples"] = unmapped[:20]

            warnings = []
            if report["mapping_count"] == 0:
                warnings.append("concept_id_map exists but has no rows.")
            if unmapped:
                warnings.append("Some quiz_results concept_id values do not map to concept_id_map.")

            report["notes"].extend(warnings)
            report["status"] = "warning" if warnings else "success"
    except Exception as exc:
        report["status"] = "error"
        report["notes"].append(f"concept mapping audit failed: {exc}")

    return report


def _schema_standardization_needed(knowledge_state_report: dict[str, Any]) -> bool:
    counts = knowledge_state_report.get("schema_counts") or knowledge_state_report.get("state_json_schema_counts") or {}
    direct = knowledge_state_report.get("direct_mastery_columns", {})
    if not knowledge_state_report.get("knowledge_state_exists"):
        return True
    if counts.get("invalid_json", 0) or counts.get("empty_state", 0):
        return True
    if len([key for key, value in counts.items() if value]) > 1:
        return True
    if counts.get("old_direct_mastery_format", 0) and not direct.get("direct_mastery_format_available"):
        return True
    return False


def _overall_status(parts: list[dict[str, Any]], standardization_needed: bool) -> str:
    statuses = [part.get("status") for part in parts]
    if "error" in statuses:
        return "error"
    if "warning" in statuses or standardization_needed:
        return "warning"
    return "success"


def _recommended_next_steps(report: dict[str, Any]) -> list[str]:
    steps = []
    knowledge = report["knowledge_state_status"]
    runtime = report["runtime_kt_status"]
    mapping = report["concept_mapping_status"]

    if report["schema_standardization_needed"]:
        steps.append("Standardize knowledge_state.state_json into one documented KT schema before DKT runtime upgrade.")
    if knowledge.get("schema_counts", {}).get("old_direct_mastery_format", 0):
        steps.append("Add a KT v2 wrapper schema around concept mastery values, including learner_id, model_source, confidence, and updated_at.")
    if runtime.get("runtime_output_fields", {}).get("status") != "success":
        steps.append("Fix or document the active KT runtime update failure before comparing DKT output.")
    if mapping.get("unmapped_quiz_concept_count"):
        steps.append("Complete concept_id_map coverage for quiz_results concept_id values before DKT sequence mapping.")
    if not steps:
        steps.append("Proceed to DKT runtime comparison using learner 14 as a smoke-test case.")

    return steps


def _build_markdown(report: dict[str, Any]) -> str:
    knowledge = report["knowledge_state_status"]
    runtime = report["runtime_kt_status"]
    mapping = report["concept_mapping_status"]

    lines = [
        "# KT State Schema Runtime Audit",
        "",
        f"Generated at: {report['generated_at']}",
        "",
        f"Overall status: `{report['overall_status']}`",
        "",
        "## knowledge_state Table",
        "",
        f"- DB exists: {knowledge.get('db_exists')}",
        f"- Table exists: {knowledge.get('knowledge_state_exists')}",
        f"- Status: `{knowledge.get('status')}`",
        f"- Row count: {knowledge.get('row_count')}",
        f"- Columns: {', '.join(knowledge.get('columns', [])) or 'None'}",
        f"- Direct mastery columns: {knowledge.get('direct_mastery_columns')}",
        "",
        "## state_json Schema Counts",
        "",
    ]

    counts = report.get("state_json_schema_counts", {})
    if counts:
        for key, value in counts.items():
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Runtime KT Check",
            "",
            f"- Status: `{runtime.get('status')}`",
            f"- Learner ID: {runtime.get('learner_id')}",
            f"- Runtime call attempted: {runtime.get('runtime_call_attempted')}",
            f"- Runtime call can write: {runtime.get('runtime_call_can_write')}",
            f"- Write note: {runtime.get('write_note')}",
            f"- Before row count: {runtime.get('before', {}).get('knowledge_state_row_count')}",
            f"- After row count: {runtime.get('after', {}).get('knowledge_state_row_count')}",
            f"- Runtime output fields: {runtime.get('runtime_output_fields')}",
            "",
            "## Concept Mapping",
            "",
            f"- Status: `{mapping.get('status')}`",
            f"- concept_id_map exists: {mapping.get('concept_id_map_exists')}",
            f"- Mapping count: {mapping.get('mapping_count')}",
            f"- quiz_results concept count: {mapping.get('quiz_results_concept_count')}",
            f"- Mapped quiz concept count: {mapping.get('mapped_quiz_concept_count')}",
            f"- Unmapped quiz concept count: {mapping.get('unmapped_quiz_concept_count')}",
            f"- Unmapped samples: {mapping.get('unmapped_quiz_concept_samples')}",
            "",
            "## Schema Standardization",
            "",
            f"- Needed: {report.get('schema_standardization_needed')}",
            "",
            "## Recommended Next Steps",
            "",
        ]
    )

    for step in report["recommended_next_steps"]:
        lines.append(f"- {step}")

    lines.extend(
        [
            "",
            "## Status",
            "",
            "```text",
            f"STATUS: {report['overall_status']}",
            "MODULE: kt_state_schema_runtime",
            "```",
            "",
        ]
    )

    return "\n".join(lines)


def build_report() -> dict[str, Any]:
    knowledge_state_report = _audit_knowledge_state_table()
    runtime_report = _runtime_kt_check()
    concept_mapping_report = _audit_concept_mapping()

    state_json_schema_counts = knowledge_state_report.get("schema_counts", {})
    knowledge_state_report["state_json_schema_counts"] = state_json_schema_counts

    standardization_needed = _schema_standardization_needed(knowledge_state_report)

    report = {
        "overall_status": _overall_status(
            [knowledge_state_report, runtime_report, concept_mapping_report],
            standardization_needed=standardization_needed,
        ),
        "module": "kt_state_schema_runtime",
        "generated_at": _now_iso(),
        "knowledge_state_status": knowledge_state_report,
        "state_json_schema_counts": state_json_schema_counts,
        "runtime_kt_status": runtime_report,
        "concept_mapping_status": concept_mapping_report,
        "schema_standardization_needed": standardization_needed,
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
    print("MODULE: kt_state_schema_runtime")
    print(f"JSON_REPORT: {OUTPUT_JSON}")
    print(f"MD_REPORT: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
