import json
from pathlib import Path
from collections import defaultdict

from tutor.rag.embedding_rag_retriever import retrieve_context
from tutor.rag.rag_reranker import rerank_chunks


CORPUS_PATH = Path("models/rag/rag_corpus.json")
REPORT_PATH = Path("evaluation_outputs/rag/rag_reranker_all_topics_report.json")


def load_unique_topics():
    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    topics = {}

    for row in corpus:
        domain = row.get("domain")
        concept_id = row.get("concept_id")
        concept_name = row.get("concept_name")

        if not domain or not concept_id or not concept_name:
            continue

        key = (domain, concept_id, concept_name)
        topics[key] = {
            "domain": domain,
            "concept_id": concept_id,
            "concept_name": concept_name,
        }

    return list(topics.values())


def test_topic(topic):
    domain = topic["domain"]
    concept_id = topic["concept_id"]
    concept_name = topic["concept_name"]

    query = f"Explain {concept_name}"

    retrieval = retrieve_context(
        query=query,
        domain=domain,
        top_k=10,
    )

    chunks = retrieval.get("chunks", [])

    reranked = rerank_chunks(
        query=query,
        chunks=chunks,
        top_k=5,
    )

    before_top = chunks[0] if chunks else {}
    after_top = reranked[0] if reranked else {}

    before_match = str(before_top.get("concept_id")) == str(concept_id)
    after_match = str(after_top.get("concept_id")) == str(concept_id)

    return {
        "domain": domain,
        "concept_id": concept_id,
        "concept_name": concept_name,
        "query": query,
        "before_top_concept_id": before_top.get("concept_id"),
        "before_top_concept_name": before_top.get("concept_name"),
        "before_match": before_match,
        "after_top_concept_id": after_top.get("concept_id"),
        "after_top_concept_name": after_top.get("concept_name"),
        "after_match": after_match,
        "after_top_section": after_top.get("section"),
        "after_score": after_top.get("reranker_score"),
    }


def main():
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    topics = load_unique_topics()
    results = []

    for topic in topics:
        result = test_topic(topic)
        results.append(result)

    total = len(results)
    before_correct = sum(1 for r in results if r["before_match"])
    after_correct = sum(1 for r in results if r["after_match"])

    by_domain = defaultdict(lambda: {
        "total": 0,
        "before_correct": 0,
        "after_correct": 0,
    })

    for r in results:
        d = r["domain"]
        by_domain[d]["total"] += 1
        by_domain[d]["before_correct"] += int(r["before_match"])
        by_domain[d]["after_correct"] += int(r["after_match"])

    report = {
        "total_topics": total,
        "before_accuracy": before_correct / total if total else 0,
        "after_accuracy": after_correct / total if total else 0,
        "by_domain": dict(by_domain),
        "results": results,
    }

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\nRAG RERANKER ALL TOPICS TEST")
    print("Total topics:", total)
    print("Before accuracy:", round(report["before_accuracy"], 4))
    print("After accuracy:", round(report["after_accuracy"], 4))
    print("\nBy domain:")

    for domain, stats in sorted(by_domain.items()):
        total_d = stats["total"]
        before_acc = stats["before_correct"] / total_d if total_d else 0
        after_acc = stats["after_correct"] / total_d if total_d else 0

        print(
            f"- {domain}: "
            f"topics={total_d}, "
            f"before={round(before_acc, 4)}, "
            f"after={round(after_acc, 4)}"
        )

    print("\nReport saved:", REPORT_PATH)

    print("\nFailures after rerank:")
    failures = [r for r in results if not r["after_match"]]

    for r in failures[:20]:
        print(
            f"- {r['domain']} | expected {r['concept_name']} ({r['concept_id']}) "
            f"but got {r['after_top_concept_name']} ({r['after_top_concept_id']})"
        )


if __name__ == "__main__":
    main()