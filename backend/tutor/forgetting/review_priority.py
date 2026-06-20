from typing import Dict, List, Tuple


def review_priority(mastery: float, decay: float) -> float:
    """
    Deterministic priority:
      priority = decay * (1 - mastery)

    High decay + low mastery => highest priority.
    """
    m = 0.0 if mastery is None else float(mastery)
    d = 0.0 if decay is None else float(decay)
    m = max(0.0, min(1.0, m))
    d = max(0.0, min(1.0, d))
    return float(d * (1.0 - m))


def build_review_queue(
    mastery_map: Dict[str, float],
    decay_map: Dict[str, float],
    top_k: int = 5,
    review_threshold: float = 0.40
) -> Tuple[List[str], Dict[str, bool], Dict[str, float]]:
    """
    Returns:
      - review_queue: list of concept_ids (top_k)
      - notes: {"no_due_items": bool}
      - priority_map: {concept_id: priority}
    """
    priority_map: Dict[str, float] = {}
    for cid, m in mastery_map.items():
        priority_map[cid] = review_priority(m, decay_map.get(cid, 0.0))

    items = sorted(priority_map.items(), key=lambda x: x[1], reverse=True)

    due_items = [(cid, pr) for cid, pr in items if float(decay_map.get(cid, 0.0)) >= review_threshold]

    if due_items:
        queue = [cid for cid, _ in due_items[:top_k]]
        return queue, {"no_due_items": False}, priority_map

    queue = [cid for cid, _ in items[:top_k]]
    return queue, {"no_due_items": True}, priority_map