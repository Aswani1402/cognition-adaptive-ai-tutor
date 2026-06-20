from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from tutor.policy.rl.double_dqn_policy import DoubleDQNPolicy, ReplayBuffer
from tutor.policy.rl.state_action_space import STATE_FEATURES, action_count, id_to_action
from tutor.policy.rl_safe_action_mask import apply_rl_safe_action_mask, detect_rl_action_violations


DATA_PATH = Path("evaluation_outputs/csv/rl_training_dataset.csv")
MODEL_PATH = Path("models/rl/double_dqn_policy.pt")
META_PATH = Path("models/rl/double_dqn_policy_meta.json")
JSON_REPORT = Path("evaluation_outputs/json/double_dqn_training_report.json")
MD_REPORT = Path("evaluation_outputs/reports/double_dqn_training_report.md")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_arrays() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, pd.DataFrame]:
    df = pd.read_csv(DATA_PATH)
    state_cols = STATE_FEATURES
    next_cols = [f"next_{feature}" for feature in STATE_FEATURES]
    states = df[state_cols].astype(float).to_numpy(dtype=np.float32)
    next_states = df[next_cols].astype(float).to_numpy(dtype=np.float32)
    actions = df["action_id"].astype(int).to_numpy()
    rewards = df["reward"].astype(float).to_numpy(dtype=np.float32)
    dones = df["done"].astype(float).to_numpy(dtype=np.float32)
    return states, actions, rewards, next_states, dones, df


def _state_dict_from_row(row: pd.Series) -> dict:
    return {
        "mastery_score": row["mastery_score"],
        "behaviour_risk": row["behaviour_risk"],
        "fused_score": row["fused_score"],
        "review_due": bool(row["review_due"]),
        "promotion_confidence": row["promotion_confidence"],
        "difficulty": "hard" if row["difficulty_encoded"] >= 0.75 else "medium" if row["difficulty_encoded"] >= 0.25 else "easy",
        "weakest_skill": "output_prediction" if row["weakest_skill_encoded"] >= 0.5 else "none",
        "behaviour_risk_label": "high_risk" if row["behaviour_risk_label_encoded"] >= 0.75 else "medium_risk" if row["behaviour_risk_label_encoded"] >= 0.25 else "low_risk",
        "concept_dependency_valid": bool(row["concept_dependency_valid"]),
        "view_reward": row["view_reward"],
    }


def _evaluate(policy: DoubleDQNPolicy, df: pd.DataFrame) -> dict:
    sample = df.head(min(500, len(df)))
    raw_bad = 0
    masked_bad = 0
    masked_count = 0
    action_counts: dict[str, int] = {}
    rewards = []
    for _, row in sample.iterrows():
        state = _state_dict_from_row(row)
        output = policy.predict_action(np.array([row[f] for f in STATE_FEATURES], dtype=np.float32))
        action = output["action_label"]
        action_counts[action] = action_counts.get(action, 0) + 1
        if detect_rl_action_violations(action, state):
            raw_bad += 1
        masked = apply_rl_safe_action_mask(state, action)
        if masked["was_masked"]:
            masked_count += 1
        if detect_rl_action_violations(masked["masked_action"], state):
            masked_bad += 1
        rewards.append(float(row["reward"]))
    n = max(1, len(sample))
    return {
        "evaluated_cases": len(sample),
        "average_logged_reward": round(sum(rewards) / n, 4),
        "raw_unsafe_action_rate": round(raw_bad / n, 4),
        "masked_unsafe_action_rate": round(masked_bad / n, 4),
        "masked_action_rate": round(masked_count / n, 4),
        "action_distribution": action_counts,
    }


def train() -> dict:
    random.seed(42)
    np.random.seed(42)
    states, actions, rewards, next_states, dones, df = _load_arrays()
    replay = ReplayBuffer(capacity=max(10000, len(states) + 100))
    for state, action, reward, next_state, done in zip(states, actions, rewards, next_states, dones):
        replay.push(state, int(action), float(reward), next_state, bool(done))

    policy = DoubleDQNPolicy(state_dim=len(STATE_FEATURES), action_dim=action_count(), hidden_dim=96, gamma=0.95, lr=0.001)
    losses: list[float] = []
    epochs = 40
    batch_size = 64
    for epoch in range(1, epochs + 1):
        epoch_losses = []
        steps = max(1, len(replay) // batch_size)
        epsilon = max(0.02, 0.15 * (1.0 - epoch / epochs))
        for _ in range(steps):
            loss = policy.train_step(replay, batch_size=batch_size)
            if loss is not None:
                epoch_losses.append(loss)
        if epoch % 5 == 0:
            policy.update_target()
        losses.append(round(sum(epoch_losses) / max(1, len(epoch_losses)), 6))

    policy.save(MODEL_PATH)
    eval_result = _evaluate(policy, df)
    report = {
        "status": "success",
        "module": "double_dqn_training",
        "generated_at": _now_iso(),
        "model_path": str(MODEL_PATH),
        "meta_path": str(META_PATH),
        "dataset_path": str(DATA_PATH),
        "rows_used": len(df),
        "state_features": STATE_FEATURES,
        "action_dim": action_count(),
        "epochs": epochs,
        "batch_size": batch_size,
        "training_mode": "double_dqn_from_scratch_offline_replay",
        "loss_history": losses,
        "evaluation": eval_result,
        "safe_action_mask_required": True,
    }
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    META_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    MD_REPORT.write_text(_markdown(report), encoding="utf-8")
    return report


def _markdown(report: dict) -> str:
    return "\n".join(
        [
            "# Double DQN Training Report",
            "",
            f"Generated at: {report['generated_at']}",
            "",
            f"- status: `{report['status']}`",
            f"- rows used: `{report['rows_used']}`",
            f"- training mode: `{report['training_mode']}`",
            f"- model path: `{report['model_path']}`",
            f"- evaluation: `{report['evaluation']}`",
            "",
            "```text",
            "STATUS: success",
            "MODULE: double_dqn_training",
            "```",
            "",
        ]
    )


def main() -> None:
    report = train()
    print(f"STATUS: {report['status']}")
    print("MODULE: double_dqn_training")
    print(f"MODEL: {MODEL_PATH}")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()

