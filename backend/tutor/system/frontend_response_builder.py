from __future__ import annotations

from typing import Any

from tutor.assessment.structured_question_types import (
    FRONTEND_COMPONENT_MAP,
    PUZZLE_QUESTION_TYPES,
)
from tutor.assessment.puzzle_schema import (
    PUZZLE_FRONTEND_COMPONENT_MAP,
    PUZZLE_TYPES,
    compact_puzzle_for_frontend,
)


ALL_PUZZLE_TYPES = list(dict.fromkeys([*PUZZLE_QUESTION_TYPES, *PUZZLE_TYPES]))


TEACHING_COMPONENTS = {
    "definition_view": "TeachingCard",
    "simple_example_view": "ExampleTeachingCard",
    "step_by_step_view": "StepTeachingCard",
    "code_view": "CodeTeachingCard",
    "analogy_view": "AnalogyCard",
    "misconception_view": "MisconceptionCard",
    "debug_view": "DebugTeachingCard",
    "output_prediction_view": "OutputPredictionTeachingCard",
    "transfer_view": "TransferCard",
    "challenge_view": "ChallengeCard",
    "revision_summary_view": "RevisionSummaryCard",
    "revision_view": "RevisionSummaryCard",
    "flashcard_view": "FlashcardDeck",
    "mindmap_view": "MindmapView",
}

QUESTION_COMPONENTS = {
    "mcq": "MCQQuestionCard",
    "debug_task": "DebugQuestionCard",
    "debug": "DebugQuestionCard",
    "output_prediction": "OutputPredictionCard",
    "transfer_question": "TransferQuestionCard",
    "transfer": "TransferQuestionCard",
    "challenge_question": "ChallengeQuestionCard",
    "challenge": "ChallengeQuestionCard",
    "explanation_check": "ExplanationAnswerCard",
    "explanation": "ExplanationAnswerCard",
    "coding_question": "CodeEditorQuestionCard",
    "syntax_completion": "SyntaxCompletionCard",
    "code_tracing": "CodeTracingCard",
    "flashcard_recall": "FlashcardRecallCard",
    "fill_blank": "FillBlankCard",
    "arrange_steps": "ArrangeStepsCard",
    "match_pairs": "MatchPairsCard",
    "drag_order": "DragOrderCard",
    "code_puzzle": "CodePuzzleCard",
}

QUESTION_COMPONENTS.update(FRONTEND_COMPONENT_MAP)
QUESTION_COMPONENTS.update(PUZZLE_FRONTEND_COMPONENT_MAP)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _first_present(*values: Any, default: Any = None) -> Any:
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return default


def _component_for_teaching_view(view_name: Any) -> str:
    return TEACHING_COMPONENTS.get(str(view_name or ""), "TeachingCard")


def _component_for_question_type(question_type: Any) -> str:
    return QUESTION_COMPONENTS.get(str(question_type or ""), "QuestionCard")


def _compact_questions(assessment: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
    questions = _as_list(assessment.get("questions"))[:limit]
    compact = []

    for question in questions:
        if not isinstance(question, dict):
            continue

        metadata = _as_dict(question.get("metadata"))

        question_type = question.get("question_type") or question.get("assessment_type")
        compact_question = {
            "question_id": question.get("question_id"),
            "assessment_type": question.get("assessment_type") or question_type,
            "question_type": question_type,
            "concept_id": question.get("concept_id") or assessment.get("concept_id"),
            "concept_name": question.get("concept_name") or assessment.get("concept_name"),
            "domain": question.get("domain") or assessment.get("domain"),
            "prompt": question.get("prompt") or question.get("question"),
            "options": question.get("options"),
            "correct_option_index": question.get("correct_option_index"),
            "expected_answer": question.get("expected_answer"),
            "frontend_component": (
                question.get("frontend_component")
                or _component_for_question_type(question_type)
            ),
            "render_mode": metadata.get("render_mode"),
            "metadata": metadata,
        }
        if question_type == "fill_blank":
            compact_question.update(
                {
                    "text_with_blank": question.get("text_with_blank") or metadata.get("text_with_blank"),
                    "answer": question.get("answer") or metadata.get("answer"),
                    "hint": question.get("hint") or metadata.get("hint"),
                }
            )
        elif question_type == "arrange_steps":
            compact_question.update(
                {
                    "steps": question.get("steps") or metadata.get("steps", []),
                    "correct_order": question.get("correct_order") or metadata.get("correct_order", []),
                }
            )
        elif question_type == "match_pairs":
            compact_question.update(
                {
                    "left_items": question.get("left_items") or metadata.get("left_items", []),
                    "right_items": question.get("right_items") or metadata.get("right_items", []),
                    "correct_pairs": question.get("correct_pairs") or metadata.get("correct_pairs", []),
                }
            )
        elif question_type == "drag_order":
            compact_question.update(
                {
                    "items": question.get("items") or metadata.get("items", []),
                    "correct_order": question.get("correct_order") or metadata.get("correct_order", []),
                }
            )
        elif question_type == "code_puzzle":
            compact_question.update(
                {
                    "starter_code": question.get("starter_code") or metadata.get("starter_code"),
                    "answer": question.get("answer") or metadata.get("answer"),
                    "expected_output": question.get("expected_output") or metadata.get("expected_output"),
                }
            )

        compact.append(compact_question)

    return compact


def _compact_puzzle_activities(
    assessment: dict[str, Any],
    puzzle_bundle: dict[str, Any],
    limit: int = 12,
) -> list[dict[str, Any]]:
    raw_puzzles = _as_list(
        _first_present(
            assessment.get("puzzle_activities"),
            assessment.get("puzzles"),
            puzzle_bundle.get("puzzle_activities"),
            puzzle_bundle.get("puzzles"),
            default=[],
        )
    )
    if not raw_puzzles:
        raw_puzzles = [
            question
            for question in _as_list(assessment.get("questions"))
            if isinstance(question, dict)
            and (question.get("puzzle_type") or question.get("question_type")) in ALL_PUZZLE_TYPES
        ]

    activities = []
    for puzzle in raw_puzzles[:limit]:
        if not isinstance(puzzle, dict):
            continue
        activities.append(compact_puzzle_for_frontend(puzzle))
    return activities


def _compact_teaching_items(teaching: dict[str, Any], limit: int = 3) -> list[dict[str, Any]]:
    items = _as_list(teaching.get("items"))[:limit]
    compact = []

    for item in items:
        if not isinstance(item, dict):
            continue

        compact.append(
            {
                "content_id": item.get("content_id"),
                "content_type": item.get("content_type"),
                "strategy": item.get("strategy"),
                "difficulty": item.get("difficulty"),
                "title": item.get("title"),
                "body": item.get("body"),
                "bullets": item.get("bullets", []),
            }
        )

    return compact


def _selected_view_payload(
    frontend_teaching_view: dict[str, Any],
    teaching: dict[str, Any],
    demo_summary: dict[str, Any],
) -> dict[str, Any]:
    selected_view = _as_dict(frontend_teaching_view.get("selected_view"))
    if selected_view:
        return selected_view

    title = _first_present(
        teaching.get("title"),
        teaching.get("concept_name"),
        demo_summary.get("final_concept_name"),
        demo_summary.get("concept_name"),
        default="Current lesson",
    )
    content = _first_present(
        teaching.get("content"),
        teaching.get("body"),
        teaching.get("definition"),
        teaching.get("summary"),
        default="",
    )
    display_type = _first_present(
        demo_summary.get("frontend_selected_display_type"),
        frontend_teaching_view.get("selected_display_type"),
        default="teaching_card",
    )
    return {
        "title": title,
        "content": content,
        "display_type": display_type,
    }


def _extract_flashcards(frontend_teaching_view: dict[str, Any], teaching: dict[str, Any]) -> list[Any]:
    return _as_list(
        _first_present(
            frontend_teaching_view.get("flashcards"),
            frontend_teaching_view.get("flashcard_deck"),
            teaching.get("generated_flashcards"),
            teaching.get("flashcards"),
            default=[],
        )
    )


def _extract_mindmap(frontend_teaching_view: dict[str, Any], teaching: dict[str, Any]) -> dict[str, Any]:
    return _as_dict(
        _first_present(
            frontend_teaching_view.get("mindmap"),
            frontend_teaching_view.get("mindmap_data"),
            teaching.get("generated_mindmap"),
            teaching.get("mindmap"),
            default={},
        )
    )


def _safe_learner_memory_context(learner_id: Any) -> dict[str, Any]:
    learner_id_text = str(learner_id or "").strip()
    base_unavailable = {
        "status": "unavailable",
        "source": "sqlite_production_memory",
        "returning_learner": False,
        "last_active_at": None,
        "last_concept_id": None,
        "last_concept_name": None,
        "last_domain": None,
        "last_teaching_view": None,
        "last_difficulty": None,
        "weak_concepts": [],
        "weak_question_types": [],
        "strong_question_types": [],
        "mistake_summary": {},
        "recommended_revision_views": [],
        "recent_scores": [],
        "next_recommended_action": None,
    }
    if not learner_id_text:
        return {
            **base_unavailable,
            "reason": "Missing learner_id; production memory context was not loaded.",
        }

    try:
        from tutor.memory.production_learner_memory_store import ProductionLearnerMemoryStore

        context = ProductionLearnerMemoryStore().get_returning_learner_context(learner_id_text)
        memory_state = _as_dict(context.get("memory_state"))
        recent_sessions = _as_list(context.get("recent_sessions"))
        latest_session = _as_dict(recent_sessions[0]) if recent_sessions else {}

        return {
            "status": "success",
            "source": "sqlite_production_memory",
            "returning_learner": bool(context.get("returning_learner_available")),
            "last_active_at": _first_present(
                memory_state.get("last_active_at"),
                latest_session.get("started_at"),
                latest_session.get("created_at"),
                default=None,
            ),
            "last_concept_id": _first_present(
                memory_state.get("last_concept_id"),
                latest_session.get("concept_id"),
                default=None,
            ),
            "last_concept_name": _first_present(
                memory_state.get("last_concept_name"),
                latest_session.get("concept_name"),
                default=None,
            ),
            "last_domain": _first_present(
                memory_state.get("last_domain"),
                latest_session.get("domain"),
                default=None,
            ),
            "last_teaching_view": _first_present(
                memory_state.get("last_teaching_view"),
                latest_session.get("selected_view"),
                default=None,
            ),
            "last_difficulty": _first_present(
                memory_state.get("last_difficulty"),
                latest_session.get("difficulty"),
                default=None,
            ),
            "weak_concepts": _as_list(context.get("weak_concepts") or memory_state.get("weak_concepts")),
            "weak_question_types": _as_list(context.get("weak_question_types") or memory_state.get("weak_question_types")),
            "strong_question_types": _as_list(memory_state.get("strong_question_types")),
            "mistake_summary": _as_dict(memory_state.get("mistake_summary")),
            "recommended_revision_views": _as_list(
                context.get("recommended_revision_views")
                or memory_state.get("recommended_revision_views")
            ),
            "recent_scores": _as_list(memory_state.get("recent_scores")),
            "next_recommended_action": _first_present(
                context.get("next_recommended_action"),
                memory_state.get("next_recommended_action"),
                default=None,
            ),
            "recent_sessions": recent_sessions,
            "recent_mistakes": _as_list(context.get("recent_mistakes")),
            "recent_doubts": _as_list(context.get("recent_doubts")),
            "recent_revisions": _as_list(context.get("recent_revisions")),
            "view_progress": _as_list(context.get("view_progress")),
        }
    except Exception as exc:
        return {
            **base_unavailable,
            "reason": f"{type(exc).__name__}: production memory context unavailable.",
        }


def build_frontend_response(full_output: dict[str, Any]) -> dict[str, Any]:
    full_output = _as_dict(full_output)

    demo_summary = _as_dict(full_output.get("demo_summary"))
    demo_output = _as_dict(full_output.get("demo_output"))

    teaching = _as_dict(
        demo_output.get("current_teaching_content")
        or full_output.get("current_teaching_content")
    )

    frontend_teaching_view = _as_dict(
        demo_output.get("frontend_teaching_view_output")
        or full_output.get("frontend_teaching_view_output")
    )

    assessment = _as_dict(
        demo_output.get("assessment")
        or full_output.get("assessment")
    )
    puzzle_bundle = _as_dict(
        demo_output.get("puzzle_bundle")
        or demo_output.get("puzzle_assessment")
        or full_output.get("puzzle_bundle")
        or full_output.get("puzzle_assessment")
    )

    structured_evaluation_output = _as_dict(
        demo_output.get("structured_evaluation_output")
        or full_output.get("structured_evaluation_output")
    )

    progression_reward_output = _as_dict(
        demo_output.get("progression_reward_output")
        or full_output.get("progression_reward_output")
    )

    reward_persistence_output = _as_dict(
        demo_output.get("reward_persistence_output")
        or full_output.get("reward_persistence_output")
    )

    progression_result = _as_dict(
        progression_reward_output.get("progression_result")
    )

    promotion_confidence_output = _as_dict(
        progression_reward_output.get("promotion_confidence_output")
    )

    reward_state = _as_dict(
        progression_reward_output.get("reward_state")
    )

    celebration = _as_dict(
        progression_reward_output.get("celebration")
    )

    frontend_contract = _as_dict(
        progression_reward_output.get("frontend_contract")
    )

    structured_evaluation = _as_dict(
        structured_evaluation_output.get("evaluation")
    )

    evaluation = _as_dict(
        demo_output.get("evaluation")
        or full_output.get("evaluation")
    )

    mistake_analysis_output = _as_dict(
        demo_output.get("mistake_analysis_output")
        or full_output.get("mistake_analysis_output")
    )

    notebook = _as_dict(
        full_output.get("learner_notebook_memory_output")
        or demo_output.get("learner_notebook_memory_output")
    )

    strategy = _as_dict(
        full_output.get("evidence_aware_teaching_strategy_output")
        or demo_output.get("evidence_aware_teaching_strategy_output")
    )

    training_log = _as_dict(
        full_output.get("teaching_strategy_training_log_output")
        or demo_output.get("teaching_strategy_training_log_output")
    )

    xai = _as_dict(
        demo_output.get("xai")
        or full_output.get("xai")
    )

    xai_data = _as_dict(xai.get("data"))


    mistake_analysis_output = _as_dict(
        demo_output.get("mistake_analysis_output")
        or full_output.get("mistake_analysis_output")
    )

    rubric_evaluation_output = _as_dict(
        demo_output.get("rubric_evaluation_output")
        or full_output.get("rubric_evaluation_output")
    )

    rubric_mode = (
        demo_output.get("rubric_mode")
        or full_output.get("rubric_mode")
    )

    debug_evaluation_output = _as_dict(
        demo_output.get("debug_evaluation_output")
        or full_output.get("debug_evaluation_output")
    )

    debug_evaluation_mode = (
        demo_output.get("debug_evaluation_mode")
        or full_output.get("debug_evaluation_mode")
    )
    output_prediction_evaluation_output = _as_dict(
        demo_output.get("output_prediction_evaluation_output")
        or full_output.get("output_prediction_evaluation_output")
    )

    output_prediction_evaluation_mode = (
        demo_output.get("output_prediction_evaluation_mode")
        or full_output.get("output_prediction_evaluation_mode")
    )

    evaluation_fusion_output = _as_dict(
        demo_output.get("evaluation_fusion_output")
        or full_output.get("evaluation_fusion_output")
    )

    evaluation_fusion_mode = (
            demo_output.get("evaluation_fusion_mode")
            or full_output.get("evaluation_fusion_mode")
    )

    cognitutor_lm_output = _as_dict(
        full_output.get("cognitutor_lm_output")
        or demo_output.get("cognitutor_lm_output")
    )

    selected_teaching_view = _first_present(
        frontend_teaching_view.get("selected_teaching_view"),
        frontend_teaching_view.get("selected_view_name"),
        demo_summary.get("frontend_selected_view"),
        demo_summary.get("teaching_view"),
        strategy.get("teaching_view"),
        teaching.get("recommended_view"),
        default="definition_view",
    )
    teaching_card = _selected_view_payload(
        frontend_teaching_view=frontend_teaching_view,
        teaching=teaching,
        demo_summary=demo_summary,
    )
    available_views = _as_list(
        _first_present(
            frontend_teaching_view.get("available_view_names"),
            frontend_teaching_view.get("available_views"),
            teaching.get("available_views"),
            demo_summary.get("available_view_names"),
            default=[],
        )
    )
    fallback_views = _as_list(
        _first_present(
            frontend_teaching_view.get("fallback_view_names"),
            frontend_teaching_view.get("fallback_views"),
            strategy.get("fallback_views"),
            demo_summary.get("fallback_view_names"),
            default=[],
        )
    )
    compact_questions = _compact_questions(assessment)
    puzzle_questions = [
        question
        for question in _compact_questions(assessment, limit=50)
        if question.get("question_type") in ALL_PUZZLE_TYPES
    ]
    puzzle_activities = _compact_puzzle_activities(assessment, puzzle_bundle)
    flashcards = _extract_flashcards(frontend_teaching_view, teaching)
    mindmap = _extract_mindmap(frontend_teaching_view, teaching)
    learner_memory = _safe_learner_memory_context(full_output.get("learner_id"))
    notebook_summary = (
        demo_summary.get("notebook_summary")
        or notebook.get("notebook_summary")
    )
    revision_summary = _first_present(
        demo_summary.get("revision_summary"),
        notebook.get("revision_summary"),
        notebook_summary,
        default=None,
    )
    compact_frontend_contract = {
        **frontend_contract,
        "show_teaching_card": True,
        "show_question_one_at_a_time": True,
        "show_adaptive_hint_card": True,
        "show_voice_script_card": True,
        "show_flashcards_tab": bool(flashcards),
        "show_mindmap_tab": bool(mindmap),
        "show_puzzle_panel": True,
        "show_doubt_panel": True,
        "show_code_runner": True,
        "show_xai_panel": True,
        "show_reward_widget": True,
        "show_returning_learner_memory": True,
    }
    concept = {
        "concept_id": _first_present(
            teaching.get("concept_id"),
            demo_summary.get("adaptive_path_resolved_concept_id"),
            demo_summary.get("final_concept"),
        ),
        "concept_name": _first_present(
            teaching.get("concept_name"),
            demo_summary.get("adaptive_path_resolved_concept_name"),
            demo_summary.get("final_concept_name"),
            demo_summary.get("concept_name"),
        ),
        "domain": _first_present(
            teaching.get("domain"),
            demo_summary.get("adaptive_path_resolved_domain"),
            demo_summary.get("domain"),
        ),
        "difficulty": _first_present(
            teaching.get("difficulty"),
            strategy.get("difficulty"),
            demo_summary.get("final_difficulty"),
        ),
    }
    cognitutor_lm_compact = {
        "status": cognitutor_lm_output.get("status", "unavailable")
        if cognitutor_lm_output
        else "unavailable",
        "output": cognitutor_lm_output,
    }
    voice_script_output = _as_dict(
        full_output.get("voice_script_output")
        or demo_output.get("voice_script_output")
    )
    voice_script_bundle = _as_dict(
        full_output.get("voice_script_bundle")
        or demo_output.get("voice_script_bundle")
    )
    if not voice_script_output and not voice_script_bundle:
        try:
            from tutor.generation.voice_script_generator import VoiceScriptGenerator

            key_points = _as_list(teaching.get("key_points"))
            if not key_points:
                for item in _as_list(teaching.get("items")):
                    key_points.extend(_as_list(_as_dict(item).get("bullets")))
            voice_evidence = {
                "concept_name": concept.get("concept_name"),
                "teaching_view": selected_teaching_view,
                "difficulty": concept.get("difficulty"),
                "learner_level": demo_summary.get("learner_level"),
                "mistake_type": _first_present(
                    evaluation_fusion_output.get("dominant_mistake_type"),
                    mistake_analysis_output.get("dominant_mistake_type"),
                ),
                "weakest_skill": _first_present(
                    _as_dict(evaluation_fusion_output.get("weakest_skill_signal")).get("weakest_skill"),
                    demo_summary.get("weakest_skill"),
                ),
                "evaluation_label": _first_present(
                    evaluation_fusion_output.get("fused_label"),
                    evaluation.get("verdict"),
                ),
                "doubt_intent": _first_present(
                    _as_dict(full_output.get("doubt_output")).get("doubt_type"),
                    _as_dict(demo_output.get("doubt_output")).get("doubt_type"),
                ),
                "next_action": _first_present(
                    demo_summary.get("next_action"),
                    strategy.get("next_activity"),
                    demo_summary.get("progression_action"),
                ),
                "key_points": key_points,
                "example": _first_present(
                    teaching_card.get("content"),
                    teaching.get("example"),
                    teaching.get("body"),
                ),
            }
            voice_script_output = VoiceScriptGenerator().generate(
                script_type="teaching_explanation",
                evidence=voice_evidence,
            )
            voice_script_bundle = VoiceScriptGenerator().generate_bundle(voice_evidence)
        except Exception as exc:
            voice_script_output = {
                "status": "unavailable",
                "module": "VoiceScriptGenerator",
                "script_type": "teaching_explanation",
                "concept_name": concept.get("concept_name"),
                "text": "",
                "tts_ready": False,
                "estimated_duration_sec": 0,
                "tone": "supportive",
                "frontend_component": "VoiceScriptCard",
                "limitations": [f"{type(exc).__name__}: voice script generation unavailable."],
            }
            voice_script_bundle = {
                "status": "unavailable",
                "module": "VoiceScriptGenerator",
                "scripts": [],
                "frontend_component": "VoiceScriptCard",
            }
    adaptive_hint_output = _as_dict(
        full_output.get("adaptive_hint_output")
        or demo_output.get("adaptive_hint_output")
    )
    if not adaptive_hint_output:
        try:
            from tutor.policy.adaptive_hint_policy import AdaptiveHintPolicy

            first_question = _as_dict(compact_questions[0]) if compact_questions else {}
            first_result = _as_dict(_as_list(evaluation.get("results"))[0]) if _as_list(evaluation.get("results")) else {}
            mastery_score = _first_present(
                _as_dict(_as_dict(_as_dict(full_output.get("knowledge_state")).get("data")).get("data")).get("predicted_mastery_last"),
                default=0.5,
            )
            behaviour_risk = _first_present(
                _as_dict(_as_dict(full_output.get("behaviour_state")).get("data")).get("behavior_score"),
                default=0.3,
            )
            adaptive_hint_output = AdaptiveHintPolicy().select_hint(
                {
                    "learner_id": full_output.get("learner_id"),
                    "concept_id": concept.get("concept_id"),
                    "concept_name": concept.get("concept_name"),
                    "question_type": _first_present(
                        first_question.get("question_type"),
                        first_result.get("question_type"),
                        first_result.get("assessment_type"),
                        default="general",
                    ),
                    "learner_answer": _first_present(
                        _as_dict(full_output.get("learner_answers_used")).get(first_question.get("question_type")),
                        default="",
                    ),
                    "expected_answer": first_question.get("expected_answer"),
                    "score": _first_present(
                        first_result.get("score"),
                        evaluation.get("overall_score"),
                        evaluation_fusion_output.get("fused_score"),
                        default=0.5,
                    ),
                    "evaluation_label": _first_present(
                        evaluation_fusion_output.get("fused_label"),
                        evaluation.get("verdict"),
                        default="unknown",
                    ),
                    "mistake_type": _first_present(
                        evaluation_fusion_output.get("dominant_mistake_type"),
                        mistake_analysis_output.get("dominant_mistake_type"),
                        default="unknown",
                    ),
                    "weakest_skill": _first_present(
                        _as_dict(evaluation_fusion_output.get("weakest_skill_signal")).get("weakest_skill"),
                        demo_summary.get("weakest_skill"),
                        default="current skill",
                    ),
                    "behaviour_risk": behaviour_risk,
                    "mastery_score": mastery_score,
                    "hint_count_used": full_output.get("hint_count_used", 0),
                    "difficulty": concept.get("difficulty"),
                    "teaching_view": selected_teaching_view,
                    "key_points": _as_list(teaching.get("key_points")),
                    "example": _first_present(
                        teaching.get("examples"),
                        teaching.get("examples_base"),
                        teaching_card.get("content"),
                    ),
                }
            )
        except Exception as exc:
            adaptive_hint_output = {
                "status": "unavailable",
                "module": "AdaptiveHintPolicy",
                "hint_type": "guided_hint",
                "hint_level": "guided_hint",
                "hint_text": "Review the main idea, then try one small step before answering again.",
                "support_need": 0.5,
                "evidence": {},
                "frontend_component": "AdaptiveHintCard",
                "fallback_used": True,
                "reason": f"{type(exc).__name__}: adaptive hint unavailable.",
            }
    learned_hint_output = _as_dict(
        full_output.get("learned_hint_output")
        or demo_output.get("learned_hint_output")
    )
    tools = {
        "code_runner_enabled": True,
        "doubt_handler_enabled": True,
        "voice_script_enabled": voice_script_output.get("status") == "success",
        "adaptive_hint_enabled": adaptive_hint_output.get("status") == "success",
        "returning_learner_available": True,
        "production_memory_enabled": learner_memory.get("status") == "success",
    }
    try:
        from tutor.xai.xai_dashboard_builder import XAIDashboardBuilder

        xai_dashboard = XAIDashboardBuilder().build(
            integrated_output=full_output,
            learner_id=full_output.get("learner_id"),
            concept_id=concept.get("concept_id"),
        )
    except Exception as exc:
        xai_dashboard = {
            "status": "unavailable",
            "module": "XAIDashboardBuilder",
            "reason": f"{type(exc).__name__}: {exc}",
        }
    try:
        from tutor.reward.badge_engine import BadgeEngine
        from tutor.reward.concept_unlock_store import ConceptUnlockStore
        from tutor.reward.daily_goal_engine import DailyGoalEngine

        learner_id = str(full_output.get("learner_id") or "")
        badge_output = BadgeEngine().evaluate_and_award(learner_id)
        daily_goal_output = DailyGoalEngine().update_goal(learner_id)
        concept_unlock_output = ConceptUnlockStore().update_unlock_state(
            learner_id=learner_id,
            concept_id=str(concept.get("concept_id") or demo_summary.get("final_concept") or ""),
            domain=concept.get("domain"),
            concept_name=concept.get("concept_name"),
            mastery_score=_first_present(
                _as_dict(_as_dict(_as_dict(full_output.get("knowledge_state")).get("data")).get("data")).get("predicted_mastery_last"),
                default=0.0,
            ),
            promotion_confidence=_first_present(
                demo_summary.get("promotion_confidence"),
                progression_result.get("promotion_confidence"),
                default=0.0,
            ),
            prerequisites_met=not bool(demo_summary.get("adaptive_path_fallback_used")),
            fused_score=_first_present(
                demo_summary.get("fused_score"),
                evaluation_fusion_output.get("fused_score"),
                default=0.0,
            ),
            review_due=bool(_as_dict(full_output.get("forgetting_state")).get("data", {}).get("review_queue")),
            evidence={"source": "frontend_response_builder"},
        )
        reward_gamification = {
            "status": "success",
            "xp": {
                "xp_awarded": reward_state.get("xp_awarded"),
                "total_xp": reward_persistence_output.get("total_xp"),
                "daily_xp": reward_persistence_output.get("daily_xp"),
                "weekly_xp": reward_persistence_output.get("weekly_xp"),
                "current_level": reward_persistence_output.get("current_level"),
            },
            "streak": {
                "current_streak": reward_persistence_output.get("current_streak"),
                "longest_streak": reward_persistence_output.get("longest_streak"),
                "last_active_date": reward_persistence_output.get("last_daily_reset_date"),
            },
            "badges": badge_output,
            "daily_goal": daily_goal_output,
            "concept_unlock": concept_unlock_output,
        }
    except Exception as exc:
        reward_gamification = {
            "status": "unavailable",
            "module": "reward_gamification",
            "reason": f"{type(exc).__name__}: {exc}",
        }

    return {
        "status": full_output.get("status", "success"),
        "learner_id": full_output.get("learner_id"),
        "timestamp": full_output.get("timestamp"),
        "concept": concept,
        "selected_teaching_view": selected_teaching_view,
        "teaching_card": teaching_card,
        "assessment_questions": compact_questions,
        "puzzle_activities": puzzle_activities,
        "revision": {
            "notebook_summary": notebook_summary,
            "flashcards": flashcards,
            "mindmap": mindmap,
            "revision_summary": revision_summary,
            "returning_learner_context": learner_memory,
            "retention_prediction": _first_present(
                full_output.get("retention_prediction"),
                _as_dict(full_output.get("revision_scheduler_output")).get("retention_prediction"),
                demo_output.get("retention_prediction"),
            ),
        },
        "learner_memory": learner_memory,
        "tools": tools,
        "adaptive_hint": {
            "status": adaptive_hint_output.get("status"),
            "hint_type": adaptive_hint_output.get("hint_type"),
            "hint_text": adaptive_hint_output.get("hint_text"),
            "support_need": adaptive_hint_output.get("support_need"),
            "frontend_component": adaptive_hint_output.get("frontend_component", "AdaptiveHintCard"),
            "full_output": adaptive_hint_output,
        },
        "learned_hint": {
            "status": learned_hint_output.get("status"),
            "model_used": learned_hint_output.get("model_used"),
            "fallback_used": learned_hint_output.get("fallback_used"),
            "hint_type": learned_hint_output.get("hint_type"),
            "hint_level": learned_hint_output.get("hint_level"),
            "hint_text": learned_hint_output.get("hint_text"),
            "predicted_success_probability": learned_hint_output.get("predicted_success_probability"),
            "confidence": learned_hint_output.get("confidence"),
            "top_features": learned_hint_output.get("top_features", []),
            "frontend_component": learned_hint_output.get("frontend_component", "AdaptiveHintCard"),
            "full_output": learned_hint_output,
        },
        "adaptive_hint_output": adaptive_hint_output,
        "learned_hint_output": learned_hint_output,
        "voice_script": voice_script_output,
        "voice_scripts": voice_script_bundle.get("scripts", []),
        "voice_script_bundle": voice_script_bundle,
        "cognitutor_lm": cognitutor_lm_compact,
        "reward": {
            "xp_awarded": reward_state.get("xp_awarded"),
            "reward_reason": reward_state.get("reason")
            or reward_persistence_output.get("reward_reason"),
            "celebration_type": celebration.get("type"),
            "celebration_message": celebration.get("message"),
        },
        "reward_gamification": reward_gamification,
        "progress": {
            "progression_action": demo_summary.get("progression_action")
            or progression_result.get("progression_action"),
            "promotion_allowed": demo_summary.get("promotion_allowed")
            if demo_summary.get("promotion_allowed") is not None
            else progression_result.get("promotion_allowed"),
            "concept_cleared": demo_summary.get("concept_cleared")
            if demo_summary.get("concept_cleared") is not None
            else progression_result.get("concept_cleared"),
            "promotion_confidence": demo_summary.get("promotion_confidence")
            or progression_result.get("promotion_confidence"),
        },
        "rubric_evaluation": {
            "status": rubric_evaluation_output.get("status"),
            "module": rubric_evaluation_output.get("module"),
            "mode": rubric_mode,
            "overall_score": rubric_evaluation_output.get("overall_score"),
            "verdict": rubric_evaluation_output.get("verdict"),
            "weak_assessment_types": rubric_evaluation_output.get("weak_assessment_types", []),
            "strong_assessment_types": rubric_evaluation_output.get("strong_assessment_types", []),
            "results": rubric_evaluation_output.get("results", []),
        },
        "debug_evaluation": {
            "status": debug_evaluation_output.get("status"),
            "module": debug_evaluation_output.get("module"),
            "mode": debug_evaluation_mode,
            "overall_score": debug_evaluation_output.get("overall_score"),
            "quality_label": debug_evaluation_output.get("quality_label"),
            "debug_question_count": debug_evaluation_output.get("debug_question_count"),
            "results": debug_evaluation_output.get("results", []),
        },

        "output_prediction_evaluation": {
            "status": output_prediction_evaluation_output.get("status"),
            "module": output_prediction_evaluation_output.get("module"),
            "mode": output_prediction_evaluation_mode,
            "overall_score": output_prediction_evaluation_output.get("overall_score"),
            "quality_label": output_prediction_evaluation_output.get("quality_label"),
            "output_prediction_question_count": output_prediction_evaluation_output.get(
                "output_prediction_question_count"
            ),
            "dominant_output_error_type": output_prediction_evaluation_output.get(
                "dominant_output_error_type"
            ),
            "output_error_type_counts": output_prediction_evaluation_output.get(
                "output_error_type_counts", {}
            ),
            "results": output_prediction_evaluation_output.get("results", []),
        },
        "evaluation_fusion": {
            "status": evaluation_fusion_output.get("status"),
            "module": evaluation_fusion_output.get("module"),
            "mode": evaluation_fusion_mode,
            "fused_score": evaluation_fusion_output.get("fused_score"),
            "fused_label": evaluation_fusion_output.get("fused_label"),
            "recommended_learning_signal": evaluation_fusion_output.get(
                "recommended_learning_signal"
            ),
            "fusion_confidence": evaluation_fusion_output.get("fusion_confidence"),
            "fusion_confidence_label": evaluation_fusion_output.get(
                "fusion_confidence_label"
            ),
            "evaluator_scores": evaluation_fusion_output.get("evaluator_scores", {}),
            "evaluator_agreement": evaluation_fusion_output.get("evaluator_agreement"),
            "weakest_skill_signal": evaluation_fusion_output.get(
                "weakest_skill_signal", {}
            ),
            "dominant_mistake_type": evaluation_fusion_output.get(
                "dominant_mistake_type"
            ),
            "high_severity_mistake_count": evaluation_fusion_output.get(
                "high_severity_mistake_count"
            ),
            "reason": evaluation_fusion_output.get("reason"),
        },

        "summary": {
            "final_concept": demo_summary.get("final_concept"),
            "final_concept_name": demo_summary.get("final_concept_name"),
            "final_strategy": demo_summary.get("final_strategy"),
            "final_difficulty": demo_summary.get("final_difficulty"),
            "explanation_mode": demo_summary.get("explanation_mode"),
            "evaluation_score": demo_summary.get("evaluation_score"),
            "dominant_mistake_type": demo_summary.get(
                "dominant_mistake_type",
                mistake_analysis_output.get("dominant_mistake_type"),
            ),
            "mistake_type_counts": demo_summary.get(
                "mistake_type_counts",
                mistake_analysis_output.get("mistake_type_counts", {}),
            ),
            "high_severity_mistake_count": demo_summary.get(
                "high_severity_mistake_count",
                mistake_analysis_output.get("high_severity_count"),
            ),
            "final_action": demo_summary.get("final_action"),

            "teaching_view": demo_summary.get("teaching_view"),
            "frontend_selected_view": demo_summary.get("frontend_selected_view"),
            "frontend_selected_display_type": demo_summary.get("frontend_selected_display_type"),
            "frontend_view_adapter_status": demo_summary.get("frontend_view_adapter_status"),

            "assessment_types": demo_summary.get("assessment_types", []),
            "assessment_question_count": demo_summary.get("assessment_question_count"),
            "assessment_frontend_ready": demo_summary.get("assessment_frontend_ready"),
            "assessment_frontend_components": demo_summary.get("assessment_frontend_components", []),
            "expanded_question_types_added": demo_summary.get("expanded_question_types_added", []),

            "structured_evaluation_status": demo_summary.get("structured_evaluation_status"),
            "structured_question_count": demo_summary.get("structured_question_count"),
            "structured_question_types": demo_summary.get("structured_question_types", []),
            "promotion_confidence": demo_summary.get(
                "promotion_confidence",
                progression_result.get("promotion_confidence"),
            ),
            "promotion_allowed": demo_summary.get(
                "promotion_allowed",
                progression_result.get("promotion_allowed"),
            ),
            "level_up_allowed": demo_summary.get(
                "level_up_allowed",
                progression_result.get("level_up_allowed"),
            ),
            "concept_cleared": demo_summary.get(
                "concept_cleared",
                progression_result.get("concept_cleared"),
            ),
            "reward_xp_awarded": demo_summary.get(
                "reward_xp_awarded",
                reward_state.get("xp_awarded"),
            ),
            "streak_updated": demo_summary.get(
                "streak_updated",
                reward_state.get("streak_updated"),
            ),
            "celebration_type": demo_summary.get(
                "celebration_type",
                celebration.get("type"),
            ),
            "celebration_message": demo_summary.get(
                "celebration_message",
                celebration.get("message"),
            ),

            "reward_persistence_status": demo_summary.get(
                "reward_persistence_status",
                reward_persistence_output.get("status"),
            ),
            "total_xp": demo_summary.get(
                "total_xp",
                reward_persistence_output.get("total_xp"),
            ),
            "daily_xp": demo_summary.get(
                "daily_xp",
                reward_persistence_output.get("daily_xp"),
            ),
            "weekly_xp": demo_summary.get(
                "weekly_xp",
                reward_persistence_output.get("weekly_xp"),
            ),
            "current_level": demo_summary.get(
                "current_level",
                reward_persistence_output.get("current_level"),
            ),
            "current_streak": demo_summary.get(
                "current_streak",
                reward_persistence_output.get("current_streak"),
            ),
            "longest_streak": demo_summary.get(
                "longest_streak",
                reward_persistence_output.get("longest_streak"),
            ),

            "dominant_mistake_type": demo_summary.get(
                "dominant_mistake_type",
                mistake_analysis_output.get("dominant_mistake_type"),
            ),
            "mistake_type_counts": demo_summary.get(
                "mistake_type_counts",
                mistake_analysis_output.get("mistake_type_counts", {}),
            ),
            "high_severity_mistake_count": demo_summary.get(
                "high_severity_mistake_count",
                mistake_analysis_output.get("high_severity_count"),
            ),
            "rubric_evaluation_status": demo_summary.get(
                "rubric_evaluation_status",
                rubric_evaluation_output.get("status"),
            ),
            "rubric_overall_score": demo_summary.get(
                "rubric_overall_score",
                rubric_evaluation_output.get("overall_score"),
            ),
            "rubric_verdict": demo_summary.get(
                "rubric_verdict",
                rubric_evaluation_output.get("verdict"),
            ),
            "rubric_mode": demo_summary.get(
                "rubric_mode",
                rubric_mode,
            ),
            "debug_evaluation_status": demo_summary.get(
                "debug_evaluation_status",
                debug_evaluation_output.get("status"),
            ),
            "debug_evaluation_score": demo_summary.get(
                "debug_evaluation_score",
                debug_evaluation_output.get("overall_score"),
            ),
            "debug_evaluation_label": demo_summary.get(
                "debug_evaluation_label",
                debug_evaluation_output.get("quality_label"),
            ),
            "debug_evaluation_mode": demo_summary.get(
                "debug_evaluation_mode",
                debug_evaluation_mode,
            ),
            "output_prediction_evaluation_status": demo_summary.get(
                "output_prediction_evaluation_status",
                output_prediction_evaluation_output.get("status"),
            ),
            "output_prediction_evaluation_score": demo_summary.get(
                "output_prediction_evaluation_score",
                output_prediction_evaluation_output.get("overall_score"),
            ),
            "output_prediction_evaluation_label": demo_summary.get(
                "output_prediction_evaluation_label",
                output_prediction_evaluation_output.get("quality_label"),
            ),
            "output_prediction_error_type": demo_summary.get(
                "output_prediction_error_type",
                output_prediction_evaluation_output.get("dominant_output_error_type"),
            ),
            "output_prediction_evaluation_mode": demo_summary.get(
                "output_prediction_evaluation_mode",
                output_prediction_evaluation_mode,
            ),
            "evaluation_fusion_status": demo_summary.get(
                "evaluation_fusion_status",
                evaluation_fusion_output.get("status"),
            ),
            "evaluation_fusion_mode": demo_summary.get(
                "evaluation_fusion_mode",
                evaluation_fusion_mode,
            ),
            "fused_score": demo_summary.get(
                "fused_score",
                evaluation_fusion_output.get("fused_score"),
            ),
            "fused_label": demo_summary.get(
                "fused_label",
                evaluation_fusion_output.get("fused_label"),
            ),
            "recommended_learning_signal": demo_summary.get(
                "recommended_learning_signal",
                evaluation_fusion_output.get("recommended_learning_signal"),
            ),
            "evaluator_agreement": demo_summary.get(
                "evaluator_agreement",
                evaluation_fusion_output.get("evaluator_agreement"),
            ),
            "fusion_confidence": demo_summary.get(
                "fusion_confidence",
                evaluation_fusion_output.get("fusion_confidence"),
            ),
            "fusion_confidence_label": demo_summary.get(
                "fusion_confidence_label",
                evaluation_fusion_output.get("fusion_confidence_label"),
            ),
            "weakest_skill": demo_summary.get(
                "weakest_skill",
                evaluation_fusion_output.get("weakest_skill_signal", {}).get("weakest_skill"),
            ),

            "next_activity": demo_summary.get("next_activity"),
            "progression_action": demo_summary.get("progression_action"),

            "model_teaching_view": demo_summary.get("model_teaching_view"),
            "model_progression_action": demo_summary.get("model_progression_action"),
            "progression_model_status": demo_summary.get("progression_model_status"),
            "progression_model_reason": demo_summary.get("progression_model_reason"),
            "model_teaching_view_confidence": demo_summary.get("model_teaching_view_confidence"),
            "teaching_strategy_agreement": demo_summary.get("teaching_strategy_agreement"),

            "notebook_summary": demo_summary.get("notebook_summary"),
            "next_practice_queue": demo_summary.get("next_practice_queue", []),
        },

        "teaching_plan": {
            "teaching_view": strategy.get("teaching_view") or demo_summary.get("teaching_view"),
            "assessment_difficulty": strategy.get("assessment_difficulty"),
            "assessment_types": strategy.get("assessment_types", demo_summary.get("assessment_types", [])),
            "fallback_views": strategy.get("fallback_views", demo_summary.get("fallback_views", [])),
            "next_activity": strategy.get("next_activity") or demo_summary.get("next_activity"),
            "progression_action": strategy.get("progression_action") or demo_summary.get("progression_action"),
            "reason": strategy.get("reason"),
        },

        "teaching": {
            "concept_id": teaching.get("concept_id"),
            "concept_name": teaching.get("concept_name"),
            "difficulty": teaching.get("difficulty"),
            "selected_view": selected_teaching_view,
            "component": _component_for_teaching_view(selected_teaching_view),
            "card": teaching_card,
            "item_count": teaching.get("item_count"),
            "recommended_view": teaching.get("recommended_view"),
            "available_views": available_views,
            "fallback_views": fallback_views,
            "items": _compact_teaching_items(teaching),
            "frontend_teaching_view": frontend_teaching_view,
        },

        "assessment": {
            "status": assessment.get("status"),
            "concept_id": assessment.get("concept_id"),
            "concept_name": assessment.get("concept_name"),
            "difficulty": assessment.get("difficulty"),
            "question_count": assessment.get("question_count"),
            "frontend_ready": assessment.get("frontend_ready"),
            "frontend_components_used": assessment.get("frontend_components_used", []),
            "components": [
                question.get("frontend_component")
                for question in compact_questions
                if question.get("frontend_component")
            ],
            "supported_question_types": assessment.get("supported_question_types", []),
            "supported_interactive_types": assessment.get(
                "supported_interactive_types",
                ALL_PUZZLE_TYPES,
            ),
            "frontend_component_map": assessment.get(
                "frontend_component_map",
                FRONTEND_COMPONENT_MAP,
            ),
            "puzzle_questions": puzzle_questions,
            "puzzle_activities": puzzle_activities,
            "expanded_question_types_added": assessment.get("expanded_question_types_added", []),
            "questions": compact_questions,
            "full_assessment": assessment,
        },

        "structured_evaluation_output": structured_evaluation_output,

        "structured_evaluation": {
            "status": structured_evaluation_output.get("status"),
            "module": structured_evaluation_output.get("module"),
            "structured_question_count": structured_evaluation_output.get("structured_question_count"),
            "structured_question_types": structured_evaluation_output.get("structured_question_types", []),
            "used_simulated_answers": structured_evaluation_output.get("used_simulated_answers"),
            "reason": structured_evaluation_output.get("reason"),
            "overall_score": structured_evaluation.get("overall_score"),
            "verdict": structured_evaluation.get("verdict"),
            "weak_assessment_types": structured_evaluation.get("weak_assessment_types", []),
            "strong_assessment_types": structured_evaluation.get("strong_assessment_types", []),
            "results": structured_evaluation.get("results", []),
        },

        "evaluation": {
            "status": evaluation.get("status"),
            "overall_score": evaluation.get("overall_score"),
            "verdict": evaluation.get("verdict"),
            "feedback_summary": evaluation.get("feedback_summary"),
            "results": evaluation.get("results", []),
        },



        "mistake_analysis": {
            "status": mistake_analysis_output.get("status"),
            "module": mistake_analysis_output.get("module"),
            "dominant_mistake_type": mistake_analysis_output.get("dominant_mistake_type"),
            "mistake_type_counts": mistake_analysis_output.get("mistake_type_counts", {}),
            "high_severity_count": mistake_analysis_output.get("high_severity_count"),
            "medium_or_high_count": mistake_analysis_output.get("medium_or_high_count"),
            "classified_mistakes": mistake_analysis_output.get("classified_mistakes", []),
        },

        "decision": {
            "policy_output": full_output.get("policy_output", {}),
            "model_based_teaching_strategy": full_output.get("model_based_teaching_strategy_output", {}),
            "learned_teaching_strategy": full_output.get("learned_teaching_strategy_output", {}),
            "learned_path_ranker": full_output.get("learned_path_ranker_output", {}),
            "learned_hint": full_output.get("learned_hint_output", {}),
            "teaching_strategy_agreement": (
                full_output.get("teaching_strategy_agreement")
                if full_output.get("teaching_strategy_agreement") is not None
                else demo_summary.get("teaching_strategy_agreement")
            ),
            "progression_model_status": demo_summary.get("progression_model_status"),
            "progression_model_reason": demo_summary.get("progression_model_reason"),
        },

        "notebook_memory": {
            "notebook_summary": notebook.get("notebook_summary") or demo_summary.get("notebook_summary"),
            "mistake_patterns": notebook.get("mistake_patterns", []),
            "weak_assessment_types": notebook.get("weak_assessment_types", []),
            "strengths": notebook.get("strengths", []),
            "revision_plan": notebook.get("revision_plan", []),
            "next_practice_queue": (
                notebook.get("next_practice_queue")
                or demo_summary.get("next_practice_queue", [])
            ),
        },

        "xai": {
            "reason": xai_data.get("reason"),
            "evidence": xai_data.get("evidence", {}),
            "top_factors": (
                _as_dict(xai_data.get("evidence"))
                .get("feature_contributions", {})
                .get("top_factors", [])
            ),
        },
        "xai_dashboard": {
            "cards": xai_dashboard.get("cards", {}),
            "top_factors": xai_dashboard.get("top_factors", []),
            "factor_contributions": xai_dashboard.get("factor_contributions", {}),
            "counterfactuals": xai_dashboard.get("counterfactuals", []),
            "evidence_coverage": xai_dashboard.get("evidence_coverage", {}),
            "explanation_quality": xai_dashboard.get("explanation_quality", {}),
            "status": xai_dashboard.get("status"),
            "module": xai_dashboard.get("module"),
        },

        "progression_reward_output": progression_reward_output,

        "progression_result": progression_result,

        "promotion_confidence": promotion_confidence_output,
        "promotion_confidence_output": promotion_confidence_output,

        "reward_state": reward_state,

        "reward_persistence_output": reward_persistence_output,

        "persistent_reward_state": {
            "status": reward_persistence_output.get("status"),
            "mode": reward_persistence_output.get("mode"),
            "learner_id": reward_persistence_output.get("learner_id"),
            "xp_awarded": reward_persistence_output.get("xp_awarded"),
            "total_xp": reward_persistence_output.get("total_xp"),
            "daily_xp": reward_persistence_output.get("daily_xp"),
            "weekly_xp": reward_persistence_output.get("weekly_xp"),
            "current_level": reward_persistence_output.get("current_level"),
            "last_daily_reset_date": reward_persistence_output.get("last_daily_reset_date"),
            "last_weekly_reset_date": reward_persistence_output.get("last_weekly_reset_date"),
            "current_streak": reward_persistence_output.get("current_streak"),
            "longest_streak": reward_persistence_output.get("longest_streak"),
            "event_logged": reward_persistence_output.get("event_logged"),
            "reward_reason": reward_persistence_output.get("reward_reason"),
            "celebration_type": reward_persistence_output.get("celebration_type"),
            "progression_action": reward_persistence_output.get("progression_action"),
            "model_progression_action": reward_persistence_output.get("model_progression_action"),
        },

        "celebration": celebration,

        "frontend_contract": compact_frontend_contract,

        "logging": {
            "teaching_strategy_training_log": training_log,
        },
        "model_comparison_status": progression_reward_output.get(
            "model_comparison_status"
        ),
        "model_comparison_output": progression_reward_output.get(
            "model_comparison_output", {}
        ),

        # Backward-compatible top-level fields
        "frontend_teaching_view": frontend_teaching_view,
        "structured_evaluation_status": demo_summary.get("structured_evaluation_status"),
        "structured_question_count": demo_summary.get("structured_question_count"),
        "structured_question_types": demo_summary.get("structured_question_types", []),
    }
