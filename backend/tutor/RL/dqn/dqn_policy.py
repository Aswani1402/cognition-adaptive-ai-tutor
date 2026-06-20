from pathlib import Path
from typing import Any, Dict

import numpy as np
import torch

from tutor.RL.dqn.action_space import get_action_by_id, get_action_count
from tutor.RL.dqn.dqn_model import DQNModel


MODEL_PATH = Path("models/rl/dqn/dqn_policy_model.pt")

LEARNING_SIGNAL_MAP = {
    "before_evaluation": 0.0,
    "weak": 0.25,
    "partial": 0.6,
    "mastered": 1.0,
}


class DQNPolicy:
    def __init__(self):
        self.model = None
        self.available = False
        self.load()

    def load(self):
        if not MODEL_PATH.exists():
            self.available = False
            return

        self.model = DQNModel(state_dim=5, action_dim=get_action_count())
        self.model.load_state_dict(torch.load(MODEL_PATH, map_location="cpu"))
        self.model.eval()
        self.available = True

    def is_available(self) -> bool:
        return self.available

    def safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

    def encode_bool(self, value: Any) -> float:
        return 1.0 if str(value).lower() == "true" else 0.0

    def encode_learning_signal(self, value: Any) -> float:
        return LEARNING_SIGNAL_MAP.get(str(value), 0.0)

    def build_state_vector(self, state: Dict[str, Any]) -> np.ndarray:
        return np.array(
            [
                self.safe_float(state.get("mastery_score")),
                self.safe_float(state.get("behavior_score")),
                self.encode_bool(state.get("review_due")),
                self.safe_float(state.get("evaluation_score")),
                self.encode_learning_signal(state.get("learning_signal")),
            ],
            dtype=np.float32,
        )

    def predict(self, state: Dict[str, Any]) -> Dict[str, Any]:
        if not self.available:
            return {
                "status": "error",
                "reason": "DQN model not available",
            }

        state_vector = self.build_state_vector(state)
        state_tensor = torch.tensor(state_vector, dtype=torch.float32).unsqueeze(0)

        with torch.no_grad():
            q_values = self.model(state_tensor)
            action_id = int(torch.argmax(q_values, dim=1).item())

        action = get_action_by_id(action_id)

        return {
            "status": "success",
            "action_id": action_id,
            "action_label": action["action_label"],
            "strategy": action["strategy"],
            "difficulty": action["difficulty"],
            "q_values": q_values.squeeze(0).tolist(),
        }