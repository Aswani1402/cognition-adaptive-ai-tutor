from __future__ import annotations

import json
from pathlib import Path

from scripts.test_learner_answer_simulator import SAMPLE_QUESTIONS
from tutor.evaluation.answer_evaluator import AnswerEvaluator
from tutor.policy.adaptive_hint_policy import AdaptiveHintPolicy
from tutor.simulation.learner_answer_simulator import PROFILE_PARAMETERS, LearnerAnswerSimulator


JSON_REPORT = Path("evaluation_outputs/json/simulated_learner_pipeline_report.json")
MD_REPORT = Path("evaluation_outputs/reports/simulated_learner_pipeline_report.md")


def build_report() -> dict:
    simulator = LearnerAnswerSimulator()
    evaluator = AnswerEvaluator()
    hint_policy = AdaptiveHintPolicy()
    profile_outputs = {}

    for profile_index, profile in enumerate(PROFILE_PARAMETERS):
        session = simulator.simulate_session(SAMPLE_QUESTIONS, profile, seed=5000 + profile_index)
        evaluated_items = []
        for question, simulated in zip(SAMPLE_QUESTIONS, session["answers"]):
            evaluation_question = dict(question)
            evaluation_question["learner_answer"] = simulated["simulated_answer"]
            if question.get("question_type") == "output_prediction":
                evaluation_question["predicted_output"] = simulated["simulated_answer"]
            if question.get("question_type") == "mcq":
                evaluation_question["selected_option"] = simulated["simulated_answer"]
            evaluation = evaluator.evaluate(evaluation_question)
            hint = hint_policy.select_hint(
                {
                    "learner_id": f"sim_{profile}",
                    "concept_id": question.get("concept_id", question.get("question_id")),
                    "concept_name": question.get("concept_name"),
                    "question_type": question.get("question_type"),
                    "learner_answer": simulated["simulated_answer"],
                    "expected_answer": simulated["expected_answer"],
                    "score": evaluation.get("score", simulated["score_estimate"]),
                    "evaluation_label": evaluation.get("label"),
                    "mistake_type": evaluation.get("mistake_type") or simulated["mistake_type"],
                    "weakest_skill": "simulated skill",
                    "behaviour_risk": simulated["simulation_parameters"]["guess_probability"],
                    "mastery_score": session["summary"]["average_score"],
                    "hint_count_used": int(simulated["hint_used"]),
                    "difficulty": "medium",
                    "teaching_view": "simulation_view",
                    "key_points": question.get("key_points"),
                    "example": question.get("expected_answer"),
                }
            )
            evaluated_items.append(
                {
                    "question_id": question.get("question_id"),
                    "question_type": question.get("question_type"),
                    "simulated_answer": simulated,
                    "evaluation": evaluation,
                    "adaptive_hint": hint,
                    "recommended_next_action": "retry_with_hint"
                    if hint.get("hint_type") != "small_hint"
                    else "continue_practice",
                }
            )
        profile_outputs[profile] = {
            "session_summary": session["summary"],
            "items": evaluated_items,
        }

    report = {
        "status": "success",
        "module": "simulated_learner_pipeline_evaluation",
        "profile_count": len(profile_outputs),
        "profiles": list(profile_outputs),
        "profile_outputs": profile_outputs,
        "limitations": [
            "Uses small sample questions only.",
            "Does not replace production learner data or full integrated tutor evaluation.",
            "Evaluator behavior depends on available local evaluator modules.",
        ],
    }
    return report


def write_reports(report: dict) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Simulated Learner Pipeline Evaluation",
        "",
        f"Status: **{report['status']}**",
        "",
        f"- Profile count: {report['profile_count']}",
        f"- Profiles: {', '.join(report['profiles'])}",
        "",
        "## Limitations",
        "",
    ]
    for limitation in report["limitations"]:
        lines.append(f"- {limitation}")
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_report()
    write_reports(report)
    print(f"STATUS: {report['status']}")
    print("MODULE: simulated_learner_pipeline_evaluation")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
