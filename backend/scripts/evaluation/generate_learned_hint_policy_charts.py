"""
Matplotlib charts for learned hint policy report.

Run: python -m scripts.evaluation.generate_learned_hint_policy_charts
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "evaluation_outputs" / "json" / "learned_hint_policy_report.json"
CHART_DIR = ROOT / "evaluation_outputs" / "charts"
JSON_OUT = ROOT / "evaluation_outputs" / "json" / "learned_hint_policy_visualization_report.json"
MD_OUT = ROOT / "evaluation_outputs" / "reports" / "learned_hint_policy_visualization_report.md"


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
    charts: Dict[str, str] = {}

    if not REPORT.exists():
        payload = {
            "status": "warning",
            "module": "learned_hint_policy_visualization_report",
            "error": f"Missing {REPORT}",
            "charts": {},
        }
        JSON_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        MD_OUT.write_text("# Learned hint charts\n\nReport missing.\n", encoding="utf-8")
        print("STATUS: warning")
        print("MODULE: learned_hint_policy_visualization_report")
        print(f"CHART_DIR: {CHART_DIR.relative_to(ROOT)}")
        print(f"JSON_REPORT: {JSON_OUT.relative_to(ROOT)}")
        print(f"MD_REPORT: {MD_OUT.relative_to(ROOT)}")
        return

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    status = "success"

    best = report.get("best_metrics_per_target", {})
    if best:
        labs = [k[:14] for k in best.keys()]
        vals = [max(float(v.get("macro_f1", 0)), float(v.get("accuracy", 0))) for v in best.values()]
        p = CHART_DIR / "learned_hint_model_comparison.png"
        save_bar(labs, vals, "Learned hint best model score", "Score", p)
        charts["learned_hint_model_comparison"] = str(p.relative_to(ROOT))

    htd = report.get("hint_type_distribution", {})
    if htd:
        p = CHART_DIR / "learned_hint_type_distribution.png"
        save_bar(list(map(str, htd.keys())), [float(v) for v in htd.values()], "Hint type distribution", "Count", p)
        charts["learned_hint_type_distribution"] = str(p.relative_to(ROOT))

    hld = report.get("hint_level_distribution", {})
    if hld:
        p = CHART_DIR / "learned_hint_level_distribution.png"
        save_bar(list(hld.keys()), [float(v) for v in hld.values()], "Hint level distribution", "Count", p)
        charts["learned_hint_level_distribution"] = str(p.relative_to(ROOT))

    psd = report.get("predicted_success_distribution", {})
    if psd:
        p = CHART_DIR / "learned_hint_success_distribution.png"
        save_bar([str(k) for k in psd.keys()], [float(v) for v in psd.values()], "Training success label distribution", "Count", p)
        charts["learned_hint_success_distribution"] = str(p.relative_to(ROOT))

    tops: Dict[str, float] = {}
    for tlist in report.get("top_features_per_target", {}).values():
        if isinstance(tlist, list):
            for name in tlist:
                tops[str(name)] = tops.get(str(name), 0.0) + 1.0
    if tops:
        items = sorted(tops.items(), key=lambda x: x[1], reverse=True)[:12]
        p = CHART_DIR / "learned_hint_top_features.png"
        save_bar([x[0] for x in items], [x[1] for x in items], "Top feature mentions", "Count", p)
        charts["learned_hint_top_features"] = str(p.relative_to(ROOT))

    if not charts:
        status = "warning"

    viz = {"status": status, "module": "learned_hint_policy_visualization_report", "charts": charts}
    JSON_OUT.write_text(json.dumps(viz, indent=2), encoding="utf-8")
    md = ["# Learned hint policy visualization", "", f"**Status:** {status}", "", "## Charts", ""]
    for k, v in charts.items():
        md.append(f"- **{k}:** `{v}`")
    md.append("")
    MD_OUT.write_text("\n".join(md), encoding="utf-8")

    print(f"STATUS: {status}")
    print("MODULE: learned_hint_policy_visualization_report")
    print(f"CHART_DIR: {CHART_DIR.relative_to(ROOT)}")
    print(f"JSON_REPORT: {JSON_OUT.relative_to(ROOT)}")
    print(f"MD_REPORT: {MD_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
