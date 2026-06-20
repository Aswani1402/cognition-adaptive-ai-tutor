from tutor.generation.frontend_view_adapter import build_frontend_teaching_view


def main():
    sample_teaching_content = {
        "concept_id": "1",
        "concept_name": "Variables",
        "difficulty": "medium",
        "recommended_view": "definition_view",
        "generated_summary": "Variables help store and reuse values.",
        "generated_flashcards": [
            {"question": "What is a variable?", "answer": "A named reference to a value."}
        ],
        "generated_mindmap": {
            "center": "Variables",
            "branches": [
                {"title": "Meaning", "points": ["Stores reusable data"]},
                {"title": "Syntax", "points": ["name = value"]},
            ],
        },
        "generated_debug_task": {
            "buggy_code": "name = Alice\"\nprint(name)",
            "expected_fix": "name = \"Alice\"\nprint(name)",
            "bug_type": "string_syntax",
        },
        "views": {
            "definition_view": {
                "view_type": "definition_view",
                "title": "What is Variables?",
                "content": "A variable is a name attached to a value.",
                "best_for": "introduction",
            },
            "code_view": {
                "view_type": "code_view",
                "title": "Variables with code",
                "content": "name = \"Alice\" age = 30 print(name) print(age)",
                "best_for": "code practice",
            },
            "debug_view": {
                "view_type": "debug_view",
                "title": "Debug Variables",
                "buggy_case": "name = Alice\"\nprint(name)",
                "task": "Find and fix the syntax mistake.",
                "best_for": "debug practice",
            },
        },
    }

    output = build_frontend_teaching_view(
        teaching_content=sample_teaching_content,
        selected_teaching_view="code_view",
    )

    print("\nSTATUS:", output["status"])
    print("MODULE:", output["module"])
    print("SELECTED:", output["selected_teaching_view"])
    print("DISPLAY TYPE:", output["selected_view"]["display_type"])
    print("CODE BLOCKS:", output["selected_view"].get("code_blocks"))
    print("FLASHCARDS:", output["flashcards"])
    print("MINDMAP CENTER:", output["mindmap"]["center"])
    print("FRONTEND RULE:", output["frontend_rule"])

    assert output["status"] == "success"
    assert output["selected_teaching_view"] == "code_view"
    assert output["selected_view"]["display_type"] == "code"
    assert output["flashcards"]
    assert output["mindmap"]["center"] == "Variables"

    print("\nfrontend view adapter test success")


if __name__ == "__main__":
    main()