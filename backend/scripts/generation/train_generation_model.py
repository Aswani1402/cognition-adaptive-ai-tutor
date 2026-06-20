import json
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import joblib


DATA_PATH = Path("evaluation_outputs/generation_dataset.jsonl")
MODEL_PATH = Path("models/generation/generation_model.pkl")
ENCODER_PATH = Path("models/generation/label_encoders.pkl")


def load_data():
    rows = []
    with open(DATA_PATH) as f:
        for line in f:
            rows.append(json.loads(line))
    return pd.DataFrame(rows)


def main():
    df = load_data()

    X = df[[
        "mastery",
        "behavior",
        "time_taken",
        "confidence",
        "hint_used"
    ]]

    df["target"] = (
        df["strategy"] + "_" + df["content_type"] + "_" + df["difficulty"]
    )

    le = LabelEncoder()
    y = le.fit_transform(df["target"])

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

    model = RandomForestClassifier(n_estimators=100)
    model.fit(X_train, y_train)

    acc = model.score(X_test, y_test)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, MODEL_PATH)
    joblib.dump(le, ENCODER_PATH)

    print("Model trained")
    print("Accuracy:", acc)
    print("Saved to:", MODEL_PATH)


if __name__ == "__main__":
    main()