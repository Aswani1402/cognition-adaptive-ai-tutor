from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

from tutor.xai.model_attribution_explainer import ModelAttributionExplainer


def main() -> None:
    explainer = ModelAttributionExplainer(random_state=42, n_repeats=3)

    # 1. Missing model should not crash
    missing = explainer.explain_model(
        model_path="models/not_existing_model.pkl",
        dataset_path="evaluation_outputs/csv/not_existing.csv",
        target_name="missing_model_test",
    )
    assert missing["status"] == "warning"

    # 2. Synthetic sklearn model attribution
    rng = np.random.default_rng(42)
    n = 120
    X = pd.DataFrame(
        {
            "mastery_score": rng.uniform(0, 1, n),
            "behaviour_risk": rng.uniform(0, 1, n),
            "fused_score": rng.uniform(0, 1, n),
            "hint_rate": rng.uniform(0, 1, n),
        }
    )
    y = ((X["mastery_score"] > 0.55) & (X["fused_score"] > 0.5)).astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y,
    )

    model = RandomForestClassifier(n_estimators=50, random_state=42)
    model.fit(X_train, y_train)

    result = explainer.explain_model_object(
        model=model,
        X=X_test,
        y=y_test,
        target_name="synthetic_test_model",
        feature_names=list(X.columns),
    )

    assert result["status"] == "success"
    assert result["module"] == "ModelAttributionExplainer"
    assert result["feature_importances"]
    assert result["top_features"]
    assert result["method_used"] in {"permutation_importance", "builtin_importance"}

    for item in result["feature_importances"]:
        assert "feature" in item
        assert "importance" in item
        assert "rank" in item
        assert isinstance(item["rank"], int)

    # 3. Built-in demo
    demo = explainer.explain_synthetic_demo()
    assert demo["status"] == "success"
    assert demo["feature_importances"]

    print("STATUS: success")
    print("MODULE: model_attribution_explainer_test")


if __name__ == "__main__":
    main()