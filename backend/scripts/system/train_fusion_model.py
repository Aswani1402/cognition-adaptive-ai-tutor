import json
import sqlite3
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

DB_PATH = Path("external/core_data/tutor.db")
MODEL_DIR = Path("models/fusion")
MODEL_DIR.mkdir(parents=True, exist_ok=True)


def load_data():
    conn = sqlite3.connect(str(DB_PATH))
    df = pd.read_sql_query("""
        SELECT
            mastery_score,
            behavior_label,
            behavior_score,
            review_due,
            evaluation_score,
            evaluation_quality,
            learning_signal,
            final_action
        FROM fusion_decision_log
        WHERE final_action IS NOT NULL
    """, conn)
    conn.close()
    return df


def main():
    df = load_data()

    if len(df) < 20:
        print(f"Not enough data yet. Need at least 20 rows, found {len(df)}.")
        return

    X = df.drop(columns=["final_action"])
    y = df["final_action"]

    numeric_features = [
        "mastery_score",
        "behavior_score",
        "review_due",
        "evaluation_score",
    ]

    categorical_features = [
        "behavior_label",
        "evaluation_quality",
        "learning_signal",
    ]

    numeric_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median"))
    ])

    categorical_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore"))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features),
        ]
    )

    model = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("classifier", RandomForestClassifier(
            n_estimators=100,
            random_state=42
        ))
    ])

    model.fit(X, y)

    joblib.dump(model, MODEL_DIR / "fusion_model.joblib")

    metadata = {
        "rows_used": len(df),
        "features": list(X.columns),
        "target": "final_action",
    }

    with open(MODEL_DIR / "fusion_model_meta.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"Fusion model trained successfully on {len(df)} rows.")
    print(f"Saved to: {MODEL_DIR / 'fusion_model.joblib'}")


if __name__ == "__main__":
    main()