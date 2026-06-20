import json
import sqlite3
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

DB_PATH = Path("external/core_data/tutor.db")
MODEL_DIR = Path("models/policy")
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
            learning_signal,
            final_action,
            recommended_strategy,
            recommended_difficulty,
            next_concept_id
        FROM policy_decision_log
        WHERE next_concept_id IS NOT NULL
          AND recommended_strategy IS NOT NULL
          AND recommended_difficulty IS NOT NULL
    """, conn)
    conn.close()
    return df


def main():
    df = load_data()

    if len(df) < 30:
        print(f"Not enough data yet. Need at least 30 rows, found {len(df)}.")
        return

    X = df.drop(columns=["next_concept_id"])
    y = df["next_concept_id"].astype(str)

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=None
    )

    numeric_features = [
        "mastery_score",
        "behavior_score",
        "review_due",
        "evaluation_score",
    ]

    categorical_features = [
        "behavior_label",
        "learning_signal",
        "final_action",
        "recommended_strategy",
        "recommended_difficulty",
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
            n_estimators=200,
            random_state=42
        ))
    ])

    model.fit(X_train, y_train)

    val_preds = model.predict(X_val)
    val_acc = accuracy_score(y_val, val_preds)

    joblib.dump(model, MODEL_DIR / "policy_model.joblib")

    metadata = {
        "rows_used": len(df),
        "train_rows": len(X_train),
        "val_rows": len(X_val),
        "features": list(X.columns),
        "target": "next_concept_id",
        "validation_accuracy": round(float(val_acc), 4),
    }

    with open(MODEL_DIR / "policy_model_meta.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"Policy model trained successfully on {len(df)} rows.")
    print(f"Validation accuracy: {val_acc:.4f}")
    print(f"Saved to: {MODEL_DIR / 'policy_model.joblib'}")


if __name__ == "__main__":
    main()