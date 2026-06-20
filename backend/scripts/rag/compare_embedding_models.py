from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np

from tutor.rag.embedding_rag_retriever import _safe_import_sentence_transformer
from tutor.rag.simple_rag_retriever import CORPUS_PATH


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = PROJECT_ROOT / "evaluation_outputs" / "rag" / "embedding_model_comparison.json"
TOP_K = 3
MODELS = [
    "sentence-transformers/all-MiniLM-L6-v2",
    "sentence-transformers/multi-qa-MiniLM-L6-cos-v1",
    "BAAI/bge-small-en-v1.5",
    "intfloat/e5-small-v2",
    "sentence-transformers/all-mpnet-base-v2",
]
TESTS = [
    {
        "query": "What is a variable in Python?",
        "domain": "Python",
        "expected_concepts": ["Variables"],
    },
    {
        "query": "How do select statements work in SQL tables?",
        "domain": "SQL",
        "expected_concepts": ["SQL SELECT Queries"],
    },
    {
        "query": "HTML tags and page elements",
        "domain": "HTML",
        "expected_concepts": ["HTML Tags & Elements"],
    },
    {
        "query": "How do I commit changes in Git?",
        "domain": "Git",
        "expected_concepts": ["Commits & History"],
    },
    {
        "query": "What are arrays stacks and queues in data structures?",
        "domain": "Data Structures",
        "expected_concepts": ["Arrays", "Stacks", "Queues"],
    },
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_corpus(corpus_path: Path) -> list[dict[str, Any]]:
    with corpus_path.open("r", encoding="utf-8") as handle:
        corpus = json.load(handle)
    if not isinstance(corpus, list):
        raise ValueError(f"Invalid RAG corpus format at {corpus_path}")
    return corpus


def _compose_chunk_text(chunk: dict[str, Any], model_name: str) -> str:
    base_text = " | ".join(
        part
        for part in [
            str(chunk.get("domain", "")).strip(),
            str(chunk.get("concept_name", "")).strip(),
            str(chunk.get("section", "")).strip(),
            str(chunk.get("text", "")).strip(),
        ]
        if part
    )
    if model_name.startswith("intfloat/e5-"):
        return f"passage: {base_text}"
    return base_text


def _build_corpus_embeddings(
    encoder: Any,
    corpus: list[dict[str, Any]],
    model_name: str,
) -> np.ndarray:
    texts = [_compose_chunk_text(chunk, model_name) for chunk in corpus]
    embeddings = encoder.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return np.asarray(embeddings, dtype=np.float32)


def _encode_query(encoder: Any, query: str, model_name: str) -> np.ndarray:
    text = str(query)
    if model_name.startswith("intfloat/e5-"):
        text = f"query: {text}"
    vector = encoder.encode(
        [text],
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )[0]
    return np.asarray(vector, dtype=np.float32)


def _candidate_indexes(
    corpus: list[dict[str, Any]],
    *,
    domain: str | None = None,
) -> list[int]:
    if not domain:
        return list(range(len(corpus)))
    return [
        index
        for index, chunk in enumerate(corpus)
        if str(chunk.get("domain", "")).lower() == str(domain).lower()
    ]


def _rank_chunks(
    corpus: list[dict[str, Any]],
    corpus_embeddings: np.ndarray,
    query_vector: np.ndarray,
    candidate_indexes: list[int],
    *,
    top_k: int = TOP_K,
) -> list[dict[str, Any]]:
    if not candidate_indexes:
        return []

    candidate_matrix = corpus_embeddings[candidate_indexes]
    scores = candidate_matrix @ query_vector
    ranked_positions = np.argsort(scores)[::-1][:top_k]

    results: list[dict[str, Any]] = []
    for rank, position in enumerate(ranked_positions, start=1):
        corpus_index = candidate_indexes[int(position)]
        chunk = dict(corpus[corpus_index])
        chunk["rank"] = rank
        chunk["corpus_index"] = corpus_index
        chunk["score"] = round(float(scores[int(position)]), 4)
        chunk["text_preview"] = str(chunk.get("text", "")).replace("\n", " ")[:180]
        results.append(chunk)
    return results


def _expected_concept_match(
    chunks: list[dict[str, Any]],
    expected_concepts: list[str],
) -> bool:
    expected = {item.lower() for item in expected_concepts}
    found = {str(chunk.get("concept_name", "")).lower() for chunk in chunks}
    return not expected.isdisjoint(found)


def _expected_domain_match(
    chunks: list[dict[str, Any]],
    expected_domain: str | None,
) -> bool:
    if not expected_domain:
        return True
    expected = str(expected_domain).lower()
    return any(str(chunk.get("domain", "")).lower() == expected for chunk in chunks)


def compare_models() -> dict[str, Any]:
    corpus = _load_corpus(CORPUS_PATH)
    SentenceTransformer, import_error = _safe_import_sentence_transformer()

    report: dict[str, Any] = {
        "status": "success",
        "built_at": _utc_now_iso(),
        "corpus_path": str(CORPUS_PATH),
        "report_path": str(REPORT_PATH),
        "top_k": TOP_K,
        "tests": TESTS,
        "models": [],
    }

    if SentenceTransformer is None:
        report["status"] = "error"
        report["reason"] = import_error or "sentence-transformers import failed"
        return report

    for model_name in MODELS:
        model_result: dict[str, Any] = {
            "model_name": model_name,
            "status": "success",
            "queries": [],
        }

        try:
            load_start = perf_counter()
            encoder = SentenceTransformer(model_name)
            model_result["load_time_seconds"] = round(perf_counter() - load_start, 4)

            build_start = perf_counter()
            corpus_embeddings = _build_corpus_embeddings(encoder, corpus, model_name)
            model_result["embedding_build_time_seconds"] = round(perf_counter() - build_start, 4)
        except Exception as exc:
            model_result["status"] = "error"
            model_result["reason"] = str(exc)
            report["models"].append(model_result)
            continue

        concept_matches = 0
        domain_matches = 0
        total_search_time_seconds = 0.0

        for test in TESTS:
            indexes = _candidate_indexes(corpus, domain=test.get("domain"))
            search_start = perf_counter()
            query_vector = _encode_query(encoder, test["query"], model_name)
            top_chunks = _rank_chunks(
                corpus,
                corpus_embeddings,
                query_vector,
                indexes,
                top_k=TOP_K,
            )
            search_time_seconds = round(perf_counter() - search_start, 4)
            total_search_time_seconds += search_time_seconds

            concept_match = _expected_concept_match(top_chunks, test["expected_concepts"])
            domain_match = _expected_domain_match(top_chunks, test.get("domain"))

            if concept_match:
                concept_matches += 1
            if domain_match:
                domain_matches += 1

            model_result["queries"].append(
                {
                    "query": test["query"],
                    "domain": test.get("domain"),
                    "expected_concepts": test["expected_concepts"],
                    "candidate_count": len(indexes),
                    "search_time_seconds": search_time_seconds,
                    "expected_concept_match": concept_match,
                    "expected_domain_match": domain_match,
                    "top_chunks": [
                        {
                            "rank": chunk["rank"],
                            "score": chunk["score"],
                            "domain": chunk.get("domain"),
                            "concept_id": chunk.get("concept_id"),
                            "concept_name": chunk.get("concept_name"),
                            "section": chunk.get("section"),
                            "text_preview": chunk["text_preview"],
                        }
                        for chunk in top_chunks
                    ],
                }
            )

        model_result["concept_matched_queries"] = concept_matches
        model_result["domain_matched_queries"] = domain_matches
        model_result["total_queries"] = len(TESTS)
        model_result["total_search_time_seconds"] = round(total_search_time_seconds, 4)
        model_result["average_search_time_seconds"] = round(total_search_time_seconds / len(TESTS), 4)
        report["models"].append(model_result)

    return report


def _write_report(report: dict[str, Any], report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)


def _print_report(report: dict[str, Any]) -> None:
    print("EMBEDDING MODEL COMPARISON")
    print("status:", report.get("status"))
    if report.get("reason"):
        print("reason:", report["reason"])

    for model in report.get("models", []):
        print("\n===")
        print("model:", model.get("model_name"))
        print("status:", model.get("status"))
        if model.get("reason"):
            print("reason:", model["reason"])
            continue
        print("load_time_seconds:", model.get("load_time_seconds"))
        print("embedding_build_time_seconds:", model.get("embedding_build_time_seconds"))
        print("concept_matched_queries:", f"{model.get('concept_matched_queries', 0)}/{model.get('total_queries', 0)}")
        print("domain_matched_queries:", f"{model.get('domain_matched_queries', 0)}/{model.get('total_queries', 0)}")
        print("average_search_time_seconds:", model.get("average_search_time_seconds"))

        for query_result in model.get("queries", []):
            print("\n---")
            print("query:", query_result.get("query"))
            print("domain:", query_result.get("domain"))
            print("expected_concepts:", ", ".join(query_result.get("expected_concepts", [])))
            print("search_time_seconds:", query_result.get("search_time_seconds"))
            print("expected_concept_match:", query_result.get("expected_concept_match"))
            print("expected_domain_match:", query_result.get("expected_domain_match"))
            for chunk in query_result.get("top_chunks", []):
                print(
                    f"{chunk.get('rank')}. "
                    f"score={chunk.get('score')} | "
                    f"{chunk.get('domain')} | "
                    f"{chunk.get('concept_id')} | "
                    f"{chunk.get('concept_name')} | "
                    f"{chunk.get('section')}"
                )
                print(" ", chunk.get("text_preview", ""), "...")

    print("\nreport_path:", report.get("report_path"))


def main() -> None:
    report = compare_models()
    _write_report(report, REPORT_PATH)
    _print_report(report)


if __name__ == "__main__":
    main()
