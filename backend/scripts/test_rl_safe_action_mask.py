from __future__ import annotations

from tutor.policy.rl_safe_action_mask import apply_rl_safe_action_mask


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _run_case(name: str, state: dict, action: dict | str, expected: set[str], masked: bool = True) -> None:
    output = apply_rl_safe_action_mask(state, action)
    print(f"{name}: {output['original_action']} -> {output['masked_action']}")
    _assert(output["status"] == "success", f"{name}: status failed")
    _assert(output["safe"] is True, f"{name}: masked action is not safe")
    _assert(output["was_masked"] is masked, f"{name}: unexpected mask flag")
    _assert(output["masked_action"] in expected, f"{name}: unexpected masked action {output['masked_action']}")


def main() -> None:
    base = {
        "mastery_score": 0.6,
        "behaviour_risk": 0.2,
        "behaviour_risk_label": "low_risk",
        "fused_score": 0.7,
        "fused_label": "partial",
        "review_due": False,
        "promotion_confidence": 0.7,
        "concept_domain_match": True,
    }

    _run_case(
        "low_mastery_advanced",
        {**base, "mastery_score": 0.2, "promotion_confidence": 0.3, "fused_score": 0.42, "fused_label": "needs_reteaching"},
        {"model_name": "dqn", "action_label": "advanced_hard", "strategy": "advanced", "difficulty": "hard"},
        {"remedial_easy", "same_level_change_view_or_practice"},
    )
    _run_case(
        "high_behaviour_risk_advanced",
        {**base, "behaviour_risk": 0.85, "behaviour_risk_label": "high_risk"},
        "advanced_hard",
        {"practice_easy", "remedial_easy"},
    )
    _run_case(
        "review_due_advanced",
        {**base, "review_due": True},
        "advanced_hard",
        {"review"},
    )
    _run_case(
        "low_promotion_level_up",
        {**base, "promotion_confidence": 0.3},
        "level_up",
        {"practice_medium"},
    )
    _run_case(
        "domain_mismatch",
        {**base, "concept_domain_match": False, "current_domain": "Python", "selected_domain": "Data Structures"},
        "practice_medium",
        {"block_or_fallback"},
    )
    _run_case(
        "safe_practice_unchanged",
        base,
        "practice_medium",
        {"practice_medium"},
        masked=False,
    )
    _run_case(
        "high_mastery_advanced_allowed",
        {**base, "mastery_score": 0.9, "fused_score": 0.9, "fused_label": "mastered", "promotion_confidence": 0.85},
        "advanced_hard",
        {"advanced_hard"},
        masked=False,
    )

    print("STATUS: success")
    print("MODULE: rl_safe_action_mask_test")


if __name__ == "__main__":
    main()
