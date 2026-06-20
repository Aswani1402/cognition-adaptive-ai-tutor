from typing import Any, Dict

from src.concept_resource_loader import find_concept


def _join(value: Any) -> str:
    if isinstance(value, list):
        return "\n".join(str(x) for x in value if str(x).strip())
    return str(value or "").strip()


def _sections_from_concept(concept: Dict[str, Any]) -> Dict[str, str]:
    return {
        "definition": _join(concept.get("definition") or concept.get("base_content")),
        "examples": _join(concept.get("examples")),
        "key_points": _join(concept.get("key_points")),
        "misconceptions": _join(concept.get("misconceptions")),
        "real_world_use": _join(concept.get("real_world_use")),
        "next_concept_link": _join(concept.get("next_concept_link")),
    }


def _context_text(sections: Dict[str, str]) -> str:
    return "\n\n".join(f"[{name}]\n{text}" for name, text in sections.items() if text).strip()


def get_live_rag_context(
    domain,
    concept_name,
    concept_id=None,
    task_type=None,
    difficulty="easy",
    teaching_view=None,
):
    issues = []
    concept = find_concept(domain, concept=concept_name, concept_id=concept_id)
    if not concept:
        return {
            "status": "FAIL",
            "rag_used": False,
            "domain": domain,
            "concept_id": concept_id,
            "concept_name": concept_name,
            "sections": {},
            "context_text": "",
            "source": "none",
            "metadata": {"task_type": task_type, "difficulty": difficulty, "teaching_view": teaching_view},
            "issues": ["concept_not_found"],
        }

    sections = _sections_from_concept(concept)
    source = "concept_resource_fallback"
    rag_used = False
    status = "WARN"
    try:
        from src.rag_connector import RagConnector

        rag = RagConnector().get_rag_context(
            concept["concept_name"],
            concept_id=concept["concept_id"],
            domain=concept["domain"],
            top_k=6,
        )
        chunks = rag.get("chunks") or []
        if rag.get("rag_connected") and chunks:
            for chunk in chunks:
                if str(chunk.get("domain") or concept["domain"]).lower() != concept["domain"].lower():
                    issues.append("rag_wrong_domain_chunk_skipped")
                    continue
                section = str(chunk.get("section") or "key_points")
                text = str(chunk.get("text") or "").strip()
                if text and section in sections:
                    sections[section] = (sections.get(section) + "\n" + text).strip()
            rag_used = True
            source = "rag"
            status = "PASS"
        else:
            issues.append(rag.get("reason") or "rag_no_chunks")
    except Exception as exc:
        issues.append(f"rag_error: {exc}")

    if not any(sections.values()):
        status = "FAIL"
        issues.append("empty_context")

    return {
        "status": status,
        "rag_used": rag_used,
        "domain": concept["domain"],
        "concept_id": concept["concept_id"],
        "concept_name": concept["concept_name"],
        "sections": sections,
        "context_text": _context_text(sections),
        "source": source,
        "metadata": {"task_type": task_type, "difficulty": difficulty, "teaching_view": teaching_view},
        "issues": issues,
    }
