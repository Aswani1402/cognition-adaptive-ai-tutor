from __future__ import annotations

import json
from tutor.api.integration_routes import notebook, notebook_save


def main() -> None:
    learner_id = "14"
    payload = {
        "learner_id": learner_id,
        "subject": "Python",
        "concept_id": "P1",
        "concept_name": "Variables",
        "note_type": "test_note",
        "title": "Variables save flow test",
        "content": "Variables save flow test content grounded in Python Variables.",
        "source_page": "test_notebook_save_flow",
    }
    first = notebook_save(payload)
    second = notebook_save(payload)
    fetched = notebook(learner_id)
    data = fetched.get("data", fetched)
    ok = bool(first.get("saved")) and bool(second.get("already_saved")) and bool(data.get("savedNotes") or data.get("notes"))
    print(json.dumps({"status": "pass" if ok else "fail", "first": first, "second": second, "note_count": len(data.get("savedNotes") or [])}, indent=2))
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
