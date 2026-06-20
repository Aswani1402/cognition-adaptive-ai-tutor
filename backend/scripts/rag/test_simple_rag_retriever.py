from tutor.rag.simple_rag_retriever import retrieve_context


def main():
    tests = [
        {
            "query": "What is a variable in Python?",
            "domain": "Python",
            "concept_name": "Variables",
        },
        {
            "query": "SQL select query basics",
            "domain": "SQL",
        },
        {
            "query": "Git commit repository",
            "domain": "Git",
        },
        {
            "query": "HTML tags and elements",
            "domain": "HTML",
        },
        {
            "query": "arrays stack queue data structures",
            "domain": "Data Structures",
        },
    ]

    for test in tests:
        print("\n---")
        output = retrieve_context(
            query=test["query"],
            domain=test.get("domain"),
            concept_name=test.get("concept_name"),
            top_k=3,
        )

        print("QUERY:", test["query"])
        print("DOMAIN:", test.get("domain"))
        print("STATUS:", output["status"])
        print("CHUNKS:", output["chunk_count"])

        for chunk in output["chunks"]:
            print(
                f"- score={chunk['score']} | "
                f"{chunk['domain']} | "
                f"{chunk['concept_id']} | "
                f"{chunk['concept_name']} | "
                f"{chunk['section']}"
            )
            print(" ", chunk["text"][:180].replace("\n", " "), "...")


if __name__ == "__main__":
    main()