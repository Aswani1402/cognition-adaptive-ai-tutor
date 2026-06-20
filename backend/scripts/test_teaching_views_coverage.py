from __future__ import annotations

from scripts.final_demo_contract_checks import EXPECTED_TEACHING_VIEWS, passed, fail, write_result
from tutor.api.concept_content_resolver import TEACHING_VIEWS, build_lesson_payload


def main() -> None:
    packet = build_lesson_payload("Python", "P1", "easy", "explanation")
    content = packet.get("content_by_view", {})
    errors = []
    if TEACHING_VIEWS != EXPECTED_TEACHING_VIEWS:
        errors.append("TEACHING_VIEWS changed or missing required order")
    missing = [view for view in EXPECTED_TEACHING_VIEWS if view not in content]
    if missing:
        errors.append(f"missing views: {missing}")
    texts = {view: str((content.get(view) or {}).get("explanation") or "") for view in EXPECTED_TEACHING_VIEWS}
    if len(set(texts.values())) < len(EXPECTED_TEACHING_VIEWS):
        errors.append("duplicate teaching view text detected")
    for view, text in texts.items():
        if "Variables" not in text and "variable" not in text.lower():
            errors.append(f"{view} is not concept-specific")
        if len(text.split()) < 8:
            errors.append(f"{view} too short")
    result = fail("Teaching view coverage failed", {"errors": errors, "views": list(content)}) if errors else passed("All 14 teaching views valid", {"views": EXPECTED_TEACHING_VIEWS})
    write_result("final_teaching_views_quality_report", result)
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
