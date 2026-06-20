from __future__ import annotations

from typing import Dict, Any


def run_explainer_agent(rag_tutor_output: Dict[str, Any]) -> Dict[str, Any]:
    final_action = rag_tutor_output.get("final_action", "reinforce_current")
    target_concept_id = rag_tutor_output.get("target_concept_id")
    reasons = rag_tutor_output.get("reasons", [])

    if final_action == "advance":
        message = f"You are ready to move to the next concept: {target_concept_id}."
    elif final_action == "review_current":
        message = "You should review the current concept before moving ahead."
    else:
        message = "You should continue practicing the current concept."

    return {
        "agent_name": "ExplainerAgent",
        "status": "success",
        "explanation": {
            "message": message,
            "reasons": reasons,
        },
    }