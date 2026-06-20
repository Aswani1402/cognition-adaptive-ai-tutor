from __future__ import annotations

from scripts.final_demo_contract_checks import fail, passed, write_result
from tutor.api.integration_routes import notebook


def main() -> None:
    learner_id = "14"
    data = notebook(learner_id)
    notes = data.get("notes") or data.get("savedNotes") or []
    required = ["summary", "weakPoints", "mistakes", "revisionPlan", "savedFlashcards"]
    errors = [key for key in required if key not in data]
    summary = str(data.get("summary") or "")
    if summary.count("Notebook summary for Variables") > 1:
        errors.append("repeated Variables notebook summary")
    if len(summary.split()) > 180:
        errors.append("summary preview too long")
    result = fail("Notebook page contract failed", {"errors": errors, "keys": sorted(data.keys()), "notes_count": len(notes)}) if errors else passed("Notebook page contract valid", {"keys": sorted(data.keys()), "notes_count": len(notes)})
    write_result("final_notebook_page_contract_report", result)
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
