import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict


CONTENT_VERSION = "v1.0.0"
GENERATOR_VERSION = "cognitutor_lm_guarded_product_generator_v1"
QUALITY_GATE_VERSION = "v1"


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def version_metadata(source: Any = None, concept_resource: Any = None, website_ready: bool = False) -> Dict[str, Any]:
    source_value = source if source is not None else concept_resource
    return {
        "content_version": CONTENT_VERSION,
        "generator_version": GENERATOR_VERSION,
        "generated_at": utc_now(),
        "source_hash": stable_hash(source_value),
        "concept_resource_hash": stable_hash(concept_resource if concept_resource is not None else source_value),
        "quality_gate_version": QUALITY_GATE_VERSION,
        "website_ready": bool(website_ready),
    }


def attach_version_metadata(item: Dict[str, Any], source: Any = None, concept_resource: Any = None, website_ready: bool = False) -> Dict[str, Any]:
    item.update(version_metadata(source=source or item, concept_resource=concept_resource or item, website_ready=website_ready))
    return item
