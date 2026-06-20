from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from tutor.memory.learner_notebook_memory import LearnerNotebookMemory
from tutor.memory.revision_scheduler import RevisionScheduler


PROJECT_ROOT = Path(__file__).resolve().parents[2]
JSON_REPORT = PROJECT_ROOT / "evaluation_outputs" / "json" / "notebook_memory_revision_report.json"
MD_REPORT = PROJECT_ROOT / "evaluation_outputs" / "reports" / "notebook_memory_revision_report.md"


def _nested_get(payload: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return default if current is None else current


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _extract_json_from_stdout(stdout: str) -> dict[str, Any]:
    text = stdout.strip()
    if not text:
        return {}
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    try:
        return json.loads(text[start : end + 1])
    except Exception:
        return {}


def _run_integrated_pipeline() -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        "tutor.system.run_integrated_tutor_once",
        "--learner_id",
        "14",
        "--reward_dry_run",
    ]
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )
    payload = _extract_json_from_stdout(completed.stdout)
    return {
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-3000:],
        "stderr_tail": completed.stderr[-3000:],
        "payload": payload,
    }


def _extract_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    demo_summary = payload.get("demo_summary", {}) if isinstance(payload, dict) else {}
    concept_id = str(
        demo_summary.get("adaptive_path_resolved_concept_id")
        or demo_summary.get("final_concept")
        or _nested_get(payload, "concept_resolution_output", "concept_id")
        or "1"
    )
    concept_name = str(
        demo_summary.get("concept_name")
        or _nested_get(payload, "concept_resolution_output", "concept_name")
        or _nested_get(payload, "current_teaching_content", "concept_name")
        or "Variables"
    )
    domain = str(
        demo_summary.get("domain")
        or _nested_get(payload, "concept_resolution_output", "domain")
        or _nested_get(payload, "current_teaching_content", "domain")
        or "Python"
    )

    kt_data = _nested_get(payload, "knowledge_state", "data", "data", default={}) or {}
    behaviour = _nested_get(payload, "behaviour_state", "data", default={}) or {}
    forgetting_data = _nested_get(payload, "forgetting_state", "data", default={}) or {}
    evaluation_fusion = payload.get("evaluation_fusion_output") or _nested_get(payload, "evaluation_output", "evaluation_fusion", default={}) or {}
    mistake = payload.get("mistake_analysis_output") or {}
    learner_memory = payload.get("learner_notebook_memory_output") or {}

    return {
        "learner_id": "14",
        "concept_id": concept_id,
        "concept_name": concept_name,
        "domain": domain,
        "mastery_score": _safe_float(
            kt_data.get("predicted_mastery_last")
            or demo_summary.get("predicted_mastery_last")
            or _nested_get(payload, "knowledge_state", "data", "predicted_mastery_last"),
            0.0,
        ),
        "fused_score": _safe_float(evaluation_fusion.get("fused_score") or demo_summary.get("fused_score"), 1.0),
        "fused_label": str(evaluation_fusion.get("fused_label") or demo_summary.get("fused_label") or ""),
        "weakest_skill": str(evaluation_fusion.get("weakest_skill") or demo_summary.get("weakest_skill") or ""),
        "dominant_mistake_type": str(
            mistake.get("dominant_mistake_type")
            or learner_memory.get("dominant_mistake_type")
            or demo_summary.get("dominant_mistake_type")
            or ""
        ),
        "mistake_type_counts": mistake.get("mistake_type_counts") or learner_memory.get("mistake_type_counts") or {},
        "behaviour_risk": _safe_float(behaviour.get("behavior_risk") or demo_summary.get("behavior_risk"), 0.0),
        "behaviour_risk_label": str(behaviour.get("behavior_risk_label") or demo_summary.get("behavior_risk_label") or ""),
        "review_due": bool(forgetting_data.get("review_queue") or demo_summary.get("review_queue")),
        "review_queue": forgetting_data.get("review_queue", []),
        "recent_scores": [],
        "notebook_summary": learner_memory.get("notebook_summary") or demo_summary.get("notebook_summary"),
        "next_practice_queue": learner_memory.get("next_practice_queue") or demo_summary.get("next_practice_queue") or [],
    }


def _latest_memory_summary(learner_id: str = "14") -> dict[str, Any]:
    try:
        return LearnerNotebookMemory().get_latest_memory(learner_id=learner_id, limit=3)
    except Exception as exc:
        return {"status": "error", "module": "LearnerNotebookMemory", "reason": str(exc), "memories": []}


def _write_reports(report: dict[str, Any]) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    scheduler = report["revision_scheduler_output"]
    packet = scheduler.get("frontend_revision_packet", {})
    lines = [
        "# Notebook Memory + Revision Scheduler Report",
        "",
        f"Status: **{report['status']}**",
        "",
        "## Learner Memory Status",
        "",
        f"- LearnerNotebookMemory status: {report['learner_memory_status'].get('status')}",
        f"- Latest memory count inspected: {report['learner_memory_status'].get('memory_count', 0)}",
        f"- Notebook summary available: {bool(report['evidence'].get('notebook_summary'))}",
        "",
        "## Revision Decision",
        "",
        f"- Revision priority: {scheduler.get('revision_priority')}",
        f"- Reason: {scheduler.get('revision_reason')}",
        f"- Recommended views: {', '.join(scheduler.get('recommended_revision_views', []))}",
        f"- Recommended question types: {', '.join(scheduler.get('recommended_question_types', []))}",
        "",
        "## Frontend Packet",
        "",
        f"- Today focus: {packet.get('today_focus')}",
        f"- Next action: {packet.get('next_revision_action')}",
        f"- Card count: {len(packet.get('cards', []))}",
        f"- Practice queue count: {len(packet.get('practice_queue', []))}",
        "",
        "## Spaced Repetition",
        "",
    ]
    for card in scheduler.get("spaced_repetition_cards", []):
        lines.append(f"- {card.get('interval')}: {card.get('prompt')}")

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
    evidence = _extract_evidence(payload)
    learner_memory_status = _latest_memory_summary(evidence["learner_id"])
    scheduler_output = RevisionScheduler().build_revision_plan(evidence)

    limitations = [
        "RevisionScheduler is deterministic and evidence-based, not a trained memory policy.",
        "The scheduler is audit-only/read-only here; it does not add new revision rows to SQLite yet.",
        "Spaced repetition intervals are rule-based and should later be personalized from retention outcomes.",
        "Semantic learner notebook search and long-term trend dashboards are future upgrades.",
    ]
    future_upgrades = [
        "Add SQLite revision_schedule and revision_card tables for persistent due-date tracking.",
        "Add semantic learner notebook search over mistakes, explanations, and weak concepts.",
        "Use long-term mastery/behaviour trends to personalize review intervals.",
        "Generate learner study guides and teacher dashboard memory timelines.",
    ]

    status = "success"
    if pipeline.get("returncode") != 0 or not payload:
        status = "warning"
        limitations.append("Integrated pipeline payload could not be fully parsed; report used safe defaults where needed.")
    if learner_memory_status.get("status") != "success":
        status = "warning"

    return {
        "status": status,
        "module": "notebook_memory_revision_report",
        "pipeline_run": {
            "returncode": pipeline.get("returncode"),
            "parsed_payload": bool(payload),
            "stderr_tail": pipeline.get("stderr_tail"),
        },
        "learner_memory_status": {
            "status": learner_memory_status.get("status"),
            "module": learner_memory_status.get("module"),
            "learner_id": learner_memory_status.get("learner_id"),
            "memory_count": learner_memory_status.get("memory_count", 0),
            "latest_memory_preview": (learner_memory_status.get("memories") or [{}])[0] if learner_memory_status.get("memories") else {},
        },
        "evidence": evidence,
        "revision_scheduler_output": scheduler_output,
        "frontend_ready": bool(scheduler_output.get("frontend_revision_packet")),
        "limitations": limitations,
        "future_upgrades": future_upgrades,
    }


def main() -> None:
    report = build_report()
    _write_reports(report)
    print(f"STATUS: {report['status']}")
    print("MODULE: notebook_memory_revision_report")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
