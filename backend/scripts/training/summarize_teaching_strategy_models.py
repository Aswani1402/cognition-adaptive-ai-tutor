import json
from pathlib import Path


REPORT_PATH = Path("evaluation_outputs/json/teaching_strategy_model_report.json")


def print_model_summary():
    if not REPORT_PATH.exists():
        print("Report not found:", REPORT_PATH)
        print("Run: python -m scripts.training.train_teaching_strategy_model")
        return

    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        report = json.load(f)

    print("\nTEACHING STRATEGY MODEL SUMMARY")
    print("Status:", report.get("status"))
    print("Raw rows:", report.get("raw_row_count"))
    print("Training rows:", report.get("training_row_count"))
    print("Dataset:", report.get("dataset_path"))

    targets = report.get("targets", {})

    for target_name, target_report in targets.items():
        print("\n" + "=" * 80)
        print("TARGET:", target_name)
        print("Best model:", target_report.get("best_model"))
        print("Best macro F1:", target_report.get("best_macro_f1"))
        print("Best accuracy:", target_report.get("best_accuracy"))

        label_counts = target_report.get("label_counts", {})
        print("\nLabel distribution:")
        for label, count in label_counts.items():
            print(f"  {label}: {count}")

        print("\nModel comparison:")
        models = target_report.get("models", {})

        for model_name, model_data in models.items():
            print(
                f"  {model_name}: "
                f"accuracy={model_data.get('accuracy')} "
                f"macro_f1={model_data.get('macro_f1')}"
            )

        print("\nTop features per model:")
        for model_name, model_data in models.items():
            print(f"\n  {model_name}:")
            features = model_data.get("top_feature_importance", [])

            if not features:
                print("    No feature importance available.")
                continue

            for item in features[:10]:
                print(
                    f"    {item.get('feature')}: "
                    f"{item.get('importance')}"
                )

        print("\nSample predictions from best model:")
        best_model = target_report.get("best_model")
        best_data = models.get(best_model, {})
        samples = best_data.get("sample_predictions", [])

        for sample in samples[:5]:
            print("  actual:", sample.get("actual"))
            print("  predicted:", sample.get("predicted"))
            print("  features:", sample.get("features"))
            print("  ---")


if __name__ == "__main__":
    print_model_summary()