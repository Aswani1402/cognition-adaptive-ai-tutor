from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier


DATASET_PATH = Path("evaluation_outputs/csv/synthetic_promotion_confidence_logs.csv")
MODEL_DIR = Path("models/promotion_confidence")
JSON_REPORT_PATH = Path("evaluation_outputs/json/promotion_confidence_model_report.json")
MD_REPORT_PATH = Path("evaluation_outputs/reports/promotion_confidence_model_report.md")


FEATURE_COLUMNS = [
    "mastery",
    "evaluation_score",
    "structured_score",
    "debug_score",
    "output_prediction_score",
    "explanation_score",
    "transfer_score",
    "behaviour_score",
    "wrong_rate",
    "low_confidence_rate",
    "view_reward",
    "forgetting_priority",
    "guess_probability",
]


TARGETS = [
    "target_promotion_allowed",
    "target_progression_action",
]


def _ensure_dirs() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    JSON_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)


def _load_dataset() -> pd.DataFrame:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_PATH}. "
            "Run: python -m scripts.data.generate_synthetic_promotion_logs"
        )

    df = pd.read_csv(DATASET_PATH)

    missing_features = [col for col in FEATURE_COLUMNS if col not in df.columns]
    missing_targets = [col for col in TARGETS if col not in df.columns]

    if missing_features:
        raise ValueError(f"Missing feature columns: {missing_features}")

    if missing_targets:
        raise ValueError(f"Missing target columns: {missing_targets}")

    df = df.dropna(subset=FEATURE_COLUMNS + TARGETS).copy()

    for col in FEATURE_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=FEATURE_COLUMNS).copy()

    return df


def _build_models() -> Dict[str, Any]:
    return {
        "logistic_regression": Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        max_iter=2000,
                        class_weight="balanced",
                        random_state=42,
                    ),
                ),
            ]
        ),
        "decision_tree": DecisionTreeClassifier(
            max_depth=8,
            min_samples_leaf=10,
            class_weight="balanced",
            random_state=42,
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            min_samples_leaf=5,
            class_weight="balanced",
            random_state=42,
        ),
    }


def _classification_report_dict(y_true, y_pred) -> Dict[str, Any]:
    return classification_report(
        y_true,
        y_pred,
        output_dict=True,
        zero_division=0,
    )


def _train_for_target(df: pd.DataFrame, target: str) -> Dict[str, Any]:
    X = df[FEATURE_COLUMNS]
    y = df[target]

    stratify = y if y.nunique() > 1 else None

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=42,
        stratify=stratify,
    )

    models = _build_models()

    target_report: Dict[str, Any] = {
        "target": target,
        "row_count": int(len(df)),
        "train_count": int(len(X_train)),
        "test_count": int(len(X_test)),
        "class_distribution": {
            str(k): int(v)
            for k, v in y.value_counts().to_dict().items()
        },
        "feature_columns": FEATURE_COLUMNS,
        "models": {},
        "best_model": None,
    }

    best_name = None
    best_score = -1.0
    best_model = None

    for model_name, model in models.items():
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)

        accuracy = accuracy_score(y_test, y_pred)
        macro_f1 = f1_score(y_test, y_pred, average="macro", zero_division=0)
        weighted_f1 = f1_score(y_test, y_pred, average="weighted", zero_division=0)

        cm = confusion_matrix(y_test, y_pred)

        model_report = {
            "accuracy": round(float(accuracy), 4),
            "macro_f1": round(float(macro_f1), 4),
            "weighted_f1": round(float(weighted_f1), 4),
            "classification_report": _classification_report_dict(y_test, y_pred),
            "confusion_matrix": cm.tolist(),
        }

        target_report["models"][model_name] = model_report

        print(
            f"{model_name}: "
            f"accuracy={round(float(accuracy), 4)} "
            f"macro_f1={round(float(macro_f1), 4)} "
            f"weighted_f1={round(float(weighted_f1), 4)}"
        )

        if macro_f1 > best_score:
            best_score = float(macro_f1)
            best_name = model_name
            best_model = model

    assert best_name is not None
    assert best_model is not None

    model_path = MODEL_DIR / f"{target}_{best_name}.joblib"
    joblib.dump(
        {
            "model": best_model,
            "feature_columns": FEATURE_COLUMNS,
            "target": target,
            "model_name": best_name,
        },
        model_path,
    )

    target_report["best_model"] = {
        "name": best_name,
        "macro_f1": round(best_score, 4),
        "path": str(model_path),
    }

    return target_report


def _feature_importance_from_model(model_bundle_path: str) -> List[Dict[str, Any]]:
    bundle = joblib.load(model_bundle_path)
    model = bundle["model"]

    raw_model = model
    if isinstance(model, Pipeline):
        raw_model = model.named_steps.get("model")

    importances = None

    if hasattr(raw_model, "feature_importances_"):
        importances = raw_model.feature_importances_
    elif hasattr(raw_model, "coef_"):
        coef = raw_model.coef_
        if len(coef.shape) == 2:
            importances = abs(coef).mean(axis=0)

    if importances is None:
        return []

    rows = []
    for feature, importance in zip(FEATURE_COLUMNS, importances):
        rows.append(
            {
                "feature": feature,
                "importance": round(float(importance), 6),
            }
        )

    rows.sort(key=lambda item: item["importance"], reverse=True)
    return rows


def _write_markdown_report(report: Dict[str, Any]) -> None:
    lines = []

    lines.append("# Promotion Confidence Model Report")
    lines.append("")
    lines.append(f"Dataset: `{report['dataset_path']}`")
    lines.append(f"Rows: `{report['row_count']}`")
    lines.append("")
    lines.append("## Targets")
    lines.append("")

    for target, target_report in report["targets"].items():
        lines.append(f"### {target}")
        lines.append("")
        lines.append(f"Train rows: `{target_report['train_count']}`")
        lines.append(f"Test rows: `{target_report['test_count']}`")
        lines.append(f"Class distribution: `{target_report['class_distribution']}`")
        lines.append("")
        lines.append("#### Model comparison")
        lines.append("")
        lines.append("| Model | Accuracy | Macro F1 | Weighted F1 |")
        lines.append("|---|---:|---:|---:|")

        for model_name, model_report in target_report["models"].items():
            lines.append(
                f"| {model_name} | "
                f"{model_report['accuracy']} | "
                f"{model_report['macro_f1']} | "
                f"{model_report['weighted_f1']} |"
            )

        best = target_report["best_model"]

        lines.append("")
        lines.append(
            f"Best model: `{best['name']}` "
            f"with macro F1 `{best['macro_f1']}`"
        )
        lines.append(f"Saved model: `{best['path']}`")
        lines.append("")

        feature_importance = target_report.get("feature_importance", [])
        if feature_importance:
            lines.append("#### Top feature importance")
            lines.append("")
            lines.append("| Feature | Importance |")
            lines.append("|---|---:|")

            for row in feature_importance[:10]:
                lines.append(f"| {row['feature']} | {row['importance']} |")

            lines.append("")

    lines.append("## Notes")
    lines.append("")
    lines.append(
        "This model is trained on synthetic tutor interaction logs for controlled "
        "pipeline validation and bootstrapping. Real learner logs should replace "
        "or extend this dataset later."
    )
    lines.append("")
    lines.append(
        "The model should run in comparison mode first. It should not override "
        "the baseline progression reward engine until agreement and stability "
        "are evaluated."
    )

    MD_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main():
    _ensure_dirs()

    df = _load_dataset()

    print("\nPROMOTION CONFIDENCE MODEL TRAINING")
    print("Loaded dataset:", DATASET_PATH)
    print("Rows:", len(df))
    print("Features:", FEATURE_COLUMNS)

    report: Dict[str, Any] = {
        "status": "success",
        "dataset_path": str(DATASET_PATH),
        "row_count": int(len(df)),
        "feature_columns": FEATURE_COLUMNS,
        "targets": {},
    }

    for target in TARGETS:
        print(f"\nTraining target: {target}")
        target_report = _train_for_target(df, target)

        best_path = target_report["best_model"]["path"]
        target_report["feature_importance"] = _feature_importance_from_model(best_path)

        report["targets"][target] = target_report

        best = target_report["best_model"]
        print(
            "Best:",
            best["name"],
            "macro_f1:",
            best["macro_f1"],
            "path:",
            best["path"],
        )

    JSON_REPORT_PATH.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    _write_markdown_report(report)

    print("\nSaved JSON report:", JSON_REPORT_PATH)
    print("Saved Markdown report:", MD_REPORT_PATH)
    print("Saved models:", MODEL_DIR)

    print("\nSUMMARY")
    for target, target_report in report["targets"].items():
        best = target_report["best_model"]
        print(
            target,
            "best_model:",
            best["name"],
            "macro_f1:",
            best["macro_f1"],
        )


if __name__ == "__main__":
    main()