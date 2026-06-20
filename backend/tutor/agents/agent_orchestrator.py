from __future__ import annotations

import json
from typing import Dict, Any, Optional

from tutor.system.run_rag_tutor import run_rag_tutor
from tutor.agents.tutor_agent import run_tutor_agent
from tutor.agents.assessment_agent import run_assessment_agent
from tutor.agents.reviewer_agent import run_reviewer_agent
from tutor.agents.explainer_agent import run_explainer_agent


def _infer_concept_info(rag_tutor_output: Dict[str, Any]) -> Dict[str, str]:
    retrieval_summary = rag_tutor_output.get("retrieval_summary", {}) or {}
    mapping = retrieval_summary.get("mapping", {}) or {}

    system_concept_id = str(rag_tutor_output.get("target_concept_id"))
    content_concept_id = str(mapping.get("content_concept_id", system_concept_id))
    domain = str(mapping.get("domain", "Unknown"))

    concept_name = content_concept_id
    return {
        "system_concept_id": system_concept_id,
        "concept_name": concept_name,
        "domain": domain,
    }


def run_agentic_tutor(
    learner_id: str,
    concept_id: Optional[str] = None,
) -> Dict[str, Any]:
    rag_tutor_output = run_rag_tutor(
        learner_id=str(learner_id),
        concept_id=str(concept_id) if concept_id else None,
    )

    tutor_agent_output = run_tutor_agent(rag_tutor_output)
    reviewer_agent_output = run_reviewer_agent(rag_tutor_output)
    explainer_agent_output = run_explainer_agent(rag_tutor_output)

    concept_info = _infer_concept_info(rag_tutor_output)
    teaching_text = (
        rag_tutor_output.get("teaching_output", {}) or {}
    ).get("teaching_text", "")

    assessment_agent_output = run_assessment_agent(
        system_concept_id=concept_info["system_concept_id"],
        concept_name=concept_info["concept_name"],
        domain=concept_info["domain"],
        difficulty="easy",
        teaching_text=teaching_text,
    )

    return {
        "learner_id": str(learner_id),
        "input_concept_id": str(concept_id) if concept_id else None,
        "final_action": rag_tutor_output.get("final_action"),
        "target_concept_id": rag_tutor_output.get("target_concept_id"),
        "tutor_agent": tutor_agent_output,
        "assessment_agent": assessment_agent_output,
        "reviewer_agent": reviewer_agent_output,
        "explainer_agent": explainer_agent_output,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--learner_id", required=True)
    parser.add_argument("--concept_id", required=False, default=None)
    args = parser.parse_args()

    output = run_agentic_tutor(
        learner_id=str(args.learner_id),
        concept_id=str(args.concept_id) if args.concept_id else None,
    )
    print(json.dumps(output, indent=2))