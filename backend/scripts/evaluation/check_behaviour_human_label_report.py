"""
Validate behaviour annotation CSVs and emit human-label readiness report.

Run: python -m scripts.evaluation.check_behaviour_human_label_report
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, cohen_kappa_score, f1_score

ROOT = Path(__file__).resolve().parents[2]
CSV_MAIN = ROOT / "evaluation_outputs" / "csv" / "behaviour_annotation_dataset.csv"
CSV_SAMPLE = ROOT / "evaluation_outputs" / "csv" / "behaviour_annotation_sample_labelled.csv"
JSON_OUT = ROOT / "evaluation_outputs" / "json" / "behaviour_human_label_report.json"
MD_OUT = ROOT / "evaluation_outputs" / "reports" / "behaviour_human_label_report.md"

REQUIRED_COLUMNS = [
    "annotation_id",
    "learner_id",
    "concept_id",
    "concept_name",
    "domain",
    "timestamp",
    "recent_score",
    "correctness_rate",
    "wrong_rate",
    "slow_rate",
    "low_confidence_rate",
    "hint_rate",
    "option_change_rate",
    "time_taken_avg",
    "confidence_avg",
    "wrong_streak",
    "attempt_count",
    "behaviour_risk",
    "behaviour_confidence",
    "anomaly_score",
    "dominant_mistake_type",
    "mistake_count",
    "wrong_output_count",
    "syntax_mistake_count",
    "debug_error_count",
    "output_prediction_error_count",
    "proxy_behaviour_label",
    "proxy_label_source",
    "proxy_label_confidence",
    "human_behaviour_label",
    "human_confidence",
    "annotator_id",
    "annotation_notes",
    "needs_review",
]

ALLOWED_HUMAN = {
    "stable",
    "confused",
    "struggling",
    "guessing",
    "careless",
    "low_confidence",
    "disengaged",
    "anomalous",
    "unclear",
}

ALLOWED_NEEDS = {"", "yes", "no"}

FINAL_WORDING = (
    "The behaviour module currently uses model-supported behaviour prediction and comparison using LSTM, "
    "supervised baselines, clustering, and anomaly detection. Since production-scale human-labelled behavioural "
    "data is not yet available, an annotation-ready behaviour dataset and human labelling guide were created. "
    "The exported dataset includes learner evidence such as correctness rate, confidence, hint usage, wrong "
    "streak, behaviour risk, mistake patterns, and anomaly score. This enables future human validation of proxy "
    "behaviour labels and supports more reliable supervised behaviour modelling."
)


def _is_blank(s: Any) -> bool:
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return True
    return str(s).strip() == ""


def _normalize_label(s: Any) -> str:
    return str(s or "").strip().lower().replace(" ", "_")


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _validate_frame(df: pd.DataFrame, name: str) -> List[str]:
    issues: List[str] = []
    if df.empty and name == "main":
        issues.append("main_dataset_empty")
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        issues.append(f"missing_columns:{name}:{','.join(missing)}")
    return issues


def _validate_labels(df: pd.DataFrame, allow_demo: bool) -> List[str]:
    issues: List[str] = []
    if "human_behaviour_label" not in df.columns:
        return issues
    for i, v in enumerate(df["human_behaviour_label"].tolist()):
        if _is_blank(v):
            continue
        lab = _normalize_label(v)
        if lab not in ALLOWED_HUMAN:
            issues.append(f"invalid_human_label_row_{i}:{v}")
    if "human_confidence" in df.columns:
        for i, v in enumerate(df["human_confidence"].tolist()):
            if _is_blank(v):
                continue
            try:
                h = int(float(str(v).strip()))
                if h < 1 or h > 5:
                    issues.append(f"human_confidence_out_of_range_row_{i}:{v}")
            except Exception:
                issues.append(f"human_confidence_non_numeric_row_{i}:{v}")
    if "needs_review" in df.columns:
        for i, v in enumerate(df["needs_review"].tolist()):
            if _is_blank(v):
                continue
            if str(v).strip().lower() not in {"yes", "no"}:
                issues.append(f"needs_review_invalid_row_{i}:{v}")
    if allow_demo:
        notes = df.get("annotation_notes", pd.Series([""] * len(df)))
        if not notes.astype(str).str.contains("DEMO|demo|placeholder|sample", case=False, regex=True).any():
            issues.append("sample_file_missing_demo_watermark_in_notes")
    return issues


def _real_human_mask(df: pd.DataFrame) -> pd.Series:
    """Rows that look like genuine human labels (exclude export demo placeholders)."""
    if df.empty or "human_behaviour_label" not in df.columns:
        return pd.Series([False] * len(df), dtype=bool)
    lab_filled = ~df["human_behaviour_label"].map(_is_blank)
    ann = df["annotator_id"].astype(str).str.strip() if "annotator_id" in df.columns else pd.Series([""] * len(df))
    notes = df["annotation_notes"].astype(str).str.lower() if "annotation_notes" in df.columns else pd.Series([""] * len(df))
    not_demo = ~(
        ann.str.upper().eq("DEMO_EXPORT")
        | notes.str.contains("demo", na=False)
        | notes.str.contains("placeholder", na=False)
        | notes.str.contains("sample", na=False)
    )
    return lab_filled & not_demo


def _compute_metrics(main: pd.DataFrame, mask: pd.Series) -> Dict[str, Any]:
    n = len(main)
    labelled = int(mask.sum())
    out: Dict[str, Any] = {
        "labelled_count": labelled,
        "unlabelled_count": max(0, n - labelled),
        "label_distribution": {},
        "proxy_vs_human_agreement": None,
        "cohen_kappa": None,
        "macro_f1_proxy_vs_human": None,
    }
    if labelled < 3:
        return out
    sub = main.loc[mask].copy()
    y_proxy = sub["proxy_behaviour_label"].map(_normalize_label)
    y_human = sub["human_behaviour_label"].map(_normalize_label)
    valid = y_human.isin(ALLOWED_HUMAN) & y_proxy.notna()
    if valid.sum() < 3:
        return out
    y_p = y_proxy[valid]
    y_h = y_human[valid]
    labels = sorted(set(y_p.tolist()) | set(y_h.tolist()))
    out["label_distribution"] = {str(k): int(v) for k, v in y_h.value_counts().items()}
    out["proxy_vs_human_agreement"] = float(accuracy_score(y_h, y_p))
    try:
        out["cohen_kappa"] = float(cohen_kappa_score(y_h, y_p))
    except Exception:
        out["cohen_kappa"] = None
    try:
        out["macro_f1_proxy_vs_human"] = float(
            f1_score(y_h, y_p, average="macro", labels=labels, zero_division=0)
        )
    except Exception:
        out["macro_f1_proxy_vs_human"] = None
    return out


def build_report() -> Dict[str, Any]:
    main = _read_csv(CSV_MAIN)
    sample = _read_csv(CSV_SAMPLE)
    issues: List[str] = []
    issues.extend(_validate_frame(main, "main"))
    issues.extend(_validate_frame(sample, "sample"))
    if not sample.empty:
        issues.extend(_validate_labels(sample, allow_demo=True))
    if not main.empty:
        issues.extend(_validate_labels(main, allow_demo=False))

    real_mask = _real_human_mask(main)
    real_human_labels_available = bool(real_mask.sum() >= 5)

    if real_human_labels_available:
        metrics = _compute_metrics(main, real_mask)
    else:
        metrics = {
            "labelled_count": 0,
            "unlabelled_count": int(len(main)),
            "label_distribution": {},
            "proxy_vs_human_agreement": None,
            "cohen_kappa": None,
            "macro_f1_proxy_vs_human": None,
        }

    status = "success"
    if not CSV_MAIN.exists():
        status = "warning"
        issues.append("main_csv_missing")
    elif issues:
        status = "warning"

    report: Dict[str, Any] = {
        "status": status,
        "module": "behaviour_human_label_report",
        "real_human_labels_available": real_human_labels_available,
        "main_row_count": int(len(main)),
        "sample_row_count": int(len(sample)),
        "validation_issues": issues,
        "labelled_count": metrics.get("labelled_count", 0),
        "unlabelled_count": metrics.get("unlabelled_count", int(len(main))),
        "label_distribution": metrics.get("label_distribution", {}),
        "proxy_vs_human_agreement": metrics.get("proxy_vs_human_agreement"),
        "cohen_kappa": metrics.get("cohen_kappa"),
        "macro_f1_proxy_vs_human": metrics.get("macro_f1_proxy_vs_human"),
        "second_rater_column_detected": "human_behaviour_label_2" in main.columns,
        "limitations": [],
        "final_report_wording": FINAL_WORDING,
    }

    if not real_human_labels_available:
        report["limitations"].append(
            "real_human_labels_available=false: fewer than five non-demo human labels in the main annotation CSV; "
            "agreement and kappa metrics are deferred. The human-labelling workflow and annotation dataset export are "
            "complete; full-scale human annotation is future work unless annotators complete the sheet."
        )
    if issues:
        report["limitations"].append("validation_issues: " + "; ".join(issues[:12]))

    if "human_behaviour_label_2" in main.columns:
        m2 = real_mask & ~main["human_behaviour_label_2"].map(_is_blank)
        if m2.sum() >= 5:
            try:
                a = main.loc[m2, "human_behaviour_label"].map(_normalize_label)
                b = main.loc[m2, "human_behaviour_label_2"].map(_normalize_label)
                report["cohen_kappa_two_annotators"] = float(cohen_kappa_score(a, b))
            except Exception:
                report["cohen_kappa_two_annotators"] = None

    return report


def build_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Behaviour human label report",
        "",
        f"**Status:** {report.get('status')}",
        f"**Real human labels available:** {report.get('real_human_labels_available')}",
        "",
        f"**Main CSV rows:** {report.get('main_row_count')}",
        f"**Sample CSV rows:** {report.get('sample_row_count')}",
        "",
        "## Validation",
        "",
        str(report.get("validation_issues", [])),
        "",
        "## Metrics (when enough non-demo human labels exist)",
        "",
        f"**Labelled count:** {report.get('labelled_count')}",
        f"**Unlabelled count:** {report.get('unlabelled_count')}",
        f"**Proxy vs human agreement (accuracy):** {report.get('proxy_vs_human_agreement')}",
        f"**Cohen kappa:** {report.get('cohen_kappa')}",
        f"**Macro F1 (proxy vs human):** {report.get('macro_f1_proxy_vs_human')}",
        f"**Second rater column present:** {report.get('second_rater_column_detected')}",
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
    status = report.get("status", "warning")
    print(f"STATUS: {status}")
    print("MODULE: behaviour_human_label_report")
    print(f"JSON_REPORT: {JSON_OUT.relative_to(ROOT)}")
    print(f"MD_REPORT: {MD_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
