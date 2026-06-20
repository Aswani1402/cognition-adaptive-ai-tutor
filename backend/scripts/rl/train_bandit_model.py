import json
import pickle
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder


DATA_PATH = Path("evaluation_outputs/csv/rl_experience_dataset.csv")
MODEL_DIR = Path("models/rl")
MODEL_PATH = MODEL_DIR / "bandit_policy_model.pkl"
ENCODER_PATH = MODEL_DIR / "bandit_label_encoders.pkl"


def build_action_label(row):
    return f"{row['strategy']}_{row['difficulty']}"


def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(DATA_PATH)

    print("Loaded RL dataset")
    print("Rows:", len(df))

    # Keep only useful rows
    df = df.dropna(subset=[
        "mastery_score",
        "behavior_score",
        "review_due",
        "evaluation_score",
        "strategy",
        "difficulty",
        "reward",
    ])

    # Create action label
    df["action_label"] = df.apply(build_action_label, axis=1)

    # For first baseline, keep rows with meaningful reward
    # This trains model to imitate the action taken under state context.
    features = [
        "mastery_score",
        "behavior_score",
        "review_due",
        "evaluation_score",
        "learning_signal",
    ]

    X = df[features].copy()
    y = df["action_label"].copy()

    encoders = {}

    # Encode categorical columns
    for col in ["review_due", "learning_signal"]:
        encoder = LabelEncoder()
        X[col] = encoder.fit_transform(X[col].astype(str))
        encoders[col] = encoder

    y_encoder = LabelEncoder()
    y_encoded = y_encoder.fit_transform(y.astype(str))
    encoders["action_label"] = y_encoder

    if len(set(y_encoded)) < 2:
        raise ValueError("Need at least 2 action classes to train.")

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y_encoded,
        test_size=0.2,
        random_state=42,
        stratify=y_encoded,
    )

    model = RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        class_weight="balanced",
    )

    model.fit(X_train, y_train)

    preds = model.predict(X_test)

    acc = accuracy_score(y_test, preds)

    print("\nBANDIT POLICY MODEL TRAINED")
    print("Accuracy:", round(acc, 4))

    print("\nClassification report:")
    print(
        classification_report(
            y_test,
            preds,
            target_names=y_encoder.classes_,
            zero_division=0,
        )
    )

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)

    with open(ENCODER_PATH, "wb") as f:
        pickle.dump(encoders, f)

    metadata = {
        "dataset_path": str(DATA_PATH),
        "rows_used": len(df),
        "features": features,
        "actions": list(y_encoder.classes_),
        "model_path": str(MODEL_PATH),
        "encoder_path": str(ENCODER_PATH),
        "accuracy": acc,
    }

    metadata_path = MODEL_DIR / "bandit_policy_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print("\nSaved:")
    print("Model:", MODEL_PATH)
    print("Encoders:", ENCODER_PATH)
    print("Metadata:", metadata_path)


if __name__ == "__main__":
    main()