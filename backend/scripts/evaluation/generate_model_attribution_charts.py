import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
REPORT_JSON = ROOT / "evaluation_outputs" / "json" / "model_attribution_report.json"
CHART_DIR = ROOT / "evaluation_outputs" / "charts"
JSON_OUTPUT = ROOT / "evaluation_outputs" / "json" / "model_attribution_visualization_report.json"
MD_OUTPUT = ROOT / "evaluation_outputs" / "reports" / "model_attribution_visualization_report.md"


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
    JSON_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    MD_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    report = load_report()
    results = report.get("results", [])

    charts: Dict[str, str] = {}

    # 1. Top features across successful models
    feature_scores = defaultdict(float)
    for result in results:
        for item in result.get("feature_importances", []):
            feature_scores[item["feature"]] += abs(float(item.get("importance", 0.0)))

    if feature_scores:
        top_items = sorted(feature_scores.items(), key=lambda x: x[1], reverse=True)[:12]
        labels = [x[0] for x in top_items]
        values = [x[1] for x in top_items]
        path = CHART_DIR / "model_attribution_top_features.png"
        save_bar(
            labels,
            values,
            "Model Attribution Top Features",
            "Aggregated importance",
            path,
        )
        charts["model_attribution_top_features"] = str(path.relative_to(ROOT))

    # 2. Method coverage
    method_counts = Counter(result.get("method_used", "none") for result in results)
    path = CHART_DIR / "model_attribution_method_coverage.png"
    save_bar(
        list(method_counts.keys()),
        list(method_counts.values()),
        "Attribution Method Coverage",
        "Count",
        path,
    )
    charts["model_attribution_method_coverage"] = str(path.relative_to(ROOT))

    # 3. Model coverage success/warning
    status_counts = Counter(result.get("status", "unknown") for result in results)
    path = CHART_DIR / "model_attribution_model_coverage.png"
    save_bar(
        list(status_counts.keys()),
        list(status_counts.values()),
        "Model Attribution Coverage",
        "Count",
        path,
    )
    charts["model_attribution_model_coverage"] = str(path.relative_to(ROOT))

    # 4. Feature importance summary per model
    model_labels = []
    model_values = []
    for result in results:
        if result.get("status") != "success":
            continue
        imps = result.get("feature_importances", [])
        if not imps:
            continue
        top_value = abs(float(imps[0].get("importance", 0.0)))
        model_labels.append(result.get("target_name", "model"))
        model_values.append(top_value)

    if model_labels:
        path = CHART_DIR / "model_attribution_feature_importance_summary.png"
        save_bar(
            model_labels,
            model_values,
            "Top Feature Importance by Model",
            "Top importance",
            path,
        )
        charts["model_attribution_feature_importance_summary"] = str(path.relative_to(ROOT))

    visualization_report = {
        "status": "success" if charts else "warning",
        "module": "model_attribution_visualization_report",
        "chart_dir": str(CHART_DIR.relative_to(ROOT)),
        "charts": charts,
        "chart_count": len(charts),
    }

    JSON_OUTPUT.write_text(json.dumps(visualization_report, indent=2), encoding="utf-8")

    lines = []
    lines.append("# Model Attribution Visualization Report\n")
    lines.append(f"Status: **{visualization_report['status']}**\n")
    lines.append(f"Chart directory: `{visualization_report['chart_dir']}`\n")
    lines.append("## Charts\n")
    for name, path in charts.items():
        lines.append(f"- {name}: `{path}`")

    MD_OUTPUT.write_text("\n".join(lines), encoding="utf-8")

    print(f"STATUS: {visualization_report['status']}")
    print("MODULE: model_attribution_visualization_report")
    print(f"CHART_DIR: {CHART_DIR.relative_to(ROOT)}")
    print(f"JSON_REPORT: {JSON_OUTPUT.relative_to(ROOT)}")
    print(f"MD_REPORT: {MD_OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()