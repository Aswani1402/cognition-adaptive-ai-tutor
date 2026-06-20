from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
FRONTEND_ROOT = PROJECT_ROOT / "frontend_ui" / "KP-UI"
TASK_MAP_FILE = FRONTEND_ROOT / "src" / "lib" / "taskTypeMap.ts"


REQUIRED_TASK_TYPES = {
    "teaching": [
        "explanation",
        "definition_view",
        "simple_example_view",
        "step_by_step_view",
        "analogy_view",
        "code_view",
        "misconception_view",
        "debug_view",
        "output_prediction_view",
        "transfer_view",
        "challenge_view",
        "revision_summary_view",
        "comparison_view",
        "real_world_connection_view",
    ],
    "assessment": [
        "mcq",
        "debug_task",
        "output_prediction",
        "transfer_question",
        "challenge_question",
        "explanation_check",
        "syntax_completion",
        "coding_prompt",
        "code_reasoning_task",
        "fill_in_the_blank",
        "true_or_false",
    ],
    "revision": [
        "revision_note",
        "revision_summary",
        "weakness_review",
        "daily_review",
        "personal_revision_plan",
        "recommended_revision_views",
        "spaced_repetition_card",
    ],
    "flashcards": [
        "flashcard",
        "concept_recall_flashcard",
        "misconception_flashcard",
        "example_flashcard",
        "debug_flashcard",
        "personal_flashcards",
        "syntax_flashcard",
    ],
    "mindmaps": ["mindmap", "concept_mindmap", "comparison_mindmap"],
    "feedback": [
        "feedback",
        "correct_answer_feedback",
        "wrong_answer_feedback",
        "partial_answer_feedback",
        "debug_feedback",
        "output_prediction_feedback",
        "next_step_feedback",
        "encouragement_feedback",
    ],
    "hints": [
        "hint",
        "small_hint",
        "guided_hint",
        "worked_example_hint",
        "debug_hint",
        "syntax_hint",
        "output_prediction_hint",
        "misconception_hint",
        "next_step_hint",
        "analogy_hint",
    ],
    "doubt": [
        "doubt_answer",
        "concept_doubt_answer",
        "syntax_doubt_answer",
        "debug_doubt_answer",
        "output_doubt_answer",
        "example_request_answer",
        "revision_doubt_answer",
        "next_step_doubt_answer",
        "comparison_doubt_answer",
    ],
    "notebook": [
        "notebook_summary",
        "mistake_summary",
        "revision_plan",
        "comeback_summary",
        "returning_learner_summary",
        "progress_insight",
    ],
    "practice": [
        "practice_question",
        "transfer_task",
        "real_world_application_question",
        "debug_challenge",
        "output_prediction_challenge",
        "multi_step_challenge",
    ],
    "voice_script": [
        "voice_script",
        "teaching_voice_script",
        "revision_voice_script",
        "mistake_feedback_voice_script",
        "doubt_explanation_voice_script",
        "encouragement_script",
        "next_step_guidance_script",
        "concept_intro_voice_script",
    ],
}


FORBIDDEN_TASK_PAGES = [
    "DefinitionViewPage.tsx",
    "SimpleExampleViewPage.tsx",
    "StepByStepViewPage.tsx",
    "AnalogyViewPage.tsx",
    "CodeViewPage.tsx",
    "MisconceptionViewPage.tsx",
    "DebugViewPage.tsx",
    "OutputPredictionViewPage.tsx",
    "TransferViewPage.tsx",
    "ChallengeViewPage.tsx",
    "MCQPage.tsx",
    "FillInTheBlankPage.tsx",
    "TrueOrFalsePage.tsx",
    "DebugTaskPage.tsx",
    "OutputPredictionPage.tsx",
    "CodingPromptPage.tsx",
    "HintPage.tsx",
    "FeedbackPage.tsx",
    "VoiceScriptPage.tsx",
]


def main() -> None:
    assert TASK_MAP_FILE.exists(), f"Missing task type mapping file: {TASK_MAP_FILE}"
    content = TASK_MAP_FILE.read_text(encoding="utf-8")

    missing = []
    for category, task_types in REQUIRED_TASK_TYPES.items():
        for task_type in task_types:
            if f"{task_type}:" not in content:
                missing.append(f"{category}:{task_type}")

    assert not missing, "Missing task type mappings: " + ", ".join(missing)
    assert "CogniGuideCard text only" in content, "Voice scripts must remain text-only in CogniGuideCard."
    assert "GuidedTutorJourney" in content, "Guided learning task types must map into the guided session."
    assert "AssessmentRenderer" in content, "Assessment task types must map into AssessmentRenderer."

    page_dir = FRONTEND_ROOT / "src" / "pages"
    existing_forbidden = [name for name in FORBIDDEN_TASK_PAGES if (page_dir / name).exists()]
    assert not existing_forbidden, "Unexpected separate task pages created: " + ", ".join(existing_forbidden)

    print("Task type mapping covers required task categories without creating per-task pages.")


if __name__ == "__main__":
    main()
