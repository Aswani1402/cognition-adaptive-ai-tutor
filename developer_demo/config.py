from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = ROOT / "cognition_adaptive_AI_tutor"
COGNITUTOR_ROOT = ROOT / "CogniTutor_LM_from_scratch"
FRONTEND_ROOT = ROOT / "frontend_ui" / "KP-UI"
FINETUNE_ROOT = ROOT / "fine_tuing_llm"

API_BASE_URL = "http://127.0.0.1:8000"
CORE_DATA = BACKEND_ROOT / "external" / "core_data"
TUTOR_DB = CORE_DATA / "tutor.db"

SUBJECT_DBS = {
    "Python": CORE_DATA / "python_learning.db",
    "HTML": CORE_DATA / "html_web_basics.db",
    "SQL": CORE_DATA / "database_sql.db",
    "Git": CORE_DATA / "git_version_control.db",
    "Data Structures": CORE_DATA / "data_structures.db",
}

FALLBACK_PATHS = {
    "Python": ["Variables", "Data Types", "Conditionals", "Loops", "Functions", "OOP"],
    "SQL": ["Database Basics", "SELECT", "WHERE and Filters", "JOIN", "Indexes", "Window Functions", "CTEs"],
    "HTML": ["What is HTML", "HTML Tags and Elements", "Attributes and Links", "Images and Lists", "Forms and Inputs"],
    "Git": ["Version Control", "Git Repositories", "Commits and History", "Branches", "Merge and Conflict Basics"],
    "Data Structures": ["Arrays", "Linked Lists", "Stacks", "Queues", "Trees", "Sets", "Graphs"],
}

RUNTIME_TABLES = [
    "users", "learner_profile", "learner_session_log", "quiz_results", "knowledge_state",
    "behaviour_state", "learner_mistake_log", "learner_doubt_log", "revision_card",
    "revision_schedule", "reward_event_log", "learner_xp_state", "learner_streak_state",
    "learner_badges", "concept_unlock_state", "concept_id_map", "teaching_strategy_log",
    "teaching_strategy_training_log", "policy_decision_log", "rl_experience_log",
    "agent_orchestration_log", "agentic_trace_log", "generation_history", "rag_chunks",
    "rag_resource_bundle", "learner_notebook_memory", "learner_memory_state", "xai_log",
]

MODEL_ARTIFACTS = {
    "DKT artifact": [BACKEND_ROOT / "models" / "dkt" / "model.pt", BACKEND_ROOT / "models" / "dkt" / "dkt_meta.json"],
    "Behaviour LSTM artifact": [BACKEND_ROOT / "models" / "behaviour_lstm" / "model.pt", BACKEND_ROOT / "models" / "behaviour_lstm" / "meta.json"],
    "Policy/RL artifacts": [BACKEND_ROOT / "models" / "rl" / "bandit_policy_model.pkl", BACKEND_ROOT / "models" / "rl" / "dqn" / "dqn_policy_model.pt"],
    "RAG artifacts": [BACKEND_ROOT / "models" / "rag" / "rag_corpus.json", BACKEND_ROOT / "models" / "rag" / "rag_reranker_model.pkl"],
    "Teaching strategy artifacts": [BACKEND_ROOT / "models" / "strategy" / "teaching_strategy_view_model.joblib"],
    "XAI surrogate artifacts": [BACKEND_ROOT / "models" / "xai" / "xai_surrogate_meta.json"],
    "CogniTutorLM reports": [COGNITUTOR_ROOT / "outputs" / "rag_llm_live_guarded" / "reports" / "rag_llm_live_guarded_full_coverage_report.json"],
    "Pretrained fine-tuned comparison": [FINETUNE_ROOT / "finetuning" / "outputs" / "final_reports" / "pretrained_finetuning_track_report.json"],
}

GENERATION_REPORTS = [
    COGNITUTOR_ROOT / "outputs" / "rag_llm_live_guarded" / "reports" / "rag_llm_live_guarded_full_coverage_report.json",
    COGNITUTOR_ROOT / "outputs" / "rag_llm_live_guarded" / "evaluation" / "rag_llm_live_guarded_full_coverage.json",
    COGNITUTOR_ROOT / "outputs" / "model_generated" / "structured_model_generated_all_tasks.json",
    COGNITUTOR_ROOT / "outputs" / "quality" / "generation_quality_report.json",
]

EVENT_LOG = DEMO_ROOT / "outputs" / "event_log.json"
