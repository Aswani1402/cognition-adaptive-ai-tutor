import json
from pathlib import Path

from tutor.system.run_integrated_tutor_once import run_integrated_tutor_once


OUTPUT_JSON = Path("evaluation_outputs/json/integrated_pipeline_keys_inspection.json")


def _summarize_dict(value, depth=0, max_depth=2):
    if depth > max_depth:
        return "MAX_DEPTH"

    if isinstance(value, dict):
        return {
            key: _summarize_dict(val, depth + 1, max_depth)
            for key, val in value.items()
        }

    if isinstance(value, list):
        return {
            "type": "list",
            "length": len(value),
            "sample": _summarize_dict(value[0], depth + 1, max_depth)
            if value
            else None,
        }

    return {
        "type": type(value).__name__,
        "value": value,
    }


def main() -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    output = run_integrated_tutor_once(
        learner_id="14",
        learner_profile="weak",
        reward_dry_run=True,
    )

    top_level_keys = sorted(output.keys())

    multi_evidence = output.get("multi_evidence_output", {})
    demo_summary = output.get("demo_summary", {})
    policy_output = output.get("policy_output", {})
    teaching_strategy_output = output.get("teaching_strategy_output", {})

    report = {
        "status": "success",
        "module": "IntegratedPipelineKeysInspection",
        "top_level_keys": top_level_keys,
        "demo_summary_keys": sorted(demo_summary.keys())
        if isinstance(demo_summary, dict)
        else [],
        "multi_evidence_keys": sorted(multi_evidence.keys())
        if isinstance(multi_evidence, dict)
        else [],
        "multi_evidence_summary": _summarize_dict(multi_evidence, max_depth=3),
        "policy_output_summary": _summarize_dict(policy_output, max_depth=2),
        "teaching_strategy_output_summary": _summarize_dict(
            teaching_strategy_output,
            max_depth=2,
        ),
        "possible_kt_behaviour_values": {
            "demo_mastery_score": demo_summary.get("mastery_score")
            if isinstance(demo_summary, dict)
            else None,
            "demo_behavior_label": demo_summary.get("behavior_label")
            if isinstance(demo_summary, dict)
            else None,
            "multi_evidence_mastery_score": (
                multi_evidence.get("evidence_summary", {}).get("mastery_score")
                if isinstance(multi_evidence, dict)
                else None
            ),
            "multi_evidence_behavior_label": (
                multi_evidence.get("evidence_summary", {}).get("behavior_label")
                if isinstance(multi_evidence, dict)
                else None
            ),
            "multi_evidence_behavior_score": (
                multi_evidence.get("evidence_summary", {}).get("behavior_score")
                if isinstance(multi_evidence, dict)
                else None
            ),
        },
    }

    OUTPUT_JSON.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    print("\nINTEGRATED PIPELINE KEYS INSPECTION")
    print("status:", report["status"])
    print("module:", report["module"])

    print("\nTOP LEVEL KEYS")
    for key in top_level_keys:
        print("-", key)

    print("\nMULTI EVIDENCE KEYS")
    for key in report["multi_evidence_keys"]:
        print("-", key)

    print("\nPOSSIBLE KT/BEHAVIOUR VALUES")
    for key, value in report["possible_kt_behaviour_values"].items():
        print(key + ":", value)

    print("\nSaved JSON:", OUTPUT_JSON)

    print("\nSTATUS: success")
    print("MODULE: integrated_pipeline_keys_inspection")


if __name__ == "__main__":
    main()