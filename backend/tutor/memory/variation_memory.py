from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


MEMORY_PATH = Path("models/memory/variation_memory.json")


class VariationMemory:
    def __init__(self) -> None:
        self.memory: Dict[str, Dict[str, List[str]]] = {}
        self._load()

    def _load(self) -> None:
        if MEMORY_PATH.exists():
            with open(MEMORY_PATH, "r", encoding="utf-8") as f:
                self.memory = json.load(f)

    def _save(self) -> None:
        MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump(self.memory, f, indent=2)

    def _get_key(self, learner_id: str, concept_id: str) -> str:
        return f"{learner_id}::{concept_id}"

    def get_history(self, learner_id: str, concept_id: str) -> Dict[str, List[str]]:
        key = self._get_key(learner_id, concept_id)
        return self.memory.get(key, {"content": [], "flashcards": [], "challenge": []})

    def add_entry(
        self,
        learner_id: str,
        concept_id: str,
        content_hashes: List[str],
        flashcard_hashes: List[str],
        challenge_hash: str,
    ) -> None:
        key = self._get_key(learner_id, concept_id)

        if key not in self.memory:
            self.memory[key] = {"content": [], "flashcards": [], "challenge": []}

        self.memory[key]["content"].extend(content_hashes)
        self.memory[key]["flashcards"].extend(flashcard_hashes)
        self.memory[key]["challenge"].append(challenge_hash)

        self._save()

    def filter_new_content(
        self,
        learner_id: str,
        concept_id: str,
        items: List[Dict[str, Any]],
        field: str,
    ) -> List[Dict[str, Any]]:
        history = self.get_history(learner_id, concept_id).get(field, [])

        filtered = []
        for item in items:
            item_hash = item.get("content_hash") or item.get("card_hash") or item.get("challenge_hash")

            if item_hash not in history:
                filtered.append(item)

        return filtered if filtered else items  # fallback if all repeated