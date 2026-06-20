from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from tutor.system.orchestrator import run_orchestrator
from tutor.concept_dependency.run_dependency_module_final import run_dependency_module_final
from tutor.rag.retriever import retrieve_rag_context
from tutor.rag.generator import build_grounded_teaching_response


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TUTOR_DB = str(PROJECT_ROOT / "external" / "core_data" / "tutor.db")

CONCEPT_DBS = [
    str(PROJECT_ROOT / "external" / "core_data" / "python_learning.db"),
    str(PROJECT_ROOT / "external" / "core_data" / "html_web_basics.db"),
    str(PROJECT_ROOT / "external" / "core_data" / "database_sql.db"),
    str(PROJECT_ROOT / "external" / "core_data" / "git_version_control.db"),
    str(PROJECT_ROOT / "external" / "core_data" / "data_structures.db"),
]


def map_action_to_teaching(final_action: str) -> Dict[str, str]:
    if final_action == "review_current":
        return {
            "strategy": "remedial",
            "difficulty": "easy",
            "content_type": "worked_example",
        }
    if final_action == "reinforce_current":
        return {
            "strategy": "practice",
            "difficulty": "medium",
            "content_type": "guided_practice",
        }
    if final_action == "advance":
        return {
            "strategy": "advanced",
            "difficulty": "medium",
            "content_type": "challenge_problem",
        }

    return {
        "strategy": "practice",
        "difficulty": "medium",
        "content_type": "worked_example",
    }


def run_rag_tutor(
    learner_id: str,
    concept_id: Optional[str] = None,
) -> Dict[str, Any]:
    orchestration = run_orchestrator(
        learner_id=str(learner_id),
        concept_id=str(concept_id) if concept_id else None,
    )

    current_concept_id = orchestration.get("concept_id")
    final_action = orchestration.get("final_action", "reinforce_current")

    target_concept_id = current_concept_id
    dependency_result = None

    if final_action == "advance":
        dependency_result = run_dependency_module_final(
            tutor_db=TUTOR_DB,
            concept_db_paths=CONCEPT_DBS,
            learner_id=str(learner_id),
            current_concept_id=current_concept_id,
        )
        target_concept_id = dependency_result.get("recommended_next_concept", current_concept_id)

    # default
    teaching_cfg = map_action_to_teaching(final_action)

    if final_action == "advance":
        cid = str(target_concept_id)

        strategy_map = (dependency_result or {}).get("strategy_map", {})
        difficulty_map = (dependency_result or {}).get("difficulty_map", {})
        content_type_map = (dependency_result or {}).get("content_type_map", {})

        # base from dependency
        strategy = strategy_map.get(cid)
        difficulty = difficulty_map.get(cid)
        content_type = content_type_map.get(cid)

        # override for demo clarity
        if strategy == "remedial":
            strategy = "advanced"

        if difficulty == "easy":
            difficulty = "medium"

        if content_type == "worked_example":
            content_type = "challenge_problem"

        teaching_cfg = {
            "strategy": strategy or "advanced",
            "difficulty": difficulty or "medium",
            "content_type": content_type or "challenge_problem",
        }

    retrieval = retrieve_rag_context(
        system_concept_id=str(target_concept_id),
        strategy=teaching_cfg["strategy"],
        difficulty=teaching_cfg["difficulty"],
        content_type=teaching_cfg["content_type"],
        limit=3,
    )

    evidence_summary = orchestration.get("evidence_summary", {}) or {}
    review_result = orchestration.get("review_result", {}) or {}

    learner_state = {
        "mastery_score": evidence_summary.get("mastery_score"),
        "behaviour_risk": evidence_summary.get("behaviour_risk"),
        "review_need_score": review_result.get("review_need_score"),
    }

    teaching_output = build_grounded_teaching_response(
        learner_id=str(learner_id),
        concept_id=str(target_concept_id),
        retrieval_result=retrieval,
        learner_state=learner_state,
    )

    return {
        "learner_id": str(learner_id),
        "input_concept_id": str(concept_id) if concept_id else None,
        "current_concept_id": current_concept_id,
        "target_concept_id": target_concept_id,
        "final_action": final_action,
        "decision_confidence": orchestration.get("decision_confidence"),
        "reasons": orchestration.get("reasons", []),
        "dependency_result": dependency_result,
        "retrieval_summary": {
            "mapping": retrieval.get("mapping"),
            "chunk_count": retrieval.get("chunk_count"),
        },
        "teaching_output": teaching_output,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--learner_id", required=True)
    parser.add_argument("--concept_id", required=False, default=None)
    args = parser.parse_args()

    output = run_rag_tutor(
        learner_id=str(args.learner_id),
        concept_id=str(args.concept_id) if args.concept_id else None,
    )
    print(json.dumps(output, indent=2))