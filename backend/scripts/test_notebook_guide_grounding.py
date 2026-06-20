from __future__ import annotations

import json
from tutor.api.integration_routes import notebook_guide_ask


def main() -> None:
    res = notebook_guide_ask({"learner_id": "14", "subject": "Python", "concept_id": "P1", "question": "What should I revise for Variables?"})
    data = res.get("data", res)
    answer = str(data.get("answer") or "")
    ok = "Variables" in answer and data.get("sources_used") and "concept_resources" in " ".join(data.get("sources_used", []))
    print(json.dumps({"status": "pass" if ok else "fail", "sources_used": data.get("sources_used"), "learner_memory_used": data.get("learner_memory_used")}, indent=2))
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
