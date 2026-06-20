import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tutor.xai.model_attribution_explainer import ModelAttributionExplainer


ROOT = Path(__file__).resolve().parents[2]
JSON_OUTPUT = ROOT / "evaluation_outputs" / "json" / "model_attribution_report.json"
MD_OUTPUT = ROOT / "evaluation_outputs" / "reports" / "model_attribution_report.md"


def find_files(patterns: List[str]) -> List[Path]:
    found: List[Path] = []
    for pattern in patterns:
        found.extend(ROOT.glob(pattern))
    return sorted(set(found))


def discover_targets() -> List[Dict[str, Any]]:
    """
    Best-effort discovery. Missing models are allowed and reported.
    The synthetic demo always runs so the module can be evaluated.
    """
    targets: List[Dict[str, Any]] = []

    # promotion confidence logs are known from project history
    promotion_csv = ROOT / "evaluation_outputs" / "csv" / "synthetic_promotion_confidence_logs.csv"
    promotion_models = find_files(
        [
            "models/promotion/**/*.pkl",
            "models/promotion/**/*.joblib",
            "models/promotion/**/*.pickle",
            "models/policy/**/*.pkl",
            "models/policy/**/*.joblib",
        ]
    )

    if promotion_models and promotion_csv.exists():
        targets.append(
            {
                "target_name": "promotion_confidence_model",
                "model_path": str(promotion_models[0]),
                "dataset_path": str(promotion_csv),
                "target_column": "promotion_allowed",
            }
        )
    else:
        targets.append(
            {
                "target_name": "promotion_confidence_model",
                "model_path": str(promotion_models[0]) if promotion_models else None,
                "dataset_path": str(promotion_csv) if promotion_csv.exists() else None,
                "target_column": "promotion_allowed",
                "expected_missing": True,
            }
        )

    behaviour_csvs = find_files(
        [
            "evaluation_outputs/csv/*behaviour*.csv",
            "evaluation_outputs/csv/*behavior*.csv",
        ]
    )
    behaviour_models = find_files(
        [
            "models/behaviour/**/*.pkl",
            "models/behaviour/**/*.joblib",
            "models/behavior/**/*.pkl",
            "models/behavior/**/*.joblib",
        ]
    )

    if behaviour_models and behaviour_csvs:
        targets.append(
            {
                "target_name": "behaviour_model",
                "model_path": str(behaviour_models[0]),
                "dataset_path": str(behaviour_csvs[0]),
                "target_column": None,
            }
        )
    else:
        targets.append(
            {
                "target_name": "behaviour_model",
                "model_path": str(behaviour_models[0]) if behaviour_models else None,
                "dataset_path": str(behaviour_csvs[0]) if behaviour_csvs else None,
                "target_column": None,
                "expected_missing": True,
            }
        )

    doubt_csvs = find_files(
        [
            "evaluation_outputs/csv/*doubt*.csv",
            "data/**/*doubt*.csv",
        ]
    )
    doubt_models = find_files(
        [
            "models/doubt/**/*.pkl",
            "models/doubt/**/*.joblib",
            "models/doubt/**/*.pickle",
        ]
    )

    if doubt_models and doubt_csvs:
        targets.append(
            {
                "target_name": "doubt_classifier",
                "model_path": str(doubt_models[0]),
                "dataset_path": str(doubt_csvs[0]),
                "target_column": None,
            }
        )
    else:
        targets.append(
            {
                "target_name": "doubt_classifier",
                "model_path": str(doubt_models[0]) if doubt_models else None,
                "dataset_path": str(doubt_csvs[0]) if doubt_csvs else None,
                "target_column": None,
                "expected_missing": True,
            }
        )

    return targets


def write_report(report: Dict[str, Any]) -> None:
    JSON_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    MD_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    JSON_OUTPUT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines: List[str] = []
    lines.append("# Model Attribution / XAI Report\n")
    lines.append(f"Status: **{report['status']}**\n")
    lines.append(
        "The XAI layer was extended with model-level attribution using "
        "permutation importance for trained machine-learning components where "
        "artifacts and evaluation data are available. This complements the "
        "dashboard’s normalized evidence scoring by identifying which model "
        "input features most influence learned predictions. SHAP is treated as "
        "optional, while permutation importance is used as the default "
        "transparent and dependency-safe attribution method.\n"
    )

    lines.append("## Summary\n")
    lines.append(f"- SHAP available: {report['shap_available']}")
    lines.append(f"- Explained model count: {report['explained_model_count']}")
    lines.append(f"- Missing model/dataset count: {report['missing_model_count']}")
    lines.append(f"- Attribution method counts: {report['method_counts']}")
    lines.append("")

    lines.append("## Explained Models\n")
    for result in report["results"]:
        lines.append(f"### {result['target_name']}")
        lines.append(f"- Status: {result['status']}")
        lines.append(f"- Model type: {result.get('model_type')}")
        lines.append(f"- Method used: {result.get('method_used')}")
        lines.append(f"- Top features: {', '.join(result.get('top_features', [])) or 'None'}")
        if result.get("explanation_text"):
            lines.append(f"- Explanation: {result['explanation_text']}")
        if result.get("missing_path"):
            lines.append(f"- Missing path: `{result['missing_path']}`")
        lines.append("")

    lines.append("## Limitations\n")
    for item in report["limitations"]:
        lines.append(f"- {item}")

    MD_OUTPUT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    explainer = ModelAttributionExplainer(random_state=42, n_repeats=5)

    results: List[Dict[str, Any]] = []

    # Always run synthetic demo
    synthetic = explainer.explain_synthetic_demo()
    results.append(synthetic)

    for target in discover_targets():
        if not target.get("model_path") or not target.get("dataset_path"):
            results.append(
                {
                    "status": "warning",
                    "module": "ModelAttributionExplainer",
                    "target_name": target["target_name"],
                    "model_type": "unknown",
                    "method_used": "none",
                    "shap_available": explainer.shap_available,
                    "feature_importances": [],
                    "top_features": [],
                    "explanation_text": "Attribution unavailable because model or dataset artifact was not found.",
                    "missing_path": str(
                        {
                            "model_path": target.get("model_path"),
                            "dataset_path": target.get("dataset_path"),
                        }
                    ),
                    "limitations": [
                        "Real model attribution requires both model artifact and compatible dataset.",
                    ],
                }
            )
            continue

        results.append(
            explainer.explain_model(
                model_path=target["model_path"],
                dataset_path=target["dataset_path"],
                target_name=target["target_name"],
                target_column=target.get("target_column"),
            )
        )

    explained_model_count = sum(1 for r in results if r.get("status") == "success")
    missing_model_count = sum(1 for r in results if r.get("status") != "success")
    method_counts = Counter(r.get("method_used", "none") for r in results)

    report = {
        "status": "success" if explained_model_count >= 1 else "warning",
        "module": "model_attribution_report",
        "shap_available": explainer.shap_available,
        "explained_model_count": explained_model_count,
        "missing_model_count": missing_model_count,
        "method_counts": dict(method_counts),
        "results": results,
        "frontend_readiness": True,
        "limitations": [
            "Permutation importance depends on available model artifacts and evaluation datasets.",
            "SHAP is optional and not required for this project version.",
            "Missing model artifacts are reported as warnings, not failures.",
            "This module complements the existing XAI dashboard and does not replace it.",
        ],
    }

    write_report(report)

    print(f"STATUS: {report['status']}")
    print("MODULE: model_attribution_report")
    print(f"JSON_REPORT: {JSON_OUTPUT.relative_to(ROOT)}")
    print(f"MD_REPORT: {MD_OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()