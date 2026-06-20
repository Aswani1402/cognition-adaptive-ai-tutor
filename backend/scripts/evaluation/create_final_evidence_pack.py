from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT / "evaluation_outputs" / "reports"
JSON_DIR = ROOT / "evaluation_outputs" / "json"
CHART_DIR = ROOT / "evaluation_outputs" / "charts"

JSON_REPORT = JSON_DIR / "final_evidence_pack.json"
MD_REPORT = REPORT_DIR / "final_evidence_pack.md"
OVERLEAF_MAPPING_REPORT = REPORT_DIR / "final_overleaf_section_mapping.md"
COMMANDS_REPORT = REPORT_DIR / "final_commands_run_summary.md"
MODULE_STATUS_REPORT = REPORT_DIR / "final_module_status_summary.md"
LIMITATIONS_REPORT = REPORT_DIR / "final_limitations_and_future_work.md"

FINAL_FLOW = "Teach -> Ask -> Evaluate -> Diagnose -> Adapt -> Remember -> Revise -> Progress"

DATASET_EXPLANATION = {
    "phase_1_public_datasets": [
        "EdNet: public student interaction data used as an external KT-style reference for sequence-based learner modeling.",
        "ASSISTments: public educational interaction data used as a reference for correctness, item, and skill-level modeling.",
        "OULAD: public open university interaction data used as a reference for behaviour, activity, and risk-style learner modeling.",
    ],
    "phase_2_local_system_data": [
        "tutor.db quiz_results: local learner answer records used by runtime evaluation, persistence, and learner-state updates.",
        "Learner state tables: local mastery, behaviour, reward, revision, and persistence tables used by backend adaptive logic.",
    ],
    "curated_datasets": [
        "Semantic answer benchmark: curated expected/learner answer cases for semantic scoring and label-quality evaluation.",
        "Doubt intent dataset: curated doubt utterances and labels for concept, debug, syntax, example, and follow-up doubt classification.",
    ],
    "generated_evaluation_datasets": [
        "RL logs: generated offline policy traces for policy comparison and safe action masking checks.",
        "Question banks: generated structured assessment cases for MCQ, debug, output prediction, transfer, challenge, explanation, and puzzle-style tasks.",
        "Generation cases: generated comparison prompts for template, RAG-grounded, connector, and fallback generation services.",
    ],
}

REPORT_CHAPTERS = [
    "Introduction",
    "Literature Review",
    "Dataset and System Data",
    "Methodology",
    "System Architecture",
    "Module Implementation",
    "Experimental Evaluation",
    "Result Analysis",
    "Website/API Design",
    "Limitations",
    "Future Work",
    "Conclusion",
]

DIAGRAM_CHECKLIST = [
    "Overall architecture",
    "Dataset/database flow",
    "KT pipeline",
    "Behaviour pipeline",
    "RAG pipeline",
    "RL / policy safety flow",
    "XAI dashboard flow",
    "Agentic orchestration flow",
    "Reward / gamification flow",
    "User database and persistence flow",
    "API / frontend response contract flow",
    "Evaluation flow",
]

REMAINING_WORK = [
    "Puzzle/gamified assessment schemas",
    "Actual FastAPI/API routes",
    "KP frontend UI",
    "Secure auth implementation",
    "Human-rated evaluation",
    "Sanvia pretrained model comparison if available; it is not the main final generator",
    "Retrain CogniTutorLM from scratch for reliable structured JSON generation",
    "Add constrained decoding or grammar-guided JSON generation for MCQ/debug/challenge outputs",
    "Replace template/rule baseline banks only after direct model-generated outputs pass strict validation",
    "Final deployment",
]


COGNITUTOR_LM_FROM_SCRATCH_DIAGNOSIS = {
    "section_title": "CogniTutorLM From-Scratch Generation Diagnosis",
    "module_role": "CogniTutorLM is trained from scratch and used as a project-specific LLM research module.",
    "stable_backend_service_modules": "PASS",
    "rag_connector": "PASS",
    "teaching_artifact_bank": {
        "valid": 494,
        "total": 494,
        "role": "stable template/rule-based baseline bank",
    },
    "assessment_question_bank": {
        "valid": 760,
        "total": 760,
        "role": "stable template/rule-based baseline bank",
    },
    "rag_grounded_direct_generation_micro_test": {
        "attempted": 7,
        "success": 7,
        "valid": 3,
        "avg_grounding_score": 0.7238,
        "avg_quality_score": 0.5957,
        "status": "WARN",
    },
    "structured_prompt_diagnosis": {
        "mcq_valid_count": 0,
        "debug_task_valid_count": 0,
        "revision_summary_valid_count": 0,
        "challenge_question_valid_count": 0,
    },
    "conclusion": (
        "Current CogniTutorLM checkpoint is not reliable enough for full structured "
        "content-bank generation."
    ),
    "clarification": (
        "generated_tutor_artifacts and assessment_question_bank are stable template/rule-based "
        "baseline banks, not fully direct CogniTutorLM-generated outputs."
    ),
    "stable_website_backend_guidance": (
        "The current stable website/backend should use validated baseline banks and "
        "RAG-grounded services."
    ),
    "pretrained_sanvia_role": "Pretrained/Sanvia model is comparison only, not the main final system.",
    "future_fix": (
        "Retrain CogniTutorLM from scratch on stronger structured JSON task data and/or "
        "add constrained decoding."
    ),
}


MODULES: list[dict[str, Any]] = [
    {
        "module_name": "KT / DKT / BKT / SAKT",
        "status": "completed",
        "keywords": ["kt_", "dkt", "bkt", "sakt", "knowledge"],
        "key_files": [
            "tutor/kt",
            "scripts/evaluation/check_kt_full_model_comparison.py",
            "scripts/evaluation/generate_kt_evaluation_charts.py",
        ],
        "commands_run": [
            "python -m scripts.evaluation.check_kt_full_model_comparison",
            "python -m scripts.evaluation.generate_kt_evaluation_charts",
        ],
        "limitations": [
            "DKT runtime can fall back to cumulative mastery when trained artifacts are unavailable.",
            "Final production use needs larger live learner sequences.",
        ],
        "wording": "Knowledge tracing was evaluated through DKT runtime readiness and comparison evidence against BKT/SAKT-style baselines. The backend exposes mastery signals for adaptive teaching, while preserving fallback behaviour when model artifacts are unavailable.",
        "overleaf_section": "Experimental Evaluation / Knowledge Tracing Evaluation",
    },
    {
        "module_name": "Behaviour modeling",
        "status": "completed",
        "keywords": ["behaviour", "behavior"],
        "key_files": [
            "tutor/behaviour",
            "scripts/evaluation/check_behaviour_full_model_comparison.py",
            "scripts/evaluation/generate_behaviour_evaluation_charts.py",
        ],
        "commands_run": [
            "python -m scripts.evaluation.check_behaviour_full_model_comparison",
            "python -m scripts.evaluation.generate_behaviour_evaluation_charts",
        ],
        "limitations": [
            "Behaviour labels remain partly proxy-derived and should be improved with real usage data.",
        ],
        "wording": "The behaviour module models learner risk and engagement signals separately from correctness, enabling adaptive decisions to respond to confidence, persistence, and risk-related evidence.",
        "overleaf_section": "Experimental Evaluation / Behaviour Modeling Evaluation",
    },
    {
        "module_name": "Semantic evaluator",
        "status": "completed",
        "keywords": ["semantic"],
        "key_files": [
            "tutor/evaluation",
            "scripts/evaluation/check_semantic_evaluator_report.py",
            "scripts/evaluation/check_semantic_answer_benchmark.py",
        ],
        "commands_run": [
            "python -m scripts.evaluation.check_semantic_evaluator_report",
            "python -m scripts.evaluation.check_semantic_answer_benchmark",
            "python -m scripts.evaluation.generate_semantic_evaluator_charts",
            "python -m scripts.evaluation.generate_semantic_benchmark_charts",
        ],
        "limitations": [
            "Automatic semantic scores should be validated by blind human ratings before claiming final pedagogical validity.",
        ],
        "wording": "The semantic evaluator provides rubric-like answer quality scoring for free-form learner responses and is supported by curated benchmark cases and visualization reports.",
        "overleaf_section": "Experimental Evaluation / Answer and Semantic Evaluation",
    },
    {
        "module_name": "AnswerEvaluator / SafeCodeRunner",
        "status": "completed",
        "keywords": ["answer_evaluator", "safe_code", "code_runner", "code_question", "debug_evaluator", "output_prediction", "rubric"],
        "key_files": [
            "tutor/evaluation",
            "tutor/code",
            "scripts/test_code_runner.py",
            "scripts/test_answer_evaluator.py",
        ],
        "commands_run": [
            "python -m scripts.evaluation.check_answer_evaluator_report",
            "python -m scripts.test_code_runner",
            "python -m scripts.test_answer_evaluator",
        ],
        "limitations": [
            "Safe execution is backend-limited and still needs production sandbox hardening before public deployment.",
        ],
        "wording": "The unified evaluator supports objective, code, debug, output-prediction, explanation, transfer, and challenge tasks. SafeCodeRunner enables controlled code execution for learner-facing programming activities.",
        "overleaf_section": "Module Implementation / Assessment and Code Evaluation",
    },
    {
        "module_name": "Doubt classifier",
        "status": "completed",
        "keywords": ["doubt"],
        "key_files": [
            "tutor/doubt",
            "scripts/evaluation/check_doubt_classifier_report.py",
            "scripts/evaluation/generate_doubt_classifier_charts.py",
        ],
        "commands_run": [
            "python -m scripts.evaluation.check_doubt_classifier_report",
            "python -m scripts.evaluation.generate_doubt_classifier_charts",
        ],
        "limitations": [
            "Classifier accuracy should improve with more real learner doubt utterances.",
        ],
        "wording": "The doubt classifier identifies learner intent so the tutor can route questions to explanation, debugging, syntax help, examples, or follow-up clarification paths.",
        "overleaf_section": "Module Implementation / Doubt Handling",
    },
    {
        "module_name": "RAG retrieval and grounding",
        "status": "completed",
        "keywords": ["rag", "retrieval", "grounding"],
        "key_files": [
            "rag_dyna",
            "tutor/rag",
            "scripts/evaluation/check_rag_grounding_report.py",
            "scripts/evaluation/check_rag_retrieval_comparison_report.py",
        ],
        "commands_run": [
            "python -m scripts.evaluation.check_rag_grounding_report",
            "python -m scripts.evaluation.check_rag_retrieval_comparison_report",
            "python -m scripts.evaluation.generate_rag_evaluation_charts",
        ],
        "limitations": [
            "Grounding checks are evidence/coverage based and do not prove full semantic entailment.",
        ],
        "wording": "RAG retrieval and grounding evidence reduce unsupported explanations by tracking source sections, unsupported terms, and context coverage for tutor responses.",
        "overleaf_section": "Experimental Evaluation / RAG Retrieval and Grounding",
    },
    {
        "module_name": "RL / policy safety",
        "status": "comparison-mode",
        "keywords": ["rl_", "dqn", "policy", "safe_action", "counterfactual"],
        "key_files": [
            "tutor/rl",
            "scripts/evaluation/check_rl_model_comparison_report.py",
            "scripts/evaluation/check_rl_safe_action_masking.py",
        ],
        "commands_run": [
            "python -m scripts.evaluation.check_rl_model_comparison_report",
            "python -m scripts.evaluation.check_rl_safe_action_masking",
            "python -m scripts.evaluation.generate_rl_evaluation_charts",
        ],
        "limitations": [
            "RL remains comparison/shadow evidence and should not replace rules without live safety validation.",
        ],
        "wording": "RL policy work is evaluated in comparison mode with safe action masking and counterfactual checks, providing evidence for future policy learning without overriding backend safety constraints.",
        "overleaf_section": "Experimental Evaluation / RL and Policy Safety",
    },
    {
        "module_name": "XAI dashboard",
        "status": "backend-ready",
        "keywords": ["xai"],
        "key_files": [
            "tutor/xai/xai_dashboard_builder.py",
            "scripts/test_xai_dashboard_builder.py",
            "scripts/evaluation/check_xai_final_explanation_report.py",
        ],
        "commands_run": [
            "python -m scripts.test_xai_dashboard_builder",
            "python -m scripts.evaluation.check_xai_final_explanation_report",
            "python -m scripts.evaluation.generate_xai_evaluation_charts",
        ],
        "limitations": [
            "XAI explanations summarize backend evidence but are not causal proof of learner outcomes.",
        ],
        "wording": "The XAI dashboard exposes why the tutor selected an action through feature contributions, evidence coverage, decision pressure, and counterfactual summaries.",
        "overleaf_section": "Experimental Evaluation / Explainability and Dashboard Evidence",
    },
    {
        "module_name": "Reward / gamification",
        "status": "backend-ready",
        "keywords": ["reward", "gamification", "badge", "streak", "unlock"],
        "key_files": [
            "tutor/reward",
            "scripts/test_badge_daily_goal_unlock.py",
            "scripts/evaluation/check_reward_gamification_report.py",
        ],
        "commands_run": [
            "python -m scripts.test_badge_daily_goal_unlock",
            "python -m scripts.evaluation.check_reward_gamification_report",
            "python -m scripts.evaluation.generate_reward_gamification_charts",
        ],
        "limitations": [
            "Gamification is backend-ready but needs frontend UX and longitudinal learner validation.",
        ],
        "wording": "Reward and gamification support XP, streaks, badges, daily goals, and concept unlocks as persistence-backed learner progression signals.",
        "overleaf_section": "Module Implementation / Reward and Progression",
    },
    {
        "module_name": "Notebook memory / revision",
        "status": "backend-ready",
        "keywords": ["notebook", "revision", "memory"],
        "key_files": [
            "tutor/memory",
            "scripts/evaluation/check_notebook_memory_revision_report.py",
        ],
        "commands_run": [
            "python -m scripts.evaluation.check_notebook_memory_revision_report",
        ],
        "limitations": [
            "Revision plans require real long-term usage to validate retention improvements.",
        ],
        "wording": "Notebook memory stores learner weaknesses, strengths, mistake patterns, and revision queues so the tutor can support returning learners and spaced review.",
        "overleaf_section": "Module Implementation / Notebook Memory and Revision",
    },
    {
        "module_name": "Agentic orchestration",
        "status": "backend-ready",
        "keywords": ["agentic", "orchestration"],
        "key_files": [
            "tutor/system",
            "scripts/evaluation/check_agentic_orchestration_report.py",
        ],
        "commands_run": [
            "python -m scripts.evaluation.check_agentic_orchestration_report",
        ],
        "limitations": [
            "Agentic routing is backend-orchestrated and still needs frontend/session-level user study validation.",
        ],
        "wording": "Agentic orchestration coordinates KT, behaviour, evaluation, RAG, memory, reward, and generation modules into a traceable adaptive tutor flow.",
        "overleaf_section": "System Architecture / Agentic Orchestration",
    },
    {
        "module_name": "Generation/service comparison",
        "status": "comparison-mode",
        "keywords": ["generation", "service", "cognitutor", "sanvia"],
        "key_files": [
            "tutor/generation",
            "scripts/evaluation/check_generation_service_comparison.py",
            "scripts/evaluation/generate_generation_comparison_charts.py",
        ],
        "commands_run": [
            "python -m scripts.evaluation.check_generation_service_comparison",
            "python -m scripts.evaluation.generate_generation_comparison_charts",
        ],
        "limitations": [
            "External Sanvia integration is pending because no safe runnable model API/artifact is currently integrated.",
        ],
        "wording": "Generation service comparison evaluates template, RAG-grounded, connector, and fallback paths to document quality, grounding, latency, task coverage, and external model readiness.",
        "overleaf_section": "Experimental Evaluation / Generation Service Comparison",
    },
    {
        "module_name": "User persistence",
        "status": "backend-ready",
        "keywords": ["persistence", "user", "website", "api_routes"],
        "key_files": [
            "tutor/persistence",
            "scripts/evaluation/check_website_user_persistence_report.py",
            "docs/frontend_api_contract_cognitutor_lm.md",
        ],
        "commands_run": [
            "python -m scripts.evaluation.check_website_user_persistence_report",
            "python -m scripts.test_api_routes_smoke",
        ],
        "limitations": [
            "Secure authentication and production authorization are still pending.",
        ],
        "wording": "User persistence supports learner state continuity across sessions and provides the backend foundation for website/API integration.",
        "overleaf_section": "Website/API Design / User Persistence",
    },
    {
        "module_name": "Multi-user integrated evaluation",
        "status": "completed",
        "keywords": ["multi_user"],
        "key_files": [
            "scripts/evaluation/run_multi_user_integrated_evaluation.py",
            "scripts/evaluation/generate_multi_user_evaluation_charts.py",
        ],
        "commands_run": [
            "python -m scripts.evaluation.run_multi_user_integrated_evaluation",
            "python -m scripts.evaluation.generate_multi_user_evaluation_charts",
        ],
        "limitations": [
            "Multi-user evaluation is simulated/backend-driven and not a live classroom deployment.",
        ],
        "wording": "The multi-user evaluation demonstrates learner-wise variation in mastery, behaviour risk, teaching views, mistakes, and reward outcomes across integrated backend sessions.",
        "overleaf_section": "Experimental Evaluation / Multi-User Integrated Evaluation",
    },
    {
        "module_name": "Overall system evaluation",
        "status": "completed",
        "keywords": ["overall", "final_backend", "full_backend", "final_chart"],
        "key_files": [
            "scripts/evaluation/run_overall_system_evaluation.py",
            "scripts/evaluation/generate_overall_evaluation_charts.py",
            "scripts/evaluation/generate_final_backend_report.py",
        ],
        "commands_run": [
            "python -m scripts.evaluation.run_overall_system_evaluation",
            "python -m scripts.evaluation.generate_overall_evaluation_charts",
            "python -m scripts.evaluation.check_final_chart_inventory",
            "python -m scripts.evaluation.generate_final_backend_report",
        ],
        "limitations": [
            "Overall score summarizes artifact readiness and automated checks, not end-user learning gains.",
        ],
        "wording": "Overall evaluation consolidates report availability, chart coverage, module status, backend smoke tests, and remaining work into a final readiness view.",
        "overleaf_section": "Experimental Evaluation / Overall Backend Evaluation",
    },
    {
        "module_name": "Frontend response builder",
        "status": "backend-ready",
        "keywords": ["frontend", "contract", "api_routes"],
        "key_files": [
            "tutor/system/frontend_response_builder.py",
            "scripts/test_frontend_response_builder.py",
            "scripts/test_frontend_contract_full.py",
            "docs/frontend_api_contract_cognitutor_lm.md",
        ],
        "commands_run": [
            "python -m scripts.test_frontend_response_builder",
            "python -m scripts.test_frontend_contract_full",
        ],
        "limitations": [
            "The compact response contract is backend-ready, while the KP frontend UI is pending.",
        ],
        "wording": "The frontend response builder compresses the integrated tutor output into stable teaching, assessment, revision, tools, reward, progress, XAI, and CogniTutorLM sections for frontend consumption.",
        "overleaf_section": "Website/API Design / Frontend Contract",
    },
    {
        "module_name": "CogniTutorLM connector",
        "status": "backend-ready",
        "keywords": ["cognitutor"],
        "key_files": [
            "tutor/generation/cognitutor_lm_connector.py",
            "docs/frontend_api_contract_cognitutor_lm.md",
        ],
        "commands_run": [
            "python -m scripts.test_frontend_response_builder",
        ],
        "limitations": [
            "CogniTutorLM remains optional connector output and does not replace the main adaptive backend pipeline.",
        ],
        "wording": "The CogniTutorLM connector is integrated as optional comparison/demo output while the main backend pipeline remains responsible for adaptive teaching, assessment, RAG, reward, and XAI decisions.",
        "overleaf_section": "System Architecture / CogniTutorLM Connector",
    },
    {
        "module_name": "Pending frontend/API/puzzle/human evaluation work",
        "status": "pending",
        "keywords": ["puzzle", "gamified", "frontend", "human", "deployment"],
        "key_files": [
            "docs/frontend_api_contract_cognitutor_lm.md",
            "evaluation_outputs/reports/frontend_api_routes_plan.md",
        ],
        "commands_run": [
            "python -m scripts.test_frontend_contract_full",
        ],
        "limitations": REMAINING_WORK,
        "wording": "Remaining work is clearly separated from completed backend evidence: puzzle schemas, production API routes, KP frontend UI, secure auth, human-rated evaluation, optional Sanvia integration, and deployment are future implementation or validation tracks.",
        "overleaf_section": "Limitations / Future Work",
    },
]


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _artifact_names(directory: Path, suffix: str) -> list[str]:
    if not directory.exists():
        return []
    return sorted(path.name for path in directory.glob(f"*{suffix}"))


def _matching_artifacts(names: list[str], keywords: list[str], prefix: str) -> list[str]:
    matched = []
    for name in names:
        lower = name.lower()
        if any(keyword.lower() in lower for keyword in keywords):
            matched.append(f"{prefix}/{name}")
    return matched


def _collect_numbers(value: Any, prefix: str = "") -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            child_key = f"{prefix}.{key}" if prefix else str(key)
            metrics.update(_collect_numbers(child, child_key))
    elif isinstance(value, (int, float, str)) and not isinstance(value, bool):
        key_lower = prefix.lower()
        interesting = [
            "accuracy",
            "f1",
            "score",
            "rate",
            "coverage",
            "count",
            "status",
            "auc",
            "loss",
            "quality",
            "confidence",
        ]
        if any(token in key_lower for token in interesting):
            metrics[prefix] = value
    return metrics


def _short_metrics(report_paths: list[str], limit: int = 8) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for report_path in report_paths:
        data = _read_json(ROOT / report_path)
        if data is None:
            continue
        for key, value in _collect_numbers(data).items():
            short_key = key.split(".")[-1]
            if short_key not in metrics:
                metrics[short_key] = value
            if len(metrics) >= limit:
                return metrics
    return metrics


def _load_existing_diagram_checklist() -> list[str]:
    path = REPORT_DIR / "final_report_diagram_checklist.md"
    if not path.exists():
        return DIAGRAM_CHECKLIST
    lines = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("- ["):
            lines.append(line.replace("- [ ] ", "").replace("- [x] ", ""))
    return lines or DIAGRAM_CHECKLIST


def _build_module_entries() -> list[dict[str, Any]]:
    report_names = _artifact_names(REPORT_DIR, ".md")
    json_names = _artifact_names(JSON_DIR, ".json")
    chart_names = _artifact_names(CHART_DIR, ".png")

    entries = []
    for spec in MODULES:
        reports = _matching_artifacts(report_names, spec["keywords"], "evaluation_outputs/reports")
        json_reports = _matching_artifacts(json_names, spec["keywords"], "evaluation_outputs/json")
        charts = _matching_artifacts(chart_names, spec["keywords"], "evaluation_outputs/charts")
        best_metrics = _short_metrics(json_reports)
        entries.append(
            {
                "module_name": spec["module_name"],
                "status": spec["status"],
                "key_files_created_or_patched": spec["key_files"],
                "commands_run": spec["commands_run"],
                "reports_generated": reports,
                "json_reports_generated": json_reports,
                "charts_generated": charts,
                "best_metrics": best_metrics,
                "important_limitations": spec["limitations"],
                "suggested_final_report_wording": spec["wording"],
                "suggested_overleaf_chapter_section": spec["overleaf_section"],
            }
        )
    return entries


def _build_pack() -> dict[str, Any]:
    overall = _read_json(JSON_DIR / "overall_system_evaluation_report.json") or {}
    chart_inventory = _read_json(JSON_DIR / "final_chart_inventory_report.json") or {}
    modules = _build_module_entries()
    status_counts: dict[str, int] = {}
    for module in modules:
        status_counts[module["status"]] = status_counts.get(module["status"], 0) + 1

    return {
        "status": "success",
        "module": "final_evidence_pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "Final backend evidence pack and Overleaf report-writing handoff for the Cognition-Adaptive AI Tutor.",
        "final_system_flow": FINAL_FLOW,
        "dataset_explanation": DATASET_EXPLANATION,
        "report_chapter_mapping": REPORT_CHAPTERS,
        "diagram_checklist": _load_existing_diagram_checklist(),
        "remaining_work": REMAINING_WORK,
        "cognitutor_lm_from_scratch_generation_diagnosis": COGNITUTOR_LM_FROM_SCRATCH_DIAGNOSIS,
        "status_counts": status_counts,
        "overall_system_evaluation_summary": {
            "overall_backend_status": overall.get("overall_backend_status"),
            "completed_module_count": overall.get("completed_module_count"),
            "warning_module_count": overall.get("warning_module_count"),
            "pending_module_count": overall.get("pending_module_count"),
            "comparison_mode_count": overall.get("comparison_mode_count"),
            "overall_scorecard": overall.get("overall_scorecard", {}),
        },
        "chart_inventory_summary": {
            "total_chart_count": chart_inventory.get("total_chart_count"),
            "chart_list_by_module": chart_inventory.get("chart_list_by_module", {}),
        },
        "modules": modules,
        "generated_outputs": {
            "json_report": _relative(JSON_REPORT),
            "md_report": _relative(MD_REPORT),
            "overleaf_mapping_report": _relative(OVERLEAF_MAPPING_REPORT),
            "commands_report": _relative(COMMANDS_REPORT),
            "module_status_report": _relative(MODULE_STATUS_REPORT),
            "limitations_report": _relative(LIMITATIONS_REPORT),
        },
    }


def _md_list(items: list[Any]) -> str:
    if not items:
        return "- None recorded"
    return "\n".join(f"- {item}" for item in items)


def _metrics_md(metrics: dict[str, Any]) -> str:
    if not metrics:
        return "- No numeric summary extracted; see linked reports."
    lines = []
    for key, value in metrics.items():
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        lines.append(f"- `{key}`: {value}")
    return "\n".join(lines)


def _diagnosis_md(diagnosis: dict[str, Any]) -> str:
    micro = diagnosis["rag_grounded_direct_generation_micro_test"]
    structured = diagnosis["structured_prompt_diagnosis"]
    return "\n".join(
        [
            f"## {diagnosis['section_title']}",
            "",
            f"- {diagnosis['module_role']}",
            f"- Stable CogniTutorLM backend/service modules: `{diagnosis['stable_backend_service_modules']}`",
            f"- RAG connector: `{diagnosis['rag_connector']}`; it successfully provides grounded concept context.",
            f"- Teaching artifact bank: `{diagnosis['teaching_artifact_bank']['valid']}/{diagnosis['teaching_artifact_bank']['total']}` valid baseline bank.",
            f"- Assessment question bank: `{diagnosis['assessment_question_bank']['valid']}/{diagnosis['assessment_question_bank']['total']}` valid baseline bank.",
            "- Direct RAG + CogniTutorLM generation was tested.",
            f"- Micro test: attempted={micro['attempted']}, success={micro['success']}, valid={micro['valid']}, avg_grounding_score={micro['avg_grounding_score']}, avg_quality_score={micro['avg_quality_score']}, status={micro['status']}.",
            "- Simple generation is possible, but structured MCQ/debug/challenge generation is not reliable with the current checkpoint.",
            f"- Structured prompt diagnosis: MCQ valid_count={structured['mcq_valid_count']}, debug_task valid_count={structured['debug_task_valid_count']}, revision_summary valid_count={structured['revision_summary_valid_count']}, challenge_question valid_count={structured['challenge_question_valid_count']}.",
            f"- Conclusion: {diagnosis['conclusion']}",
            f"- Stable website/backend guidance: {diagnosis['stable_website_backend_guidance']}",
            f"- Clarification: {diagnosis['clarification']}",
            f"- Pretrained/Sanvia role: {diagnosis['pretrained_sanvia_role']}",
            f"- Future work: {diagnosis['future_fix']}",
            "",
        ]
    )


def _write_main_report(pack: dict[str, Any]) -> None:
    lines = [
        "# Final Evidence Pack",
        "",
        f"Generated at: `{pack['generated_at']}`",
        "",
        f"Status: `{pack['status']}`",
        "",
        "## Purpose",
        "",
        pack["purpose"],
        "",
        "## Final System Flow",
        "",
        pack["final_system_flow"],
        "",
        "## Dataset Explanation",
        "",
    ]
    for title, items in pack["dataset_explanation"].items():
        lines.extend([f"### {title.replace('_', ' ').title()}", "", _md_list(items), ""])

    lines.extend(
        [
            "## Overall Evaluation Snapshot",
            "",
            f"- Backend status: `{pack['overall_system_evaluation_summary'].get('overall_backend_status')}`",
            f"- Status counts: `{pack['status_counts']}`",
            f"- Chart count: `{pack['chart_inventory_summary'].get('total_chart_count')}`",
            "",
            _diagnosis_md(pack["cognitutor_lm_from_scratch_generation_diagnosis"]),
            "## Module Evidence",
            "",
        ]
    )
    for module in pack["modules"]:
        lines.extend(
            [
                f"### {module['module_name']}",
                "",
                f"- Status: `{module['status']}`",
                f"- Suggested Overleaf placement: {module['suggested_overleaf_chapter_section']}",
                "",
                "**Key files created or patched**",
                "",
                _md_list(module["key_files_created_or_patched"]),
                "",
                "**Commands run**",
                "",
                _md_list(module["commands_run"]),
                "",
                "**Reports generated**",
                "",
                _md_list(module["reports_generated"] + module["json_reports_generated"]),
                "",
                "**Charts generated**",
                "",
                _md_list(module["charts_generated"]),
                "",
                "**Best metrics**",
                "",
                _metrics_md(module["best_metrics"]),
                "",
                "**Important limitations**",
                "",
                _md_list(module["important_limitations"]),
                "",
                "**Suggested final report wording**",
                "",
                module["suggested_final_report_wording"],
                "",
            ]
        )

    lines.extend(
        [
            "## Diagram Checklist",
            "",
            _md_list(pack["diagram_checklist"]),
            "",
            "## Remaining Work",
            "",
            _md_list(pack["remaining_work"]),
            "",
            "## Terminal Output",
            "",
            "```text",
            "STATUS: success",
            "MODULE: final_evidence_pack",
            "JSON_REPORT: evaluation_outputs/json/final_evidence_pack.json",
            "MD_REPORT: evaluation_outputs/reports/final_evidence_pack.md",
            "```",
            "",
        ]
    )
    MD_REPORT.write_text("\n".join(lines), encoding="utf-8")


def _write_overleaf_mapping(pack: dict[str, Any]) -> None:
    lines = [
        "# Final Overleaf Section Mapping",
        "",
        "## Chapter Map",
        "",
        _md_list(pack["report_chapter_mapping"]),
        "",
        "## Module Placement",
        "",
    ]
    for module in pack["modules"]:
        lines.append(f"- **{module['module_name']}**: {module['suggested_overleaf_chapter_section']}")
    lines.extend(["", "## Diagram Checklist", "", _md_list(pack["diagram_checklist"]), ""])
    OVERLEAF_MAPPING_REPORT.write_text("\n".join(lines), encoding="utf-8")


def _write_commands_report(pack: dict[str, Any]) -> None:
    seen = []
    for module in pack["modules"]:
        for command in module["commands_run"]:
            if command not in seen:
                seen.append(command)
    lines = [
        "# Final Commands Run Summary",
        "",
        "These are the evidence-generation and validation commands referenced by the final handoff.",
        "",
        _md_list(seen),
        "",
        "## Final Pack Command",
        "",
        "- python -m scripts.evaluation.create_final_evidence_pack",
        "",
    ]
    COMMANDS_REPORT.write_text("\n".join(lines), encoding="utf-8")


def _write_module_status_report(pack: dict[str, Any]) -> None:
    lines = [
        "# Final Module Status Summary",
        "",
        f"Status counts: `{pack['status_counts']}`",
        "",
        "| Module | Status | Reports | Charts | Overleaf placement |",
        "|---|---:|---:|---:|---|",
    ]
    for module in pack["modules"]:
        report_count = len(module["reports_generated"]) + len(module["json_reports_generated"])
        chart_count = len(module["charts_generated"])
        lines.append(
            f"| {module['module_name']} | {module['status']} | {report_count} | {chart_count} | {module['suggested_overleaf_chapter_section']} |"
        )
    lines.append("")
    MODULE_STATUS_REPORT.write_text("\n".join(lines), encoding="utf-8")


def _write_limitations_report(pack: dict[str, Any]) -> None:
    lines = [
        "# Final Limitations And Future Work",
        "",
        "## Cross-Cutting Limitations",
        "",
        "- Automated backend evaluations do not replace blind human-rated pedagogical evaluation.",
        "- Several ML modules are backend-ready or comparison-mode rather than production-replacement models.",
        "- Live deployment requires production API routing, secure authentication, monitoring, and frontend validation.",
        "- External pretrained model integration remains optional and must be validated through a safe API before learner use.",
        "- CogniTutorLM direct structured generation is experimental/WARN and should not be reported as PASS until generated outputs pass strict validation.",
        "- Template/rule banks remain stable baseline/fallback banks, not direct CogniTutorLM-generated content.",
        "",
        _diagnosis_md(pack["cognitutor_lm_from_scratch_generation_diagnosis"]),
        "## Module-Specific Limitations",
        "",
    ]
    for module in pack["modules"]:
        lines.extend([f"### {module['module_name']}", "", _md_list(module["important_limitations"]), ""])
    lines.extend(["## Future Work", "", _md_list(pack["remaining_work"]), ""])
    LIMITATIONS_REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    pack = _build_pack()

    JSON_REPORT.write_text(json.dumps(pack, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_main_report(pack)
    _write_overleaf_mapping(pack)
    _write_commands_report(pack)
    _write_module_status_report(pack)
    _write_limitations_report(pack)

    print("STATUS: success")
    print("MODULE: final_evidence_pack")
    print("JSON_REPORT: evaluation_outputs/json/final_evidence_pack.json")
    print("MD_REPORT: evaluation_outputs/reports/final_evidence_pack.md")


if __name__ == "__main__":
    main()
