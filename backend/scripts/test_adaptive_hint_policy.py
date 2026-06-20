from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from tutor.policy.adaptive_hint_policy import AdaptiveHintPolicy, EVIDENCE_FIELDS


JSON_REPORT = Path("evaluation_outputs/json/adaptive_hint_policy_report.json")
MD_REPORT = Path("evaluation_outputs/reports/adaptive_hint_policy_report.md")


TEST_CASES = [
    {
        "name": "strong learner gets small hint",
        "expected_hint_type": "small_hint",
        "evidence": {
            "learner_id": "L1",
            "concept_id": "1",
            "concept_name": "Variables",
            "question_type": "mcq",
            "learner_answer": "A variable stores a value.",
            "expected_answer": "A variable stores a value.",
            "score": 0.92,
            "evaluation_label": "strong",
            "mistake_type": "correct",
            "weakest_skill": "concept recall",
            "behaviour_risk": 0.05,
            "mastery_score": 0.9,
            "hint_count_used": 0,
            "difficulty": "easy",
            "teaching_view": "definition_view",
            "key_points": ["Variables are names linked to values."],
            "example": "score = 10 stores 10 using the name score.",
        },
    },
    {
        "name": "weak score and low mastery gets worked example",
        "expected_hint_type": "worked_example",
        "evidence": {
            "learner_id": "L2",
            "concept_id": "1",
            "concept_name": "Variables",
            "question_type": "explanation",
            "learner_answer": "I do not know",
            "expected_answer": "A variable stores a value.",
            "score": 0.05,
            "evaluation_label": "weak",
            "mistake_type": "no_answer",
            "weakest_skill": "concept explanation",
            "behaviour_risk": 0.75,
            "mastery_score": 0.1,
            "hint_count_used": 1,
            "difficulty": "easy",
            "teaching_view": "definition_view",
            "key_points": ["A variable is a reusable name for a value."],
            "example": "age = 15 connects the name age to the value 15.",
        },
    },
    {
        "name": "debug task gets debug hint",
        "expected_hint_type": "debug_hint",
        "evidence": {
            "learner_id": "L3",
            "concept_id": "2",
            "concept_name": "Strings",
            "question_type": "debug_task",
            "learner_answer": "No mistake",
            "expected_answer": "Add missing quotes.",
            "score": 0.35,
            "evaluation_label": "weak",
            "mistake_type": "debug_misdiagnosis",
            "weakest_skill": "bug localization",
            "behaviour_risk": 0.2,
            "mastery_score": 0.5,
            "hint_count_used": 0,
            "difficulty": "medium",
            "teaching_view": "debug_view",
        },
    },
    {
        "name": "output prediction gets output prediction hint",
        "expected_hint_type": "output_prediction_hint",
        "evidence": {
            "learner_id": "L4",
            "concept_id": "3",
            "concept_name": "Loops",
            "question_type": "output_prediction",
            "learner_answer": "5",
            "expected_answer": "0 1 2",
            "score": 0.3,
            "evaluation_label": "weak",
            "mistake_type": "wrong_output",
            "weakest_skill": "state tracing",
            "behaviour_risk": 0.3,
            "mastery_score": 0.45,
            "hint_count_used": 0,
            "difficulty": "medium",
            "teaching_view": "output_prediction_view",
        },
    },
    {
        "name": "syntax misunderstanding gets syntax hint",
        "expected_hint_type": "syntax_hint",
        "evidence": {
            "learner_id": "L5",
            "concept_id": "4",
            "concept_name": "If Statements",
            "question_type": "syntax_completion",
            "learner_answer": "if x = 3",
            "expected_answer": "if x == 3:",
            "score": 0.25,
            "evaluation_label": "weak",
            "mistake_type": "syntax_misunderstanding",
            "weakest_skill": "syntax accuracy",
            "behaviour_risk": 0.25,
            "mastery_score": 0.4,
            "hint_count_used": 0,
            "difficulty": "medium",
            "teaching_view": "code_view",
        },
    },
    {
        "name": "misconception gets misconception hint",
        "expected_hint_type": "misconception_hint",
        "evidence": {
            "learner_id": "L6",
            "concept_id": "1",
            "concept_name": "Variables",
            "question_type": "explanation",
            "learner_answer": "A variable is the same as a constant.",
            "expected_answer": "A variable can reference a value that may be reused or updated.",
            "score": 0.3,
            "evaluation_label": "weak",
            "mistake_type": "concept_misconception",
            "weakest_skill": "concept distinction",
            "behaviour_risk": 0.15,
            "mastery_score": 0.35,
            "hint_count_used": 0,
            "difficulty": "easy",
            "teaching_view": "misconception_view",
            "key_points": ["Variables are not the same as constants."],
        },
    },
    {
        "name": "repeated hint use escalates",
        "expected_hint_type": "worked_example",
        "evidence": {
            "learner_id": "L7",
            "concept_id": "1",
            "concept_name": "Variables",
            "question_type": "mcq",
            "learner_answer": "loop",
            "expected_answer": "stores a value",
            "score": 0.55,
            "evaluation_label": "partial",
            "mistake_type": "wrong_mcq_choice",
            "weakest_skill": "concept recall",
            "behaviour_risk": 0.2,
            "mastery_score": 0.55,
            "hint_count_used": 3,
            "difficulty": "easy",
            "teaching_view": "definition_view",
        },
    },
    {
        "name": "missing evidence safe fallback",
        "expected_hint_type": "guided_hint",
        "evidence": {
            "concept_name": "Variables",
            "question_type": "general",
        },
    },
]


def build_report() -> dict:
    policy = AdaptiveHintPolicy()
    outputs = []
    for case in TEST_CASES:
        output = policy.select_hint(case["evidence"])
        output["test_case"] = case["name"]
        output["expected_hint_type"] = case["expected_hint_type"]
        outputs.append(output)

    hint_counts = Counter(item["hint_type"] for item in outputs)
    fallback_count = sum(1 for item in outputs if item["fallback_used"])
    component_count = sum(
        1 for item in outputs if item.get("frontend_component") == "AdaptiveHintCard"
    )
    avg_support = sum(item["support_need"] for item in outputs) / len(outputs)

    report = {
        "status": "success",
        "module": "adaptive_hint_policy_test",
        "test_case_count": len(TEST_CASES),
        "hint_type_distribution": dict(hint_counts),
        "average_support_need": round(avg_support, 6),
        "fallback_rate": round(fallback_count / len(outputs), 6),
        "frontend_component_coverage": round(component_count / len(outputs), 6),
        "evidence_fields_used": EVIDENCE_FIELDS,
        "test_outputs": outputs,
        "final_report_wording": (
            "The adaptive hint policy provides graduated learner support using evaluation score, "
            "mistake type, mastery, behaviour risk, and previous hint usage. Instead of immediately "
            "revealing answers, the system selects small hints, guided hints, misconception hints, "
            "debug hints, output-prediction hints, or worked examples based on learner need."
        ),
        "limitations": [
            "The policy is deterministic and evidence-scored; it is not a trained hint model.",
            "Fallback defaults are used when score, mastery, or behaviour evidence is missing.",
            "Worked examples use similar examples and should avoid revealing exact answers unless configured by a caller.",
        ],
    }
    return report


def write_reports(report: dict) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# Adaptive Hint Policy Report",
        "",
        f"Status: **{report['status']}**",
        "",
        report["final_report_wording"],
        "",
        f"- Test case count: {report['test_case_count']}",
        f"- Average support need: {report['average_support_need']}",
        f"- Fallback rate: {report['fallback_rate']}",
        f"- Frontend component coverage: {report['frontend_component_coverage']}",
        "",
        "## Hint Type Distribution",
        "",
    ]
    for hint_type, count in report["hint_type_distribution"].items():
        lines.append(f"- {hint_type}: {count}")
    lines.extend(["", "## Limitations", ""])
    for limitation in report["limitations"]:
        lines.append(f"- {limitation}")
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_report()
    write_reports(report)

    assert report["status"] == "success"
    assert report["module"] == "adaptive_hint_policy_test"
    assert report["test_case_count"] == 8
    assert report["frontend_component_coverage"] == 1.0
    for output in report["test_outputs"]:
        assert output["status"] == "success"
        assert output["module"] == "AdaptiveHintPolicy"
        assert output["hint_text"]
        assert output["frontend_component"] == "AdaptiveHintCard"
        assert output["hint_type"] == output["expected_hint_type"]

    print("STATUS: success")
    print("MODULE: adaptive_hint_policy_test")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
