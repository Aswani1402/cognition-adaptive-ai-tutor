from __future__ import annotations

from typing import Any, Dict, List, Optional

from tutor.assessment.adaptive_question_generator import generate_assessment_bundle


class AssessmentAgent:
    def __init__(self, default_types: Optional[List[str]] = None) -> None:
        self.default_types = default_types or [
            "mcq",
            "output_prediction",
            "debug",
            "short_explanation",
            "transfer",
        ]

    def run(
        self,
        concept_resource: Dict[str, Any],
        learner_id: Optional[str] = None,
        difficulty: str = "medium",
        requested_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        qtypes = requested_types or self.default_types

        assessment_output = generate_assessment_bundle(
            concept_resource=concept_resource,
            learner_id=learner_id,
            difficulty=difficulty,
            requested_types=qtypes,
        )

        return {
            "status": "success",
            "agent": "AssessmentAgent",
            "data": assessment_output,
        }