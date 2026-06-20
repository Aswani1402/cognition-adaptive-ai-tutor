import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT_DIR / "outputs" / "final_reports"
OUTPUT_JSON = OUTPUT_DIR / "run_all_cognitutor_lm_tests_report.json"
OUTPUT_MD = OUTPUT_DIR / "run_all_cognitutor_lm_tests_report.md"


COMMANDS = [
    "python -m scripts.audit_concept_resources",
    "python -m scripts.generate_tutor_artifacts",
    "python -m scripts.inspect_generated_tutor_artifacts",
    "python -m scripts.inspect_assessment_question_bank",
    "python -m src.answer_evaluator",
    "python -m src.safe_code_runner",
    "python -m src.learner_memory_service",
    "python -m src.teaching_view_progression_service",
    "python -m src.doubt_handler_service",
    "python -m src.tutor_lm_service",
    "python -m scripts.generate_cognitutor_lm_quality_fix_report",
    "python -m scripts.test_tutor_lm_service_quality",
    "python -m scripts.test_cognitutor_lm_task_coverage_quality",
    "python -m scripts.test_cognitutor_lm_task_coverage",
    "python -m scripts.test_cognitutor_lm_teaching_richness",
    "python -m scripts.test_cognitutor_lm_assessment_quality",
    "python -m scripts.test_cognitutor_lm_flashcard_mindmap_quality",
    "python -m scripts.test_cognitutor_lm_hint_feedback_doubt_quality",
    "python -m scripts.test_cognitutor_lm_voice_script_quality",
    "python -m scripts.test_variation_diversity",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def tail_text(value: str, max_chars: int = 3000) -> str:
    value = value or ""
    if len(value) <= max_chars:
        return value
    return value[-max_chars:]


def command_to_args(command: str) -> List[str]:
    parts = command.split()
    if parts[:2] == ["python", "-m"]:
        return [sys.executable, "-m", parts[2]]
    return parts


def run_command(command: str) -> Dict[str, Any]:
    print(f"\nRunning: {command}")

    completed = subprocess.run(
        command_to_args(command),
        cwd=ROOT_DIR,
        text=True,
        capture_output=True,
    )

    status = "pass" if completed.returncode == 0 else "fail"

    return {
        "command": command,
        "status": status,
        "return_code": completed.returncode,
        "stdout_tail": tail_text(completed.stdout),
        "stderr_tail": tail_text(completed.stderr),
        "timestamp": now_iso(),
    }


def build_markdown_report(report: Dict[str, Any]) -> str:
    lines = [
        "# CogniTutorLM Final Smoke Test Report",
        "",
        f"Generated at: `{report['generated_at']}`",
        f"Overall status: `{report['overall_status']}`",
        f"Stop on failure: `{report['stop_on_failure']}`",
        "",
        "## Commands",
        "",
    ]

    for item in report["results"]:
        lines.append(f"### {item['command']}")
        lines.append("")
        lines.append(f"- Status: `{item['status']}`")
        lines.append(f"- Return code: `{item['return_code']}`")
        lines.append(f"- Timestamp: `{item['timestamp']}`")

        if item.get("stdout_tail"):
            lines.append("")
            lines.append("**Stdout tail**")
            lines.append("")
            lines.append("```text")
            lines.append(item["stdout_tail"])
            lines.append("```")

        if item.get("stderr_tail"):
            lines.append("")
            lines.append("**Stderr tail**")
            lines.append("")
            lines.append("```text")
            lines.append(item["stderr_tail"])
            lines.append("```")

        lines.append("")

    return "\n".join(lines)


def run_all(stop_on_failure: bool = True) -> Dict[str, Any]:
    results = []

    for command in COMMANDS:
        result = run_command(command)
        results.append(result)

        if stop_on_failure and result["status"] == "fail":
            break

    overall_status = "PASS" if all(item["status"] == "pass" for item in results) and len(results) == len(COMMANDS) else "FAIL"

    return {
        "generated_at": now_iso(),
        "stop_on_failure": stop_on_failure,
        "overall_status": overall_status,
        "results": results,
    }


def main() -> None:
    stop_on_failure = "--no-stop" not in sys.argv
    report = run_all(stop_on_failure=stop_on_failure)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with OUTPUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    with OUTPUT_MD.open("w", encoding="utf-8") as f:
        f.write(build_markdown_report(report))

    print("\nFinal smoke test report saved.")
    print(f"JSON: {OUTPUT_JSON}")
    print(f"Markdown: {OUTPUT_MD}")
    print(f"Overall status: {report['overall_status']}")

    if report["overall_status"] != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
