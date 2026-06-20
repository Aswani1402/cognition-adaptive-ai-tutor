import json
import sqlite3
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List


DB_PATH = Path("external/core_data/tutor.db")
TABLE_NAME = "teaching_strategy_model_comparison_log"

OUTPUT_JSON_DIR = Path("evaluation_outputs/json")
OUTPUT_REPORT_DIR = Path("evaluation_outputs/reports")

OUTPUT_JSON_PATH = OUTPUT_JSON_DIR / "teaching_strategy_agreement_report.json"
OUTPUT_MD_PATH = OUTPUT_REPORT_DIR / "teaching_strategy_agreement_report.md"


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def table_exists(cur: sqlite3.Cursor) -> bool:
    cur.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name=?
        """,
        (TABLE_NAME,),
    )
    return cur.fetchone() is not None


def load_rows() -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if not table_exists(cur):
        conn.close()
        return []

    cur.execute(
        f"""
        SELECT
            id,
            learner_id,
            concept_id,
            concept_name,
            evidence_teaching_view,
            model_teaching_view,
            teaching_view_agreement,
            evidence_progression_action,
            model_progression_action,
            progression_agreement,
            model_teaching_view_confidence,
            model_progression_confidence,
            created_at
        FROM {TABLE_NAME}
        ORDER BY id ASC
        """
    )

    rows = [dict(row) for row in cur.fetchall()]
    conn.close()

    return rows


def compute_rate(rows: List[Dict[str, Any]], column: str) -> float:
    valid = [row for row in rows if row.get(column) is not None]

    if not valid:
        return 0.0

    positive = sum(1 for row in valid if int(row.get(column)) == 1)
    return round(positive / len(valid), 4)


def compute_average(rows: List[Dict[str, Any]], column: str) -> float:
    values = [
        safe_float(row.get(column))
        for row in rows
        if row.get(column) is not None
    ]

    if not values:
        return 0.0

    return round(sum(values) / len(values), 4)


def count_by(rows: List[Dict[str, Any]], column: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}

    for row in rows:
        key = str(row.get(column, "unknown"))
        counts[key] = counts.get(key, 0) + 1

    return dict(sorted(counts.items(), key=lambda item: item[1], reverse=True))


def find_disagreements(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    output = []

    for row in rows:
        teaching_disagree = (
            row.get("teaching_view_agreement") is not None
            and int(row.get("teaching_view_agreement")) == 0
        )

        progression_disagree = (
            row.get("progression_agreement") is not None
            and int(row.get("progression_agreement")) == 0
        )

        if teaching_disagree or progression_disagree:
            output.append(row)

    return output


def build_report(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(rows)

    latest_samples = list(reversed(rows[-10:]))

    disagreements = find_disagreements(rows)

    report = {
        "status": "success",
        "module": "TeachingStrategyAgreementReport",
        "generated_at": now_iso(),
        "total_comparisons": total,
        "teaching_view_agreement_rate": compute_rate(rows, "teaching_view_agreement"),
        "progression_agreement_rate": compute_rate(rows, "progression_agreement"),
        "average_model_teaching_view_confidence": compute_average(
            rows,
            "model_teaching_view_confidence",
        ),
        "average_model_progression_confidence": compute_average(
            rows,
            "model_progression_confidence",
        ),
        "evidence_teaching_view_distribution": count_by(rows, "evidence_teaching_view"),
        "model_teaching_view_distribution": count_by(rows, "model_teaching_view"),
        "evidence_progression_distribution": count_by(rows, "evidence_progression_action"),
        "model_progression_distribution": count_by(rows, "model_progression_action"),
        "disagreement_count": len(disagreements),
        "disagreement_samples": disagreements[:20],
        "latest_samples": latest_samples,
        "note": (
            "The model-based selector is currently evaluated in comparison-only mode. "
            "It should not replace the evidence-aware selector until agreement is stable "
            "across larger and more diverse logs."
        ),
    }

    return report


def markdown_table_from_counts(title: str, counts: Dict[str, int]) -> str:
    lines = []
    lines.append(f"### {title}")
    lines.append("")
    lines.append("| Label | Count |")
    lines.append("|---|---:|")

    if not counts:
        lines.append("| N/A | 0 |")
    else:
        for label, count in counts.items():
            lines.append(f"| `{label}` | {count} |")

    lines.append("")
    return "\n".join(lines)


def markdown_samples(title: str, rows: List[Dict[str, Any]]) -> str:
    lines = []
    lines.append(f"### {title}")
    lines.append("")

    if not rows:
        lines.append("No samples available.")
        lines.append("")
        return "\n".join(lines)

    for idx, row in enumerate(rows[:10], start=1):
        lines.append(f"#### Sample {idx}")
        lines.append("")
        lines.append(f"- **Learner:** `{row.get('learner_id')}`")
        lines.append(f"- **Concept:** `{row.get('concept_id')}` / `{row.get('concept_name')}`")
        lines.append(f"- **Evidence view:** `{row.get('evidence_teaching_view')}`")
        lines.append(f"- **Model view:** `{row.get('model_teaching_view')}`")
        lines.append(f"- **Teaching view agreement:** `{bool(row.get('teaching_view_agreement')) if row.get('teaching_view_agreement') is not None else None}`")
        lines.append(f"- **Evidence progression:** `{row.get('evidence_progression_action')}`")
        lines.append(f"- **Model progression:** `{row.get('model_progression_action')}`")
        lines.append(f"- **Progression agreement:** `{bool(row.get('progression_agreement')) if row.get('progression_agreement') is not None else None}`")
        lines.append(f"- **Model view confidence:** `{row.get('model_teaching_view_confidence')}`")
        lines.append(f"- **Created at:** `{row.get('created_at')}`")
        lines.append("")

    return "\n".join(lines)


def build_markdown(report: Dict[str, Any]) -> str:
    lines = []

    lines.append("# Teaching Strategy Agreement Report")
    lines.append("")
    lines.append(f"Generated at: `{report.get('generated_at')}`")
    lines.append("")
    lines.append("## 1. Purpose")
    lines.append("")
    lines.append(
        "This report compares the evidence-aware TeachingStrategySelector with the "
        "model-based TeachingStrategySelector. The model is currently running in "
        "comparison-only mode and does not override the evidence-aware selector."
    )
    lines.append("")

    lines.append("## 2. Summary")
    lines.append("")
    lines.append(f"- **Total comparisons:** {report.get('total_comparisons')}")
    lines.append(f"- **Teaching view agreement rate:** {report.get('teaching_view_agreement_rate')}")
    lines.append(f"- **Progression agreement rate:** {report.get('progression_agreement_rate')}")
    lines.append(f"- **Average model teaching-view confidence:** {report.get('average_model_teaching_view_confidence')}")
    lines.append(f"- **Average model progression confidence:** {report.get('average_model_progression_confidence')}")
    lines.append(f"- **Disagreement count:** {report.get('disagreement_count')}")
    lines.append("")

    lines.append("## 3. Teaching View Distribution")
    lines.append("")
    lines.append(markdown_table_from_counts(
        "Evidence-aware teaching view distribution",
        report.get("evidence_teaching_view_distribution", {}),
    ))
    lines.append(markdown_table_from_counts(
        "Model teaching view distribution",
        report.get("model_teaching_view_distribution", {}),
    ))

    lines.append("## 4. Progression Action Distribution")
    lines.append("")
    lines.append(markdown_table_from_counts(
        "Evidence-aware progression distribution",
        report.get("evidence_progression_distribution", {}),
    ))
    lines.append(markdown_table_from_counts(
        "Model progression distribution",
        report.get("model_progression_distribution", {}),
    ))

    lines.append("## 5. Disagreement Samples")
    lines.append("")
    lines.append(markdown_samples(
        "Disagreement cases",
        report.get("disagreement_samples", []),
    ))

    lines.append("## 6. Latest Samples")
    lines.append("")
    lines.append(markdown_samples(
        "Latest comparison cases",
        report.get("latest_samples", []),
    ))

    lines.append("## 7. Interpretation")
    lines.append("")
    lines.append(
        "If agreement remains high across many learners and concepts, the model-based selector "
        "can later be allowed to influence or override the evidence-aware baseline. If disagreement "
        "appears, disagreement cases should be inspected and used to improve the model or data generation."
    )
    lines.append("")

    lines.append("## 8. Next Steps")
    lines.append("")
    lines.append(
        "1. Run the integrated pipeline for multiple learners and concepts.\n"
        "2. Regenerate this agreement report.\n"
        "3. Inspect disagreement cases.\n"
        "4. Add noisy synthetic logs and retrain models.\n"
        "5. Move toward contextual bandit view selection after stable comparison."
    )
    lines.append("")

    return "\n".join(lines)


def save_report(report: Dict[str, Any]) -> None:
    OUTPUT_JSON_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_REPORT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    markdown = build_markdown(report)

    with open(OUTPUT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(markdown)


def main():
    rows = load_rows()
    report = build_report(rows)
    save_report(report)

    print("\nTeaching strategy agreement report generated.")
    print("Total comparisons:", report["total_comparisons"])
    print("Teaching view agreement rate:", report["teaching_view_agreement_rate"])
    print("Progression agreement rate:", report["progression_agreement_rate"])
    print("Average model teaching-view confidence:", report["average_model_teaching_view_confidence"])
    print("Disagreement count:", report["disagreement_count"])
    print("JSON:", OUTPUT_JSON_PATH)
    print("Markdown:", OUTPUT_MD_PATH)


if __name__ == "__main__":
    main()