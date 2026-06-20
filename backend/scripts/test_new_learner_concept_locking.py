from __future__ import annotations

import time

from scripts.final_demo_contract_checks import fail, passed, write_result
from tutor.api.concept_content_resolver import assessment_payload
from tutor.api.evaluation_routes import submit_answer
from tutor.api.integration_routes import subject_path
from tutor.api.learner_routes import select_subject
from tutor.api.schemas import SelectSubjectRequest, SubmitAnswerRequest


def _path(learner_id: str):
    response = subject_path(learner_id, "python")
    return response.get("path") or response.get("nodes") or []


def _data_types_node(nodes):
    return next((n for n in nodes if "data" in str(n.get("name", "")).lower() or str(n.get("id")) == "P2"), {})


def _submit_pass(learner_id: str, difficulty: str):
    packet = assessment_payload("Python", "P1", difficulty)
    mcq = next(q for q in packet["questions"] if q["task_type"] == "mcq")
    submit_answer(SubmitAnswerRequest(
        learner_id=learner_id,
        concept_id="P1",
        concept_name="Variables",
        subject="Python",
        difficulty=difficulty,
        question_id=mcq["question_id"],
        question_type="mcq",
        answer=mcq["correct_answer"],
        question=mcq,
        confidence=0.9,
        time_taken_sec=12,
    ))


def main() -> None:
    learner_id = f"final_demo_lock_{int(time.time())}"
    select_subject(SelectSubjectRequest(learner_id=learner_id, subject="Python"))
    errors = []
    nodes = _path(learner_id)
    if not nodes or nodes[0].get("status") != "current" or "variable" not in str(nodes[0].get("name", "")).lower():
        errors.append("fresh learner does not start at Variables/current")
    if _data_types_node(nodes).get("status") != "locked":
        errors.append("Data Types is not locked for fresh learner")
    _submit_pass(learner_id, "easy")
    nodes = _path(learner_id)
    if _data_types_node(nodes).get("status") != "locked":
        errors.append("Data Types unlocked after easy only")
    _submit_pass(learner_id, "medium")
    nodes = _path(learner_id)
    if _data_types_node(nodes).get("status") != "locked":
        errors.append("Data Types unlocked after medium only")
    _submit_pass(learner_id, "hard")
    nodes = _path(learner_id)
    if _data_types_node(nodes).get("status") not in {"current", "unlocked"}:
        errors.append("Data Types did not unlock after hard pass")
    result = fail("New learner locking failed", {"errors": errors, "final_path": nodes}) if errors else passed("New learner locking valid", {"final_path": nodes})
    write_result("final_learning_path_locking_report", result)
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
