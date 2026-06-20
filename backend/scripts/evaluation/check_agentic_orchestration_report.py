from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from tutor.agents.orchestration_trace import build_agentic_orchestration_trace


PROJECT_ROOT = Path(__file__).resolve().parents[2]
JSON_REPORT = PROJECT_ROOT / "evaluation_outputs" / "json" / "agentic_orchestration_report.json"
MD_REPORT = PROJECT_ROOT / "evaluation_outputs" / "reports" / "agentic_orchestration_report.md"
REPORT_DIR = PROJECT_ROOT / "evaluation_outputs" / "json"

RECENT_REPORTS = [
    "final_backend_report.json",
    "xai_model_explanation_report.json",
    "notebook_memory_revision_report.json",
    "rag_grounding_report.json",
    "rl_model_comparison_report.json",
    "dependency_adaptive_path_report.json",
]


def _extract_json(stdout: str) -> dict[str, Any]:
    start = stdout.find("{")
    end = stdout.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    try:
        return json.loads(stdout[start : end + 1])
    except Exception:
        return {}


def _run_integrated_pipeline() -> dict[str, Any]:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "tutor.system.run_integrated_tutor_once",
            "--learner_id",
            "14",
            "--reward_dry_run",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )
    return {
        "returncode": completed.returncode,
        "payload": _extract_json(completed.stdout),
        "stderr_tail": completed.stderr[-3000:],
    }


def _load_recent_reports() -> dict[str, Any]:
    loaded: dict[str, Any] = {}
    for filename in RECENT_REPORTS:
        path = REPORT_DIR / filename
        key = filename.replace(".json", "")
        if not path.exists():
            loaded[key] = {"exists": False}
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            loaded[key] = {"exists": True, "error": str(exc)}
            continue
        loaded[key] = {
            "exists": True,
            "status": data.get("status") or data.get("overall_status"),
            "module": data.get("module"),
            "summary_fields": _summary_fields(data),
        }
    return loaded


def _summary_fields(data: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "current_active_source",
        "current_policy_status",
        "rl_status",
        "frontend_ready",
        "full_rl_replacement_allowed",
        "query_count",
        "revision_scheduler_output",
    ]
    summary: dict[str, Any] = {}
    for key in keys:
        if key in data:
            value = data[key]
            if key == "revision_scheduler_output" and isinstance(value, dict):
                summary["revision_priority"] = value.get("revision_priority")
            else:
                summary[key] = value
    return summary


def _write_reports(report: dict[str, Any]) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    trace = report["agentic_trace"]
    lines = [
        "# Agentic Orchestration Report",
        "",
        f"Status: **{report['status']}**",
        "",
        "## Overall Flow",
        "",
        f"`{trace.get('final_flow')}`",
        "",
        trace.get("report_summary", ""),
        "",
        "## Agent Steps",
        "",
        "| Step | Agent | Status | Primary Decision | Primary Output |",
        "|---:|---|---|---|---|",
    ]
    cards_by_step = {card["step"]: card for card in trace.get("frontend_trace_cards", [])}
    for step in trace.get("trace_steps", []):
        card = cards_by_step.get(step["step"], {})
        lines.append(
            f"| {step.get('step')} | {step.get('agent')} | {step.get('status')} | "
            f"{card.get('primary_decision', '')} | {card.get('primary_output', '')} |"
        )

    lines.extend(["", "## Dependencies", ""])
    for dependency in trace.get("agent_dependencies", []):
        lines.append(f"- {dependency}")

    lines.extend(["", "## Loaded Evidence Reports", ""])
    for name, data in report["loaded_reports"].items():
        lines.append(f"- {name}: exists={data.get('exists')} status={data.get('status')}")

    lines.extend(["", "## Frontend Trace Card Format", ""])
    lines.append("Each card includes: step, agent, title, status, primary_decision, primary_output, reason.")

    lines.extend(["", "## Limitations", ""])
    for limitation in report["limitations"]:
        lines.append(f"- {limitation}")

    lines.extend(["", "## Future Upgrades", ""])
    for step in report["future_upgrades"]:
        lines.append(f"- {step}")

    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_report() -> dict[str, Any]:
    pipeline = _run_integrated_pipeline()
    payload = pipeline.get("payload") or {}
    trace = build_agentic_orchestration_trace(payload)
    loaded_reports = _load_recent_reports()

    limitations = [
        "The trace is observational and report/dashboard-oriented; it does not yet act as a planner controller.",
        "Trace steps are reconstructed from integrated pipeline outputs, not persisted in a dedicated trace table.",
        "Optional model comparison outputs remain shadow/comparison mode where marked by their source modules.",
    ]
    future_upgrades = [
        "Add a real planner agent that can select tools and recover from module disagreement.",
        "Persist every orchestration trace step in SQLite for audit and replay.",
        "Add teacher dashboard visualizations for agent dependencies, evidence, and disagreement.",
        "Add automated recovery policies when policy, RL, teaching strategy, or RAG safety agents disagree.",
    ]

    status = "success"
    if pipeline.get("returncode") != 0 or not payload:
        status = "warning"
        limitations.append("Integrated pipeline payload was incomplete; trace used available fallback fields.")
    if any(step.get("status") == "warning" for step in trace.get("trace_steps", [])):
        # Missing optional fields do not fail the report, but they are useful to surface.
        status = "warning" if status != "success" else "success"

    return {
        "status": status,
        "module": "agentic_orchestration_report",
        "pipeline_run": {
            "returncode": pipeline.get("returncode"),
            "parsed_payload": bool(payload),
            "stderr_tail": pipeline.get("stderr_tail"),
        },
        "agentic_trace": trace,
        "loaded_reports": loaded_reports,
        "frontend_dashboard_ready": bool(trace.get("frontend_trace_cards")),
        "limitations": limitations,
        "future_upgrades": future_upgrades,
    }


def main() -> None:
    report = build_report()
    _write_reports(report)
    print(f"STATUS: {report['status']}")
    print("MODULE: agentic_orchestration_report")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
