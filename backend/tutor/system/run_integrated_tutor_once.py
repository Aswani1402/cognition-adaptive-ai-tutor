from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tutor.long_term_personalization.profile_engine import get_policy_teaching_bias
from tutor.utils.fetch_learning_content import get_learning_content
from tutor.rag.rag_context_builder import build_rag_concept_resource
from tutor.behaviour.lstm_behaviour_model import run_behaviour_model
from tutor.agents.tutor_agent import TutorAgent
from tutor.agents.assessment_agent import AssessmentAgent
from tutor.agents.evaluator_agent import EvaluatorAgent
from tutor.agents.decision_agent import DecisionAgent
from tutor.RL.rl_logger import log_from_tutor_pipeline
from tutor.system.reflection_agent import ReflectionAgent
from tutor.system.learner_insight_layer import LearnerInsightLayer
from tutor.adaptation.view_performance_tracker import ViewPerformanceTracker
from tutor.concept_dependency.run_dependency_module_final import run_dependency_module_final
from tutor.path.adaptive_path_selector import AdaptivePathSelector
from tutor.path.adaptive_path_validation import (
    build_frontend_path_output,
    load_concept_id_map,
    validate_selected_concept_id,
)
from tutor.policy.adaptive_policy_bridge import AdaptivePolicyBridge
from tutor.policy.adaptive_hint_policy import AdaptiveHintPolicy
from tutor.policy.learned_hint_policy import LearnedHintPolicy
from tutor.xai.feature_contribution_explainer import FeatureContributionExplainer
from tutor.memory.learner_notebook_memory import LearnerNotebookMemory
from tutor.strategy.selector import recommend_evidence_aware_teaching_strategy
from tutor.strategy.strategy_training_logger import log_teaching_strategy_training_session
from tutor.strategy.model_based_selector import ModelBasedTeachingStrategySelector
from tutor.strategy.learned_teaching_strategy_selector import (
    LearnedTeachingStrategySelector,
    merge_pipeline_evidence,
)
from tutor.strategy.model_comparison_logger import log_teaching_strategy_model_comparison
from tutor.system.concept_name_resolver import resolve_concept_name
from tutor.generation.frontend_view_adapter import build_frontend_teaching_view
from tutor.generation.voice_script_generator import VoiceScriptGenerator
from tutor.assessment.structured_question_types import normalize_assessment_bundle_for_frontend
from tutor.assessment.expanded_assessment_generator import attach_expanded_questions_to_bundle
from tutor.evaluation.structured_evaluation_bridge import run_structured_evaluation_bridge
from tutor.progression.progression_reward_engine import build_progression_reward_output
from tutor.progression.reward_state_store import persist_reward_state


DB_PATH = Path("external/core_data/tutor.db")
CONCEPT_DB_PATHS = [
    "external/core_data/python_learning.db",
    "external/core_data/html_web_basics.db",
    "external/core_data/database_sql.db",
    "external/core_data/git_version_control.db",
    "external/core_data/data_structures.db",
]

# =========================
# DB helpers
# =========================

def get_connection(db_path: str | Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn



def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


def get_behaviour_runtime_summary(behaviour_state: dict[str, Any]) -> dict[str, Any]:
    data = behaviour_state.get("data", {}) if isinstance(behaviour_state, dict) else {}
    if isinstance(data.get("data"), dict):
        data = data.get("data", {})
    return {
        "model_source": data.get("model_source") or data.get("behavior_source"),
        "model_source_label": "LSTM runtime" if (data.get("model_source") or data.get("behavior_source")) == "lstm_runtime" else "fallback proxy",
        "behaviour_state": data.get("behaviour_state") or data.get("behavior_label"),
        "behaviour_risk": data.get("behaviour_risk") or data.get("behavior_risk"),
        "confidence_score": data.get("confidence_score") or data.get("behavior_confidence"),
        "evidence_inputs": data.get("evidence_inputs", {}),
        "fallback_reason": data.get("fallback_reason"),
    }


def get_kt_runtime_summary(knowledge_state: dict[str, Any]) -> dict[str, Any]:
    data = knowledge_state.get("data", {}).get("data", {}) if isinstance(knowledge_state, dict) else {}
    return {
        "concept_id": data.get("concept_id") or next(iter(data.get("written_state", {}) or {}), None),
        "mastery_before": data.get("mastery_before"),
        "mastery_after": data.get("mastery_after") or data.get("predicted_mastery_last"),
        "kt_source": data.get("kt_source") or data.get("source") or "Not available",
        "fallback_used": bool(data.get("fallback_used")),
        "fallback_reason": data.get("fallback_reason") or data.get("inference_error"),
        "model_path": data.get("model_path"),
    }


def get_policy_runtime_summary(decision_agent_output: dict[str, Any], policy_output: dict[str, Any]) -> dict[str, Any]:
    packet = decision_agent_output.get("safe_policy_output", {}) if isinstance(decision_agent_output, dict) else {}
    data = policy_output.get("data", {}) if isinstance(policy_output, dict) else {}
    return {
        "label": "Policy/RL safe decision support",
        "policy_source": packet.get("policy_source") or data.get("policy_source") or "safe_rule_fallback",
        "raw_policy_recommendation": packet.get("raw_policy_recommendation") or data.get("raw_policy_recommendation"),
        "raw_recommendation": packet.get("raw_policy_recommendation") or data.get("raw_policy_recommendation"),
        "safe_mask_applied": bool(packet.get("safe_mask_applied") or data.get("safe_mask_applied")),
        "final_safe_action": packet.get("final_safe_action") or data.get("final_safe_action"),
        "reason": packet.get("reason") or data.get("policy_reason"),
    }


def get_generation_source_summary(cognitutor_lm_output: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(cognitutor_lm_output, dict):
        return {"final_learner_facing_source": "Not available", "fallback_used": True}
    product = cognitutor_lm_output.get("cognitutor_lm_product_output") or {}
    return {
        "raw_cognitutor_attempted": bool(cognitutor_lm_output.get("raw_cognitutor_attempted")),
        "raw_valid": bool(cognitutor_lm_output.get("raw_valid")),
        "guarded_product_generator_used": bool(cognitutor_lm_output.get("guarded_product_generator_used")),
        "fallback_used": bool(cognitutor_lm_output.get("fallback_used")),
        "final_learner_facing_source": cognitutor_lm_output.get("final_learner_facing_source") or product.get("source") or cognitutor_lm_output.get("source") or "Not available",
        "validation_reason": cognitutor_lm_output.get("validation_reason"),
        "reviewer_safe_explanation": "Learner-facing content uses guarded generation; raw CogniTutorLM is not directly trusted.",
    }


def get_adaptive_path_validation_summary(
    adaptive_path_output: dict[str, Any] | None,
    adaptive_path_validation_output: dict[str, Any],
) -> dict[str, Any]:
    original = (
        adaptive_path_output.get("original_selected_next_concept")
        if isinstance(adaptive_path_output, dict)
        else None
    )
    selected = (
        adaptive_path_output.get("selected_next_concept")
        if isinstance(adaptive_path_output, dict)
        else None
    )
    fallback_used = bool(adaptive_path_validation_output.get("fallback_used"))
    message = adaptive_path_validation_output.get("reason")
    if fallback_used and original and selected and str(original) != str(selected):
        message = "Adaptive path validator corrected a wrong-domain recommendation."
    return {
        "status": (
            "fallback"
            if fallback_used
            else "valid"
            if adaptive_path_validation_output.get("valid")
            else "invalid"
        ),
        "original_selected_concept_id": original,
        "final_selected_concept_id": selected,
        "resolved_concept_id": adaptive_path_validation_output.get("resolved_concept_id"),
        "resolved_concept_name": adaptive_path_validation_output.get("resolved_concept_name"),
        "resolved_domain": adaptive_path_validation_output.get("resolved_domain"),
        "fallback_used": fallback_used,
        "message": message,
    }


def build_reward_source_summary(
    progression_reward_output: dict[str, Any],
    reward_persistence_output: dict[str, Any],
) -> dict[str, Any]:
    reward_state = progression_reward_output.get("reward_state", {}) if isinstance(progression_reward_output, dict) else {}
    progression = progression_reward_output.get("progression_result", {}) if isinstance(progression_reward_output, dict) else {}
    persisted = isinstance(reward_persistence_output, dict) and reward_persistence_output.get("status") == "success"
    return {
        "reward_source": "backend_reward_state" if persisted else "session_progress_preview",
        "xp": reward_persistence_output.get("total_xp") if persisted else reward_state.get("xp_awarded", 0),
        "streak": reward_persistence_output.get("current_streak") if persisted else reward_state.get("streak_updated", False),
        "daily_goal_progress": reward_persistence_output.get("daily_xp") if isinstance(reward_persistence_output, dict) else 0,
        "badge_status": reward_persistence_output.get("badge_status", "Not available") if isinstance(reward_persistence_output, dict) else "Not available",
        "concept_progress": progression or "Not available",
    }


# =========================
# Quiz
# =========================

def run_quiz_step(conn: sqlite3.Connection, learner_id: str) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT *
        FROM quiz_results
        WHERE learner_id = ?
        ORDER BY
            CASE WHEN timestamp IS NULL THEN 1 ELSE 0 END,
            timestamp DESC,
            quiz_id DESC
        LIMIT 1
        """,
        (learner_id,),
    ).fetchone()

    if row is None:
        return {
            "status": "no_quiz_result_found",
            "learner_id": learner_id,
        }

    return {
        "status": "success",
        "learner_id": learner_id,
        "latest_quiz_result": row_to_dict(row),
    }


# =========================
# Knowledge state
# =========================

def run_knowledge_state(conn: sqlite3.Connection, learner_id: str) -> dict[str, Any]:
    try:
        from tutor.knowledge_state.update import update_knowledge_state

        result = update_knowledge_state(conn, learner_id)
        return {
            "status": "success",
            "learner_id": learner_id,
            "data": result,
        }
    except Exception as e:
        return {
            "status": "error",
            "module": "knowledge_state",
            "error": str(e),
        }


# =========================
# Behaviour
# =========================

def run_behaviour_state(conn: sqlite3.Connection, learner_id: str) -> dict[str, Any]:
    try:
        from tutor.behaviour.behaviour_state_store import persist_behaviour_state

        result = run_behaviour_model(learner_id)
        persistence_output = {}
        if isinstance(result, dict) and result.get("status") == "success":
            persistence_output = persist_behaviour_state(result)
            result["persistence_output"] = persistence_output
        return {
            "status": "success",
            "learner_id": learner_id,
            "data": result,
        }
    except Exception as e:
        return {
            "status": "error",
            "module": "behaviour",
            "error": str(e),
        }


# =========================
# Forgetting / decay
# =========================

def run_forgetting_decay(conn: sqlite3.Connection, learner_id: str) -> dict[str, Any]:
    try:
        from tutor.forgetting.service import compute_and_store_decay

        result = compute_and_store_decay(conn, learner_id)
        return {
            "status": "success",
            "learner_id": learner_id,
            "data": result if isinstance(result, dict) else {"value": result},
        }
    except Exception as e:
        return {
            "status": "error",
            "module": "forgetting",
            "error": str(e),
        }


def save_decay_state(conn: sqlite3.Connection, learner_id: str, forgetting_state: dict[str, Any]) -> None:
    data = forgetting_state.get("data", {})
    if not data:
        return

    try:
        conn.execute(
            """
            INSERT INTO decay_state
            (learner_id, decay_json, priority_json, queue_json, params_json, generated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                learner_id,
                json.dumps(data.get("decay", {})),
                json.dumps(data.get("review_priority", {})),
                json.dumps(data.get("review_queue", [])),
                json.dumps(data.get("params", {})),
                now_iso(),
            ),
        )
        conn.commit()
    except Exception:
        pass


# =========================
# Personalization
# =========================

def run_personalization(conn: sqlite3.Connection, learner_id: str) -> dict[str, Any]:
    try:
        result = get_policy_teaching_bias(conn, learner_id)
        return {
            "status": "success",
            "learner_id": learner_id,
            "data": result,
        }
    except Exception as e:
        return {
            "status": "error",
            "module": "long_term_personalization",
            "error": str(e),
        }


# =========================
# Policy
# =========================

def run_policy(
    conn: sqlite3.Connection,
    learner_id: str,
    knowledge_state: dict[str, Any],
    behaviour_state: dict[str, Any],
    forgetting_state: dict[str, Any],
    personalization: dict[str, Any],
) -> dict[str, Any]:
    try:
        from tutor.policy.run_policy_from_dependency import run_policy_once

        tutor_db = "external/core_data/tutor.db"
        concept_db_paths = [
            "external/core_data/python_learning.db",
            "external/core_data/html_web_basics.db",
            "external/core_data/data_structures.db",
            "external/core_data/database_sql.db",
            "external/core_data/git_version_control.db",
        ]

        result = run_policy_once(tutor_db, concept_db_paths, learner_id)

        def _nested_get(data: dict[str, Any] | None, *path: str) -> Any:
            current: Any = data or {}
            for key in path:
                if not isinstance(current, dict):
                    return None
                current = current.get(key)
            return current

        def _as_float(value: Any) -> float | None:
            try:
                if value is None:
                    return None
                return float(value)
            except (TypeError, ValueError):
                return None

        result = dict(result) if isinstance(result, dict) else {"value": result}

        review_queue = _nested_get(forgetting_state, "data", "review_queue") or []
        mastery = _as_float(_nested_get(knowledge_state, "data", "data", "predicted_mastery_last"))
        behavior_label = _nested_get(behaviour_state, "data", "behavior_label")
        behavior_score = _as_float(_nested_get(behaviour_state, "data", "behavior_score"))
        support_level = _nested_get(personalization, "data", "support_level")
        challenge_readiness = _nested_get(personalization, "data", "challenge_readiness")

        should_use_forgetting = bool(review_queue) and (
            (mastery is not None and mastery < 0.45)
            or (behavior_label in {"high_risk", "moderate_risk"})
            or (behavior_score is not None and behavior_score >= 0.4)
            or (support_level in {"high", "medium"} and challenge_readiness != "high")
        )

        if should_use_forgetting:
            review_concept = review_queue[0]
            result["next_concept_id"] = review_concept
            result["decision_type"] = "selected_from_forgetting_module"
            if not result.get("strategy"):
                result["strategy"] = "remedial"
            if not result.get("content_type"):
                result["content_type"] = "worked_example"
            result["difficulty"] = "easy"
        else:
            if not result.get("strategy") and mastery is not None:
                if mastery < 0.45:
                    result["strategy"] = "remedial"
                    result["difficulty"] = "easy"
                    result["content_type"] = "worked_example"
                elif mastery < 0.75:
                    result["strategy"] = "practice"
                    result["difficulty"] = "medium"
                    result["content_type"] = "guided_practice"
                else:
                    result["strategy"] = "advanced"
                    result["difficulty"] = "hard"
                    result["content_type"] = "challenge_problem"

            if not result.get("next_concept_id") and review_queue:
                result["next_concept_id"] = review_queue[0]
                result["decision_type"] = "selected_from_forgetting_fallback_missing_policy"

        return {
            "status": "success",
            "learner_id": learner_id,
            "data": result,
        }

    except Exception as e:
        return {
            "status": "error",
            "module": "policy",
            "error": str(e),
        }


# =========================
# Teaching strategy
# =========================

def run_teaching_strategy(
    conn: sqlite3.Connection,
    learner_id: str,
    policy_output: dict[str, Any],
    behaviour_state: dict[str, Any],
) -> dict[str, Any]:
    policy_data = policy_output.get("data", {})
    strategy = policy_data.get("strategy") or "remedial"

    result = {
        "final_strategy": strategy,
        "reason": "Derived from policy output",
    }

    try:
        conn.execute(
            """
            INSERT INTO teaching_strategy_log
            (learner_id, strategy, timestamp)
            VALUES (?, ?, ?)
            """,
            (learner_id, strategy, now_iso()),
        )
        conn.commit()
    except Exception:
        pass

    return {
        "status": "success",
        "learner_id": learner_id,
        "data": result,
    }


# =========================
# Teaching content
# =========================

def fetch_teaching_content_for_policy(
    learner_id: str,
    policy_output: dict[str, Any],
    strategy_output: dict[str, Any],
) -> dict[str, Any]:
    policy_data = policy_output.get("data", {})
    strategy_data = strategy_output.get("data", {})

    system_concept_id = policy_data.get("next_concept_id")
    difficulty = policy_data.get("difficulty")
    content_type = policy_data.get("content_type")
    strategy = strategy_data.get("final_strategy", policy_data.get("strategy"))

    print(f"[DEBUG] RAG PIPELINE concept_id={system_concept_id}")

    try:
        resource = get_learning_content(str(system_concept_id))
        print(f"[DEBUG] concept_resources used = {bool(resource)}")
    except Exception as e:
        resource = None
        print(f"[DEBUG] concept_resources error = {e}")

    try:
        concept_name = resource.get("topic") if resource else None
        domain = None  # optional, can improve later

        rag_resource = build_rag_concept_resource(
            query=concept_name or str(system_concept_id),
            domain=domain,
            concept_id=str(system_concept_id),
            top_k=8,
        )

        print(f"[DEBUG] new RAG chunks = {rag_resource.get('chunk_count', 0)}")

    except Exception as e:
        rag_resource = {
            "status": "error",
            "retrieved_chunks": [],
            "chunk_count": 0,
            "error": str(e),
        }
        print(f"[DEBUG] new RAG error = {e}")

    if resource:
        chunks = rag_resource.get("retrieved_chunks", [])

        if strategy == "remedial":
            top_chunks = [c for c in chunks if c.get("section") in ["definition", "examples"]][:5]
        elif strategy == "practice":
            top_chunks = [c for c in chunks if c.get("section") in ["examples", "key_points"]][:5]
        else:
            top_chunks = [c for c in chunks if c.get("section") in ["key_points"]][:5]

        definition = clean_definition(
            rag_resource.get("definition") or resource.get("base_content") or ""
        )

        examples = clean_examples(
            rag_resource.get("examples") or resource.get("examples") or ""
        )

        key_points = clean_key_points(
            rag_resource.get("key_points") or resource.get("key_points") or []
        )

        misconceptions = rag_resource.get("misconceptions") or resource.get("misconceptions") or []

        practice_ideas = rag_resource.get("practice_ideas") or []

        seen = set()
        clean_chunks = []

        for c in top_chunks:
            text = c.get("content", "").strip()
            if text and text not in seen:
                clean_chunks.append(text)
                seen.add(text)

        if definition in seen:
            combined_content_parts = clean_chunks
        else:
            combined_content_parts = [definition] + clean_chunks[:3]

        combined_content = "\n\n".join([p for p in combined_content_parts if p])

        return {
            "status": "success",
            "learner_id": learner_id,
            "data": {
                "source": "rag_augmented",
                "concept_id": resource.get("concept_id"),
                "topic": resource.get("topic"),
                "strategy": strategy,
                "content_type": content_type,
                "difficulty": difficulty,
                "base_content": resource.get("base_content"),
                "examples_base": resource.get("examples"),
                "key_points_base": resource.get("key_points"),
                "misconceptions_base": resource.get("misconceptions"),
                "real_world_use": clean_real_world_use(resource.get("real_world_use")),
                "definition": definition,
                "examples": examples,
                "key_points": key_points,
                "misconceptions": misconceptions,
                "practice_ideas": practice_ideas,
                "reference_text": rag_resource.get("content", ""),
                "retrieved_chunks": top_chunks,
                "chunk_count": rag_resource.get("chunk_count", 0),
                "content": combined_content,
            }
        }

    return {
        "status": "error",
        "module": "teaching_content",
        "error": "concept_resources not found",
        "concept_id": system_concept_id,
    }


# =========================
# Evaluation helpers
# =========================

def derive_learning_signal_from_bundle(evaluation_output: dict[str, Any]) -> str:
    score = float(evaluation_output.get("overall_score", 0.0))
    if score >= 0.85:
        return "mastered"
    elif score >= 0.6:
        return "partial"
    else:
        return "weak"


def build_evaluation_evidence(evaluation_output: dict[str, Any], learning_signal: str) -> dict[str, Any]:
    results = evaluation_output.get("results", [])
    weak_item_count = len([r for r in results if float(r.get("score", 0.0)) < 0.75])

    return {
        "overall_score": evaluation_output.get("overall_score", 0.0),
        "verdict": evaluation_output.get("verdict", ""),
        "feedback_summary": evaluation_output.get("feedback_summary", ""),
        "learning_signal": learning_signal,
        "weak_item_count": weak_item_count,
        "item_count": len(results),
    }


def _assessment_plan_from_strategy(
    evidence_aware_teaching_strategy_output: dict[str, Any] | None,
    fallback_difficulty: str,
    fallback_types: list[str],
) -> tuple[str, list[str]]:
    if not isinstance(evidence_aware_teaching_strategy_output, dict):
        return fallback_difficulty, fallback_types

    assessment_types = evidence_aware_teaching_strategy_output.get("assessment_types")
    assessment_difficulty = evidence_aware_teaching_strategy_output.get("assessment_difficulty")

    if not isinstance(assessment_types, list) or not assessment_types:
        assessment_types = fallback_types

    assessment_types = [str(item) for item in assessment_types if str(item).strip()]
    if not assessment_types:
        assessment_types = fallback_types

    if not assessment_difficulty:
        assessment_difficulty = fallback_difficulty

    return str(assessment_difficulty), assessment_types


def _normalize_assessment_question_types(assessment_output: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(assessment_output, dict):
        return assessment_output

    for question in assessment_output.get("questions", []):
        if not isinstance(question, dict):
            continue
        if not question.get("assessment_type") and question.get("question_type"):
            question["assessment_type"] = question.get("question_type")

    return assessment_output


def get_default_learner_answers(profile: str = "average") -> dict[str, str]:
    normalized = (profile or "average").strip().lower()

    if normalized == "strong":
        return {
            "mcq": "A variable stores a value and can be reused or updated during program execution.",
            "explanation": "A variable stores a value and can be used later in a program.",
            "output_prediction": "15",
            "debug": "Use the correct variable name x instead of x1.",
            "transfer": "Variables store names, prices, settings, and other values in programs.",
        }

    if normalized == "weak":
        return {
            "mcq": "Loop statement",
            "explanation": "I don't know",
            "output_prediction": "5",
            "debug": "",
            "transfer": "Not sure",
        }

    return {
        "mcq": "A variable stores a value.",
        "explanation": "A variable stores a value that can be used later.",
        "output_prediction": "15",
        "debug": "The variable name is inconsistent. Use x instead of x1.",
        "transfer": "Variables store names, prices, and values in programs.",
    }


def build_mock_answers_for_profile(learner_profile: str) -> dict[str, str]:
    normalized = (learner_profile or "").strip().lower()

    if normalized == "strong":
        return {
            "mcq": "A variable stores a value and can be reused or updated.",
            "output_prediction": "15",
            "debug": "The variable name is inconsistent. Use x consistently instead of x1.",
            "explanation": "A variable stores a value using a name and can be reused or updated later.",
            "transfer": "Variables can store configuration values, counters, names, prices, and API response values.",
        }

    if normalized == "average":
        return {
            "mcq": "A variable stores something.",
            "output_prediction": "15",
            "debug": "There is a mistake.",
            "explanation": "Variables hold data.",
            "transfer": "Variables are used in coding.",
        }

    if normalized == "weak":
        return {
            "mcq": "Variables are only for advanced programs.",
            "output_prediction": "10",
            "debug": "No mistake.",
            "explanation": "Variable means changing thing.",
            "transfer": "",
        }

    return {}


def clean_key_points(raw_key_points: Any) -> list[str]:
    if raw_key_points is None:
        return []

    if isinstance(raw_key_points, str):
        candidates = [part.strip() for part in raw_key_points.split("\n") if part.strip()]
    elif isinstance(raw_key_points, list):
        candidates = [str(kp).strip() for kp in raw_key_points if str(kp).strip()]
    else:
        candidates = [str(raw_key_points).strip()]

    blocked_terms = [
        "worked example",
        "this example",
        "learner",
        "guidance",
        "support",
        "assessment",
        "quiz",
        "teacher note",
        "instruction",
        "metadata",
    ]

    cleaned = []
    seen = set()
    for kp in candidates:
        kp = re.sub(r"^[-*•]+\s*", "", kp).strip()
        kp = re.sub(r"\s+", " ", kp)
        lower_kp = kp.lower()
        if any(term in lower_kp for term in blocked_terms):
            continue
        if len(kp.split()) < 3:
            continue
        if any(token in lower_kp for token in ["print(", " = ", "==", "output:", "trace"]):
            continue
        if any(token in lower_kp for token in ["constant", "identity", "advanced", "debug"]):
            continue
        if lower_kp in seen:
            continue
        cleaned.append(kp)
        seen.add(lower_kp)

    return cleaned


def clean_definition(raw_definition: Any) -> str:
    if raw_definition is None:
        return ""

    text = str(raw_definition).replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return ""

    sentences = []
    seen = set()
    for part in re.split(r"\n\s*\n|(?<=[.!?])\s+", text):
        cleaned = re.sub(r"\s+", " ", part).strip(" -*•")
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        sentences.append(cleaned)
        if len(sentences) == 2:
            break
    return " ".join(sentences)


def clean_examples(raw_examples: Any) -> list[str]:
    if raw_examples is None:
        return []

    if isinstance(raw_examples, list):
        candidates = [str(example).strip() for example in raw_examples if str(example).strip()]
    elif isinstance(raw_examples, str):
        text = raw_examples.strip()
        candidates = [part.strip() for part in text.split("|") if part.strip()]
        if not candidates and text:
            split_examples = re.split(r"(?=Example\s+\d+\s*[—:\-])", text, flags=re.IGNORECASE)
            candidates = [part.strip() for part in split_examples if part.strip()] or [text]
    else:
        candidates = [str(raw_examples).strip()]

    cleaned = []
    seen = set()
    for example in candidates:
        example = example.replace("\r\n", "\n").replace("\r", "\n").strip()
        if not example:
            continue
        example = re.sub(r"^Example\s+\d+\s*[—:\-]\s*", "", example, flags=re.IGNORECASE)
        if "```" in example:
            example = example.replace("```python", "").replace("```", "").strip()
        if any(term in example.lower() for term in ["teacher note", "worked example explanation", "hint:"]):
            continue
        if "\n" not in example and "=" in example and " print(" in example:
            example = example.replace(" print(", "\nprint(")
        normalized = re.sub(r"\s+", " ", example).lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(example)

    code_first = [
        example for example in cleaned
        if any(token in example for token in ["print(", "=", "if ", "for ", "while ", "def "])
    ]
    return code_first or cleaned


def clean_real_world_use(raw_real_world_use: Any) -> str:
    if raw_real_world_use is None:
        return ""

    text = str(raw_real_world_use).replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return ""

    if "\n" in text:
        points = []
        for line in text.splitlines():
            cleaned = re.sub(r"^[-*•]+\s*", "", line).strip()
            if cleaned:
                points.append(cleaned)
            if len(points) == 3:
                break
        if points:
            return "; ".join(points)

    return re.sub(r"\s+", " ", text)


def convert_assessment_for_evaluator(assessment_bundle: dict[str, Any]) -> dict[str, Any]:
    mapping = {
        "mcq": "mcq",
        "short_explanation": "explanation",
        "output_prediction": "output_prediction",
        "debug": "debug",
        "transfer": "transfer",
    }

    converted_questions = []
    for q in assessment_bundle.get("questions", []):
        question_type = q.get("question_type", "")
        converted_questions.append({
            "assessment_type": mapping.get(question_type, question_type),
            "question": q.get("prompt"),
            "prompt": q.get("prompt"),
            "expected_answer": q.get("expected_answer"),
            "options": q.get("options"),
            "correct_option_index": q.get("correct_option_index"),
            "metadata": q.get("metadata", {}),
        })

    converted_bundle = {
        "status": assessment_bundle.get("status", "success"),
        "concept_id": assessment_bundle.get("concept_id", ""),
        "concept_name": assessment_bundle.get("concept_name", ""),
        "difficulty": assessment_bundle.get("difficulty", ""),
        "questions": converted_questions,
    }
    converted_bundle["assessment_items"] = converted_questions
    return converted_bundle


# =========================
# XAI
# =========================

def generate_xai(
    conn: sqlite3.Connection,
    learner_id: str,
    quiz_result: dict[str, Any],
    knowledge_state: dict[str, Any],
    behaviour_state: dict[str, Any],
    forgetting_state: dict[str, Any],
    personalization: dict[str, Any],
    policy_output: dict[str, Any],
    evaluation_output: dict[str, Any] | None = None,
    view_performance_output: dict[str, Any] | None = None,
    adaptive_path_output: dict[str, Any] | None = None,
    adaptive_policy_bridge_output: dict[str, Any] | None = None,
    feature_contribution_output: dict[str, Any] | None = None,
) -> dict[str, Any]:

    evaluation_output = evaluation_output or {}
    view_performance_output = view_performance_output or {}
    adaptive_path_output = adaptive_path_output or {}
    adaptive_policy_bridge_output = adaptive_policy_bridge_output or {}
    feature_contribution_output = feature_contribution_output or {}

    policy_data = policy_output.get("data", {})
    next_concept = policy_data.get("next_concept_id")
    difficulty = policy_data.get("difficulty")
    strategy = policy_data.get("strategy")
    content_type = policy_data.get("content_type")
    decision_type = policy_data.get("decision_type")

    mastery = (
        knowledge_state
        .get("data", {})
        .get("data", {})
        .get("predicted_mastery_last")
    )

    behaviour_data = behaviour_state.get("data", {})
    if isinstance(behaviour_data.get("data"), dict):
        behaviour_data = behaviour_data.get("data", {})

    behavior_label = behaviour_data.get("behavior_label", "")
    behavior_score = behaviour_data.get("behavior_score", None)

    review_queue = (
        forgetting_state
        .get("data", {})
        .get("review_queue", [])
    )

    evaluation_score = evaluation_output.get("overall_score")
    evaluation_verdict = evaluation_output.get("verdict")
    feedback_summary = evaluation_output.get("feedback_summary")

    weak_assessment_types = []
    for item in evaluation_output.get("results", []):
        try:
            if float(item.get("score", 0.0)) < 0.75:
                weak_assessment_types.append(item.get("assessment_type"))
        except Exception:
            pass

    view_reward = None
    teaching_view = None
    try:
        logged_view = view_performance_output.get("logged", {})
        view_reward = logged_view.get("reward")
        teaching_view = logged_view.get("teaching_view")
    except Exception:
        pass

    adaptive_selected = adaptive_path_output.get("selected_next_concept")
    adaptive_strategy = adaptive_path_output.get("recommended_strategy")
    adaptive_difficulty = adaptive_path_output.get("recommended_difficulty")
    adaptive_reason = adaptive_path_output.get("selected_reason")

    bridge_agreement = adaptive_policy_bridge_output.get("agreement")
    bridge_override_allowed = adaptive_policy_bridge_output.get("override_allowed")
    bridge_recommendation = adaptive_policy_bridge_output.get("final_recommendation", {})
    bridge_reason = adaptive_policy_bridge_output.get("reason", "")

    explanation_parts = []

    explanation_parts.append(
        f"The final policy selected concept {next_concept} with {difficulty} difficulty "
        f"and {strategy} strategy using {content_type} content."
    )

    if decision_type:
        explanation_parts.append(
            f"The decision type was {decision_type}."
        )

    if mastery is not None:
        explanation_parts.append(
            f"The learner's latest mastery estimate was {round(float(mastery), 4)}."
        )

    if behavior_label or behavior_score is not None:
        explanation_parts.append(
            f"Behaviour evidence showed label={behavior_label} and score={behavior_score}."
        )

    if review_queue:
        explanation_parts.append(
            f"Forgetting module suggested review queue: {review_queue}."
        )

    if evaluation_score is not None:
        explanation_parts.append(
            f"Evaluation score was {evaluation_score} with verdict '{evaluation_verdict}'."
        )

    if weak_assessment_types:
        explanation_parts.append(
            f"Weak assessment areas were: {weak_assessment_types}."
        )

    if feedback_summary:
        explanation_parts.append(
            f"Evaluator feedback summary: {feedback_summary}."
        )

    if teaching_view or view_reward is not None:
        explanation_parts.append(
            f"The selected teaching view was {teaching_view}, with view reward {view_reward}."
        )

    if adaptive_selected:
        explanation_parts.append(
            f"AdaptivePathSelector suggested concept {adaptive_selected} "
            f"with {adaptive_difficulty} difficulty and {adaptive_strategy} strategy."
        )

    if adaptive_reason:
        explanation_parts.append(
            f"Adaptive path reason: {adaptive_reason}"
        )

    if bridge_recommendation:
        explanation_parts.append(
            f"AdaptivePolicyBridge agreement={bridge_agreement}, "
            f"override_allowed={bridge_override_allowed}. "
            f"Bridge recommendation source: {bridge_recommendation.get('source')}."
        )

    if bridge_reason:
        explanation_parts.append(
            f"Bridge reason: {bridge_reason}"
        )


    if feature_contribution_output.get("status") == "success":
        pressure_label = feature_contribution_output.get("decision_pressure_label")
        total_pressure = feature_contribution_output.get("total_decision_pressure")
        top_factors = feature_contribution_output.get("top_factors", [])

        factor_names = [
            factor.get("feature")
            for factor in top_factors
            if isinstance(factor, dict)
        ]

        explanation_parts.append(
            f"Feature contribution XAI classified decision pressure as "
            f"{pressure_label} with total pressure {total_pressure}."
        )

        if factor_names:
            explanation_parts.append(
                f"Top contributing factors were: {factor_names}."
            )

    explanation = " ".join(explanation_parts)

    evidence_json = {
        "policy": {
            "next_concept_id": next_concept,
            "difficulty": difficulty,
            "strategy": strategy,
            "content_type": content_type,
            "decision_type": decision_type,
        },
        "learner_state": {
            "mastery": mastery,
            "behavior_label": behavior_label,
            "behavior_score": behavior_score,
            "review_queue": review_queue,
        },
        "evaluation": {
            "score": evaluation_score,
            "verdict": evaluation_verdict,
            "weak_assessment_types": weak_assessment_types,
            "feedback_summary": feedback_summary,
        },
        "view_performance": {
            "teaching_view": teaching_view,
            "view_reward": view_reward,
        },
        "adaptive_path": {
            "selected_next_concept": adaptive_selected,
            "recommended_difficulty": adaptive_difficulty,
            "recommended_strategy": adaptive_strategy,
            "reason": adaptive_reason,
        },
        "adaptive_policy_bridge": {
            "agreement": bridge_agreement,
            "override_allowed": bridge_override_allowed,
            "recommendation": bridge_recommendation,
            "reason": bridge_reason,
        },
        "feature_contributions": {
            "decision_pressure_label": feature_contribution_output.get("decision_pressure_label"),
            "total_decision_pressure": feature_contribution_output.get("total_decision_pressure"),
            "top_factors": feature_contribution_output.get("top_factors"),
            "ranked_contributions": feature_contribution_output.get("ranked_contributions"),
        },
    }

    try:
        conn.execute(
            """
            INSERT INTO xai_log
            (learner_id, concept_id, decision_type, explanation_text, evidence_json, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                learner_id,
                str(next_concept),
                decision_type,
                explanation,
                json.dumps(evidence_json),
                now_iso(),
            ),
        )
        conn.commit()
    except Exception as e:
        print("XAI LOG ERROR:", e)

    return {
        "status": "success",
        "learner_id": learner_id,
        "data": {
            "reason": explanation,
            "evidence": evidence_json,
        },
    }

# =========================
# Logs
# =========================

def log_learning_path(
    conn: sqlite3.Connection,
    learner_id: str,
    policy_output: dict[str, Any],
) -> None:
    policy_data = policy_output.get("data", {})
    next_concept_id = policy_data.get("next_concept_id")
    decision_type = policy_data.get("decision_type")

    try:
        conn.execute(
            """
            INSERT INTO learning_path_log
            (learner_id, from_concept_id, to_concept_id, action, reason_json, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                learner_id,
                None,
                str(next_concept_id),
                "recommended",
                json.dumps({"decision_type": decision_type}),
                now_iso(),
            ),
        )
        conn.commit()
    except Exception as e:
        print("LEARNING PATH LOG ERROR:", e)


def log_fusion_decision(
    conn: sqlite3.Connection,
    learner_id: str,
    concept_id: str,
    multi_evidence_output: dict[str, Any],
) -> None:
    try:
        evidence = multi_evidence_output.get("evidence_summary", {})

        conn.execute(
            """
            INSERT INTO fusion_decision_log (
                learner_id,
                concept_id,
                mastery_score,
                behavior_label,
                behavior_score,
                review_due,
                evaluation_score,
                evaluation_quality,
                learning_signal,
                final_action,
                recommended_strategy,
                recommended_difficulty,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                learner_id,
                str(concept_id),
                evidence.get("mastery_score"),
                evidence.get("behavior_label"),
                evidence.get("behavior_score"),
                1 if evidence.get("review_due") else 0,
                evidence.get("evaluation_score"),
                evidence.get("evaluation_quality"),
                evidence.get("learning_signal"),
                multi_evidence_output.get("final_action"),
                multi_evidence_output.get("recommended_strategy"),
                multi_evidence_output.get("recommended_difficulty"),
                now_iso(),
            ),
        )
        conn.commit()
    except Exception as e:
        print("FUSION DECISION LOG ERROR:", e)


def log_policy_decision(
    conn: sqlite3.Connection,
    learner_id: str,
    current_concept_id: str,
    next_concept_id: str,
    knowledge_state: dict[str, Any],
    behaviour_state: dict[str, Any],
    forgetting_state: dict[str, Any],
    evaluation_output: dict[str, Any],
    learning_signal: str,
    multi_evidence_output: dict[str, Any],
) -> None:
    try:
        mastery = knowledge_state.get("data", {}).get("data", {}).get("predicted_mastery_last", 0.0)
        behaviour_data = behaviour_state.get("data", {})
        review_due = bool(forgetting_state.get("data", {}).get("review_queue", []))

        conn.execute(
            """
            INSERT INTO policy_decision_log (
                learner_id,
                current_concept_id,
                next_concept_id,
                mastery_score,
                behavior_label,
                behavior_score,
                review_due,
                evaluation_score,
                learning_signal,
                final_action,
                recommended_strategy,
                recommended_difficulty,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                learner_id,
                str(current_concept_id),
                str(next_concept_id),
                float(mastery or 0.0),
                behaviour_data.get("behavior_label", ""),
                float(behaviour_data.get("behavior_score", 0.0) or 0.0),
                1 if review_due else 0,
                float(evaluation_output.get("overall_score", 0.0) or 0.0),
                learning_signal,
                multi_evidence_output.get("final_action", ""),
                multi_evidence_output.get("recommended_strategy", ""),
                multi_evidence_output.get("recommended_difficulty", ""),
                now_iso(),
            ),
        )
        conn.commit()
    except Exception as e:
        print("POLICY DECISION LOG ERROR:", e)


def log_evaluation(
    conn: sqlite3.Connection,
    learner_id: str,
    concept_id: str,
    evaluation_output: dict[str, Any],
    learning_signal: str,
) -> None:
    try:
        results = evaluation_output.get("results", [])

        def get_score(item_type: str):
            for r in results:
                if r.get("assessment_type") == item_type:
                    return r.get("score", 0.0)
            return 0.0

        conn.execute(
            """
            INSERT INTO evaluation_log (
                learner_id,
                concept_id,
                overall_score,
                verdict,
                feedback_summary,
                mcq_score,
                explanation_score,
                output_score,
                transfer_score,
                learning_signal,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                learner_id,
                str(concept_id),
                evaluation_output.get("overall_score", 0.0),
                evaluation_output.get("verdict", ""),
                evaluation_output.get("feedback_summary", ""),
                get_score("mcq"),
                get_score("explanation"),
                get_score("output_prediction"),
                get_score("transfer"),
                learning_signal,
                now_iso(),
            ),
        )
        conn.commit()
    except Exception as e:
        print("EVALUATION LOG ERROR:", e)


# =========================
# Helpers
# =========================

def get_next_concept_from_db(conn: sqlite3.Connection, current_concept_id: str) -> str | None:
    try:
        rows = conn.execute(
            """
            SELECT system_concept_id
            FROM concept_id_map
            ORDER BY CAST(system_concept_id AS INTEGER)
            """
        ).fetchall()

        ids = [str(r[0]) for r in rows if r[0] is not None]

        if current_concept_id in ids:
            idx = ids.index(current_concept_id)
            if idx + 1 < len(ids):
                return ids[idx + 1]

        return None
    except Exception:
        return None


def resolve_demo_concept(
    policy_output: dict[str, Any] | None,
    fallback_to_variables: bool = True,
) -> dict[str, Any]:
    policy_data = policy_output.get("data", {}) if isinstance(policy_output, dict) else {}
    concept_id = policy_data.get("next_concept_id")

    if concept_id in [None, "", "None", "null"]:
        if fallback_to_variables:
            return {
                "status": "fallback_used",
                "concept_id": "1",
                "concept_name": "Variables",
                "domain": "Python",
                "fallback_used": True,
                "reason": "policy_output had no usable next_concept_id",
            }

    if str(concept_id) == "1":
        return {
            "status": "success",
            "concept_id": "1",
            "concept_name": "Variables",
            "domain": "Python",
            "fallback_used": False,
            "reason": "resolved from policy_output",
        }

    return {
        "status": "partial",
        "concept_id": str(concept_id),
        "concept_name": "Concept " + str(concept_id),
        "domain": "",
        "fallback_used": False,
        "reason": "basic fallback resolver used",
    }


def apply_resolved_concept_to_packet(
    packet: dict[str, Any] | None,
    resolved_concept: dict[str, Any],
) -> dict[str, Any] | None:
    if not isinstance(packet, dict):
        return packet

    replacements = {
        "concept_id": resolved_concept.get("concept_id"),
        "concept_name": resolved_concept.get("concept_name"),
        "domain": resolved_concept.get("domain"),
    }

    for key, value in replacements.items():
        current = packet.get(key)
        if current in [None, "", "None", "null", "Unknown Concept"]:
            packet[key] = value

    for item in packet.get("items", []) or []:
        if isinstance(item, dict):
            for key, value in replacements.items():
                current = item.get(key)
                if current in [None, "", "None", "null", "Unknown Concept"]:
                    item[key] = value

    for question in packet.get("questions", []) or []:
        if isinstance(question, dict):
            for key, value in replacements.items():
                current = question.get(key)
                if current in [None, "", "None", "null", "Unknown Concept"]:
                    question[key] = value

    return packet


def build_cognitutor_lm_output(
    connector_result: dict[str, Any] | Any,
    fallback_concept_used: bool,
    teaching_view: str | None = None,
    difficulty: str | None = None,
) -> dict[str, Any]:
    if not isinstance(connector_result, dict):
        return {
            "status": "error",
            "source": "main_project_cognitutor_lm_connector",
            "mode": "optional_connector_demo",
            "fallback_concept_used": fallback_concept_used,
            "error": "Connector result was not a dictionary.",
            "note": "Main pipeline continued without CogniTutorLM.",
            "details": {
                "response_type": type(connector_result).__name__,
                "response": connector_result,
            },
        }

    if connector_result.get("status") != "success":
        return {
            "status": "error",
            "source": "main_project_cognitutor_lm_connector",
            "mode": "optional_connector_demo",
            "fallback_concept_used": fallback_concept_used,
            "error": connector_result.get("error") or "CogniTutorLM connector returned an error.",
            "details": connector_result.get("details", {}),
            "note": "Main pipeline continued without CogniTutorLM.",
        }

    data = connector_result.get("data", {}) or {}
    teaching = data.get("teaching", {}) or {}
    assessment = data.get("assessment", {}) or {}
    questions = assessment.get("questions", []) or []

    return {
        "status": "success",
        "source": "main_project_cognitutor_lm_connector",
        "mode": "optional_connector_demo",
        "fallback_concept_used": fallback_concept_used,
        "adaptive_session": data,
        "connector_method": connector_result.get("method"),
        "teaching_view_used": teaching_view,
        "difficulty_used": difficulty,
        "concept_id": data.get("concept_id"),
        "concept_name": data.get("concept_name"),
        "domain": data.get("domain"),
        "selected_view": data.get("selected_view"),
        "question_types": data.get("question_types", []),
        "teaching_source": teaching.get("source"),
        "teaching_preview": str(teaching.get("teaching", "")).strip()[:300],
        "assessment_count": len(questions),
        "frontend_contract": data.get("frontend_contract", {}),
    }


def build_optional_cognitutor_lm_output(
    learner_id: str,
    concept_id: str | None,
    concept_name: str | None,
    domain: str | None = None,
    teaching_view: str | None = None,
    difficulty: str | None = None,
) -> dict[str, Any]:
    """
    Optional comparison-mode CogniTutorLM call.

    This must never control or block the main integrated tutor pipeline.
    """
    fallback_concept_used = False
    requested_concept_id = str(concept_id or "").strip()
    requested_concept_name = str(concept_name or "").strip()
    requested_domain = str(domain or "").strip()

    if (
        not requested_concept_id
        or requested_concept_id.lower() in {"none", "null"}
        or not requested_concept_name
        or requested_concept_name.lower() == "unknown concept"
    ):
        external_concept_id = "P1"
        requested_concept_name = "Variables"
        requested_domain = "Python"
        fallback_concept_used = True
    else:
        external_concept_id = requested_concept_id

    if external_concept_id and not re.match(r"^[A-Za-z]+\d+$", str(external_concept_id)):
        external_concept_id = "P1"
        requested_concept_name = "Variables"
        requested_domain = "Python"
        fallback_concept_used = True

    if not requested_domain and requested_concept_name.lower() == "variables":
        requested_domain = "Python"

    try:
        from tutor.generation.cognitutor_lm_frontend_bridge import build_frontend_cognitutor_packet

        product_packet = build_frontend_cognitutor_packet(
            learner_id=learner_id,
            domain=requested_domain or "Python",
            concept=requested_concept_name or "Variables",
            difficulty=difficulty or "easy",
            teaching_view=teaching_view or "definition_view",
        )
        if product_packet.get("status") == "success":
            return {
                "status": "success",
                "source": "main_project_cognitutor_lm_connector",
                "mode": "optional_product_frontend_bridge",
                "raw_cognitutor_attempted": False,
                "raw_valid": False,
                "guarded_product_generator_used": True,
                "fallback_used": fallback_concept_used,
                "final_learner_facing_source": "guarded_product_generator",
                "validation_reason": "Raw CogniTutorLM connector was not used because guarded product generator succeeded.",
                "fallback_concept_used": fallback_concept_used,
                "cognitutor_lm_product_output": product_packet,
                "teaching_title": (product_packet.get("teaching_content") or {}).get("title"),
                "assessment_count": len(product_packet.get("assessment_bank") or []),
                "assessment_types_available": product_packet.get("assessment_types_available") or [],
                "product_assessment_type_count": len(product_packet.get("assessment_types_available") or []),
                "flashcard_count": len(product_packet.get("flashcards") or []),
                "flashcard_variants_available": product_packet.get("flashcard_variants_available") or [],
                "product_flashcard_variant_count": len(product_packet.get("flashcard_variants_available") or []),
                "mindmap_variants_available": product_packet.get("mindmap_variants_available") or [],
                "product_mindmap_variant_count": len(product_packet.get("mindmap_variants_available") or []),
                "voice_variants_available": product_packet.get("voice_variants_available") or [],
                "product_voice_variant_count": len(product_packet.get("voice_variants_available") or []),
                "product_frontend_ready": product_packet.get("frontend_ready") is True,
                "audio_overview_status": (product_packet.get("audio_overview") or {}).get("status"),
                "raw_generation_status": "WARN",
                "guarded_generation_status": "PASS",
            }
    except Exception:
        pass

    try:
        from tutor.generation.cognitutor_lm_connector import generate_cognitutor_adaptive_session

        connector_result = generate_cognitutor_adaptive_session(
            learner_id=learner_id,
            concept_id=external_concept_id,
            concept_name=requested_concept_name,
            domain=requested_domain or None,
        )

        raw_output = build_cognitutor_lm_output(
            connector_result=connector_result,
            fallback_concept_used=fallback_concept_used,
            teaching_view=teaching_view,
            difficulty=difficulty,
        )
        raw_output.update(
            {
                "raw_cognitutor_attempted": True,
                "raw_valid": raw_output.get("status") == "success",
                "guarded_product_generator_used": False,
                "fallback_used": raw_output.get("status") != "success" or fallback_concept_used,
                "final_learner_facing_source": "raw_cognitutor_lm" if raw_output.get("status") == "success" else "fallback_generation",
                "validation_reason": None if raw_output.get("status") == "success" else raw_output.get("error"),
            }
        )
        return raw_output

    except Exception as e:
        return {
            "status": "error",
            "source": "main_project_cognitutor_lm_connector",
            "mode": "optional_connector_demo",
            "raw_cognitutor_attempted": True,
            "raw_valid": False,
            "guarded_product_generator_used": False,
            "fallback_used": True,
            "final_learner_facing_source": "fallback_generation",
            "validation_reason": str(e),
            "fallback_concept_used": fallback_concept_used,
            "error": str(e),
            "details": {
                "exception_type": type(e).__name__,
                "exception_message": str(e),
            },
            "note": "Main pipeline continued without CogniTutorLM.",
        }


# =========================
# Main pipeline
# =========================

def run_integrated_tutor_once(
            learner_id: str,
            learner_answers: dict[str, str] | None = None,
            learner_profile: str | None = None,
            db_path: str | Path = DB_PATH,
            reward_dry_run: bool = False,
    ) -> dict[str, Any]:
    conn = get_connection(db_path)

    tutor_agent = TutorAgent()
    assessment_agent = AssessmentAgent()
    evaluator_agent = EvaluatorAgent()
    decision_agent = DecisionAgent(conn=conn)

    try:
        quiz_result = run_quiz_step(conn, learner_id)
        knowledge_state = run_knowledge_state(conn, learner_id)
        behaviour_state = run_behaviour_state(conn, learner_id)
        forgetting_state = run_forgetting_decay(conn, learner_id)
        save_decay_state(conn, learner_id, forgetting_state)
        personalization = run_personalization(conn, learner_id)

        # =====================================================
        # Old Concept Dependency Module
        # Prerequisite safety gate: unlocked / blocked concepts
        # =====================================================
        try:
            latest_quiz = quiz_result.get("latest_quiz_result", {})
            current_concept_id = latest_quiz.get("concept_id")

            dependency_output = run_dependency_module_final(
                tutor_db=str(DB_PATH),
                concept_db_paths=CONCEPT_DB_PATHS,
                learner_id=str(learner_id),
                current_concept_id=str(current_concept_id) if current_concept_id else None,
            )
        except Exception as e:
            dependency_output = {
                "status": "error",
                "module": "run_dependency_module_final",
                "reason": str(e),
                "unlocked_concepts": [],
                "blocked_concepts": [],
                "recommended_next_concept": None,
            }


        current_policy_output = run_policy(
            conn=conn,
            learner_id=learner_id,
            knowledge_state=knowledge_state,
            behaviour_state=behaviour_state,
            forgetting_state=forgetting_state,
            personalization=personalization,
        )

        current_strategy_output = run_teaching_strategy(
            conn=conn,
            learner_id=learner_id,
            policy_output=current_policy_output,
            behaviour_state=behaviour_state,
        )

        current_policy_data = current_policy_output.get("data", {})
        concept_resolution_output = resolve_demo_concept(current_policy_output)
        concept_id = str(concept_resolution_output.get("concept_id", "1"))
        teaching_data = get_learning_content(concept_id) or {}

        concept_examples = clean_examples(teaching_data.get("examples"))
        if not concept_examples:
            concept_examples = clean_examples(teaching_data.get("examples_base", ""))

        concept_key_points = clean_key_points(teaching_data.get("key_points"))
        if not concept_key_points:
            concept_key_points = clean_key_points(teaching_data.get("key_points_base"))

        concept_resource = {
            "concept_id": concept_id,
            "concept_name": (
                teaching_data.get("topic", "")
                or concept_resolution_output.get("concept_name")
                or "Variables"
            ),
            "domain": concept_resolution_output.get("domain") or teaching_data.get("domain", ""),
            "definition": clean_definition(teaching_data.get("definition", "") or teaching_data.get("base_content", "")),
            "examples": concept_examples,
            "key_points": concept_key_points,
            "misconceptions": teaching_data.get("misconceptions", "") or teaching_data.get("misconceptions_base", ""),
            "real_world_use": clean_real_world_use(teaching_data.get("real_world_use", "")),
            "syntax": teaching_data.get("syntax", ""),
        }

        baseline_assessment_agent_output = assessment_agent.run(
            concept_resource=concept_resource,
            learner_id=learner_id,
            difficulty=current_policy_output.get("data", {}).get("difficulty", "easy"),
            requested_types=["mcq", "output_prediction", "debug", "short_explanation", "transfer"],
        )

        baseline_assessment_output = baseline_assessment_agent_output["data"]

        if learner_answers is not None:
            final_learner_answers = learner_answers
        elif learner_profile:
            final_learner_answers = build_mock_answers_for_profile(learner_profile)
        else:
            final_learner_answers = get_default_learner_answers()

        baseline_evaluator_agent_output = evaluator_agent.run(
            assessment_bundle=baseline_assessment_output,
            learner_answers=final_learner_answers,
        )

        baseline_evaluation_output = baseline_evaluator_agent_output["evaluation"]
        apply_resolved_concept_to_packet(baseline_evaluation_output, concept_resolution_output)
        baseline_learning_signal = baseline_evaluator_agent_output["learning_signal"]

        view_tracker = ViewPerformanceTracker()

        log_evaluation(
            conn=conn,
            learner_id=learner_id,
            concept_id=str(current_policy_output.get("data", {}).get("next_concept_id")),
            evaluation_output=baseline_evaluation_output,
            learning_signal=baseline_learning_signal,
        )

        decision_agent_output = decision_agent.run(
            current_policy_output=current_policy_output,
            knowledge_state=knowledge_state,
            behaviour_state=behaviour_state,
            forgetting_state=forgetting_state,
            evaluation_output=baseline_evaluation_output,
            learning_signal=baseline_learning_signal,
        )

        multi_evidence_output = decision_agent_output["multi_evidence_output"]
        final_policy_output = decision_agent_output["policy_output"]
        policy_output = final_policy_output
        adapted_decision = decision_agent_output["adapted_decision"]
        final_policy_data = policy_output.get("data", {}) if isinstance(policy_output, dict) else {}

        final_difficulty = final_policy_data.get("difficulty", "easy")
        final_strategy = final_policy_data.get("strategy", "practice")
        final_explanation_mode = final_policy_data.get("explanation_mode", "simple")

        tutor_agent_output = tutor_agent.run(
            concept_resource=concept_resource,
            learner_id=learner_id,
            difficulty=final_difficulty,
            context={
                "difficulty": final_difficulty,
                "strategy": final_strategy,
                "explanation_mode": final_explanation_mode,
                "decision_output": {
                    "policy_output": policy_output,
                },
                "mastery_score": multi_evidence_output.get("evidence_summary", {}).get("mastery_score", 0.5),
                "behavior_score": multi_evidence_output.get("evidence_summary", {}).get("behavior_score", 0.5),
                "evaluation_score": multi_evidence_output.get("evidence_summary", {}).get("evaluation_score", 0.0),
            },
        )
        current_teaching_content = tutor_agent_output.get("data", {})
        apply_resolved_concept_to_packet(current_teaching_content, concept_resolution_output)

        assessment_agent_output = assessment_agent.run(
            concept_resource=concept_resource,
            learner_id=learner_id,
            difficulty=final_difficulty,
            requested_types=["mcq", "output_prediction", "debug", "short_explanation", "transfer"],
        )

        assessment_output = assessment_agent_output["data"]
        assessment_output = _normalize_assessment_question_types(assessment_output)
        assessment_output = normalize_assessment_bundle_for_frontend(assessment_output)
        apply_resolved_concept_to_packet(assessment_output, concept_resolution_output)

        evaluator_agent_output = evaluator_agent.run(
            assessment_bundle=assessment_output,
            learner_answers=final_learner_answers,
        )

        converted_bundle = evaluator_agent_output["converted_assessment"]
        evaluation_output = evaluator_agent_output["evaluation"]
        apply_resolved_concept_to_packet(converted_bundle, concept_resolution_output)
        apply_resolved_concept_to_packet(evaluation_output, concept_resolution_output)

        rubric_evaluation_output = evaluator_agent_output.get(
            "rubric_evaluation_output",
            {
                "status": "not_available",
                "module": "RubricEvaluator",
            },
        )

        rubric_mode = evaluator_agent_output.get(
            "rubric_mode",
            "not_available",
        )

        debug_evaluation_output = evaluator_agent_output.get(
            "debug_evaluation_output",
            {
                "status": "not_available",
                "module": "DebugAnswerEvaluator",
            },
        )

        debug_evaluation_mode = evaluator_agent_output.get(
            "debug_evaluation_mode",
            "not_available",
        )

        output_prediction_evaluation_output = evaluator_agent_output.get(
            "output_prediction_evaluation_output",
            {
                "status": "not_available",
                "module": "OutputPredictionEvaluator",
            },
        )

        output_prediction_evaluation_mode = evaluator_agent_output.get(
            "output_prediction_evaluation_mode",
            "not_available",
        )

        evaluation_fusion_output = evaluator_agent_output.get(
            "evaluation_fusion_output",
            {
                "status": "not_available",
                "module": "EvaluationFusionEngine",
            },
        )

        evaluation_fusion_mode = evaluator_agent_output.get(
            "evaluation_fusion_mode",
            "not_available",
        )


        learning_signal = evaluator_agent_output["learning_signal"]
        evaluation_evidence = evaluator_agent_output["evaluation_evidence"]

        mistake_analysis_output = evaluator_agent_output.get(
            "mistake_analysis_output",
            {
                "status": "not_available",
                "module": "MistakeTypeClassifier",
            },
        )

        # === Reflection Agent ===
        reflection_agent = ReflectionAgent()

        reflection_output = reflection_agent.reflect(
            evaluation=evaluation_output,
            multi_evidence=multi_evidence_output,
            policy_output=policy_output,
            mistake_analysis_output=mistake_analysis_output,
        )

        learner_insight_layer = LearnerInsightLayer()

        learner_insight_output = learner_insight_layer.build(
            evaluation=evaluation_output,
            reflection_output=reflection_output,
            mistake_analysis_output=mistake_analysis_output,
        )


        rl_log_output = log_from_tutor_pipeline(
            conn=conn,
            learner_id=learner_id,
            concept_id=str(current_policy_output.get("data", {}).get("next_concept_id")),
            current_policy_output=current_policy_output,
            final_policy_output=final_policy_output,
            knowledge_state=knowledge_state,
            behaviour_state=behaviour_state,
            forgetting_state=forgetting_state,
            evaluation_output=evaluation_output,
            learning_signal=learning_signal,
            multi_evidence_output=multi_evidence_output,
        )

        # =====================================================
        # View Performance Tracking
        # =====================================================
        view_performance_output = None

        try:
            teaching_data = (
                tutor_agent_output.get("data", {})
                if isinstance(tutor_agent_output, dict)
                else {}
            )

            recommended_view = (
                teaching_data.get("recommended_view")
                or tutor_agent_output.get("recommended_view")
                if isinstance(tutor_agent_output, dict)
                else None
            )

            if not recommended_view:
                recommended_view = "definition_view"

            evaluation_score = 0.0

            if isinstance(evaluation_output, dict):
                evaluation_score = float(
                    evaluation_output.get("overall_score", 0.0)
                    or evaluation_output.get("score", 0.0)
                    or 0.0
                )

            mastery_before = None
            mastery_after = None

            try:
                mastery_before = float(
                    knowledge_state
                    .get("data", {})
                    .get("data", {})
                    .get("predicted_mastery_last", 0.5)
                )
            except Exception:
                mastery_before = 0.5

            mastery_after = mastery_before

            try:
                behavior_data = behaviour_state.get("data", {})
                if isinstance(behavior_data.get("data"), dict):
                    behavior_data = behavior_data.get("data", {})

                engagement_score = float(
                    behavior_data.get("behavior_score", 0.5)
                    or 0.5
                )
            except Exception:
                engagement_score = 0.5

            try:
                latest_quiz = quiz_result.get("latest_quiz_result", {})
                time_taken = latest_quiz.get("time_taken_sec", None)
                hint_usage = latest_quiz.get("hint_count", latest_quiz.get("hint_used", 0))
            except Exception:
                time_taken = None
                hint_usage = 0

            view_performance_output = view_tracker.log_view_result(
                learner_id=learner_id,
                concept_id=str(policy_output.get("data", {}).get("next_concept_id", "")),
                teaching_view=recommended_view,
                difficulty=str(policy_output.get("data", {}).get("difficulty", "medium")),
                assessment_score=evaluation_score,
                time_taken=time_taken,
                hint_usage=hint_usage,
                engagement_score=engagement_score,
                mastery_before=mastery_before,
                mastery_after=mastery_after,
                metadata={
                    "source": "integrated_pipeline",
                    "strategy": policy_output.get("data", {}).get("strategy"),
                    "content_type": policy_output.get("data", {}).get("content_type"),
                    "evaluation_verdict": evaluation_output.get("verdict")
                    if isinstance(evaluation_output, dict)
                    else None,
                },
            )

        except Exception as e:
            view_performance_output = {
                "status": "error",
                "module": "ViewPerformanceTracker",
                "reason": str(e),
            }


        # =====================================================
        # Adaptive Path Selector
        # Connects old dependency output + new multi-evidence scoring
        # =====================================================
        adaptive_path_output = None

        try:
            adaptive_path_selector = AdaptivePathSelector()

            mastery_used = {}

            try:
                mastery_used = (
                    dependency_output.get("mastery_used", {})
                    if isinstance(dependency_output, dict)
                    else {}
                )

                if not mastery_used:
                    written_state = (
                        knowledge_state
                        .get("data", {})
                        .get("data", {})
                        .get("written_state", {})
                    )

                    if isinstance(written_state, dict):
                        mastery_used = {
                            str(k): float(v)
                            for k, v in written_state.items()
                        }

                if not mastery_used:
                    predicted_mastery = (
                        knowledge_state
                        .get("data", {})
                        .get("data", {})
                        .get("predicted_mastery_last", 0.5)
                    )

                    current_policy_concept = str(
                        final_policy_output
                        .get("data", {})
                        .get("next_concept_id", "")
                    )

                    if current_policy_concept:
                        mastery_used = {
                            current_policy_concept: float(predicted_mastery)
                        }

            except Exception:
                mastery_used = {}

            review_priority = {}

            try:
                review_priority = (
                    forgetting_state
                    .get("data", {})
                    .get("review_priority", {})
                )
            except Exception:
                review_priority = {}

            behaviour_evidence = {}

            try:
                behaviour_evidence = behaviour_state.get("data", {})
                if isinstance(behaviour_evidence.get("data"), dict):
                    behaviour_evidence = behaviour_evidence.get("data", {})
            except Exception:
                behaviour_evidence = {}

            adaptive_path_output = adaptive_path_selector.select_next_path(
                dependency_output=dependency_output,
                mastery=mastery_used,
                forgetting_priority=review_priority,
                evaluation_evidence=evaluation_evidence,
                behaviour_evidence=behaviour_evidence,
                view_performance=view_performance_output,
                current_concept_id=str(final_policy_output.get("data", {}).get("next_concept_id", "")),
            )

        except Exception as e:
            adaptive_path_output = {
                "status": "error",
                "module": "AdaptivePathSelector",
                "reason": str(e),
            }

        adaptive_path_validation_output = {
            "valid": False,
            "selected_concept_id": None,
            "resolved_concept_id": str(final_policy_output.get("data", {}).get("next_concept_id", "")),
            "resolved_concept_name": concept_resolution_output.get("concept_name"),
            "resolved_domain": concept_resolution_output.get("domain"),
            "fallback_used": True,
            "reason": "Adaptive path validation was not run.",
        }
        frontend_path_output = {
            "status": "not_available",
            "module": "AdaptivePathFrontendOutput",
            "path_nodes": [],
        }

        try:
            concept_id_map = load_concept_id_map(DB_PATH)
            fallback_concept_id = str(final_policy_output.get("data", {}).get("next_concept_id", ""))
            adaptive_path_validation_output = validate_selected_concept_id(
                selected_concept_id=(
                    adaptive_path_output.get("selected_next_concept")
                    if isinstance(adaptive_path_output, dict)
                    else None
                ),
                concept_id_map=concept_id_map,
                fallback_concept_id=fallback_concept_id,
                current_domain=concept_resolution_output.get("domain"),
                dependency_output=dependency_output,
            )

            if isinstance(adaptive_path_output, dict):
                original_selected = adaptive_path_output.get("selected_next_concept")
                adaptive_path_output["original_selected_next_concept"] = original_selected
                adaptive_path_output["selected_next_concept"] = adaptive_path_validation_output.get("resolved_concept_id")
                adaptive_path_output["validation"] = adaptive_path_validation_output
                if adaptive_path_validation_output.get("fallback_used"):
                    adaptive_path_output["selected_reason"] = adaptive_path_validation_output.get("reason")

            review_queue_for_path = (
                forgetting_state.get("data", {}).get("review_queue", [])
                if isinstance(forgetting_state, dict)
                else []
            )
            frontend_path_output = build_frontend_path_output(
                concept_id_map=concept_id_map,
                dependency_output=dependency_output,
                validation_output=adaptive_path_validation_output,
                current_concept_id=fallback_concept_id,
                mastery=mastery_used if isinstance(mastery_used, dict) else {},
                review_queue=review_queue_for_path,
                current_domain=concept_resolution_output.get("domain"),
            )
        except Exception as e:
            adaptive_path_validation_output = {
                "valid": False,
                "selected_concept_id": (
                    adaptive_path_output.get("selected_next_concept")
                    if isinstance(adaptive_path_output, dict)
                    else None
                ),
                "resolved_concept_id": str(final_policy_output.get("data", {}).get("next_concept_id", "")),
                "resolved_concept_name": concept_resolution_output.get("concept_name"),
                "resolved_domain": concept_resolution_output.get("domain"),
                "fallback_used": True,
                "reason": f"Adaptive path validation failed safely: {e}",
            }



        # =====================================================
        # Adaptive Policy Bridge
        # Safely compares policy/RL output with adaptive path
        # =====================================================
        adaptive_policy_bridge_output = None

        try:
            adaptive_policy_bridge = AdaptivePolicyBridge()

            adaptive_policy_bridge_output = adaptive_policy_bridge.reconcile(
                policy_output=final_policy_output,
                adaptive_path_output=adaptive_path_output,
                view_performance_output=view_performance_output,
                evaluation_output=evaluation_output,
                multi_evidence_output=multi_evidence_output,
            )

        except Exception as e:
            adaptive_policy_bridge_output = {
                "status": "error",
                "module": "AdaptivePolicyBridge",
                "reason": str(e),
            }



        log_fusion_decision(
            conn=conn,
            learner_id=learner_id,
            concept_id=str(current_policy_output.get("data", {}).get("next_concept_id")),
            multi_evidence_output=multi_evidence_output,
        )

        log_policy_decision(
            conn=conn,
            learner_id=learner_id,
            current_concept_id=str(quiz_result.get("latest_quiz_result", {}).get("concept_id", "")),
            next_concept_id=str(final_policy_output.get("data", {}).get("next_concept_id", "")),
            knowledge_state=knowledge_state,
            behaviour_state=behaviour_state,
            forgetting_state=forgetting_state,
            evaluation_output=evaluation_output,
            learning_signal=learning_signal,
            multi_evidence_output=multi_evidence_output,
        )

        final_strategy_output = run_teaching_strategy(
            conn=conn,
            learner_id=learner_id,
            policy_output=final_policy_output,
            behaviour_state=behaviour_state,
        )

        # =====================================================
        # Feature Contribution XAI
        # Explains which learner/system signals influenced decision
        # =====================================================
        feature_contribution_output = None

        try:
            feature_explainer = FeatureContributionExplainer()

            feature_contribution_output = feature_explainer.explain(
                knowledge_state=knowledge_state,
                behaviour_state=behaviour_state,
                forgetting_state=forgetting_state,
                evaluation_output=evaluation_output,
                view_performance_output=view_performance_output,
                adaptive_path_output=adaptive_path_output,
                adaptive_policy_bridge_output=adaptive_policy_bridge_output,
            )

        except Exception as e:
            feature_contribution_output = {
                "status": "error",
                "module": "FeatureContributionExplainer",
                "reason": str(e),
            }

        xai_output = generate_xai(
            conn=conn,
            learner_id=learner_id,
            quiz_result=quiz_result,
            knowledge_state=knowledge_state,
            behaviour_state=behaviour_state,
            forgetting_state=forgetting_state,
            personalization=personalization,
            policy_output=final_policy_output,
            evaluation_output=evaluation_output,
            view_performance_output=view_performance_output,
            adaptive_path_output=adaptive_path_output,
            adaptive_policy_bridge_output=adaptive_policy_bridge_output,
            feature_contribution_output=feature_contribution_output,
        )

        # =====================================================
        # Resolve Final Concept Identity
        # Prevents "Unknown Concept" in notebook, strategy logs,
        # model comparison logs, and frontend summaries.
        # =====================================================
        final_policy_data = final_policy_output.get("data", {})
        final_concept_id = str(
            final_policy_data.get("next_concept_id")
            or concept_resolution_output.get("concept_id")
            or "1"
        )

        resolved_concept_name = resolve_concept_name(
            concept_id=final_concept_id,
            fallback_name=(
                current_teaching_content.get("concept_name")
                or current_teaching_content.get("topic")
                or concept_resource.get("concept_name")
                or concept_resource.get("topic")
                or concept_resolution_output.get("concept_name")
                or "Variables"
            ),
        )

        if resolved_concept_name == "Unknown Concept":
            resolved_concept_name = concept_resolution_output.get("concept_name") or "Variables"

        # =====================================================
        # Learner Notebook Memory
        # NotebookLM-style memory: mistakes, weak skills, revision plan
        # =====================================================
        learner_notebook_memory_output = None

        try:
            notebook_memory = LearnerNotebookMemory()

            final_policy_data = final_policy_output.get("data", {})

            learner_notebook_memory_output = notebook_memory.update_memory(
                learner_id=learner_id,
                concept_id=str(final_policy_data.get("next_concept_id", "")),
                concept_name=resolved_concept_name,
                evaluation_output=evaluation_output,
                reflection_output=reflection_output,
                learner_insight_output=learner_insight_output,
                view_performance_output=view_performance_output,
                xai_output=xai_output,
                mistake_analysis_output=mistake_analysis_output,
            )

        except Exception as e:
            learner_notebook_memory_output = {
                "status": "error",
                "module": "LearnerNotebookMemory",
                "reason": str(e),
            }

        # =====================================================
        # Evidence-Aware Teaching Strategy
        # Selects one targeted teaching view and matching assessment plan
        # =====================================================
        evidence_aware_teaching_strategy_output = None

        try:
            final_policy_data = final_policy_output.get("data", {})

            evidence_aware_teaching_strategy_output = recommend_evidence_aware_teaching_strategy(
                learner_id=learner_id,
                concept_id=str(final_policy_data.get("next_concept_id", "")),
                concept_name=resolved_concept_name,
                policy_output=final_policy_output,
                evaluation_output=evaluation_output,
                evaluation_fusion_output=evaluation_fusion_output,
                mistake_analysis_output=mistake_analysis_output,
                behaviour_state=behaviour_state,
                knowledge_state=knowledge_state,
                forgetting_state=forgetting_state,
                view_performance_output=view_performance_output,
                learner_notebook_memory_output=learner_notebook_memory_output,
                xai_output=xai_output,
                adaptive_path_output=adaptive_path_output,
                conn=conn,
            )

        except Exception as e:
            evidence_aware_teaching_strategy_output = {
                "status": "error",
                "module": "TeachingStrategySelector",
                "reason": str(e),
            }

        # =====================================================
        # Model-Based Teaching Strategy Selector
        # Comparison-only mode.
        # Does not override evidence-aware selector yet.
        # =====================================================
        model_based_teaching_strategy_output = None
        teaching_strategy_agreement = None
        learned_teaching_strategy_output = None

        try:
            learned_selector = LearnedTeachingStrategySelector()
            learned_selector.load()
            if (
                isinstance(evidence_aware_teaching_strategy_output, dict)
                and evidence_aware_teaching_strategy_output.get("status") == "success"
            ):
                learned_evidence = merge_pipeline_evidence(
                    evidence_aware_teaching_strategy_output,
                    evaluation_fusion_output,
                    mistake_analysis_output,
                    final_policy_output,
                )
                learned_teaching_strategy_output = learned_selector.predict_with_fallback(
                    learned_evidence,
                    fallback_strategy=evidence_aware_teaching_strategy_output,
                )
            else:
                learned_teaching_strategy_output = {
                    "status": "warning",
                    "module": "LearnedTeachingStrategySelector",
                    "model_used": False,
                    "fallback_used": True,
                    "teaching_view": "definition_view",
                    "difficulty": "medium",
                    "next_action": "continue",
                    "assessment_type_group": "mcq_basic",
                    "confidence": 0.0,
                    "model_versions": {},
                    "top_features": [],
                    "limitations": ["Evidence-aware strategy unavailable; learned selector not run."],
                }
        except Exception as e:
            learned_teaching_strategy_output = {
                "status": "warning",
                "module": "LearnedTeachingStrategySelector",
                "model_used": False,
                "fallback_used": True,
                "teaching_view": "definition_view",
                "difficulty": "medium",
                "next_action": "continue",
                "assessment_type_group": "mcq_basic",
                "confidence": 0.0,
                "model_versions": {},
                "top_features": [],
                "reason": str(e),
                "limitations": ["Learned teaching strategy selector failed; see reason."],
            }

        try:
            model_selector = ModelBasedTeachingStrategySelector()

            final_policy_data = final_policy_output.get("data", {})

            model_based_teaching_strategy_output = model_selector.predict(
                learner_id=learner_id,
                concept_id=str(final_policy_data.get("next_concept_id", "")),
                concept_name=resolved_concept_name,
                policy_output=final_policy_output,
                evaluation_output=evaluation_output,
                behaviour_state=behaviour_state,
                view_performance_output=view_performance_output,
                learner_notebook_memory_output=learner_notebook_memory_output,
                xai_output=xai_output,
                adaptive_path_output=adaptive_path_output,
                knowledge_state=knowledge_state,
                forgetting_state=forgetting_state,
            )

            if (
                isinstance(model_based_teaching_strategy_output, dict)
                and model_based_teaching_strategy_output.get("status") == "success"
                and isinstance(evidence_aware_teaching_strategy_output, dict)
            ):
                teaching_strategy_agreement = (
                    model_based_teaching_strategy_output.get("model_teaching_view")
                    == evidence_aware_teaching_strategy_output.get("teaching_view")
                )

        except Exception as e:
            model_based_teaching_strategy_output = {
                "status": "error",
                "module": "ModelBasedTeachingStrategySelector",
                "reason": str(e),
            }
            teaching_strategy_agreement = None

        teaching_strategy_model_comparison_log_output = None

        try:
            final_policy_data = final_policy_output.get("data", {})

            teaching_strategy_model_comparison_log_output = log_teaching_strategy_model_comparison(
                conn=conn,
                learner_id=learner_id,
                concept_id=str(final_policy_data.get("next_concept_id", "")),
                concept_name=resolved_concept_name,
                evidence_aware_output=evidence_aware_teaching_strategy_output,
                model_based_output=model_based_teaching_strategy_output,
            )

        except Exception as e:
            teaching_strategy_model_comparison_log_output = {
                "status": "error",
                "module": "TeachingStrategyModelComparisonLogger",
                "reason": str(e),
            }

        # =====================================================
        # Frontend Teaching View Adapter
        # Converts full generated teaching content into one
        # frontend-safe selected view.
        # =====================================================
        frontend_teaching_view_output = None

        try:
            selected_teaching_view = None

            if isinstance(evidence_aware_teaching_strategy_output, dict):
                selected_teaching_view = evidence_aware_teaching_strategy_output.get("teaching_view")

            frontend_teaching_view_output = build_frontend_teaching_view(
                teaching_content=current_teaching_content,
                selected_teaching_view=selected_teaching_view,
            )

        except Exception as e:
            frontend_teaching_view_output = {
                "status": "error",
                "module": "FrontendTeachingViewAdapter",
                "reason": str(e),
            }

        # =====================================================
        # Strategy Training Log
        # Stores session evidence for future strategy tuning
        # =====================================================
        teaching_strategy_training_log_output = None

        try:
            final_policy_data = final_policy_output.get("data", {})

            teaching_strategy_training_log_output = log_teaching_strategy_training_session(
                conn=conn,
                learner_id=learner_id,
                concept_id=str(final_policy_data.get("next_concept_id", "")),
                concept_name=resolved_concept_name,
                policy_output=final_policy_output,
                evaluation_output=evaluation_output,
                behaviour_state=behaviour_state,
                view_performance_output=view_performance_output,
                learner_notebook_memory_output=learner_notebook_memory_output,
                xai_output=xai_output,
                adaptive_path_output=adaptive_path_output,
                evidence_aware_teaching_strategy_output=evidence_aware_teaching_strategy_output,
            )

        except Exception as e:
            teaching_strategy_training_log_output = {
                "status": "error",
                "module": "TeachingStrategyTrainingLogger",
                "reason": str(e),
            }

        structured_evaluation_output = {
            "status": "success",
            "module": "StructuredEvaluationBridge",
            "structured_question_count": 0,
            "structured_question_types": [],
            "used_simulated_answers": False,
            "evaluation": None,
            "reason": "Structured evaluation not run yet.",
        }



        progression_reward_output = {
            "status": "success",
            "module": "ProgressionRewardEngine",
            "progression_result": {},
            "promotion_confidence_output": {},
            "reward_state": {},
            "celebration": {
                "show": False,
                "type": "none",
                "message": "",
                "mascot_emotion": "neutral",
                "animation": "none",
                "xp_awarded": 0,
                "streak_updated": False,
                "next_unlock": None,
            },
            "frontend_contract": {
                "show_celebration_modal": False,
                "show_xp_popup": False,
                "update_streak_widget": False,
                "update_path_node": False,
                "mascot_emotion": "neutral",
            },
            "reason": "Progression reward not run yet.",
        }

        reward_persistence_output = {
            "status": "not_run",
            "module": "RewardStateStore",
            "reason": "Reward persistence not run yet.",
        }

        try:
            assessment_difficulty, assessment_types = _assessment_plan_from_strategy(
                evidence_aware_teaching_strategy_output=evidence_aware_teaching_strategy_output,
                fallback_difficulty=final_difficulty,
                fallback_types=["mcq", "output_prediction", "debug", "short_explanation", "transfer"],
            )

            reward_persistence_output = persist_reward_state(
                progression_reward_output,
                dry_run=reward_dry_run,
            )

            targeted_assessment_agent_output = assessment_agent.run(
                concept_resource=concept_resource,
                learner_id=learner_id,
                difficulty=assessment_difficulty,
                requested_types=assessment_types,
            )

            assessment_agent_output = targeted_assessment_agent_output
            assessment_output = targeted_assessment_agent_output["data"]
            assessment_output = _normalize_assessment_question_types(assessment_output)

            # =====================================================
            # Expanded Assessment Generator
            # Adds extra structured question types only if requested
            # by TeachingStrategySelector.
            # Safe mode: max 2 extra questions.
            # =====================================================
            assessment_output = attach_expanded_questions_to_bundle(
                assessment_bundle=assessment_output,
                concept_resource=concept_resource,
                requested_types=assessment_types,
                difficulty=assessment_difficulty,
                max_extra_questions=2,
            )

            assessment_output = normalize_assessment_bundle_for_frontend(assessment_output)
            apply_resolved_concept_to_packet(assessment_output, concept_resolution_output)



            try:
                structured_evaluation_output = run_structured_evaluation_bridge(
                    assessment_output=assessment_output,
                    learner_answers=None,
                    use_simulated_answers=True,
                )

            except Exception as e:
                structured_evaluation_output = {
                    "status": "error",
                    "module": "StructuredEvaluationBridge",
                    "reason": str(e),
                }

            # =====================================================
            # Progression Reward Engine
            # Creates Duolingo-style progression, XP, streak,
            # celebration, and mascot trigger output.
            # Does not override policy yet.
            # =====================================================
            progression_reward_output = None

            try:
                progression_reward_output = build_progression_reward_output(
                    learner_id=learner_id,
                    concept_id=final_concept_id,
                    concept_name=resolved_concept_name,
                    current_difficulty=assessment_difficulty,
                    evaluation_output=evaluation_output,
                    structured_evaluation_output=structured_evaluation_output,
                    behaviour_state=behaviour_state,
                    view_performance_output=view_performance_output,
                    teaching_strategy_output=evidence_aware_teaching_strategy_output,
                    next_concept_name=None,
                    guess_probability=0.0,
                )
                reward_persistence_output = persist_reward_state(
                    progression_reward_output,
                    dry_run=reward_dry_run,
                )
            except Exception as e:
                progression_reward_output = {
                    "status": "error",
                    "module": "ProgressionRewardEngine",
                    "reason": str(e),
                }

                reward_persistence_output = {
                    "status": "error",
                    "module": "RewardStateStore",
                    "reason": "ProgressionRewardEngine failed, so reward state was not persisted.",
                }
        except Exception:
            pass

        cognitutor_lm_output = build_optional_cognitutor_lm_output(
            learner_id=learner_id,
            concept_id=final_concept_id,
            concept_name=resolved_concept_name,
            domain=concept_resource.get("domain") or current_teaching_content.get("domain"),
            teaching_view=(
                frontend_teaching_view_output.get("selected_teaching_view")
                if isinstance(frontend_teaching_view_output, dict)
                else None
            ),
            difficulty=str(final_difficulty or final_policy_data.get("difficulty") or "medium"),
        )

        voice_script_output = {}
        voice_script_bundle = {}
        try:
            selected_voice_view = (
                frontend_teaching_view_output.get("selected_teaching_view")
                if isinstance(frontend_teaching_view_output, dict)
                else None
            )
            key_points = current_teaching_content.get("key_points") or current_teaching_content.get("key_points_base") or []
            if not isinstance(key_points, list):
                key_points = [str(key_points)] if key_points else []
            if not key_points:
                for item in current_teaching_content.get("items", []):
                    if isinstance(item, dict) and isinstance(item.get("bullets"), list):
                        key_points.extend(item.get("bullets", []))

            voice_evidence = {
                "concept_name": resolved_concept_name,
                "teaching_view": selected_voice_view
                or (
                    evidence_aware_teaching_strategy_output.get("teaching_view")
                    if isinstance(evidence_aware_teaching_strategy_output, dict)
                    else None
                ),
                "difficulty": str(final_difficulty or final_policy_data.get("difficulty") or "medium"),
                "learner_level": learner_profile,
                "mistake_type": (
                    mistake_analysis_output.get("dominant_mistake_type")
                    if isinstance(mistake_analysis_output, dict)
                    else None
                ),
                "weakest_skill": (
                    evaluation_fusion_output.get("weakest_skill_signal", {}).get("weakest_skill")
                    if isinstance(evaluation_fusion_output, dict)
                    else None
                ),
                "evaluation_label": (
                    evaluation_fusion_output.get("fused_label")
                    if isinstance(evaluation_fusion_output, dict)
                    else evaluation_output.get("verdict")
                ),
                "doubt_intent": None,
                "next_action": (
                    evidence_aware_teaching_strategy_output.get("next_activity")
                    if isinstance(evidence_aware_teaching_strategy_output, dict)
                    else multi_evidence_output.get("final_action")
                ),
                "key_points": key_points,
                "example": (
                    current_teaching_content.get("examples")
                    or current_teaching_content.get("examples_base")
                    or current_teaching_content.get("content")
                    or current_teaching_content.get("definition")
                ),
            }
            voice_generator = VoiceScriptGenerator()
            voice_script_output = voice_generator.generate(
                script_type="teaching_explanation",
                evidence=voice_evidence,
            )
            voice_script_bundle = voice_generator.generate_bundle(voice_evidence)
        except Exception as e:
            voice_script_output = {
                "status": "error",
                "module": "VoiceScriptGenerator",
                "script_type": "teaching_explanation",
                "concept_name": resolved_concept_name,
                "text": "",
                "tts_ready": False,
                "estimated_duration_sec": 0,
                "tone": "supportive",
                "frontend_component": "VoiceScriptCard",
                "limitations": [f"{type(e).__name__}: voice script generation failed."],
            }
            voice_script_bundle = {
                "status": "error",
                "module": "VoiceScriptGenerator",
                "scripts": [],
                "frontend_component": "VoiceScriptCard",
            }

        adaptive_hint_output = {}
        learned_hint_output = None
        learned_path_ranker_output = None
        hint_evidence: dict[str, Any] = {}
        try:
            first_question = assessment_output.get("questions", [])[0] if assessment_output.get("questions") else {}
            first_result = evaluation_output.get("results", [])[0] if evaluation_output.get("results") else {}
            first_question_type = (
                first_question.get("question_type")
                or first_question.get("assessment_type")
                or first_result.get("question_type")
                or first_result.get("assessment_type")
                or "general"
            )
            hint_evidence = {
                "learner_id": learner_id,
                "concept_id": final_concept_id,
                "concept_name": resolved_concept_name,
                "question_type": first_question_type,
                "learner_answer": final_learner_answers.get(first_question_type, ""),
                "expected_answer": first_question.get("expected_answer"),
                "score": first_result.get("score", evaluation_output.get("overall_score", 0.5)),
                "evaluation_label": (
                    evaluation_fusion_output.get("fused_label")
                    if isinstance(evaluation_fusion_output, dict)
                    else evaluation_output.get("verdict")
                ),
                "mistake_type": (
                    mistake_analysis_output.get("dominant_mistake_type")
                    if isinstance(mistake_analysis_output, dict)
                    else None
                ),
                "weakest_skill": (
                    evaluation_fusion_output.get("weakest_skill_signal", {}).get("weakest_skill")
                    if isinstance(evaluation_fusion_output, dict)
                    else None
                ),
                "behaviour_risk": (
                    behaviour_state.get("data", {}).get("behavior_score")
                    if isinstance(behaviour_state, dict)
                    else 0.3
                ),
                "mastery_score": (
                    knowledge_state.get("data", {}).get("data", {}).get("predicted_mastery_last")
                    if isinstance(knowledge_state, dict)
                    else 0.5
                ),
                "hint_count_used": 0,
                "difficulty": str(final_difficulty or final_policy_data.get("difficulty") or "medium"),
                "teaching_view": (
                    frontend_teaching_view_output.get("selected_teaching_view")
                    if isinstance(frontend_teaching_view_output, dict)
                    else None
                ),
                "key_points": current_teaching_content.get("key_points") or current_teaching_content.get("key_points_base"),
                "example": (
                    current_teaching_content.get("examples")
                    or current_teaching_content.get("examples_base")
                    or current_teaching_content.get("content")
                ),
                "confidence": first_result.get("confidence"),
                "time_taken_sec": first_result.get("time_taken_sec"),
                "wrong_streak": mistake_analysis_output.get("high_severity_count", 0)
                if isinstance(mistake_analysis_output, dict)
                else 0,
                "previous_score": evaluation_output.get("overall_score"),
                "previous_hint_success": 0.5,
            }
            adaptive_hint_output = AdaptiveHintPolicy().select_hint(hint_evidence)
            try:
                lhp = LearnedHintPolicy()
                lhp.load()
                learned_hint_output = lhp.predict_with_fallback(
                    hint_evidence,
                    fallback_hint=adaptive_hint_output,
                )
            except Exception:
                learned_hint_output = {
                    "status": "warning",
                    "module": "LearnedHintPolicy",
                    "model_used": False,
                    "fallback_used": True,
                    "limitations": ["Learned hint policy invocation failed; using adaptive hint only."],
                }
        except Exception as e:
            adaptive_hint_output = {
                "status": "error",
                "module": "AdaptiveHintPolicy",
                "hint_type": "guided_hint",
                "hint_level": "guided_hint",
                "hint_text": "Review the main idea, then try one small step before answering again.",
                "support_need": 0.5,
                "evidence": {},
                "frontend_component": "AdaptiveHintCard",
                "fallback_used": True,
                "reason": str(e),
            }
            learned_hint_output = {
                "status": "warning",
                "module": "LearnedHintPolicy",
                "model_used": False,
                "fallback_used": True,
                "limitations": ["Adaptive hint failed before learned hint could run."],
            }

        try:
            from tutor.concept_dependency.learned_adaptive_path_ranker import LearnedAdaptivePathRanker

            fus = evaluation_fusion_output if isinstance(evaluation_fusion_output, dict) else {}
            fus_score = float(
                fus.get("fused_score", evaluation_evidence.get("overall_score", 0.5)) or 0.5
            )
            km = mastery_used if isinstance(mastery_used, dict) else {}
            mast_vals = [float(v) for v in km.values()] if km else []
            cur_m = float(mast_vals[0]) if mast_vals else float(
                knowledge_state.get("data", {}).get("data", {}).get("predicted_mastery_last", 0.5)
                or 0.5
            )
            prereq_m = float(sum(mast_vals) / len(mast_vals)) if mast_vals else cur_m
            beh_s = float(
                behaviour_evidence.get("behavior_score")
                or behaviour_evidence.get("behaviour_score")
                or 0.5
            )
            next_cid = str(final_policy_output.get("data", {}).get("next_concept_id", "") or "")
            rq = forgetting_state.get("data", {}).get("review_queue", []) if isinstance(forgetting_state, dict) else []
            review_ids = [str(x.get("concept_id", x)) if isinstance(x, dict) else str(x) for x in (rq or [])]
            path_evidence = {
                "current_mastery": cur_m,
                "prerequisite_mastery": prereq_m,
                "behaviour_risk": float(max(0.0, min(1.0, 1.0 - beh_s))),
                "behaviour_confidence": float(max(0.0, min(1.0, beh_s))),
                "fused_score": fus_score,
                "recent_score": float(evaluation_evidence.get("overall_score", fus_score) or fus_score),
                "wrong_streak": float(
                    mistake_analysis_output.get("high_severity_count", 0)
                    if isinstance(mistake_analysis_output, dict)
                    else 0
                ),
                "review_due": 0.75 if next_cid and next_cid in review_ids else 0.2,
                "time_gap_days": 4.0,
                "attempts_on_concept": 3.0,
                "hint_usage": float(hint_evidence.get("hint_count_used", 0)) if isinstance(hint_evidence, dict) else 0.0,
                "mistake_count": float(
                    sum((mistake_analysis_output.get("mistake_type_counts") or {}).values())
                    if isinstance(mistake_analysis_output, dict)
                    else 0.0
                ),
                "weak_concept_flag": fus_score < 0.45,
                "concept_unlock_status": "unlocked",
                "difficulty": str(final_policy_data.get("difficulty") or "medium"),
                "reward_xp": float(
                    progression_reward_output.get("xp_awarded", 0)
                    if isinstance(progression_reward_output, dict)
                    else 0.0
                ),
                "anomaly_score": float(max(0.0, 1.0 - beh_s)),
                "path_position": 0.5,
                "review_queue_concept_ids": review_ids,
            }
            rnk = LearnedAdaptivePathRanker()
            rnk.load()
            learned_path_ranker_output = rnk.predict_with_fallback(
                learner_id=str(learner_id),
                current_concept_id=next_cid,
                dependency_output=dependency_output if isinstance(dependency_output, dict) else {},
                evidence=path_evidence,
                fallback_path=adaptive_path_output if isinstance(adaptive_path_output, dict) else {},
            )
        except Exception as _e_path:
            learned_path_ranker_output = {
                "status": "warning",
                "module": "LearnedAdaptivePathRanker",
                "model_used": False,
                "fallback_used": True,
                "recommended_action": "review_current",
                "recommended_node_type": "lesson",
                "recommended_concept_id": str(final_policy_output.get("data", {}).get("next_concept_id", "") or ""),
                "rank_score_bucket": "low_priority",
                "confidence": 0.0,
                "safe_candidates_count": 0,
                "blocked_candidates_count": 0,
                "safety_violation": False,
                "top_features": [],
                "frontend_component": "AdaptivePathRecommendationCard",
                "limitations": [f"Learned path ranker skipped: {_e_path!r}"],
            }

        log_learning_path(conn, learner_id, final_policy_output)

        return {
            "learner_id": learner_id,
            "timestamp": now_iso(),
            "quiz_result": quiz_result,
            "knowledge_state": knowledge_state,
            "behaviour_state": behaviour_state,
            "forgetting_state": forgetting_state,
            "personalization": personalization,
            "baseline_policy_output": current_policy_output,
            "baseline_teaching_strategy": current_strategy_output,
            "reflection_output": reflection_output,
            "learner_insight_output": learner_insight_output,
            "baseline_note": "Used only for debugging. Final decision is policy_output.",
            "demo_summary": {
                "learner_id": learner_id,
                "final_concept": final_policy_data.get("next_concept_id"),
                "selected_learner": learner_id,
                "latest_interaction": quiz_result.get("latest_quiz_result") if isinstance(quiz_result, dict) else None,
                "latest_action_or_route": "integrated_tutor_once",
                "final_concept_name": resolved_concept_name,
                "final_strategy": final_policy_data.get("strategy"),
                "final_difficulty": final_policy_data.get("difficulty"),
                "behaviour_runtime": get_behaviour_runtime_summary(behaviour_state),
                "kt_runtime": get_kt_runtime_summary(knowledge_state),
                "policy_runtime": get_policy_runtime_summary(decision_agent_output, final_policy_output),
                "generation_source": get_generation_source_summary(cognitutor_lm_output),
                "reward_source": build_reward_source_summary(progression_reward_output, reward_persistence_output),
                "agentic_trace_status": "success",
                "explanation_mode": final_policy_data.get("explanation_mode"),
                "concept_resolution_status": concept_resolution_output.get("status"),
                "resolved_concept_id": concept_resolution_output.get("concept_id"),
                "resolved_concept_name": concept_resolution_output.get("concept_name"),
                "resolved_domain": concept_resolution_output.get("domain"),
                "old_pipeline_fallback_concept_used": concept_resolution_output.get("fallback_used"),
                "cognitutor_lm_status": (
                    cognitutor_lm_output.get("status")
                    if isinstance(cognitutor_lm_output, dict)
                    else None
                ),
                "cognitutor_lm_selected_view": (
                    cognitutor_lm_output.get("selected_view")
                    if isinstance(cognitutor_lm_output, dict)
                    else None
                ),
                "cognitutor_lm_assessment_count": (
                    cognitutor_lm_output.get("assessment_count")
                    if isinstance(cognitutor_lm_output, dict)
                    else None
                ),
                "cognitutor_lm_product_status": (
                    (cognitutor_lm_output.get("cognitutor_lm_product_output") or {}).get("status")
                    if isinstance(cognitutor_lm_output, dict)
                    else None
                ),
                "product_assessment_type_count": (
                    cognitutor_lm_output.get("product_assessment_type_count")
                    if isinstance(cognitutor_lm_output, dict)
                    else None
                ),
                "product_flashcard_variant_count": (
                    cognitutor_lm_output.get("product_flashcard_variant_count")
                    if isinstance(cognitutor_lm_output, dict)
                    else None
                ),
                "product_mindmap_variant_count": (
                    cognitutor_lm_output.get("product_mindmap_variant_count")
                    if isinstance(cognitutor_lm_output, dict)
                    else None
                ),
                "product_voice_variant_count": (
                    cognitutor_lm_output.get("product_voice_variant_count")
                    if isinstance(cognitutor_lm_output, dict)
                    else None
                ),
                "product_frontend_ready": (
                    cognitutor_lm_output.get("product_frontend_ready")
                    if isinstance(cognitutor_lm_output, dict)
                    else None
                ),
                "voice_script_status": (
                    voice_script_output.get("status")
                    if isinstance(voice_script_output, dict)
                    else None
                ),
                "voice_script_type": (
                    voice_script_output.get("script_type")
                    if isinstance(voice_script_output, dict)
                    else None
                ),
                "voice_script_tts_ready": (
                    voice_script_output.get("tts_ready")
                    if isinstance(voice_script_output, dict)
                    else None
                ),
                "adaptive_hint_status": (
                    adaptive_hint_output.get("status")
                    if isinstance(adaptive_hint_output, dict)
                    else None
                ),
                "adaptive_hint_type": (
                    adaptive_hint_output.get("hint_type")
                    if isinstance(adaptive_hint_output, dict)
                    else None
                ),
                "teaching_item_count": current_teaching_content.get("item_count"),
                "recommended_view": recommended_view,
                "view_reward": (
                    view_performance_output.get("logged", {}).get("reward")
                    if isinstance(view_performance_output, dict)
                    else None
                ),
                "adaptive_path_selected": (
                    adaptive_path_output.get("selected_next_concept")
                    if isinstance(adaptive_path_output, dict)
                    else None
                ),
                "adaptive_path_original_selected": (
                    adaptive_path_output.get("original_selected_next_concept")
                    if isinstance(adaptive_path_output, dict)
                    else None
                ),
                "adaptive_path_validation_status": (
                    "fallback"
                    if adaptive_path_validation_output.get("fallback_used")
                    else "valid"
                    if adaptive_path_validation_output.get("valid")
                    else "invalid"
                ),
                "adaptive_path_resolved_concept_id": adaptive_path_validation_output.get("resolved_concept_id"),
                "adaptive_path_resolved_concept_name": adaptive_path_validation_output.get("resolved_concept_name"),
                "adaptive_path_resolved_domain": adaptive_path_validation_output.get("resolved_domain"),
                "adaptive_path_fallback_used": adaptive_path_validation_output.get("fallback_used"),
                "adaptive_path_validation_reason": adaptive_path_validation_output.get("reason"),
                "adaptive_path_validation_result": get_adaptive_path_validation_summary(
                    adaptive_path_output,
                    adaptive_path_validation_output,
                ),
                "frontend_path_output": frontend_path_output,
                "adaptive_path_strategy": (
                    adaptive_path_output.get("recommended_strategy")
                    if isinstance(adaptive_path_output, dict)
                    else None
                ),
                "adaptive_path_difficulty": (
                    adaptive_path_output.get("recommended_difficulty")
                    if isinstance(adaptive_path_output, dict)
                    else None
                ),
                "path_ranker_status": (
                    learned_path_ranker_output.get("status")
                    if isinstance(learned_path_ranker_output, dict)
                    else None
                ),
                "path_ranker_action": (
                    learned_path_ranker_output.get("recommended_action")
                    if isinstance(learned_path_ranker_output, dict)
                    else None
                ),
                "path_ranker_fallback": (
                    learned_path_ranker_output.get("fallback_used")
                    if isinstance(learned_path_ranker_output, dict)
                    else None
                ),
                "bridge_agreement": (
                    adaptive_policy_bridge_output.get("agreement")
                    if isinstance(adaptive_policy_bridge_output, dict)
                    else None
                ),
                "bridge_override_allowed": (
                    adaptive_policy_bridge_output.get("override_allowed")
                    if isinstance(adaptive_policy_bridge_output, dict)
                    else None
                ),
                "bridge_recommendation": (
                    adaptive_policy_bridge_output.get("final_recommendation")
                    if isinstance(adaptive_policy_bridge_output, dict)
                    else None
                ),
                "xai_pressure": (
                    feature_contribution_output.get("decision_pressure_label")
                    if isinstance(feature_contribution_output, dict)
                    else None
                ),
                "xai_top_factors": (
                    [
                        factor.get("feature")
                        for factor in feature_contribution_output.get("top_factors", [])
                    ]
                    if isinstance(feature_contribution_output, dict)
                    else []
                ),
                "notebook_summary": (
                    learner_notebook_memory_output.get("notebook_summary")
                    if isinstance(learner_notebook_memory_output, dict)
                    else None
                ),
                "next_practice_queue": (
                    learner_notebook_memory_output.get("next_practice_queue")
                    if isinstance(learner_notebook_memory_output, dict)
                    else []
                ),
                "teaching_view": (
                    evidence_aware_teaching_strategy_output.get("teaching_view")
                    if isinstance(evidence_aware_teaching_strategy_output, dict)
                    else None
                ),
                "frontend_selected_view": (
                    frontend_teaching_view_output.get("selected_teaching_view")
                    if isinstance(frontend_teaching_view_output, dict)
                    else None
                ),
                "frontend_selected_display_type": (
                    frontend_teaching_view_output.get("selected_view", {}).get("display_type")
                    if isinstance(frontend_teaching_view_output, dict)
                    else None
                ),
                "frontend_view_adapter_status": (
                    frontend_teaching_view_output.get("status")
                    if isinstance(frontend_teaching_view_output, dict)
                    else None
                ),
                "assessment_types": (
                    evidence_aware_teaching_strategy_output.get("assessment_types")
                    if isinstance(evidence_aware_teaching_strategy_output, dict)
                    else []
                ),
                "fallback_views": (
                    evidence_aware_teaching_strategy_output.get("fallback_views")
                    if isinstance(evidence_aware_teaching_strategy_output, dict)
                    else []
                ),
                "next_activity": (
                    evidence_aware_teaching_strategy_output.get("next_activity")
                    if isinstance(evidence_aware_teaching_strategy_output, dict)
                    else None
                ),
                "progression_action": (
                    evidence_aware_teaching_strategy_output.get("progression_action")
                    if isinstance(evidence_aware_teaching_strategy_output, dict)
                    else None
                ),
                "training_log_status": (
                    teaching_strategy_training_log_output.get("status")
                    if isinstance(teaching_strategy_training_log_output, dict)
                    else None
                ),
                "model_teaching_view": (
                    model_based_teaching_strategy_output.get("model_teaching_view")
                    if isinstance(model_based_teaching_strategy_output, dict)
                    else None
                ),
                "model_progression_action": (
                    model_based_teaching_strategy_output.get("model_progression_action")
                    if isinstance(model_based_teaching_strategy_output, dict)
                    else None
                ),
                "progression_model_status": (
                    model_based_teaching_strategy_output.get("progression_model_status")
                    if isinstance(model_based_teaching_strategy_output, dict)
                    else None
                ),
                "progression_model_reason": (
                    model_based_teaching_strategy_output.get("progression_model_reason")
                    if isinstance(model_based_teaching_strategy_output, dict)
                    else None
                ),
                "model_teaching_view_confidence": (
                    model_based_teaching_strategy_output.get("teaching_view_confidence")
                    if isinstance(model_based_teaching_strategy_output, dict)
                    else None
                ),
                "model_comparison_log_status": (
                    teaching_strategy_model_comparison_log_output.get("status")
                    if isinstance(teaching_strategy_model_comparison_log_output, dict)
                    else None
                ),
                "debug_evaluation_status": (
                    debug_evaluation_output.get("status")
                    if isinstance(debug_evaluation_output, dict)
                    else None
                ),
                "debug_evaluation_score": (
                    debug_evaluation_output.get("overall_score")
                    if isinstance(debug_evaluation_output, dict)
                    else None
                ),
                "debug_evaluation_label": (
                    debug_evaluation_output.get("quality_label")
                    if isinstance(debug_evaluation_output, dict)
                    else None
                ),
                "debug_evaluation_mode": debug_evaluation_mode,
                "output_prediction_evaluation_status": (
                    output_prediction_evaluation_output.get("status")
                    if isinstance(output_prediction_evaluation_output, dict)
                    else None
                ),
                "output_prediction_evaluation_score": (
                    output_prediction_evaluation_output.get("overall_score")
                    if isinstance(output_prediction_evaluation_output, dict)
                    else None
                ),
                "output_prediction_evaluation_label": (
                    output_prediction_evaluation_output.get("quality_label")
                    if isinstance(output_prediction_evaluation_output, dict)
                    else None
                ),
                "output_prediction_error_type": (
                    output_prediction_evaluation_output.get("dominant_output_error_type")
                    if isinstance(output_prediction_evaluation_output, dict)
                    else None
                ),
                "output_prediction_evaluation_mode": output_prediction_evaluation_mode,

                "evaluation_fusion_status": (
                    evaluation_fusion_output.get("status")
                    if isinstance(evaluation_fusion_output, dict)
                    else None
                ),
                "evaluation_fusion_mode": evaluation_fusion_mode,
                "fused_score": (
                    evaluation_fusion_output.get("fused_score")
                    if isinstance(evaluation_fusion_output, dict)
                    else None
                ),
                "fused_label": (
                    evaluation_fusion_output.get("fused_label")
                    if isinstance(evaluation_fusion_output, dict)
                    else None
                ),
                "recommended_learning_signal": (
                    evaluation_fusion_output.get("recommended_learning_signal")
                    if isinstance(evaluation_fusion_output, dict)
                    else None
                ),
                "evaluator_agreement": (
                    evaluation_fusion_output.get("evaluator_agreement")
                    if isinstance(evaluation_fusion_output, dict)
                    else None
                ),
                "fusion_confidence": (
                    evaluation_fusion_output.get("fusion_confidence")
                    if isinstance(evaluation_fusion_output, dict)
                    else None
                ),
                "fusion_confidence_label": (
                    evaluation_fusion_output.get("fusion_confidence_label")
                    if isinstance(evaluation_fusion_output, dict)
                    else None
                ),
                "weakest_skill": (
                    evaluation_fusion_output.get("weakest_skill_signal", {}).get("weakest_skill")
                    if isinstance(evaluation_fusion_output, dict)
                    else None
                ),

                "teaching_strategy_agreement": teaching_strategy_agreement,
                "assessment_question_count": assessment_output.get("question_count"),
                "assessment_frontend_ready": assessment_output.get("frontend_ready"),
                "assessment_frontend_components": assessment_output.get("frontend_components_used", []),
                "expanded_question_types_added": assessment_output.get("expanded_question_types_added", []),
                "structured_evaluation_status": (
                    structured_evaluation_output.get("status")
                    if isinstance(structured_evaluation_output, dict)
                    else None
                ),
                "structured_question_count": (
                    structured_evaluation_output.get("structured_question_count")
                    if isinstance(structured_evaluation_output, dict)
                    else None
                ),
                "structured_question_types": (
                    structured_evaluation_output.get("structured_question_types", [])
                    if isinstance(structured_evaluation_output, dict)
                    else []
                ),
                "promotion_confidence": (
                    progression_reward_output.get("progression_result", {}).get("promotion_confidence")
                    if isinstance(progression_reward_output, dict)
                    else None
                ),
                "promotion_allowed": (
                    progression_reward_output.get("progression_result", {}).get("promotion_allowed")
                    if isinstance(progression_reward_output, dict)
                    else None
                ),
                "level_up_allowed": (
                    progression_reward_output.get("progression_result", {}).get("level_up_allowed")
                    if isinstance(progression_reward_output, dict)
                    else None
                ),
                "concept_cleared": (
                    progression_reward_output.get("progression_result", {}).get("concept_cleared")
                    if isinstance(progression_reward_output, dict)
                    else None
                ),
                "reward_xp_awarded": (
                    progression_reward_output.get("reward_state", {}).get("xp_awarded")
                    if isinstance(progression_reward_output, dict)
                    else None
                ),
                "streak_updated": (
                    progression_reward_output.get("reward_state", {}).get("streak_updated")
                    if isinstance(progression_reward_output, dict)
                    else None
                ),
                "celebration_type": (
                    progression_reward_output.get("celebration", {}).get("type")
                    if isinstance(progression_reward_output, dict)
                    else None
                ),
                "celebration_message": (
                    progression_reward_output.get("celebration", {}).get("message")
                    if isinstance(progression_reward_output, dict)
                    else None
                ),
                "reward_persistence_status": (
                    reward_persistence_output.get("status")
                    if isinstance(reward_persistence_output, dict)
                    else None
                ),
                "reward_persistence_mode": (
                    reward_persistence_output.get("mode")
                    if isinstance(reward_persistence_output, dict)
                    else None
                ),
                "total_xp": (
                    reward_persistence_output.get("total_xp")
                    if isinstance(reward_persistence_output, dict)
                    else None
                ),
                "daily_xp": (
                    reward_persistence_output.get("daily_xp")
                    if isinstance(reward_persistence_output, dict)
                    else None
                ),
                "weekly_xp": (
                    reward_persistence_output.get("weekly_xp")
                    if isinstance(reward_persistence_output, dict)
                    else None
                ),
                "current_level": (
                    reward_persistence_output.get("current_level")
                    if isinstance(reward_persistence_output, dict)
                    else None
                ),
                "current_streak": (
                    reward_persistence_output.get("current_streak")
                    if isinstance(reward_persistence_output, dict)
                    else None
                ),
                "longest_streak": (
                    reward_persistence_output.get("longest_streak")
                    if isinstance(reward_persistence_output, dict)
                    else None
                ),
                "evaluation_score": evaluation_output.get("overall_score"),
                "final_action": multi_evidence_output.get("final_action"),
                "dominant_mistake_type": (
                    mistake_analysis_output.get("dominant_mistake_type")
                    if isinstance(mistake_analysis_output, dict)
                    else None
                ),
                "mistake_type_counts": (
                    mistake_analysis_output.get("mistake_type_counts", {})
                    if isinstance(mistake_analysis_output, dict)
                    else {}
                ),
                "high_severity_mistake_count": (
                    mistake_analysis_output.get("high_severity_count")
                    if isinstance(mistake_analysis_output, dict)
                    else None
                ),
                "rubric_evaluation_status": (
                    rubric_evaluation_output.get("status")
                    if isinstance(rubric_evaluation_output, dict)
                    else None
                ),
                "rubric_overall_score": (
                    rubric_evaluation_output.get("overall_score")
                    if isinstance(rubric_evaluation_output, dict)
                    else None
                ),
                "rubric_verdict": (
                    rubric_evaluation_output.get("verdict")
                    if isinstance(rubric_evaluation_output, dict)
                    else None
                ),
                "rubric_mode": rubric_mode,
            },
            "demo_output": {
                "demo_summary": {
                    "learner_id": learner_id,
                    "final_concept": final_policy_data.get("next_concept_id"),
                    "selected_learner": learner_id,
                    "latest_interaction": quiz_result.get("latest_quiz_result") if isinstance(quiz_result, dict) else None,
                    "latest_action_or_route": "integrated_tutor_once",
                    "final_concept_name": resolved_concept_name,
                    "final_strategy": final_policy_data.get("strategy"),
                    "final_difficulty": final_policy_data.get("difficulty"),
                    "behaviour_runtime": get_behaviour_runtime_summary(behaviour_state),
                    "kt_runtime": get_kt_runtime_summary(knowledge_state),
                    "policy_runtime": get_policy_runtime_summary(decision_agent_output, final_policy_output),
                    "generation_source": get_generation_source_summary(cognitutor_lm_output),
                    "reward_source": build_reward_source_summary(progression_reward_output, reward_persistence_output),
                    "agentic_trace_status": "success",
                    "explanation_mode": final_policy_data.get("explanation_mode"),
                    "concept_resolution_status": concept_resolution_output.get("status"),
                    "resolved_concept_id": concept_resolution_output.get("concept_id"),
                    "resolved_concept_name": concept_resolution_output.get("concept_name"),
                    "resolved_domain": concept_resolution_output.get("domain"),
                    "old_pipeline_fallback_concept_used": concept_resolution_output.get("fallback_used"),
                    "teaching_item_count": current_teaching_content.get("item_count"),
                    "recommended_view": recommended_view,
                    "view_reward": (
                        view_performance_output.get("logged", {}).get("reward")
                        if isinstance(view_performance_output, dict)
                        else None
                    ),
                    "adaptive_path_selected": (
                        adaptive_path_output.get("selected_next_concept")
                        if isinstance(adaptive_path_output, dict)
                        else None
                    ),
                    "adaptive_path_original_selected": (
                        adaptive_path_output.get("original_selected_next_concept")
                        if isinstance(adaptive_path_output, dict)
                        else None
                    ),
                    "adaptive_path_validation_status": (
                        "fallback"
                        if adaptive_path_validation_output.get("fallback_used")
                        else "valid"
                        if adaptive_path_validation_output.get("valid")
                        else "invalid"
                    ),
                    "adaptive_path_resolved_concept_id": adaptive_path_validation_output.get("resolved_concept_id"),
                    "adaptive_path_resolved_concept_name": adaptive_path_validation_output.get("resolved_concept_name"),
                    "adaptive_path_resolved_domain": adaptive_path_validation_output.get("resolved_domain"),
                    "adaptive_path_fallback_used": adaptive_path_validation_output.get("fallback_used"),
                    "adaptive_path_validation_reason": adaptive_path_validation_output.get("reason"),
                    "adaptive_path_validation_result": get_adaptive_path_validation_summary(
                        adaptive_path_output,
                        adaptive_path_validation_output,
                    ),
                    "frontend_path_output": frontend_path_output,
                    "adaptive_path_strategy": (
                        adaptive_path_output.get("recommended_strategy")
                        if isinstance(adaptive_path_output, dict)
                        else None
                    ),
                    "adaptive_path_difficulty": (
                        adaptive_path_output.get("recommended_difficulty")
                        if isinstance(adaptive_path_output, dict)
                        else None
                    ),
                    "path_ranker_status": (
                        learned_path_ranker_output.get("status")
                        if isinstance(learned_path_ranker_output, dict)
                        else None
                    ),
                    "path_ranker_action": (
                        learned_path_ranker_output.get("recommended_action")
                        if isinstance(learned_path_ranker_output, dict)
                        else None
                    ),
                    "path_ranker_fallback": (
                        learned_path_ranker_output.get("fallback_used")
                        if isinstance(learned_path_ranker_output, dict)
                        else None
                    ),
                    "bridge_agreement": (
                        adaptive_policy_bridge_output.get("agreement")
                        if isinstance(adaptive_policy_bridge_output, dict)
                        else None
                    ),
                    "bridge_override_allowed": (
                        adaptive_policy_bridge_output.get("override_allowed")
                        if isinstance(adaptive_policy_bridge_output, dict)
                        else None
                    ),
                    "bridge_recommendation": (
                        adaptive_policy_bridge_output.get("final_recommendation")
                        if isinstance(adaptive_policy_bridge_output, dict)
                        else None
                    ),
                    "xai_pressure": (
                        feature_contribution_output.get("decision_pressure_label")
                        if isinstance(feature_contribution_output, dict)
                        else None
                    ),
                    "xai_top_factors": (
                        [
                            factor.get("feature")
                            for factor in feature_contribution_output.get("top_factors", [])
                        ]
                        if isinstance(feature_contribution_output, dict)
                        else []
                    ),
                    "notebook_summary": (
                        learner_notebook_memory_output.get("notebook_summary")
                        if isinstance(learner_notebook_memory_output, dict)
                        else None
                    ),
                    "next_practice_queue": (
                        learner_notebook_memory_output.get("next_practice_queue")
                        if isinstance(learner_notebook_memory_output, dict)
                        else []
                    ),
                    "teaching_view": (
                        evidence_aware_teaching_strategy_output.get("teaching_view")
                        if isinstance(evidence_aware_teaching_strategy_output, dict)
                        else None
                    ),
                    "frontend_selected_view": (
                        frontend_teaching_view_output.get("selected_teaching_view")
                        if isinstance(frontend_teaching_view_output, dict)
                        else None
                    ),
                    "frontend_selected_display_type": (
                        frontend_teaching_view_output.get("selected_view", {}).get("display_type")
                        if isinstance(frontend_teaching_view_output, dict)
                        else None
                    ),
                    "frontend_view_adapter_status": (
                        frontend_teaching_view_output.get("status")
                        if isinstance(frontend_teaching_view_output, dict)
                        else None
                    ),
                    "assessment_types": (
                        evidence_aware_teaching_strategy_output.get("assessment_types")
                        if isinstance(evidence_aware_teaching_strategy_output, dict)
                        else []
                    ),
                    "fallback_views": (
                        evidence_aware_teaching_strategy_output.get("fallback_views")
                        if isinstance(evidence_aware_teaching_strategy_output, dict)
                        else []
                    ),
                    "next_activity": (
                        evidence_aware_teaching_strategy_output.get("next_activity")
                        if isinstance(evidence_aware_teaching_strategy_output, dict)
                        else None
                    ),
                    "progression_action": (
                        evidence_aware_teaching_strategy_output.get("progression_action")
                        if isinstance(evidence_aware_teaching_strategy_output, dict)
                        else None
                    ),
                    "training_log_status": (
                        teaching_strategy_training_log_output.get("status")
                        if isinstance(teaching_strategy_training_log_output, dict)
                        else None
                    ),
                    "model_teaching_view": (
                        model_based_teaching_strategy_output.get("model_teaching_view")
                        if isinstance(model_based_teaching_strategy_output, dict)
                        else None
                    ),
                    "model_progression_action": (
                        model_based_teaching_strategy_output.get("model_progression_action")
                        if isinstance(model_based_teaching_strategy_output, dict)
                        else None
                    ),

                    "progression_model_status": (
                        model_based_teaching_strategy_output.get("progression_model_status")
                        if isinstance(model_based_teaching_strategy_output, dict)
                        else None
                    ),
                    "progression_model_reason": (
                        model_based_teaching_strategy_output.get("progression_model_reason")
                        if isinstance(model_based_teaching_strategy_output, dict)
                        else None
                    ),
                    "model_teaching_view_confidence": (
                        model_based_teaching_strategy_output.get("teaching_view_confidence")
                        if isinstance(model_based_teaching_strategy_output, dict)
                        else None
                    ),
                    "model_comparison_log_status": (
                        teaching_strategy_model_comparison_log_output.get("status")
                        if isinstance(teaching_strategy_model_comparison_log_output, dict)
                        else None
                    ),
                    "reward_persistence_status": (
                        reward_persistence_output.get("status")
                        if isinstance(reward_persistence_output, dict)
                        else None
                    ),
                    "reward_persistence_mode": (
                        reward_persistence_output.get("mode")
                        if isinstance(reward_persistence_output, dict)
                        else None
                    ),
                    "total_xp": (
                        reward_persistence_output.get("total_xp")
                        if isinstance(reward_persistence_output, dict)
                        else None
                    ),
                    "daily_xp": (
                        reward_persistence_output.get("daily_xp")
                        if isinstance(reward_persistence_output, dict)
                        else None
                    ),
                    "weekly_xp": (
                        reward_persistence_output.get("weekly_xp")
                        if isinstance(reward_persistence_output, dict)
                        else None
                    ),
                    "current_level": (
                        reward_persistence_output.get("current_level")
                        if isinstance(reward_persistence_output, dict)
                        else None
                    ),
                    "current_streak": (
                        reward_persistence_output.get("current_streak")
                        if isinstance(reward_persistence_output, dict)
                        else None
                    ),
                    "longest_streak": (
                        reward_persistence_output.get("longest_streak")
                        if isinstance(reward_persistence_output, dict)
                        else None
                    ),
                    "debug_evaluation_status": (
                        debug_evaluation_output.get("status")
                        if isinstance(debug_evaluation_output, dict)
                        else None
                    ),
                    "debug_evaluation_score": (
                        debug_evaluation_output.get("overall_score")
                        if isinstance(debug_evaluation_output, dict)
                        else None
                    ),
                    "debug_evaluation_label": (
                        debug_evaluation_output.get("quality_label")
                        if isinstance(debug_evaluation_output, dict)
                        else None
                    ),
                    "debug_evaluation_mode": debug_evaluation_mode,
                    "teaching_strategy_agreement": teaching_strategy_agreement,
                    "assessment_question_count": assessment_output.get("question_count"),
                    "assessment_frontend_ready": assessment_output.get("frontend_ready"),
                    "assessment_frontend_components": assessment_output.get("frontend_components_used", []),
                    "expanded_question_types_added": assessment_output.get("expanded_question_types_added", []),
                    "structured_evaluation_status": (
                        structured_evaluation_output.get("status")
                        if isinstance(structured_evaluation_output, dict)
                        else None
                    ),
                    "structured_question_count": (
                        structured_evaluation_output.get("structured_question_count")
                        if isinstance(structured_evaluation_output, dict)
                        else None
                    ),
                    "structured_question_types": (
                        structured_evaluation_output.get("structured_question_types", [])
                        if isinstance(structured_evaluation_output, dict)
                        else []
                    ),
                    "promotion_confidence": (
                        progression_reward_output.get("progression_result", {}).get("promotion_confidence")
                        if isinstance(progression_reward_output, dict)
                        else None
                    ),
                    "promotion_allowed": (
                        progression_reward_output.get("progression_result", {}).get("promotion_allowed")
                        if isinstance(progression_reward_output, dict)
                        else None
                    ),
                    "level_up_allowed": (
                        progression_reward_output.get("progression_result", {}).get("level_up_allowed")
                        if isinstance(progression_reward_output, dict)
                        else None
                    ),
                    "concept_cleared": (
                        progression_reward_output.get("progression_result", {}).get("concept_cleared")
                        if isinstance(progression_reward_output, dict)
                        else None
                    ),
                    "reward_xp_awarded": (
                        progression_reward_output.get("reward_state", {}).get("xp_awarded")
                        if isinstance(progression_reward_output, dict)
                        else None
                    ),
                    "streak_updated": (
                        progression_reward_output.get("reward_state", {}).get("streak_updated")
                        if isinstance(progression_reward_output, dict)
                        else None
                    ),
                    "celebration_type": (
                        progression_reward_output.get("celebration", {}).get("type")
                        if isinstance(progression_reward_output, dict)
                        else None
                    ),
                    "celebration_message": (
                        progression_reward_output.get("celebration", {}).get("message")
                        if isinstance(progression_reward_output, dict)
                        else None
                    ),
                    "evaluation_score": evaluation_output.get("overall_score"),
                    "final_action": multi_evidence_output.get("final_action"),
                    "dominant_mistake_type": (
                        mistake_analysis_output.get("dominant_mistake_type")
                        if isinstance(mistake_analysis_output, dict)
                        else None
                    ),
                    "mistake_type_counts": (
                        mistake_analysis_output.get("mistake_type_counts", {})
                        if isinstance(mistake_analysis_output, dict)
                        else {}
                    ),
                    "high_severity_mistake_count": (
                        mistake_analysis_output.get("high_severity_count")
                        if isinstance(mistake_analysis_output, dict)
                        else None
                    ),
                    "rubric_evaluation_status": (
                        rubric_evaluation_output.get("status")
                        if isinstance(rubric_evaluation_output, dict)
                        else None
                    ),
                    "rubric_overall_score": (
                        rubric_evaluation_output.get("overall_score")
                        if isinstance(rubric_evaluation_output, dict)
                        else None
                    ),
                    "rubric_verdict": (
                        rubric_evaluation_output.get("verdict")
                        if isinstance(rubric_evaluation_output, dict)
                        else None
                    ),
                    "rubric_mode": rubric_mode,
                    "output_prediction_evaluation_status": (
                        output_prediction_evaluation_output.get("status")
                        if isinstance(output_prediction_evaluation_output, dict)
                        else None
                    ),
                    "output_prediction_evaluation_score": (
                        output_prediction_evaluation_output.get("overall_score")
                        if isinstance(output_prediction_evaluation_output, dict)
                        else None
                    ),
                    "output_prediction_evaluation_label": (
                        output_prediction_evaluation_output.get("quality_label")
                        if isinstance(output_prediction_evaluation_output, dict)
                        else None
                    ),
                    "output_prediction_error_type": (
                        output_prediction_evaluation_output.get("dominant_output_error_type")
                        if isinstance(output_prediction_evaluation_output, dict)
                        else None
                    ),
                    "output_prediction_evaluation_mode": output_prediction_evaluation_mode,
                    "evaluation_fusion_status": (
                        evaluation_fusion_output.get("status")
                        if isinstance(evaluation_fusion_output, dict)
                        else None
                    ),
                    "evaluation_fusion_mode": evaluation_fusion_mode,
                    "fused_score": (
                        evaluation_fusion_output.get("fused_score")
                        if isinstance(evaluation_fusion_output, dict)
                        else None
                    ),
                    "fused_label": (
                        evaluation_fusion_output.get("fused_label")
                        if isinstance(evaluation_fusion_output, dict)
                        else None
                    ),
                    "recommended_learning_signal": (
                        evaluation_fusion_output.get("recommended_learning_signal")
                        if isinstance(evaluation_fusion_output, dict)
                        else None
                    ),
                    "evaluator_agreement": (
                        evaluation_fusion_output.get("evaluator_agreement")
                        if isinstance(evaluation_fusion_output, dict)
                        else None
                    ),
                    "fusion_confidence": (
                        evaluation_fusion_output.get("fusion_confidence")
                        if isinstance(evaluation_fusion_output, dict)
                        else None
                    ),
                    "fusion_confidence_label": (
                        evaluation_fusion_output.get("fusion_confidence_label")
                        if isinstance(evaluation_fusion_output, dict)
                        else None
                    ),
                    "weakest_skill": (
                        evaluation_fusion_output.get("weakest_skill_signal", {}).get("weakest_skill")
                        if isinstance(evaluation_fusion_output, dict)
                        else None
                    ),
                },
                "current_teaching_content": current_teaching_content,
                "frontend_teaching_view_output": frontend_teaching_view_output,
                "assessment": assessment_output,
                "structured_evaluation_output": structured_evaluation_output,
                "progression_reward_output": progression_reward_output,
                "adaptive_hint_output": adaptive_hint_output,
                "learned_hint_output": learned_hint_output,
                "learned_path_ranker_output": learned_path_ranker_output,
                "voice_script_output": voice_script_output,
                "voice_script_bundle": voice_script_bundle,

                "evaluation": evaluation_output,
                "reflection_output": reflection_output,
                "learner_insight_output": learner_insight_output,
                "policy_output": final_policy_output,
                "xai": xai_output,
            },
            "current_teaching_content": current_teaching_content,
            "frontend_teaching_view_output": frontend_teaching_view_output,
            "cognitutor_lm_output": cognitutor_lm_output,
            "cognitutor_lm_product_output": cognitutor_lm_output.get("cognitutor_lm_product_output") if isinstance(cognitutor_lm_output, dict) else None,
            "adaptive_hint_output": adaptive_hint_output,
            "learned_hint_output": learned_hint_output,
            "learned_path_ranker_output": learned_path_ranker_output,
            "voice_script_output": voice_script_output,
            "voice_script_bundle": voice_script_bundle,
            "assessment": assessment_output,
            "structured_evaluation_output": structured_evaluation_output,
            "progression_reward_output": progression_reward_output,
            "reward_persistence_output": reward_persistence_output,
            "learner_answers_used": final_learner_answers,
            "evaluation": evaluation_output,
            "rubric_evaluation_output": rubric_evaluation_output,
            "rubric_mode": rubric_mode,
            "debug_evaluation_output": debug_evaluation_output,
            "debug_evaluation_mode": debug_evaluation_mode,
            "output_prediction_evaluation_output": output_prediction_evaluation_output,
            "output_prediction_evaluation_mode": output_prediction_evaluation_mode,
            "evaluation_fusion_output": evaluation_fusion_output,
            "evaluation_fusion_mode": evaluation_fusion_mode,
            "mistake_analysis_output": mistake_analysis_output,
            "learning_signal": learning_signal,
            "learner_profile_used": learner_profile,
            "adapted_decision": adapted_decision,
            "evaluation_evidence": evaluation_evidence,
            "dependency_output": dependency_output,
            "adaptive_path_output": adaptive_path_output,
            "adaptive_path_validation_output": adaptive_path_validation_output,
            "frontend_path_output": frontend_path_output,
            "adaptive_policy_bridge_output": adaptive_policy_bridge_output,

            "multi_evidence_output": multi_evidence_output,
            "policy_output": final_policy_output,
            "teaching_strategy": final_strategy_output,
            "view_performance_output": view_performance_output,
            "feature_contribution_output": feature_contribution_output,
            "learner_notebook_memory_output": learner_notebook_memory_output,
            "evidence_aware_teaching_strategy_output": evidence_aware_teaching_strategy_output,
            "model_based_teaching_strategy_output": model_based_teaching_strategy_output,
            "learned_teaching_strategy_output": learned_teaching_strategy_output,
            "teaching_strategy_agreement": teaching_strategy_agreement,
            "teaching_strategy_training_log_output": teaching_strategy_training_log_output,
            "teaching_strategy_model_comparison_log_output": teaching_strategy_model_comparison_log_output,
            "xai": xai_output,
            "status": "success",
            "rl_log_output": rl_log_output,
            "tutor_agent_output": tutor_agent_output,
            "evaluator_agent_output": evaluator_agent_output,
            "decision_agent_output": decision_agent_output,
        }

    except Exception as e:
        return {
            "learner_id": learner_id,
            "timestamp": now_iso(),
            "status": "error",
            "error": str(e),
        }
    finally:
        conn.close()




# =========================
# CLI
# =========================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--learner_id", type=str, required=True)
    parser.add_argument("--learner_profile", type=str, default=None)
    parser.add_argument("--db_path", type=str, default=str(DB_PATH))
    parser.add_argument(
        "--reward_dry_run",
        action="store_true",
        help="Run reward persistence in dry-run mode without writing XP/streak to DB.",
    )

    args = parser.parse_args()

    output = run_integrated_tutor_once(
        learner_id=args.learner_id,
        learner_profile=args.learner_profile,
        db_path=args.db_path,
        reward_dry_run=args.reward_dry_run,
    )

    print(json.dumps(output, indent=2, default=str))
