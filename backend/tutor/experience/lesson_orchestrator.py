from __future__ import annotations

from typing import Any, Dict, Optional

from tutor.agents.tutor_agent import TutorAgent
from tutor.assessment.assessment_agent import AssessmentAgent
from tutor.experience.lesson_pack_generator import generate_lesson_pack
from tutor.progression.level_engine import LevelEngine
from tutor.progression.xp_streak_engine import XPStreakEngine
from tutor.notebook.notebook_generator import NotebookGenerator

class LessonOrchestrator:
    def __init__(self):
        self.tutor_agent = TutorAgent()
        self.assessment_agent = AssessmentAgent()
        self.level_engine = LevelEngine()
        self.xp_streak_engine = XPStreakEngine()
        self.notebook_generator = NotebookGenerator()

    def run(
        self,
        concept_resource: Dict[str, Any],
        learner_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        difficulty: str = "medium",
    ) -> Dict[str, Any]:
        context = context or {}

        mastery = float(context.get("mastery_score", 0.0))
        level_info = self.level_engine.get_level(mastery)

        adaptive_difficulty = level_info.get("difficulty", difficulty)

        tutor_output = self.tutor_agent.run(
            concept_resource=concept_resource,
            learner_id=learner_id,
            difficulty=adaptive_difficulty,
            context=context,
        )

        teaching_data = tutor_output.get("data", {})

        final_difficulty = tutor_output.get("used_difficulty", adaptive_difficulty)

        assessment_output = self.assessment_agent.run(
            concept_resource=concept_resource,
            learner_id=learner_id,
            difficulty=final_difficulty,
        )

        assessment_data = assessment_output.get("data", {})

        lesson_pack = generate_lesson_pack(
            concept_resource=concept_resource,
            generated_content=teaching_data,
            assessment_output=assessment_data,
            learner_id=learner_id,
            difficulty=final_difficulty,
        )

        lesson_pack["progression"] = {
            "level": level_info.get("level"),
            "difficulty": final_difficulty,
            "target_score": level_info.get("target_score"),
            "mastery_score": mastery,
        }
        xp_earned = lesson_pack.get("engagement", {}).get("xp_reward", 0)

        xp_profile = None
        if learner_id:
            xp_profile = self.xp_streak_engine.update(
                learner_id=str(learner_id),
                xp_earned=int(xp_earned),
                lesson_completed=True,
            )

        lesson_pack["xp_streak"] = xp_profile

        notebook_output = None

        if learner_id:
            notebook_output = self.notebook_generator.update_from_lesson(
                learner_id=str(learner_id),
                lesson_pack=lesson_pack,
            )

        lesson_pack["notebook"] = {
            "updated": notebook_output is not None,
            "concept_note_count": len(notebook_output.get("concept_notes", [])) if notebook_output else 0,
            "revision_note_count": len(notebook_output.get("revision_notes", [])) if notebook_output else 0,
        }

        return {
            "status": "success",
            "agent": "LessonOrchestrator",
            "lesson_pack": lesson_pack,
            "tutor_output": tutor_output,
            "assessment_output": assessment_output,
            "progression": lesson_pack["progression"],
            "xp_streak": xp_profile,
            "notebook": lesson_pack["notebook"],
        }