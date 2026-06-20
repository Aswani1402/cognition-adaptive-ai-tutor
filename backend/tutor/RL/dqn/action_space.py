from typing import Dict, List


ACTIONS: List[Dict[str, str]] = [
    {
        "action_id": 0,
        "action_label": "remedial_easy",
        "strategy": "remedial",
        "difficulty": "easy",
    },
    {
        "action_id": 1,
        "action_label": "practice_medium",
        "strategy": "practice",
        "difficulty": "medium",
    },
    {
        "action_id": 2,
        "action_label": "advanced_hard",
        "strategy": "advanced",
        "difficulty": "hard",
    },
]


ACTION_LABEL_TO_ID = {
    action["action_label"]: action["action_id"]
    for action in ACTIONS
}


ACTION_ID_TO_ACTION = {
    action["action_id"]: action
    for action in ACTIONS
}


def get_action_count() -> int:
    return len(ACTIONS)


def get_action_id(strategy: str, difficulty: str) -> int:
    action_label = f"{strategy}_{difficulty}"
    return ACTION_LABEL_TO_ID.get(action_label, 1)


def get_action_by_id(action_id: int) -> Dict[str, str]:
    return ACTION_ID_TO_ACTION.get(action_id, ACTION_ID_TO_ACTION[1])


def get_action_label(action_id: int) -> str:
    return get_action_by_id(action_id)["action_label"]