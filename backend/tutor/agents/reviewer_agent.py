from __future__ import annotations

from typing import Dict, Any


def run_reviewer_agent(rag_tutor_output: Dict[str, Any]) -> Dict[str, Any]:
    reasons = rag_tutor_output.get("reasons", [])
    final_action = rag_tutor_output.get("final_action")
    decision_confidence = rag_tutor_output.get("decision_confidence")

    return {
        "agent_name": "ReviewerAgent",
        "status": "success",
        "review_summary": {
            "final_action": final_action,
            "decision_confidence": decision_confidence,
            "reasons": reasons,
        },
    }