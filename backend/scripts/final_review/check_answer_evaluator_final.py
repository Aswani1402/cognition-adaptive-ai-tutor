from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

JSON_DIR = ROOT / "evaluation_outputs" / "json"
REPORT_DIR = ROOT / "evaluation_outputs" / "reports"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def score_ok(result: dict[str, Any], threshold: float = 0.75) -> bool:
    try:
        return float(result.get("score", result.get("overall_score", 0.0)) or 0.0) >= threshold
    except Exception:
        return False


def run_cases() -> list[dict[str, Any]]:
    from tutor.evaluation.answer_evaluator import evaluate_answer
    from tutor.evaluation.code_runner import SafeCodeRunner

    cases: list[dict[str, Any]] = []

    evaluator_cases = [
        {
            "name": "mcq",
            "question": {
                "question_id": "final-mcq",
                "task_type": "mcq",
                "prompt": "What does a Python variable do?",
                "expected_answer": "A named place used to store a value",
                "learner_answer": "A named place used to store a value",
            },
            "threshold": 0.85,
        },
        {
            "name": "fill_blank",
            "question": {
                "question_id": "final-fill",
                "task_type": "fill_blank",
                "prompt": "A variable stores a ____.",
                "expected_answer": "value",
                "learner_answer": "value",
            },
            "threshold": 0.85,
        },
        {
            "name": "true_false",
            "question": {
                "question_id": "final-tf",
                "task_type": "true_or_false",
                "prompt": "True or false: A Python variable can be reassigned.",
                "expected_answer": "true",
                "learner_answer": "true",
            },
            "threshold": 0.85,
        },
        {
            "name": "output_prediction",
            "question": {
                "question_id": "final-output",
                "task_type": "output_prediction",
                "prompt": "What is printed?",
                "expected_answer": "20",
                "learner_answer": "20",
            },
            "threshold": 0.85,
        },
        {
            "name": "debug_task",
            "question": {
                "question_id": "final-debug",
                "task_type": "debug_task",
                "prompt": "Fix: 2score = 10",
                "expected_answer": {"expected_fix": "score = 10", "bug_type": "invalid_variable_name"},
                "learner_answer": "Use score = 10 because variable names cannot start with a digit.",
            },
            "threshold": 0.45,
        },
    ]

    for case in evaluator_cases:
        try:
            result = evaluate_answer(case["question"])
            passed = score_ok(result, case["threshold"])
            cases.append(
                {
                    "case": case["name"],
                    "passed": passed,
                    "score": result.get("score"),
                    "label": result.get("label"),
                    "routed_to": result.get("routed_to"),
                    "feedback": result.get("feedback"),
                    "result": result,
                }
            )
        except Exception as exc:
            cases.append(
                {
                    "case": case["name"],
                    "passed": False,
                    "score": 0.0,
                    "label": "error",
                    "routed_to": None,
                    "feedback": f"{type(exc).__name__}: {exc}",
                    "result": None,
                }
            )

    try:
        code_result = SafeCodeRunner().run('name = "Ada"\nprint(name)', expected_output="Ada")
        cases.append(
            {
                "case": "simple_coding_print_safecoderunner",
                "passed": bool(code_result.get("passed")),
                "score": code_result.get("score"),
                "label": code_result.get("execution_status"),
                "routed_to": "SafeCodeRunner",
                "feedback": code_result.get("error") or "Safe code execution passed.",
                "result": code_result,
            }
        )
    except Exception as exc:
        cases.append(
            {
                "case": "simple_coding_print_safecoderunner",
                "passed": False,
                "score": 0.0,
                "label": "error",
                "routed_to": "SafeCodeRunner",
                "feedback": f"{type(exc).__name__}: {exc}",
                "result": None,
            }
        )

    return cases


def write_report(payload: dict[str, Any]) -> str:
    lines = [
        "# Final Answer Evaluator Check Report",
        "",
        f"Generated at: `{payload['generated_at']}`",
        "",
        f"- Total cases: `{payload['total_cases']}`",
        f"- Passed: `{payload['passed']}`",
        f"- Failed: `{payload['failed']}`",
        f"- Pass rate: `{payload['pass_rate']}`",
        "",
        "| Case | Passed | Score | Label | Route | Feedback |",
        "|---|---:|---:|---|---|---|",
    ]
    for item in payload["examples"]:
        lines.append(
            f"| {item['case']} | {item['passed']} | {item.get('score')} | {item.get('label')} | {item.get('routed_to')} | {str(item.get('feedback', '')).replace('|', '/')} |"
        )
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- These are deterministic module checks, not a complete pedagogical validity study.",
            "- Free-form semantic/debug scoring is approximate and should be paired with human review for final claims.",
            "- SafeCodeRunner is suitable for controlled demo execution, not unrestricted public code execution.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    cases = run_cases()
    passed = sum(1 for case in cases if case["passed"])
    payload = {
        "status": "success" if passed == len(cases) else "warning",
        "generated_at": now_iso(),
        "total_cases": len(cases),
        "passed": passed,
        "failed": len(cases) - passed,
        "pass_rate": round(passed / len(cases), 4) if cases else 0.0,
        "examples": cases,
        "limitations": [
            "Module-level deterministic cases only.",
            "No classroom outcome claim.",
            "SafeCodeRunner is restricted and intentionally blocks unsafe code.",
        ],
    }
    json_path = JSON_DIR / "final_answer_evaluator_check.json"
    report_path = REPORT_DIR / "final_answer_evaluator_check_report.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    report_path.write_text(write_report(payload), encoding="utf-8")
    print("FINAL ANSWER EVALUATOR CHECK")
    print(f"status: {payload['status']}")
    print(f"passed: {payload['passed']}/{payload['total_cases']}")
    print(f"json: {json_path}")
    print(f"report: {report_path}")


if __name__ == "__main__":
    main()
