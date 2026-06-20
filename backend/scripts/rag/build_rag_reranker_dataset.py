import csv
import json
import random
from pathlib import Path


CORPUS_PATH = Path("models/rag/rag_corpus.json")
OUTPUT_DIR = Path("evaluation_outputs/rag")
OUTPUT_PATH = OUTPUT_DIR / "rag_reranker_dataset.csv"


QUERY_TEMPLATES = [
    "What is {concept_name}?",
    "Explain {concept_name}",
    "Teach me {concept_name}",
    "{concept_name} basics",
    "How does {concept_name} work?",
    "Give example of {concept_name}",
]


def load_corpus():
    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    corpus = load_corpus()
    rows = []

    for chunk in corpus:
        concept_name = chunk.get("concept_name", "")
        domain = chunk.get("domain", "")
        concept_id = chunk.get("concept_id", "")
        text = chunk.get("text", "")

        if not concept_name or not text:
            continue

        # Positive pairs
        for template in QUERY_TEMPLATES[:3]:
            rows.append({
                "query": template.format(concept_name=concept_name),
                "chunk_text": text,
                "domain": domain,
                "concept_id": concept_id,
                "concept_name": concept_name,
                "label": 1,
            })

        # Negative pairs from different concepts
        negatives = [
            c for c in corpus
            if c.get("concept_name") != concept_name and c.get("text")
        ]

        for neg in random.sample(negatives, min(3, len(negatives))):
            rows.append({
                "query": random.choice(QUERY_TEMPLATES).format(concept_name=concept_name),
                "chunk_text": neg.get("text", ""),
                "domain": domain,
                "concept_id": concept_id,
                "concept_name": concept_name,
                "label": 0,
            })

    random.shuffle(rows)

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "query",
                "chunk_text",
                "domain",
                "concept_id",
                "concept_name",
                "label",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print("RAG reranker dataset created")
    print("Rows:", len(rows))
    print("Path:", OUTPUT_PATH)


if __name__ == "__main__":
    main()