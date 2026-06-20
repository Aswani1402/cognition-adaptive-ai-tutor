from tutor.api.concept_content_resolver import ASSESSMENT_TYPES, FLASHCARD_TYPES, HINT_TYPES, TEACHING_VIEWS, assessment_payload, build_flashcards, build_hints, build_lesson_payload, build_mindmap


def main():
    lesson = build_lesson_payload("Python", "P1")
    assert set(TEACHING_VIEWS).issubset(set(lesson["available_views"]))
    assessment = assessment_payload("Python", "P1", "hard")
    assert len(assessment["questions"]) >= 10
    assert {"mcq", "debug_task", "output_prediction", "coding_prompt"}.issubset(assessment["coverage"])
    hints = build_hints("Python", "P1")
    assert set(HINT_TYPES).issubset(hints["available_hints"])
    cards = build_flashcards("Python", "P1")
    assert len(cards["flashcards"]) >= len(FLASHCARD_TYPES)
    mindmap = build_mindmap("Python", "P1")
    assert {"concept_mindmap", "comparison_mindmap", "revision_mindmap"}.issubset(mindmap["mindmap_variants"])
    assert ASSESSMENT_TYPES
    print("full task generation coverage ok")


if __name__ == "__main__":
    main()
