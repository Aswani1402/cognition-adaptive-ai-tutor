import json
from pathlib import Path
from datetime import datetime, timezone

from tutor.system.run_integrated_tutor_once import run_integrated_tutor_once


OUTPUT_JSON = Path("evaluation_outputs/json/kt_behaviour_runtime_outputs_report.json")
OUTPUT_MD = Path("evaluation_outputs/reports/kt_behaviour_runtime_outputs_report.md")


def _safe_dict(value):
    return value if isinstance(value, dict) else {}


def _extract_runtime_summary(full_output: dict, learner_id: str, profile: str | None) -> dict:
    demo_summary = _safe_dict(full_output.get("demo_summary"))
    kt_output = (
        full_output.get("knowledge_state_output")
        or full_output.get("knowledge_tracing_output")
        or full_output.get("kt_output")
        or {}
    )
    behaviour_output = (
        full_output.get("behaviour_output")
        or full_output.get("behavior_output")
        or full_output.get("behaviour_state_output")
        or full_output.get("behavior_state_output")
        or {}
    )

    multi_evidence_output = _safe_dict(full_output.get("multi_evidence_output"))
    evidence_summary = _safe_dict(multi_evidence_output.get("evidence_summary"))

    policy_output = _safe_dict(full_output.get("policy_output"))
    policy_data = _safe_dict(policy_output.get("data"))

    teaching_strategy_output = _safe_dict(full_output.get("teaching_strategy_output"))

    evaluation_fusion_output = _safe_dict(full_output.get("evaluation_fusion_output"))
    mistake_analysis_output = _safe_dict(full_output.get("mistake_analysis_output"))

    possible_mastery = [
        demo_summary.get("mastery_score"),
        evidence_summary.get("mastery_score"),
        kt_output.get("mastery"),
        kt_output.get("mastery_score"),
        kt_output.get("current_mastery"),
        kt_output.get("predicted_mastery"),
    ]

    mastery_value = next(
        (item for item in possible_mastery if item is not None),
        None,
    )

    possible_behaviour = [
        demo_summary.get("behavior_label"),
        demo_summary.get("behaviour_label"),
        evidence_summary.get("behavior_label"),
        evidence_summary.get("behaviour_label"),
        behaviour_output.get("behavior_label"),
        behaviour_output.get("behaviour_label"),
        behaviour_output.get("label"),
    ]

    behaviour_label = next(
        (item for item in possible_behaviour if item is not None),
        None,
    )

    possible_behaviour_score = [
        evidence_summary.get("behavior_score"),
        evidence_summary.get("behaviour_score"),
        behaviour_output.get("behavior_score"),
        behaviour_output.get("behaviour_score"),
        behaviour_output.get("score"),
    ]

    behaviour_score = next(
        (item for item in possible_behaviour_score if item is not None),
        None,
    )

    return {
        "learner_id": learner_id,
        "profile": profile,
        "status": full_output.get("status"),
        "demo_summary": {
            "learner_id": demo_summary.get("learner_id"),
            "concept_id": demo_summary.get("concept_id"),
            "concept_name": demo_summary.get("concept_name"),
            "teaching_view": demo_summary.get("teaching_view"),
            "assessment_types": demo_summary.get("assessment_types"),
            "rubric_verdict": demo_summary.get("rubric_verdict"),
            "fused_score": demo_summary.get("fused_score"),
            "recommended_learning_signal": demo_summary.get(
                "recommended_learning_signal"
            ),
        },
        "knowledge_tracing": {
            "found": bool(kt_output),
            "status": kt_output.get("status"),
            "module": kt_output.get("module"),
            "mastery_value": mastery_value,
            "raw_keys": sorted(list(kt_output.keys())) if isinstance(kt_output, dict) else [],
            "raw_output": kt_output,
        },
        "behaviour": {
            "found": bool(behaviour_output),
            "status": behaviour_output.get("status"),
            "module": behaviour_output.get("module"),
            "behaviour_label": behaviour_label,
            "behaviour_score": behaviour_score,
            "raw_keys": sorted(list(behaviour_output.keys())) if isinstance(behaviour_output, dict) else [],
            "raw_output": behaviour_output,
        },
        "multi_evidence": {
            "found": bool(multi_evidence_output),
            "status": multi_evidence_output.get("status"),
            "mastery_score": evidence_summary.get("mastery_score"),
            "behavior_label": evidence_summary.get("behavior_label")
            or evidence_summary.get("behaviour_label"),
            "behavior_score": evidence_summary.get("behavior_score")
            or evidence_summary.get("behaviour_score"),
            "evaluation_score": evidence_summary.get("evaluation_score"),
            "raw_evidence_summary": evidence_summary,
        },
        "policy": {
            "status": policy_output.get("status"),
            "strategy": policy_data.get("strategy"),
            "difficulty": policy_data.get("difficulty"),
            "next_concept_id": policy_data.get("next_concept_id"),
        },
        "teaching_strategy": {
            "status": teaching_strategy_output.get("status"),
            "teaching_view": teaching_strategy_output.get("teaching_view"),
            "assessment_types": teaching_strategy_output.get("assessment_types"),
            "difficulty": teaching_strategy_output.get("difficulty"),
        },
        "evaluation_fusion": {
            "status": evaluation_fusion_output.get("status"),
            "fused_score": evaluation_fusion_output.get("fused_score"),
            "fused_label": evaluation_fusion_output.get("fused_label"),
            "recommended_learning_signal": evaluation_fusion_output.get(
                "recommended_learning_signal"
            ),
            "weakest_skill": _safe_dict(
                evaluation_fusion_output.get("weakest_skill_signal")
            ).get("weakest_skill"),
        },
        "mistake_analysis": {
            "status": mistake_analysis_output.get("status"),
            "dominant_mistake_type": mistake_analysis_output.get(
                "dominant_mistake_type"
            ),
            "high_severity_count": mistake_analysis_output.get(
                "high_severity_count"
            ),
        },
    }


def _run_case(learner_id: str, profile: str | None) -> dict:
    try:
        output = run_integrated_tutor_once(
            learner_id=learner_id,
            learner_profile=profile,
            reward_dry_run=True,
        )

        return _extract_runtime_summary(
            full_output=output,
            learner_id=learner_id,
            profile=profile,
        )

    except Exception as exc:
        return {
            "learner_id": learner_id,
            "profile": profile,
            "status": "error",
            "reason": str(exc),
        }


def _compare_variation(cases: list[dict]) -> dict:
    mastery_values = [
        case.get("knowledge_tracing", {}).get("mastery_value")
        for case in cases
        if case.get("status") == "success"
    ]

    behaviour_labels = [
        case.get("behaviour", {}).get("behaviour_label")
        for case in cases
        if case.get("status") == "success"
    ]

    fused_scores = [
        case.get("evaluation_fusion", {}).get("fused_score")
        for case in cases
        if case.get("status") == "success"
    ]

    recommended_signals = [
        case.get("evaluation_fusion", {}).get("recommended_learning_signal")
        for case in cases
        if case.get("status") == "success"
    ]

    return {
        "mastery_values": mastery_values,
        "unique_mastery_values": sorted(
            {str(item) for item in mastery_values if item is not None}
        ),
        "behaviour_labels": behaviour_labels,
        "unique_behaviour_labels": sorted(
            {str(item) for item in behaviour_labels if item is not None}
        ),
        "fused_scores": fused_scores,
        "unique_fused_scores": sorted(
            {str(item) for item in fused_scores if item is not None}
        ),
        "recommended_learning_signals": recommended_signals,
        "unique_recommended_learning_signals": sorted(
            {str(item) for item in recommended_signals if item is not None}
        ),
        "mastery_varies": len({str(item) for item in mastery_values if item is not None}) > 1,
        "behaviour_varies": len({str(item) for item in behaviour_labels if item is not None}) > 1,
        "fusion_varies": len({str(item) for item in fused_scores if item is not None}) > 1,
    }


def _build_markdown(report: dict) -> str:
    lines = []

    lines.append("# KT + Behaviour Runtime Output Audit")
    lines.append("")
    lines.append(f"Generated at: {report['generated_at']}")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This audit checks the runtime outputs of Knowledge Tracing and Behaviour "
        "inside the integrated tutor pipeline before upgrading those modules."
    )
    lines.append("")
    lines.append("## Runtime Cases")
    lines.append("")
    lines.append(
        "| Learner | Profile | Status | KT Found | Mastery | Behaviour Found | Behaviour Label | Behaviour Score | Fused Score | Signal |"
    )
    lines.append("|---|---|---|---|---:|---|---|---:|---:|---|")

    for case in report["cases"]:
        kt = case.get("knowledge_tracing", {})
        behaviour = case.get("behaviour", {})
        fusion = case.get("evaluation_fusion", {})

        lines.append(
            f"| {case.get('learner_id')} | "
            f"{case.get('profile')} | "
            f"{case.get('status')} | "
            f"{kt.get('found')} | "
            f"{kt.get('mastery_value')} | "
            f"{behaviour.get('found')} | "
            f"{behaviour.get('behaviour_label')} | "
            f"{behaviour.get('behaviour_score')} | "
            f"{fusion.get('fused_score')} | "
            f"{fusion.get('recommended_learning_signal')} |"
        )

    lines.append("")
    lines.append("## Variation Check")
    lines.append("")
    variation = report["variation"]
    lines.append(f"- Mastery varies: {variation['mastery_varies']}")
    lines.append(f"- Behaviour varies: {variation['behaviour_varies']}")
    lines.append(f"- Fusion varies: {variation['fusion_varies']}")
    lines.append(f"- Unique mastery values: {variation['unique_mastery_values']}")
    lines.append(f"- Unique behaviour labels: {variation['unique_behaviour_labels']}")
    lines.append(f"- Unique fused scores: {variation['unique_fused_scores']}")
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "- If KT output is missing or mastery does not vary, inspect the KT runtime path."
    )
    lines.append(
        "- If behaviour output is missing or labels do not vary, inspect Behaviour runtime path."
    )
    lines.append(
        "- If fusion varies while KT/Behaviour do not, evaluation is adapting but KT/Behaviour may still be static."
    )
    lines.append("")
    lines.append("## Next Steps")
    lines.append("")
    lines.append("- Identify exactly which KT function is called by the pipeline.")
    lines.append("- Identify exactly which Behaviour function is called by the pipeline.")
    lines.append("- Create profile-based KT test cases.")
    lines.append("- Create profile-based Behaviour test cases.")
    lines.append("- Upgrade the weaker module first.")
    lines.append("")
    lines.append("## Status")
    lines.append("")
    lines.append("```text")
    lines.append("KT + Behaviour runtime output audit completed.")
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)

    cases_to_run = [
        ("14", None),
        ("14", "strong"),
        ("14", "average"),
        ("14", "weak"),
        ("14", "debug_weak"),
        ("14", "low_confidence"),
    ]

    cases = [
        _run_case(learner_id=learner_id, profile=profile)
        for learner_id, profile in cases_to_run
    ]

    report = {
        "status": "success",
        "module": "KTBehaviourRuntimeOutputAudit",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reward_dry_run": True,
        "cases": cases,
        "variation": _compare_variation(cases),
    }

    OUTPUT_JSON.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    OUTPUT_MD.write_text(
        _build_markdown(report),
        encoding="utf-8",
    )

    print("\nKT + BEHAVIOUR RUNTIME OUTPUT AUDIT")
    print("status:", report["status"])
    print("module:", report["module"])
    print("reward_dry_run:", report["reward_dry_run"])

    print("\nCASE SUMMARY")
    for case in cases:
        kt = case.get("knowledge_tracing", {})
        behaviour = case.get("behaviour", {})
        fusion = case.get("evaluation_fusion", {})

        print(
            "learner:",
            case.get("learner_id"),
            "| profile:",
            case.get("profile"),
            "| status:",
            case.get("status"),
            "| kt_found:",
            kt.get("found"),
            "| mastery:",
            kt.get("mastery_value"),
            "| behaviour_found:",
            behaviour.get("found"),
            "| behaviour_label:",
            behaviour.get("behaviour_label"),
            "| behaviour_score:",
            behaviour.get("behaviour_score"),
            "| fused_score:",
            fusion.get("fused_score"),
            "| signal:",
            fusion.get("recommended_learning_signal"),
        )

    print("\nVARIATION")
    print("mastery_varies:", report["variation"]["mastery_varies"])
    print("behaviour_varies:", report["variation"]["behaviour_varies"])
    print("fusion_varies:", report["variation"]["fusion_varies"])

    print("\nSaved JSON:", OUTPUT_JSON)
    print("Saved Markdown:", OUTPUT_MD)

    print("\nSTATUS: success")
    print("MODULE: kt_behaviour_runtime_output_audit")


if __name__ == "__main__":
    main()