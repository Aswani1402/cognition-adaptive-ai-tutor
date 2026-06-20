"""Generate final RL/policy evaluation charts from existing report JSON files."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt


JSON_DIR = Path("evaluation_outputs/json")
REPORT_DIR = Path("evaluation_outputs/reports")
CHART_DIR = Path("evaluation_outputs/charts")
JSON_REPORT = JSON_DIR / "rl_visualization_report.json"
MD_REPORT = REPORT_DIR / "rl_visualization_report.md"


def load_json(name: str) -> dict[str, Any]:
    path = JSON_DIR / name
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_bar(labels: list[str], values: list[float], title: str, ylabel: str, path: Path, rotate: int = 25) -> bool:
    if not labels or not values:
        return False
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(labels, values)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.tick_params(axis="x", rotation=rotate)
    ax.set_ylim(0, max(1.0, max(values) * 1.15))
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return True


def main() -> None:
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    CHART_DIR.mkdir(parents=True, exist_ok=True)

    model_comparison = load_json("rl_model_comparison_report.json")
    safe_masking = load_json("rl_safe_action_masking_report.json")
    offline = load_json("rl_offline_policy_evaluation_report.json")
    counterfactual = load_json("rl_counterfactual_safety_report.json")
    created: list[str] = []
    warnings: list[str] = []

    metrics = model_comparison.get("model_metrics") or offline.get("metrics") or {}
    models = list(metrics.keys())
    rewards = [float((metrics.get(model) or {}).get("average_predicted_reward", 0.0) or 0.0) for model in models]
    if save_bar(models, rewards, "RL Model Comparison by Average Predicted Reward", "Average predicted reward", CHART_DIR / "rl_model_comparison.png"):
        created.append("rl_model_comparison.png")
    else:
        warnings.append("RL model metric summaries were unavailable.")

    mask_results = safe_masking.get("model_results") or {}
    mask_models = list(mask_results.keys())
    before_rates = [float(((mask_results.get(model) or {}).get("before") or {}).get("bad_action_rate", 0.0) or 0.0) for model in mask_models]
    after_rates = [float(((mask_results.get(model) or {}).get("after") or {}).get("bad_action_rate", 0.0) or 0.0) for model in mask_models]
    if mask_models:
        fig, ax = plt.subplots(figsize=(9, 5))
        x_positions = list(range(len(mask_models)))
        width = 0.35
        ax.bar([x - width / 2 for x in x_positions], before_rates, width, label="Before mask")
        ax.bar([x + width / 2 for x in x_positions], after_rates, width, label="After mask")
        ax.set_title("RL Safe Action Masking Summary")
        ax.set_ylabel("Bad action rate")
        ax.set_xticks(x_positions)
        ax.set_xticklabels(mask_models, rotation=25)
        ax.legend()
        ax.set_ylim(0, max(1.0, max(before_rates + after_rates) * 1.15))
        fig.tight_layout()
        fig.savefig(CHART_DIR / "rl_safe_action_masking_summary.png")
        plt.close(fig)
        created.append("rl_safe_action_masking_summary.png")
    else:
        warnings.append("RL safe-action masking results were unavailable.")

    offline_metrics = offline.get("metrics") or metrics
    reward_values = [
        float((model_metrics or {}).get("average_predicted_reward", 0.0) or 0.0)
        for model_metrics in offline_metrics.values()
    ]
    if reward_values:
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.hist(reward_values, bins=min(6, max(3, len(reward_values))))
        ax.set_title("RL Reward Distribution Across Models")
        ax.set_xlabel("Average predicted reward")
        ax.set_ylabel("Model count")
        fig.tight_layout()
        fig.savefig(CHART_DIR / "rl_reward_distribution.png")
        plt.close(fig)
        created.append("rl_reward_distribution.png")
    else:
        warnings.append("RL reward distribution data was unavailable.")

    action_counts: Counter[str] = Counter()
    for key in ["policy_action_distribution", "bandit_action_distribution", "dqn_action_distribution"]:
        action_counts.update(offline.get(key) or {})
    if not action_counts:
        for model_metric in offline_metrics.values():
            action_counts.update((model_metric or {}).get("action_distribution") or {})
    if save_bar(list(action_counts.keys()), [float(v) for v in action_counts.values()], "RL Action Distribution", "Action count", CHART_DIR / "rl_action_distribution.png", rotate=35):
        created.append("rl_action_distribution.png")
    else:
        warnings.append("RL action distribution data was unavailable.")

    status = "success" if len(created) == 4 and not warnings else "warning"
    report = {
        "status": status,
        "module": "rl_visualization_report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "chart_dir": str(CHART_DIR),
        "charts": created,
        "warnings": warnings,
        "counterfactual_scenario_count": (counterfactual.get("summary") or {}).get("scenario_count"),
        "source_reports": [
            "evaluation_outputs/json/rl_model_comparison_report.json",
            "evaluation_outputs/json/rl_safe_action_masking_report.json",
            "evaluation_outputs/json/rl_counterfactual_safety_report.json",
            "evaluation_outputs/json/rl_offline_policy_evaluation_report.json",
        ],
    }
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    MD_REPORT.write_text(
        "# RL Visualization Report\n\n"
        f"- Status: {status}\n"
        f"- Charts generated: {len(created)}\n"
        + "\n".join(f"- `{chart}`" for chart in created)
        + ("\n\n## Warnings\n" + "\n".join(f"- {w}" for w in warnings) if warnings else "\n"),
        encoding="utf-8",
    )

    print(f"STATUS: {status}")
    print("MODULE: rl_visualization_report")
    print(f"CHART_DIR: {CHART_DIR}")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
