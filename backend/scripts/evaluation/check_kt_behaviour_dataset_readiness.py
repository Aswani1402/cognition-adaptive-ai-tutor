from __future__ import annotations

import csv
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


ASSISTMENTS_PATH = Path("external/dataset/assistments.csv")
DB_PATH = Path("external/core_data/tutor.db")
OUTPUT_JSON = Path("evaluation_outputs/json/kt_behaviour_dataset_readiness_report.json")
OUTPUT_MD = Path("evaluation_outputs/reports/kt_behaviour_dataset_readiness_report.md")

KT_COLUMN_GROUPS = {
    "learner": ["learner_id", "user_id", "student_id"],
    "concept": ["concept_id", "skill_id", "problem_id"],
    "correctness": ["correct", "is_correct", "answer_correct"],
    "ordering": ["timestamp", "order_id"],
}

BEHAVIOUR_FEATURE_COLUMNS = [
    "time_taken_sec",
    "confidence",
    "hint_used",
    "hint_count",
    "option_changes_count",
    "is_correct",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_column(name: str) -> str:
    return str(name or "").strip().lower()


def _matching_columns(columns: list[str], candidates: list[str]) -> list[str]:
    normalized = {_normalize_column(column): column for column in columns}
    return [normalized[item] for item in candidates if item in normalized]


def _status_from_issues(errors: list[str], warnings: list[str]) -> str:
    if errors:
        return "error"
    if warnings:
        return "warning"
    return "success"


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    number = _safe_float(value)
    if number is None:
        return None
    return int(number)


def _sequence_stats(lengths: list[int]) -> dict[str, Any]:
    if not lengths:
        return {
            "min": None,
            "avg": None,
            "max": None,
            "count": 0,
        }

    return {
        "min": min(lengths),
        "avg": round(mean(lengths), 3),
        "max": max(lengths),
        "count": len(lengths),
    }


def _audit_assistments_csv() -> dict[str, Any]:
    report: dict[str, Any] = {
        "path": str(ASSISTMENTS_PATH),
        "exists": ASSISTMENTS_PATH.exists(),
        "status": "warning",
        "row_count": 0,
        "columns": [],
        "usable_columns": {},
        "missing_required_or_usable_columns": [],
        "can_support_dkt_sequences": False,
        "notes": [],
    }

    if not ASSISTMENTS_PATH.exists():
        report["missing_required_or_usable_columns"] = [
            "learner",
            "concept",
            "correctness",
            "ordering_optional_but_recommended",
        ]
        report["notes"].append("assistments.csv not found; external KT/DKT dataset is not available yet.")
        return report

    try:
        with ASSISTMENTS_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            columns = list(reader.fieldnames or [])
            report["columns"] = columns

            usable_columns = {
                group: _matching_columns(columns, candidates)
                for group, candidates in KT_COLUMN_GROUPS.items()
            }
            report["usable_columns"] = usable_columns

            missing = [
                group
                for group in ["learner", "concept", "correctness"]
                if not usable_columns.get(group)
            ]
            if not usable_columns.get("ordering"):
                missing.append("ordering_optional_but_recommended")
            report["missing_required_or_usable_columns"] = missing

            learner_col = usable_columns.get("learner", [None])[0]
            concept_col = usable_columns.get("concept", [None])[0]
            correct_col = usable_columns.get("correctness", [None])[0]
            order_col = usable_columns.get("ordering", [None])[0]

            learner_counts: Counter[str] = Counter()
            concept_values: set[str] = set()
            correctness_non_null = 0
            order_non_null = 0

            for row in reader:
                report["row_count"] += 1
                if learner_col and str(row.get(learner_col, "")).strip():
                    learner_counts[str(row.get(learner_col)).strip()] += 1
                if concept_col and str(row.get(concept_col, "")).strip():
                    concept_values.add(str(row.get(concept_col)).strip())
                if correct_col and str(row.get(correct_col, "")).strip():
                    correctness_non_null += 1
                if order_col and str(row.get(order_col, "")).strip():
                    order_non_null += 1

            sequence_lengths = list(learner_counts.values())
            report["learner_count"] = len(learner_counts)
            report["concept_count"] = len(concept_values)
            report["correctness_non_null_count"] = correctness_non_null
            report["ordering_non_null_count"] = order_non_null
            report["sequence_length_per_learner"] = _sequence_stats(sequence_lengths)

            report["can_support_dkt_sequences"] = bool(
                report["row_count"] > 0
                and learner_col
                and concept_col
                and correct_col
                and len(learner_counts) > 0
                and max(sequence_lengths or [0]) >= 2
            )

            warnings = []
            if missing:
                warnings.append("Missing one or more required/usable KT columns.")
            if not report["can_support_dkt_sequences"]:
                warnings.append("Dataset does not yet look sequence-ready for DKT.")
            if report["row_count"] < 1000:
                warnings.append("Dataset has fewer than 1,000 rows; useful for smoke tests, weak for DKT training.")

            report["status"] = "warning" if warnings else "success"
            report["notes"].extend(warnings)
            return report

    except Exception as exc:
        report["status"] = "error"
        report["notes"].append(f"CSV audit failed: {exc}")
        return report


def _connect_readonly(db_path: Path) -> sqlite3.Connection:
    uri = f"file:{db_path.resolve().as_posix()}?mode=ro&immutable=1"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


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
    rows = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [str(row[1]) for row in rows]


def _count_distinct(cursor: sqlite3.Cursor, table_name: str, column: str | None) -> int | None:
    if not column:
        return None
    row = cursor.execute(
        f"SELECT COUNT(DISTINCT {column}) FROM {table_name} WHERE {column} IS NOT NULL"
    ).fetchone()
    return int(row[0] or 0)


def _non_null_count(cursor: sqlite3.Cursor, table_name: str, column: str) -> int:
    row = cursor.execute(
        f"SELECT COUNT(*) FROM {table_name} WHERE {column} IS NOT NULL AND CAST({column} AS TEXT) != ''"
    ).fetchone()
    return int(row[0] or 0)


def _find_first_column(columns: list[str], candidates: list[str]) -> str | None:
    matches = _matching_columns(columns, candidates)
    return matches[0] if matches else None


def _group_lengths(cursor: sqlite3.Cursor, table_name: str, group_columns: list[str]) -> list[int]:
    select_cols = ", ".join(group_columns)
    query = (
        f"SELECT {select_cols}, COUNT(*) AS n "
        f"FROM {table_name} "
        f"WHERE " + " AND ".join(f"{column} IS NOT NULL" for column in group_columns) + " "
        f"GROUP BY {select_cols}"
    )
    rows = cursor.execute(query).fetchall()
    return [int(row["n"]) for row in rows]


def _proxy_label_for_row(row: sqlite3.Row, available_columns: set[str]) -> str:
    is_correct = _safe_int(row["is_correct"]) if "is_correct" in available_columns else None
    time_taken = _safe_float(row["time_taken_sec"]) if "time_taken_sec" in available_columns else None
    confidence = _safe_float(row["confidence"]) if "confidence" in available_columns else None
    hint_count = None
    if "hint_count" in available_columns:
        hint_count = _safe_int(row["hint_count"])
    elif "hint_used" in available_columns:
        hint_count = _safe_int(row["hint_used"])
    option_changes = (
        _safe_int(row["option_changes_count"])
        if "option_changes_count" in available_columns
        else None
    )

    hints_high = hint_count is not None and hint_count >= 2
    many_changes = option_changes is not None and option_changes >= 3
    low_confidence = confidence is not None and confidence <= 0.35
    slow = time_taken is not None and time_taken >= 120
    very_fast = time_taken is not None and time_taken <= 5

    if is_correct == 0 and (hints_high or low_confidence or slow):
        return "struggling"
    if is_correct == 0 and (many_changes or very_fast):
        return "guessing"
    if low_confidence or hints_high or many_changes:
        return "confused"
    return "stable"


def _audit_tutor_db() -> tuple[dict[str, Any], dict[str, Any]]:
    tutor_report: dict[str, Any] = {
        "path": str(DB_PATH),
        "exists": DB_PATH.exists(),
        "status": "warning",
        "quiz_results_exists": False,
        "row_count": 0,
        "columns": [],
        "learner_count": None,
        "concept_count": None,
        "interaction_count": 0,
        "sequence_length_per_learner": _sequence_stats([]),
        "sequence_length_per_learner_concept": _sequence_stats([]),
        "enough_data_for_runtime_kt_validation": False,
        "notes": [],
    }
    behaviour_report: dict[str, Any] = {
        "status": "warning",
        "feature_availability": {},
        "proxy_label_readiness": {
            "status": "warning",
            "existing_label_columns": [],
            "proxy_labels_generated": False,
            "proxy_label_distribution": {},
            "rules_note": (
                "Proxy labels are transparent audit estimates only and must not be treated "
                "as final model-training labels without review."
            ),
        },
        "notes": [],
    }

    if not DB_PATH.exists():
        tutor_report["status"] = "error"
        tutor_report["notes"].append("tutor.db not found.")
        behaviour_report["status"] = "error"
        behaviour_report["notes"].append("Cannot inspect quiz_results because tutor.db is missing.")
        return tutor_report, behaviour_report

    try:
        with _connect_readonly(DB_PATH) as conn:
            cursor = conn.cursor()
            if not _table_exists(cursor, "quiz_results"):
                tutor_report["status"] = "error"
                tutor_report["notes"].append("quiz_results table not found.")
                behaviour_report["status"] = "error"
                behaviour_report["notes"].append("Behaviour features unavailable because quiz_results table is missing.")
                return tutor_report, behaviour_report

            columns = _table_columns(cursor, "quiz_results")
            column_set = set(columns)
            tutor_report["quiz_results_exists"] = True
            tutor_report["columns"] = columns

            row_count = int(cursor.execute("SELECT COUNT(*) FROM quiz_results").fetchone()[0] or 0)
            tutor_report["row_count"] = row_count
            tutor_report["interaction_count"] = row_count

            learner_col = _find_first_column(columns, ["learner_id", "user_id", "student_id"])
            concept_col = _find_first_column(columns, ["concept_id", "skill_id", "problem_id", "system_concept_id"])

            tutor_report["learner_column_used"] = learner_col
            tutor_report["concept_column_used"] = concept_col
            tutor_report["learner_count"] = _count_distinct(cursor, "quiz_results", learner_col)
            tutor_report["concept_count"] = _count_distinct(cursor, "quiz_results", concept_col)

            if learner_col:
                learner_lengths = _group_lengths(cursor, "quiz_results", [learner_col])
                tutor_report["sequence_length_per_learner"] = _sequence_stats(learner_lengths)

            if learner_col and concept_col:
                learner_concept_lengths = _group_lengths(cursor, "quiz_results", [learner_col, concept_col])
                tutor_report["sequence_length_per_learner_concept"] = _sequence_stats(learner_concept_lengths)

            enough_data = bool(
                row_count >= 20
                and (tutor_report["learner_count"] or 0) >= 1
                and tutor_report["sequence_length_per_learner"]["max"] is not None
                and tutor_report["sequence_length_per_learner"]["max"] >= 5
            )
            tutor_report["enough_data_for_runtime_kt_validation"] = enough_data

            tutor_warnings = []
            if not learner_col:
                tutor_warnings.append("No learner id column found in quiz_results.")
            if not concept_col:
                tutor_warnings.append("No concept/problem column found in quiz_results.")
            if not enough_data:
                tutor_warnings.append("quiz_results is not yet large enough for strong runtime KT validation.")
            tutor_report["notes"].extend(tutor_warnings)
            tutor_report["status"] = "warning" if tutor_warnings else "success"

            for feature in BEHAVIOUR_FEATURE_COLUMNS:
                exists = feature in column_set
                non_null = _non_null_count(cursor, "quiz_results", feature) if exists else 0
                behaviour_report["feature_availability"][feature] = {
                    "exists": exists,
                    "non_null_count": non_null,
                    "non_null_ratio": round(non_null / row_count, 4) if row_count else 0.0,
                    "usable": exists and non_null > 0,
                }

            label_columns = [
                column for column in columns
                if _normalize_column(column) in {"behavior_label", "behaviour_label", "label", "engagement_label"}
            ]
            behaviour_report["proxy_label_readiness"]["existing_label_columns"] = label_columns

            usable_feature_count = sum(
                1
                for item in behaviour_report["feature_availability"].values()
                if item["usable"]
            )

            if not label_columns and usable_feature_count > 0 and row_count > 0:
                select_columns = [
                    column for column in BEHAVIOUR_FEATURE_COLUMNS
                    if column in column_set
                ]
                query = f"SELECT {', '.join(select_columns)} FROM quiz_results"
                distribution: Counter[str] = Counter()
                for row in cursor.execute(query).fetchall():
                    distribution[_proxy_label_for_row(row, column_set)] += 1

                behaviour_report["proxy_label_readiness"]["proxy_labels_generated"] = True
                behaviour_report["proxy_label_readiness"]["proxy_label_distribution"] = {
                    label: int(distribution.get(label, 0))
                    for label in ["stable", "confused", "guessing", "struggling"]
                }
                behaviour_report["proxy_label_readiness"]["status"] = "success"
            elif label_columns:
                behaviour_report["proxy_label_readiness"]["status"] = "success"
                behaviour_report["proxy_label_readiness"]["note"] = "Existing label column found; proxy labels not required for audit."
            else:
                behaviour_report["proxy_label_readiness"]["status"] = "warning"
                behaviour_report["notes"].append("No existing labels and no usable behaviour feature values for proxy labels.")

            behaviour_warnings = []
            if usable_feature_count < 3:
                behaviour_warnings.append("Fewer than three behaviour feature columns have non-null values.")
            if behaviour_report["proxy_label_readiness"]["status"] != "success":
                behaviour_warnings.append("Proxy-label readiness is incomplete.")
            behaviour_report["notes"].extend(behaviour_warnings)
            behaviour_report["status"] = "warning" if behaviour_warnings else "success"

    except Exception as exc:
        tutor_report["status"] = "error"
        tutor_report["notes"].append(f"DB audit failed: {exc}")
        behaviour_report["status"] = "error"
        behaviour_report["notes"].append(f"Behaviour audit failed: {exc}")

    return tutor_report, behaviour_report


def _recommended_next_steps(report: dict[str, Any]) -> list[str]:
    steps = []
    kt_dataset = report["kt_dataset_status"]
    tutor_db = report["tutor_db_status"]
    behaviour = report["behaviour_dataset_status"]

    if not kt_dataset.get("exists"):
        steps.append("Add external/dataset/assistments.csv or update the audit path before DKT dataset preparation.")
    elif not kt_dataset.get("can_support_dkt_sequences"):
        steps.append("Map ASSISTments columns to learner, concept/problem, correctness, and ordering fields for DKT sequences.")

    if not tutor_db.get("enough_data_for_runtime_kt_validation"):
        steps.append("Collect or seed more quiz_results interactions per learner before runtime KT validation.")

    usable_behaviour = [
        name
        for name, item in behaviour.get("feature_availability", {}).items()
        if item.get("usable")
    ]
    if len(usable_behaviour) < 3:
        steps.append("Capture more behaviour features in quiz_results, especially time, confidence, hints, option changes, and correctness.")

    if behaviour.get("proxy_label_readiness", {}).get("status") != "success":
        steps.append("Define reviewed behaviour labels or ensure enough features exist for transparent proxy-label auditing.")

    if not steps:
        steps.append("Proceed to KT/DKT and Behaviour model upgrade experiments using audit outputs as readiness evidence.")

    return steps


def _limitations() -> list[str]:
    return [
        "This script is audit-only and does not modify tutor.db.",
        "CSV inspection uses column names and simple counts; it does not validate semantic correctness of mapped fields.",
        "Runtime KT readiness thresholds are conservative smoke-test thresholds, not proof of production-scale training data.",
        "Behaviour proxy labels are simple transparent estimates for reporting only, not final model-training labels.",
        "If equivalent columns use unexpected names, they may need to be added to the candidate lists in this script.",
    ]


def _overall_status(parts: list[dict[str, Any]]) -> str:
    statuses = [part.get("status") for part in parts]
    if "error" in statuses:
        return "error"
    if "warning" in statuses:
        return "warning"
    return "success"


def _build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# KT + Behaviour Dataset Readiness Audit",
        "",
        f"Generated at: {report['generated_at']}",
        "",
        f"Overall status: `{report['overall_status']}`",
        "",
        "## KT External Dataset",
        "",
    ]

    kt = report["kt_dataset_status"]
    lines.extend(
        [
            f"- Path: `{kt['path']}`",
            f"- Exists: {kt['exists']}",
            f"- Status: `{kt['status']}`",
            f"- Row count: {kt.get('row_count')}",
            f"- Columns: {', '.join(kt.get('columns', [])) or 'None'}",
            f"- Can support DKT sequences: {kt.get('can_support_dkt_sequences')}",
            f"- Missing required/usable columns: {', '.join(kt.get('missing_required_or_usable_columns', [])) or 'None'}",
            "",
            "## Tutor DB quiz_results",
            "",
        ]
    )

    db = report["tutor_db_status"]
    lines.extend(
        [
            f"- Path: `{db['path']}`",
            f"- DB exists: {db['exists']}",
            f"- quiz_results exists: {db.get('quiz_results_exists')}",
            f"- Status: `{db['status']}`",
            f"- Row count: {db.get('row_count')}",
            f"- Learner count: {db.get('learner_count')}",
            f"- Concept count: {db.get('concept_count')}",
            f"- Interaction count: {db.get('interaction_count')}",
            f"- Sequence length per learner: {db.get('sequence_length_per_learner')}",
            f"- Sequence length per learner-concept: {db.get('sequence_length_per_learner_concept')}",
            f"- Enough data for runtime KT validation: {db.get('enough_data_for_runtime_kt_validation')}",
            f"- Schema columns: {', '.join(db.get('columns', [])) or 'None'}",
            "",
            "## Behaviour Dataset Features",
            "",
            "| Feature | Exists | Non-null Count | Non-null Ratio | Usable |",
            "|---|---|---:|---:|---|",
        ]
    )

    behaviour = report["behaviour_dataset_status"]
    for feature, info in behaviour.get("feature_availability", {}).items():
        lines.append(
            f"| {feature} | {info.get('exists')} | {info.get('non_null_count')} | "
            f"{info.get('non_null_ratio')} | {info.get('usable')} |"
        )

    proxy = behaviour.get("proxy_label_readiness", {})
    lines.extend(
        [
            "",
            "## Behaviour Proxy-Label Readiness",
            "",
            f"- Status: `{proxy.get('status')}`",
            f"- Existing label columns: {', '.join(proxy.get('existing_label_columns', [])) or 'None'}",
            f"- Proxy labels generated: {proxy.get('proxy_labels_generated')}",
            f"- Proxy label distribution: {proxy.get('proxy_label_distribution')}",
            f"- Note: {proxy.get('rules_note')}",
            "",
            "## Recommended Next Steps",
            "",
        ]
    )

    for step in report["recommended_next_steps"]:
        lines.append(f"- {step}")

    lines.extend(["", "## Limitations", ""])
    for limitation in report["limitations"]:
        lines.append(f"- {limitation}")

    lines.extend(
        [
            "",
            "## Status",
            "",
            "```text",
            f"STATUS: {report['overall_status']}",
            "MODULE: kt_behaviour_dataset_readiness",
            "```",
            "",
        ]
    )

    return "\n".join(lines)


def build_report() -> dict[str, Any]:
    kt_dataset_report = _audit_assistments_csv()
    tutor_db_report, behaviour_report = _audit_tutor_db()

    report = {
        "overall_status": _overall_status([kt_dataset_report, tutor_db_report, behaviour_report]),
        "module": "kt_behaviour_dataset_readiness",
        "generated_at": _now_iso(),
        "kt_dataset_status": kt_dataset_report,
        "tutor_db_status": tutor_db_report,
        "behaviour_dataset_status": behaviour_report,
        "recommended_next_steps": [],
        "limitations": _limitations(),
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
    print("MODULE: kt_behaviour_dataset_readiness")
    print(f"JSON_REPORT: {OUTPUT_JSON}")
    print(f"MD_REPORT: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
