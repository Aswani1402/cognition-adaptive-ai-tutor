from __future__ import annotations

from typing import Dict, Any, List


def _clean_text(text: str) -> str:
    return " ".join((text or "").strip().split())


def _strategy_explanation(strategy: str) -> str:
    if strategy == "remedial":
        return "You were given more supportive material to reinforce the core idea before moving on."
    if strategy == "practice":
        return "You were given example-driven material so you can apply the concept actively."
    if strategy == "advanced":
        return "You were given more demanding material because you appear ready for deeper application."
    return "You were given grounded material selected for the current learning state."


def build_grounded_teaching_response(
    learner_id: str,
    concept_id: str,
    retrieval_result: Dict[str, Any],
    learner_state: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    learner_state = learner_state or {}

    chunks: List[Dict[str, Any]] = retrieval_result.get("chunks", [])
    mapping = retrieval_result.get("mapping", {}) or {}
    bundle = retrieval_result.get("bundle", {}) or {}
    resource_bundle = bundle.get("resource_bundle", {}) if isinstance(bundle, dict) else {}

    if not chunks:
        return {
            "learner_id": str(learner_id),
            "concept_id": str(concept_id),
            "mode": "fallback",
            "title": "No grounded content found",
            "teaching_text": (
                "No grounded teaching content was found for this concept. "
                "Please add content or use fallback explanation."
            ),
            "sources": [],
        }

    first = chunks[0]
    strategy = first.get("strategy", "practice")
    difficulty = first.get("difficulty", "medium")
    content_type = first.get("content_type", "worked_example")
    concept_name = bundle.get("concept_name") or f"concept {concept_id}"

    mastery = learner_state.get("mastery_score")
    behaviour_risk = learner_state.get("behaviour_risk")
    review_need = learner_state.get("review_need_score")

    intro_lines = [
        f"Concept: {concept_name}",
        f"Concept ID: {mapping.get('content_concept_id', concept_id)}",
        f"Strategy: {strategy}",
        f"Difficulty: {difficulty}",
        f"Content type: {content_type}",
    ]

    if mastery is not None:
        intro_lines.append(f"Estimated mastery: {mastery:.2f}")
    if behaviour_risk is not None:
        intro_lines.append(f"Behaviour risk: {behaviour_risk:.2f}")
    if review_need is not None:
        intro_lines.append(f"Review need: {review_need:.2f}")

    grounded_material = "\n\n".join(
        f"Source chunk {i + 1}:\n{_clean_text(chunk.get('content', ''))}"
        for i, chunk in enumerate(chunks)
    )

    definition = _clean_text(resource_bundle.get("definition", ""))
    teaching_parts = ["Personalized grounded teaching response", "\n".join(intro_lines)]
    if definition:
        teaching_parts.append("Core definition:\n" + definition)
    teaching_parts.append("Grounded material:\n" + grounded_material)
    teaching_text = "\n\n".join(teaching_parts)

    return {
        "learner_id": str(learner_id),
        "concept_id": str(concept_id),
        "mode": "grounded_db_rag",
        "title": f"Teaching for {concept_name}",
        "teaching_text": teaching_text,
        "explanation": _strategy_explanation(str(strategy)),
        "sources": [
            {
                "strategy": c.get("strategy"),
                "difficulty": c.get("difficulty"),
                "content_type": c.get("content_type"),
                "section": c.get("section"),
            }
            for c in chunks
        ],
    }
