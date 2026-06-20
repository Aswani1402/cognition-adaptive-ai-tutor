from tutor.rag.embedding_rag_retriever import retrieve_context
from tutor.rag.rag_reranker import rerank_chunks


TESTS = [
    ("Python", "What is a variable in Python?"),
    ("SQL", "How do SELECT statements work in SQL?"),
    ("HTML", "What are HTML tags and elements?"),
    ("Git", "How do Git commits work?"),
    ("Data Structures", "What are arrays stacks and queues?"),
]


def run_test(domain, query):
    retrieval = retrieve_context(
        query=query,
        domain=domain,
        top_k=8,
    )

    chunks = retrieval.get("chunks", [])

    reranked = rerank_chunks(
        query=query,
        chunks=chunks,
        top_k=5,
    )

    print("\n---")
    print("DOMAIN:", domain)
    print("QUERY:", query)

    print("\nTOP BEFORE:")
    for c in chunks[:3]:
        print(c.get("score"), "|", c.get("concept_name"), "|", c.get("section"))

    print("\nTOP AFTER:")
    for c in reranked[:3]:
        print(c.get("reranker_score"), "|", c.get("concept_name"), "|", c.get("section"))


def main():
    for domain, query in TESTS:
        run_test(domain, query)


if __name__ == "__main__":
    main()