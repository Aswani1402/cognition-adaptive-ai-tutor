from __future__ import annotations

from tutor.simulation.learner_answer_simulator import (
    PROFILE_PARAMETERS,
    LearnerAnswerSimulator,
)


SAMPLE_QUESTIONS = [
    {
        "question_id": "q1",
        "question_type": "mcq",
        "concept_name": "Variables",
        "prompt": "Which is a valid Python variable name?",
        "options": ["2score", "total_score", "my-var", "class"],
        "correct_option_index": 1,
        "expected_answer": "total_score",
        "key_points": ["Variable names should be valid identifiers."],
    },
    {
        "question_id": "q2",
        "question_type": "output_prediction",
        "concept_name": "Variables",
        "prompt": "What prints after score = 10; score = 15; print(score)?",
        "expected_answer": "15",
    },
    {
        "question_id": "q3",
        "question_type": "debug_task",
        "concept_name": "Strings",
        "prompt": "Find the bug in name = Alice",
        "expected_answer": "Add quotes around Alice.",
    },
    {
        "question_id": "q4",
        "question_type": "explanation_check",
        "concept_name": "Variables",
        "prompt": "Explain variables.",
        "expected_answer": "A variable is a name linked to a value.",
        "key_points": ["A variable is a name linked to a value.", "It can be reused later."],
    },
    {
        "question_id": "q5",
        "question_type": "transfer_question",
        "concept_name": "Variables",
        "prompt": "Use variables in a shopping bill example.",
        "expected_answer": "Use names such as price and quantity to store values.",
        "key_points": ["Variables can store price and quantity values."],
    },
    {
        "question_id": "q6",
        "question_type": "challenge_question",
        "concept_name": "Loops",
        "prompt": "Explain a loop challenge.",
        "expected_answer": "Track each iteration and update the variable.",
        "key_points": ["Track values through each iteration."],
    },
    {
        "question_id": "q7",
        "question_type": "syntax_completion",
        "concept_name": "If Statements",
        "prompt": "Complete the condition.",
        "expected_answer": "if x == 3:",
    },
    {
        "question_id": "q8",
        "question_type": "puzzle",
        "concept_name": "Variables",
        "prompt": "Arrange assignment then print.",
        "expected_answer": "name = 'Ada'; print(name)",
    },
]


def _assert_answer_shape(answer: dict) -> None:
    required = {
        "status",
        "module",
        "profile",
        "question_type",
        "simulated_answer",
        "expected_answer",
        "is_expected_correct",
        "score_estimate",
        "confidence",
        "time_taken_sec",
        "hint_used",
        "option_changes",
        "mistake_type",
        "simulation_parameters",
    }
    assert required.issubset(answer)
    assert answer["status"] == "success"
    assert answer["module"] == "LearnerAnswerSimulator"
    assert 0.0 <= answer["confidence"] <= 1.0
    assert 0.0 <= answer["score_estimate"] <= 1.0
    assert answer["time_taken_sec"] > 0


def main() -> None:
    simulator = LearnerAnswerSimulator()

    single_outputs = {}
    for index, profile in enumerate(PROFILE_PARAMETERS):
        answer = simulator.simulate_answer(SAMPLE_QUESTIONS[index % len(SAMPLE_QUESTIONS)], profile, seed=42 + index)
        _assert_answer_shape(answer)
        single_outputs[profile] = answer

    sessions = {}
    for index, profile in enumerate(PROFILE_PARAMETERS):
        session = simulator.simulate_session(SAMPLE_QUESTIONS, profile, seed=100 + index)
        assert session["status"] == "success"
        assert session["profile"] == profile
        assert session["question_count"] == len(SAMPLE_QUESTIONS)
        for answer in session["answers"]:
            _assert_answer_shape(answer)
        sessions[profile] = session

    first = simulator.simulate_session(SAMPLE_QUESTIONS, "average", seed=1234)
    second = simulator.simulate_session(SAMPLE_QUESTIONS, "average", seed=1234)
    assert first == second

    patterns = {
        profile: (
            session["summary"]["average_score"],
            session["summary"]["average_confidence"],
            session["summary"]["average_time_taken_sec"],
            session["summary"]["hint_usage_rate"],
        )
        for profile, session in sessions.items()
    }
    assert len(set(patterns.values())) >= 4
    assert patterns["strong"][0] > patterns["weak"][0]
    assert patterns["weak"][3] >= patterns["strong"][3]
    assert patterns["guessing"][2] < patterns["weak"][2]
    assert patterns["low_confidence"][1] < patterns["average"][1]

    print("STATUS: success")
    print("MODULE: learner_answer_simulator_test")


if __name__ == "__main__":
    main()
