import json
import re
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


DB_PATH = Path("external/core_data/tutor.db")
OUTPUT_JSON = Path("evaluation_outputs/json/kt_behaviour_model_quality_report.json")
OUTPUT_MD = Path("evaluation_outputs/reports/kt_behaviour_model_quality_report.md")


SEARCH_ROOTS = [
    Path("tutor/knowledge_state"),
    Path("tutor/behaviour"),
    Path("tutor/behavior"),
]


MODEL_KEYWORDS = [
    "lstm",
    "gru",
    "rnn",
    "dkt",
    "torch",
    "nn.module",
    "tensorflow",
    "keras",
    "sklearn",
    "joblib",
    "predict",
    "predict_proba",
    "load_state_dict",
    "state_dict",
    "model_path",
    "checkpoint",
]

RULE_KEYWORDS = [
    "if ",
    "elif ",
    "threshold",
    "heuristic",
    "rule",
    "weighted",
    "score >",
    "score <",
    "mastery >",
    "mastery <",
    "wrong_rate >",
    "wrong_rate <",
]

KT_TABLES = [
    "knowledge_state",
    "quiz_results",
]

BEHAVIOUR_TABLES = [
    "behaviour_state",
    "quiz_results",
]


def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _collect_python_files() -> list[Path]:
    files = []

    for root in SEARCH_ROOTS:
        if not root.exists():
            continue

        if root.is_file() and root.suffix == ".py":
            files.append(root)

        if root.is_dir():
            files.extend(root.rglob("*.py"))

    unique = []
    seen = set()

    for file in files:
        normalized = str(file).replace("\\", "/")
        if normalized not in seen:
            unique.append(file)
            seen.add(normalized)

    return unique


def _count_keywords(text: str, keywords: list[str]) -> dict:
    lower = text.lower()
    return {
        keyword: lower.count(keyword.lower())
        for keyword in keywords
        if lower.count(keyword.lower()) > 0
    }


def _inspect_file(path: Path) -> dict:
    text = _safe_read(path)
    lower = text.lower()

    model_hits = _count_keywords(text, MODEL_KEYWORDS)
    rule_hits = _count_keywords(text, RULE_KEYWORDS)

    class_names = re.findall(r"class\s+([A-Za-z_][A-Za-z0-9_]*)", text)
    function_names = re.findall(r"def\s+([A-Za-z_][A-Za-z0-9_]*)", text)

    likely_role = "unknown"

    if "knowledge" in lower or "dkt" in lower or "mastery" in lower:
        likely_role = "knowledge_tracing"

    if "behaviour" in lower or "behavior" in lower or "wrong_rate" in lower:
        if likely_role == "knowledge_tracing":
            likely_role = "mixed_kt_behaviour"
        else:
            likely_role = "behaviour_modeling"

    if model_hits and rule_hits:
        implementation_style = "mixed_model_and_rules"
    elif model_hits:
        implementation_style = "model_indicators_found"
    elif rule_hits:
        implementation_style = "rule_or_heuristic_indicators_found"
    else:
        implementation_style = "unclear_or_lightweight"

    return {
        "path": str(path),
        "line_count": len(text.splitlines()),
        "likely_role": likely_role,
        "implementation_style": implementation_style,
        "model_keyword_hits": model_hits,
        "rule_keyword_hits": rule_hits,
        "class_names": class_names,
        "function_names": function_names,
    }


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
    return [row[1] for row in cursor.fetchall()]


def _latest_rows(cursor: sqlite3.Cursor, table_name: str, limit: int = 5) -> list[dict]:
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

    return [dict(zip(columns, row)) for row in rows]


def _db_table_report(table_names: list[str]) -> dict:
    if not DB_PATH.exists():
        return {
            "status": "error",
            "reason": f"DB not found: {DB_PATH}",
            "tables": {},
        }

    tables = {}

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        for table_name in table_names:
            exists = _table_exists(cursor, table_name)
            columns = _table_columns(cursor, table_name) if exists else []

            row_count = None
            if exists:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = int(cursor.fetchone()[0])

            tables[table_name] = {
                "exists": exists,
                "columns": columns,
                "row_count": row_count,
                "latest_rows": _latest_rows(cursor, table_name, limit=5) if exists else [],
            }

    return {
        "status": "success",
        "db_path": str(DB_PATH),
        "tables": tables,
    }


def _infer_quality(file_reports: list[dict], db_report: dict) -> dict:
    kt_files = [
        item for item in file_reports
        if item["likely_role"] in {"knowledge_tracing", "mixed_kt_behaviour"}
    ]

    behaviour_files = [
        item for item in file_reports
        if item["likely_role"] in {"behaviour_modeling", "mixed_kt_behaviour"}
    ]

    kt_model_indicators = sum(
        len(item["model_keyword_hits"])
        for item in kt_files
    )

    kt_rule_indicators = sum(
        len(item["rule_keyword_hits"])
        for item in kt_files
    )

    behaviour_model_indicators = sum(
        len(item["model_keyword_hits"])
        for item in behaviour_files
    )

    behaviour_rule_indicators = sum(
        len(item["rule_keyword_hits"])
        for item in behaviour_files
    )

    kt_quality = "unclear_needs_manual_inspection"
    behaviour_quality = "unclear_needs_manual_inspection"

    if kt_model_indicators > 0 and kt_rule_indicators > 0:
        kt_quality = "mixed_model_and_rule_based"
    elif kt_model_indicators > 0:
        kt_quality = "model_indicators_found_but_needs_runtime_validation"
    elif kt_rule_indicators > 0:
        kt_quality = "likely_rule_or_heuristic_based"

    if behaviour_model_indicators > 0 and behaviour_rule_indicators > 0:
        behaviour_quality = "mixed_model_and_rule_based"
    elif behaviour_model_indicators > 0:
        behaviour_quality = "model_indicators_found_but_needs_runtime_validation"
    elif behaviour_rule_indicators > 0:
        behaviour_quality = "likely_rule_or_heuristic_based"

    kt_next = [
        "Run KT module for strong/average/weak learner profiles.",
        "Check whether mastery uses trained sequence model output or simple score rules.",
        "Verify feature sequence construction from quiz_results.",
        "Verify knowledge_state table updates after KT run.",
        "Prepare KT comparison report before replacing any existing logic.",
    ]

    behaviour_next = [
        "Run behaviour module for strong/average/weak/low_confidence learners.",
        "Check whether behaviour label comes from LSTM/model prediction or weighted heuristics.",
        "Verify behaviour features: wrong_rate, slow_rate, low_confidence_rate, hint_rate, option_change_rate.",
        "Verify behaviour_state table updates after behaviour run.",
        "Prepare behaviour comparison report before replacing any existing logic.",
    ]

    return {
        "knowledge_tracing": {
            "file_count": len(kt_files),
            "model_indicator_count": kt_model_indicators,
            "rule_indicator_count": kt_rule_indicators,
            "quality_label": kt_quality,
            "next_steps": kt_next,
        },
        "behaviour": {
            "file_count": len(behaviour_files),
            "model_indicator_count": behaviour_model_indicators,
            "rule_indicator_count": behaviour_rule_indicators,
            "quality_label": behaviour_quality,
            "next_steps": behaviour_next,
        },
    }


def _build_markdown(report: dict) -> str:
    lines = []

    lines.append("# KT + Behaviour Model Quality Audit")
    lines.append("")
    lines.append(f"Generated at: {report['generated_at']}")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This audit checks whether the current Knowledge Tracing and Behaviour "
        "modules show evidence of model-based implementation, rule-based implementation, "
        "or mixed logic."
    )
    lines.append("")
    lines.append("## File Inspection Summary")
    lines.append("")
    lines.append("| File | Role | Style | Lines | Model Hits | Rule Hits |")
    lines.append("|---|---|---|---:|---:|---:|")

    for item in report["file_reports"]:
        lines.append(
            f"| {item['path']} | "
            f"{item['likely_role']} | "
            f"{item['implementation_style']} | "
            f"{item['line_count']} | "
            f"{len(item['model_keyword_hits'])} | "
            f"{len(item['rule_keyword_hits'])} |"
        )

    lines.append("")
    lines.append("## Inference")
    lines.append("")
    kt = report["inference"]["knowledge_tracing"]
    behaviour = report["inference"]["behaviour"]

    lines.append(f"- Knowledge Tracing quality label: `{kt['quality_label']}`")
    lines.append(f"- KT model indicator count: {kt['model_indicator_count']}")
    lines.append(f"- KT rule indicator count: {kt['rule_indicator_count']}")
    lines.append("")
    lines.append(f"- Behaviour quality label: `{behaviour['quality_label']}`")
    lines.append(f"- Behaviour model indicator count: {behaviour['model_indicator_count']}")
    lines.append(f"- Behaviour rule indicator count: {behaviour['rule_indicator_count']}")
    lines.append("")
    lines.append("## DB Table Summary")
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
    lines.append("## KT Next Steps")
    lines.append("")
    for item in kt["next_steps"]:
        lines.append(f"- {item}")

    lines.append("")
    lines.append("## Behaviour Next Steps")
    lines.append("")
    for item in behaviour["next_steps"]:
        lines.append(f"- {item}")

    lines.append("")
    lines.append("## Status")
    lines.append("")
    lines.append("```text")
    lines.append("KT + Behaviour model-quality audit completed.")
    lines.append("```")

    return "\n".join(lines)


def main() -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)

    python_files = _collect_python_files()
    file_reports = [_inspect_file(path) for path in python_files]

    db_report = _db_table_report(
        sorted(set(KT_TABLES + BEHAVIOUR_TABLES))
    )

    report = {
        "status": "success",
        "module": "KTBehaviourModelQualityAudit",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "file_count": len(file_reports),
        "file_reports": file_reports,
        "database": db_report,
    }

    report["inference"] = _infer_quality(
        file_reports=file_reports,
        db_report=db_report,
    )

    OUTPUT_JSON.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    OUTPUT_MD.write_text(
        _build_markdown(report),
        encoding="utf-8",
    )

    print("\nKT + BEHAVIOUR MODEL QUALITY AUDIT")
    print("status:", report["status"])
    print("module:", report["module"])
    print("file_count:", report["file_count"])

    print("\nFILE SUMMARY")
    for item in file_reports:
        print(
            item["path"],
            "| role:",
            item["likely_role"],
            "| style:",
            item["implementation_style"],
            "| model_hits:",
            len(item["model_keyword_hits"]),
            "| rule_hits:",
            len(item["rule_keyword_hits"]),
        )

    print("\nINFERENCE")
    print(
        "KT quality:",
        report["inference"]["knowledge_tracing"]["quality_label"],
    )
    print(
        "Behaviour quality:",
        report["inference"]["behaviour"]["quality_label"],
    )

    print("\nSaved JSON:", OUTPUT_JSON)
    print("Saved Markdown:", OUTPUT_MD)

    print("\nSTATUS: success")
    print("MODULE: kt_behaviour_model_quality_audit")


if __name__ == "__main__":
    main()