import json
import sqlite3
from datetime import datetime, UTC
from typing import Dict, Any, Optional, List, Tuple

from tutor.strategy.config import STRATEGY_THRESHOLDS, STRATEGY_WEIGHTS


# ============================================================
# Basic loaders
# ============================================================

def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    try:
        value = float(value)
    except Exception:
        value = 0.0

    return max(low, min(high, value))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _unique(items: List[str]) -> List[str]:
    seen = set()
    output = []

    for item in items:
        if item is None:
            continue

        key = str(item).strip().lower()

        if not key:
            continue

        if key not in seen:
            output.append(str(item))
            seen.add(key)

    return output


def load_mastery_for_concept(
    conn: sqlite3.Connection,
    student_id: str,
    concept_id: str,
) -> float:
    """
    Backward-compatible mastery loader.

    Supports older schema:
        knowledge_state.state_json with {"mastery": {...}}

    If missing, returns 0.0.
    """
    try:
        cur = conn.execute(
            "SELECT state_json FROM knowledge_state WHERE student_id = ?",
            (student_id,),
        )
        row = cur.fetchone()

        if not row or not row[0]:
            return 0.0

        state = json.loads(row[0])
        if state.get("schema_version") == "kt_v2" and isinstance(state.get("concepts"), dict):
            mastery_map = {
                item_id: item.get("mastery")
                for item_id, item in state["concepts"].items()
                if isinstance(item, dict)
            }
        else:
            mastery_map = state.get("mastery", state)

        return _safe_float(mastery_map.get(str(concept_id), 0.0), 0.0)

    except Exception:
        return 0.0


def load_decay_for_concept(
    conn: sqlite3.Connection,
    student_id: str,
    concept_id: str,
) -> float:
    try:
        cur = conn.execute(
            """
            SELECT decay_json
            FROM decay_state
            WHERE learner_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (student_id,),
        )

        row = cur.fetchone()

        if not row or not row[0]:
            return 0.0

        decay_data = json.loads(row[0])

        return _safe_float(decay_data.get(str(concept_id), 0.0), 0.0)

    except Exception:
        return 0.0


def load_review_priority_for_concept(
    conn: sqlite3.Connection,
    student_id: str,
    concept_id: str,
) -> float:
    try:
        cur = conn.execute(
            """
            SELECT priority_json
            FROM decay_state
            WHERE learner_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (student_id,),
        )

        row = cur.fetchone()

        if not row or not row[0]:
            return 0.0

        priority_data = json.loads(row[0])

        return _safe_float(priority_data.get(str(concept_id), 0.0), 0.0)

    except Exception:
        return 0.0


def load_behaviour_signal(
    conn: sqlite3.Connection,
    student_id: str,
    concept_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Backward-compatible behaviour loader.

    Keeps old function name, but fixes the old parameter mismatch issue.
    """
    try:
        cur = conn.execute(
            """
            SELECT behavior_json
            FROM behaviour_state
            WHERE student_id = ?
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (student_id,),
        )

        row = cur.fetchone()

        if not row or not row[0]:
            return {}

        return json.loads(row[0])

    except Exception:
        return {}


# ============================================================
# Old baseline strategy logic
# Kept for compatibility
# ============================================================

def _medium_band_score(mastery: float, low: float, high: float) -> float:
    midpoint = (low + high) / 2.0
    half_width = (high - low) / 2.0

    if half_width <= 0:
        return 0.0

    dist = abs(mastery - midpoint)
    score = 1.0 - (dist / half_width)

    return _clamp(score)


def compute_strategy_scores(
    mastery: float,
    decay: float,
    review_priority: float = 0.0,
    behaviour: Optional[Dict[str, Any]] = None,
) -> Dict[str, float]:
    """
    Old baseline scoring.

    Status:
        WORKING BASELINE / PARTIAL UPGRADE

    Kept so older code does not break.
    """
    behaviour = behaviour or {}

    mastery = _clamp(mastery)
    decay = _clamp(decay)
    review_priority = _clamp(review_priority)

    mastery_low = STRATEGY_THRESHOLDS.get("mastery_low", 0.45)
    mastery_high = STRATEGY_THRESHOLDS.get("mastery_high", 0.80)

    mastery_w = STRATEGY_WEIGHTS.get("mastery", 0.65)
    decay_w = STRATEGY_WEIGHTS.get("decay", 0.35)

    forget_signal = max(decay, review_priority)

    definition_score = (
        mastery_w * (1.0 - mastery)
        + decay_w * (1.0 - forget_signal) * 0.3
    )

    worked_example_score = (
        mastery_w * _medium_band_score(mastery, mastery_low, mastery_high)
        + decay_w * (1.0 - forget_signal) * 0.2
    )

    practice_score = (
        mastery_w * mastery
        + decay_w * (1.0 - forget_signal) * 0.4
    )

    revision_score = (
        decay_w * forget_signal
        + mastery_w * (1.0 - mastery) * 0.2
    )

    fatigue = _clamp(_safe_float(behaviour.get("fatigue", 0.0), 0.0))
    confidence = _clamp(_safe_float(behaviour.get("confidence", 0.0), 0.0))

    definition_score += fatigue * 0.05
    worked_example_score += fatigue * 0.08
    practice_score -= fatigue * 0.10
    revision_score += fatigue * 0.05

    practice_score += confidence * 0.08
    definition_score -= confidence * 0.03

    return {
        "definition": round(_clamp(definition_score), 6),
        "worked_example": round(_clamp(worked_example_score), 6),
        "practice": round(_clamp(practice_score), 6),
        "revision": round(_clamp(revision_score), 6),
    }


def choose_teaching_strategy(
    mastery: float,
    decay: float = 0.0,
    review_priority: float = 0.0,
    behaviour: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str, Dict[str, float]]:
    scores = compute_strategy_scores(
        mastery=mastery,
        decay=decay,
        review_priority=review_priority,
        behaviour=behaviour,
    )

    strategy = max(scores, key=scores.get)
    reason = f"selected by highest strategy score ({strategy}={scores[strategy]:.3f})"

    return strategy, reason, scores


def log_teaching_strategy(
    conn: sqlite3.Connection,
    decision: Dict[str, Any],
) -> None:
    """
    Backward-compatible logger.

    Expected existing table:
        teaching_strategy_log(
            learner_id,
            concept_id,
            strategy,
            strategy_source,
            timestamp
        )
    """
    try:
        conn.execute(
            """
            INSERT INTO teaching_strategy_log
            (learner_id, concept_id, strategy, strategy_source, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                decision.get("student_id") or decision.get("learner_id"),
                decision.get("concept_id"),
                decision.get("teaching_strategy")
                or decision.get("teaching_view")
                or decision.get("final_strategy"),
                decision.get("reason", ""),
                decision.get("generated_at", _now_iso()),
            ),
        )
        conn.commit()

    except Exception as e:
        print("TEACHING STRATEGY LOG ERROR:", e)


def recommend_teaching_strategy(
    conn: sqlite3.Connection,
    student_id: str,
    concept_id: str,
) -> Dict[str, Any]:
    """
    Old public function.

    Kept for existing code compatibility.
    """
    mastery = load_mastery_for_concept(conn, student_id, concept_id)
    decay = load_decay_for_concept(conn, student_id, concept_id)
    review_priority = load_review_priority_for_concept(conn, student_id, concept_id)
    behaviour = load_behaviour_signal(conn, student_id, concept_id)

    strategy, reason, scores = choose_teaching_strategy(
        mastery=mastery,
        decay=decay,
        review_priority=review_priority,
        behaviour=behaviour,
    )

    decision = {
        "student_id": str(student_id),
        "learner_id": str(student_id),
        "concept_id": str(concept_id),
        "teaching_strategy": strategy,
        "final_strategy": strategy,
        "reason": reason,
        "evidence": {
            "mastery": mastery,
            "decay": decay,
            "review_priority": review_priority,
            "behaviour": behaviour,
            "strategy_scores": scores,
        },
        "generated_at": _now_iso(),
    }

    log_teaching_strategy(conn, decision)

    return decision


# ============================================================
# New evidence-aware teaching strategy selector
# ============================================================

def _extract_policy_data(policy_output: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(policy_output, dict):
        return {}

    return policy_output.get("data", policy_output)


def _extract_behaviour_data(behaviour_state: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(behaviour_state, dict):
        return {}

    data = behaviour_state.get("data", behaviour_state)

    if isinstance(data, dict) and isinstance(data.get("data"), dict):
        data = data.get("data", {})

    return data if isinstance(data, dict) else {}


def _extract_weak_assessment_types(evaluation_output: Dict[str, Any]) -> List[str]:
    weak = []

    if not isinstance(evaluation_output, dict):
        return weak

    for item in evaluation_output.get("results", []):
        score = _safe_float(item.get("score"), 0.0)
        assessment_type = item.get("assessment_type")

        if assessment_type and score < 0.75:
            weak.append(str(assessment_type))

    if not weak:
        feedback_summary = str(evaluation_output.get("feedback_summary", "")).lower()

        if "output" in feedback_summary:
            weak.append("output_prediction")

        if "debug" in feedback_summary:
            weak.append("debug")

        if "explanation" in feedback_summary:
            weak.append("short_explanation")

        if "transfer" in feedback_summary:
            weak.append("transfer")

    return _unique(weak)


def _extract_strengths(evaluation_output: Dict[str, Any]) -> List[str]:
    strengths = []

    if not isinstance(evaluation_output, dict):
        return strengths

    for item in evaluation_output.get("results", []):
        score = _safe_float(item.get("score"), 0.0)
        assessment_type = item.get("assessment_type")

        if assessment_type and score >= 0.75:
            strengths.append(str(assessment_type))

    return _unique(strengths)


def _extract_view_reward(view_performance_output: Dict[str, Any]) -> float:
    if not isinstance(view_performance_output, dict):
        return 0.5

    logged = view_performance_output.get("logged", {})

    return _safe_float(
        logged.get("reward", view_performance_output.get("reward", 0.5)),
        0.5,
    )


def _extract_last_view(view_performance_output: Dict[str, Any]) -> Optional[str]:
    if not isinstance(view_performance_output, dict):
        return None

    logged = view_performance_output.get("logged", {})

    view = logged.get("teaching_view") or view_performance_output.get("teaching_view")

    return str(view) if view else None


def _extract_notebook_weaknesses(
    learner_notebook_memory_output: Dict[str, Any],
) -> List[str]:
    if not isinstance(learner_notebook_memory_output, dict):
        return []

    weakness_candidates = []
    weakness_candidates.extend(learner_notebook_memory_output.get("weak_assessment_types", []))
    weakness_candidates.extend(learner_notebook_memory_output.get("memory_weaknesses", []))
    weakness_candidates.extend(learner_notebook_memory_output.get("weaknesses", []))

    return _unique(
        [
            str(x)
            for x in weakness_candidates
        ]
    )


def _extract_memory_weaknesses(
    learner_notebook_memory_output: Dict[str, Any],
) -> List[str]:
    return _extract_notebook_weaknesses(learner_notebook_memory_output)


def _extract_xai_top_factors(xai_output: Dict[str, Any]) -> List[str]:
    if not isinstance(xai_output, dict):
        return []

    evidence = xai_output.get("data", {}).get("evidence", {})
    feature_contributions = evidence.get("feature_contributions", {})

    top_factors = []

    for factor in feature_contributions.get("top_factors", []):
        if isinstance(factor, dict) and factor.get("feature"):
            top_factors.append(str(factor.get("feature")))

    return _unique(top_factors)


def _difficulty_from_policy(policy_output: Dict[str, Any]) -> str:
    policy_data = _extract_policy_data(policy_output)
    difficulty = str(policy_data.get("difficulty", "medium")).lower()

    if difficulty in {"easy", "medium", "hard"}:
        return difficulty

    if difficulty == "difficult":
        return "hard"

    return "medium"


def _strategy_from_policy(policy_output: Dict[str, Any]) -> str:
    policy_data = _extract_policy_data(policy_output)
    strategy = str(policy_data.get("strategy", "practice")).lower()

    if strategy in {"remedial", "practice", "advanced", "revision"}:
        return strategy

    if strategy in {"definition", "worked_example"}:
        return "remedial"

    return "practice"


def _adjust_difficulty(
    base_difficulty: str,
    evaluation_score: float,
    behaviour_risk: float,
    view_reward: float,
    weak_types: List[str],
    strengths: List[str],
) -> str:
    """
    Level-aware progression:

    - Strong understanding -> level up.
    - Partial understanding -> same level.
    - Weak understanding -> same/lower level and different view.
    """
    difficulty_order = ["easy", "medium", "hard"]

    if base_difficulty not in difficulty_order:
        base_difficulty = "medium"

    idx = difficulty_order.index(base_difficulty)

    strong_understanding = (
        evaluation_score >= 0.80
        and behaviour_risk < 0.45
        and view_reward >= 0.55
    )

    partial_understanding = 0.50 <= evaluation_score < 0.80

    weak_understanding = (
        evaluation_score < 0.50
        or behaviour_risk >= 0.70
    )

    if strong_understanding:
        return difficulty_order[min(idx + 1, len(difficulty_order) - 1)]

    if weak_understanding:
        return difficulty_order[max(idx - 1, 0)]

    if partial_understanding:
        return base_difficulty

    return base_difficulty


def _behaviour_risk(behaviour_state: Dict[str, Any]) -> float:
    behaviour_data = _extract_behaviour_data(behaviour_state)

    explicit_risk = behaviour_data.get("behavior_risk", behaviour_data.get("behaviour_risk"))
    if explicit_risk is not None:
        return _clamp(_safe_float(explicit_risk, 0.5))

    behavior_score = _safe_float(
        behaviour_data.get("behavior_score", behaviour_data.get("behaviour_score", 0.5)),
        0.5,
    )

    wrong_rate = _safe_float(behaviour_data.get("wrong_rate"), 0.0)
    slow_rate = _safe_float(behaviour_data.get("slow_rate"), 0.0)
    low_confidence_rate = _safe_float(behaviour_data.get("low_confidence_rate"), 0.0)
    hint_rate = _safe_float(behaviour_data.get("hint_rate"), 0.0)

    risk = (
        0.40 * (1.0 - behavior_score)
        + 0.25 * wrong_rate
        + 0.15 * slow_rate
        + 0.15 * low_confidence_rate
        + 0.05 * hint_rate
    )

    return _clamp(risk)


def _behaviour_risk_label(behaviour_state: Dict[str, Any], behaviour_risk: float) -> str:
    behaviour_data = _extract_behaviour_data(behaviour_state)
    label = str(
        behaviour_data.get("behavior_risk_label")
        or behaviour_data.get("behaviour_risk_label")
        or ""
    ).strip()

    if label:
        return label

    if behaviour_risk >= 0.70:
        return "high_risk"

    if behaviour_risk >= 0.40:
        return "medium_risk"

    return "low_risk"


def _extract_mastery_score(
    policy_output: Dict[str, Any],
    knowledge_state: Optional[Dict[str, Any]],
    concept_id: str,
) -> Optional[float]:
    policy_data = _extract_policy_data(policy_output)

    for key in ["mastery_score", "mastery", "predicted_mastery_last"]:
        if policy_data.get(key) is not None:
            return _clamp(_safe_float(policy_data.get(key), 0.5))

    if isinstance(knowledge_state, dict):
        data = knowledge_state.get("data", knowledge_state)
        if isinstance(data, dict) and isinstance(data.get("data"), dict):
            data = data.get("data", {})
        if isinstance(data, dict):
            for key in ["predicted_mastery_last", "mastery_score", "mastery"]:
                if data.get(key) is not None:
                    return _clamp(_safe_float(data.get(key), 0.5))

            state = data.get("written_state") or data.get("state_json") or data.get("concepts")
            if isinstance(state, str):
                try:
                    state = json.loads(state)
                except Exception:
                    state = {}

            if isinstance(state, dict):
                if state.get("schema_version") == "kt_v2" and isinstance(state.get("concepts"), dict):
                    concept = state["concepts"].get(str(concept_id))
                    if isinstance(concept, dict) and concept.get("mastery") is not None:
                        return _clamp(_safe_float(concept.get("mastery"), 0.5))
                elif state.get(str(concept_id)) is not None:
                    return _clamp(_safe_float(state.get(str(concept_id)), 0.5))

    return None


def _extract_fusion_data(evaluation_fusion_output: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(evaluation_fusion_output, dict):
        return {}
    return evaluation_fusion_output.get("data", evaluation_fusion_output)


def _extract_fused_score(
    evaluation_fusion_output: Optional[Dict[str, Any]],
    evaluation_output: Dict[str, Any],
) -> float:
    fusion = _extract_fusion_data(evaluation_fusion_output)
    return _clamp(
        _safe_float(
            fusion.get("fused_score", evaluation_output.get("overall_score", evaluation_output.get("score", 0.5))),
            0.5,
        )
    )


def _extract_fused_label(
    evaluation_fusion_output: Optional[Dict[str, Any]],
    evaluation_output: Dict[str, Any],
) -> str:
    fusion = _extract_fusion_data(evaluation_fusion_output)
    label = str(
        fusion.get("fused_label")
        or fusion.get("recommended_learning_signal")
        or evaluation_output.get("verdict")
        or ""
    ).strip()
    return label or "unknown"


def _extract_weakest_skill(
    evaluation_fusion_output: Optional[Dict[str, Any]],
    evaluation_output: Dict[str, Any],
    weak_types: List[str],
) -> Optional[str]:
    fusion = _extract_fusion_data(evaluation_fusion_output)
    weakest_signal = fusion.get("weakest_skill_signal", {})

    if isinstance(weakest_signal, dict) and weakest_signal.get("weakest_skill"):
        return str(weakest_signal.get("weakest_skill"))

    if fusion.get("weakest_skill"):
        return str(fusion.get("weakest_skill"))

    if weak_types:
        return weak_types[0]

    for item in evaluation_output.get("results", []):
        if item.get("assessment_type"):
            return str(item.get("assessment_type"))

    return None


def _extract_dominant_mistake_type(
    mistake_analysis_output: Optional[Dict[str, Any]],
    evaluation_output: Dict[str, Any],
) -> Optional[str]:
    if isinstance(mistake_analysis_output, dict):
        for key in ["dominant_mistake_type", "mistake_type", "classified_mistake_type"]:
            if mistake_analysis_output.get(key):
                return str(mistake_analysis_output.get(key))

        data = mistake_analysis_output.get("data", {})
        if isinstance(data, dict):
            for key in ["dominant_mistake_type", "mistake_type", "classified_mistake_type"]:
                if data.get(key):
                    return str(data.get(key))

    for item in evaluation_output.get("results", []):
        if item.get("mistake_type"):
            return str(item.get("mistake_type"))

    return None


def _review_due_for_concept(
    forgetting_state: Optional[Dict[str, Any]],
    concept_id: str,
) -> bool:
    if not isinstance(forgetting_state, dict):
        return False

    data = forgetting_state.get("data", forgetting_state)
    queue = data.get("review_queue", []) if isinstance(data, dict) else []
    priority = data.get("review_priority", {}) if isinstance(data, dict) else {}

    queue_strings = {str(item) for item in queue if item is not None}
    if str(concept_id) in queue_strings:
        return True

    if isinstance(priority, dict):
        return _safe_float(priority.get(str(concept_id)), 0.0) >= 0.65

    return bool(queue)


def _reduce_difficulty(difficulty: str) -> str:
    if difficulty == "hard":
        return "medium"
    if difficulty == "medium":
        return "easy"
    return "easy"


def _choose_teaching_view(
    difficulty: str,
    strategy: str,
    weak_types: List[str],
    strengths: List[str],
    view_reward: float,
    last_view: Optional[str],
    xai_top_factors: List[str],
) -> str:
    """
    Select exactly one view to show now.
    Do not dump all concept sections at once.
    """

    weak_set = set(weak_types)
    strength_set = set(strengths)

    # Code weakness should move to code/debug views.
    if "debug" in weak_set:
        return "debug_view"

    if "output_prediction" in weak_set:
        return "code_view"

    if "syntax" in weak_set:
        return "syntax_view"

    if "short_explanation" in weak_set or "explanation" in weak_set:
        if last_view == "definition_view" and view_reward < 0.55:
            return "step_by_step_view"
        return "definition_view"

    if "transfer" in weak_set:
        return "transfer_view"

    # Low reward means previous view did not work; switch variation.
    if view_reward < 0.45 and last_view:
        fallback_map = {
            "definition_view": "step_by_step_view",
            "step_by_step_view": "analogy_view",
            "analogy_view": "simple_code_view",
            "simple_code_view": "revision_view",
            "code_view": "debug_view",
            "debug_view": "misconception_view",
            "misconception_view": "step_by_step_view",
        }

        return fallback_map.get(last_view, "step_by_step_view")

    # Difficulty-driven default view.
    if strategy == "remedial" or difficulty == "easy":
        return "definition_view"

    if strategy == "advanced" or difficulty == "hard":
        if "transfer" in strength_set or "explanation" in strength_set:
            return "challenge_view"
        return "transfer_view"

    if strategy == "revision":
        return "revision_view"

    # Practice / medium default.
    return "code_view"


def _assessment_types_for_view(
    teaching_view: str,
    difficulty: str,
    weak_types: List[str],
) -> List[str]:
    """
    Assessment type must match teaching view and level.
    """
    view_map = {
        "definition_view": ["mcq", "short_explanation"],
        "syntax_view": ["syntax_completion", "mcq"],
        "step_by_step_view": ["mcq", "short_explanation"],
        "analogy_view": ["short_explanation", "mcq"],
        "simple_code_view": ["output_prediction", "mcq"],
        "code_view": ["output_prediction", "short_explanation"],
        "debug_view": ["debug", "output_prediction"],
        "misconception_view": ["mcq", "debug"],
        "challenge_view": ["debug", "transfer", "code_writing"],
        "transfer_view": ["transfer", "short_explanation"],
        "revision_view": ["mcq", "flashcard_recall"],
        "flashcard_view": ["flashcard_recall", "mcq"],
    }

    assessment_types = view_map.get(teaching_view, ["mcq", "short_explanation"])

    for weak_type in weak_types:
        if weak_type not in assessment_types:
            assessment_types.append(weak_type)

    if difficulty == "easy":
        allowed = {
            "mcq",
            "short_explanation",
            "syntax_completion",
            "output_prediction",
            "flashcard_recall",
        }
        assessment_types = [x for x in assessment_types if x in allowed]

    elif difficulty == "medium":
        allowed = {
            "mcq",
            "short_explanation",
            "output_prediction",
            "debug",
            "transfer",
            "syntax_completion",
            "flashcard_recall",
        }
        assessment_types = [x for x in assessment_types if x in allowed]

    else:
        # hard
        if "transfer" not in assessment_types:
            assessment_types.append("transfer")
        if "debug" not in assessment_types:
            assessment_types.append("debug")

    return _unique(assessment_types)[:4]


def _fallback_views_for(
    teaching_view: str,
    difficulty: str,
    weak_types: List[str],
) -> List[str]:
    if teaching_view == "definition_view":
        return ["step_by_step_view", "analogy_view", "simple_code_view", "revision_view"]

    if teaching_view == "step_by_step_view":
        return ["analogy_view", "simple_code_view", "revision_view", "flashcard_view"]

    if teaching_view == "code_view":
        return ["debug_view", "step_by_step_view", "misconception_view", "revision_view"]

    if teaching_view == "debug_view":
        return ["code_view", "misconception_view", "step_by_step_view", "revision_view"]

    if teaching_view == "misconception_view":
        return ["step_by_step_view", "code_view", "revision_view"]

    if teaching_view == "challenge_view":
        return ["transfer_view", "debug_view", "code_view"]

    if teaching_view == "transfer_view":
        return ["challenge_view", "code_view", "debug_view"]

    return ["step_by_step_view", "analogy_view", "revision_view"]


def _content_focus(
    weak_types: List[str],
    teaching_view: str,
    xai_top_factors: List[str],
) -> List[str]:
    focus = []

    focus.extend(weak_types)

    if teaching_view == "definition_view":
        focus.append("concept_meaning")

    if teaching_view == "syntax_view":
        focus.append("syntax")

    if teaching_view in {"code_view", "simple_code_view"}:
        focus.append("code_tracing")

    if teaching_view == "debug_view":
        focus.append("debugging")

    if teaching_view == "misconception_view":
        focus.append("misconception_correction")

    if teaching_view in {"challenge_view", "transfer_view"}:
        focus.append("application")

    if "view_reward_need" in xai_top_factors:
        focus.append("change_teaching_view")

    if "evaluation_need" in xai_top_factors:
        focus.append("target_recent_errors")

    return _unique(focus)


def _explanation_mode_for_view(teaching_view: str) -> str:
    if teaching_view in {"code_view", "simple_code_view"}:
        return "code"

    if teaching_view == "debug_view":
        return "debug"

    if teaching_view == "analogy_view":
        return "analogy"

    if teaching_view in {"revision_view", "flashcard_view"}:
        return "revision"

    if teaching_view in {"challenge_view", "transfer_view"}:
        return "step_by_step"

    if teaching_view in {"step_by_step_view", "misconception_view"}:
        return "step_by_step"

    return "simple"


def _next_activity_for(
    difficulty: str,
    teaching_view: str,
    weak_types: List[str],
    evaluation_score: float,
) -> str:
    weak_set = set(weak_types)

    if "debug" in weak_set or teaching_view == "debug_view":
        return "short code tracing and debugging practice"

    if "output_prediction" in weak_set or teaching_view == "code_view":
        return "guided output prediction practice"

    if teaching_view == "definition_view":
        return "basic concept check with simple MCQ or short explanation"

    if teaching_view == "step_by_step_view":
        return "step-by-step guided concept check"

    if teaching_view == "analogy_view":
        return "explain the concept back using the analogy"

    if teaching_view == "challenge_view":
        return "challenge problem with feedback"

    if teaching_view == "transfer_view":
        return "real-world transfer question"

    if difficulty == "hard":
        return "hard mixed practice and transfer task"

    return "matched practice for current teaching view"


def _progression_decision(
    difficulty: str,
    evaluation_score: float,
    behaviour_risk: float,
    view_reward: float,
) -> Dict[str, Any]:
    if evaluation_score >= 0.80 and behaviour_risk < 0.45 and view_reward >= 0.55:
        if difficulty == "easy":
            return {
                "progression_action": "level_up_to_medium",
                "next_difficulty": "medium",
            }

        if difficulty == "medium":
            return {
                "progression_action": "level_up_to_hard",
                "next_difficulty": "hard",
            }

        return {
            "progression_action": "advance_concept",
            "next_difficulty": "hard",
        }

    if 0.50 <= evaluation_score < 0.80:
        return {
            "progression_action": "same_level_change_view_or_practice",
            "next_difficulty": difficulty,
        }

    return {
        "progression_action": "same_or_lower_level_change_view",
        "next_difficulty": "easy" if difficulty == "medium" else difficulty,
    }


def recommend_evidence_aware_teaching_strategy(
    learner_id: str,
    concept_id: str,
    concept_name: str = "",
    policy_output: Optional[Dict[str, Any]] = None,
    evaluation_output: Optional[Dict[str, Any]] = None,
    evaluation_fusion_output: Optional[Dict[str, Any]] = None,
    mistake_analysis_output: Optional[Dict[str, Any]] = None,
    behaviour_state: Optional[Dict[str, Any]] = None,
    knowledge_state: Optional[Dict[str, Any]] = None,
    forgetting_state: Optional[Dict[str, Any]] = None,
    view_performance_output: Optional[Dict[str, Any]] = None,
    learner_notebook_memory_output: Optional[Dict[str, Any]] = None,
    xai_output: Optional[Dict[str, Any]] = None,
    adaptive_path_output: Optional[Dict[str, Any]] = None,
    conn: Optional[sqlite3.Connection] = None,
    log: bool = True,
) -> Dict[str, Any]:
    """
    New teaching strategy selector.

    Purpose:
    - Chooses one teaching view at a time.
    - Matches assessment difficulty/type to taught level/view.
    - Moves easy -> medium -> hard only when learner understands.
    - If learner fails, keeps same/lower level and changes view.
    """

    policy_output = policy_output or {}
    evaluation_output = evaluation_output or {}
    evaluation_fusion_output = evaluation_fusion_output or {}
    mistake_analysis_output = mistake_analysis_output or {}
    behaviour_state = behaviour_state or {}
    knowledge_state = knowledge_state or {}
    forgetting_state = forgetting_state or {}
    view_performance_output = view_performance_output or {}
    learner_notebook_memory_output = learner_notebook_memory_output or {}
    xai_output = xai_output or {}
    adaptive_path_output = adaptive_path_output or {}

    base_difficulty = _difficulty_from_policy(policy_output)
    policy_strategy = _strategy_from_policy(policy_output)

    evaluation_score = _safe_float(
        evaluation_output.get("overall_score", evaluation_output.get("score", 0.5)),
        0.5,
    )
    fused_score = _extract_fused_score(evaluation_fusion_output, evaluation_output)
    fused_label = _extract_fused_label(evaluation_fusion_output, evaluation_output)

    weak_types = _extract_weak_assessment_types(evaluation_output)
    strengths = _extract_strengths(evaluation_output)

    notebook_weaknesses = _extract_notebook_weaknesses(learner_notebook_memory_output)
    weak_types = _unique(weak_types + notebook_weaknesses)
    weakest_skill = _extract_weakest_skill(evaluation_fusion_output, evaluation_output, weak_types)
    dominant_mistake_type = _extract_dominant_mistake_type(mistake_analysis_output, evaluation_output)

    if weakest_skill:
        weak_types = _unique([weakest_skill] + weak_types)

    mastery_score = _extract_mastery_score(policy_output, knowledge_state, concept_id)
    review_due = _review_due_for_concept(forgetting_state, concept_id)
    memory_weaknesses = _extract_memory_weaknesses(learner_notebook_memory_output)

    behaviour_risk = _behaviour_risk(behaviour_state)
    behaviour_risk_label = _behaviour_risk_label(behaviour_state, behaviour_risk)
    view_reward = _extract_view_reward(view_performance_output)
    last_view = _extract_last_view(view_performance_output)

    xai_top_factors = _extract_xai_top_factors(xai_output)

    selected_difficulty = _adjust_difficulty(
        base_difficulty=base_difficulty,
        evaluation_score=evaluation_score,
        behaviour_risk=behaviour_risk,
        view_reward=view_reward,
        weak_types=weak_types,
        strengths=strengths,
    )

    if mastery_score is not None:
        if mastery_score < 0.4:
            selected_difficulty = "easy"
        elif mastery_score < 0.7 and selected_difficulty == "hard":
            selected_difficulty = "medium"
        elif mastery_score >= 0.75 and fused_label in {"mastered", "partial_strong", "strong", "success"}:
            selected_difficulty = "hard"

    high_behaviour_risk = behaviour_risk_label == "high_risk" or behaviour_risk >= 0.70

    if high_behaviour_risk:
        selected_difficulty = _reduce_difficulty(selected_difficulty)

    teaching_view = _choose_teaching_view(
        difficulty=selected_difficulty,
        strategy=policy_strategy,
        weak_types=weak_types,
        strengths=strengths,
        view_reward=view_reward,
        last_view=last_view,
        xai_top_factors=xai_top_factors,
    )

    fusion_needs_remediation = fused_label in {
        "needs_reteaching",
        "focused_remediation",
        "needs_remediation",
        "needs_review",
    }

    if review_due:
        teaching_view = "revision_view"
    elif fusion_needs_remediation:
        if weakest_skill == "output_prediction":
            teaching_view = "code_view"
        elif weakest_skill in {"debug", "debug_task"} or dominant_mistake_type == "syntax_misunderstanding":
            teaching_view = "debug_view"
        elif dominant_mistake_type and "misconception" in dominant_mistake_type:
            teaching_view = "misconception_view"
        else:
            teaching_view = "step_by_step_view"
    elif weakest_skill == "output_prediction":
        teaching_view = "code_view"
    elif weakest_skill in {"debug", "debug_task"} or dominant_mistake_type == "syntax_misunderstanding":
        teaching_view = "debug_view"
    elif mastery_score is not None and mastery_score < 0.4:
        teaching_view = "step_by_step_view" if behaviour_risk_label == "high_risk" else "definition_view"
    elif (
        mastery_score is not None
        and mastery_score >= 0.75
        and fused_label in {"mastered", "partial_strong", "strong", "success"}
        and behaviour_risk_label != "high_risk"
    ):
        teaching_view = "challenge_view" if selected_difficulty == "hard" else "transfer_view"

    if high_behaviour_risk and teaching_view in {"challenge_view", "transfer_view"}:
        if review_due:
            teaching_view = "revision_view"
        elif weakest_skill in {"debug", "debug_task", "output_prediction"}:
            teaching_view = "code_view"
        elif dominant_mistake_type and "misconception" in dominant_mistake_type:
            teaching_view = "misconception_view"
        else:
            teaching_view = "step_by_step_view"

    explanation_mode = _explanation_mode_for_view(teaching_view)

    assessment_types = _assessment_types_for_view(
        teaching_view=teaching_view,
        difficulty=selected_difficulty,
        weak_types=weak_types,
    )
    if weakest_skill == "output_prediction" and "output_prediction" not in assessment_types:
        assessment_types.insert(0, "output_prediction")
    if (
        weakest_skill in {"debug", "debug_task"}
        or dominant_mistake_type == "syntax_misunderstanding"
    ) and "debug" not in assessment_types:
        assessment_types.insert(0, "debug")
    if mastery_score is not None and mastery_score < 0.4:
        assessment_types = _unique(["mcq", "explanation_check"] + assessment_types)
    assessment_types = _unique(assessment_types)[:4]

    fallback_views = _fallback_views_for(
        teaching_view=teaching_view,
        difficulty=selected_difficulty,
        weak_types=weak_types,
    )

    content_focus = _content_focus(
        weak_types=weak_types,
        teaching_view=teaching_view,
        xai_top_factors=xai_top_factors,
    )

    next_activity = _next_activity_for(
        difficulty=selected_difficulty,
        teaching_view=teaching_view,
        weak_types=weak_types,
        evaluation_score=evaluation_score,
    )

    progression = _progression_decision(
        difficulty=selected_difficulty,
        evaluation_score=evaluation_score,
        behaviour_risk=behaviour_risk,
        view_reward=view_reward,
    )

    if review_due:
        next_activity = "revision_before_new_content"
        progression = {
            "progression_action": "review",
            "next_difficulty": selected_difficulty,
        }
    elif high_behaviour_risk:
        next_activity = "reteach_with_support"
        progression = {
            "progression_action": "same_level_change_view_or_practice",
            "next_difficulty": selected_difficulty,
        }
    elif fusion_needs_remediation:
        progression = {
            "progression_action": "reteach",
            "next_difficulty": selected_difficulty,
        }
    elif (
        mastery_score is not None
        and mastery_score >= 0.75
        and fused_label in {"mastered", "partial_strong", "strong", "success"}
        and behaviour_risk_label != "high_risk"
    ):
        progression = {
            "progression_action": "level_up" if selected_difficulty != "hard" else "advance_concept",
            "next_difficulty": selected_difficulty,
        }

    progression_action = progression.get("progression_action")
    if progression_action in {"level_up_to_medium", "level_up_to_hard"}:
        progression["progression_action"] = "level_up"
    elif progression_action == "same_or_lower_level_change_view":
        progression["progression_action"] = "reteach"

    reason_parts = [
        f"Policy suggested {policy_strategy} at {base_difficulty} level.",
        f"Evaluation score is {evaluation_score}.",
    ]

    if weak_types:
        reason_parts.append(f"Weak areas: {weak_types}.")

    if strengths:
        reason_parts.append(f"Strengths: {strengths}.")

    if mastery_score is not None:
        reason_parts.append(f"KT mastery is {round(mastery_score, 4)}.")

    reason_parts.append(f"Fusion label is {fused_label} with score {round(fused_score, 4)}.")
    reason_parts.append(f"Behaviour risk is {round(behaviour_risk, 4)} ({behaviour_risk_label}).")
    reason_parts.append(f"Previous view reward is {round(view_reward, 4)}.")

    if weakest_skill:
        reason_parts.append(f"Weakest skill is {weakest_skill}.")

    if dominant_mistake_type:
        reason_parts.append(f"Dominant mistake type is {dominant_mistake_type}.")

    if review_due:
        reason_parts.append("Forgetting evidence shows review is due for this concept.")

    if high_behaviour_risk:
        reason_parts.append("High behaviour risk reduced difficulty and selected a supportive view.")

    if teaching_view:
        reason_parts.append(
            f"Selected {teaching_view} so the learner sees one targeted view instead of all concept content."
        )

    if progression.get("progression_action"):
        reason_parts.append(
            f"Progression action: {progression.get('progression_action')}."
        )

    evidence_used = {
        "mastery_score": mastery_score,
        "behaviour_risk": round(behaviour_risk, 4),
        "behaviour_risk_label": behaviour_risk_label,
        "fused_score": round(fused_score, 4),
        "fused_label": fused_label,
        "weakest_skill": weakest_skill,
        "dominant_mistake_type": dominant_mistake_type,
        "review_due": bool(review_due),
        "weak_assessment_types": weak_types,
        "memory_weaknesses": memory_weaknesses,
        "adaptive_path_selected": adaptive_path_output.get("selected_next_concept"),
        "adaptive_path_strategy": adaptive_path_output.get("recommended_strategy"),
        "view_reward": round(view_reward, 4),
        "last_view": last_view,
    }

    confidence = _clamp(
        0.45
        + (0.15 if mastery_score is not None else 0.0)
        + (0.10 if fused_label != "unknown" else 0.0)
        + (0.10 if weakest_skill else 0.0)
        + (0.05 if behaviour_risk_label else 0.0)
        + (0.05 if review_due else 0.0)
    )

    decision = {
        "status": "success",
        "module": "TeachingStrategySelector",
        "learner_id": str(learner_id),
        "concept_id": str(concept_id),
        "concept_name": concept_name,

        "final_strategy": policy_strategy,
        "difficulty": selected_difficulty,
        "teaching_view": teaching_view,
        "explanation_mode": explanation_mode,

        "content_focus": content_focus,

        "assessment_difficulty": selected_difficulty,
        "assessment_types": assessment_types,

        "fallback_views": fallback_views,
        "next_activity": next_activity,

        "progression_action": progression.get("progression_action"),
        "next_difficulty": progression.get("next_difficulty"),

        "reason": " ".join(reason_parts),
        "confidence": round(confidence, 4),
        "evidence_used": evidence_used,

        "evidence": {
            "base_difficulty": base_difficulty,
            "policy_strategy": policy_strategy,
            "evaluation_score": evaluation_score,
            "fused_score": round(fused_score, 4),
            "fused_label": fused_label,
            "mastery_score": mastery_score,
            "weak_assessment_types": weak_types,
            "weakest_skill": weakest_skill,
            "dominant_mistake_type": dominant_mistake_type,
            "strengths": strengths,
            "behaviour_risk": round(behaviour_risk, 4),
            "behaviour_risk_label": behaviour_risk_label,
            "review_due": bool(review_due),
            "memory_weaknesses": memory_weaknesses,
            "view_reward": round(view_reward, 4),
            "last_view": last_view,
            "xai_top_factors": xai_top_factors,
            "adaptive_path_selected": adaptive_path_output.get("selected_next_concept"),
            "adaptive_path_strategy": adaptive_path_output.get("recommended_strategy"),
            "adaptive_path_difficulty": adaptive_path_output.get("recommended_difficulty"),
        },

        "generated_at": _now_iso(),
    }

    if conn is not None and log:
        log_teaching_strategy(
            conn,
            {
                "student_id": str(learner_id),
                "learner_id": str(learner_id),
                "concept_id": str(concept_id),
                "teaching_strategy": teaching_view,
                "final_strategy": policy_strategy,
                "reason": decision["reason"],
                "generated_at": decision["generated_at"],
            },
        )

    return decision


# ============================================================
# Quick manual test
# ============================================================

if __name__ == "__main__":
    sample_policy_output = {
        "status": "success",
        "data": {
            "next_concept_id": "1",
            "difficulty": "medium",
            "strategy": "practice",
            "content_type": "worked_example",
            "decision_type": "dqn_rl_policy_override",
            "explanation_mode": "code",
        },
    }

    sample_evaluation_output = {
        "overall_score": 0.6,
        "verdict": "needs_light_review",
        "feedback_summary": "Needs improvement in: output_prediction, debug",
        "results": [
            {"assessment_type": "mcq", "score": 1.0},
            {"assessment_type": "output_prediction", "score": 0.0},
            {"assessment_type": "debug", "score": 0.0},
            {"assessment_type": "explanation", "score": 1.0},
            {"assessment_type": "transfer", "score": 1.0},
        ],
    }

    sample_behaviour_state = {
        "data": {
            "behavior_label": "stable",
            "behavior_score": 0.6062,
            "wrong_rate": 0.4,
            "slow_rate": 0.2,
            "low_confidence_rate": 1.0,
            "hint_rate": 0.0,
        }
    }

    sample_view_performance = {
        "status": "success",
        "logged": {
            "teaching_view": "definition_view",
            "reward": 0.4512,
            "outcome_label": "weak_success",
            "difficulty": "medium",
        },
    }

    sample_notebook = {
        "weak_assessment_types": ["output_prediction", "debug"],
    }

    sample_xai = {
        "data": {
            "evidence": {
                "feature_contributions": {
                    "top_factors": [
                        {"feature": "mastery_need"},
                        {"feature": "evaluation_need"},
                        {"feature": "view_reward_need"},
                    ]
                }
            }
        }
    }

    output = recommend_evidence_aware_teaching_strategy(
        learner_id="LNR-DEMO-SAMPLE",
        concept_id="1",
        concept_name="Variables",
        policy_output=sample_policy_output,
        evaluation_output=sample_evaluation_output,
        behaviour_state=sample_behaviour_state,
        view_performance_output=sample_view_performance,
        learner_notebook_memory_output=sample_notebook,
        xai_output=sample_xai,
        adaptive_path_output={},
        conn=None,
    )

    print(json.dumps(output, indent=2))
