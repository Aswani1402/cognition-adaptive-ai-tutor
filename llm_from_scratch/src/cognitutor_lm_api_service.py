import json
from typing import Any, Dict, List, Optional

from src.cognitutor_lm_config import ALL_89_TASK_TYPES, ALL_TASK_OUTPUT, CORE_OUTPUT, CORE_TASK_TYPES, PACKET_OUTPUT, REPORTS_DIR, ROOT, TEACHING_VIEWS
from src.content_versioning import CONTENT_VERSION, GENERATOR_VERSION, attach_version_metadata
from src.concept_resource_loader import find_concept, load_concept_resources
from src.production_quality_gate import apply_quality_gate
from src.voice_script_generator import generate_voice_script
from scripts.generate_teaching_aligned_packets import build_difficulty_content_blocks


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _packets() -> List[Dict[str, Any]]:
    return json.loads(PACKET_OUTPUT.read_text(encoding="utf-8")) if PACKET_OUTPUT.exists() else []


def _tasks() -> List[Dict[str, Any]]:
    return json.loads(ALL_TASK_OUTPUT.read_text(encoding="utf-8")) if ALL_TASK_OUTPUT.exists() else []


def _load_json(path, fallback):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else fallback


def _base_response() -> Dict[str, Any]:
    return {
        "source": "CogniTutorLM_from_scratch",
        "generation_mode": "guarded_concept_resources",
        "raw_generation_status": "WARN",
        "final_guarded_generation_status": "PASS",
        "content_version": CONTENT_VERSION,
    }


def _finalize_response(response: Dict[str, Any], item_type: str = "website_packet") -> Dict[str, Any]:
    response.update({k: v for k, v in _base_response().items() if k not in response})
    apply_quality_gate(response, item_type=item_type)
    attach_version_metadata(response, source=response, concept_resource=response, website_ready=response.get("website_ready", False))
    metadata = response.setdefault("metadata", {})
    metadata.update(
        {
            "content_version": response.get("content_version"),
            "generator_version": GENERATOR_VERSION,
            "quality_gate_status": response.get("quality_gate_status"),
            "website_ready": response.get("website_ready"),
        }
    )
    return response


def _live_guarded(task_type: str, domain: str, concept_name: str = None, concept_id: str = None, difficulty: str = "easy", teaching_view: str = None, learner_state: dict = None) -> Dict[str, Any]:
    from src.rag_llm_live_guarded_generator import generate_live_guarded

    return generate_live_guarded(task_type, domain, concept_name, concept_id=concept_id, difficulty=difficulty, teaching_view=teaching_view, learner_state=learner_state)


def _live_metadata(live: Dict[str, Any]) -> Dict[str, Any]:
    model_attempt = live.get("model_attempt") or {}
    validation = live.get("validation") or {}
    return {
        "generation_mode_requested": live.get("generation_mode_requested") or "rag_llm_live_guarded",
        "rag_used": bool((live.get("rag_context") or {}).get("rag_used")),
        "model_attempted": bool(model_attempt.get("model_attempted")),
        "model_loaded": bool(model_attempt.get("model_loaded")),
        "model_valid": bool(model_attempt.get("model_valid")),
        "model_quality_score": validation.get("quality_score"),
        "model_checkpoint_used": live.get("model_checkpoint_used") or (live.get("metadata") or {}).get("model_checkpoint_used"),
        "model_checkpoint_status": live.get("model_checkpoint_status") or (live.get("metadata") or {}).get("model_checkpoint_status"),
        "model_training_report_status": live.get("model_training_report_status") or (live.get("metadata") or {}).get("model_training_report_status"),
        "fallback_used": bool(live.get("fallback_used")),
        "fallback_source": live.get("fallback_source"),
        "final_source": live.get("final_source"),
        "learner_facing_safe": bool(live.get("learner_facing_safe")),
    }


def _is_live_mode(generation_mode: str) -> bool:
    return generation_mode in {"rag_llm_live_guarded", "model_first_retrained_if_valid"}


def get_available_subjects() -> list[str]:
    return sorted({c["domain"] for c in load_concept_resources()})


def get_available_concepts(domain: str) -> list[dict]:
    return [
        {"domain": c["domain"], "concept_id": c["concept_id"], "concept_name": c["concept_name"]}
        for c in load_concept_resources()
        if _norm(c["domain"]) == _norm(domain)
    ]


def get_available_tasks(core_only: bool = False) -> list[str]:
    return list(CORE_TASK_TYPES if core_only else ALL_89_TASK_TYPES)


def get_learning_packet(
    domain,
    concept_name=None,
    concept_id=None,
    difficulty="easy",
    teaching_view="definition_view",
    concept=None,
    generation_mode: str = "guarded",
) -> dict:
    concept_name = concept_name or concept
    if _is_live_mode(generation_mode):
        live = _live_guarded(teaching_view or "explanation", domain, concept_name, concept_id, difficulty, teaching_view)
        live["generation_mode_requested"] = generation_mode
        return {"status": live.get("status"), **_base_response(), "generation_mode": generation_mode, "live_guarded_output": live, "metadata": _live_metadata(live)}
    found = find_concept(domain, concept=concept_name, concept_id=concept_id)
    for packet in _packets():
        if found and packet["domain"] == found["domain"] and packet["concept_id"] == found["concept_id"] and packet["teaching_view"] == teaching_view and packet.get("difficulty") == difficulty:
            return {"status": "success", **packet}
    return {"status": "not_found", "domain": domain, "concept_name": concept_name, "concept_id": concept_id, "difficulty": difficulty, "teaching_view": teaching_view}


def get_aligned_assessment(packet_id: str) -> list[dict]:
    for packet in _packets():
        if packet["packet_id"] == packet_id:
            return packet.get("aligned_assessments", [])
    return []


def get_level_content_blocks(domain, concept_name=None, concept_id=None, concept=None) -> dict:
    concept_name = concept_name or concept
    found = find_concept(domain, concept=concept_name, concept_id=concept_id)
    if not found:
        return {"status": "not_found", "domain": domain, "concept_name": concept_name, "concept_id": concept_id}
    return {"status": "success", **build_difficulty_content_blocks(found)}


def get_available_difficulties(domain, concept_name=None, concept_id=None, concept=None) -> dict:
    concept_name = concept_name or concept
    found = find_concept(domain, concept=concept_name, concept_id=concept_id)
    if not found:
        return {"status": "not_found", "domain": domain, "concept_name": concept_name, "concept_id": concept_id}
    difficulties = sorted({p.get("difficulty") for p in _packets() if p.get("domain") == found["domain"] and p.get("concept_id") == found["concept_id"]})
    return {"status": "success", "domain": found["domain"], "concept_id": found["concept_id"], "concept_name": found["concept_name"], "difficulties": difficulties}


def get_study_report_packet(domain, concept_name=None, concept_id=None, learner_id=None, concept=None) -> dict:
    concept_name = concept_name or concept
    found = find_concept(domain, concept=concept_name, concept_id=concept_id)
    if not found:
        return {"status": "not_found", "domain": domain, "concept_name": concept_name, "concept_id": concept_id}
    learner = learner_id or "demo_learner_001"
    path = REPORTS_DIR / "concept_study_reports" / f"{learner}_{found['domain'].replace(' ', '_')}_{found['concept_name'].replace(' ', '_')}.json"
    if path.exists():
        return {"status": "success", **json.loads(path.read_text(encoding="utf-8"))}
    rows = [p for p in _packets() if p.get("domain") == found["domain"] and p.get("concept_id") == found["concept_id"]]
    return {
        "status": "success",
        "learner_id": learner,
        "domain": found["domain"],
        "concept_id": found["concept_id"],
        "concept_name": found["concept_name"],
        "studied_levels": sorted({p.get("difficulty") for p in rows if p.get("difficulty") != "revision"}),
        "packet_count": len(rows),
        "assessment_questions_seen": [a for p in rows for a in p.get("aligned_assessments", [])][:10],
    }


def get_all_task_outputs(domain: str, concept_name: str = None, concept_id: str = None, concept: str = None, generation_mode: str = "guarded") -> list[dict]:
    concept_name = concept_name or concept
    found = find_concept(domain, concept=concept_name, concept_id=concept_id)
    if not found:
        return []
    return [r for r in _tasks() if r["domain"] == found["domain"] and r["concept_id"] == found["concept_id"]]


def _task_rows(domain: str, concept_name: str = None, concept_id: str = None, task_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    rows = get_all_task_outputs(domain, concept_name=concept_name, concept_id=concept_id)
    if task_types:
        allowed = set(task_types)
        rows = [row for row in rows if row.get("task_type") in allowed]
    return rows


def _assessment_question_from_row(row: Dict[str, Any], index: int = 0) -> Dict[str, Any]:
    out = row.get("output") or {}
    task_type = row.get("task_type") or "practice_question"
    question = {
        "questionId": f"{row.get('concept_id')}-{task_type}-{index}",
        "taskType": task_type,
        "questionType": task_type,
        "difficulty": row.get("difficulty"),
        "source_level": row.get("source_level"),
        "teaching_view": row.get("teaching_view"),
        "prompt": out.get("question") or out.get("statement") or out.get("prompt") or out.get("title") or f"Practice {row.get('concept_name')} with {task_type}.",
        "options": out.get("options"),
        "correctAnswer": str(row.get("answer") or out.get("answer") or out.get("expected_output") or out.get("expected_fix") or ""),
        "explanation": row.get("explanation") or out.get("explanation"),
        "hint": out.get("hint") or row.get("hint"),
        "concept_id": row.get("concept_id"),
        "concept_name": row.get("concept_name"),
        "subject": row.get("domain"),
    }
    if out.get("code"):
        question["code"] = out.get("code")
    if out.get("buggy_code"):
        question["buggyCode"] = out.get("buggy_code")
    if out.get("expected_output"):
        question["expectedOutput"] = out.get("expected_output")
    if out.get("expected_fix"):
        question["expectedFix"] = out.get("expected_fix")
    if task_type == "fill_in_the_blank":
        question["blanks"] = [{"id": "answer", "label": "Missing answer", "answer": question["correctAnswer"]}]
    if task_type == "true_or_false":
        question["options"] = ["True", "False"]
        question["correctAnswer"] = "True" if out.get("answer") is True else "False"
    return question


def get_flashcards(domain, concept_name=None, concept_id=None, difficulty=None, variant="all", generation_mode: str = "guarded") -> Dict[str, Any]:
    if _is_live_mode(generation_mode):
        task_type = "flashcard" if variant == "all" else variant
        live = _live_guarded(task_type, domain, concept_name, concept_id, difficulty or "easy", "flashcard_view")
        return {"status": live.get("status"), **_base_response(), "generation_mode": generation_mode, "flashcards": [live.get("final_output")], "live_guarded_output": live, "metadata": _live_metadata(live)}
    variants = [
        "flashcard",
        "concept_recall_flashcard",
        "misconception_flashcard",
        "example_flashcard",
        "debug_flashcard",
        "personal_flashcards",
        "syntax_flashcard",
    ]
    selected = variants if variant == "all" else [variant]
    rows = _task_rows(domain, concept_name=concept_name, concept_id=concept_id, task_types=selected)
    cards = []
    for idx, row in enumerate(rows):
        out = row.get("output") or {}
        level_cards = out.get("cards_by_difficulty") or out.get("all_level_flashcards") or {}
        selected_level_card = level_cards.get(difficulty) if difficulty else None
        if difficulty and level_cards and not selected_level_card:
            continue
        if difficulty and not level_cards and row.get("difficulty") not in {difficulty, "revision"}:
            continue
        card_front = (selected_level_card or {}).get("front") or out.get("front") or f"What should you recall about {row.get('concept_name')}?"
        card_back = (selected_level_card or {}).get("back") or out.get("back") or out.get("summary") or row.get("answer") or row.get("explanation")
        card_difficulty = (selected_level_card or {}).get("difficulty") or row.get("difficulty")
        card_source_level = (selected_level_card or {}).get("source_level") or row.get("source_level")
        cards.append(
            {
                "id": f"{row.get('concept_id')}-{row.get('task_type')}-{idx}",
                "conceptId": row.get("concept_id"),
                "conceptName": row.get("concept_name"),
                "card_type": row.get("task_type"),
                "card_kind": (selected_level_card or {}).get("card_kind") or out.get("card_kind"),
                "front": card_front,
                "back": card_back,
                "explanation": row.get("explanation"),
                "difficulty": card_difficulty,
                "source_level": card_source_level,
                "due": True,
            }
        )
    return {"status": "success" if cards else "not_found", **_base_response(), "domain": domain, "concept_name": concept_name, "concept_id": concept_id, "variant": variant, "flashcards": cards}


def get_mindmap(domain, concept_name=None, concept_id=None, variant="concept_mindmap", generation_mode: str = "guarded") -> Dict[str, Any]:
    if _is_live_mode(generation_mode):
        live = _live_guarded(variant or "mindmap", domain, concept_name, concept_id, "easy", "mindmap_view")
        return {"status": live.get("status"), **_base_response(), "generation_mode": generation_mode, "mindmap": live.get("final_output"), "live_guarded_output": live, "metadata": _live_metadata(live)}
    rows = _task_rows(domain, concept_name=concept_name, concept_id=concept_id, task_types=["mindmap", "concept_mindmap", "comparison_mindmap"])
    selected = next((row for row in rows if row.get("task_type") == variant), None) or (rows[0] if rows else None)
    if not selected:
        return {"status": "not_found", **_base_response(), "domain": domain, "concept_name": concept_name, "concept_id": concept_id, "variant": variant}
    out = selected.get("output") or {}
    raw_branches = out.get("branches") or []
    nodes = []
    for idx, branch in enumerate(raw_branches):
        label = branch.get("label", f"Branch {idx + 1}") if isinstance(branch, dict) else str(branch)
        items = branch.get("items") if isinstance(branch, dict) else [str(branch)]
        nodes.append({"id": f"node-{idx}", "title": label, "body": "; ".join(str(x) for x in (items or [])), "color": ["#2563eb", "#16a34a", "#7c3aed", "#e11d48", "#0891b2"][idx % 5], "x": 50 + ((idx % 3) - 1) * 28, "y": 20 + (idx // 3) * 26})
    return {
        "status": "success",
        **_base_response(),
        "domain": selected.get("domain"),
        "concept_id": selected.get("concept_id"),
        "concept_name": selected.get("concept_name"),
        "variant": selected.get("task_type"),
        "mindmap": {"conceptId": selected.get("concept_id"), "title": selected.get("concept_name"), "center": out.get("center") or selected.get("concept_name"), "branches": raw_branches, "nodes": nodes},
    }


def get_notebook_packet(domain, concept_name=None, concept_id=None, learner_state=None) -> Dict[str, Any]:
    rows = _task_rows(domain, concept_name=concept_name, concept_id=concept_id, task_types=["notebook_summary", "mistake_summary", "revision_plan", "comeback_summary", "returning_learner_summary", "progress_insight"])
    found = find_concept(domain, concept=concept_name, concept_id=concept_id)
    summary_row = next((r for r in rows if r.get("task_type") == "notebook_summary"), rows[0] if rows else {})
    mistake_row = next((r for r in rows if r.get("task_type") == "mistake_summary"), {})
    revision_row = next((r for r in rows if r.get("task_type") == "revision_plan"), {})
    summary_out = summary_row.get("output") or {}
    mistake_out = mistake_row.get("output") or {}
    revision_out = revision_row.get("output") or {}
    summary = summary_out.get("summary") or f"{(found or {}).get('concept_name', concept_name)} notebook summary."
    weaknesses = mistake_out.get("weaknesses") or summary_out.get("weaknesses") or []
    revision_plan = revision_out.get("next_revision") or revision_out.get("summary") or summary_out.get("next_revision") or "Review one aligned packet and try one practice item."
    return {
        "status": "success" if found else "not_found",
        **_base_response(),
        "learner_state": learner_state or {},
        "domain": (found or {}).get("domain", domain),
        "concept_id": (found or {}).get("concept_id", concept_id),
        "concept_name": (found or {}).get("concept_name", concept_name),
        "notebook_summary": summary,
        "mistake_summary": weaknesses if isinstance(weaknesses, list) else [weaknesses],
        "revision_plan": revision_plan if isinstance(revision_plan, list) else [revision_plan],
        "rows": rows,
    }


def get_generated_content(domain: str, concept: str = None, concept_id: str = None, task_type: str = "explanation", generation_mode: str = "guarded") -> Dict[str, Any]:
    if _is_live_mode(generation_mode):
        live = _live_guarded(task_type, domain, concept, concept_id, "easy", None)
        return {"status": live.get("status"), **_base_response(), "generation_mode": generation_mode, "output": live.get("final_output"), "live_guarded_output": live, "metadata": _live_metadata(live)}
    found = find_concept(domain, concept=concept, concept_id=concept_id)
    for row in _tasks():
        if found and row["domain"] == found["domain"] and row["concept_id"] == found["concept_id"] and row["task_type"] == task_type:
            return {"status": "success", **row}
    return {"status": "not_found", "domain": domain, "concept": concept, "task_type": task_type}


def _packet_by_view(domain: str, concept: str, view: str, difficulty: str = None) -> Optional[Dict[str, Any]]:
    found = find_concept(domain, concept=concept)
    for packet in _packets():
        if found and packet["domain"] == found["domain"] and packet["concept_id"] == found["concept_id"] and packet["teaching_view"] == view and (difficulty is None or packet.get("difficulty") == difficulty):
            return packet
    return None


def get_website_session_packet(domain: str, concept: str, learner_id: str = None, difficulty: str = "easy", teaching_view: str = "definition_view", use_rag: bool = True, generation_mode: str = "guarded") -> dict:
    packet = _packet_by_view(domain, concept, teaching_view, difficulty) or _packet_by_view(domain, concept, teaching_view)
    if not packet:
        return {"status": "not_found", "domain": domain, "concept": concept}
    found = find_concept(packet["domain"], concept_id=packet["concept_id"])
    flash = _packet_by_view(domain, concept, "flashcard_view", "revision") or _packet_by_view(domain, concept, "flashcard_view") or {}
    mind = _packet_by_view(domain, concept, "mindmap_view", "revision") or _packet_by_view(domain, concept, "mindmap_view") or {}
    voice_script = generate_voice_script(
        found or packet,
        task_type="teaching_voice_script",
        difficulty=difficulty,
        teaching_view=teaching_view,
        packet=packet,
    )
    audio_overview = {
        "status": "success",
        "script": voice_script["script"],
        "audio_ready": True,
        "concept_name": packet["concept_name"],
        "difficulty": difficulty,
        "source_level": voice_script["source_level"],
        "estimated_duration_sec": voice_script["estimated_duration_sec"],
        "voice_sections": voice_script["voice_sections"],
    }
    all_tasks = get_all_task_outputs(packet["domain"], concept_id=packet["concept_id"])
    rag_sections: List[str] = []
    rag_used = False
    if use_rag:
        try:
            from src.rag_connector import RagConnector

            context_result = RagConnector().get_rag_context(packet["concept_name"], concept_id=packet["concept_id"], domain=packet["domain"], top_k=5)
            contexts = context_result.get("chunks") or []
            rag_sections = [str(c.get("section") or c.get("source") or "context") for c in contexts[:5]] if isinstance(contexts, list) else []
            rag_used = bool(rag_sections)
        except Exception:
            rag_sections = []
            rag_used = False
    assessment_bank = [_assessment_question_from_row(row, idx) for idx, row in enumerate(all_tasks) if row.get("task_family") in {"assessment", "practice_challenge"}]
    assessment_types = sorted({row.get("task_type") for row in all_tasks if row.get("task_family") in {"assessment", "practice_challenge"}})
    flashcards_packet = get_flashcards(packet["domain"], concept_id=packet["concept_id"])
    flashcards = flashcards_packet.get("flashcards", [])
    flashcard_variants = sorted({card.get("card_type") for card in flashcards if card.get("card_type")})
    mindmap_variants = ["mindmap", "concept_mindmap", "comparison_mindmap"]
    mindmaps = {
        variant: get_mindmap(packet["domain"], concept_id=packet["concept_id"], variant=variant).get("mindmap", {})
        for variant in mindmap_variants
    }
    notebook_packet = get_notebook_packet(packet["domain"], concept_id=packet["concept_id"], learner_state={"learner_id": learner_id})
    voice_variants = [
        "voice_script",
        "teaching_voice_script",
        "revision_voice_script",
        "mistake_feedback_voice_script",
        "doubt_explanation_voice_script",
        "encouragement_script",
        "next_step_guidance_script",
        "concept_intro_voice_script",
    ]
    voice_scripts = {
        variant: generate_voice_script(found or packet, task_type=variant, difficulty=difficulty, teaching_view=teaching_view, packet=packet)
        for variant in voice_variants
    }
    response = {
        "status": "success",
        **_base_response(),
        "domain": packet["domain"],
        "concept_id": packet["concept_id"],
        "concept_name": packet["concept_name"],
        "difficulty": packet["difficulty"],
        "source_level": packet.get("source_level"),
        "teaching_view": packet["teaching_view"],
        "teaching_content": packet["teaching_content"],
        "aligned_assessments": packet["aligned_assessments"],
        "assessment_bank": assessment_bank,
        "assessment_types_available": assessment_types,
        "all_assessment_types": assessment_types,
        "all_task_outputs": all_tasks,
        "puzzle_tasks": [_assessment_question_from_row(row, idx) for idx, row in enumerate(all_tasks) if row.get("task_type") in {"debug_task", "output_prediction", "debug_challenge", "output_prediction_challenge", "multi_step_challenge", "challenge_question"}],
        "hint": packet["hint"],
        "hints": [row.get("output") for row in all_tasks if row.get("task_family") == "hint"],
        "feedback_template": packet["feedback_template"],
        "revision_summary": packet["revision_summary"],
        "flashcard": (flash.get("teaching_content") or {}).get("flashcards", {}),
        "flashcards": flashcards,
        "flashcard_variants_available": flashcard_variants,
        "mindmap": mindmaps.get("concept_mindmap") or mindmaps.get("mindmap") or (mind.get("teaching_content") or {}).get("mindmap", {}),
        "mindmaps": mindmaps,
        "mindmap_variants_available": [variant for variant, value in mindmaps.items() if value],
        "notebook": notebook_packet,
        "notebook_summary": notebook_packet.get("notebook_summary"),
        "mistake_summary": notebook_packet.get("mistake_summary"),
        "revision_plan": notebook_packet.get("revision_plan"),
        "voice_script": voice_script,
        "voice_scripts": voice_scripts,
        "voice_variants_available": sorted(voice_scripts.keys()),
        "audio_overview": audio_overview,
        "next_step": packet["next_step"],
        "all_task_count": len(all_tasks),
        "rag_used": rag_used,
        "rag_context_count": len(rag_sections),
        "rag_sections": rag_sections,
        "rag_grounding_status": "PASS" if rag_used else "WARN",
        "rag_metadata": {
            "rag_used": rag_used,
            "rag_context_count": len(rag_sections),
            "rag_sections": rag_sections,
            "rag_grounding_status": "PASS" if rag_used else "WARN",
        },
        "all_task_outputs_available": len(all_tasks) == len(ALL_89_TASK_TYPES),
        "frontend_ready": True,
        "metadata": {
            "concept_count": len(load_concept_resources()),
            "packet_count": len(_packets()),
            "task_type_count": len(ALL_89_TASK_TYPES),
            "rag_used": rag_used,
            "rag_context_count": len(rag_sections),
            "raw_valid": False,
            "fallback_applied": True,
            "website_ready": True,
            "learner_id": learner_id,
        },
    }
    if _is_live_mode(generation_mode):
        live = _live_guarded(teaching_view or "explanation", packet["domain"], packet["concept_name"], packet["concept_id"], difficulty, teaching_view, {"learner_id": learner_id})
        live["generation_mode_requested"] = generation_mode
        response["generation_mode"] = generation_mode
        response["live_guarded_output"] = live
        response["cognitutor_lm_live_guarded_output"] = live
        response["final_source"] = live.get("final_source")
        response["learner_facing_safe"] = live.get("learner_facing_safe")
        response["frontend_ready"] = live.get("frontend_ready")
        response["metadata"].update(_live_metadata(live))
    return _finalize_response(response, item_type="website_packet")


def ask_doubt_and_get_answer(domain: str, concept: str, question: str, use_rag: bool = True, generation_mode: str = "guarded") -> dict:
    if _is_live_mode(generation_mode):
        live = _live_guarded("doubt_answer", domain, concept, None, "medium", None, {"question": question})
        return {"status": live.get("status"), **_base_response(), "question": question, "answer": live.get("final_output"), "live_guarded_output": live, "metadata": _live_metadata(live)}
    rows = get_all_task_outputs(domain, concept)
    answer = next((r for r in rows if r["task_type"] == "doubt_answer"), None)
    voice = get_voice_script(domain, concept_name=concept, difficulty="medium", teaching_view="step_by_step_view", voice_type="doubt_explanation_voice_script")
    output = (answer or {}).get("output") or {}
    return {
        "status": "success" if answer else "not_found",
        **_base_response(),
        "question": question,
        "answer": output.get("answer") if isinstance(output, dict) else output,
        "reason": output.get("reason") if isinstance(output, dict) else "",
        "example": output.get("example") if isinstance(output, dict) else "",
        "try_this": output.get("try_this") if isinstance(output, dict) else "",
        "voice_script": voice.get("voice_script", {}),
        "rag_used": False if not use_rag else None,
    }


def get_revision_packet(domain: str, concept_name: str = None, concept_id: str = None, learner_state: dict = None, concept: str = None, generation_mode: str = "guarded") -> dict:
    concept_name = concept_name or concept
    if _is_live_mode(generation_mode):
        live = _live_guarded("revision_summary", domain, concept_name, concept_id, "revision", "revision_view", learner_state)
        return {"status": live.get("status"), **_base_response(), "generation_mode": generation_mode, "revision_summary": live.get("final_output"), "live_guarded_output": live, "metadata": _live_metadata(live)}
    found = find_concept(domain, concept=concept_name, concept_id=concept_id)
    packet = _packet_by_view(domain, (found or {}).get("concept_name", concept_name), "revision_view", "revision") or _packet_by_view(domain, (found or {}).get("concept_name", concept_name), "revision_view")
    return {"status": "success", **packet, "learner_state": learner_state or {}} if packet else {"status": "not_found"}


def get_concept_study_report(domain: str, concept: str, learner_id: str = None) -> dict:
    return get_study_report_packet(domain, concept_name=concept, learner_id=learner_id)


def get_product_status() -> Dict[str, Any]:
    concepts = load_concept_resources()
    packets = _packets()
    tasks = _tasks()
    core = _load_json(CORE_OUTPUT, [])
    registry_path = ROOT / "outputs" / "content_registry" / "content_registry.json"
    smoke_path = REPORTS_DIR / "cognitutor_lm_product_smoke_test.json"
    response = {
        "status": "success",
        **_base_response(),
        "core_outputs": f"{len(core)} / 456",
        "learning_packets": len(packets),
        "all_89_outputs": f"{len(tasks)} / {38 * len(ALL_89_TASK_TYPES)}",
        "task_types": f"{len({r.get('task_type') for r in tasks})} / {len(ALL_89_TASK_TYPES)}",
        "concepts": f"{len(concepts)} / 38",
        "content_registry": "PASS" if registry_path.exists() else "FAIL",
        "product_smoke_test": (_load_json(smoke_path, {}).get("status") if smoke_path.exists() else "MISSING"),
        "website_safe_output": True,
        "metadata": {"concept_count": len(concepts), "packet_count": len(packets), "task_type_count": len(ALL_89_TASK_TYPES)},
    }
    return _finalize_response(response, item_type="status")


def get_content_registry() -> Dict[str, Any]:
    path = ROOT / "outputs" / "content_registry" / "content_registry.json"
    if not path.exists():
        return {"status": "fail", **_base_response(), "website_ready": False, "quality_gate_status": "FAIL", "metadata": {"reason": "content registry not built"}}
    registry = _load_json(path, {})
    registry_status = registry.get("status")
    response = {**_base_response(), **registry, "status": "success", "registry_status": registry_status, "metadata": {"registry_path": str(path)}}
    return response


def get_subject_catalog() -> Dict[str, Any]:
    subjects = get_available_subjects()
    return _finalize_response({"status": "success", **_base_response(), "subjects": subjects, "metadata": {"subject_count": len(subjects)}}, item_type="catalog")


def get_concept_catalog(domain: str) -> Dict[str, Any]:
    concepts = get_available_concepts(domain)
    return _finalize_response({"status": "success", **_base_response(), "domain": domain, "concepts": concepts, "metadata": {"concept_count": len(concepts)}}, item_type="catalog")


def get_packet_by_level(domain: str, concept: str, difficulty: str, teaching_view: str) -> Dict[str, Any]:
    return get_learning_packet(domain, concept_name=concept, difficulty=difficulty, teaching_view=teaching_view)


def get_next_packet_for_learner(domain: str, concept: str, learner_state: Dict[str, Any]) -> Dict[str, Any]:
    difficulty = (learner_state or {}).get("difficulty") or "easy"
    teaching_view = (learner_state or {}).get("teaching_view") or ("code_view" if difficulty == "medium" else "challenge_view" if difficulty == "hard" else "definition_view")
    return get_website_ready_packet(domain, concept, difficulty=difficulty, teaching_view=teaching_view, learner_id=(learner_state or {}).get("learner_id"))


def get_assessment_for_packet(packet_id: str) -> Dict[str, Any]:
    assessments = get_aligned_assessment(packet_id)
    return _finalize_response({"status": "success" if assessments else "fail", **_base_response(), "packet_id": packet_id, "aligned_assessments": assessments, "metadata": {"assessment_count": len(assessments)}}, item_type="assessment")


def get_all_89_tasks_for_concept(domain: str, concept: str) -> Dict[str, Any]:
    rows = get_all_task_outputs(domain, concept_name=concept)
    return _finalize_response({"status": "success" if rows else "fail", **_base_response(), "domain": domain, "concept_name": concept, "tasks": rows, "task_count": len(rows), "metadata": {"task_count": len(rows)}}, item_type="catalog")


def get_website_ready_packet(domain: str, concept: str, difficulty: str = "easy", teaching_view: str = "definition_view", learner_id: str = None, generation_mode: str = "guarded") -> Dict[str, Any]:
    return get_website_session_packet(domain, concept, learner_id=learner_id, difficulty=difficulty, teaching_view=teaching_view, use_rag=True, generation_mode=generation_mode)


def get_revision_or_comeback_packet(domain: str, concept: str, learner_state: Dict[str, Any] = None) -> Dict[str, Any]:
    packet = get_revision_packet(domain, concept, learner_state=learner_state)
    if packet.get("status") == "success":
        packet.update(_base_response())
        apply_quality_gate(packet, item_type="packet")
    return packet


def get_similar_question(domain, concept, weakness=None, question_type=None, difficulty="medium") -> Dict[str, Any]:
    preferred = [question_type] if question_type else []
    preferred += ["debug_task", "output_prediction", "syntax_completion", "practice_question", "transfer_question", "challenge_question", "mcq"]
    rows = get_all_task_outputs(domain, concept)
    rows = [row for row in rows if row.get("difficulty") in {difficulty, "medium", "hard", "easy"} and row.get("task_family") in {"assessment", "practice_challenge"}]
    selected = None
    for task_type in preferred:
        selected = next((row for row in rows if row.get("task_type") == task_type), None)
        if selected:
            break
    selected = selected or (rows[0] if rows else None)
    if not selected:
        return {"status": "not_found", **_base_response(), "domain": domain, "concept": concept, "weakness": weakness}
    question = _assessment_question_from_row(selected, 0)
    question["weakness"] = weakness
    return {"status": "success", **_base_response(), "domain": selected.get("domain"), "concept_id": selected.get("concept_id"), "concept_name": selected.get("concept_name"), "question": question, "similar_question": question}


def get_doubt_answer(domain: str, concept: str, question: str, use_rag: bool = True, generation_mode: str = "guarded") -> Dict[str, Any]:
    response = ask_doubt_and_get_answer(domain, concept, question, use_rag=use_rag, generation_mode=generation_mode)
    response.update(_base_response())
    response.setdefault("metadata", {})["use_rag"] = use_rag
    return _finalize_response(response, item_type="doubt")


def get_voice_script(
    domain,
    concept_name=None,
    concept_id=None,
    difficulty="easy",
    teaching_view="definition_view",
    voice_type="teaching_voice_script",
    generation_mode: str = "guarded",
) -> Dict[str, Any]:
    if _is_live_mode(generation_mode):
        live = _live_guarded(voice_type, domain, concept_name, concept_id, difficulty, teaching_view)
        return {"status": live.get("status"), **_base_response(), "generation_mode": generation_mode, "voice_script": live.get("final_output"), "script": live.get("final_output"), "live_guarded_output": live, "metadata": _live_metadata(live)}
    found = find_concept(domain, concept=concept_name, concept_id=concept_id)
    if not found:
        return {"status": "not_found", **_base_response(), "domain": domain, "concept_name": concept_name, "concept_id": concept_id}
    packet = get_learning_packet(
        found["domain"],
        concept_id=found["concept_id"],
        difficulty=difficulty,
        teaching_view=teaching_view,
    )
    packet_arg = packet if packet.get("status") == "success" else None
    voice = generate_voice_script(
        found,
        task_type=voice_type,
        difficulty=difficulty,
        teaching_view=teaching_view,
        packet=packet_arg,
    )
    response = {
        "status": "success",
        **_base_response(),
        "domain": found["domain"],
        "concept_id": found["concept_id"],
        "concept_name": found["concept_name"],
        "difficulty": voice["difficulty"],
        "source_level": voice["source_level"],
        "teaching_view": voice["teaching_view"],
        "voice_script": voice,
        "script": voice["script"],
        "audio_ready": True,
        "estimated_duration_sec": voice["estimated_duration_sec"],
        "voice_sections": voice["voice_sections"],
        "metadata": {"voice_type": voice_type, "raw_valid": False, "fallback_applied": True},
    }
    return _finalize_response(response, item_type="catalog")


def get_audio_overview_packet(
    domain,
    concept_name=None,
    concept_id=None,
    learner_state=None,
) -> Dict[str, Any]:
    learner_state = learner_state or {}
    difficulty = learner_state.get("difficulty", "easy")
    teaching_view = learner_state.get("teaching_view", "definition_view")
    result = get_voice_script(
        domain,
        concept_name=concept_name,
        concept_id=concept_id,
        difficulty=difficulty,
        teaching_view=teaching_view,
        voice_type="teaching_voice_script",
    )
    if result.get("status") != "success":
        return result
    voice = result["voice_script"]
    return {
        "status": "success",
        **_base_response(),
        "script": voice["script"],
        "audio_ready": True,
        "concept_name": voice["concept_name"],
        "concept_id": voice["concept_id"],
        "domain": voice["domain"],
        "difficulty": voice["difficulty"],
        "source_level": voice["source_level"],
        "estimated_duration_sec": voice["estimated_duration_sec"],
        "voice_sections": voice["voice_sections"],
    }


def get_frontend_contract_sample() -> Dict[str, Any]:
    return get_website_ready_packet("Python", "Variables", difficulty="easy", teaching_view="definition_view", learner_id="demo_learner_001")
