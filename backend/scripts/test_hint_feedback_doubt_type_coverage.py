from tutor.api.concept_content_resolver import DOUBT_TYPES, FEEDBACK_TYPES, HINT_TYPES, build_doubt_answer, build_feedback, build_hints


def main():
    hints = build_hints("Python", "P1", "debug_task", 1)
    assert set(HINT_TYPES).issubset(hints["available_hints"])
    feedback = build_feedback("Python", "P1", False, 0.2, "debug_task")
    assert set(FEEDBACK_TYPES).issubset(feedback["feedback_by_type"])
    doubt = build_doubt_answer("Python", "P1", "Why does this output happen?")
    assert set(DOUBT_TYPES).issubset(set(doubt["available_doubt_types"]))
    assert doubt["answer"]
    print("hint feedback doubt coverage ok")


if __name__ == "__main__":
    main()
