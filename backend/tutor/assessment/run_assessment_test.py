from __future__ import annotations

import json
from tutor.assessment.dynamic_assessment_generator import generate_assessment_bundle


def run_test():
    result = generate_assessment_bundle(
        system_concept_id="1",
        concept_name="Variables",
        domain="Python",
        difficulty="easy",
        teaching_text="A variable stores a value and can be updated."
    )

    print("\n=== ASSESSMENT OUTPUT ===\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    run_test()