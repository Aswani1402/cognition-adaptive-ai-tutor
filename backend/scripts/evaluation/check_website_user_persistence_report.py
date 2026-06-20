from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from scripts.migration.create_user_persistence_tables import TABLE_NAMES, create_tables


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "external" / "core_data" / "tutor.db"
JSON_REPORT = PROJECT_ROOT / "evaluation_outputs" / "json" / "website_user_persistence_report.json"
MD_REPORT = PROJECT_ROOT / "evaluation_outputs" / "reports" / "website_user_persistence_report.md"


def _table_exists(cursor: sqlite3.Cursor, table_name: str) -> bool:
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    )
    return cursor.fetchone() is not None


def _row_count(cursor: sqlite3.Cursor, table_name: str) -> int:
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    return int(cursor.fetchone()[0])


def build_report() -> dict[str, Any]:
    create_tables(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    table_existence = {table_name: _table_exists(cursor, table_name) for table_name in TABLE_NAMES}
    row_counts = {
        table_name: _row_count(cursor, table_name)
        for table_name, exists in table_existence.items()
        if exists
    }
    missing_tables = [table_name for table_name, exists in table_existence.items() if not exists]
    conn.close()

    readiness = {
        "user_login_flow_readiness": table_existence.get("users", False)
        and table_existence.get("learner_profile", False),
        "subject_concept_selection_readiness": table_existence.get("learner_profile", False)
        and table_existence.get("learner_concept_progress", False),
        "session_save_resume_readiness": table_existence.get("learner_session_state", False)
        and table_existence.get("learner_session_log", False),
        "memory_mistake_doubt_revision_persistence_readiness": all(
            table_existence.get(table_name, False)
            for table_name in [
                "learner_mistake_log",
                "learner_doubt_log",
                "revision_schedule",
                "revision_card",
                "revision_attempt_log",
            ]
        ),
        "long_term_personalization_readiness": all(
            table_existence.get(table_name, False)
            for table_name in [
                "learner_profile",
                "learner_concept_progress",
                "learner_view_progress",
                "agent_orchestration_log",
            ]
        ),
    }

    frontend_api_needs = [
        "POST /auth/register to create users and learner_profile rows with secure password hashing.",
        "POST /auth/login to verify credentials, update last_login_at, and return user/learner identifiers.",
        "GET /learner/context to call build_returning_user_context for resume state.",
        "POST /learner/session to save active teaching packet and selected subject/concept.",
        "POST /learner/evaluation to persist mistakes, concept progress, agent trace, and revision needs after answers.",
        "POST /learner/doubt to persist learner questions and grounded answer summaries.",
        "GET /learner/revision and POST /learner/revision/attempt for due cards and outcomes.",
    ]
    limitations = [
        "Authentication routes are not implemented yet; this layer provides database and store primitives.",
        "Password hashes are demo placeholders in create_demo_user and must be replaced by a production password hasher.",
        "Foreign keys are intentionally not enforced yet to avoid breaking existing pipeline writes.",
        "Existing knowledge_state, behaviour_state, decay_state, reward, teaching, and XAI tables are not migrated here; this layer complements them.",
        "Revision intervals are stored but not yet updated by a trained retention policy.",
    ]

    status = "success" if not missing_tables and all(readiness.values()) else "warning"
    return {
        "status": status,
        "module": "website_user_persistence_report",
        "db_path": str(DB_PATH),
        "table_existence": table_existence,
        "row_counts": row_counts,
        "readiness": readiness,
        "frontend_api_needs": frontend_api_needs,
        "limitations": limitations,
    }


def write_reports(report: dict[str, Any]) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# Website User Persistence Report",
        "",
        f"Status: **{report['status']}**",
        f"Database: `{report['db_path']}`",
        "",
        "## Table Existence",
        "",
    ]
    for table_name, exists in report["table_existence"].items():
        lines.append(f"- {table_name}: {'present' if exists else 'missing'}")

    lines.extend(["", "## Row Counts", ""])
    for table_name, count in report["row_counts"].items():
        lines.append(f"- {table_name}: {count}")

    lines.extend(["", "## Readiness", ""])
    readiness_labels = {
        "user_login_flow_readiness": "User/login flow readiness",
        "subject_concept_selection_readiness": "Subject/concept selection readiness",
        "session_save_resume_readiness": "Session save/resume readiness",
        "memory_mistake_doubt_revision_persistence_readiness": "Memory/mistake/doubt/revision persistence readiness",
        "long_term_personalization_readiness": "Long-term personalization readiness",
    }
    for key, label in readiness_labels.items():
        lines.append(f"- {label}: {'ready' if report['readiness'][key] else 'not ready'}")

    lines.extend(["", "## Frontend API Needs", ""])
    for item in report["frontend_api_needs"]:
        lines.append(f"- {item}")

    lines.extend(["", "## Limitations", ""])
    for item in report["limitations"]:
        lines.append(f"- {item}")

    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_report()
    write_reports(report)
    print(f"STATUS: {report['status']}")
    print("MODULE: website_user_persistence_report")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
