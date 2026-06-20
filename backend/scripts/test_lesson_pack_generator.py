from tutor.experience.lesson_pack_generator import generate_lesson_pack


def main():
    concept_resource = {
        "system_concept_id": "1",
        "concept_name": "Variables",
        "definition": "A variable stores a value and can be reused or updated during program execution.",
        "examples": [
            "x = 10\ny = x + 5\nprint(y)",
            "name = 'Alice'\nprint(name)",
        ],
        "key_points": [
            "A variable is a name bound to an object in memory.",
            "Python variables are dynamically typed.",
            "Variable names are case-sensitive.",
        ],
        "misconceptions": [
            "Variables do not store values directly; they reference objects."
        ],
    }

    pack = generate_lesson_pack(
        concept_resource=concept_resource,
        generated_content={"items": []},
        assessment_output={"questions": []},
        learner_id="14",
        difficulty="easy",
    )

    print(pack)


if __name__ == "__main__":
    main()