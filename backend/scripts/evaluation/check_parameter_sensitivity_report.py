from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
JSON_REPORT = PROJECT_ROOT / "evaluation_outputs" / "json" / "parameter_sensitivity_report.json"
MD_REPORT = PROJECT_ROOT / "evaluation_outputs" / "reports" / "parameter_sensitivity_report.md"


SYNTHETIC_LEARNER_STATES = [
    {
        "learner_id": "s_low_mastery_high_risk",
        "mastery": 0.25,
        "fused_score": 0.32,
        "behaviour_risk": 0.82,
        "promotion_confidence": 0.28,
        "grounding_score": 0.45,
        "retrieval_rank": 5,
        "review_due": True,
    },
    {
        "learner_id": "s_partial_mastery_medium_risk",
        "mastery": 0.52,
        "fused_score": 0.55,
        "behaviour_risk": 0.62,
        "promotion_confidence": 0.58,
        "grounding_score": 0.61,
        "retrieval_rank": 3,
        "review_due": False,
    },
    {
        "learner_id": "s_high_mastery_low_risk",
        "mastery": 0.84,
        "fused_score": 0.86,
        "behaviour_risk": 0.18,
        "promotion_confidence": 0.82,
        "grounding_score": 0.78,
        "retrieval_rank": 1,
        "review_due": False,
    },
    {
        "learner_id": "s_borderline_score",
        "mastery": 0.68,
        "fused_score": 0.49,
        "behaviour_risk": 0.36,
        "promotion_confidence": 0.52,
        "grounding_score": 0.52,
        "retrieval_rank": 4,
        "review_due": True,
    },
    {
        "learner_id": "s_good_score_high_risk",
        "mastery": 0.74,
        "fused_score": 0.79,
        "behaviour_risk": 0.77,
        "promotion_confidence": 0.71,
        "grounding_score": 0.66,
        "retrieval_rank": 2,
        "review_due": False,
    },
    {
        "learner_id": "s_low_mastery_good_behaviour",
        "mastery": 0.38,
        "fused_score": 0.63,
        "behaviour_risk": 0.22,
        "promotion_confidence": 0.47,
        "grounding_score": 0.39,
        "retrieval_rank": 8,
        "review_due": True,
    },
]


def _teaching_decision(
    state: dict[str, Any],
    *,
    fused_threshold: float = 0.5,
    mastery_low: float = 0.4,
    mastery_high: float = 0.75,
    behaviour_risk_threshold: float = 0.7,
) -> str:
    if state["behaviour_risk"] >= behaviour_risk_threshold:
        return "supportive_revision"
    if state["fused_score"] < fused_threshold:
        return "reteach"
    if state["mastery"] < mastery_low:
        return "easy_support"
    if state["mastery"] >= mastery_high and state["fused_score"] >= fused_threshold:
        return "challenge_or_progress"
    return "medium_practice"


def _rag_decision(state: dict[str, Any], *, grounding_threshold: float, top_k: int) -> str:
    retrieved = state["retrieval_rank"] <= top_k
    grounded = state["grounding_score"] >= grounding_threshold
    if retrieved and grounded:
        return "grounded_answer"
    if retrieved:
        return "retrieved_but_low_grounding"
    return "fallback_or_expand_search"


def _rl_action(
    state: dict[str, Any],
    *,
    promotion_threshold: float,
    behaviour_risk_threshold: float,
    mastery_threshold: float,
) -> str:
    if state["behaviour_risk"] >= behaviour_risk_threshold:
        return "masked_supportive_action"
    if state["mastery"] < mastery_threshold:
        return "blocked_promotion_low_mastery"
    if state["promotion_confidence"] >= promotion_threshold:
        return "promote_or_unlock"
    return "continue_practice"


def _revision_priority(
    state: dict[str, Any],
    *,
    fused_high_priority_threshold: float,
    mastery_revision_threshold: float,
) -> str:
    score = 0
    if state["review_due"]:
        score += 1
    if state["fused_score"] < fused_high_priority_threshold:
        score += 2
    if state["mastery"] < mastery_revision_threshold:
        score += 2
    if state["behaviour_risk"] >= 0.7:
        score += 1
    if score >= 4:
        return "high"
    if score >= 2:
        return "medium"
    return "low"


def _distribution(values: list[str]) -> dict[str, int]:
    return dict(Counter(values))


def _sensitivity_note(default_distribution: dict[str, int], changed: dict[float | int, dict[str, int]]) -> str:
    return (
        f"Default distribution is {default_distribution}. "
        f"Changing the parameter shifts decisions as: {changed}."
    )


def teaching_strategy_experiments() -> list[dict[str, Any]]:
    experiments = []

    configs = [
        {
            "parameter_name": "teaching.fused_score_threshold",
            "tested_values": [0.4, 0.5, 0.6],
            "selected_default": 0.5,
            "kwargs_name": "fused_threshold",
            "justification": "0.5 separates clearly weak/partial fused evaluation from acceptable performance while avoiding excessive remediation.",
            "risk_of_too_low": "Weak learners may progress before misconceptions are corrected.",
            "risk_of_too_high": "Too many learners are sent to reteaching, slowing progression and increasing repetition.",
        },
        {
            "parameter_name": "teaching.mastery_low_threshold",
            "tested_values": [0.3, 0.4, 0.5],
            "selected_default": 0.4,
            "kwargs_name": "mastery_low",
            "justification": "0.4 marks low KT mastery where easy/supportive instruction is safer than medium practice.",
            "risk_of_too_low": "Low-mastery learners may receive practice that is too hard.",
            "risk_of_too_high": "Learners with partial understanding may be held in support mode too long.",
        },
        {
            "parameter_name": "teaching.mastery_high_threshold",
            "tested_values": [0.7, 0.75, 0.8],
            "selected_default": 0.75,
            "kwargs_name": "mastery_high",
            "justification": "0.75 requires strong mastery before challenge/progression but still allows capable learners to move forward.",
            "risk_of_too_low": "Learners may reach challenge/progression with fragile mastery.",
            "risk_of_too_high": "Strong learners may be over-practiced before progression.",
        },
        {
            "parameter_name": "teaching.behaviour_risk_threshold",
            "tested_values": [0.6, 0.7, 0.8],
            "selected_default": 0.7,
            "kwargs_name": "behaviour_risk_threshold",
            "justification": "0.7 treats only clearly risky behaviour as requiring supportive teaching.",
            "risk_of_too_low": "Normal hesitation may be over-classified as risk.",
            "risk_of_too_high": "Struggling learners may not receive support early enough.",
        },
    ]

    for config in configs:
        changed: dict[float, dict[str, int]] = {}
        for value in config["tested_values"]:
            kwargs = {config["kwargs_name"]: value}
            decisions = [_teaching_decision(state, **kwargs) for state in SYNTHETIC_LEARNER_STATES]
            changed[value] = _distribution(decisions)
        default_distribution = changed[config["selected_default"]]
        experiments.append(
            {
                "section": "teaching_strategy_thresholds",
                **{k: v for k, v in config.items() if k != "kwargs_name"},
                "observed_effect": _sensitivity_note(default_distribution, changed),
                "decision_distributions": changed,
            }
        )

    return experiments


def rag_experiments() -> list[dict[str, Any]]:
    experiments = []

    grounding_changed: dict[float, dict[str, int]] = {}
    for value in [0.4, 0.5, 0.6, 0.7]:
        decisions = [
            _rag_decision(state, grounding_threshold=value, top_k=5)
            for state in SYNTHETIC_LEARNER_STATES
        ]
        grounding_changed[value] = _distribution(decisions)
    experiments.append(
        {
            "section": "rag_thresholds",
            "parameter_name": "rag.grounding_threshold",
            "tested_values": [0.4, 0.5, 0.6, 0.7],
            "observed_effect": _sensitivity_note(grounding_changed[0.5], grounding_changed),
            "selected_default": 0.5,
            "justification": "0.5 is a balanced minimum for grounded answer generation; lower values allow weak grounding and higher values increase fallback.",
            "risk_of_too_low": "Answers may be generated from weak or accidental matches.",
            "risk_of_too_high": "Many useful answers may be blocked or downgraded to fallback.",
            "decision_distributions": grounding_changed,
        }
    )

    top_k_changed: dict[int, dict[str, int]] = {}
    for value in [3, 5, 8]:
        decisions = [
            _rag_decision(state, grounding_threshold=0.5, top_k=value)
            for state in SYNTHETIC_LEARNER_STATES
        ]
        top_k_changed[value] = _distribution(decisions)
    experiments.append(
        {
            "section": "rag_thresholds",
            "parameter_name": "rag.top_k",
            "tested_values": [3, 5, 8],
            "observed_effect": _sensitivity_note(top_k_changed[5], top_k_changed),
            "selected_default": 5,
            "justification": "top_k=5 balances retrieval coverage and noise for concept-level doubt answering.",
            "risk_of_too_low": "Relevant evidence can be missed, increasing fallback rate.",
            "risk_of_too_high": "More irrelevant sections can enter context, reducing precision and increasing latency.",
            "decision_distributions": top_k_changed,
        }
    )
    return experiments


def rl_experiments() -> list[dict[str, Any]]:
    experiments = []
    defaults = {
        "promotion_threshold": 0.6,
        "behaviour_risk_threshold": 0.7,
        "mastery_threshold": 0.4,
    }
    configs = [
        {
            "parameter_name": "rl.promotion_confidence_threshold",
            "tested_values": [0.5, 0.6, 0.7],
            "selected_default": 0.6,
            "kwargs_name": "promotion_threshold",
            "justification": "0.6 requires moderate confidence before promotion while keeping progression achievable.",
            "risk_of_too_low": "Promotion may happen before the evidence is strong enough.",
            "risk_of_too_high": "Progression becomes conservative and may reduce motivation.",
        },
        {
            "parameter_name": "rl.behaviour_risk_threshold",
            "tested_values": [0.6, 0.7, 0.8],
            "selected_default": 0.7,
            "kwargs_name": "behaviour_risk_threshold",
            "justification": "0.7 masks unsafe promotion only when behaviour risk is clearly high.",
            "risk_of_too_low": "Safe actions may be over-masked for normal learners.",
            "risk_of_too_high": "High-risk learners may get promoted or challenged too early.",
        },
        {
            "parameter_name": "rl.mastery_threshold",
            "tested_values": [0.3, 0.4, 0.5],
            "selected_default": 0.4,
            "kwargs_name": "mastery_threshold",
            "justification": "0.4 is a minimum mastery gate below which promotion is blocked.",
            "risk_of_too_low": "Promotion can occur with weak knowledge evidence.",
            "risk_of_too_high": "Learners may need unnecessary extra practice before unlocking progress.",
        },
    ]
    for config in configs:
        changed: dict[float, dict[str, int]] = {}
        for value in config["tested_values"]:
            kwargs = {**defaults, config["kwargs_name"]: value}
            actions = [_rl_action(state, **kwargs) for state in SYNTHETIC_LEARNER_STATES]
            changed[value] = _distribution(actions)
        experiments.append(
            {
                "section": "rl_safe_action_thresholds",
                **{k: v for k, v in config.items() if k != "kwargs_name"},
                "observed_effect": _sensitivity_note(changed[config["selected_default"]], changed),
                "decision_distributions": changed,
            }
        )
    return experiments


def revision_experiments() -> list[dict[str, Any]]:
    experiments = []
    fused_changed: dict[float, dict[str, int]] = {}
    for value in [0.4, 0.5, 0.6]:
        priorities = [
            _revision_priority(state, fused_high_priority_threshold=value, mastery_revision_threshold=0.5)
            for state in SYNTHETIC_LEARNER_STATES
        ]
        fused_changed[value] = _distribution(priorities)
    experiments.append(
        {
            "section": "revision_scheduler_thresholds",
            "parameter_name": "revision.fused_score_high_priority_threshold",
            "tested_values": [0.4, 0.5, 0.6],
            "observed_effect": _sensitivity_note(fused_changed[0.5], fused_changed),
            "selected_default": 0.5,
            "justification": "0.5 aligns high-priority revision with weak fused evaluation.",
            "risk_of_too_low": "Some learners with partial performance may not receive timely revision.",
            "risk_of_too_high": "Revision load increases and can crowd out new learning.",
            "decision_distributions": fused_changed,
        }
    )

    mastery_changed: dict[float, dict[str, int]] = {}
    for value in [0.4, 0.5, 0.6]:
        priorities = [
            _revision_priority(state, fused_high_priority_threshold=0.5, mastery_revision_threshold=value)
            for state in SYNTHETIC_LEARNER_STATES
        ]
        mastery_changed[value] = _distribution(priorities)
    experiments.append(
        {
            "section": "revision_scheduler_thresholds",
            "parameter_name": "revision.mastery_revision_threshold",
            "tested_values": [0.4, 0.5, 0.6],
            "observed_effect": _sensitivity_note(mastery_changed[0.5], mastery_changed),
            "selected_default": 0.5,
            "justification": "0.5 catches weak-to-partial mastery for revision without scheduling every medium learner.",
            "risk_of_too_low": "Low mastery learners near the boundary may miss revision.",
            "risk_of_too_high": "Too many medium learners receive revision cards, increasing workload.",
            "decision_distributions": mastery_changed,
        }
    )
    return experiments


def build_report() -> dict[str, Any]:
    experiments = (
        teaching_strategy_experiments()
        + rag_experiments()
        + rl_experiments()
        + revision_experiments()
    )

    defaults = {
        "teaching.fused_score_threshold": 0.5,
        "teaching.mastery_low_threshold": 0.4,
        "teaching.mastery_high_threshold": 0.75,
        "teaching.behaviour_risk_threshold": 0.7,
        "rag.grounding_threshold": 0.5,
        "rag.top_k": 5,
        "rl.promotion_confidence_threshold": 0.6,
        "rl.behaviour_risk_threshold": 0.7,
        "rl.mastery_threshold": 0.4,
        "revision.fused_score_high_priority_threshold": 0.5,
        "revision.mastery_revision_threshold": 0.5,
    }

    action_counts = Counter()
    for state in SYNTHETIC_LEARNER_STATES:
        action_counts[
            _teaching_decision(
                state,
                fused_threshold=defaults["teaching.fused_score_threshold"],
                mastery_low=defaults["teaching.mastery_low_threshold"],
                mastery_high=defaults["teaching.mastery_high_threshold"],
                behaviour_risk_threshold=defaults["teaching.behaviour_risk_threshold"],
            )
        ] += 1

    return {
        "status": "success",
        "module": "parameter_sensitivity_report",
        "method": "Synthetic no-write ablation over representative learner states.",
        "sample_state_count": len(SYNTHETIC_LEARNER_STATES),
        "sample_state_summary": {
            "mastery_mean": round(mean(state["mastery"] for state in SYNTHETIC_LEARNER_STATES), 4),
            "fused_score_mean": round(mean(state["fused_score"] for state in SYNTHETIC_LEARNER_STATES), 4),
            "behaviour_risk_mean": round(mean(state["behaviour_risk"] for state in SYNTHETIC_LEARNER_STATES), 4),
            "default_teaching_action_distribution": dict(action_counts),
        },
        "selected_defaults": defaults,
        "experiments": experiments,
        "limitations": [
            "This report uses representative synthetic states, not a full replay of all learner histories.",
            "Observed effects are decision-distribution changes, not causal learning outcome estimates.",
            "Next upgrade should replay thresholds against saved learner histories and compare retention/progression outcomes.",
        ],
    }


def write_reports(report: dict[str, Any]) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# Parameter Sensitivity / Ablation Report",
        "",
        f"Status: **{report['status']}**",
        "",
        f"Method: {report['method']}",
        f"Sample states: {report['sample_state_count']}",
        "",
        "## Selected Defaults",
        "",
    ]
    for key, value in report["selected_defaults"].items():
        lines.append(f"- {key}: {value}")

    lines.extend(["", "## Experiments", ""])
    for experiment in report["experiments"]:
        lines.extend(
            [
                f"### {experiment['parameter_name']}",
                "",
                f"- Section: {experiment['section']}",
                f"- Tested values: {experiment['tested_values']}",
                f"- Selected default: {experiment['selected_default']}",
                f"- Observed effect: {experiment['observed_effect']}",
                f"- Justification: {experiment['justification']}",
                f"- Risk if too low: {experiment['risk_of_too_low']}",
                f"- Risk if too high: {experiment['risk_of_too_high']}",
                "",
            ]
        )

    lines.extend(["## Limitations", ""])
    for item in report["limitations"]:
        lines.append(f"- {item}")

    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_report()
    write_reports(report)
    print(f"STATUS: {report['status']}")
    print("MODULE: parameter_sensitivity_report")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
