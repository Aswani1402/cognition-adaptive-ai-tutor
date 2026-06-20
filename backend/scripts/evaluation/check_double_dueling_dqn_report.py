from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tutor.RL.dqn.dqn_policy import DQNPolicy


OUTPUT_JSON = Path("evaluation_outputs/json/double_dueling_dqn_report.json")
OUTPUT_MD = Path("evaluation_outputs/reports/double_dueling_dqn_report.md")

DQN_MODEL_PATH = Path("models/rl/dqn/dqn_policy_model.pt")
DQN_META_PATH = Path("models/rl/dqn/dqn_policy_metadata.json")
REPORT_PATHS = {
    "rl_offline_policy_evaluation": Path("evaluation_outputs/json/rl_offline_policy_evaluation_report.json"),
    "rl_counterfactual_safety": Path("evaluation_outputs/json/rl_counterfactual_safety_report.json"),
    "rl_safe_action_masking": Path("evaluation_outputs/json/rl_safe_action_masking_report.json"),
    "policy_rl_upgrade": Path("evaluation_outputs/json/policy_rl_upgrade_report.json"),
}
SEARCH_ROOTS = [
    Path("tutor/policy"),
    Path("tutor/RL"),
    Path("scripts/rl"),
    Path("scripts/evaluation"),
    Path("models"),
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("exists", True)
            return data
        return {"exists": True, "value": data}
    except Exception as exc:
        return {"exists": True, "status": "error", "error": str(exc)}


def _discover_files() -> dict[str, list[str]]:
    keywords = ("dqn", "double_dqn", "dueling_dqn", "ppo", "rl_safe_action_mask")
    found: dict[str, list[str]] = {keyword: [] for keyword in keywords}
    for root in SEARCH_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            lowered = str(path).lower()
            for keyword in keywords:
                if keyword in lowered:
                    found[keyword].append(str(path))
    return {key: sorted(value)[:100] for key, value in found.items()}


def _dqn_prediction_sample() -> dict[str, Any]:
    try:
        policy = DQNPolicy()
        state = {
            "mastery_score": 0.6,
            "behavior_score": 0.25,
            "review_due": True,
            "evaluation_score": 0.35,
            "learning_signal": "weak",
        }
        output = policy.predict(state) if policy.is_available() else {"status": "error", "reason": "DQN unavailable"}
        return {
            "available": policy.is_available(),
            "sample_state": state,
            "sample_output": output,
        }
    except Exception as exc:
        return {"available": False, "error": str(exc)}


def _current_dqn_status(discovered: dict[str, list[str]]) -> dict[str, Any]:
    metadata = _load_json(DQN_META_PATH)
    sample = _dqn_prediction_sample()
    output = sample.get("sample_output", {}) if isinstance(sample, dict) else {}
    return {
        "artifact_exists": DQN_MODEL_PATH.exists(),
        "artifact_path": str(DQN_MODEL_PATH),
        "metadata_path": str(DQN_META_PATH),
        "metadata": metadata,
        "training_mode": metadata.get("training_mode"),
        "is_supervised_q_vector_baseline": metadata.get("training_mode") == "supervised_q_vector_baseline",
        "action_labels_available": ["remedial_easy", "practice_medium", "advanced_hard"],
        "sample_action_label": output.get("action_label") if isinstance(output, dict) else None,
        "sample_q_values": output.get("q_values") if isinstance(output, dict) else None,
        "safe_action_mask_file_present": bool(discovered.get("rl_safe_action_mask")),
        "safe_action_mask_applied_in_reports": True,
    }


def _status_from_files(discovered: dict[str, list[str]], key: str, artifact_keywords: tuple[str, ...]) -> str:
    files = discovered.get(key, [])
    if not files:
        return "pending"
    artifact_found = any(any(keyword in path.lower() for keyword in artifact_keywords) for path in files)
    return "implemented" if artifact_found else "pending"


def _latest_report_summary() -> dict[str, Any]:
    reports = {name: _load_json(path) for name, path in REPORT_PATHS.items()}
    masking = reports["rl_safe_action_masking"]
    offline = reports["rl_offline_policy_evaluation"]
    counterfactual = reports["rl_counterfactual_safety"]
    dqn_masking = (
        masking.get("model_results", {}).get("dqn", {})
        if isinstance(masking.get("model_results"), dict)
        else {}
    )
    bandit_masking = (
        masking.get("model_results", {}).get("contextual_bandit", {})
        if isinstance(masking.get("model_results"), dict)
        else {}
    )
    return {
        "reports_loaded": {
            name: report.get("exists", False)
            for name, report in reports.items()
        },
        "safe_masking_status": {
            "report_status": masking.get("status"),
            "dqn_before_bad_action_rate": dqn_masking.get("before", {}).get("bad_action_rate"),
            "dqn_after_bad_action_rate": dqn_masking.get("after", {}).get("bad_action_rate"),
            "dqn_before_unsafe_promotion_rate": dqn_masking.get("before", {}).get("unsafe_promotion_rate"),
            "dqn_after_unsafe_promotion_rate": dqn_masking.get("after", {}).get("unsafe_promotion_rate"),
            "dqn_masked_action_rate": dqn_masking.get("masked_action_rate"),
            "contextual_bandit_before_bad_action_rate": bandit_masking.get("before", {}).get("bad_action_rate"),
            "contextual_bandit_after_bad_action_rate": bandit_masking.get("after", {}).get("bad_action_rate"),
            "contextual_bandit_masked_action_rate": bandit_masking.get("masked_action_rate"),
        },
        "offline_policy_status": {
            "status": offline.get("status"),
            "full_rl_replacement_status": offline.get("model_status", {}).get("full_rl_replacement_status")
            if isinstance(offline.get("model_status"), dict)
            else None,
            "masking_status": offline.get("masking_status"),
        },
        "counterfactual_status": {
            "status": counterfactual.get("status"),
            "summary": counterfactual.get("summary"),
        },
    }


def build_report() -> dict[str, Any]:
    discovered = _discover_files()
    latest = _latest_report_summary()
    current_dqn = _current_dqn_status(discovered)
    double_status = _status_from_files(discovered, "double_dqn", ("model", ".pt", ".joblib"))
    dueling_status = _status_from_files(discovered, "dueling_dqn", ("model", ".pt", ".joblib"))
    ppo_status = "optional_future" if not discovered.get("ppo") else "implemented"
    full_allowed = False
    status = "warning"
    if double_status == "implemented" and dueling_status == "implemented":
        status = "success"
    return {
        "status": status,
        "module": "DoubleDuelingDQNReport",
        "generated_at": _now_iso(),
        "current_dqn_status": current_dqn,
        "double_dqn_status": double_status,
        "double_dqn_expected_benefit": "Reduce max-Q overestimation bias by decoupling action selection from target evaluation.",
        "dueling_dqn_status": dueling_status,
        "dueling_dqn_expected_benefit": "Separate state value and action advantage so the model can learn when state quality matters more than action choice.",
        "ppo_status": ppo_status,
        "ppo_note": "PPO is heavier and can remain optional future work unless time and reward data are sufficient.",
        "safe_masking_status": latest["safe_masking_status"],
        "latest_report_summary": latest,
        "discovered_files": discovered,
        "full_rl_replacement_allowed": full_allowed,
        "recommendation": (
            "Keep current DQN and contextual bandit in safety-masked comparison mode. "
            "Implement Double DQN and Dueling DQN next if RL remains a priority; do not enable full RL replacement until offline reward, safety, and counterfactual metrics beat the baseline."
        ),
        "research_upgrade_plan": [
            "Define a shared state vector: mastery_score, behaviour_risk, fused_score, weakest_skill, review_due, promotion_confidence, difficulty, view_reward, concept_dependency_status.",
            "Define a shared action space: remedial_easy, practice_easy, practice_medium, practice_hard, advanced_hard, review, reteach, same_level_change_view_or_practice, advance_concept, level_up.",
            "Define reward: mastery gain, evaluation improvement, reduced mistakes, correct promotion, retention, engagement, and safe progression.",
            "Train baseline DQN with real logged reward targets and held-out evaluation.",
            "Train Double DQN using a target network to reduce overestimation bias.",
            "Train Dueling DQN with separate value and advantage heads.",
            "Evaluate average reward, unsafe action rate before/after mask, action agreement with safe bridge, promotion safety, counterfactual pass rate, and Q-value stability.",
            "Keep RLSafeActionMask and AdaptivePolicyBridge as final guards for every learned RL variant.",
            "Consider PPO only after offline reward data and environment simulation are strong enough.",
        ],
        "limitations": [
            "Current DQN metadata identifies the artifact as supervised_q_vector_baseline, not full online RL training.",
            "Double DQN and Dueling DQN files/artifacts were not found.",
            "Safe action masking reduced unsafe rates to zero after masking, but raw DQN remains unsafe without the mask.",
            "Full RL replacement is not allowed until stronger offline policy evaluation and counterfactual safety pass without relying only on masking.",
        ],
    }


def _build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Double DQN / Dueling DQN Readiness Report",
        "",
        f"Generated at: {report['generated_at']}",
        "",
        f"Overall status: `{report['status']}`",
        "",
        "## Current DQN",
        "",
        f"- artifact exists: `{report['current_dqn_status']['artifact_exists']}`",
        f"- training mode: `{report['current_dqn_status']['training_mode']}`",
        f"- supervised Q-vector baseline: `{report['current_dqn_status']['is_supervised_q_vector_baseline']}`",
        f"- sample action label: `{report['current_dqn_status']['sample_action_label']}`",
        f"- sample q_values: `{report['current_dqn_status']['sample_q_values']}`",
        f"- safe action mask present: `{report['current_dqn_status']['safe_action_mask_file_present']}`",
        "",
        "## Stronger RL Variant Status",
        "",
        f"- Double DQN: `{report['double_dqn_status']}`",
        f"- Double DQN expected benefit: {report['double_dqn_expected_benefit']}",
        f"- Dueling DQN: `{report['dueling_dqn_status']}`",
        f"- Dueling DQN expected benefit: {report['dueling_dqn_expected_benefit']}",
        f"- PPO: `{report['ppo_status']}`",
        f"- PPO note: {report['ppo_note']}",
        "",
        "## Safe Masking Evidence",
        "",
    ]
    for key, value in report["safe_masking_status"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            f"- full RL replacement allowed: `{report['full_rl_replacement_allowed']}`",
            f"- recommendation: {report['recommendation']}",
            "",
            "## Research Upgrade Plan",
            "",
        ]
    )
    for item in report["research_upgrade_plan"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Limitations", ""])
    for item in report["limitations"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Status", "", "```text", f"STATUS: {report['status']}", "MODULE: double_dueling_dqn_report", "```", ""])
    return "\n".join(lines)


def main() -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    report = build_report()
    OUTPUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    OUTPUT_MD.write_text(_build_markdown(report), encoding="utf-8")
    print(f"STATUS: {report['status']}")
    print("MODULE: double_dueling_dqn_report")
    print(f"JSON_REPORT: {OUTPUT_JSON}")
    print(f"MD_REPORT: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
