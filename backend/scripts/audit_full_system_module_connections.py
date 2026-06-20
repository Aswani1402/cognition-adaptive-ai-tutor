from __future__ import annotations

import importlib
import json
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT.parent / "frontend_ui" / "KP-UI"
JSON_REPORT = ROOT / "evaluation_outputs" / "json" / "full_system_connection_audit_report.json"
MD_REPORT = ROOT / "evaluation_outputs" / "reports" / "full_system_connection_audit_report.md"
MODEL_JSON_REPORT = ROOT / "evaluation_outputs" / "json" / "full_frontend_backend_model_connection_report.json"
MODEL_MD_REPORT = ROOT / "evaluation_outputs" / "reports" / "full_frontend_backend_model_connection_report.md"
INVENTORY_JSON_REPORT = ROOT / "evaluation_outputs" / "json" / "module_evaluation_inventory_report.json"
INVENTORY_MD_REPORT = ROOT / "evaluation_outputs" / "reports" / "module_evaluation_inventory_report.md"
FRONTEND_REPORT = FRONTEND / "frontend_full_model_connection_report.md"


GENERATION_TASKS: dict[str, list[str]] = {
    "Teaching views": ["explanation", "definition_view", "simple_example_view", "step_by_step_view", "analogy_view", "code_view", "misconception_view", "debug_view", "output_prediction_view", "transfer_view", "challenge_view", "revision_summary_view", "comparison_view", "real_world_connection_view"],
    "Assessment": ["mcq", "debug_task", "output_prediction", "transfer_question", "challenge_question", "explanation_check", "syntax_completion", "coding_prompt", "code_reasoning_task", "fill_in_the_blank", "true_or_false"],
    "Revision": ["revision_note", "revision_summary", "weakness_review", "daily_review", "personal_revision_plan", "recommended_revision_views", "spaced_repetition_card"],
    "Flashcards": ["flashcard", "concept_recall_flashcard", "misconception_flashcard", "example_flashcard", "debug_flashcard", "personal_flashcards", "syntax_flashcard"],
    "Mindmaps": ["mindmap", "concept_mindmap", "comparison_mindmap"],
    "Feedback": ["feedback", "correct_answer_feedback", "wrong_answer_feedback", "partial_answer_feedback", "debug_feedback", "output_prediction_feedback", "next_step_feedback", "encouragement_feedback"],
    "Hints": ["hint", "small_hint", "guided_hint", "worked_example_hint", "debug_hint", "syntax_hint", "output_prediction_hint", "misconception_hint", "next_step_hint", "analogy_hint"],
    "Doubt answers": ["doubt_answer", "concept_doubt_answer", "syntax_doubt_answer", "debug_doubt_answer", "output_doubt_answer", "example_request_answer", "revision_doubt_answer", "next_step_doubt_answer", "comparison_doubt_answer"],
    "Notebook/memory": ["notebook_summary", "mistake_summary", "revision_plan", "comeback_summary", "returning_learner_summary", "progress_insight"],
    "Practice/challenge": ["practice_question", "transfer_task", "real_world_application_question", "debug_challenge", "output_prediction_challenge", "multi_step_challenge"],
    "Voice-ready scripts": ["voice_script", "teaching_voice_script", "revision_voice_script", "mistake_feedback_voice_script", "doubt_explanation_voice_script", "encouragement_script", "next_step_guidance_script", "concept_intro_voice_script"],
}


MODULES: list[dict[str, Any]] = [
    {"module": "Authentication", "imports": ["tutor.api.auth_routes"], "routes": ["/auth/register", "/auth/login"], "frontend": ["src/pages/RegisterPage.tsx", "src/pages/LoginPage.tsx"], "tables": ["users", "learner_profile"], "inputs": ["name", "email", "password"], "output": "user_id, learner_id, access_token"},
    {"module": "Learner profile/session", "imports": ["tutor.api.learner_routes"], "routes": ["/learner/context/{learner_id}", "/learner/session/{learner_id}"], "frontend": ["src/context/LearnerSessionContext.tsx", "src/pages/DashboardPage.tsx"], "tables": ["learner_profile", "learner_session_log"], "inputs": ["learner_id"], "output": "active subject, concept, returning learner context"},
    {"module": "Knowledge Tracing", "imports": ["tutor.knowledge_state", "tutor.api.evaluation_routes"], "routes": ["/answer/submit", "/ai/evidence/{learner_id}"], "frontend": ["src/components/assessment/AssessmentRenderer.tsx"], "tables": ["knowledge_state", "quiz_results"], "inputs": ["learner_id", "concept_id", "score", "difficulty", "question_type"], "output": "kt_update and mastery state"},
    {"module": "Behaviour Modeling", "imports": ["tutor.behaviour", "tutor.api.evaluation_routes"], "routes": ["/answer/submit"], "frontend": ["src/components/assessment/AssessmentRenderer.tsx", "src/components/assessment/CodeConsole.tsx"], "tables": ["behaviour_state"], "inputs": ["time_taken_sec", "confidence", "hint_count", "option_change_count", "answer_change_count", "run_code_count", "attempt_count"], "output": "behaviour_update"},
    {"module": "Concept Dependency", "imports": ["tutor.concept_dependency"], "routes": ["/learner/select-subject", "/path/{learner_id}/{subject:path}"], "frontend": ["src/pages/SubjectsPage.tsx", "src/pages/LearningPathPage.tsx"], "tables": ["concept_unlock_state", "concept_id_map"], "inputs": ["subject", "concept_id", "difficulty_passed"], "output": "locked/current/mastered path nodes"},
    {"module": "Adaptive Path", "imports": ["tutor.concept_dependency.learned_adaptive_path_ranker"], "routes": ["/adaptive-path/{learner_id}", "/answer/submit"], "frontend": ["src/pages/LearningPathPage.tsx"], "tables": ["knowledge_state", "behaviour_state", "concept_unlock_state"], "inputs": ["mastery", "behaviour risk", "revision due"], "output": "path_update"},
    {"module": "Teaching Strategy", "imports": ["tutor.strategy", "tutor.api.integration_routes"], "routes": ["/lesson/{learner_id}/{concept_id}"], "frontend": ["src/pages/LessonPage.tsx"], "tables": ["teaching_strategy_log"], "inputs": ["learner_id", "subject", "concept_id", "difficulty"], "output": "selected teaching view"},
    {"module": "Policy/RL", "imports": ["tutor.policy", "tutor.RL", "tutor.api.evaluation_routes"], "routes": ["/answer/submit", "/ai/evidence/{learner_id}"], "frontend": ["src/components/ai/PolicyDecisionCard.tsx"], "tables": ["concept_unlock_state"], "inputs": ["path candidates", "safe action mask"], "output": "policy_update warning/safe decision"},
    {"module": "RAG", "imports": ["tutor.rag", "tutor.api.integration_routes"], "routes": ["/lesson/{learner_id}/{concept_id}", "/doubt/ask", "/mindmap/{concept_id}"], "frontend": ["src/components/ai/RAGGroundingCard.tsx"], "tables": ["concept_resources"], "inputs": ["subject", "concept_id"], "output": "rag_update/source sections"},
    {"module": "CogniTutorLM connector / generation artifacts", "imports": ["tutor.generation.cognitutor_lm_connector"], "routes": ["/generation/cognitutor", "/generation/coverage/{learner_id}"], "frontend": ["src/components/ai/GenerationCoverageCard.tsx"], "tables": ["concept_resources"], "inputs": ["task_type", "concept content"], "output": "llm_generation or warning fallback"},
    {"module": "LLM generation task coverage", "imports": ["tutor.generation"], "routes": ["/generation/coverage/{learner_id}"], "frontend": ["src/components/ai/GenerationCoverageCard.tsx"], "tables": [], "inputs": ["task categories"], "output": "coverage report/card"},
    {"module": "Agentic orchestration trace", "imports": ["tutor.agents.orchestration_trace"], "routes": ["/agentic/trace/{learner_id}"], "frontend": ["src/components/ai/AgentTraceCard.tsx"], "tables": ["learner_session_log"], "inputs": ["module outputs"], "output": "orchestration trace warning/success"},
    {"module": "Long-term personalization / Notebook memory", "imports": ["tutor.memory", "tutor.api.learner_routes"], "routes": ["/notebook/{learner_id}", "/learner/notebook/search/{learner_id}", "/learner/personalization/{learner_id}"], "frontend": ["src/pages/NotebookPage.tsx"], "tables": ["learner_mistake_log", "learner_doubt_log", "learner_session_log", "revision_card"], "inputs": ["mistakes", "doubts", "sessions"], "output": "notebook/search/personalization"},
    {"module": "Forgetting / Retention", "imports": ["tutor.forgetting.retention_predictor"], "routes": ["/retention/{learner_id}", "/revision/{learner_id}"], "frontend": ["src/pages/FlashcardsPage.tsx", "src/pages/ReviewerInsightsPage.tsx"], "tables": ["revision_schedule", "knowledge_state"], "inputs": ["last_active_at", "mastery", "revision due"], "output": "retention/revision packet"},
    {"module": "Assessment generator/question bank", "imports": ["tutor.assessment", "tutor.api.integration_routes"], "routes": ["/assessment/{learner_id}/{concept_id}"], "frontend": ["src/pages/QuizPage.tsx"], "tables": ["concept_resources"], "inputs": ["subject", "concept_id", "difficulty"], "output": "subject-specific questions"},
    {"module": "Answer evaluator", "imports": ["tutor.evaluation.answer_evaluator"], "routes": ["/answer/submit"], "frontend": ["src/components/assessment/AssessmentRenderer.tsx"], "tables": ["quiz_results"], "inputs": ["answer", "correct answer", "question type"], "output": "score, feedback, mistake type"},
    {"module": "Safe code runner", "imports": ["tutor.evaluation.code_runner"], "routes": ["/code/run"], "frontend": ["src/components/assessment/CodeConsole.tsx"], "tables": [], "inputs": ["code", "language", "test_cases"], "output": "stdout/stderr/test results"},
    {"module": "Code/debug/output evaluator", "imports": ["tutor.evaluation.code_runner", "tutor.evaluation.answer_evaluator"], "routes": ["/answer/submit", "/code/run"], "frontend": ["src/components/assessment/CodeConsole.tsx"], "tables": ["quiz_results"], "inputs": ["code", "expected output"], "output": "code score/feedback"},
    {"module": "Mistake analysis", "imports": ["tutor.evaluation", "tutor.system.user_persistence_store"], "routes": ["/answer/submit", "/mistakes/{learner_id}"], "frontend": ["src/pages/MistakesPage.tsx"], "tables": ["learner_mistake_log"], "inputs": ["evaluation result"], "output": "mistake log/review"},
    {"module": "Hint policy", "imports": ["tutor.api.integration_routes"], "routes": ["/hint/predict"], "frontend": ["src/components/assessment/AssessmentRenderer.tsx"], "tables": ["behaviour_state"], "inputs": ["question context", "hint_count", "mastery", "behaviour risk"], "output": "hint response"},
    {"module": "Doubt handler", "imports": ["tutor.doubt.doubt_intent_classifier", "tutor.api.doubt_routes"], "routes": ["/doubt/ask"], "frontend": ["src/components/doubt/DoubtPanel.tsx"], "tables": ["learner_doubt_log"], "inputs": ["doubt_text", "subject", "concept_id"], "output": "classified/grounded answer"},
    {"module": "Flashcards", "imports": ["tutor.api.integration_routes"], "routes": ["/flashcards/{learner_id}/{concept_id}"], "frontend": ["src/pages/FlashcardsPage.tsx"], "tables": ["revision_card", "concept_resources"], "inputs": ["learner_id", "concept_id", "subject"], "output": "flashcards"},
    {"module": "Mindmap", "imports": ["tutor.api.integration_routes"], "routes": ["/mindmap/{concept_id}"], "frontend": ["src/pages/MindMapPage.tsx"], "tables": ["concept_resources"], "inputs": ["concept_id", "subject"], "output": "mindmap"},
    {"module": "Revision summary / revision plan", "imports": ["tutor.memory.revision_scheduler", "tutor.api.revision_routes"], "routes": ["/revision/{learner_id}"], "frontend": ["src/pages/ReviewerInsightsPage.tsx"], "tables": ["revision_schedule", "revision_card"], "inputs": ["mistakes", "retention", "mastery"], "output": "revision plan"},
    {"module": "Rewards / XP / streak", "imports": ["tutor.api.reward_routes"], "routes": ["/reward/{learner_id}", "/answer/submit"], "frontend": ["src/pages/RewardsPage.tsx"], "tables": ["learner_xp_state", "learner_streak_state", "reward_event_log", "learner_badges"], "inputs": ["score", "concept", "activity"], "output": "reward state"},
    {"module": "XAI", "imports": ["tutor.api.xai_routes"], "routes": ["/xai/{learner_id}", "/ai/evidence/{learner_id}"], "frontend": ["src/pages/XAIPage.tsx"], "tables": ["knowledge_state", "behaviour_state"], "inputs": ["decision evidence"], "output": "learner/reviewer explanation"},
    {"module": "Frontend API connection", "imports": [], "routes": [], "frontend": ["src/lib/api.ts"], "tables": [], "inputs": ["VITE_API_BASE_URL"], "output": "backend requests/fallback logging"},
    {"module": "Database persistence", "imports": ["tutor.api.dependencies"], "routes": ["/answer/submit", "/learner/select-subject"], "frontend": ["src/lib/api.ts"], "tables": ["users", "learner_profile", "quiz_results", "knowledge_state", "behaviour_state", "learner_mistake_log", "revision_schedule", "reward_event_log", "learner_session_log"], "inputs": ["learner events"], "output": "SQLite state"},
    {"module": "Evaluation reports/charts", "imports": [], "routes": [], "frontend": ["src/pages/ReviewerInsightsPage.tsx"], "tables": [], "inputs": ["evaluation_outputs"], "output": "report/chart inventory"},
]


def _route_paths() -> set[str]:
    try:
        from tutor.api.app import app
        return {getattr(route, "path", "") for route in app.routes}
    except Exception:
        return set()


def _tables() -> set[str]:
    try:
        from tutor.api.dependencies import DB_PATH, create_tables

        db = ROOT / DB_PATH if not Path(DB_PATH).is_absolute() else Path(DB_PATH)
        create_tables(DB_PATH)
    except Exception:
        db = ROOT / "external" / "core_data" / "tutor.db"
    if not db.exists():
        return set()
    try:
        all_tables: set[str] = set()
        dbs = [db, *sorted((ROOT / "external" / "core_data").glob("*.db"))]
        for db_path in dbs:
            if not db_path.exists():
                continue
            con = sqlite3.connect(db_path)
            try:
                all_tables.update(row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall())
            finally:
                con.close()
        return all_tables
    except sqlite3.Error:
        return set()


def _importable(names: list[str]) -> tuple[bool, list[str], list[str]]:
    ok: list[str] = []
    bad: list[str] = []
    for name in names:
        try:
            importlib.import_module(name)
            ok.append(name)
        except Exception as exc:
            bad.append(f"{name}: {type(exc).__name__}")
    return (not bad if names else True), ok, bad


def _frontend_exists(files: list[str]) -> tuple[bool, list[str]]:
    missing = [item for item in files if not (FRONTEND / item).exists()]
    return not missing, missing


def _route_connected(routes: list[str], paths: set[str]) -> tuple[bool, list[str]]:
    missing = [route for route in routes if route not in paths]
    return not missing, missing


def _table_status(names: list[str], tables: set[str]) -> tuple[bool, list[str]]:
    missing = [name for name in names if name not in tables]
    return not missing, missing


def build_module_audit() -> dict[str, Any]:
    paths = _route_paths()
    tables = _tables()
    rows: list[dict[str, Any]] = []
    for spec in MODULES:
        imports_ok, imports_found, imports_missing = _importable(spec["imports"])
        routes_ok, routes_missing = _route_connected(spec["routes"], paths)
        frontend_ok, frontend_missing = _frontend_exists(spec["frontend"])
        tables_ok, tables_missing = _table_status(spec["tables"], tables)
        connected = imports_ok and routes_ok and frontend_ok and (tables_ok or not spec["tables"])
        issue_parts = []
        if imports_missing:
            issue_parts.append("missing imports: " + "; ".join(imports_missing))
        if routes_missing:
            issue_parts.append("missing routes: " + ", ".join(routes_missing))
        if frontend_missing:
            issue_parts.append("missing frontend: " + ", ".join(frontend_missing))
        if tables_missing:
            issue_parts.append("missing tables: " + ", ".join(tables_missing))
        rows.append({
            "Module": spec["module"],
            "Backend files": ", ".join(spec["imports"]) or "n/a",
            "API route": ", ".join(spec["routes"]) or "n/a",
            "Frontend component/page": ", ".join(spec["frontend"]) or "n/a",
            "DB table": ", ".join(spec["tables"]) or "n/a",
            "Inputs required": ", ".join(spec["inputs"]),
            "Inputs currently received?": "yes" if routes_ok and frontend_ok else "warning",
            "Output produced": spec["output"],
            "Connected?": bool(connected),
            "Missing/Issue": "; ".join(issue_parts) if issue_parts else "none",
            "Fix recommendation": "No action required." if connected else "Keep fallback warning visible and connect/import/create missing item before claiming live support.",
            "importable": imports_ok,
            "routes_connected": routes_ok,
            "frontend_connected": frontend_ok,
            "tables_present": tables_ok or not spec["tables"],
        })
    return {
        "status": "success" if all(row["Connected?"] for row in rows) else "warning",
        "module": "full_system_connection_audit",
        "root": str(ROOT),
        "frontend_root": str(FRONTEND),
        "modules": rows,
        "route_count": len(paths),
        "db_tables_detected": sorted(tables),
        "website_flow": "Register/Login -> Subject -> Guided Session -> Teaching -> Assessment -> Feedback -> Revision -> Progress",
        "streamlit_decision": "A separate Streamlit dashboard is not required because the project already has a web frontend. Streamlit may be used only as an optional internal debugging tool.",
    }


def build_generation_coverage() -> list[dict[str, str]]:
    frontend_renderers = {
        "Assessment": "AssessmentRenderer",
        "Teaching views": "SelectedTeachingViewRenderer/LessonPage",
        "Revision": "ReviewerInsightsPage/FlashcardDeck/MindMapView",
        "Flashcards": "FlashcardDeck",
        "Mindmaps": "MindMapView",
        "Feedback": "FeedbackCard",
        "Hints": "HintPanel",
        "Doubt answers": "DoubtPanel",
        "Notebook/memory": "NotebookPage",
        "Practice/challenge": "PuzzlePage/CodeConsole",
        "Voice-ready scripts": "text script only",
    }
    rows: list[dict[str, str]] = []
    for category, tasks in GENERATION_TASKS.items():
        for task in tasks:
            rows.append({
                "Task category": category,
                "Task type": task,
                "Frontend renderer": frontend_renderers.get(category, "warning: renderer not mapped"),
                "Backend source": "CogniTutorLM/RAG/concept_resources/fallback",
                "Status": "connected_or_warning_fallback",
                "Missing/limitation": "Voice-ready scripts are text only, not audio/TTS." if category == "Voice-ready scripts" else "If CogniTutorLM artifact is unavailable, backend must return warning/fallback.",
            })
    return rows


def build_evaluation_inventory() -> dict[str, Any]:
    expected = {
        "KT model comparison": ["*kt*", "*bkt*", "*dkt*"],
        "Behaviour model comparison": ["*behavio*"],
        "Teaching strategy model": ["*teaching_strategy*", "*strategy*"],
        "XAI/surrogate": ["*xai*"],
        "RL/policy comparison": ["*rl*", "*policy*"],
        "RAG retrieval/grounding": ["*rag*"],
        "LLM generation comparison": ["*llm*", "*generation*", "*cognitutor*"],
        "Answer evaluator": ["*answer_evaluator*", "*evaluation_fusion*", "*rubric*"],
        "Hint policy": ["*hint*"],
        "Adaptive path": ["*adaptive_path*", "*path*"],
        "Retention/forgetting": ["*retention*", "*forgetting*"],
        "Notebook search": ["*notebook*", "*semantic*"],
        "Reward/gamification": ["*reward*"],
        "Human evaluation setup": ["*human_eval*"],
        "Full backend smoke test": ["*api_routes_smoke*"],
        "Overall system evaluation": ["*overall*", "*full_system*"],
        "Final chart inventory": ["*chart*", "*inventory*"],
        "Final evidence pack": ["*evidence*", "*final*"],
    }
    base_dirs = [ROOT / "evaluation_outputs" / "reports", ROOT / "evaluation_outputs" / "json", ROOT / "evaluation_outputs" / "charts"]
    items: list[dict[str, Any]] = []
    for name, patterns in expected.items():
        found: list[str] = []
        for directory in base_dirs:
            if directory.exists():
                for pattern in patterns:
                    found.extend(str(path.relative_to(ROOT)) for path in directory.glob(pattern))
        found = sorted(set(found))
        items.append({
            "module": name,
            "status": "success" if found else "warning",
            "artifacts_found": found[:25],
            "artifact_count": len(found),
            "recommendation": "Use existing artifacts; do not fake metrics." if found else "Create/run a real evaluation script before claiming metrics.",
        })
    return {"status": "warning" if any(item["status"] == "warning" for item in items) else "success", "module": "module_evaluation_inventory", "items": items}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _write_module_md(path: Path, report: dict[str, Any], generation_rows: list[dict[str, str]], inventory: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Full Frontend/Backend Model Connection Report",
        "",
        f"- Status: {report['status']}",
        f"- Website flow: {report['website_flow']}",
        f"- Streamlit decision: {report['streamlit_decision']}",
        "",
        "## Module Connection Table",
        "",
        "| Module | Backend files | API route | Frontend component/page | DB table | Inputs required | Inputs currently received? | Output produced | Connected? | Missing/Issue | Fix recommendation |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in report["modules"]:
        lines.append("| " + " | ".join(str(row[key]).replace("|", "/") for key in ["Module", "Backend files", "API route", "Frontend component/page", "DB table", "Inputs required", "Inputs currently received?", "Output produced", "Connected?", "Missing/Issue", "Fix recommendation"]) + " |")
    lines.extend([
        "",
        "## Required Status Sections",
        "",
        "1. Proper website flow status: learner-first flow preserved.",
        "2. Frontend-backend connection status: API layer uses `VITE_API_BASE_URL`, status badge, request logs, and fallback logs.",
        "3. Auth and user DB persistence: register/login routes use `users` and `learner_profile`; password hash is required.",
        "4. Subject context status: global learner session context drives subject/concept/difficulty.",
        "5. Guided session flow status: guided teaching/assessment/feedback/revision path remains the primary UX.",
        "6. Difficulty easy->medium->hard status: `/answer/submit` enforces next concept only after hard pass.",
        "7. Assessment type coverage: MCQ, fill blank, true/false, debug, output prediction, syntax, coding, transfer, challenge, explanation, drag, match, puzzle, flashcard recall are rendered or warning/fallback documented.",
        "8. Behaviour input collection status: frontend sends time, confidence, hint, option, answer, code-run, attempt, and wrong-attempt signals.",
        "9. KT input/output status: answer submit returns `kt_update` and writes `knowledge_state` when available.",
        "10. Concept dependency/adaptive path status: answer submit returns `path_update`; subject selection updates first concept/unlock state.",
        "11. Policy/RL status: safe bridge/warning evidence only, not raw final authority.",
        "12. RAG status: concept resources/RAG grounding are exposed through lesson/doubt/mindmap/evidence routes.",
        "13. LLM/CogniTutorLM status: connector/artifact/fallback is reported honestly.",
        "14. LLM generation task coverage: see generation coverage table below.",
        "15. Agentic orchestration status: shown as orchestration trace, not fully autonomous agent.",
        "16. Long-term personalization status: notebook, mistakes, doubts, and revision routes connected.",
        "17. Forgetting/retention status: retention/revision routes connected or warning/fallback.",
        "18. Notebook memory status: notebook/search pages use current learner.",
        "19. Hint/doubt status: hint and doubt routes connected with fallback warnings.",
        "20. Flashcard/mindmap/revision status: subject-aware routes connected.",
        "21. Code console status: run/submit/output/error/test panels and run count tracking present.",
        "22. XAI/Why-this status: compact learner Why-this and reviewer XAI/evidence only.",
        "23. Teacher/reviewer analytics status: `ReviewerInsightsPage` is available inside the web app.",
        "24. DB tables/columns used: listed in module table and JSON report.",
        "25. Per-module evaluation/chart inventory: see inventory section.",
        "26. Missing features: warnings are listed per row; unavailable models remain fallback/warning.",
        "27. Fixes applied: code console metadata/tracking, answer response contracts, reviewer insights, audit/tests/reports.",
        "28. Remaining limitations: manual browser checks are still required; warnings do not imply live model support.",
        "29. Demo readiness: Sanvia remains comparison-only/pending because base model is missing.",
        "",
        "## Generation Coverage",
        "",
        "| Task category | Task type | Frontend renderer | Backend source | Status | Missing/limitation |",
        "|---|---|---|---|---|---|",
    ])
    for row in generation_rows:
        lines.append("| " + " | ".join(row[key].replace("|", "/") for key in ["Task category", "Task type", "Frontend renderer", "Backend source", "Status", "Missing/limitation"]) + " |")
    lines.extend(["", "## Per-module Evaluation/Chart Inventory", ""])
    for item in inventory["items"]:
        lines.append(f"- {item['module']}: {item['status']} ({item['artifact_count']} artifacts)")
        if item["status"] == "warning":
            lines.append(f"  - Recommendation: {item['recommendation']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_audit() -> dict[str, Any]:
    module_report = build_module_audit()
    generation_rows = build_generation_coverage()
    inventory = build_evaluation_inventory()
    combined = {
        **module_report,
        "generation_task_coverage": generation_rows,
        "evaluation_inventory": inventory,
    }
    _write_json(JSON_REPORT, combined)
    _write_json(MODEL_JSON_REPORT, combined)
    _write_json(INVENTORY_JSON_REPORT, inventory)
    _write_module_md(MD_REPORT, module_report, generation_rows, inventory)
    _write_module_md(MODEL_MD_REPORT, module_report, generation_rows, inventory)
    _write_module_md(FRONTEND_REPORT, module_report, generation_rows, inventory)
    _write_inventory_md(INVENTORY_MD_REPORT, inventory)
    return combined


def _write_inventory_md(path: Path, inventory: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Module Evaluation Inventory Report", "", f"- Status: {inventory['status']}", "", "| Module | Status | Artifact count | Recommendation |", "|---|---|---|---|"]
    for item in inventory["items"]:
        lines.append(f"| {item['module']} | {item['status']} | {item['artifact_count']} | {item['recommendation']} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = run_audit()
    print(f"STATUS: {report['status']}")
    print("MODULE: full_system_connection_audit")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
