from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


REPORT_DIR = Path("evaluation_outputs/reports")
JSON_DIR = Path("evaluation_outputs/json")

STATUSES = {
    "FULLY CONNECTED",
    "BACKEND CONNECTED BUT NOT FRONTEND VISIBLE",
    "BACKEND READY WITH FALLBACK",
    "COMPARISON ONLY",
    "PARTIAL",
    "MISSING",
    "BROKEN",
}


MODULES: list[dict[str, Any]] = [
    {
        "module_name": "Knowledge Tracing",
        "folder_file": "tutor/knowledge_state/update.py; tutor/knowledge_state/dkt/dkt_inference.py; models/dkt/model.pt",
        "purpose": "Estimate concept mastery from recent quiz interactions and persist knowledge_state.",
        "inputs": ["learner_id", "concept_id", "is_correct", "quiz_results history", "concept_id_map"],
        "model_algorithm_formula": "DKT artifact if runtime concept ids map to id_map.json; otherwise BKT baseline; otherwise fallback cumulative mastery via simple_infer.",
        "trained_artifact_used": "Available in models/dkt/model.pt and models/kt/bkt_baseline.json for integrated KT; /answer/submit currently writes fallback_cumulative score from answer score.",
        "fallback_used": True,
        "output": ["mastery_score", "mastery_label", "model_used", "fallback_used", "knowledge_state.state_json"],
        "db_tables_read": ["quiz_results", "concept_id_map"],
        "db_tables_written": ["knowledge_state"],
        "called_by": ["tutor/system/run_integrated_tutor_once.py", "tutor/api/evaluation_routes.py"],
        "calls_which_modules": ["tutor.knowledge_state.dkt.dkt_inference", "tutor.knowledge_state.bkt.bkt_baseline"],
        "api_route_connected": True,
        "frontend_visible": True,
        "affects_next_decision": True,
        "status": "BACKEND READY WITH FALLBACK",
        "missing_upgrade_needed": "Use shared KT runtime in /answer/submit when concept id mapping is reliable; report mapped/unmapped ids per update.",
    },
    {
        "module_name": "Behaviour Modelling",
        "folder_file": "tutor/behaviour/lstm_behaviour_model.py; models/behaviour_lstm/model.pt",
        "purpose": "Classify learner behaviour and risk from recent answer signals.",
        "inputs": ["time_taken_sec", "confidence", "hint_used", "hint_count", "option_change_count", "answer_change_count", "run_code_count", "attempt_count", "wrong_attempt_count", "score"],
        "model_algorithm_formula": "Integrated runtime can load BehaviourLSTM over 7-feature sequences; /answer/submit uses engineered behaviour_risk = average of wrong/slow/low_confidence/hint/option_change/answer_change/run_code/retry rates.",
        "trained_artifact_used": "models/behaviour_lstm/model.pt exists for run_behaviour_model; answer-submit does not invoke it live.",
        "fallback_used": False,
        "output": ["stable_score", "confused_score", "guessing_score", "struggling_score", "behaviour_label", "behaviour_risk", "behaviour_confidence"],
        "db_tables_read": ["quiz_results"],
        "db_tables_written": ["behaviour_state", "quiz_results"],
        "called_by": ["tutor/system/run_integrated_tutor_once.py", "tutor/api/evaluation_routes.py"],
        "calls_which_modules": ["tutor.behaviour.behaviour_state_store"],
        "api_route_connected": True,
        "frontend_visible": True,
        "affects_next_decision": True,
        "status": "BACKEND READY WITH FALLBACK",
        "missing_upgrade_needed": "Unify signal names and add live LSTM opt-in only after calibration on current frontend payload distribution.",
    },
    {
        "module_name": "Concept Dependency",
        "folder_file": "tutor/concept_dependency/run_dependency_module_final.py; tutor/path/adaptive_path_validation.py",
        "purpose": "Compute unlocked/blocked concepts and validate next concept IDs.",
        "inputs": ["subject", "concept_id", "prerequisites", "concept_unlock_state", "mastery_score"],
        "model_algorithm_formula": "Prerequisite graph/rule checks with concept_id_map validation; learned ranker exists separately.",
        "trained_artifact_used": "No trained dependency model; path ranker artifacts exist under models/path.",
        "fallback_used": True,
        "output": ["locked", "unlocked", "blocked_concepts", "next_concept_id", "prerequisite_reason"],
        "db_tables_read": ["concept_dependencies", "concept_id_map", "concept_unlock_state"],
        "db_tables_written": ["concept_unlock_state"],
        "called_by": ["tutor/system/run_integrated_tutor_once.py", "tutor/api/path_routes.py", "tutor/api/evaluation_routes.py"],
        "calls_which_modules": ["AdaptivePathSelector"],
        "api_route_connected": True,
        "frontend_visible": True,
        "affects_next_decision": True,
        "status": "BACKEND READY WITH FALLBACK",
        "missing_upgrade_needed": "Make subject-specific dependency DB source explicit in /answer/submit path_update.",
    },
    {
        "module_name": "Adaptive Path",
        "folder_file": "tutor/path/adaptive_path_selector.py; tutor/concept_dependency/learned_adaptive_path_ranker.py",
        "purpose": "Rank next learning actions and difficulties from mastery, behaviour, retention, evaluation and dependency evidence.",
        "inputs": ["mastery", "behaviour_risk", "evaluation_score", "mistake_type", "retention_priority", "dependency_status", "difficulty"],
        "model_algorithm_formula": "Weighted mathematical score: 0.30 low_mastery + 0.25 review_priority + 0.20 evaluation_need + 0.15 behaviour_risk + 0.10 view_reward_need.",
        "trained_artifact_used": "models/path/*.joblib available for learned ranker; answer-submit uses rule progression easy->medium->hard.",
        "fallback_used": True,
        "output": ["path_update", "recommended_next_activity", "next_difficulty", "concept_completed", "next_concept_id"],
        "db_tables_read": ["knowledge_state", "behaviour_state", "concept_unlock_state"],
        "db_tables_written": ["learner_profile", "concept_unlock_state"],
        "called_by": ["tutor/system/run_integrated_tutor_once.py", "tutor/api/evaluation_routes.py"],
        "calls_which_modules": ["AdaptivePolicyBridge", "FeatureContributionExplainer"],
        "api_route_connected": True,
        "frontend_visible": True,
        "affects_next_decision": True,
        "status": "FULLY CONNECTED",
        "missing_upgrade_needed": "Use learned ranker in shadow in answer-submit before promoting it to decision authority.",
    },
    {
        "module_name": "Teaching Strategy",
        "folder_file": "tutor/strategy/*.py; models/strategy/*.joblib; tutor/api/concept_content_resolver.py",
        "purpose": "Select teaching view, assessment types, next activity and explanation reason.",
        "inputs": ["mastery", "behaviour", "mistake_type", "difficulty", "retention_need", "previous_view"],
        "model_algorithm_formula": "Evidence-aware selector plus learned joblib models where available; lesson routes also use deterministic content resolver defaults.",
        "trained_artifact_used": "models/strategy/*.joblib and models/teaching_strategy/*.joblib exist; API lesson route uses resolver/rules.",
        "fallback_used": True,
        "output": ["selected_view", "reason", "available_views", "assessment_types"],
        "db_tables_read": ["teaching_strategy_log", "concept_resources"],
        "db_tables_written": ["teaching_strategy_log", "teaching_strategy_model_comparison_log"],
        "called_by": ["run_integrated_tutor_once", "lesson route", "answer-submit response builder"],
        "calls_which_modules": ["frontend_view_adapter", "voice_script_generator", "concept_content_resolver"],
        "api_route_connected": True,
        "frontend_visible": True,
        "affects_next_decision": True,
        "status": "FULLY CONNECTED",
        "missing_upgrade_needed": "Align lesson route selected_view with model selector output when adaptive session evidence exists.",
    },
    {
        "module_name": "Dynamic Assessment",
        "folder_file": "tutor/assessment/*.py; tutor/api/integration_routes.py",
        "purpose": "Generate multi-type assessment bundles for concept and difficulty.",
        "inputs": ["subject", "concept_id", "difficulty", "teaching_strategy", "concept_resources"],
        "model_algorithm_formula": "Template/resource-driven generation with expanded structured question generators.",
        "trained_artifact_used": "No trained assessment generator in live API; generation policy model exists for task choice.",
        "fallback_used": True,
        "output": ["questions", "supported_question_types", "frontend_components", "coverage"],
        "db_tables_read": ["concept_resources", "question_bank"],
        "db_tables_written": [],
        "called_by": ["/assessment/{learner_id}/{concept_id}", "run_integrated_tutor_once"],
        "calls_which_modules": ["structured_question_types", "expanded_assessment_generator"],
        "api_route_connected": True,
        "frontend_visible": True,
        "affects_next_decision": False,
        "status": "FULLY CONNECTED",
        "missing_upgrade_needed": "Increase database-backed variety for each supported assessment type.",
    },
    {
        "module_name": "Answer Evaluation",
        "folder_file": "tutor/evaluation/answer_evaluator.py; tutor/evaluation/structured_answer_evaluator.py",
        "purpose": "Score learner answers and classify mistakes across structured and semantic tasks.",
        "inputs": ["question", "learner_answer", "expected_answer", "question_type", "rubric"],
        "model_algorithm_formula": "Exact/equivalence checks, structured scoring, lexical/semantic fallback; fusion engine is comparison-only.",
        "trained_artifact_used": "No required trained evaluator artifact; optional embeddings unavailable fallback to lexical.",
        "fallback_used": True,
        "output": ["score", "label", "feedback", "explanation", "mistake_type"],
        "db_tables_read": [],
        "db_tables_written": ["quiz_results", "learner_mistake_log", "revision_schedule"],
        "called_by": ["/answer/submit", "EvaluatorAgent", "structured_evaluation_bridge"],
        "calls_which_modules": ["SafeCodeRunner", "mistake_type_classifier", "evaluation_fusion_engine"],
        "api_route_connected": True,
        "frontend_visible": True,
        "affects_next_decision": True,
        "status": "FULLY CONNECTED",
        "missing_upgrade_needed": "Calibrate semantic thresholds per question type with labeled data.",
    },
    {
        "module_name": "Safe Code Runner",
        "folder_file": "tutor/evaluation/code_runner.py; /code/run",
        "purpose": "Execute simple Python code safely for code/output tasks.",
        "inputs": ["code", "expected_output", "test_cases"],
        "model_algorithm_formula": "Sandboxed subprocess/static safety checks and output comparison.",
        "trained_artifact_used": "No trained artifact.",
        "fallback_used": False,
        "output": ["stdout", "stderr", "execution_status", "score", "blocked_reason"],
        "db_tables_read": [],
        "db_tables_written": [],
        "called_by": ["/code/run", "answer-submit equivalence precheck", "code_question_evaluator"],
        "calls_which_modules": [],
        "api_route_connected": True,
        "frontend_visible": True,
        "affects_next_decision": True,
        "status": "FULLY CONNECTED",
        "missing_upgrade_needed": "Persist run attempts if product analytics needs code-run behaviour evidence.",
    },
    {
        "module_name": "Mistake Analysis",
        "folder_file": "tutor/evaluation/mistake_type_classifier.py; tutor/system/learner_insight_layer.py",
        "purpose": "Classify dominant mistake type and summarize weak skills.",
        "inputs": ["evaluation results", "question_type", "learner_answer", "expected_answer", "score"],
        "model_algorithm_formula": "Rule/keyword classifier and aggregation; no live trained classifier found.",
        "trained_artifact_used": "No trained artifact used live.",
        "fallback_used": True,
        "output": ["mistake_type", "dominant_mistake_type", "weakest_skill", "severity"],
        "db_tables_read": ["learner_mistake_log"],
        "db_tables_written": ["learner_mistake_log"],
        "called_by": ["/answer/submit", "EvaluatorAgent", "LearnerInsightLayer"],
        "calls_which_modules": ["LearnerNotebookMemory", "XAI"],
        "api_route_connected": True,
        "frontend_visible": True,
        "affects_next_decision": True,
        "status": "FULLY CONNECTED",
        "missing_upgrade_needed": "Add labeled mistake taxonomy evaluation by question type.",
    },
    {
        "module_name": "Hint Policy",
        "folder_file": "tutor/policy/adaptive_hint_policy.py; tutor/policy/learned_hint_policy.py; /hint/predict",
        "purpose": "Choose hint level/type from support need and question context.",
        "inputs": ["concept_id", "question_type", "hint_count", "score", "behaviour_risk"],
        "model_algorithm_formula": "Rule adaptive hint policy plus learned hint joblib artifacts when used by integrated runner.",
        "trained_artifact_used": "models/hints/*.joblib exist; /hint/predict uses resolver/rules.",
        "fallback_used": True,
        "output": ["hint_type", "hint_level", "hint_text", "worked_example"],
        "db_tables_read": ["concept_resources"],
        "db_tables_written": [],
        "called_by": ["run_integrated_tutor_once", "/hint/predict"],
        "calls_which_modules": ["concept_content_resolver"],
        "api_route_connected": True,
        "frontend_visible": True,
        "affects_next_decision": True,
        "status": "BACKEND READY WITH FALLBACK",
        "missing_upgrade_needed": "Return learned_hint_output in /hint/predict when artifacts load safely.",
    },
    {
        "module_name": "Doubt Handling",
        "folder_file": "tutor/doubt/doubt_intent_classifier.py; tutor/api/doubt_routes.py",
        "purpose": "Classify learner doubts and return grounded support answer.",
        "inputs": ["learner_id", "doubt_text", "subject", "concept_id", "code_context"],
        "model_algorithm_formula": "TF-IDF/vectorizer classifier artifacts with rule fallback on low confidence/unavailable model.",
        "trained_artifact_used": "models/doubt/doubt_intent_classifier.pkl and vectorizer exist.",
        "fallback_used": True,
        "output": ["intent", "confidence", "answer", "recommended_route"],
        "db_tables_read": ["concept_resources"],
        "db_tables_written": ["learner_doubt_log"],
        "called_by": ["/doubt/ask", "/ask"],
        "calls_which_modules": ["concept_content_resolver"],
        "api_route_connected": True,
        "frontend_visible": True,
        "affects_next_decision": True,
        "status": "FULLY CONNECTED",
        "missing_upgrade_needed": "Surface doubt-derived weak concepts in adaptive path evidence.",
    },
    {
        "module_name": "RAG",
        "folder_file": "tutor/rag/*.py; models/rag/*; concept_resources",
        "purpose": "Retrieve concept-grounded chunks and check/support generation grounding.",
        "inputs": ["subject", "concept_id", "query", "task_type", "learner doubt"],
        "model_algorithm_formula": "Option C TF-IDF retriever, hybrid/reranker modules, embedding artifacts, and grounding/semantic support scoring.",
        "trained_artifact_used": "models/rag/rag_embeddings.npy and rag_reranker_model.pkl exist; API content routes primarily use concept_resources/resolver.",
        "fallback_used": True,
        "output": ["retrieved_context", "source_sections", "grounding_score", "unsupported_terms"],
        "db_tables_read": ["concept_resources", "rag_chunks"],
        "db_tables_written": [],
        "called_by": ["run_integrated_tutor_once", "lesson/doubt/flashcard/mindmap routes"],
        "calls_which_modules": ["rag_context_builder", "rag_grounding_checker", "rag_semantic_support_checker"],
        "api_route_connected": True,
        "frontend_visible": True,
        "affects_next_decision": False,
        "status": "BACKEND READY WITH FALLBACK",
        "missing_upgrade_needed": "Return exact chunk ids/source rows in every generation route.",
    },
    {
        "module_name": "CogniTutorLM Connector / Generation",
        "folder_file": "tutor/generation/cognitutor_lm_connector.py; tutor/generation/sanvia_finetuned_connector.py",
        "purpose": "Generate/select teaching artifacts and compare generation backends.",
        "inputs": ["learner_id", "concept_id", "concept_name", "domain", "task_type", "RAG context"],
        "model_algorithm_formula": "Local generation connector, generation policy classifier, template fallback; Sanvia route is comparison-only and not live.",
        "trained_artifact_used": "models/generation/generation_model.pkl exists; Sanvia base model unavailable by route report.",
        "fallback_used": True,
        "output": ["lesson/session artifacts", "model_generated", "fallback_used", "limitations"],
        "db_tables_read": ["concept_resources", "question_bank"],
        "db_tables_written": [],
        "called_by": ["/generation/cognitutor", "/generation/compare", "run_integrated_tutor_once"],
        "calls_which_modules": ["RAG", "adaptive_content_generator"],
        "api_route_connected": True,
        "frontend_visible": True,
        "affects_next_decision": False,
        "status": "BACKEND READY WITH FALLBACK",
        "missing_upgrade_needed": "Keep Sanvia comparison-only until local base/merged model is valid.",
    },
    {
        "module_name": "Policy / RL",
        "folder_file": "tutor/policy/*.py; tutor/RL/*.py; models/rl/*; models/policy/policy_model.joblib",
        "purpose": "Recommend adaptive action with safe action masking.",
        "inputs": ["mastery_score", "behaviour_risk", "difficulty", "score", "mistake_type", "retention_risk", "dependency_status"],
        "model_algorithm_formula": "Policy model/joblib, contextual bandit, DQN/DDQN/dueling DQN artifacts; safe policy bridge masks unsafe actions.",
        "trained_artifact_used": "models/policy and models/rl artifacts exist; /answer/submit uses safe bridge recommendation from rule path.",
        "fallback_used": True,
        "output": ["recommended_action", "safe_action_applied", "final_action", "reason"],
        "db_tables_read": ["knowledge_state", "behaviour_state", "decay_state", "concept_unlock_state"],
        "db_tables_written": ["rl_decision_log"],
        "called_by": ["run_integrated_tutor_once", "DecisionAgent", "/answer/submit evidence"],
        "calls_which_modules": ["rl_safe_action_mask", "AdaptivePathSelector"],
        "api_route_connected": True,
        "frontend_visible": True,
        "affects_next_decision": True,
        "status": "COMPARISON ONLY",
        "missing_upgrade_needed": "Policy/RL is safe decision support or shadow recommendation, not unrestricted final authority.",
    },
    {
        "module_name": "XAI / Why-this",
        "folder_file": "tutor/xai/*.py; tutor/api/xai_routes.py; /ai/evidence",
        "purpose": "Explain decisions to learner/reviewer using feature and module evidence.",
        "inputs": ["mastery_score", "behaviour_risk", "mistake_type", "teaching_strategy", "retention_need", "policy_action", "RAG grounding"],
        "model_algorithm_formula": "Feature contribution/rule explainer plus surrogate attribution artifacts for dashboard.",
        "trained_artifact_used": "models/xai/*.joblib exists for surrogate dashboard; answer-submit builds evidence packet.",
        "fallback_used": True,
        "output": ["learner_reason", "top_factors", "reviewer_evidence", "counterfactuals"],
        "db_tables_read": ["learner_session_state", "evaluation reports"],
        "db_tables_written": ["xai_log"],
        "called_by": ["/xai/{learner_id}", "/ai/evidence/{learner_id}", "run_integrated_tutor_once", "/answer/submit"],
        "calls_which_modules": ["feature_contribution_explainer", "xai_dashboard_builder"],
        "api_route_connected": True,
        "frontend_visible": True,
        "affects_next_decision": False,
        "status": "FULLY CONNECTED",
        "missing_upgrade_needed": "Persist answer-submit xai_packet to xai_log where table schema exists.",
    },
    {
        "module_name": "Notebook Memory / Long-term Personalization",
        "folder_file": "tutor/memory/*.py; tutor/long_term_personalization/*.py",
        "purpose": "Build returning learner context, notebook summaries, weak concepts and practice queues.",
        "inputs": ["mistakes", "doubts", "weak concepts", "mastery", "behaviour risk", "last_active_at"],
        "model_algorithm_formula": "SQLite memory aggregation, profile rules and optional semantic notebook search.",
        "trained_artifact_used": "No central trained model; notebook JSON files and semantic search fallback are available.",
        "fallback_used": True,
        "output": ["notebook_summary", "mistake_summary", "revision_plan", "comeback_summary", "next_practice_queue"],
        "db_tables_read": ["learner_session_log", "learner_mistake_log", "learner_doubt_log", "revision_schedule"],
        "db_tables_written": ["learner_session_state", "learner_session_log", "learner_mistake_log"],
        "called_by": ["run_integrated_tutor_once", "/notebook", "/learner/notebook/*", "/answer/submit"],
        "calls_which_modules": ["ProductionLearnerMemoryStore", "LearnerNotebookMemory"],
        "api_route_connected": True,
        "frontend_visible": True,
        "affects_next_decision": True,
        "status": "FULLY CONNECTED",
        "missing_upgrade_needed": "Use the same memory context in /answer/submit next-action selection.",
    },
    {
        "module_name": "Forgetting / Retention / Revision",
        "folder_file": "tutor/forgetting/*.py; tutor/api/revision_routes.py; /retention",
        "purpose": "Predict retention risk, due revision, priority and review interval.",
        "inputs": ["mastery", "last_active_at", "mistake history", "behaviour risk", "revision due date"],
        "model_algorithm_formula": "Supervised retention models when evidence/artifacts available; exponential decay and rule fallback otherwise.",
        "trained_artifact_used": "models/forgetting/*.joblib exists.",
        "fallback_used": True,
        "output": ["retention_risk", "revision_plan", "due revision activity", "review_interval"],
        "db_tables_read": ["knowledge_state", "quiz_results", "revision_schedule"],
        "db_tables_written": ["decay_state", "revision_schedule"],
        "called_by": ["run_integrated_tutor_once", "/revision", "/retention", "/answer/submit"],
        "calls_which_modules": ["retention_predictor", "revision_scheduler"],
        "api_route_connected": True,
        "frontend_visible": True,
        "affects_next_decision": True,
        "status": "BACKEND READY WITH FALLBACK",
        "missing_upgrade_needed": "Replace placeholder /retention probabilities with retention_predictor output.",
    },
    {
        "module_name": "Rewards / Gamification",
        "folder_file": "tutor/progression/*.py; tutor/reward/*.py; tutor/api/reward_routes.py",
        "purpose": "Award XP/streaks/badges and track concept unlock progression.",
        "inputs": ["answer result", "concept complete", "revision complete", "streak", "difficulty pass"],
        "model_algorithm_formula": "Progression/reward rules plus promotion confidence model comparison.",
        "trained_artifact_used": "models/promotion_confidence/*.joblib exists for promotion comparison.",
        "fallback_used": True,
        "output": ["XP", "streak", "badge", "reward_event", "unlock_progress"],
        "db_tables_read": ["learner_xp_state", "learner_streak_state", "learner_badges", "concept_unlock_state"],
        "db_tables_written": ["reward_event_log", "learner_xp_state", "learner_streak_state", "learner_badges", "concept_unlock_state"],
        "called_by": ["run_integrated_tutor_once", "/reward", "/answer/submit"],
        "calls_which_modules": ["progression_reward_engine", "reward_state_store"],
        "api_route_connected": True,
        "frontend_visible": True,
        "affects_next_decision": True,
        "status": "FULLY CONNECTED",
        "missing_upgrade_needed": "Ensure every reward is tied to assessed mastery/progression evidence, not page clicks.",
    },
    {
        "module_name": "Agentic Orchestration Trace",
        "folder_file": "tutor/agents/orchestration_trace.py; tutor/api/integration_routes.py",
        "purpose": "Expose ordered tutor-module trace for reviewer analytics.",
        "inputs": ["integrated tutor output", "learner_id", "module outputs"],
        "model_algorithm_formula": "Trace builder over module sequence; not a fully autonomous multi-agent system.",
        "trained_artifact_used": "No trained artifact.",
        "fallback_used": True,
        "output": ["agentic_trace", "stages", "module statuses"],
        "db_tables_read": ["learner_session_log"],
        "db_tables_written": ["learner_session_log"],
        "called_by": ["/agentic/trace/{learner_id}", "run_integrated_tutor_once", "/answer/submit"],
        "calls_which_modules": ["TutorAgent", "EvaluatorAgent", "DecisionAgent", "ExplainerAgent"],
        "api_route_connected": True,
        "frontend_visible": True,
        "affects_next_decision": False,
        "status": "BACKEND READY WITH FALLBACK",
        "missing_upgrade_needed": "Persist latest integrated trace and return it instead of static fallback when available.",
    },
    {
        "module_name": "Frontend Response Builder",
        "folder_file": "tutor/system/frontend_response_builder.py",
        "purpose": "Compact integrated backend output into frontend contract.",
        "inputs": ["full integrated tutor output"],
        "model_algorithm_formula": "Deterministic response mapping.",
        "trained_artifact_used": "No trained artifact.",
        "fallback_used": True,
        "output": ["frontend_response", "teaching", "assessment", "decision", "xai", "reward", "revision"],
        "db_tables_read": ["production memory tables"],
        "db_tables_written": [],
        "called_by": ["/tutor/adaptive-session/{learner_id}"],
        "calls_which_modules": ["ProductionLearnerMemoryStore"],
        "api_route_connected": True,
        "frontend_visible": True,
        "affects_next_decision": False,
        "status": "FULLY CONNECTED",
        "missing_upgrade_needed": "Add compact kt_update/behaviour_update/path_update aliases for integrated sessions.",
    },
    {
        "module_name": "API Routes",
        "folder_file": "tutor/api/*.py",
        "purpose": "Expose tutor services to frontend and tests.",
        "inputs": ["HTTP path/query/body payloads"],
        "model_algorithm_formula": "FastAPI route wrappers with warning fallback responses.",
        "trained_artifact_used": "Route dependent.",
        "fallback_used": True,
        "output": ["JSON API responses"],
        "db_tables_read": ["multiple"],
        "db_tables_written": ["multiple"],
        "called_by": ["frontend KP-UI", "scripts tests"],
        "calls_which_modules": ["evaluation", "integration", "xai", "revision", "reward", "path", "doubt"],
        "api_route_connected": True,
        "frontend_visible": True,
        "affects_next_decision": True,
        "status": "FULLY CONNECTED",
        "missing_upgrade_needed": "Replace placeholder evidence in /ai/evidence with latest persisted module evidence where possible.",
    },
    {
        "module_name": "Main Integrated Tutor Runner",
        "folder_file": "tutor/system/run_integrated_tutor_once.py",
        "purpose": "Run full backend pipeline across KT, behaviour, dependency, policy, teaching, assessment, evaluation, memory, reward and XAI.",
        "inputs": ["learner_id", "learner_profile", "db_path", "reward_dry_run"],
        "model_algorithm_formula": "Sequential orchestration of model, scoring, retrieval, rule and comparison modules.",
        "trained_artifact_used": "Uses available artifacts opportunistically through child modules.",
        "fallback_used": True,
        "output": ["integrated tutor packet", "demo_summary", "module outputs"],
        "db_tables_read": ["quiz_results", "knowledge_state", "behaviour_state", "concept_resources", "reward tables"],
        "db_tables_written": ["knowledge_state", "behaviour_state", "teaching_strategy_log", "reward tables", "learner logs"],
        "called_by": ["/tutor/adaptive-session/{learner_id}", "/xai/{learner_id}", "tests"],
        "calls_which_modules": ["KT", "Behaviour", "Forgetting", "Policy", "RAG", "Assessment", "Evaluation", "XAI", "Reward"],
        "api_route_connected": True,
        "frontend_visible": True,
        "affects_next_decision": True,
        "status": "FULLY CONNECTED",
        "missing_upgrade_needed": "Reduce divergence between integrated runner and lightweight /answer/submit route.",
    },
]


def summary() -> dict[str, Any]:
    counts = Counter(item["status"] for item in MODULES)
    return {
        "total_modules_found": len(MODULES),
        "fully_connected": counts["FULLY CONNECTED"],
        "backend_ready_with_fallback": counts["BACKEND READY WITH FALLBACK"],
        "comparison_only": counts["COMPARISON ONLY"],
        "partial": counts["PARTIAL"],
        "missing_broken": counts["MISSING"] + counts["BROKEN"],
        "modules_connected_to_frontend": sum(1 for item in MODULES if item["frontend_visible"]),
        "modules_not_visible_in_frontend": sum(1 for item in MODULES if not item["frontend_visible"]),
        "trained_artifacts_missing": [
            "Sanvia local base/merged model for live generation",
            "Live trained mistake-analysis classifier artifact",
            "Live trained assessment-generation model artifact",
        ],
        "warnings": [
            "Agentic AI is represented as an orchestration trace, not a fully autonomous agent.",
            "Policy/RL remains safe decision support/comparison unless explicitly promoted after validation.",
            "Sanvia is comparison-only and is not connected live.",
            "The answer-submit route uses fallback/scoring evidence for KT and behaviour, while the integrated runner can use trained artifacts.",
        ],
    }


def connection_matrix() -> list[dict[str, Any]]:
    return [
        {
            "module_name": item["module_name"],
            "folder_file": item["folder_file"],
            "runtime_status": item["status"],
            "api_route_connected": item["api_route_connected"],
            "frontend_visible": item["frontend_visible"],
            "db_tables_read": item["db_tables_read"],
            "db_tables_written": item["db_tables_written"],
            "called_by": item["called_by"],
            "calls_which_modules": item["calls_which_modules"],
            "affects_next_decision": item["affects_next_decision"],
        }
        for item in MODULES
    ]


def upgrade_plan() -> list[dict[str, Any]]:
    return [
        {
            "module_name": item["module_name"],
            "status": item["status"],
            "missing_issues": item["missing_upgrade_needed"],
            "safe_fix_applied_or_plan": _fix_applied(item),
        }
        for item in MODULES
    ]


def _fix_applied(item: dict[str, Any]) -> str:
    if item["module_name"] in {"Knowledge Tracing", "Behaviour Modelling", "Adaptive Path", "Policy / RL", "RAG", "XAI / Why-this", "Rewards / Gamification", "Notebook Memory / Long-term Personalization", "Agentic Orchestration Trace", "Teaching Strategy"}:
        return "Safe response evidence fields added or verified in /answer/submit without forcing unavailable/unsafe live model usage."
    if item["module_name"] in {"API Routes", "Main Integrated Tutor Runner"}:
        return "Audit tests and reports added; existing routes verified by smoke tests."
    return "Documented in inventory; no runtime change required for this task."


def write_reports() -> dict[str, Any]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_DIR.mkdir(parents=True, exist_ok=True)

    audit = {"summary": summary(), "modules": MODULES}
    matrix = {"summary": summary(), "connection_matrix": connection_matrix()}
    inventory = {"summary": summary(), "model_input_output_inventory": MODULES}
    plan = {"summary": summary(), "upgrade_plan": upgrade_plan()}

    _write_json("backend_module_intelligence_audit_report.json", audit)
    _write_json("backend_module_connection_matrix.json", matrix)
    _write_json("backend_model_input_output_inventory.json", inventory)
    _write_json("backend_missing_module_upgrade_plan.json", plan)

    _write_md("backend_module_intelligence_audit_report.md", "Backend Module Intelligence Audit Report", audit["modules"], include_summary=True)
    _write_md("backend_module_connection_matrix.md", "Backend Module Connection Matrix", matrix["connection_matrix"], include_summary=True)
    _write_md("backend_model_input_output_inventory.md", "Backend Model Input Output Inventory", inventory["model_input_output_inventory"], include_summary=True)
    _write_upgrade_md(plan)

    return {
        "status": "success",
        "summary": summary(),
        "reports": [
            str(REPORT_DIR / "backend_module_intelligence_audit_report.md"),
            str(JSON_DIR / "backend_module_intelligence_audit_report.json"),
            str(REPORT_DIR / "backend_module_connection_matrix.md"),
            str(JSON_DIR / "backend_module_connection_matrix.json"),
            str(REPORT_DIR / "backend_model_input_output_inventory.md"),
            str(JSON_DIR / "backend_model_input_output_inventory.json"),
            str(REPORT_DIR / "backend_missing_module_upgrade_plan.md"),
            str(JSON_DIR / "backend_missing_module_upgrade_plan.json"),
        ],
    }


def _write_json(filename: str, payload: dict[str, Any]) -> None:
    (JSON_DIR / filename).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_md(filename: str, title: str, rows: list[dict[str, Any]], include_summary: bool = False) -> None:
    lines = [f"# {title}", ""]
    if include_summary:
        lines.extend(_summary_lines())
    headers = [
        "Module Name",
        "Folder/File",
        "Purpose",
        "Inputs",
        "Model/Algorithm Used",
        "Trained Artifact Used?",
        "Fallback Used?",
        "Output",
        "DB Tables Read",
        "DB Tables Written",
        "Called By",
        "Calls Which Modules",
        "API Route Connected?",
        "Frontend Visible?",
        "Affects Next Decision?",
        "Status",
        "Missing/Upgrade Needed",
    ]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for item in rows:
        values = [
            item.get("module_name"),
            item.get("folder_file"),
            item.get("purpose"),
            item.get("inputs"),
            item.get("model_algorithm_formula"),
            item.get("trained_artifact_used"),
            item.get("fallback_used"),
            item.get("output"),
            item.get("db_tables_read"),
            item.get("db_tables_written"),
            item.get("called_by"),
            item.get("calls_which_modules"),
            item.get("api_route_connected"),
            item.get("frontend_visible"),
            item.get("affects_next_decision"),
            item.get("status"),
            item.get("missing_upgrade_needed"),
        ]
        lines.append("| " + " | ".join(_cell(value) for value in values) + " |")
    (REPORT_DIR / filename).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_upgrade_md(plan: dict[str, Any]) -> None:
    lines = ["# Backend Missing Module Upgrade Plan", ""]
    lines.extend(_summary_lines())
    lines.append("| Module Name | Status | Missing Issues | Fix Applied or Upgrade Plan |")
    lines.append("| --- | --- | --- | --- |")
    for item in plan["upgrade_plan"]:
        lines.append(
            "| "
            + " | ".join(
                _cell(item[key])
                for key in ["module_name", "status", "missing_issues", "safe_fix_applied_or_plan"]
            )
            + " |"
        )
    (REPORT_DIR / "backend_missing_module_upgrade_plan.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _summary_lines() -> list[str]:
    data = summary()
    return [
        "## Summary",
        "",
        f"- Total modules found: {data['total_modules_found']}",
        f"- Fully connected: {data['fully_connected']}",
        f"- Backend-ready with fallback: {data['backend_ready_with_fallback']}",
        f"- Comparison-only: {data['comparison_only']}",
        f"- Partial: {data['partial']}",
        f"- Missing/broken: {data['missing_broken']}",
        f"- Modules connected to frontend: {data['modules_connected_to_frontend']}",
        f"- Modules not visible in frontend: {data['modules_not_visible_in_frontend']}",
        "",
    ]


def _cell(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        text = ", ".join(str(item) for item in value)
    elif isinstance(value, dict):
        text = json.dumps(value, sort_keys=True)
    else:
        text = str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def validate_inventory() -> None:
    assert MODULES, "No modules inventoried."
    for item in MODULES:
        assert item["status"] in STATUSES, f"Invalid status for {item['module_name']}: {item['status']}"
        required = [
            "module_name",
            "folder_file",
            "purpose",
            "inputs",
            "model_algorithm_formula",
            "output",
            "db_tables_read",
            "db_tables_written",
            "called_by",
            "api_route_connected",
            "frontend_visible",
            "affects_next_decision",
            "missing_upgrade_needed",
        ]
        missing = [key for key in required if key not in item]
        assert not missing, f"{item['module_name']} missing keys {missing}"


if __name__ == "__main__":
    validate_inventory()
    result = write_reports()
    print("BACKEND INTELLIGENCE AUDIT SUMMARY")
    for key, value in result["summary"].items():
        print(f"- {key}: {value}")
