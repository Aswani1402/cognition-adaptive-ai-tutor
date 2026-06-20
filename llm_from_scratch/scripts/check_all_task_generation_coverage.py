import json
from pathlib import Path

ALL_TASK_TYPES = [
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
    "revision_note",
    "revision_summary",
    "weakness_review",
    "daily_review",
    "personal_revision_plan",
    "recommended_revision_views",
    "spaced_repetition_card",
    "flashcard",
    "concept_recall_flashcard",
    "misconception_flashcard",
    "example_flashcard",
    "debug_flashcard",
    "personal_flashcards",
    "syntax_flashcard",
    "mindmap",
    "concept_mindmap",
    "comparison_mindmap",
    "feedback",
    "correct_answer_feedback",
    "wrong_answer_feedback",
    "partial_answer_feedback",
    "debug_feedback",
    "output_prediction_feedback",
    "next_step_feedback",
    "encouragement_feedback",
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
    "doubt_answer",
    "concept_doubt_answer",
    "syntax_doubt_answer",
    "debug_doubt_answer",
    "output_doubt_answer",
    "example_request_answer",
    "revision_doubt_answer",
    "next_step_doubt_answer",
    "comparison_doubt_answer",
    "notebook_summary",
    "mistake_summary",
    "revision_plan",
    "comeback_summary",
    "returning_learner_summary",
    "progress_insight",
    "practice_question",
    "transfer_task",
    "real_world_application_question",
    "debug_challenge",
    "output_prediction_challenge",
    "multi_step_challenge",
    "voice_script",
    "teaching_voice_script",
    "revision_voice_script",
    "mistake_feedback_voice_script",
    "doubt_explanation_voice_script",
    "encouragement_script",
    "next_step_guidance_script",
    "concept_intro_voice_script",
]

path = Path("outputs/model_generated/structured_model_generated_core.json")
data = json.loads(path.read_text(encoding="utf-8"))

generated_tasks = sorted(set(x["task_type"] for x in data))
missing = sorted(set(ALL_TASK_TYPES) - set(generated_tasks))
extra = sorted(set(generated_tasks) - set(ALL_TASK_TYPES))

print("generated_task_count:", len(generated_tasks))
print("expected_all_task_count:", len(ALL_TASK_TYPES))
print("missing_task_count:", len(missing))
print("extra_task_count:", len(extra))
print("\nGENERATED TASKS:")
for t in generated_tasks:
    print("-", t)
print("\nMISSING TASKS:")
for t in missing:
    print("-", t)

Path("outputs/final_reports").mkdir(parents=True, exist_ok=True)
Path("outputs/final_reports/all_task_generation_coverage_check.json").write_text(
    json.dumps({
        "generated_task_count": len(generated_tasks),
        "expected_all_task_count": len(ALL_TASK_TYPES),
        "generated_tasks": generated_tasks,
        "missing_task_count": len(missing),
        "missing_tasks": missing,
        "extra_task_count": len(extra),
        "extra_tasks": extra,
    }, indent=2, ensure_ascii=False),
    encoding="utf-8",
)
