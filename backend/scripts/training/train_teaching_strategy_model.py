import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeClassifier


DB_PATH = Path("external/core_data/tutor.db")
TABLE_NAME = "teaching_strategy_training_log"

MODEL_DIR = Path("models/teaching_strategy")
OUTPUT_JSON_DIR = Path("evaluation_outputs/json")
OUTPUT_CSV_DIR = Path("evaluation_outputs/csv")


def safe_json_loads(value: Any, default: Any) -> Any:
    if value is None:
        return default

    if isinstance(value, (dict, list)):
        return value

    try:
        return json.loads(value)
    except Exception:
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def load_logs() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)

    query = f"""
        SELECT
            id,
            learner_id,
            concept_id,
            concept_name,
            teaching_view,
            final_strategy,
            difficulty,
            assessment_difficulty,
            assessment_types_json,
            fallback_views_json,
            next_activity,
            progression_action,
            evaluation_score,
            evaluation_verdict,
            behavior_label,
            view_reward,
            policy_output_json,
            evidence_strategy_json,
            learner_memory_json,
            xai_json,
            adaptive_path_json,
            created_at
        FROM {TABLE_NAME}
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    return df


def extract_first_json_number(data: Dict[str, Any], keys: List[str], default: float = 0.0) -> float:
    for key in keys:
        if key in data:
            return safe_float(data.get(key), default)
    return default


def extract_xai_factor_flags(xai_json: Any) -> Dict[str, int]:
    xai_data = safe_json_loads(xai_json, {})

    factors = []

    if isinstance(xai_data, dict):
        # Synthetic rows use {"top_factors": [...]}
        if isinstance(xai_data.get("top_factors"), list):
            factors.extend(xai_data.get("top_factors", []))

        # Real XAI may be nested differently later
        evidence = xai_data.get("evidence", {})
        if isinstance(evidence, dict):
            feature_contributions = evidence.get("feature_contributions", {})
            if isinstance(feature_contributions, dict):
                for item in feature_contributions.get("top_factors", []):
                    if isinstance(item, dict) and item.get("feature"):
                        factors.append(item["feature"])

    factor_set = {str(f) for f in factors}

    return {
        "xai_mastery_need": int("mastery_need" in factor_set),
        "xai_evaluation_need": int("evaluation_need" in factor_set),
        "xai_view_reward_need": int("view_reward_need" in factor_set),
        "xai_forgetting_need": int("forgetting_need" in factor_set),
        "xai_behaviour_risk": int("behaviour_risk" in factor_set),
        "xai_mastery_strength": int("mastery_strength" in factor_set),
    }


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for _, row in df.iterrows():
        evidence = safe_json_loads(row.get("evidence_strategy_json"), {})
        learner_memory = safe_json_loads(row.get("learner_memory_json"), {})
        policy = safe_json_loads(row.get("policy_output_json"), {})
        adaptive_path = safe_json_loads(row.get("adaptive_path_json"), {})

        assessment_types = safe_json_loads(row.get("assessment_types_json"), [])
        fallback_views = safe_json_loads(row.get("fallback_views_json"), [])

        weak_types = learner_memory.get("weak_assessment_types", [])
        if not isinstance(weak_types, list):
            weak_types = []

        if not isinstance(assessment_types, list):
            assessment_types = []

        if not isinstance(fallback_views, list):
            fallback_views = []

        xai_flags = extract_xai_factor_flags(row.get("xai_json"))

        feature_row = {
            "id": row.get("id"),
            "learner_id": row.get("learner_id"),
            "concept_id": str(row.get("concept_id")),
            "concept_name": row.get("concept_name"),

            # Numeric features
            "mastery_before": extract_first_json_number(
                evidence,
                ["mastery_before", "mastery", "predicted_mastery_last"],
                default=0.5,
            ),
            "behaviour_score": extract_first_json_number(
                evidence,
                ["behaviour_score", "behavior_score"],
                default=0.5,
            ),
            "wrong_rate": extract_first_json_number(evidence, ["wrong_rate"], default=0.0),
            "slow_rate": extract_first_json_number(evidence, ["slow_rate"], default=0.0),
            "low_confidence_rate": extract_first_json_number(
                evidence,
                ["low_confidence_rate"],
                default=0.0,
            ),
            "forgetting_priority": extract_first_json_number(
                evidence,
                ["forgetting_priority", "review_priority"],
                default=0.0,
            ),
            "evaluation_score": safe_float(row.get("evaluation_score"), 0.5),
            "view_reward": safe_float(row.get("view_reward"), 0.5),
            "adaptive_path_score": safe_float(
                adaptive_path.get("selected_score", 0.0),
                0.0,
            ),

            # Categorical features
            "final_strategy": str(row.get("final_strategy") or "practice"),
            "difficulty": str(row.get("difficulty") or "medium"),
            "assessment_difficulty": str(row.get("assessment_difficulty") or "medium"),
            "evaluation_verdict": str(row.get("evaluation_verdict") or "unknown"),
            "behavior_label": str(row.get("behavior_label") or "unknown"),
            "policy_strategy": str(policy.get("policy_strategy") or row.get("final_strategy") or "practice"),
            "policy_difficulty": str(policy.get("policy_difficulty") or row.get("difficulty") or "medium"),

            # Count/list features
            "assessment_type_count": len(assessment_types),
            "fallback_view_count": len(fallback_views),
            "weak_type_count": len(weak_types),

            "has_debug_weakness": int("debug" in weak_types),
            "has_output_prediction_weakness": int("output_prediction" in weak_types),
            "has_syntax_weakness": int("syntax_completion" in weak_types or "syntax" in weak_types),
            "has_transfer_weakness": int("transfer" in weak_types),
            "has_explanation_weakness": int(
                "short_explanation" in weak_types or "explanation" in weak_types
            ),
            "has_mcq_weakness": int("mcq" in weak_types),

            # Targets
            "target_teaching_view": row.get("teaching_view"),
            "target_progression_action": row.get("progression_action"),
        }

        feature_row.update(xai_flags)
        rows.append(feature_row)

    features_df = pd.DataFrame(rows)

    # remove rows without targets
    features_df = features_df.dropna(
        subset=["target_teaching_view", "target_progression_action"]
    )

    return features_df


def make_preprocessor(feature_columns: List[str], categorical_columns: List[str]) -> ColumnTransformer:
    numeric_columns = [col for col in feature_columns if col not in categorical_columns]

    return ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore"),
                categorical_columns,
            ),
            (
                "numeric",
                "passthrough",
                numeric_columns,
            ),
        ]
    )


def train_models_for_target(
    df: pd.DataFrame,
    target_column: str,
    feature_columns: List[str],
    categorical_columns: List[str],
) -> Tuple[Dict[str, Any], Dict[str, Pipeline]]:
    X = df[feature_columns]
    y = df[target_column]

    label_counts = y.value_counts().to_dict()

    # Stratify only if each class has at least 2 rows
    can_stratify = all(count >= 2 for count in label_counts.values())

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y if can_stratify else None,
    )

    models = {
        "decision_tree": DecisionTreeClassifier(
            max_depth=8,
            min_samples_leaf=3,
            random_state=42,
            class_weight="balanced",
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=150,
            max_depth=12,
            min_samples_leaf=2,
            random_state=42,
            class_weight="balanced",
        ),
        "logistic_regression": LogisticRegression(
            max_iter=2000,
            class_weight="balanced",
        ),
    }

    reports = {}
    trained_pipelines = {}

    for model_name, model in models.items():
        pipeline = Pipeline(
            steps=[
                (
                    "preprocess",
                    make_preprocessor(
                        feature_columns=feature_columns,
                        categorical_columns=categorical_columns,
                    ),
                ),
                ("model", model),
            ]
        )

        pipeline.fit(X_train, y_train)
        preds = pipeline.predict(X_test)

        accuracy = accuracy_score(y_test, preds)
        macro_f1 = f1_score(y_test, preds, average="macro", zero_division=0)

        report = classification_report(
            y_test,
            preds,
            output_dict=True,
            zero_division=0,
        )

        reports[model_name] = {
            "accuracy": round(float(accuracy), 4),
            "macro_f1": round(float(macro_f1), 4),
            "classification_report": report,
            "sample_predictions": build_sample_predictions(
                X_test=X_test,
                y_test=y_test,
                preds=preds,
                limit=8,
            ),
        }

        trained_pipelines[model_name] = pipeline

    best_model_name = max(
        reports,
        key=lambda name: reports[name]["macro_f1"],
    )

    target_report = {
        "target": target_column,
        "row_count": int(len(df)),
        "label_counts": label_counts,
        "feature_columns": feature_columns,
        "categorical_columns": categorical_columns,
        "models": reports,
        "best_model": best_model_name,
        "best_macro_f1": reports[best_model_name]["macro_f1"],
        "best_accuracy": reports[best_model_name]["accuracy"],
    }

    return target_report, trained_pipelines


def build_sample_predictions(
    X_test: pd.DataFrame,
    y_test: pd.Series,
    preds: Any,
    limit: int = 8,
) -> List[Dict[str, Any]]:
    samples = []

    X_reset = X_test.reset_index(drop=True)
    y_reset = y_test.reset_index(drop=True)

    for i in range(min(limit, len(X_reset))):
        sample = X_reset.iloc[i].to_dict()

        # keep sample small
        compact_sample = {
            "concept_id": sample.get("concept_id"),
            "difficulty": sample.get("difficulty"),
            "evaluation_score": sample.get("evaluation_score"),
            "view_reward": sample.get("view_reward"),
            "behavior_label": sample.get("behavior_label"),
            "has_debug_weakness": sample.get("has_debug_weakness"),
            "has_output_prediction_weakness": sample.get("has_output_prediction_weakness"),
            "has_transfer_weakness": sample.get("has_transfer_weakness"),
        }

        samples.append(
            {
                "features": compact_sample,
                "actual": y_reset.iloc[i],
                "predicted": preds[i],
            }
        )

    return samples


def save_feature_importance(
    pipeline: Pipeline,
    feature_columns: List[str],
    target_name: str,
    model_name: str,
) -> List[Dict[str, Any]]:
    try:
        preprocessor = pipeline.named_steps["preprocess"]
        model = pipeline.named_steps["model"]

        feature_names = list(
            preprocessor.get_feature_names_out(feature_columns)
        )

        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
        elif hasattr(model, "coef_"):
            importances = abs(model.coef_).mean(axis=0)
        else:
            return []

        pairs = sorted(
            zip(feature_names, importances),
            key=lambda item: item[1],
            reverse=True,
        )

        output = [
            {
                "feature": str(name),
                "importance": round(float(value), 6),
            }
            for name, value in pairs[:20]
        ]

        importance_path = OUTPUT_JSON_DIR / f"{target_name}_{model_name}_feature_importance.json"

        with open(importance_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)

        return output

    except Exception as e:
        print(f"Feature importance skipped for {target_name}/{model_name}: {e}")
        return []


def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_CSV_DIR.mkdir(parents=True, exist_ok=True)

    raw_df = load_logs()
    features_df = build_features(raw_df)

    dataset_path = OUTPUT_CSV_DIR / "teaching_strategy_training_dataset.csv"
    features_df.to_csv(dataset_path, index=False)

    print("\nLoaded raw rows:", len(raw_df))
    print("Prepared training rows:", len(features_df))
    print("Saved dataset:", dataset_path)

    feature_columns = [
        "concept_id",
        "concept_name",

        "mastery_before",
        "behaviour_score",
        "wrong_rate",
        "slow_rate",
        "low_confidence_rate",
        "forgetting_priority",
        "evaluation_score",
        "view_reward",
        "adaptive_path_score",

        "final_strategy",
        "difficulty",
        "assessment_difficulty",
        "evaluation_verdict",
        "behavior_label",
        "policy_strategy",
        "policy_difficulty",

        "assessment_type_count",
        "fallback_view_count",
        "weak_type_count",

        "has_debug_weakness",
        "has_output_prediction_weakness",
        "has_syntax_weakness",
        "has_transfer_weakness",
        "has_explanation_weakness",
        "has_mcq_weakness",

        "xai_mastery_need",
        "xai_evaluation_need",
        "xai_view_reward_need",
        "xai_forgetting_need",
        "xai_behaviour_risk",
        "xai_mastery_strength",
    ]

    categorical_columns = [
        "concept_id",
        "concept_name",
        "final_strategy",
        "difficulty",
        "assessment_difficulty",
        "evaluation_verdict",
        "behavior_label",
        "policy_strategy",
        "policy_difficulty",
    ]

    final_report = {
        "status": "success",
        "module": "TeachingStrategyModelTrainer",
        "raw_row_count": int(len(raw_df)),
        "training_row_count": int(len(features_df)),
        "dataset_path": str(dataset_path),
        "targets": {},
        "note": (
            "Synthetic and real pipeline logs are used for bootstrapping. "
            "This model should later be retrained with larger and real interaction logs."
        ),
    }

    targets = [
        "target_teaching_view",
        "target_progression_action",
    ]

    for target in targets:
        print("\nTraining target:", target)

        target_report, trained_pipelines = train_models_for_target(
            df=features_df,
            target_column=target,
            feature_columns=feature_columns,
            categorical_columns=categorical_columns,
        )

        final_report["targets"][target] = target_report

        for model_name, pipeline in trained_pipelines.items():
            model_path = MODEL_DIR / f"{target}_{model_name}.joblib"
            joblib.dump(pipeline, model_path)

            importance = save_feature_importance(
                pipeline=pipeline,
                feature_columns=feature_columns,
                target_name=target,
                model_name=model_name,
            )

            final_report["targets"][target]["models"][model_name]["model_path"] = str(model_path)
            final_report["targets"][target]["models"][model_name]["top_feature_importance"] = importance[:10]

            print(
                f"{model_name}: "
                f"accuracy={target_report['models'][model_name]['accuracy']} "
                f"macro_f1={target_report['models'][model_name]['macro_f1']}"
            )

        print(
            "Best:",
            target_report["best_model"],
            "macro_f1:",
            target_report["best_macro_f1"],
            "accuracy:",
            target_report["best_accuracy"],
        )

    report_path = OUTPUT_JSON_DIR / "teaching_strategy_model_report.json"

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(final_report, f, indent=2)

    print("\nSaved report:", report_path)
    print("Saved models:", MODEL_DIR)

    print("\nSUMMARY")
    for target, report in final_report["targets"].items():
        print(
            target,
            "best_model:",
            report["best_model"],
            "macro_f1:",
            report["best_macro_f1"],
            "accuracy:",
            report["best_accuracy"],
        )


if __name__ == "__main__":
    main()