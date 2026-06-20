from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


NOTEBOOK_DIR = Path("models/notebook")


class NotebookGenerator:
    def __init__(self):
        NOTEBOOK_DIR.mkdir(parents=True, exist_ok=True)

    def _path(self, learner_id: str) -> Path:
        return NOTEBOOK_DIR / f"learner_{learner_id}_notebook.json"

    def load_notebook(self, learner_id: str) -> Dict[str, Any]:
        path = self._path(learner_id)

        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)

        return {
            "learner_id": learner_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": None,
            "concept_notes": [],
            "mistake_notes": [],
            "revision_notes": [],
            "next_recommendations": [],
        }

    def update_from_lesson(
        self,
        learner_id: str,
        lesson_pack: Dict[str, Any],
        evaluation: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        notebook = self.load_notebook(learner_id)

        concept_id = lesson_pack.get("concept_id")
        concept_name = lesson_pack.get("concept_name")
        difficulty = lesson_pack.get("difficulty")

        key_points = []
        recap = lesson_pack.get("quick_recap", {})
        if isinstance(recap, dict):
            key_points = recap.get("bullets", [])

        flashcards = lesson_pack.get("flashcards", [])
        assessment_items = lesson_pack.get("assessment_items", [])

        note = {
            "concept_id": concept_id,
            "concept_name": concept_name,
            "difficulty": difficulty,
            "summary": recap.get("body") if isinstance(recap, dict) else "",
            "key_points": key_points,
            "flashcard_count": len(flashcards),
            "assessment_count": len(assessment_items),
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }

        notebook["concept_notes"].append(note)

        if evaluation:
            score = evaluation.get("score") or evaluation.get("overall_score")
            learning_signal = evaluation.get("learning_signal")

            notebook["mistake_notes"].append({
                "concept_id": concept_id,
                "concept_name": concept_name,
                "score": score,
                "learning_signal": learning_signal,
                "feedback": evaluation.get("feedback_summary", ""),
                "saved_at": datetime.now(timezone.utc).isoformat(),
            })

        notebook["revision_notes"].append({
            "concept_id": concept_id,
            "concept_name": concept_name,
            "revision": recap.get("body") if isinstance(recap, dict) else "",
            "saved_at": datetime.now(timezone.utc).isoformat(),
        })

        notebook["next_recommendations"].append({
            "concept_id": concept_id,
            "concept_name": concept_name,
            "recommendation": f"Review {concept_name} flashcards and try the mini challenge again.",
            "saved_at": datetime.now(timezone.utc).isoformat(),
        })

        notebook["updated_at"] = datetime.now(timezone.utc).isoformat()

        path = self._path(learner_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(notebook, f, indent=2, ensure_ascii=False)

        return notebook