from datetime import datetime
from typing import Dict, Any, Optional

from tutor.knowledge_state.dkt.infer import update_interaction, predict_mastery

# TensorFlow/Keras behaviour model may not be available on some Python versions (e.g., 3.13).
# Make this import optional so knowledge-state integration can still run (DKT-only + behaviour disabled/warmup).
try:
    from tutor.knowledge_state.behavior_model.infer import predict_behavior
except Exception:
    predict_behavior = None

from tutor.knowledge_state.behavior import BehaviourBuffer

_BEHAV_BUFFER = BehaviourBuffer(seq_len=20)


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _default_mastery() -> Dict[str, float]:
    return {}


def _overall_mastery(mastery: Dict[str, float]) -> float:
    return float(sum(mastery.values()) / len(mastery)) if mastery else 0.5


def build_behaviour_feat(correct: int, time_taken: float, hints: int, attempts: int) -> list:
    # MUST match training-time features
    return [float(correct), float(time_taken), float(hints), float(attempts)]


def integrate_knowledge_state(
    student_id: str,
    skill_id: str,
    question_id: str,
    correct: int,
    time_taken: float = 0.0,
    hints: int = 0,
    attempts: int = 1,
    prev_mastery: Optional[Dict[str, float]] = None,
    behaviour_dataset: str = "ednet",
    behaviour_threshold: float = 0.01
) -> Dict[str, Any]:
    # 1) KT update using real DKT (question-level)
    mastery = dict(prev_mastery) if prev_mastery else _default_mastery()

    # Update DKT using QUESTION ID
    update_interaction(
        user_id=student_id,
        item_id=question_id,  # THIS is the key change
        correct=int(correct),
        model_key="assistments_v1"
    )

    # Predict mastery for THIS question
    p = predict_mastery(
        user_id=student_id,
        next_item_id=question_id,
        model_key="assistments_v1"
    )

    # Assign question mastery to skill mastery (simple aggregation)
    mastery[skill_id] = float(p)

    # 2) Behaviour update
    feat = build_behaviour_feat(int(correct), time_taken, hints, attempts)
    seq = _BEHAV_BUFFER.add(student_id, feat)

    if predict_behavior is None:
        behaviour_state = {
            "label": "disabled",
            "confidence": 0.0,
            "source": "lstm",
            "dataset": behaviour_dataset,
            "mse": 0.0,
            "reason": "tensorflow_not_available"
        }
    elif len(seq) < 20:
        behaviour_state = {
            "label": "warmup",
            "confidence": 0.0,
            "source": "lstm",
            "dataset": behaviour_dataset,
            "mse": 0.0
        }
    else:
        behaviour_state = predict_behavior(seq, dataset_key=behaviour_dataset, threshold=behaviour_threshold)

    # 3) Combined knowledge state
    return {
        "student_id": student_id,
        "mastery": {k: float(v) for k, v in mastery.items()},
        "overall_mastery": _overall_mastery(mastery),
        "behaviour": behaviour_state,
        "updated_at": _now_iso(),
        "meta": {"skill_updated": skill_id}
    }