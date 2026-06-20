import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

from src.tutor_lm_service import TutorLMService


ROOT_DIR = Path(__file__).resolve().parents[1]

OUTPUT_DIR = ROOT_DIR / "outputs" / "service_tests"
OUTPUT_JSON = OUTPUT_DIR / "tutor_lm_service_quality_report.json"
OUTPUT_MD = OUTPUT_DIR / "tutor_lm_service_quality_report.md"

TEST_CONCEPTS = [
    {
        "domain": "Python",
        "concept_id": "P1",
        "label": "Python Variables",
    },
    {
        "domain": "Python",
        "concept_id": "P4",
        "label": "Python Loops",
    },
    {
        "domain": "SQL",
        "concept_id": "S2",
        "label": "SQL SELECT",
    },
    {
        "domain": "HTML",
        "concept_id": "H2",
        "label": "HTML Tags & Elements",
    },
    {
        "domain": "Git",
        "concept_id": "G3",
        "label": "Git Commits & History",
    },
    {
        "domain": "Data Structures",
        "concept_id": "D1",
        "label": "Data Structures Arrays",
    },
    {
        "domain": "Data Structures",
        "concept_id": "D3",
        "label": "Data Structures Stack",
    },
]

TEST_VIEWS = [
    "definition_view",
    "code_view",
    "analogy_view",
    "misconception_view",
    "revision_summary_view",
]

REQUIRED_QUESTION_TYPES = {
    "mcq",
    "debug_task",
    "output_prediction",
    "transfer_question",
    "challenge_question",
    "explanation_check",
}


def short_preview(value: Any, max_chars: int = 220) -> str:
    if isinstance(value, dict):
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value or "")

    text = text.replace("\n", " ").strip()

    if len(text) <= max_chars:
        return text

    return text[:max_chars] + "..."


def validate_teaching_response(response: Dict[str, Any]) -> List[str]:
    issues = []

    if response.get("status") != "success":
        issues.append("teaching_status_not_success")

    if not response.get("concept_id"):
        issues.append("missing_concept_id")

    if not response.get("concept_name"):
        issues.append("missing_concept_name")

    if not response.get("domain"):
        issues.append("missing_domain")

    teaching = response.get("teaching")

    if teaching is None:
        issues.append("missing_teaching_output")
    elif isinstance(teaching, str) and len(teaching.strip()) < 40:
        issues.append("teaching_text_too_short")
    elif isinstance(teaching, dict) and not teaching:
        issues.append("teaching_json_empty")

    if response.get("valid") is not True:
        issues.append("teaching_valid_not_true")

    return issues


def validate_assessment_response(response: Dict[str, Any], min_questions: int = 6) -> List[str]:
    issues = []

    if response.get("status") != "success":
        issues.append("assessment_status_not_success")

    questions = response.get("questions", [])

    if len(questions) < min_questions:
        issues.append(f"low_question_count_{len(questions)}")

    seen_types = {q.get("question_type") for q in questions}

    missing_types = sorted(REQUIRED_QUESTION_TYPES - seen_types)

    if missing_types:
        issues.append(f"missing_question_types_{missing_types}")

    for q in questions:
        if not q.get("concept_id"):
            issues.append("question_missing_concept_id")

        if not q.get("concept_name"):
            issues.append("question_missing_concept_name")

        if not q.get("domain"):
            issues.append("question_missing_domain")

        if not q.get("question_type"):
            issues.append("question_missing_type")

        if q.get("question") is None:
            issues.append("question_missing_payload")

        if q.get("answer_key") is None:
            issues.append("question_missing_answer_key")

    return issues


def pick_sample_answer(question: Dict[str, Any]) -> Any:
    qtype = question.get("question_type")
    answer_key = question.get("answer_key") or {}

    if qtype == "mcq":
        return answer_key.get("answer", "")

    if qtype == "output_prediction":
        return answer_key.get("answer", "")

    if qtype == "debug_task":
        return answer_key.get("expected_fix", "")

    concept_name = question.get("concept_name") or "the concept"
    return f"I would explain {concept_name} using the main rule and one clear example."


def run_quality_test() -> Dict[str, Any]:
    service = TutorLMService()

    all_results = []
    global_issues = []
    teaching_status_counts = Counter()
    assessment_type_counts = Counter()
    evaluation_scores = []

    for concept in TEST_CONCEPTS:
        domain = concept["domain"]
        concept_id = concept["concept_id"]

        concept_result = {
            "label": concept["label"],
            "domain": domain,
            "concept_id": concept_id,
            "teaching_tests": [],
            "assessment_test": None,
            "evaluation_test": None,
            "code_runner_test": None,
            "issues": [],
        }

        # 1. Teaching view tests
        for view in TEST_VIEWS:
            response = service.get_teaching_view(
                concept_id=concept_id,
                domain=domain,
                artifact_type=view,
            )

            issues = validate_teaching_response(response)

            teaching_status_counts[response.get("status", "unknown")] += 1

            concept_result["teaching_tests"].append(
                {
                    "view": view,
                    "status": response.get("status"),
                    "concept_name": response.get("concept_name"),
                    "valid": response.get("valid"),
                    "issues": issues,
                    "preview": short_preview(response.get("teaching")),
                }
            )

            for issue in issues:
                concept_result["issues"].append(f"{view}: {issue}")

        # 2. Assessment question test
        assessment = service.get_assessment_questions(
            concept_id=concept_id,
            domain=domain,
            num_questions=18,
            shuffle=False,
        )

        assessment_issues = validate_assessment_response(
            assessment,
            min_questions=15,
        )

        for q in assessment.get("questions", []):
            assessment_type_counts[q.get("question_type")] += 1

        concept_result["assessment_test"] = {
            "status": assessment.get("status"),
            "num_available": assessment.get("num_available"),
            "num_returned": assessment.get("num_returned"),
            "question_types": dict(Counter(q.get("question_type") for q in assessment.get("questions", []))),
            "issues": assessment_issues,
            "sample_questions": [
                {
                    "session_question_id": q.get("session_question_id"),
                    "question_type": q.get("question_type"),
                    "variant_id": q.get("variant_id"),
                    "preview": short_preview(q.get("question")),
                }
                for q in assessment.get("questions", [])[:4]
            ],
        }

        for issue in assessment_issues:
            concept_result["issues"].append(f"assessment: {issue}")

        # 3. Evaluation test using first question
        if assessment.get("questions"):
            sample_question = assessment["questions"][0]
            learner_answer = pick_sample_answer(sample_question)

            evaluation = service.evaluate_learner_answer(
                concept_id=sample_question["concept_id"],
                question_type=sample_question["question_type"],
                variant_id=sample_question["variant_id"],
                learner_answer=learner_answer,
            )

            eval_payload = evaluation.get("evaluation", {})
            score = float(eval_payload.get("score", 0.0))
            evaluation_scores.append(score)

            concept_result["evaluation_test"] = {
                "status": evaluation.get("status"),
                "question_type": sample_question.get("question_type"),
                "variant_id": sample_question.get("variant_id"),
                "score": score,
                "correct": eval_payload.get("correct"),
                "mistake_type": eval_payload.get("mistake_type"),
                "feedback": eval_payload.get("feedback"),
                "next_signal": eval_payload.get("next_signal"),
            }

            if evaluation.get("status") != "success":
                concept_result["issues"].append("evaluation_status_not_success")

            if score < 0.35:
                concept_result["issues"].append(f"evaluation_low_score_{score}")

        else:
            concept_result["issues"].append("no_question_for_evaluation_test")

        # 4. Python code runner test only for Python concepts
        if domain == "Python":
            code_result = service.run_code(
                code="x = 10\nx = 20\nprint(x)",
                expected_output="20",
            )

            concept_result["code_runner_test"] = {
                "status": code_result.get("status"),
                "mode": code_result.get("mode"),
                "success": (code_result.get("result") or {}).get("success"),
                "score": (code_result.get("result") or {}).get("score"),
            }

            if (code_result.get("result") or {}).get("score") != 1.0:
                concept_result["issues"].append("code_runner_score_not_1")

        all_results.append(concept_result)

        for issue in concept_result["issues"]:
            global_issues.append(
                {
                    "concept_id": concept_id,
                    "domain": domain,
                    "label": concept["label"],
                    "issue": issue,
                }
            )

    passed_concepts = sum(1 for item in all_results if not item["issues"])

    report = {
        "status": "PASS" if not global_issues else "CHECK",
        "total_test_concepts": len(TEST_CONCEPTS),
        "passed_concepts": passed_concepts,
        "failed_or_warning_concepts": len(TEST_CONCEPTS) - passed_concepts,
        "global_issue_count": len(global_issues),
        "global_issues": global_issues,
        "teaching_status_counts": dict(teaching_status_counts),
        "assessment_type_counts": dict(assessment_type_counts),
        "average_sample_evaluation_score": round(
            sum(evaluation_scores) / len(evaluation_scores),
            3,
        )
        if evaluation_scores
        else 0.0,
        "concept_results": all_results,
    }

    return report


def build_markdown(report: Dict[str, Any]) -> str:
    lines = []

    lines.append("# TutorLM Service Multi-Concept Quality Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Status: **{report['status']}**")
    lines.append(f"- Total tested concepts: **{report['total_test_concepts']}**")
    lines.append(f"- Passed concepts: **{report['passed_concepts']}**")
    lines.append(f"- Failed/warning concepts: **{report['failed_or_warning_concepts']}**")
    lines.append(f"- Global issue count: **{report['global_issue_count']}**")
    lines.append(f"- Average sample evaluation score: **{report['average_sample_evaluation_score']}**")
    lines.append("")

    lines.append("## Teaching Status Counts")
    lines.append("")
    for key, value in report["teaching_status_counts"].items():
        lines.append(f"- {key}: {value}")
    lines.append("")

    lines.append("## Assessment Question Type Counts In Test")
    lines.append("")
    for key, value in sorted(report["assessment_type_counts"].items()):
        lines.append(f"- {key}: {value}")
    lines.append("")

    lines.append("## Global Issues")
    lines.append("")
    if not report["global_issues"]:
        lines.append("No issues found.")
    else:
        for issue in report["global_issues"]:
            lines.append(
                f"- {issue['domain']} {issue['concept_id']} — {issue['label']}: {issue['issue']}"
            )
    lines.append("")

    lines.append("## Concept Results")
    lines.append("")

    for item in report["concept_results"]:
        lines.append(f"### {item['label']} ({item['domain']} {item['concept_id']})")
        lines.append("")
        lines.append(f"Issues: `{item['issues']}`")
        lines.append("")

        lines.append("#### Teaching Views")
        lines.append("")
        for test in item["teaching_tests"]:
            lines.append(
                f"- **{test['view']}** | status={test['status']} | valid={test['valid']} | "
                f"issues={test['issues']} | preview={test['preview']}"
            )
        lines.append("")

        assessment = item["assessment_test"] or {}
        lines.append("#### Assessment")
        lines.append("")
        lines.append(f"- Status: {assessment.get('status')}")
        lines.append(f"- Num available: {assessment.get('num_available')}")
        lines.append(f"- Num returned: {assessment.get('num_returned')}")
        lines.append(f"- Question types: {assessment.get('question_types')}")
        lines.append(f"- Issues: {assessment.get('issues')}")
        lines.append("")

        lines.append("Sample questions:")
        for q in assessment.get("sample_questions", []):
            lines.append(
                f"- {q['session_question_id']} | {q['question_type']} v{q['variant_id']} | {q['preview']}"
            )
        lines.append("")

        evaluation = item["evaluation_test"] or {}
        lines.append("#### Evaluation")
        lines.append("")
        lines.append(f"- Status: {evaluation.get('status')}")
        lines.append(f"- Question type: {evaluation.get('question_type')}")
        lines.append(f"- Score: {evaluation.get('score')}")
        lines.append(f"- Correct: {evaluation.get('correct')}")
        lines.append(f"- Feedback: {evaluation.get('feedback')}")
        lines.append("")

        if item.get("code_runner_test"):
            code = item["code_runner_test"]
            lines.append("#### Code Runner")
            lines.append("")
            lines.append(f"- Status: {code.get('status')}")
            lines.append(f"- Success: {code.get('success')}")
            lines.append(f"- Score: {code.get('score')}")
            lines.append("")

    return "\n".join(lines)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\nRunning TutorLM service multi-concept quality test...")
    print("=" * 80)

    report = run_quality_test()

    with OUTPUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    with OUTPUT_MD.open("w", encoding="utf-8") as f:
        f.write(build_markdown(report))

    print("\nQuality test complete.")
    print(f"Status: {report['status']}")
    print(f"Total tested concepts: {report['total_test_concepts']}")
    print(f"Passed concepts: {report['passed_concepts']}")
    print(f"Failed/warning concepts: {report['failed_or_warning_concepts']}")
    print(f"Global issue count: {report['global_issue_count']}")
    print(f"Average sample evaluation score: {report['average_sample_evaluation_score']}")
    print(f"Output JSON: {OUTPUT_JSON}")
    print(f"Output Markdown: {OUTPUT_MD}")

    if report["global_issues"]:
        print("\nIssues:")
        for issue in report["global_issues"]:
            print(issue)

    print(f"\nSTATUS: {report['status']}")


if __name__ == "__main__":
    main()