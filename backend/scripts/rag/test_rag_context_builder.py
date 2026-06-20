from tutor.experience.lesson_orchestrator import LessonOrchestrator
from tutor.rag.rag_context_builder import build_rag_concept_resource


def main():
    concept_resource = build_rag_concept_resource(
        query="What is a variable in Python?",
        domain="Python",
        concept_name="Variables",
        top_k=8,
    )

    print("\nRAG CONCEPT RESOURCE")
    print("status:", concept_resource.get("status"))
    print("concept_id:", concept_resource.get("concept_id"))
    print("concept_name:", concept_resource.get("concept_name"))
    print("domain:", concept_resource.get("domain"))
    print("chunk_count:", concept_resource.get("chunk_count"))

    orchestrator = LessonOrchestrator()

    output = orchestrator.run(
        concept_resource=concept_resource,
        learner_id="14",
        context={
            "mastery_score": 0.3,
            "behavior_score": 0.7,
            "time_taken": 30,
            "confidence": 1,
            "hint_used": 1,
        },
    )

    pack = output["lesson_pack"]

    print("\nLESSON PACK")
    print("concept_id:", pack["concept_id"])
    print("concept_name:", pack["concept_name"])
    print("difficulty:", pack["difficulty"])
    print("teaching_items:", len(pack["teaching_items"]))
    print("flashcards:", len(pack["flashcards"]))
    print("assessment_items:", len(pack["assessment_items"]))
    print("variation_memory:", pack.get("variation_memory"))
    print("voice_script:", pack["voice_script"]["script"][:200], "...")


if __name__ == "__main__":
    main()