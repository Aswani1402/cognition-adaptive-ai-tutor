from tutor.experience.lesson_orchestrator import LessonOrchestrator


def main():
    concept_resource = {
        "system_concept_id": "1",
        "concept_name": "Variables",
        "definition": "A variable stores a value.",
        "examples": ["x = 10\nprint(x)"],
        "key_points": [
            "Variables store values",
            "They can change",
        ],
        "misconceptions": [
            "Variables store values directly"
        ],
    }

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

    print(output)


if __name__ == "__main__":
    main()