from typing import Dict


class LevelEngine:
    def __init__(self):
        self.levels = [
            {"level": 1, "difficulty": "easy", "target_score": 0.4},
            {"level": 2, "difficulty": "easy", "target_score": 0.6},
            {"level": 3, "difficulty": "medium", "target_score": 0.7},
            {"level": 4, "difficulty": "medium", "target_score": 0.8},
            {"level": 5, "difficulty": "hard", "target_score": 0.9},
        ]

    def get_level(self, mastery_score: float) -> Dict:
        for lvl in self.levels:
            if mastery_score < lvl["target_score"]:
                return lvl

        return self.levels[-1]

    def next_level(self, current_level: int) -> Dict:
        for lvl in self.levels:
            if lvl["level"] == current_level + 1:
                return lvl

        return self.levels[-1]