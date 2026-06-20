import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


DB_PATH = Path("external/core_data/tutor.db")
OUTPUT_JSON = Path("evaluation_outputs/json/kt_behaviour_current_status_report.json")
OUTPUT_MD = Path("evaluation_outputs/reports/kt_behaviour_current_status_report.md")


KT_FILES = [
    "tutor/knowledge_state",
    "tutor/knowledge_state/dkt_model.py",
    "tutor/knowledge_state/run_knowledge_tracing.py",
    "tutor/knowledge_state/knowledge_state_tracker.py",
    "tutor/knowledge_state/knowledge_state_store.py",
]

BEHAVIOUR_FILES = [
    "tutor/behaviour",
    "tutor/behaviour/behavior_model.py",
    "tutor/behaviour/behaviour_model.py",
    "tutor/behaviour/run_behaviour_model.py",
    "tutor/behaviour/behavior_state_tracker.py",
    "tutor/behaviour/behaviour_state_tracker.py",
]

EXPECTED_TABLES = [
    "quiz_results",
    "knowledge_state",
    "behaviour_state",
    "decay_state",
    "learning_path_log",
    "teaching_strategy_log",
    "xai_log",
]


def _path_status(paths: list[str]) -> list[dict]:
    output = []

    for item in paths:
        path = Path(item)
        output.append(
            {
                "path": item,
                "exists": path.exists(),
                "is_file": path.is_file(),
                "is_dir": path.is_dir(),
            }
        )

    return output


def _table_exists(cursor: sqlite3.Cursor, table_name: str) -> bool:
    cursor.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name=?
        """,
        (table_name,),
    )
    return cursor.fetchone() is not None


def _table_columns(cursor: sqlite3.Cursor, table_name: str) -> list[str]:
    if not _table_exists(cursor, table_name):
        return []

    cursor.execute(f"PRAGMA table_info({table_name})")
    rows = cursor.fetchall()
    return [row[1] for row in rows]


def _table_count(cursor: sqlite3.Cursor, table_name: str) -> int | None:
    if not _table_exists(cursor, table_name):
        return None

    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    return int(cursor.fetchone()[0])


def _latest_rows(cursor: sqlite3.Cursor, table_name: str, limit: int = 3) -> list[dict]:
    if not _table_exists(cursor, table_name):
        return []

    columns = _table_columns(cursor, table_name)

    order_column = None
    for candidate in ["id", "timestamp", "created_at", "updated_at"]:
        if candidate in columns:
            order_column = candidate
            break

    if order_column:
        query = f"SELECT * FROM {table_name} ORDER BY {order_column} DESC LIMIT ?"
    else:
        query = f"SELECT * FROM {table_name} LIMIT ?"

    cursor.execute(query, (limit,))
    rows = cursor.fetchall()

    return [
        dict(zip(columns, row))
        for row in rows
    ]


def _build_db_report() -> dict:
    if not DB_PATH.exists():
        return {
            "status": "error",
            "reason": f"DB not found: {DB_PATH}",
            "tables": {},
        }

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        tables = {}

        for table_name in EXPECTED_TABLES:
            exists = _table_exists(cursor, table_name)
            tables[table_name] = {
                "exists": exists,
                "columns": _table_columns(cursor, table_name) if exists else [],
                "row_count": _table_count(cursor, table_name) if exists else None,
                "latest_rows": _latest_rows(cursor, table_name, limit=3) if exists else [],
            }

    return {
        "status": "success",
        "db_path": str(DB_PATH),
        "tables": tables,
    }


def _infer_status(report: dict) -> dict:
    kt_files = report["files"]["knowledge_tracing"]
    behaviour_files = report["files"]["behaviour"]
    tables = report["database"]["tables"]

    kt_file_count = sum(1 for item in kt_files if item["exists"])
    behaviour_file_count = sum(1 for item in behaviour_files if item["exists"])

    quiz_exists = tables.get("quiz_results", {}).get("exists", False)
    kt_table_exists = tables.get("knowledge_state", {}).get("exists", False)
    behaviour_table_exists = tables.get("behaviour_state", {}).get("exists", False)

    kt_status = "needs_inspection"
    behaviour_status = "needs_inspection"

    if kt_file_count > 0 and quiz_exists and kt_table_exists:
        kt_status = "implemented_but_needs_model_quality_audit"

    if behaviour_file_count > 0 and quiz_exists and behaviour_table_exists:
        behaviour_status = "implemented_but_needs_model_quality_audit"

    return {
        "knowledge_tracing_status": kt_status,
        "behaviour_status": behaviour_status,
        "current_assessment": {
            "knowledge_tracing": (
                "KT appears connected to quiz logs and knowledge_state storage, "
                "but needs audit for whether it uses a real trained DKT/LSTM model, "
                "how sequences are built, and whether outputs update mastery correctly."
            ),
            "behaviour": (
                "Behaviour appears connected to quiz behaviour features, "
                "but needs audit for whether LSTM/model-based prediction is active "
                "or whether output is still mostly heuristic scoring."
            ),
        },
        "next_upgrade_requirements": [
            "Inspect KT model loading and feature sequence construction.",
            "Inspect behaviour model loading and feature sequence construction.",
            "Create profile-based KT/behaviour test cases.",
            "Compare weak/average/strong learners.",
            "Generate KT/behaviour evaluation report.",
            "Plan model-based replacement if current logic is rule-based.",
        ],
    }


def _build_markdown(report: dict) -> str:
    lines = []

    lines.append("# KT + Behaviour Current Status Audit")
    lines.append("")
    lines.append(f"Generated at: {report['generated_at']}")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This audit checks the current state of Knowledge Tracing and Behaviour Modeling "
        "before the next backend intelligence upgrade."
    )
    lines.append("")
    lines.append("## File Check — Knowledge Tracing")
    lines.append("")
    for item in report["files"]["knowledge_tracing"]:
        lines.append(f"- {item['path']} — exists: {item['exists']}")
    lines.append("")
    lines.append("## File Check — Behaviour")
    lines.append("")
    for item in report["files"]["behaviour"]:
        lines.append(f"- {item['path']} — exists: {item['exists']}")
    lines.append("")
    lines.append("## Database Tables")
    lines.append("")
    lines.append("| Table | Exists | Rows | Columns |")
    lines.append("|---|---|---:|---|")

    for table_name, table_info in report["database"]["tables"].items():
        columns = ", ".join(table_info.get("columns", []))
        lines.append(
            f"| {table_name} | {table_info.get('exists')} | "
            f"{table_info.get('row_count')} | {columns} |"
        )

    lines.append("")
    lines.append("## Current Assessment")
    lines.append("")
    lines.append(f"- Knowledge Tracing: {report['inference']['knowledge_tracing_status']}")
    lines.append(f"- Behaviour: {report['inference']['behaviour_status']}")
    lines.append("")
    lines.append("### Notes")
    lines.append("")
    lines.append(f"- KT: {report['inference']['current_assessment']['knowledge_tracing']}")
    lines.append(f"- Behaviour: {report['inference']['current_assessment']['behaviour']}")
    lines.append("")
    lines.append("## Next Upgrade Requirements")
    lines.append("")
    for item in report["inference"]["next_upgrade_requirements"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Status")
    lines.append("")
    lines.append("```text")
    lines.append("KT + Behaviour current-status audit completed.")
    lines.append("```")

    return "\n".join(lines)


def main() -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "status": "success",
        "module": "KTBehaviourCurrentStatusAudit",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": {
            "knowledge_tracing": _path_status(KT_FILES),
            "behaviour": _path_status(BEHAVIOUR_FILES),
        },
        "database": _build_db_report(),
    }

    report["inference"] = _infer_status(report)

    OUTPUT_JSON.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    OUTPUT_MD.write_text(
        _build_markdown(report),
        encoding="utf-8",
    )

    print("\nKT + BEHAVIOUR CURRENT STATUS AUDIT")
    print("status:", report["status"])
    print("module:", report["module"])
    print("db_status:", report["database"].get("status"))
    print("kt_status:", report["inference"]["knowledge_tracing_status"])
    print("behaviour_status:", report["inference"]["behaviour_status"])

    print("\nFILE CHECK")
    print("KT files found:", sum(1 for x in report["files"]["knowledge_tracing"] if x["exists"]))
    print("Behaviour files found:", sum(1 for x in report["files"]["behaviour"] if x["exists"]))

    print("\nTABLE CHECK")
    for table_name, table_info in report["database"]["tables"].items():
        print(
            table_name,
            "| exists:",
            table_info.get("exists"),
            "| rows:",
            table_info.get("row_count"),
        )

    print("\nSaved JSON:", OUTPUT_JSON)
    print("Saved Markdown:", OUTPUT_MD)

    print("\nSTATUS: success")
    print("MODULE: kt_behaviour_current_status_audit")


if __name__ == "__main__":
    main()