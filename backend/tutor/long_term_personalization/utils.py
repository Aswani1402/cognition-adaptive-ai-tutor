import json
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_json_object(raw: Any) -> Dict[str, Any]:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def parse_timestamp(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def mean(values: Iterable[float], default: float = 0.0) -> float:
    values_list = list(values)
    return sum(values_list) / len(values_list) if values_list else default


def normalize_mastery_values(state_json: Dict[str, Any]) -> Dict[str, float]:
    if not state_json:
        return {}

    if state_json.get("schema_version") == "kt_v2" and isinstance(state_json.get("concepts"), dict):
        candidate = {
            concept_id: concept_state.get("mastery")
            for concept_id, concept_state in state_json["concepts"].items()
            if isinstance(concept_state, dict)
        }
    else:
        candidate = state_json.get("mastery", state_json)

    if not isinstance(candidate, dict):
        return {}

    output: Dict[str, float] = {}
    for concept_id, raw_value in candidate.items():
        try:
            score = float(raw_value)
        except (TypeError, ValueError):
            continue
        output[str(concept_id)] = max(0.0, min(1.0, score))
    return output


def safe_round(value: float, digits: int = 4) -> float:
    return round(safe_float(value), digits)


def top_domains(
    concept_scores: Dict[str, float],
    concept_to_domain: Dict[str, str],
    threshold: float,
    reverse: bool = True,
    limit: int = 5,
) -> List[str]:
    domain_scores: Dict[str, List[float]] = {}
    for concept_id, score in concept_scores.items():
        ok = score >= threshold if reverse else score < threshold
        if not ok:
            continue
        domain = concept_to_domain.get(concept_id, concept_id)
        domain_scores.setdefault(domain, []).append(score)

    ranked = sorted(
        domain_scores.items(),
        key=lambda kv: mean(kv[1], default=0.0),
        reverse=reverse,
    )
    return [domain for domain, _ in ranked[:limit]]
