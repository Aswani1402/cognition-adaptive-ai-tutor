from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tutor.evaluation.answer_evaluator import AnswerEvaluator


OUTPUT_JSON = Path("evaluation_outputs/json/answer_evaluator_report.json")
OUTPUT_MD = Path("evaluation_outputs/reports/answer_evaluator_report.md")
ANSWER_EVALUATOR_PATH = Path("tutor/evaluation/answer_evaluator.py")

SUPPORTED_TYPES = [
    "mcq",
    "output_prediction",
    "debug_task",
    "debug",
    "coding_question",
    "syntax_completion",
    "explanation",
    "transfer_question",
    "challenge_question",
    "challenge",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sample_cases() -> list[dict[str, Any]]:
    return [
        {
            "case_id": "mcq_correct",
            "question": {
                "question_id": "R1",
                "question_type": "mcq",
                "selected_option": "B",
                "correct_answer": "B",
            },
        },
        {
            "case_id": "mcq_wrong",
            "question": {
                "question_id": "R2",
                "assessment_type": "mcq",
                "selected_option": "A",
                "correct_answer": "B",
            },
        },
        {
            "case_id": "output_prediction_correct",
            "question": {
                "question_id": "R3",
                "task_type": "output_prediction",
                "expected_output": "10",
                "learner_answer": "10",
            },
        },
        {
            "case_id": "output_prediction_wrong",
            "question": {
                "question_id": "R4",
                "task_type": "output_prediction",
                "expected_output": "10",
                "learner_answer": "9",
            },
        },
        {
            "case_id": "debug_task_corrected_code",
            "question": {
                "question_id": "R5",
                "task_type": "debug_task",
                "corrected_code": "x = 5\nprint(x)",
                "expected_output": "5",
                "expected_fix": "Use x instead of an undefined name.",
            },
        },
        {
            "case_id": "debug_text",
            "question": {
                "question_id": "R6",
                "task_type": "debug",
                "learner_answer": "The code uses y before assigning it; replace y with x.",
                "expected_fix": "Replace y with x.",
            },
        },
        {
            "case_id": "coding_question_correct",
            "question": {
                "question_id": "R7",
                "task_type": "coding_question",
                "learner_answer": "print(10)",
                "expected_output": "10",
            },
        },
        {
            "case_id": "syntax_completion_correct",
            "question": {
                "question_id": "R8",
                "task_type": "syntax_completion",
                "starter_code": "x = ",
                "learner_answer": "10\nprint(x)",
                "expected_output": "10",
            },
        },
        {
            "case_id": "explanation_partial",
            "question": {
                "question_id": "R9",
                "task_type": "explanation",
                "learner_answer": "A variable is a named value stored so a program can reuse it later.",
                "expected_answer": "A variable stores a value and can be reused later in a program.",
            },
        },
        {
            "case_id": "transfer_question",
            "question": {
                "question_id": "R10",
                "task_type": "transfer_question",
                "learner_answer": "Use variables to store prices and quantities, then calculate a bill total.",
                "expected_answer": "Variables can store real-world values such as prices and quantities for later calculations.",
            },
        },
        {
            "case_id": "challenge_with_code",
            "question": {
                "question_id": "R11",
                "task_type": "challenge",
                "learner_answer": "total = 7 + 3\nprint(total)",
                "expected_output": "10",
            },
        },
        {
            "case_id": "challenge_question_with_tests",
            "question": {
                "question_id": "R12",
                "task_type": "challenge_question",
                "learner_answer": "print(4)",
                "test_cases": [{"expected_output": "4"}],
            },
        },
        {
            "case_id": "unsafe_code_blocked",
            "question": {
                "question_id": "R13",
                "task_type": "coding_question",
                "learner_answer": "import os\nprint(os.getcwd())",
                "expected_output": "",
            },
        },
    ]


def _run_cases() -> dict[str, Any]:
    evaluator = AnswerEvaluator()
    results: list[dict[str, Any]] = []
    failures: list[str] = []

    for case in _sample_cases():
        case_id = case["case_id"]
        try:
            output = evaluator.evaluate(case["question"])
            results.append(
                {
                    "case_id": case_id,
                    "task_type": output.get("task_type"),
                    "routed_to": output.get("routed_to"),
                    "score": output.get("score"),
                    "label": output.get("label"),
                    "correct": output.get("correct"),
                    "mistake_type": output.get("mistake_type"),
                    "status": output.get("status"),
                    "feedback": output.get("feedback"),
                }
            )
        except Exception as exc:
            failures.append(f"{case_id}: {exc}")

    labels = Counter(str(result.get("label")) for result in results)
    route_counts = Counter(str(result.get("routed_to")) for result in results)
    unsafe_result = next((result for result in results if result["case_id"] == "unsafe_code_blocked"), {})

    return {
        "status": "success" if not failures and unsafe_result.get("mistake_type") == "unsafe_code" else "warning",
        "cases": results,
        "case_count": len(results),
        "failures": failures,
        "label_counts": {
            "strong": labels.get("strong", 0),
            "partial": labels.get("partial", 0),
            "weak": labels.get("weak", 0),
        },
        "route_counts": dict(route_counts),
        "unsafe_code_blocked": unsafe_result.get("mistake_type") == "unsafe_code",
    }


def _support_status(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    observed_types = {str(result.get("task_type")) for result in case_results}
    required_groups = {
        "mcq": "mcq" in observed_types,
        "output_prediction": "output_prediction" in observed_types,
        "debug_task/debug": bool({"debug_task", "debug"} & observed_types),
        "coding_question": "coding_question" in observed_types,
        "syntax_completion": "syntax_completion" in observed_types,
        "explanation": "explanation" in observed_types,
        "transfer_question": "transfer_question" in observed_types,
        "challenge_question/challenge": bool({"challenge_question", "challenge"} & observed_types),
    }
    missing = [name for name, available in required_groups.items() if not available]
    return {
        "status": "success" if not missing else "warning",
        "answer_evaluator_exists": ANSWER_EVALUATOR_PATH.exists(),
        "supported_types_requested": SUPPORTED_TYPES,
        "observed_task_types": sorted(observed_types),
        "required_groups": required_groups,
        "missing_groups": missing,
    }


def _frontend_component_status() -> dict[str, Any]:
    roots = [
        Path("frontend"),
        Path("ui"),
        Path("tutor/system"),
        Path("tutor/assessment"),
    ]
    extensions = {".py", ".js", ".jsx", ".ts", ".tsx"}
    matches: dict[str, list[str]] = {task_type: [] for task_type in SUPPORTED_TYPES}

    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in extensions:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for task_type in SUPPORTED_TYPES:
                if task_type in text:
                    matches[task_type].append(str(path))

    matched_components = {
        task_type: sorted(set(paths))[:5]
        for task_type, paths in matches.items()
        if paths
    }
    return {
        "status": "success" if matched_components else "warning",
        "note": "Frontend component discovery is best-effort and non-blocking.",
        "matched_assessment_components": matched_components,
        "supported_frontend_assessment_components": sorted(matched_components.keys()),
    }


def _overall_status(parts: list[dict[str, Any]]) -> str:
    blocking_statuses = [part.get("status") for part in parts]
    if "error" in blocking_statuses:
        return "error"
    if "warning" in blocking_statuses:
        return "warning"
    return "success"


def _build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# AnswerEvaluator Report",
        "",
        f"Generated at: {report['generated_at']}",
        "",
        f"Overall status: `{report['overall_status']}`",
        "",
        "## Module",
        "",
        f"- AnswerEvaluator exists: {report['support_status']['answer_evaluator_exists']}",
        f"- Support status: `{report['support_status']['status']}`",
        f"- Missing groups: {report['support_status']['missing_groups']}",
        "",
        "## Sample Results",
        "",
        "| Case | Task type | Routed to | Score | Label | Correct | Mistake type |",
        "| --- | --- | --- | ---: | --- | --- | --- |",
    ]

    for result in report["case_status"]["cases"]:
        lines.append(
            "| {case_id} | {task_type} | {routed_to} | {score} | {label} | {correct} | {mistake_type} |".format(
                **result
            )
        )

    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- Case count: {report['case_status']['case_count']}",
            f"- Label counts: {report['case_status']['label_counts']}",
            f"- Route counts: {report['case_status']['route_counts']}",
            f"- Unsafe code blocked: {report['case_status']['unsafe_code_blocked']}",
            "",
            "## Frontend Assessment Components",
            "",
            f"- Status: `{report['frontend_component_status']['status']}`",
            f"- Supported components found: {report['frontend_component_status']['supported_frontend_assessment_components']}",
            f"- Note: {report['frontend_component_status']['note']}",
            "",
            "## Status",
            "",
            "```text",
            f"STATUS: {report['overall_status']}",
            "MODULE: answer_evaluator_report",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def build_report() -> dict[str, Any]:
    case_status = _run_cases()
    support = _support_status(case_status["cases"])
    frontend = _frontend_component_status()

    return {
        "overall_status": _overall_status([case_status, support]),
        "module": "answer_evaluator_report",
        "generated_at": _now_iso(),
        "support_status": support,
        "case_status": case_status,
        "frontend_component_status": frontend,
        "limitations": [
            "Frontend component discovery is a static keyword scan and is not treated as a blocking backend evaluator check.",
            "Rubric-style sample scores depend on the current local rubric evaluator heuristics.",
            "Code execution remains intentionally sandboxed and blocks unsafe imports and file/network access.",
        ],
    }


def main() -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)

    report = build_report()
    OUTPUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    OUTPUT_MD.write_text(_build_markdown(report), encoding="utf-8")

    print(f"STATUS: {report['overall_status']}")
    print("MODULE: answer_evaluator_report")
    print(f"JSON_REPORT: {OUTPUT_JSON}")
    print(f"MD_REPORT: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
