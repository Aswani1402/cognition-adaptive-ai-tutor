from __future__ import annotations

from tutor.path.adaptive_path_validation import (
    build_frontend_path_output,
    load_concept_id_map,
    validate_selected_concept_id,
)
from tutor.system.run_integrated_tutor_once import run_integrated_tutor_once


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    concept_map = load_concept_id_map()
    _assert("1" in concept_map, "concept_id_map does not contain system concept 1")

    valid = validate_selected_concept_id(
        selected_concept_id="1",
        concept_id_map=concept_map,
        fallback_concept_id="1",
        current_domain="Python",
        dependency_output={"unlocked_concepts": ["1"], "blocked_concepts": []},
    )
    _assert(valid["valid"], f"valid concept did not pass: {valid}")
    _assert(not valid["fallback_used"], f"valid concept used fallback: {valid}")

    invalid = validate_selected_concept_id(
        selected_concept_id="9999",
        concept_id_map=concept_map,
        fallback_concept_id="1",
        current_domain="Python",
        dependency_output={"unlocked_concepts": ["1"], "blocked_concepts": []},
    )
    _assert(not invalid["valid"], f"invalid concept marked valid: {invalid}")
    _assert(invalid["fallback_used"], f"invalid concept did not fallback: {invalid}")
    _assert(invalid["resolved_concept_id"] == "1", f"invalid fallback wrong: {invalid}")

    selected_31 = validate_selected_concept_id(
        selected_concept_id="31",
        concept_id_map=concept_map,
        fallback_concept_id="1",
        current_domain="Python",
        dependency_output={"unlocked_concepts": ["1", "31"], "blocked_concepts": []},
    )
    _assert(
        selected_31["valid"] or selected_31["fallback_used"],
        f"31 was neither valid nor safely corrected: {selected_31}",
    )
    if concept_map.get("31", {}).get("domain") != "Python":
        _assert(selected_31["fallback_used"], f"31 should fallback due domain mismatch: {selected_31}")
        _assert(selected_31["resolved_concept_id"] == "1", f"31 fallback target wrong: {selected_31}")

    frontend_path = build_frontend_path_output(
        concept_id_map=concept_map,
        dependency_output={"unlocked_concepts": ["1"], "blocked_concepts": []},
        validation_output=selected_31,
        current_concept_id="1",
        mastery={"1": 0.6},
        review_queue=["1"],
        current_domain="Python",
    )
    _assert(frontend_path["path_nodes"], f"frontend path nodes missing: {frontend_path}")
    _assert(frontend_path["selected_node"], f"selected node missing: {frontend_path}")

    output = run_integrated_tutor_once(learner_id="14", reward_dry_run=True)
    summary = output.get("demo_summary", {})
    _assert(output.get("learner_id") == "14", "integrated pipeline did not run for learner 14")
    _assert("adaptive_path_selected" in summary, f"adaptive_path_selected missing: {summary}")
    _assert("adaptive_path_validation_status" in summary, f"validation status missing: {summary}")
    _assert("adaptive_path_resolved_concept_id" in summary, f"resolved concept missing: {summary}")
    _assert("adaptive_path_fallback_used" in summary, f"fallback flag missing: {summary}")
    _assert(
        summary.get("frontend_path_output") or output.get("frontend_path_output"),
        "frontend path output missing from integrated output",
    )

    selected = str(summary.get("adaptive_path_selected"))
    resolved_domain = summary.get("adaptive_path_resolved_domain")
    _assert(selected in concept_map, f"frontend received unmapped selected concept: {selected}")
    if summary.get("resolved_domain") and resolved_domain:
        _assert(
            str(summary.get("resolved_domain")).lower() == str(resolved_domain).lower(),
            f"frontend selected concept crosses domain: {summary}",
        )

    print("valid_concept:", valid)
    print("invalid_fallback:", invalid)
    print("selected_31_validation:", selected_31)
    print("integrated_adaptive_path_selected:", summary.get("adaptive_path_selected"))
    print("integrated_adaptive_path_original_selected:", summary.get("adaptive_path_original_selected"))
    print("integrated_adaptive_path_validation_status:", summary.get("adaptive_path_validation_status"))
    print("integrated_adaptive_path_fallback_used:", summary.get("adaptive_path_fallback_used"))
    print("frontend_path_node_count:", len((summary.get("frontend_path_output") or {}).get("path_nodes", [])))
    print("STATUS: success")
    print("MODULE: dependency_adaptive_path_validation_test")


if __name__ == "__main__":
    main()
