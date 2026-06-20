from __future__ import annotations

import random
from collections import deque
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from tutor.policy.rl.state_action_space import action_count, id_to_action, model_action_dict, state_to_vector


class DuelingQNetwork(nn.Module):
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 96):
        super().__init__()
        self.feature = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
        )
        self.value_stream = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )
        self.advantage_stream = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, action_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        features = self.feature(x)
        value = self.value_stream(features)
        advantage = self.advantage_stream(features)
        return value + advantage - advantage.mean(dim=1, keepdim=True)


class ReplayBuffer:
    def __init__(self, capacity: int = 10000):
        self.buffer: deque[tuple[np.ndarray, int, float, np.ndarray, bool]] = deque(maxlen=capacity)

    def push(self, state: np.ndarray, action_id: int, reward: float, next_state: np.ndarray, done: bool = False) -> None:
        self.buffer.append((state, int(action_id), float(reward), next_state, bool(done)))

    def sample(self, batch_size: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        batch = random.sample(self.buffer, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        return (
            torch.tensor(np.stack(states), dtype=torch.float32),
            torch.tensor(actions, dtype=torch.long),
            torch.tensor(rewards, dtype=torch.float32),
            torch.tensor(np.stack(next_states), dtype=torch.float32),
            torch.tensor(dones, dtype=torch.float32),
        )

    def __len__(self) -> int:
        return len(self.buffer)


class DuelingDQNPolicy:
    def __init__(
        self,
        state_dim: int = 10,
        action_dim: int | None = None,
        hidden_dim: int = 96,
        gamma: float = 0.95,
        lr: float = 0.001,
    ):
        self.state_dim = state_dim
        self.action_dim = action_dim or action_count()
        self.gamma = gamma
        self.policy_net = DuelingQNetwork(state_dim, self.action_dim, hidden_dim)
        self.target_net = DuelingQNetwork(state_dim, self.action_dim, hidden_dim)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=lr)
        self.loss_fn = nn.SmoothL1Loss()

    def select_action(self, state: np.ndarray, epsilon: float = 0.0) -> int:
        if random.random() < epsilon:
            return random.randrange(self.action_dim)
        with torch.no_grad():
            state_t = torch.tensor(state, dtype=torch.float32).unsqueeze(0)
            q_values = self.policy_net(state_t)
            return int(torch.argmax(q_values, dim=1).item())

    def train_step(self, replay: ReplayBuffer, batch_size: int) -> float | None:
        if len(replay) < batch_size:
            return None
        states, actions, rewards, next_states, dones = replay.sample(batch_size)
        q_values = self.policy_net(states).gather(1, actions.unsqueeze(1)).squeeze(1)
        with torch.no_grad():
            next_q = self.target_net(next_states).max(dim=1)[0]
            targets = rewards + self.gamma * next_q * (1.0 - dones)
        loss = self.loss_fn(q_values, targets)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        return float(loss.item())

    def update_target(self) -> None:
        self.target_net.load_state_dict(self.policy_net.state_dict())

    def predict_action(self, state: dict[str, Any] | np.ndarray) -> dict[str, Any]:
        vector = state if isinstance(state, np.ndarray) else state_to_vector(state)
        with torch.no_grad():
            q_values = self.policy_net(torch.tensor(vector, dtype=torch.float32).unsqueeze(0)).squeeze(0)
        action_id = int(torch.argmax(q_values).item())
        action_label = id_to_action(action_id)
        return {
            "status": "success",
            "module": "DuelingDQNPolicy",
            "action_id": action_id,
            "action_label": action_label,
            "q_values": [float(v) for v in q_values.tolist()],
            **model_action_dict(action_label),
        }

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "policy_state_dict": self.policy_net.state_dict(),
                "target_state_dict": self.target_net.state_dict(),
                "state_dim": self.state_dim,
                "action_dim": self.action_dim,
                "gamma": self.gamma,
            },
            path,
        )

    @classmethod
    def load(cls, path: str | Path) -> "DuelingDQNPolicy":
        checkpoint = torch.load(path, map_location="cpu")
        policy = cls(
            state_dim=int(checkpoint.get("state_dim", 10)),
            action_dim=int(checkpoint.get("action_dim", action_count())),
            gamma=float(checkpoint.get("gamma", 0.95)),
        )
        policy.policy_net.load_state_dict(checkpoint["policy_state_dict"])
        policy.target_net.load_state_dict(checkpoint.get("target_state_dict", checkpoint["policy_state_dict"]))
        policy.policy_net.eval()
        policy.target_net.eval()
        return policy
