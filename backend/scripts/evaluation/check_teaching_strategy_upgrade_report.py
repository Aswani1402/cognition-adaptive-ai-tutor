from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tutor.strategy.selector import recommend_evidence_aware_teaching_strategy


SELECTOR_PATH = Path("tutor/strategy/selector.py")
OUTPUT_JSON = Path("evaluation_outputs/json/teaching_strategy_upgrade_report.json")
OUTPUT_MD = Path("evaluation_outputs/reports/teaching_strategy_upgrade_report.md")

REQUIRED_EVIDENCE_TERMS = [
    "evaluation_fusion_output",
    "mistake_analysis_output",
    "knowledge_state",
    "mastery_score",
    "behaviour_risk",
    "behaviour_risk_label",
    "forgetting_state",
    "review_queue",
    "learner_notebook_memory_output",
    "memory_weaknesses",
    "adaptive_path_output",
    "view_performance_output",
    "evidence_used",
    "confidence",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _base_kwargs(**overrides: Any) -> dict[str, Any]:
    data = {
        "learner_id": "14",
        "concept_id": "1",
        "concept_name": "Variables",
        "policy_output": {
            "status": "success",
            "data": {
                "next_concept_id": "1",
                "difficulty": "medium",
                "strategy": "practice",
            },
        },
        "evaluation_output": {
            "overall_score": 0.62,
            "results": [],
        },
        "evaluation_fusion_output": {
            "status": "success",
            "fused_score": 0.62,
            "fused_label": "partial",
        },
        "mistake_analysis_output": {},
        "behaviour_state": {
            "data": {
                "behavior_risk": 0.22,
                "behavior_risk_label": "low_risk",
                "behavior_confidence": 0.70,
            }
        },
        "knowledge_state": {
            "data": {
                "predicted_mastery_last": 0.58,
                "written_state": {"1": 0.58},
            }
        },
        "forgetting_state": {
            "data": {
                "review_queue": [],
                "review_priority": {},
            }
        },
        "view_performance_output": {
            "logged": {
                "teaching_view": "definition_view",
                "reward": 0.62,
            }
        },
        "learner_notebook_memory_output": {},
        "xai_output": {},
        "adaptive_path_output": {},
        "conn": None,
        "log": False,
    }
    data.update(overrides)
    return data


def _selector_static_status() -> dict[str, Any]:
    report = {
        "status": "warning",
        "selector_exists": SELECTOR_PATH.exists(),
        "required_terms": REQUIRED_EVIDENCE_TERMS,
        "missing_terms": [],
    }
    if not SELECTOR_PATH.exists():
        report["status"] = "error"
        report["missing_terms"] = REQUIRED_EVIDENCE_TERMS
        return report

    text = SELECTOR_PATH.read_text(encoding="utf-8", errors="ignore")
    report["missing_terms"] = [term for term in REQUIRED_EVIDENCE_TERMS if term not in text]
    report["status"] = "success" if not report["missing_terms"] else "warning"
    return report


def _case_definitions() -> dict[str, dict[str, Any]]:
    return {
        "weak_output_prediction": _base_kwargs(
            evaluation_fusion_output={
                "fused_score": 0.48,
                "fused_label": "focused_remediation",
                "weakest_skill_signal": {"weakest_skill": "output_prediction"},
            }
        ),
        "syntax_debug_weakness": _base_kwargs(
            evaluation_fusion_output={
                "fused_score": 0.46,
                "fused_label": "focused_remediation",
                "weakest_skill_signal": {"weakest_skill": "debug"},
            },
            mistake_analysis_output={"dominant_mistake_type": "syntax_misunderstanding"},
        ),
        "low_mastery": _base_kwargs(
            knowledge_state={
                "data": {
                    "predicted_mastery_last": 0.30,
                    "written_state": {"1": 0.30},
                }
            },
            evaluation_fusion_output={"fused_score": 0.35, "fused_label": "needs_reteaching"},
        ),
        "high_mastery": _base_kwargs(
            policy_output={
                "status": "success",
                "data": {
                    "next_concept_id": "1",
                    "difficulty": "medium",
                    "strategy": "advanced",
                },
            },
            knowledge_state={
                "data": {
                    "predicted_mastery_last": 0.86,
                    "written_state": {"1": 0.86},
                }
            },
            evaluation_output={"overall_score": 0.88, "results": [{"assessment_type": "transfer", "score": 0.9}]},
            evaluation_fusion_output={"fused_score": 0.88, "fused_label": "mastered"},
        ),
        "high_behaviour_risk": _base_kwargs(
            policy_output={
                "status": "success",
                "data": {
                    "next_concept_id": "1",
                    "difficulty": "hard",
                    "strategy": "advanced",
                },
            },
            behaviour_state={
                "data": {
                    "behavior_risk": 0.82,
                    "behavior_risk_label": "high_risk",
                }
            },
            knowledge_state={
                "data": {
                    "predicted_mastery_last": 0.78,
                    "written_state": {"1": 0.78},
                }
            },
            evaluation_fusion_output={"fused_score": 0.78, "fused_label": "partial_strong"},
        ),
        "forgetting_due": _base_kwargs(
            forgetting_state={
                "data": {
                    "review_queue": ["1"],
                    "review_priority": {"1": 0.92},
                }
            }
        ),
        "missing_evidence": {
            "learner_id": "14",
            "concept_id": "1",
            "conn": None,
            "log": False,
        },
    }


def _summarize_output(output: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": output.get("status"),
        "teaching_view": output.get("teaching_view"),
        "difficulty": output.get("difficulty"),
        "assessment_types": output.get("assessment_types", []),
        "next_activity": output.get("next_activity"),
        "progression_action": output.get("progression_action"),
        "confidence": output.get("confidence"),
        "reason": output.get("reason"),
        "evidence_used": output.get("evidence_used", {}),
    }


def _validate_case(case_id: str, output: dict[str, Any]) -> tuple[bool, str]:
    view = output.get("teaching_view")
    difficulty = output.get("difficulty")
    assessment_types = output.get("assessment_types", [])
    progression = output.get("progression_action")
    next_activity = output.get("next_activity")

    if output.get("status") != "success":
        return False, "Selector did not return success."

    if case_id == "weak_output_prediction":
        return (
            view in {"code_view", "debug_view"} and "output_prediction" in assessment_types,
            "Weak output prediction should use code/debug view and output_prediction assessment.",
        )
    if case_id == "syntax_debug_weakness":
        return (
            view == "debug_view" and "debug" in assessment_types,
            "Syntax/debug weakness should use debug_view and debug assessment.",
        )
    if case_id == "low_mastery":
        return (
            difficulty == "easy" and view in {"definition_view", "step_by_step_view"},
            "Low mastery should use easy difficulty and supportive view.",
        )
    if case_id == "high_mastery":
        return (
            difficulty == "hard"
            and view in {"challenge_view", "transfer_view"}
            and progression in {"level_up", "advance_concept"},
            "High mastery should route to challenge/transfer and advance or level up.",
        )
    if case_id == "high_behaviour_risk":
        return (
            view not in {"transfer_view", "challenge_view"}
            and view in {"step_by_step_view", "revision_view", "misconception_view", "code_view"}
            and next_activity in {"supportive_practice", "reteach_with_support"}
            and progression in {"same_level_change_view_or_practice", "reteach"},
            "High behaviour risk should avoid transfer/challenge and use supportive practice.",
        )
    if case_id == "forgetting_due":
        return (
            view in {"revision_view", "flashcard_view"}
            and next_activity == "revision_before_new_content",
            "Forgetting due should route to revision/flashcard before new content.",
        )
    if case_id == "missing_evidence":
        return (bool(output.get("evidence_used")), "Missing evidence should fallback with evidence_used.")

    return True, "Case passed."


def _run_cases() -> dict[str, Any]:
    cases = []
    failures = []
    for case_id, kwargs in _case_definitions().items():
        try:
            output = recommend_evidence_aware_teaching_strategy(**kwargs)
            passed, expectation = _validate_case(case_id, output)
            summary = _summarize_output(output)
            summary["case_id"] = case_id
            summary["passed"] = passed
            summary["expectation"] = expectation
            cases.append(summary)
            if not passed:
                failures.append(f"{case_id}: {expectation}")
        except Exception as exc:
            failures.append(f"{case_id}: {exc}")
            cases.append({"case_id": case_id, "passed": False, "error": str(exc)})

    return {
        "status": "success" if not failures else "warning",
        "case_count": len(cases),
        "cases": cases,
        "failures": failures,
        "high_behaviour_risk_safe": next(
            (
                case.get("teaching_view") not in {"transfer_view", "challenge_view"}
                for case in cases
                if case.get("case_id") == "high_behaviour_risk"
            ),
            False,
        ),
    }


def _frontend_status() -> dict[str, Any]:
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "scripts.test_frontend_response_builder"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        combined = "\n".join([completed.stdout.strip(), completed.stderr.strip()]).strip()
        return {
            "status": "success" if completed.returncode == 0 else "warning",
            "called": True,
            "returncode": completed.returncode,
            "summary_lines": combined.splitlines()[:40],
        }
    except Exception as exc:
        return {
            "status": "warning",
            "called": False,
            "note": f"Frontend compatibility check skipped safely: {exc}",
        }


def _overall_status(parts: list[dict[str, Any]]) -> str:
    statuses = [part.get("status") for part in parts]
    if "error" in statuses:
        return "error"
    if "warning" in statuses:
        return "warning"
    return "success"


def _build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Teaching Strategy Upgrade Report",
        "",
        f"Generated at: {report['generated_at']}",
        "",
        f"Overall status: `{report['overall_status']}`",
        "",
        "## Static Evidence Check",
        "",
        f"- Selector exists: {report['static_status']['selector_exists']}",
        f"- Missing evidence terms: {report['static_status']['missing_terms']}",
        "",
        "## Sample Cases",
        "",
        "| Case | Passed | Difficulty | View | Assessment types | Next activity | Progression | Confidence |",
        "| --- | --- | --- | --- | --- | --- | --- | ---: |",
    ]
    for case in report["case_status"]["cases"]:
        lines.append(
            "| {case_id} | {passed} | {difficulty} | {teaching_view} | {assessment_types} | {next_activity} | {progression_action} | {confidence} |".format(
                case_id=case.get("case_id"),
                passed=case.get("passed"),
                difficulty=case.get("difficulty"),
                teaching_view=case.get("teaching_view"),
                assessment_types=case.get("assessment_types"),
                next_activity=case.get("next_activity"),
                progression_action=case.get("progression_action"),
                confidence=case.get("confidence"),
            )
        )

    lines.extend(
        [
            "",
            "## Key Checks",
            "",
            f"- High behaviour risk avoids transfer/challenge: {report['case_status']['high_behaviour_risk_safe']}",
            f"- Case failures: {report['case_status']['failures']}",
            f"- Frontend compatibility status: `{report['frontend_status']['status']}`",
            "",
            "## Limitations",
            "",
        ]
    )
    for limitation in report["limitations"]:
        lines.append(f"- {limitation}")

    lines.extend(
        [
            "",
            "## Status",
            "",
            "```text",
            f"STATUS: {report['overall_status']}",
            "MODULE: teaching_strategy_upgrade_report",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def build_report() -> dict[str, Any]:
    static_status = _selector_static_status()
    case_status = _run_cases()
    frontend_status = _frontend_status()

    return {
        "overall_status": _overall_status([static_status, case_status, frontend_status]),
        "module": "teaching_strategy_upgrade_report",
        "generated_at": _now_iso(),
        "static_status": static_status,
        "case_status": case_status,
        "frontend_status": frontend_status,
        "limitations": [
            "This is an evidence-aware baseline, not a trained replacement for the model-based selector.",
            "Model-based teaching strategy remains shadow/comparison-only until agreement and outcome evidence improve.",
            "Frontend compatibility is checked by running the compact frontend response builder test.",
        ],
    }


def main() -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)

    report = build_report()
    OUTPUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    OUTPUT_MD.write_text(_build_markdown(report), encoding="utf-8")

    print(f"STATUS: {report['overall_status']}")
    print("MODULE: teaching_strategy_upgrade_report")
    print(f"JSON_REPORT: {OUTPUT_JSON}")
    print(f"MD_REPORT: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
