from tutor.api.concept_content_resolver import assessment_payload, build_lesson_payload


def main():
    py = build_lesson_payload("Python", "P1")
    sql = build_lesson_payload("SQL / Database", "S1")
    assert py["subject"] == "Python"
    assert sql["subject"] == "SQL / Database"
    assert "Variables" in py["concept_name"]
    assert "Variables" not in sql["concept_name"]
    sql_assessment = assessment_payload("SQL / Database", "S1")
    assert all(q["subject"] == "SQL / Database" for q in sql_assessment["questions"])
    print("subject context flow ok")


if __name__ == "__main__":
    main()
