"""
Validate human evaluation CSVs and emit readiness / summary report.

Run: python -m scripts.evaluation.check_human_evaluation_report
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CSV_ITEMS = ROOT / "evaluation_outputs" / "csv" / "human_evaluation_items.csv"
CSV_SAMPLE = ROOT / "evaluation_outputs" / "csv" / "human_evaluation_sample_rated.csv"
JSON_OUT = ROOT / "evaluation_outputs" / "json" / "human_evaluation_report.json"
MD_OUT = ROOT / "evaluation_outputs" / "reports" / "human_evaluation_report.md"

REQUIRED = [
    "item_id",
    "category",
    "domain",
    "concept_id",
    "concept_name",
    "prompt_or_context",
    "system_output",
    "source_or_grounding",
    "expected_reference",
    "automatic_score_if_available",
    "correctness_rating",
    "clarity_rating",
    "helpfulness_rating",
    "grounding_rating",
    "learner_suitability_rating",
    "actionability_rating",
    "overall_score",
    "rater_confidence",
    "rater_id",
    "human_notes",
    "needs_revision",
]

CATEGORIES = {
    "teaching_explanation",
    "rag_grounded_answer",
    "doubt_answer",
    "semantic_evaluator_judgement",
    "adaptive_hint",
    "generated_flashcard",
    "generated_mindmap",
    "assessment_question",
    "feedback_response",
}

DIMENSION_RATINGS = [
    "correctness_rating",
    "clarity_rating",
    "helpfulness_rating",
    "grounding_rating",
    "learner_suitability_rating",
    "actionability_rating",
]

RATING_FIELDS = [*DIMENSION_RATINGS, "overall_score", "rater_confidence"]

FINAL_WORDING = (
    "A human-rated evaluation workflow was prepared to complement automatic metrics. The exported rating sheet "
    "allows evaluators to score teaching explanations, RAG-grounded answers, doubt responses, semantic evaluation "
    "judgements, adaptive hints, assessment questions, flashcards, and mindmap outputs using correctness, clarity, "
    "helpfulness, grounding, learner suitability, and actionability. Since large-scale human ratings are not yet "
    "collected, the current version reports the evaluation protocol, rubric, and sample-rated examples, while full "
    "human evaluation is retained as future validation work."
)


def _blank(s: Any) -> bool:
    if s is None:
        return True
    return str(s).strip() == ""


def _is_demo_rater_series(r: pd.Series) -> pd.Series:
    s = r.astype(str).str.strip().str.upper()
    return s.isin({"", "DEMO_RATER", "DEMO"})


def _real_ratings_mask(df: pd.DataFrame) -> pd.Series:
    if df.empty or "correctness_rating" not in df.columns:
        return pd.Series([], dtype=bool)
    filled = ~df["correctness_rating"].map(_blank)
    rid = df["rater_id"] if "rater_id" in df.columns else pd.Series([""] * len(df))
    notes = df["human_notes"] if "human_notes" in df.columns else pd.Series([""] * len(df))
    not_demo = ~_is_demo_rater_series(rid)
    not_sample_note = ~notes.astype(str).str.contains("SAMPLE_RATINGS_ONLY", case=False, na=False)
    return filled & not_demo & not_sample_note


def _validate(df: pd.DataFrame, name: str) -> List[str]:
    issues: List[str] = []
    miss = [c for c in REQUIRED if c not in df.columns]
    if miss:
        issues.append(f"{name}_missing_columns:{','.join(miss)}")
    if df.empty and name == "items":
        issues.append("items_empty")
    for col in RATING_FIELDS:
        if col not in df.columns:
            continue
        for i, v in enumerate(df[col].tolist()):
            if _blank(v):
                continue
            try:
                x = float(str(v).strip())
                if x < 1 or x > 5:
                    issues.append(f"{name}_row{i}_{col}_out_of_range")
            except Exception:
                issues.append(f"{name}_row{i}_{col}_non_numeric")
            if col in DIMENSION_RATINGS or col == "rater_confidence":
                try:
                    if float(str(v).strip()) != int(float(str(v).strip())):
                        issues.append(f"{name}_row{i}_{col}_should_be_integer_1_to_5")
                except Exception:
                    pass
    if "category" in df.columns:
        for i, v in enumerate(df["category"].tolist()):
            if str(v).strip() not in CATEGORIES:
                issues.append(f"{name}_row{i}_bad_category:{v}")
    if "needs_revision" in df.columns:
        for i, v in enumerate(df["needs_revision"].tolist()):
            if _blank(v):
                continue
            if str(v).strip().lower() not in {"yes", "no"}:
                issues.append(f"{name}_row{i}_bad_needs_revision:{v}")
    return issues


def _numeric_series(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(df[col], errors="coerce")


def _aggregate_ratings(df: pd.DataFrame) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for c in RATING_FIELDS:
        s = _numeric_series(df, c)
        if s.notna().any():
            out[f"average_{c}"] = round(float(s.mean()), 4)
    if "category" in df.columns:
        cat_avg: Dict[str, Any] = {}
        for cat, grp in df.groupby(df["category"].astype(str)):
            dims = {f"average_{c}": round(float(_numeric_series(grp, c).mean()), 4) for c in RATING_FIELDS[:6]}
            cat_avg[str(cat)] = dims
        out["category_averages"] = cat_avg
    if "needs_revision" in df.columns:
        out["needs_revision_count"] = int(df["needs_revision"].astype(str).str.lower().eq("yes").sum())
    return out


def build_report() -> Dict[str, Any]:
    items = pd.read_csv(CSV_ITEMS, keep_default_na=False) if CSV_ITEMS.exists() else pd.DataFrame()
    sample = pd.read_csv(CSV_SAMPLE, keep_default_na=False) if CSV_SAMPLE.exists() else pd.DataFrame()

    issues: List[str] = []
    issues.extend(_validate(items, "items"))
    issues.extend(_validate(sample, "sample"))

    mask = _real_ratings_mask(items)
    real_human = bool(mask.sum() >= 3)
    sample_only = not real_human

    metrics_source = "human_evaluation_items.csv"
    df_metrics = items.loc[mask].copy() if real_human else pd.DataFrame()
    if sample_only and not sample.empty:
        metrics_source = "human_evaluation_sample_rated.csv (demo placeholders only)"
        # use rows where numeric ratings exist in sample
        sm = sample.copy()
        if "correctness_rating" in sm.columns and not sm["correctness_rating"].map(_blank).all():
            df_metrics = sm

    agg = _aggregate_ratings(df_metrics) if not df_metrics.empty else {}

    if real_human:
        rated_count = int(mask.sum())
        unrated_count = int((~mask).sum())
    else:
        rated_count = int(len(df_metrics)) if not df_metrics.empty else 0
        unrated_count = int(len(items))

    report: Dict[str, Any] = {
        "status": "warning" if issues or items.empty else "success",
        "module": "human_evaluation_report",
        "real_human_ratings_available": real_human,
        "sample_ratings_only": sample_only,
        "metrics_source": metrics_source,
        "item_row_count": int(len(items)),
        "sample_row_count": int(len(sample)),
        "rated_count": rated_count,
        "unrated_count": unrated_count,
        "validation_issues": issues,
        "averages": {k: v for k, v in agg.items() if k != "category_averages"},
        "category_averages": agg.get("category_averages", {}),
        "needs_revision_count": agg.get("needs_revision_count", 0),
        "limitations": [],
        "final_report_wording": FINAL_WORDING,
    }

    if sample_only:
        report["limitations"].append(
            "real_human_ratings_available=false; sample_ratings_only=true: metrics below (if any) use "
            "human_evaluation_sample_rated.csv for demonstration only. Full human evaluation is pending."
        )
    if issues:
        report["limitations"].append("validation: " + "; ".join(issues[:20]))
    if items.empty:
        report["limitations"].append("human_evaluation_items.csv missing or empty — run export script.")

    if not issues and not items.empty:
        report["status"] = "success"

    return report


def build_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Human evaluation report",
        "",
        f"**Status:** {report.get('status')}",
        f"**Real human ratings available:** {report.get('real_human_ratings_available')}",
        f"**Sample ratings only (demo):** {report.get('sample_ratings_only')}",
        f"**Metrics source:** {report.get('metrics_source')}",
        "",
        f"**Item rows:** {report.get('item_row_count')}",
        f"**Sample rows:** {report.get('sample_row_count')}",
        f"**Rated count (per metric rules):** {report.get('rated_count')}",
        f"**Unrated count:** {report.get('unrated_count')}",
        "",
        "## Validation issues",
        "",
        str(report.get("validation_issues", [])),
        "",
        "## Averages (when ratings present)",
        "",
        str(report.get("averages", {})),
        "",
        "## Category averages",
        "",
        str(report.get("category_averages", {})),
        "",
        f"**needs_revision_count:** {report.get('needs_revision_count')}",
        "",
        "## Limitations",
        "",
    ]
    for lim in report.get("limitations", []):
        lines.append(f"- {lim}")
    lines.extend(["", "## Final report wording", "", report.get("final_report_wording", ""), ""])
    return "\n".join(lines)


def main() -> None:
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    MD_OUT.parent.mkdir(parents=True, exist_ok=True)
    report = build_report()
    JSON_OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    MD_OUT.write_text(build_markdown(report), encoding="utf-8")
    print(f"STATUS: {report.get('status', 'warning')}")
    print("MODULE: human_evaluation_report")
    print(f"JSON_REPORT: {JSON_OUT.relative_to(ROOT)}")
    print(f"MD_REPORT: {MD_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
