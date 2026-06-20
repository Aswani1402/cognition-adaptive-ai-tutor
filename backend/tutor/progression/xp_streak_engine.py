from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any


XP_MEMORY_PATH = Path("models/memory/xp_streak_memory.json")


class XPStreakEngine:
    def __init__(self):
        self.memory = self._load()

    def _load(self) -> Dict[str, Any]:
        if XP_MEMORY_PATH.exists():
            with open(XP_MEMORY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save(self) -> None:
        XP_MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(XP_MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump(self.memory, f, indent=2)

    def update(
        self,
        learner_id: str,
        xp_earned: int,
        lesson_completed: bool = True,
    ) -> Dict[str, Any]:
        learner_id = str(learner_id)

        if learner_id not in self.memory:
            self.memory[learner_id] = {
                "total_xp": 0,
                "streak": 0,
                "lessons_completed": 0,
                "last_updated": None,
            }

        profile = self.memory[learner_id]

        profile["total_xp"] += int(xp_earned)

        if lesson_completed:
            profile["streak"] += 1
            profile["lessons_completed"] += 1

        profile["last_updated"] = datetime.now(timezone.utc).isoformat()

        self._save()

        return profile

    def get_profile(self, learner_id: str) -> Dict[str, Any]:
        return self.memory.get(str(learner_id), {
            "total_xp": 0,
            "streak": 0,
            "lessons_completed": 0,
            "last_updated": None,
        })