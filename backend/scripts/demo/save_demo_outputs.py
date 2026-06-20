import json
from datetime import datetime
from pathlib import Path

from tutor.rag.rag_context_builder import build_rag_concept_resource
from tutor.experience.lesson_orchestrator import LessonOrchestrator


OUTPUT_DIR = Path("evaluation_outputs/demo")


DEMO_CASES = [
    ("Python", "What is a variable in Python?", "demo_python"),
    ("SQL", "How do SELECT statements work in SQL?", "demo_sql"),
    ("HTML", "What are HTML tags and elements?", "demo_html"),
    ("Git", "How do Git commits work?", "demo_git"),
    ("Data Structures", "What are arrays in data structures?", "demo_dsa"),
]


def run_demo(domain, query, learner_id):
    concept_resource = build_rag_concept_resource(
        query=query,
        domain=domain,
        top_k=8,
    )

    orchestrator = LessonOrchestrator()

    return orchestrator.run(
        concept_resource=concept_resource,
        learner_id=learner_id,
        context={
            "mastery_score": 0.4,
            "behavior_score": 0.6,
            "time_taken": 30,
            "confidence": 1,
            "hint_used": 1,
        },
    )


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    all_outputs = []

    for domain, query, learner_id in DEMO_CASES:
        output = run_demo(domain, query, learner_id)

        filename = f"{domain.lower().replace(' ', '_')}_demo_{timestamp}.json"
        path = OUTPUT_DIR / filename

        with open(path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        pack = output.get("lesson_pack", {})

        summary = {
            "domain": domain,
            "query": query,
            "concept_id": pack.get("concept_id"),
            "concept_name": pack.get("concept_name"),
            "teaching_count": len(pack.get("teaching_items", [])),
            "flashcard_count": len(pack.get("flashcards", [])),
            "assessment_count": len(pack.get("assessment_items", [])),
            "xp": pack.get("engagement", {}).get("xp_reward"),
            "file": str(path),
        }

        all_outputs.append(summary)
        print("Saved:", path)

    summary_path = OUTPUT_DIR / f"demo_summary_{timestamp}.json"

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(all_outputs, f, indent=2, ensure_ascii=False)

    print("\nDemo outputs saved.")
    print("Summary:", summary_path)


if __name__ == "__main__":
    main()