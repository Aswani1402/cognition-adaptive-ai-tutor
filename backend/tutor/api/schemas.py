from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    name: str | None = None
    username: str | None = None
    email: str | None = None
    password: str = Field(min_length=8, repr=False)
    goal: str | None = None
    learning_goal: str | None = None
    level: str | None = None
    skill_level: str | None = None
    preferred_subject: str | None = None


class LoginRequest(BaseModel):
    email: str | None = None
    username: str | None = None
    password: str = Field(repr=False)


class SaveSessionRequest(BaseModel):
    learner_id: str
    subject: str | None = None
    concept_id: str | None = None
    concept_name: str | None = None
    teaching_view: str | None = None
    difficulty: str | None = None
    active_session_packet: dict[str, Any] = Field(default_factory=dict)


class SelectSubjectRequest(BaseModel):
    learner_id: str
    subject: str


class SubmitAnswerRequest(BaseModel):
    learner_id: str
    concept_id: str | None = None
    concept_name: str | None = None
    domain: str | None = None
    subject: str | None = None
    difficulty: str | None = None
    question_id: str | None = None
    question_type: str = "practice_question"
    answer: Any = ""
    question: dict[str, Any] = Field(default_factory=dict)
    confidence: float | None = 0.5
    time_taken_sec: float | None = 0
    hint_used: bool = False
    hint_count: int = 0
    option_change_count: int = 0
    answer_change_count: int = 0
    run_code_count: int = 0
    attempt_count: int = 1
    wrong_attempt_count: int = 0


class RunCodeRequest(BaseModel):
    learner_id: str | None = None
    language: str = "python"
    code: str
    concept_id: str | None = None
    question_id: str | None = None
    expected_output: str | None = None
    test_cases: list[dict[str, Any]] = Field(default_factory=list)


class AskDoubtRequest(BaseModel):
    learner_id: str
    doubt_text: str
    subject: str | None = None
    concept_id: str | None = None
    concept_name: str | None = None
    domain: str | None = None
    difficulty: str | None = None
    current_teaching_view: str | None = None
    code_context: str | None = None


def api_response(
    *,
    status: str = "success",
    module: str = "TutorAPI",
    fallback_used: bool = False,
    data: dict[str, Any] | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": status,
        "module": module,
        "fallback_used": fallback_used,
    }
    if data:
        for key, value in data.items():
            if key in {"status", "module", "fallback_used"}:
                payload[f"data_{key}"] = value
            else:
                payload[key] = value
    if reason:
        payload["reason"] = reason
    return payload
