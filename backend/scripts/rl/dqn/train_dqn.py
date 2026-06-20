import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim

from tutor.RL.dqn.action_space import get_action_count, get_action_id
from tutor.RL.dqn.dqn_model import DQNModel


DATA_PATH = Path("evaluation_outputs/csv/rl_experience_dataset.csv")
MODEL_DIR = Path("models/rl/dqn")
MODEL_PATH = MODEL_DIR / "dqn_policy_model.pt"
METADATA_PATH = MODEL_DIR / "dqn_policy_metadata.json"

STATE_FEATURES = [
    "mastery_score",
    "behavior_score",
    "review_due",
    "evaluation_score",
    "learning_signal",
]

LEARNING_SIGNAL_MAP = {
    "before_evaluation": 0.0,
    "weak": 0.25,
    "partial": 0.6,
    "mastered": 1.0,
}

NON_SELECTED_ACTION_TARGET = -1.0


def encode_bool(value):
    return 1.0 if str(value).lower() == "true" else 0.0


def encode_learning_signal(value):
    return LEARNING_SIGNAL_MAP.get(str(value), 0.0)


def build_state(row, prefix=""):
    return np.array(
        [
            float(row.get(f"{prefix}mastery_score", 0.0)),
            float(row.get(f"{prefix}behavior_score", 0.0)),
            encode_bool(row.get(f"{prefix}review_due", False)),
            float(row.get(f"{prefix}evaluation_score", 0.0)),
            encode_learning_signal(row.get(f"{prefix}learning_signal", "")),
        ],
        dtype=np.float32,
    )


def build_target_q_vector(action_id, reward, action_dim):
    target_q = np.full(action_dim, NON_SELECTED_ACTION_TARGET, dtype=np.float32)
    target_q[action_id] = float(reward)
    return target_q


def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(DATA_PATH)

    df = df.dropna(
        subset=[
            "mastery_score",
            "behavior_score",
            "review_due",
            "evaluation_score",
            "learning_signal",
            "strategy",
            "difficulty",
            "reward",
            "next_mastery_score",
            "next_behavior_score",
            "next_review_due",
            "next_evaluation_score",
            "next_learning_signal",
        ]
    )

    print("Loaded RL dataset")
    print("Rows used:", len(df))

    state_dim = len(STATE_FEATURES)
    action_dim = get_action_count()

    states = []
    target_q_vectors = []

    for _, row in df.iterrows():
        state = build_state(row, prefix="")
        action_id = get_action_id(str(row["strategy"]), str(row["difficulty"]))
        reward = float(row["reward"])

        states.append(state)
        target_q_vectors.append(build_target_q_vector(action_id, reward, action_dim))

    states_np = np.stack(states)
    target_q_np = np.stack(target_q_vectors)

    policy_net = DQNModel(state_dim=state_dim, action_dim=action_dim)

    optimizer = optim.Adam(policy_net.parameters(), lr=0.001)
    loss_fn = nn.MSELoss()

    batch_size = 32
    epochs = 200

    if len(states_np) < batch_size:
        raise ValueError("Not enough RL experiences to train DQN.")

    for epoch in range(1, epochs + 1):
        permutation = np.random.permutation(len(states_np))
        epoch_loss = 0.0
        batch_count = 0

        for start_idx in range(0, len(states_np), batch_size):
            batch_indices = permutation[start_idx:start_idx + batch_size]
            states_t = torch.tensor(states_np[batch_indices], dtype=torch.float32)
            target_q_t = torch.tensor(target_q_np[batch_indices], dtype=torch.float32)

            predicted_q = policy_net(states_t)
            loss = loss_fn(predicted_q, target_q_t)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            epoch_loss += loss.item()
            batch_count += 1

        if epoch % 10 == 0:
            average_loss = epoch_loss / max(batch_count, 1)
            print(f"Epoch {epoch}/{epochs} | loss={average_loss:.4f}")

    torch.save(policy_net.state_dict(), MODEL_PATH)

    metadata = {
        "dataset_path": str(DATA_PATH),
        "rows_used": len(df),
        "state_features": STATE_FEATURES,
        "state_dim": state_dim,
        "action_dim": action_dim,
        "model_path": str(MODEL_PATH),
        "epochs": epochs,
        "batch_size": batch_size,
        "training_mode": "supervised_q_vector_baseline",
        "non_selected_action_target": NON_SELECTED_ACTION_TARGET,
    }

    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print("\nDQN TRAINING COMPLETE")
    print("Saved model:", MODEL_PATH)
    print("Saved metadata:", METADATA_PATH)


if __name__ == "__main__":
    main()
