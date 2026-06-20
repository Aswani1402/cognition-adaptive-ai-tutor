from __future__ import annotations

from typing import Any, Dict, Optional

from tutor.assessment.dynamic_assessment_generator import generate_assessment_bundle


class AssessmentAgent:
    def run(
        self,
        concept_resource: Dict[str, Any],
        learner_id: Optional[str] = None,
        difficulty: str = "medium",
    ) -> Dict[str, Any]:

        concept_id = str(
            concept_resource.get("system_concept_id")
            or concept_resource.get("concept_id")
            or concept_resource.get("content_concept_id")
            or ""
        )

        concept_name = concept_resource.get("concept_name", "")

        assessment_output = generate_assessment_bundle(
            system_concept_id=concept_id,
            concept_name=concept_name,
            difficulty=difficulty,
        )

        return {
            "status": "success",
            "agent": "AssessmentAgent",
            "data": assessment_output,
        }