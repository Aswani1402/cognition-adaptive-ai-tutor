from tutor.rag.rag_context_builder import build_rag_concept_resource
from tutor.experience.lesson_orchestrator import LessonOrchestrator


DEMO_CASES = [
    {
        "domain": "Python",
        "query": "What is a variable in Python?",
        "learner_id": "demo_python",
    },
    {
        "domain": "SQL",
        "query": "How do SELECT statements work in SQL?",
        "learner_id": "demo_sql",
    },
    {
        "domain": "HTML",
        "query": "What are HTML tags and elements?",
        "learner_id": "demo_html",
    },
    {
        "domain": "Git",
        "query": "How do Git commits work?",
        "learner_id": "demo_git",
    },
    {
        "domain": "Data Structures",
        "query": "What are arrays in data structures?",
        "learner_id": "demo_dsa",
    },
]


def run_case(case):
    concept_resource = build_rag_concept_resource(
        query=case["query"],
        domain=case["domain"],
        top_k=8,
    )

    orchestrator = LessonOrchestrator()

    output = orchestrator.run(
        concept_resource=concept_resource,
        learner_id=case["learner_id"],
        context={
            "mastery_score": 0.4,
            "behavior_score": 0.6,
            "time_taken": 30,
            "confidence": 1,
            "hint_used": 1,
        },
    )

    pack = output["lesson_pack"]

    return {
        "domain": case["domain"],
        "query": case["query"],
        "concept_id": pack.get("concept_id"),
        "concept_name": pack.get("concept_name"),
        "difficulty": pack.get("difficulty"),
        "teaching_count": len(pack.get("teaching_items", [])),
        "flashcard_count": len(pack.get("flashcards", [])),
        "assessment_count": len(pack.get("assessment_items", [])),
        "xp": pack.get("engagement", {}).get("xp_reward"),
        "voice_preview": pack.get("voice_script", {}).get("script", "")[:120],
        "status": output.get("status"),
        "progression": pack.get("progression"),
        "xp_streak": pack.get("xp_streak"),
    }


def main():
    print("\nMULTI-SUBJECT DEMO REPORT")

    rows = []

    for case in DEMO_CASES:
        try:
            row = run_case(case)
            rows.append(row)
        except Exception as e:
            rows.append({
                "domain": case["domain"],
                "query": case["query"],
                "status": "error",
                "error": str(e),
            })

    for row in rows:
        print("\n---")
        print("Domain:", row.get("domain"))
        print("Status:", row.get("status"))
        print("Concept:", row.get("concept_name"), "|", row.get("concept_id"))
        print("Difficulty:", row.get("difficulty"))
        print("Teaching:", row.get("teaching_count"))
        print("Flashcards:", row.get("flashcard_count"))
        print("Assessment:", row.get("assessment_count"))
        print("XP:", row.get("xp"))
        print("Voice:", row.get("voice_preview"), "...")
        print("Progression:", row.get("progression"))
        print("XP/Streak:", row.get("xp_streak"))
        if row.get("error"):
            print("Error:", row.get("error"))


if __name__ == "__main__":
    main()