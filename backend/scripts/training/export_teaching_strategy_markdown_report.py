import json
from pathlib import Path
from datetime import datetime, UTC


REPORT_JSON_PATH = Path("evaluation_outputs/json/teaching_strategy_model_report.json")
OUTPUT_REPORT_DIR = Path("evaluation_outputs/reports")
OUTPUT_MD_PATH = OUTPUT_REPORT_DIR / "teaching_strategy_model_report.md"


def load_json_report() -> dict:
    if not REPORT_JSON_PATH.exists():
        raise FileNotFoundError(
            f"JSON report not found: {REPORT_JSON_PATH}\n"
            "Run this first:\n"
            "python -m scripts.training.train_teaching_strategy_model"
        )

    with open(REPORT_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def fmt(value):
    if value is None:
        return "N/A"
    return str(value)


def make_model_comparison_table(models: dict) -> str:
    lines = [
        "| Model | Accuracy | Macro F1 |",
        "|---|---:|---:|",
    ]

    for model_name, model_data in models.items():
        lines.append(
            f"| {model_name} | "
            f"{model_data.get('accuracy')} | "
            f"{model_data.get('macro_f1')} |"
        )

    return "\n".join(lines)


def make_label_distribution_table(label_counts: dict) -> str:
    lines = [
        "| Label | Count |",
        "|---|---:|",
    ]

    for label, count in label_counts.items():
        lines.append(f"| {label} | {count} |")

    return "\n".join(lines)


def make_top_features_section(models: dict) -> str:
    sections = []

    for model_name, model_data in models.items():
        features = model_data.get("top_feature_importance", [])

        sections.append(f"#### {model_name}")

        if not features:
            sections.append("No feature importance available.")
            continue

        sections.append("| Rank | Feature | Importance |")
        sections.append("|---:|---|---:|")

        for idx, item in enumerate(features[:10], start=1):
            sections.append(
                f"| {idx} | `{item.get('feature')}` | {item.get('importance')} |"
            )

        sections.append("")

    return "\n".join(sections)


def make_sample_predictions_section(best_model_data: dict) -> str:
    samples = best_model_data.get("sample_predictions", [])

    if not samples:
        return "No sample predictions available."

    lines = []

    for idx, sample in enumerate(samples[:8], start=1):
        features = sample.get("features", {})

        lines.append(f"#### Sample {idx}")
        lines.append("")
        lines.append(f"- **Actual:** `{sample.get('actual')}`")
        lines.append(f"- **Predicted:** `{sample.get('predicted')}`")
        lines.append("- **Key features:**")
        lines.append("")

        for key, value in features.items():
            lines.append(f"  - `{key}`: {value}")

        lines.append("")

    return "\n".join(lines)


def build_markdown(report: dict) -> str:
    generated_at = datetime.now(UTC).isoformat()

    lines = []

    lines.append("# Teaching Strategy Model Report")
    lines.append("")
    lines.append(f"Generated at: `{generated_at}`")
    lines.append("")
    lines.append("## 1. Purpose")
    lines.append("")
    lines.append(
        "This report summarizes the model-based Teaching Strategy Selector training. "
        "The goal is to predict the most suitable teaching view and progression action "
        "from learner evidence such as mastery, behaviour, evaluation score, weak assessment "
        "types, view reward, XAI factors, and adaptive path evidence."
    )
    lines.append("")
    lines.append("## 2. Dataset Summary")
    lines.append("")
    lines.append(f"- **Raw rows:** {report.get('raw_row_count')}")
    lines.append(f"- **Training rows:** {report.get('training_row_count')}")
    lines.append(f"- **Dataset path:** `{report.get('dataset_path')}`")
    lines.append("")
    lines.append("### Dataset note")
    lines.append("")
    lines.append(
        "The current dataset contains a mixture of real pipeline logs and synthetic tutor "
        "interaction traces. Synthetic traces are used for controlled bootstrapping and "
        "system validation. The model should be retrained later with larger real learner "
        "interaction logs for stronger generalization."
    )
    lines.append("")

    targets = report.get("targets", {})

    for target_name, target_report in targets.items():
        lines.append("---")
        lines.append("")
        lines.append(f"## 3. Target: `{target_name}`")
        lines.append("")
        lines.append(f"- **Best model:** `{target_report.get('best_model')}`")
        lines.append(f"- **Best accuracy:** {target_report.get('best_accuracy')}")
        lines.append(f"- **Best macro F1:** {target_report.get('best_macro_f1')}")
        lines.append("")

        lines.append("### 3.1 Label Distribution")
        lines.append("")
        lines.append(make_label_distribution_table(target_report.get("label_counts", {})))
        lines.append("")

        lines.append("### 3.2 Model Comparison")
        lines.append("")
        models = target_report.get("models", {})
        lines.append(make_model_comparison_table(models))
        lines.append("")

        lines.append("### 3.3 Top Feature Importance / Coefficients")
        lines.append("")
        lines.append(make_top_features_section(models))
        lines.append("")

        best_model_name = target_report.get("best_model")
        best_model_data = models.get(best_model_name, {})

        lines.append("### 3.4 Sample Predictions from Best Model")
        lines.append("")
        lines.append(make_sample_predictions_section(best_model_data))
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 4. Interpretation")
    lines.append("")
    lines.append(
        "Decision Tree is currently selected for inference because it achieved top performance "
        "and provides an interpretable decision path. Random Forest is retained as a stronger "
        "ensemble model for future noisy or real learner data, and Logistic Regression is kept "
        "as a transparent linear baseline."
    )
    lines.append("")
    lines.append("## 5. Current Limitations")
    lines.append("")
    lines.append(
        "- Current high scores are expected because most logs are synthetic and rule-generated.\n"
        "- These scores should not be claimed as real learner performance.\n"
        "- More diverse real interaction logs are required before final deployment claims.\n"
        "- The model is currently used in comparison mode and should not fully replace the evidence-aware selector yet."
    )
    lines.append("")
    lines.append("## 6. Next Steps")
    lines.append("")
    lines.append(
        "1. Integrate the model-based selector into the main pipeline as comparison-only.\n"
        "2. Log evidence-aware vs model-based agreement.\n"
        "3. Generate larger synthetic datasets: 2,000 to 10,000 rows.\n"
        "4. Add controlled noise to synthetic logs for better robustness testing.\n"
        "5. Retrain models and compare again.\n"
        "6. Later upgrade teaching-view selection to a contextual bandit."
    )
    lines.append("")

    return "\n".join(lines)


def main():
    OUTPUT_REPORT_DIR.mkdir(parents=True, exist_ok=True)

    report = load_json_report()
    markdown = build_markdown(report)

    with open(OUTPUT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(markdown)

    print("\nMarkdown report exported successfully.")
    print("Output:", OUTPUT_MD_PATH)


if __name__ == "__main__":
    main()