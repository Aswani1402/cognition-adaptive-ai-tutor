from __future__ import annotations

from tutor.rag.rag_grounding_checker import check_rag_grounding


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _python_variables_context() -> dict:
    return {
        "status": "success",
        "content_concept_id": "1",
        "topic": "Variables",
        "domain": "Python",
        "definition": "A variable in Python is a named reference used to store a value for later use.",
        "examples": [
            "Example: name = 'Alice' stores the text Alice in the variable name.",
            "Example: total = price * quantity stores a calculated value.",
        ],
        "key_points": [
            "Variables make values reusable.",
            "A clear variable name helps code readability.",
        ],
        "misconceptions": [
            "A variable is not a fixed box; it is a name that can refer to a new value after reassignment.",
        ],
        "real_world_use": "Variables can store prices, names, quantities, and totals in real programs.",
        "retrieved_chunks": [
            {
                "content_concept_id": "1",
                "topic": "Variables",
                "domain": "Python",
                "section": "definition",
                "content": "Python variables store values using names such as count, total, or name.",
            }
        ],
    }


def main() -> None:
    grounded = check_rag_grounding(
        generated_text="A Python variable is a named reference that stores a value for later use.",
        rag_context=_python_variables_context(),
        concept_id="1",
        concept_name="Variables",
        domain="Python",
    )
    _assert(grounded["safe_to_generate"], f"grounded content not safe: {grounded}")
    _assert(grounded["risk_level"] == "low", f"grounded content not low risk: {grounded}")

    no_context = check_rag_grounding(
        generated_text="A variable stores a value.",
        rag_context=None,
        concept_id="1",
        concept_name="Variables",
        domain="Python",
    )
    _assert(not no_context["safe_to_generate"], f"no context marked safe: {no_context}")
    _assert(no_context["risk_level"] == "high", f"no context not high risk: {no_context}")
    _assert(no_context["fallback_recommended"], f"no context did not recommend fallback: {no_context}")

    wrong_context = check_rag_grounding(
        generated_text="A Python variable stores a value for later use.",
        rag_context={
            "content_concept_id": "9",
            "topic": "Primary Keys",
            "domain": "SQL",
            "definition": "A primary key uniquely identifies a row in a relational database table.",
        },
        concept_id="1",
        concept_name="Variables",
        domain="Python",
    )
    _assert(not wrong_context["safe_to_generate"], f"wrong context marked safe: {wrong_context}")
    _assert(wrong_context["fallback_recommended"], f"wrong context no fallback: {wrong_context}")
    _assert(wrong_context["grounding_score"] < grounded["grounding_score"], "wrong context did not lower score")

    hallucinated = check_rag_grounding(
        generated_text=(
            "A Python variable stores values and automatically creates quantum_encryption "
            "for distributed blockchain synchronization."
        ),
        rag_context=_python_variables_context(),
        concept_id="1",
        concept_name="Variables",
        domain="Python",
    )
    _assert(hallucinated["risk_level"] != "low", f"hallucinated content low risk: {hallucinated}")
    _assert(hallucinated["unsupported_terms"], f"unsupported terms not detected: {hallucinated}")

    misconception = check_rag_grounding(
        generated_text="A variable is not a fixed box because it can refer to a new value after reassignment.",
        rag_context=_python_variables_context(),
        concept_id="1",
        concept_name="Variables",
        domain="Python",
    )
    _assert(misconception["section_match"], f"misconception section did not match: {misconception}")
    _assert("misconceptions" in misconception["evidence_sections"], f"misconception evidence missing: {misconception}")

    examples = check_rag_grounding(
        generated_text="For example, total = price * quantity stores a calculated value in a variable.",
        rag_context=_python_variables_context(),
        concept_id="1",
        concept_name="Variables",
        domain="Python",
    )
    _assert(examples["section_match"], f"examples section did not match: {examples}")
    _assert("examples" in examples["evidence_sections"], f"examples evidence missing: {examples}")

    print("grounded_content:", grounded["risk_level"], grounded["safe_to_generate"], grounded["grounding_score"])
    print("no_context:", no_context["risk_level"], no_context["safe_to_generate"])
    print("wrong_context:", wrong_context["risk_level"], wrong_context["fallback_recommended"], wrong_context["grounding_score"])
    print("hallucinated:", hallucinated["risk_level"], hallucinated["unsupported_terms"])
    print("misconception_section:", misconception["section_match"], misconception["evidence_sections"])
    print("examples_section:", examples["section_match"], examples["evidence_sections"])
    print("STATUS: success")
    print("MODULE: rag_grounding_checker_test")


if __name__ == "__main__":
    main()
