from tutor.api.concept_content_resolver import assessment_payload


def main():
    packet = assessment_payload("Python", "P1", "hard")
    types = [q["question_type"] for q in packet["questions"]]
    assert len(packet["questions"]) >= 10
    assert len(set(types)) >= 10
    assert types.count("mcq") >= 2
    assert "fill_in_the_blank" in types
    assert "true_or_false" in types
    assert "output_prediction" in types
    assert "debug_task" in types
    print("assessment multi type sequence ok")


if __name__ == "__main__":
    main()
