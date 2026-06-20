from __future__ import annotations

import json
from tutor.api.concept_content_resolver import assessment_payload


def main() -> None:
    packet = assessment_payload("Python", "P1", "hard")
    failures = []
    for q in packet["questions"]:
        for field in ["frontend_component", "title", "prompt", "instructions", "task_type", "expected_answer"]:
            if q.get(field) in (None, "", []):
                failures.append(f"{q.get('question_id')} missing {field}")
    print(json.dumps({"status": "pass" if not failures else "fail", "failures": failures}, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
