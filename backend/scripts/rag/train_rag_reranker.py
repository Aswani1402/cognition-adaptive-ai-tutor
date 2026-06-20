import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


DATA_PATH = Path("evaluation_outputs/rag/rag_reranker_dataset.csv")
MODEL_DIR = Path("models/rag")
MODEL_PATH = MODEL_DIR / "rag_reranker_model.pkl"
REPORT_PATH = Path("evaluation_outputs/rag/rag_reranker_report.json")


def main():
    df = pd.read_csv(DATA_PATH)

    df = df.dropna(subset=["query", "chunk_text", "label"])

    df["pair_text"] = (
        "Query: " + df["query"].astype(str)
        + "\nChunk: " + df["chunk_text"].astype(str)
    )

    X = df["pair_text"]
    y = df["label"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    model = Pipeline([
        ("tfidf", TfidfVectorizer(
            max_features=20000,
            ngram_range=(1, 2),
            stop_words="english",
        )),
        ("clf", LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
        )),
    ])

    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    probs = model.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, preds)

    report = {
        "dataset_path": str(DATA_PATH),
        "rows_total": int(len(df)),
        "rows_train": int(len(X_train)),
        "rows_test": int(len(X_test)),
        "accuracy": float(acc),
        "classification_report": classification_report(
            y_test,
            preds,
            output_dict=True,
            zero_division=0,
        ),
        "confusion_matrix": confusion_matrix(y_test, preds).tolist(),
        "model_path": str(MODEL_PATH),
    }

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, MODEL_PATH)

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("RAG reranker trained")
    print("Rows:", len(df))
    print("Train:", len(X_train))
    print("Test:", len(X_test))
    print("Accuracy:", round(acc, 4))
    print("Model:", MODEL_PATH)
    print("Report:", REPORT_PATH)


if __name__ == "__main__":
    main()