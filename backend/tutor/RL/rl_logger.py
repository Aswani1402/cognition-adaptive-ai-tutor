import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, Optional


def create_rl_table(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rl_experience_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT NOT NULL,
            concept_id TEXT,
            state_json TEXT NOT NULL,
            action_json TEXT NOT NULL,
            reward REAL NOT NULL,
            next_state_json TEXT NOT NULL,
            source TEXT DEFAULT 'integrated_tutor',
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def extract_mastery_score(knowledge_state: Dict[str, Any]) -> float:
    if not isinstance(knowledge_state, dict):
        return 0.0

    data = knowledge_state.get("data", {})

    # 🔑 Step 1 — unwrap nested "data" layers (handles your structure)
    for _ in range(2):  # max 2 levels (safe)
        if isinstance(data, dict) and "data" in data:
            data = data.get("data", {})
        else:
            break

    # Step 2 — direct mastery fields
    if isinstance(data, dict):
        if "predicted_mastery_last" in data:
            return safe_float(data.get("predicted_mastery_last"))

        if "mastery_score" in data:
            return safe_float(data.get("mastery_score"))

    # Step 3 — fallback: state_json aggregation
    state_json = data.get("state_json", {})
    if isinstance(state_json, dict):
        values = []

        for value in state_json.values():
            if isinstance(value, (int, float)):
                values.append(float(value))
            elif isinstance(value, dict) and "mastery" in value:
                values.append(safe_float(value.get("mastery")))

        if values:
            return sum(values) / len(values)

    return 0.0


def extract_review_due(forgetting_state: Dict[str, Any]) -> bool:
    if not isinstance(forgetting_state, dict):
        return False

    data = forgetting_state.get("data", forgetting_state)

    if isinstance(data, dict):
        if data.get("review_due") is True:
            return True

        review_queue = data.get("review_queue", [])
        if isinstance(review_queue, list) and len(review_queue) > 0:
            return True

        due_reviews = data.get("due_reviews", [])
        if isinstance(due_reviews, list) and len(due_reviews) > 0:
            return True

    return False


def build_rl_state(
    knowledge_state: Dict[str, Any],
    behaviour_state: Dict[str, Any],
    forgetting_state: Dict[str, Any],
    evaluation_output: Dict[str, Any],
    learning_signal: str,
) -> Dict[str, Any]:
    behaviour_data = behaviour_state.get("data", behaviour_state) if isinstance(behaviour_state, dict) else {}

    return {
        "mastery_score": extract_mastery_score(knowledge_state),
        "behavior_label": behaviour_data.get("behavior_label", behaviour_data.get("label", "unknown")),
        "behavior_score": safe_float(behaviour_data.get("behavior_score", behaviour_data.get("score", 0.0))),
        "review_due": extract_review_due(forgetting_state),
        "evaluation_score": safe_float(evaluation_output.get("overall_score", evaluation_output.get("score", 0.0))),
        "learning_signal": learning_signal,
    }


def build_rl_action(policy_output: Dict[str, Any]) -> Dict[str, Any]:
    data = policy_output.get("data", policy_output) if isinstance(policy_output, dict) else {}

    return {
        "next_concept_id": data.get("next_concept_id"),
        "strategy": data.get("strategy"),
        "difficulty": data.get("difficulty"),
        "content_type": data.get("content_type"),
        "decision_type": data.get("decision_type"),
    }


def compute_reward(
    state: Dict[str, Any],
    action: Dict[str, Any],
    next_state: Dict[str, Any],
    multi_evidence_output: Optional[Dict[str, Any]] = None,
) -> float:
    reward = 0.0

    evaluation_score = safe_float(next_state.get("evaluation_score"))
    behavior_score = safe_float(next_state.get("behavior_score"))
    learning_signal = next_state.get("learning_signal")
    review_due = bool(next_state.get("review_due"))

    # --- 1. Core performance signal (dominant but bounded)
    # scale 0–1 → 0–0.6
    reward += 0.6 * evaluation_score

    # --- 2. Learning signal bonus (discrete, not too strong)
    if learning_signal == "mastered":
        reward += 0.4
    elif learning_signal == "partial":
        reward += 0.15
    elif learning_signal == "weak":
        reward -= 0.5

    # --- 3. Behavior penalty (only if risky)
    if behavior_score >= 0.7:
        reward -= 0.2

    # --- 4. Review pressure (don’t over-penalize)
    if review_due:
        reward -= 0.1

    # --- 5. Decision quality adjustment (small influence)
    if isinstance(multi_evidence_output, dict):
        final_action = multi_evidence_output.get("final_action", "")

        if final_action in {"progress_with_review_later", "promote_next"}:
            reward += 0.2
        elif final_action in {"reinforce_current", "reteach"}:
            reward -= 0.2
        elif final_action == "light_review":
            reward += 0.05

    # --- 6. Clamp to stable range
    reward = max(-1.0, min(1.0, reward))

    return round(reward, 4)

def log_rl_experience(
    conn: sqlite3.Connection,
    learner_id: str,
    concept_id: str,
    state: Dict[str, Any],
    action: Dict[str, Any],
    reward: float,
    next_state: Dict[str, Any],
    source: str = "integrated_tutor",
) -> None:
    create_rl_table(conn)

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO rl_experience_log (
            learner_id,
            concept_id,
            state_json,
            action_json,
            reward,
            next_state_json,
            source,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(learner_id),
            str(concept_id),
            json.dumps(state),
            json.dumps(action),
            float(reward),
            json.dumps(next_state),
            source,
            datetime.now().isoformat(timespec="seconds"),
        ),
    )

    conn.commit()


def log_from_tutor_pipeline(
    conn: sqlite3.Connection,
    learner_id: str,
    concept_id: str,
    current_policy_output: Dict[str, Any],
    final_policy_output: Dict[str, Any],
    knowledge_state: Dict[str, Any],
    behaviour_state: Dict[str, Any],
    forgetting_state: Dict[str, Any],
    evaluation_output: Dict[str, Any],
    learning_signal: str,
    multi_evidence_output: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    state = build_rl_state(
        knowledge_state=knowledge_state,
        behaviour_state=behaviour_state,
        forgetting_state=forgetting_state,
        evaluation_output=evaluation_output,
        learning_signal="before_evaluation",
    )

    next_state = build_rl_state(
        knowledge_state=knowledge_state,
        behaviour_state=behaviour_state,
        forgetting_state=forgetting_state,
        evaluation_output=evaluation_output,
        learning_signal=learning_signal,
    )

    action = build_rl_action(final_policy_output)

    reward = compute_reward(
        state=state,
        action=action,
        next_state=next_state,
        multi_evidence_output=multi_evidence_output,
    )

    log_rl_experience(
        conn=conn,
        learner_id=learner_id,
        concept_id=concept_id,
        state=state,
        action=action,
        reward=reward,
        next_state=next_state,
    )

    return {
        "status": "success",
        "state": state,
        "action": action,
        "reward": reward,
        "next_state": next_state,
    }