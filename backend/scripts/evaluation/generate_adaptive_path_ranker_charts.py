"""
Matplotlib charts for adaptive path ranker report.

Run: python -m scripts.evaluation.generate_adaptive_path_ranker_charts
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "evaluation_outputs" / "json" / "adaptive_path_ranker_report.json"
CHART_DIR = ROOT / "evaluation_outputs" / "charts"
JSON_OUT = ROOT / "evaluation_outputs" / "json" / "adaptive_path_ranker_visualization_report.json"
MD_OUT = ROOT / "evaluation_outputs" / "reports" / "adaptive_path_ranker_visualization_report.md"


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

    if not REPORT.exists():
        payload = {
            "status": "warning",
            "module": "adaptive_path_ranker_visualization_report",
            "error": f"Missing {REPORT}",
            "charts": {},
        }
        JSON_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        MD_OUT.write_text("# Adaptive path ranker charts\n\nReport missing.\n", encoding="utf-8")
        print("STATUS: warning")
        print("MODULE: adaptive_path_ranker_visualization_report")
        print(f"CHART_DIR: {CHART_DIR.relative_to(ROOT)}")
        print(f"JSON_REPORT: {JSON_OUT.relative_to(ROOT)}")
        print(f"MD_REPORT: {MD_OUT.relative_to(ROOT)}")
        return

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    status = "success"

    best = report.get("best_metrics_per_target", {})
    if best:
        labs = [k[:12] for k in best.keys()]
        vals = [float(v.get("macro_f1", 0)) for v in best.values()]
        p = CHART_DIR / "adaptive_path_model_comparison.png"
        _bar(labs, vals, "Adaptive path best model macro-F1", "macro_f1", p)
        charts["adaptive_path_model_comparison"] = str(p.relative_to(ROOT))

    ad = report.get("action_distribution", {})
    if ad:
        p = CHART_DIR / "adaptive_path_action_distribution.png"
        _bar(list(map(str, ad.keys())), [float(v) for v in ad.values()], "Path action distribution", "Count", p)
        charts["adaptive_path_action_distribution"] = str(p.relative_to(ROOT))

    nd = report.get("node_type_distribution", {})
    if nd:
        p = CHART_DIR / "adaptive_path_node_type_distribution.png"
        _bar(list(map(str, nd.keys())), [float(v) for v in nd.values()], "Node type distribution", "Count", p)
        charts["adaptive_path_node_type_distribution"] = str(p.relative_to(ROOT))

    p = CHART_DIR / "adaptive_path_safety_filter_summary.png"
    _bar(
        ["safety_violation_rate", "blocked_feature_rows"],
        [
            float(report.get("safety_violation_rate", 0)),
            float(report.get("blocked_candidate_count", 0)),
        ],
        "Safety filter summary",
        "Rate / count",
        p,
    )
    charts["adaptive_path_safety_filter_summary"] = str(p.relative_to(ROOT))

    tops: Dict[str, float] = {}
    for tlist in report.get("top_features_per_target", {}).values():
        if isinstance(tlist, list):
            for name in tlist:
                tops[str(name)] = tops.get(str(name), 0.0) + 1.0
    if tops:
        items = sorted(tops.items(), key=lambda x: x[1], reverse=True)[:12]
        p = CHART_DIR / "adaptive_path_top_features.png"
        _bar([x[0] for x in items], [x[1] for x in items], "Top feature mentions", "Count", p)
        charts["adaptive_path_top_features"] = str(p.relative_to(ROOT))

    if not charts:
        status = "warning"

    viz = {"status": status, "module": "adaptive_path_ranker_visualization_report", "charts": charts}
    JSON_OUT.write_text(json.dumps(viz, indent=2), encoding="utf-8")
    md = ["# Adaptive path ranker visualization", "", f"**Status:** {status}", "", "## Charts", ""]
    for k, v in charts.items():
        md.append(f"- **{k}:** `{v}`")
    md.append("")
    MD_OUT.write_text("\n".join(md), encoding="utf-8")

    print(f"STATUS: {status}")
    print("MODULE: adaptive_path_ranker_visualization_report")
    print(f"CHART_DIR: {CHART_DIR.relative_to(ROOT)}")
    print(f"JSON_REPORT: {JSON_OUT.relative_to(ROOT)}")
    print(f"MD_REPORT: {MD_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
