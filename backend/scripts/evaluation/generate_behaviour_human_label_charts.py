"""
Matplotlib charts for behaviour human-label readiness / sample demo.

Run: python -m scripts.evaluation.generate_behaviour_human_label_charts
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CSV_MAIN = ROOT / "evaluation_outputs" / "csv" / "behaviour_annotation_dataset.csv"
CSV_SAMPLE = ROOT / "evaluation_outputs" / "csv" / "behaviour_annotation_sample_labelled.csv"
REPORT = ROOT / "evaluation_outputs" / "json" / "behaviour_human_label_report.json"
CHART_DIR = ROOT / "evaluation_outputs" / "charts"
JSON_OUT = ROOT / "evaluation_outputs" / "json" / "behaviour_human_label_visualization_report.json"
MD_OUT = ROOT / "evaluation_outputs" / "reports" / "behaviour_human_label_visualization_report.md"


def _bar(labels: List[str], values: List[float], title: str, ylabel: str, path: Path) -> None:
    plt.figure(figsize=(10, 5))
    plt.bar(labels, values)
    plt.title(title)
    plt.ylabel(ylabel)
    plt.xticks(rotation=30, ha="right")
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

    main = pd.read_csv(CSV_MAIN, keep_default_na=False) if CSV_MAIN.exists() else pd.DataFrame()
    sample = pd.read_csv(CSV_SAMPLE, keep_default_na=False) if CSV_SAMPLE.exists() else pd.DataFrame()

    real_human = False
    if REPORT.exists():
        try:
            rep = json.loads(REPORT.read_text(encoding="utf-8"))
            real_human = bool(rep.get("real_human_labels_available"))
        except Exception:
            rep = {}

    chart_source = "main_and_sample_mixed_as_documented_in_notes"
    df_main = main if not main.empty else pd.DataFrame()
    df_plot = df_main if not df_main.empty else sample
    if df_plot.empty:
        status = "warning"
        notes.append("No CSV rows available for charts.")
    else:
        if "proxy_behaviour_label" in df_plot.columns:
            c = Counter(df_plot["proxy_behaviour_label"].astype(str))
            p = CHART_DIR / "behaviour_annotation_label_distribution.png"
            _bar(list(c.keys()), [float(v) for v in c.values()], "Proxy behaviour label distribution", "Count", p)
            charts["behaviour_annotation_label_distribution"] = str(p.relative_to(ROOT))

        if not sample.empty and "proxy_behaviour_label" in sample.columns and "human_behaviour_label" in sample.columns:
            agree = (
                sample["proxy_behaviour_label"].astype(str).str.strip()
                == sample["human_behaviour_label"].astype(str).str.strip()
            ).mean()
            p = CHART_DIR / "behaviour_annotation_proxy_vs_human_sample.png"
            _bar(
                ["agree", "disagree"],
                [float(agree), float(1.0 - agree)],
                "Sample sheet: proxy vs placeholder human label match rate",
                "Fraction",
                p,
            )
            charts["behaviour_annotation_proxy_vs_human_sample"] = str(p.relative_to(ROOT))
            notes.append("proxy_vs_human chart uses sample_labelled CSV (placeholders), not adjudicated human data.")

        if "correctness_rate" in df_plot.columns:
            vals = pd.to_numeric(df_plot["correctness_rate"], errors="coerce").fillna(0).clip(0, 1)
            try:
                hist = pd.cut(vals, bins=8)
                counts = hist.astype(str).value_counts().sort_index()
            except Exception:
                counts = pd.Series(dtype=float)
            labs = list(counts.index)
            p = CHART_DIR / "behaviour_annotation_feature_distribution.png"
            _bar(labs, [float(x) for x in counts.values], "Correctness rate bins (annotation set)", "Rows", p)
            charts["behaviour_annotation_feature_distribution"] = str(p.relative_to(ROOT))

        if "proxy_label_confidence" in df_plot.columns:
            v = pd.to_numeric(df_plot["proxy_label_confidence"], errors="coerce").fillna(0).clip(0, 1)
            try:
                hist = pd.cut(v, bins=10)
                counts = hist.astype(str).value_counts().sort_index()
            except Exception:
                counts = pd.Series(dtype=float)
            labs = list(counts.index)
            p = CHART_DIR / "behaviour_annotation_confidence_distribution.png"
            _bar(labs, [float(x) for x in counts.values], "Proxy label confidence bins", "Rows", p)
            charts["behaviour_annotation_confidence_distribution"] = str(p.relative_to(ROOT))

    if not charts:
        status = "warning"

    payload = {
        "status": status,
        "module": "behaviour_human_label_visualization_report",
        "chart_source": chart_source,
        "charts": charts,
        "notes": notes,
        "real_human_labels_available": real_human,
    }
    JSON_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md = [
        "# Behaviour human label visualization",
        "",
        f"**Status:** {status}",
        f"**Chart source:** {chart_source}",
        f"**Real human labels (from report):** {real_human}",
        "",
        "**Notes:**",
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
    print("MODULE: behaviour_human_label_visualization_report")
    print(f"CHART_DIR: {CHART_DIR.relative_to(ROOT)}")
    print(f"JSON_REPORT: {JSON_OUT.relative_to(ROOT)}")
    print(f"MD_REPORT: {MD_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
