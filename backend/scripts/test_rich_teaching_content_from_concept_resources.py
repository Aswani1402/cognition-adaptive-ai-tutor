from tutor.api.concept_content_resolver import TEACHING_VIEWS, build_lesson_payload


def main():
    lesson = build_lesson_payload("Python", "P1")
    assert lesson["resource_source"] == "concept_resources"
    assert lesson["concept_id"] == "P1"
    assert "Variables" in lesson["concept_name"]
    for view in TEACHING_VIEWS:
        content = lesson["content_by_view"][view]
        assert len(content["explanation"]) > 80, view
        assert content["key_points"], view
    print("rich teaching content ok")


if __name__ == "__main__":
    main()
