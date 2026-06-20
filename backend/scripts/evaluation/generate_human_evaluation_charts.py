"""
Matplotlib charts for human evaluation sheet (uses sample when no real ratings).

Run: python -m scripts.evaluation.generate_human_evaluation_charts
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CSV_ITEMS = ROOT / "evaluation_outputs" / "csv" / "human_evaluation_items.csv"
CSV_SAMPLE = ROOT / "evaluation_outputs" / "csv" / "human_evaluation_sample_rated.csv"
REPORT = ROOT / "evaluation_outputs" / "json" / "human_evaluation_report.json"
CHART_DIR = ROOT / "evaluation_outputs" / "charts"
JSON_OUT = ROOT / "evaluation_outputs" / "json" / "human_evaluation_visualization_report.json"
MD_OUT = ROOT / "evaluation_outputs" / "reports" / "human_evaluation_visualization_report.md"

DIMS = [
    "correctness_rating",
    "clarity_rating",
    "helpfulness_rating",
    "grounding_rating",
    "learner_suitability_rating",
    "actionability_rating",
]


def _bar(labels: List[str], values: List[float], title: str, ylabel: str, path: Path) -> None:
    plt.figure(figsize=(10, 5))
    plt.bar(labels, values)
    plt.title(title)
    plt.ylabel(ylabel)
    plt.xticks(rotation=28, ha="right")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()


def main() -> None:
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    MD_OUT.parent.mkdir(parents=True, exist_ok=True)

    charts: Dict[str, str] = {}
    notes: List[str] = []
    status = "success"

    rep: Dict[str, Any] = {}
    if REPORT.exists():
        try:
            rep = json.loads(REPORT.read_text(encoding="utf-8"))
        except Exception:
            rep = {}

    sample_only = bool(rep.get("sample_ratings_only", True))
    real = bool(rep.get("real_human_ratings_available", False))

    sample = pd.read_csv(CSV_SAMPLE, keep_default_na=False) if CSV_SAMPLE.exists() else pd.DataFrame()
    items = pd.read_csv(CSV_ITEMS, keep_default_na=False) if CSV_ITEMS.exists() else pd.DataFrame()

    df_plot = sample if sample_only and not sample.empty else items
    if sample_only:
        notes.append("Charts use human_evaluation_sample_rated.csv (sample_ratings_only); not real evaluator data.")

    if df_plot.empty:
        status = "warning"
        notes.append("No rows to plot.")
    else:
        if "category" in df_plot.columns:
            c = Counter(df_plot["category"].astype(str))
            p = CHART_DIR / "human_eval_category_distribution.png"
            _bar(list(c.keys()), [float(v) for v in c.values()], "Evaluation items by category", "Count", p)
            charts["human_eval_category_distribution"] = str(p.relative_to(ROOT))

        if "overall_score" in df_plot.columns:
            v = pd.to_numeric(df_plot["overall_score"], errors="coerce").dropna()
            if len(v):
                vc = v.round(2).value_counts().sort_index()
                p = CHART_DIR / "human_eval_sample_score_distribution.png"
                _bar([str(k) for k in vc.index], [float(x) for x in vc.values], "Overall score distribution", "Rows", p)
                charts["human_eval_sample_score_distribution"] = str(p.relative_to(ROOT))

        dim_means = []
        dim_labels = []
        for d in DIMS:
            if d not in df_plot.columns:
                continue
            s = pd.to_numeric(df_plot[d], errors="coerce").dropna()
            if len(s):
                dim_labels.append(d.replace("_rating", ""))
                dim_means.append(float(s.mean()))
        if dim_means:
            p = CHART_DIR / "human_eval_dimension_scores.png"
            _bar(dim_labels, dim_means, "Mean dimension scores (1–5)", "Mean", p)
            charts["human_eval_dimension_scores"] = str(p.relative_to(ROOT))

        if "rater_confidence" in df_plot.columns:
            rc = pd.to_numeric(df_plot["rater_confidence"], errors="coerce").dropna()
            if len(rc):
                vc = rc.astype(int).value_counts().sort_index()
                p = CHART_DIR / "human_eval_rater_confidence.png"
                _bar([str(k) for k in vc.index], [float(x) for x in vc.values], "Rater confidence distribution", "Rows", p)
                charts["human_eval_rater_confidence"] = str(p.relative_to(ROOT))

    if not charts:
        status = "warning"

    payload = {
        "status": status,
        "module": "human_evaluation_visualization_report",
        "sample_ratings_only": sample_only,
        "real_human_ratings_available": real,
        "charts": charts,
        "notes": notes,
    }
    JSON_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md = [
        "# Human evaluation visualization",
        "",
        f"**Status:** {status}",
        f"**sample_ratings_only:** {sample_only}",
        f"**real_human_ratings_available:** {real}",
        "",
        "## Notes",
        "",
        "\n".join(f"- {n}" for n in notes) or "- (none)",
        "",
        "## Charts",
        "",
    ]
    for k, v in charts.items():
        md.append(f"- **{k}:** `{v}`")
    md.append("")
    MD_OUT.write_text("\n".join(md), encoding="utf-8")

    print(f"STATUS: {status}")
    print("MODULE: human_evaluation_visualization_report")
    print(f"CHART_DIR: {CHART_DIR.relative_to(ROOT)}")
    print(f"JSON_REPORT: {JSON_OUT.relative_to(ROOT)}")
    print(f"MD_REPORT: {MD_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
