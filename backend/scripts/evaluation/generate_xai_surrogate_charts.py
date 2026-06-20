"""
Generate matplotlib charts for XAI surrogate model evaluation.

Run: python -m scripts.evaluation.generate_xai_surrogate_charts
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
REPORT_JSON = ROOT / "evaluation_outputs" / "json" / "xai_surrogate_model_report.json"
CHART_DIR = ROOT / "evaluation_outputs" / "charts"
JSON_OUT = ROOT / "evaluation_outputs" / "json" / "xai_surrogate_visualization_report.json"
MD_OUT = ROOT / "evaluation_outputs" / "reports" / "xai_surrogate_visualization_report.md"

TARGET_COLUMNS = [
    "selected_teaching_view",
    "next_action",
    "promotion_allowed",
    "difficulty_selected",
    "revision_needed",
]


def load_report() -> Dict[str, Any]:
    if not REPORT_JSON.exists():
        raise FileNotFoundError(f"Missing report: {REPORT_JSON}")
    return json.loads(REPORT_JSON.read_text(encoding="utf-8"))


def save_bar(labels: List[str], values: List[float], title: str, ylabel: str, path: Path) -> None:
    plt.figure(figsize=(10, 5))
    plt.bar(labels, values)
    plt.title(title)
    plt.ylabel(ylabel)
    plt.xticks(rotation=35, ha="right")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()


def main() -> None:
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    MD_OUT.parent.mkdir(parents=True, exist_ok=True)

    try:
        report = load_report()
    except FileNotFoundError as exc:
        print("STATUS: warning")
        print("MODULE: xai_surrogate_visualization_report")
        print(f"CHART_DIR: {CHART_DIR.relative_to(ROOT)}")
        print(f"JSON_REPORT: {JSON_OUT.relative_to(ROOT)}")
        print(f"MD_REPORT: {MD_OUT.relative_to(ROOT)}")
        payload = {
            "status": "warning",
            "module": "xai_surrogate_visualization_report",
            "error": str(exc),
            "charts": {},
        }
        JSON_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        MD_OUT.write_text(f"# XAI Surrogate Visualization\n\n**Status:** warning\n\n{exc}\n", encoding="utf-8")
        return

    charts: Dict[str, str] = {}
    status = "success"

    # 1. Model comparison: best macro_f1 per target
    best_metrics = report.get("best_metrics_per_target", {})
    labels_cmp: List[str] = []
    values_cmp: List[float] = []
    for target in report.get("targets_trained", []):
        m = best_metrics.get(target, {})
        score = max(float(m.get("macro_f1", 0.0)), float(m.get("accuracy", 0.0)))
        labels_cmp.append(target[:18])
        values_cmp.append(score)
    if labels_cmp:
        p = CHART_DIR / "xai_surrogate_model_comparison.png"
        save_bar(labels_cmp, values_cmp, "XAI surrogate best score (macro F1 or accuracy)", "Score", p)
        charts["xai_surrogate_model_comparison"] = str(p.relative_to(ROOT))

    # 2. Top aggregated feature importances
    feature_scores: defaultdict[str, float] = defaultdict(float)
    for attr in report.get("attribution_per_target", {}).values():
        for item in attr.get("feature_importances", []) or []:
            feature_scores[str(item.get("feature", ""))] += abs(float(item.get("importance", 0.0)))
    if feature_scores:
        top_items = sorted(feature_scores.items(), key=lambda x: x[1], reverse=True)[:14]
        p = CHART_DIR / "xai_surrogate_top_features.png"
        save_bar(
            [x[0] for x in top_items],
            [x[1] for x in top_items],
            "XAI surrogate aggregated feature importance",
            "Sum |importance|",
            p,
        )
        charts["xai_surrogate_top_features"] = str(p.relative_to(ROOT))

    # 3. Target label distribution (from training report slice)
    from tutor.xai.xai_surrogate_trainer import build_surrogate_dataset

    df, _ = build_surrogate_dataset(ROOT / "external" / "core_data" / "tutor.db")
    dist_labels: List[str] = []
    dist_values: List[float] = []
    for col in TARGET_COLUMNS:
        if col not in df.columns:
            continue
        vc = df[col].astype(str).value_counts().head(8)
        for lab, cnt in vc.items():
            dist_labels.append(f"{col[:10]}:{str(lab)[:12]}")
            dist_values.append(float(cnt))
    if dist_labels:
        p = CHART_DIR / "xai_surrogate_target_distribution.png"
        save_bar(dist_labels, dist_values, "Target label counts (top per target)", "Count", p)
        charts["xai_surrogate_target_distribution"] = str(p.relative_to(ROOT))

    # 4. Confusion summary: correct vs incorrect from trace vs rest
    correct: List[str] = []
    corr_vals: List[float] = []
    for target, matrix in report.get("confusion_matrices", {}).items():
        if not matrix:
            continue
        arr = matrix
        total = sum(sum(row) for row in arr)
        if total <= 0:
            continue
        tr = 0.0
        for i, row in enumerate(arr):
            if i < len(row):
                tr += float(row[i])
        correct.append(f"{target[:14]}\nok")
        corr_vals.append(tr)
        correct.append(f"{target[:14]}\nmiss")
        corr_vals.append(max(total - tr, 0.0))
    if correct:
        p = CHART_DIR / "xai_surrogate_confusion_summary.png"
        save_bar(correct, corr_vals, "Correct vs incorrect (diagonal vs off)", "Count", p)
        charts["xai_surrogate_confusion_summary"] = str(p.relative_to(ROOT))

    # 5. Attribution method coverage
    method_counts: Counter[str] = Counter()
    for attr in report.get("attribution_per_target", {}).values():
        m = str(attr.get("method_used", "unavailable"))
        if m in ("none", "unknown", ""):
            m = "unavailable"
        method_counts[m] += 1
    if not method_counts:
        method_counts["unavailable"] = 1
    p = CHART_DIR / "xai_surrogate_attribution_method_coverage.png"
    save_bar(
        list(method_counts.keys()),
        [float(v) for v in method_counts.values()],
        "Attribution method coverage",
        "Targets",
        p,
    )
    charts["xai_surrogate_attribution_method_coverage"] = str(p.relative_to(ROOT))

    if not charts:
        status = "warning"

    viz = {
        "status": status,
        "module": "xai_surrogate_visualization_report",
        "charts": charts,
        "limitations": [
            "Charts summarize the latest surrogate training report; regenerate after retraining.",
        ],
    }
    JSON_OUT.write_text(json.dumps(viz, indent=2), encoding="utf-8")

    md_lines = [
        "# XAI Surrogate Visualization Report",
        "",
        f"**Status:** {status}",
        "",
        "## Charts",
        "",
    ]
    for k, v in charts.items():
        md_lines.append(f"- **{k}:** `{v}`")
    md_lines.extend(["", "## Notes", "", "\n".join(f"- {x}" for x in viz["limitations"]), ""])
    MD_OUT.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"STATUS: {status}")
    print("MODULE: xai_surrogate_visualization_report")
    print(f"CHART_DIR: {CHART_DIR.relative_to(ROOT)}")
    print(f"JSON_REPORT: {JSON_OUT.relative_to(ROOT)}")
    print(f"MD_REPORT: {MD_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
