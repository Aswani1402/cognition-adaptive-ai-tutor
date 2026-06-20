from pprint import pprint

from tutor.generation.adaptive_content_generator import generate_content_bundle

concept_resource = {
    "concept_id": "P1",
    "concept_name": "Variables",
    "definition": "A variable is a named storage location used to hold data.",
    "key_points": [
        "Variables store values.",
        "Variable names should be meaningful.",
        "Variables can be updated during execution."
    ],
    "examples": [
        "x = 5\ny = x + 2\nprint(y)",
        "name = 'Aswini'\nprint(name)"
    ],
    "misconceptions": [
        "Variables do not need assignment.",
        "A variable name can be anything without rules.",
        "Variables never change after creation."
    ],
    "real_world_use": "Variables can store marks, usernames, prices, and sensor values in real programs.",
    "syntax": "x = 10"
}

result = generate_content_bundle(
    concept_resource=concept_resource,
    learner_id="14",
    difficulty="easy",
    requested_plan=[
        {"content_type": "teaching", "strategy": "definition_first"},
        {"content_type": "teaching", "strategy": "example_first"},
        {"content_type": "revision", "strategy": "revision_summary"},
        {"content_type": "flashcard", "strategy": "revision_summary"},
        {"content_type": "common_mistakes", "strategy": "misconception_first"},
    ]
)

pprint(result)