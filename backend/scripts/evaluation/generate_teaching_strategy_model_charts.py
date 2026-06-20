"""
Matplotlib charts for teaching strategy model report.

Run: python -m scripts.evaluation.generate_teaching_strategy_model_charts
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
REPORT_JSON = ROOT / "evaluation_outputs" / "json" / "teaching_strategy_model_report.json"
CHART_DIR = ROOT / "evaluation_outputs" / "charts"
JSON_OUT = ROOT / "evaluation_outputs" / "json" / "teaching_strategy_model_visualization_report.json"
MD_OUT = ROOT / "evaluation_outputs" / "reports" / "teaching_strategy_model_visualization_report.md"


def load_report() -> Dict[str, Any]:
    if not REPORT_JSON.exists():
        raise FileNotFoundError(f"Missing {REPORT_JSON}")
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
    charts: Dict[str, str] = {}

    try:
        report = load_report()
    except FileNotFoundError as exc:
        payload = {"status": "warning", "module": "teaching_strategy_model_visualization_report", "error": str(exc)}
        JSON_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        MD_OUT.write_text(f"# Teaching strategy charts\n\n{exc}\n", encoding="utf-8")
        print("STATUS: warning")
        print("MODULE: teaching_strategy_model_visualization_report")
        print(f"CHART_DIR: {CHART_DIR.relative_to(ROOT)}")
        print(f"JSON_REPORT: {JSON_OUT.relative_to(ROOT)}")
        print(f"MD_REPORT: {MD_OUT.relative_to(ROOT)}")
        return

    status = "success"
    best = report.get("best_metrics_per_target", {})
    if best:
        labels = [k[:16] for k in best.keys()]
        vals = [max(float(v.get("macro_f1", 0)), float(v.get("accuracy", 0))) for v in best.values()]
        p = CHART_DIR / "teaching_strategy_model_comparison.png"
        save_bar(labels, vals, "Teaching strategy best model score", "Score", p)
        charts["teaching_strategy_model_comparison"] = str(p.relative_to(ROOT))

    from scripts.training.strategy.train_teaching_strategy_selector import build_training_dataframe

    df, _ = build_training_dataframe(ROOT / "external" / "core_data" / "tutor.db")
    dist_l: List[str] = []
    dist_v: List[float] = []
    for col in ("teaching_view", "difficulty", "next_action", "assessment_type_group"):
        if col not in df.columns:
            continue
        vc = df[col].astype(str).value_counts().head(10)
        for lab, c in vc.items():
            dist_l.append(f"{col[:8]}:{str(lab)[:14]}")
            dist_v.append(float(c))
    if dist_l:
        p = CHART_DIR / "teaching_strategy_target_distribution.png"
        save_bar(dist_l, dist_v, "Label distribution (sample)", "Count", p)
        charts["teaching_strategy_target_distribution"] = str(p.relative_to(ROOT))

    conf_l: List[str] = []
    conf_v: List[float] = []
    for tgt, cm in report.get("confusion_matrices", {}).items():
        if not cm:
            continue
        tot = sum(sum(r) for r in cm)
        if tot <= 0:
            continue
        ok = sum(float(cm[i][i]) for i in range(min(len(cm), len(cm[0]))))
        conf_l.extend([f"{tgt[:12]}\nok", f"{tgt[:12]}\nmiss"])
        conf_v.extend([ok, max(tot - ok, 0.0)])
    if conf_l:
        p = CHART_DIR / "teaching_strategy_confusion_summary.png"
        save_bar(conf_l, conf_v, "Confusion summary", "Count", p)
        charts["teaching_strategy_confusion_summary"] = str(p.relative_to(ROOT))

    feat_scores: defaultdict[str, float] = defaultdict(float)
    for tops in report.get("top_features_per_target", {}).values():
        if isinstance(tops, list):
            for name in tops:
                feat_scores[str(name)] += 1.0
    if feat_scores:
        top = sorted(feat_scores.items(), key=lambda x: x[1], reverse=True)[:14]
        p = CHART_DIR / "teaching_strategy_top_features.png"
        save_bar([x[0] for x in top], [x[1] for x in top], "Top feature mentions", "Count", p)
        charts["teaching_strategy_top_features"] = str(p.relative_to(ROOT))

    pred_l = list(best.keys())
    pred_v = [float(report.get("best_metrics_per_target", {}).get(k, {}).get("accuracy", 0)) for k in pred_l]
    if pred_l:
        p = CHART_DIR / "teaching_strategy_prediction_distribution.png"
        save_bar([f"{k}\nacc" for k in pred_l], pred_v, "Best-model accuracy by target", "Accuracy", p)
        charts["teaching_strategy_prediction_distribution"] = str(p.relative_to(ROOT))

    if not charts:
        status = "warning"

    viz = {
        "status": status,
        "module": "teaching_strategy_model_visualization_report",
        "charts": charts,
    }
    JSON_OUT.write_text(json.dumps(viz, indent=2), encoding="utf-8")
    md = ["# Teaching strategy model visualization", "", f"**Status:** {status}", "", "## Charts", ""]
    for k, v in charts.items():
        md.append(f"- **{k}:** `{v}`")
    md.append("")
    MD_OUT.write_text("\n".join(md), encoding="utf-8")

    print(f"STATUS: {status}")
    print("MODULE: teaching_strategy_model_visualization_report")
    print(f"CHART_DIR: {CHART_DIR.relative_to(ROOT)}")
    print(f"JSON_REPORT: {JSON_OUT.relative_to(ROOT)}")
    print(f"MD_REPORT: {MD_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
