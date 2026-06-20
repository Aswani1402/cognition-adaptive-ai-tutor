from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUTPUT_JSON = Path("evaluation_outputs/json/full_backend_smoke_test_report.json")
OUTPUT_MD = Path("evaluation_outputs/reports/full_backend_smoke_test_report.md")

COMMANDS = [
    {
        "id": "reward_db_audit",
        "label": "Reward DB audit",
        "command": [sys.executable, "-m", "scripts.db_audit.check_reward_state_tables"],
        "critical": True,
    },
    {
        "id": "frontend_response_builder",
        "label": "Frontend response builder",
        "command": [sys.executable, "-m", "scripts.test_frontend_response_builder"],
        "critical": True,
        "timeout_sec": 180,
    },
    {
        "id": "kt_runtime_inference",
        "label": "KT runtime inference",
        "command": [sys.executable, "-m", "scripts.test_kt_runtime_inference"],
        "critical": True,
    },
    {
        "id": "kt_upgrade_report",
        "label": "KT upgrade report",
        "command": [sys.executable, "-m", "scripts.evaluation.check_kt_upgrade_report"],
        "critical": True,
        "allow_warning_status": True,
    },
    {
        "id": "behaviour_persistence",
        "label": "Behaviour persistence",
        "command": [sys.executable, "-m", "scripts.test_behaviour_persistence"],
        "critical": True,
    },
    {
        "id": "behaviour_upgrade_report",
        "label": "Behaviour upgrade report",
        "command": [sys.executable, "-m", "scripts.evaluation.check_behaviour_upgrade_report"],
        "critical": True,
    },
    {
        "id": "safe_code_runner",
        "label": "SafeCodeRunner",
        "command": [sys.executable, "-m", "scripts.test_code_runner"],
        "critical": True,
    },
    {
        "id": "code_question_evaluator",
        "label": "CodeQuestionEvaluator",
        "command": [sys.executable, "-m", "scripts.test_code_question_evaluator"],
        "critical": True,
    },
    {
        "id": "answer_evaluator",
        "label": "AnswerEvaluator",
        "command": [sys.executable, "-m", "scripts.test_answer_evaluator"],
        "critical": True,
    },
    {
        "id": "answer_evaluator_report",
        "label": "AnswerEvaluator report",
        "command": [sys.executable, "-m", "scripts.evaluation.check_answer_evaluator_report"],
        "critical": True,
    },
    {
        "id": "teaching_strategy_evidence_upgrade",
        "label": "Teaching strategy evidence upgrade",
        "command": [sys.executable, "-m", "scripts.test_teaching_strategy_evidence_upgrade"],
        "critical": True,
    },
    {
        "id": "teaching_strategy_upgrade_report",
        "label": "Teaching strategy upgrade report",
        "command": [sys.executable, "-m", "scripts.evaluation.check_teaching_strategy_upgrade_report"],
        "critical": True,
        "timeout_sec": 180,
    },
    {
        "id": "rag_grounding_checker",
        "label": "RAG grounding checker",
        "command": [sys.executable, "-m", "scripts.test_rag_grounding_checker"],
        "critical": True,
    },
    {
        "id": "rag_grounding_report",
        "label": "RAG grounding report",
        "command": [sys.executable, "-m", "scripts.evaluation.check_rag_grounding_report"],
        "critical": True,
    },
    {
        "id": "cognitutor_lm_connector",
        "label": "CogniTutorLM connector test",
        "command": [sys.executable, "-m", "tutor.generation.cognitutor_lm_connector"],
        "critical": True,
        "allow_warning_status": True,
    },
    {
        "id": "integrated_tutor_dry_run",
        "label": "Integrated tutor dry run",
        "command": [
            sys.executable,
            "-m",
            "tutor.system.run_integrated_tutor_once",
            "--learner_id",
            "14",
            "--reward_dry_run",
        ],
        "critical": True,
        "timeout_sec": 240,
    },
]

KNOWN_WARNING_PATTERNS = [
    "DKT model artifacts not found",
    "fallback_cumulative",
    "HF",
    "unauthenticated",
    "BertModel",
    "position_ids",
    "InconsistentVersionWarning",
    "oneDNN custom operations are on",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_status(text: str) -> str | None:
    for line in text.splitlines():
        clean = line.strip()
        if clean.startswith("STATUS:"):
            return clean.split(":", 1)[1].strip().lower()
    return None


def _tail(text: str, max_chars: int = 6000) -> str:
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def _has_known_warning(text: str) -> bool:
    lowered = text.lower()
    return any(pattern.lower() in lowered for pattern in KNOWN_WARNING_PATTERNS)


def _run_command(item: dict[str, Any]) -> dict[str, Any]:
    timeout_sec = int(item.get("timeout_sec", 120))
    started_at = _now_iso()
    try:
        completed = subprocess.run(
            item["command"],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        combined = "\n".join(part for part in [stdout.strip(), stderr.strip()] if part)
        status_line = _extract_status(combined)
        known_warning = _has_known_warning(combined)

        passed = completed.returncode == 0
        if status_line == "error":
            passed = False
        elif status_line == "warning" and not item.get("allow_warning_status"):
            passed = False

        return {
            "id": item["id"],
            "label": item["label"],
            "command": " ".join(item["command"]),
            "critical": bool(item.get("critical", True)),
            "passed": passed,
            "returncode": completed.returncode,
            "status_line": status_line,
            "known_warning_observed": known_warning,
            "started_at": started_at,
            "finished_at": _now_iso(),
            "stdout_tail": _tail(stdout),
            "stderr_tail": _tail(stderr),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "id": item["id"],
            "label": item["label"],
            "command": " ".join(item["command"]),
            "critical": bool(item.get("critical", True)),
            "passed": False,
            "returncode": None,
            "status_line": "timeout",
            "known_warning_observed": False,
            "started_at": started_at,
            "finished_at": _now_iso(),
            "stdout_tail": _tail(exc.stdout or ""),
            "stderr_tail": _tail(exc.stderr or f"Timed out after {timeout_sec} seconds."),
        }
    except Exception as exc:
        return {
            "id": item["id"],
            "label": item["label"],
            "command": " ".join(item["command"]),
            "critical": bool(item.get("critical", True)),
            "passed": False,
            "returncode": None,
            "status_line": "error",
            "known_warning_observed": False,
            "started_at": started_at,
            "finished_at": _now_iso(),
            "stdout_tail": "",
            "stderr_tail": str(exc),
        }


def _overall_status(results: list[dict[str, Any]]) -> str:
    critical_failures = [result for result in results if result["critical"] and not result["passed"]]
    if critical_failures:
        return "error"
    warnings = [
        result
        for result in results
        if result.get("status_line") == "warning" or result.get("known_warning_observed")
    ]
    if warnings:
        return "warning"
    return "success"


def _build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Full Backend Smoke Test Report",
        "",
        f"Generated at: {report['generated_at']}",
        "",
        f"Overall status: `{report['overall_status']}`",
        f"Passed: {report['passed_count']}/{report['total_count']}",
        "",
        "## Results",
        "",
        "| Module | Passed | Status | Return code | Known warning |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for result in report["results"]:
        lines.append(
            "| {label} | {passed} | {status_line} | {returncode} | {known_warning_observed} |".format(
                label=result["label"],
                passed=result["passed"],
                status_line=result.get("status_line"),
                returncode=result.get("returncode"),
                known_warning_observed=result.get("known_warning_observed"),
            )
        )

    if report["failed"]:
        lines.extend(["", "## Failures", ""])
        for result in report["failed"]:
            lines.append(f"- {result['label']}: `{result.get('status_line')}` return code `{result.get('returncode')}`")

    lines.extend(
        [
            "",
            "## Allowed Warning Patterns",
            "",
        ]
    )
    for pattern in KNOWN_WARNING_PATTERNS:
        lines.append(f"- {pattern}")

    lines.extend(
        [
            "",
            "## Status",
            "",
            "```text",
            f"STATUS: {report['overall_status']}",
            "MODULE: full_backend_smoke_test",
            f"PASSED: {report['passed_count']}/{report['total_count']}",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def build_report() -> dict[str, Any]:
    results = [_run_command(item) for item in COMMANDS]
    passed_count = sum(1 for result in results if result["passed"])
    failed = [result for result in results if not result["passed"]]
    report = {
        "overall_status": _overall_status(results),
        "module": "full_backend_smoke_test",
        "generated_at": _now_iso(),
        "total_count": len(results),
        "passed_count": passed_count,
        "failed_count": len(failed),
        "failed": failed,
        "known_warning_patterns": KNOWN_WARNING_PATTERNS,
        "results": results,
    }
    return report


def main() -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)

    report = build_report()
    OUTPUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    OUTPUT_MD.write_text(_build_markdown(report), encoding="utf-8")

    print(f"STATUS: {report['overall_status']}")
    print("MODULE: full_backend_smoke_test")
    print(f"PASSED: {report['passed_count']}/{report['total_count']}")
    print(f"JSON_REPORT: {OUTPUT_JSON}")
    print(f"MD_REPORT: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
