from tutor.rag.rag_context_builder import build_rag_concept_resource
from tutor.experience.lesson_orchestrator import LessonOrchestrator


def run_demo(query, domain, learner_id):
    concept_resource = build_rag_concept_resource(
        query=query,
        domain=domain,
        top_k=8,
    )

    orchestrator = LessonOrchestrator()

    output = orchestrator.run(
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

    pack = output["lesson_pack"]

    print("\n=== DEMO ===")
    print("Concept:", pack["concept_name"])
    print("Teaching:", len(pack["teaching_items"]))
    print("Flashcards:", len(pack["flashcards"]))
    print("Assessment:", len(pack["assessment_items"]))
    print("XP:", pack["gamification"]["xp"])
    print("Voice:", pack["voice_script"]["script"][:150], "...")


if __name__ == "__main__":
    run_demo("What is a variable in Python?", "Python", "demo_user_1")