from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MAIN_PROJECT = ROOT.parent / "cognition_adaptive_AI_tutor"
DB_DIR = MAIN_PROJECT / "external" / "core_data"

SUBJECT_DBS = {
    "Python": DB_DIR / "python_learning.db",
    "SQL": DB_DIR / "database_sql.db",
    "HTML": DB_DIR / "html_web_basics.db",
    "Git": DB_DIR / "git_version_control.db",
    "Data Structures": DB_DIR / "data_structures.db",
}

MODEL_CHECKPOINT = ROOT / "models" / "cognitutor_lm_structured_generation" / "best_model.pt"
CORE_OUTPUT = ROOT / "outputs" / "model_generated" / "structured_model_generated_core.json"
RAW_GENERATED_OUTPUT = ROOT / "outputs" / "model_generated" / "structured_model_raw_generation_core.json"
CORE_GENERATED_OUTPUT = CORE_OUTPUT
PACKET_OUTPUT = ROOT / "outputs" / "learning_packets" / "all_learning_packets.json"
LEARNING_PACKET_OUTPUT = PACKET_OUTPUT
ALL_TASK_OUTPUT = ROOT / "outputs" / "model_generated" / "structured_model_generated_all_tasks.json"
ALL_TASK_GENERATED_OUTPUT = ALL_TASK_OUTPUT
BY_SUBJECT_DIR = ROOT / "outputs" / "model_generated" / "by_subject"
BY_CONCEPT_DIR = ROOT / "outputs" / "model_generated" / "by_concept"
REPORTS_DIR = ROOT / "outputs" / "final_reports"
PACKETS_DIR = ROOT / "outputs" / "learning_packets"

TEACHING_VIEWS = [
    "definition_view",
    "simple_example_view",
    "step_by_step_view",
    "analogy_view",
    "code_view",
    "debug_view",
    "output_prediction_view",
    "misconception_view",
    "transfer_view",
    "challenge_view",
    "revision_view",
    "flashcard_view",
    "mindmap_view",
    "voice_script_view",
]

DIFFICULTIES = ["easy", "medium", "hard", "revision"]
STYLES = ["simple", "step_by_step", "analogy", "code", "debug", "revision"]

CORE_TASK_TYPES = [
    "explanation",
    "flashcard",
    "mcq",
    "debug_task",
    "output_prediction",
    "challenge_question",
    "revision_summary",
    "hint",
    "feedback",
    "mindmap",
    "doubt_answer",
    "voice_script",
]

TEACHING_TASKS = [
    "explanation", "definition_view", "simple_example_view", "step_by_step_view",
    "analogy_view", "code_view", "misconception_view", "debug_view",
    "output_prediction_view", "transfer_view", "challenge_view",
    "revision_summary_view", "comparison_view", "real_world_connection_view",
]

ASSESSMENT_TASKS = [
    "mcq", "debug_task", "output_prediction", "transfer_question",
    "challenge_question", "explanation_check", "syntax_completion",
    "coding_prompt", "code_reasoning_task", "fill_in_the_blank", "true_or_false",
]

REVISION_TASKS = [
    "revision_note", "revision_summary", "weakness_review", "daily_review",
    "personal_revision_plan", "recommended_revision_views", "spaced_repetition_card",
]

FLASHCARD_TASKS = [
    "flashcard", "concept_recall_flashcard", "misconception_flashcard",
    "example_flashcard", "debug_flashcard", "personal_flashcards", "syntax_flashcard",
]

MINDMAP_TASKS = ["mindmap", "concept_mindmap", "comparison_mindmap"]

FEEDBACK_TASKS = [
    "feedback", "correct_answer_feedback", "wrong_answer_feedback",
    "partial_answer_feedback", "debug_feedback", "output_prediction_feedback",
    "next_step_feedback", "encouragement_feedback",
]

HINT_TASKS = [
    "hint", "small_hint", "guided_hint", "worked_example_hint", "debug_hint",
    "syntax_hint", "output_prediction_hint", "misconception_hint",
    "next_step_hint", "analogy_hint",
]

DOUBT_TASKS = [
    "doubt_answer", "concept_doubt_answer", "syntax_doubt_answer",
    "debug_doubt_answer", "output_doubt_answer", "example_request_answer",
    "revision_doubt_answer", "next_step_doubt_answer", "comparison_doubt_answer",
]

NOTEBOOK_TASKS = [
    "notebook_summary", "mistake_summary", "revision_plan", "comeback_summary",
    "returning_learner_summary", "progress_insight",
]

PRACTICE_CHALLENGE_TASKS = [
    "practice_question", "transfer_task", "real_world_application_question",
    "debug_challenge", "output_prediction_challenge", "multi_step_challenge",
]

VOICE_TASKS = [
    "voice_script", "teaching_voice_script", "revision_voice_script",
    "mistake_feedback_voice_script", "doubt_explanation_voice_script",
    "encouragement_script", "next_step_guidance_script",
    "concept_intro_voice_script",
]

ALL_TASK_TYPES = (
    TEACHING_TASKS
    + ASSESSMENT_TASKS
    + REVISION_TASKS
    + FLASHCARD_TASKS
    + MINDMAP_TASKS
    + FEEDBACK_TASKS
    + HINT_TASKS
    + DOUBT_TASKS
    + NOTEBOOK_TASKS
    + PRACTICE_CHALLENGE_TASKS
    + VOICE_TASKS
)

ALL_89_TASK_TYPES = ALL_TASK_TYPES

TASK_TOKENS = {task: f"<task_{task}>" for task in ALL_89_TASK_TYPES}
