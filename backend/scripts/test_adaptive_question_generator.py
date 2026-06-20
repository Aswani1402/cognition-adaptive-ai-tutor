from pprint import pprint

from tutor.assessment.adaptive_question_generator import generate_assessment_bundle

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

result = generate_assessment_bundle(
    concept_resource=concept_resource,
    learner_id="14",
    difficulty="easy",
    requested_types=["mcq", "output_prediction", "debug", "short_explanation", "transfer"]
)

pprint(result)