from tutor.generation.multi_view_generator import MultiViewGenerator


def main():
    concept_resource = {
        "concept_id": "P3",
        "topic": "Conditionals",
        "base_content": "Conditionals allow a program to make decisions based on whether a condition is true or false.",
        "examples": "Example: if age >= 18: print('Adult') else: print('Minor')",
        "key_points": "Use if for first condition; use elif for additional conditions; use else for default case; conditions return True or False",
        "misconceptions": "Using = instead of ==; forgetting indentation; writing too many nested if statements",
        "real_world_use": "Used in login systems, grading systems, recommendation systems, and game logic.",
        "next_concept_link": "Loops",
    }

    learner_profile = {
        "learner_id": 14,
        "mastery": 0.35,
        "behaviour_label": "struggling",
    }

    generator = MultiViewGenerator()

    output = generator.generate(
        concept_resource=concept_resource,
        learner_profile=learner_profile,
        difficulty="easy",
    )

    print("\nSTATUS:", output["status"])
    print("MODULE:", output["module"])
    print("TOPIC:", output["topic"])
    print("RECOMMENDED VIEW:", output["recommended_view"])
    print("AVAILABLE VIEWS:", output["available_views"])

    print("\n--- SAMPLE VIEW OUTPUT ---")
    recommended = output["recommended_view"]
    print(output["views"][recommended])


if __name__ == "__main__":
    main()