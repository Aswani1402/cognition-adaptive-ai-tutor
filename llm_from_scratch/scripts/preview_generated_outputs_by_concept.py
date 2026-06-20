import argparse
import json
from typing import Any, Dict, Iterable, List

from scripts.structured_generation_common import ROOT_DIR


IN_JSON = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_core.json"


def norm(value: Any) -> str:
    return str(value or "").strip().lower()


def concept_matches(item: Dict[str, Any], needle: str) -> bool:
    target = norm(needle)
    return target in {norm(item.get("concept_id")), norm(item.get("concept_name"))} or target in norm(item.get("concept_name"))


def matching_items(items: Iterable[Dict[str, Any]], domain: str, concept: str) -> List[Dict[str, Any]]:
    domain_target = norm(domain)
    return [
        item
        for item in items
        if norm(item.get("domain")) == domain_target and concept_matches(item, concept)
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview generated structured outputs for one concept.")
    parser.add_argument("--domain", required=True)
    parser.add_argument("--concept", required=True)
    args = parser.parse_args()

    items = json.loads(IN_JSON.read_text(encoding="utf-8")) if IN_JSON.exists() else []
    matches = matching_items(items, args.domain, args.concept)

    print(f"source: {IN_JSON}")
    print(f"matches: {len(matches)}")
    for item in matches:
        preview = {
            "domain": item.get("domain"),
            "concept_id": item.get("concept_id"),
            "concept_name": item.get("concept_name"),
            "task_type": item.get("task_type"),
            "raw_valid": item.get("raw_valid"),
            "final_valid": item.get("final_valid", item.get("valid")),
            "valid": item.get("final_valid", item.get("valid")),
            "raw_quality_score": item.get("raw_quality_score"),
            "final_quality_score": item.get("final_quality_score", item.get("quality_score")),
            "quality_score": item.get("final_quality_score", item.get("quality_score")),
            "fallback_applied": item.get("fallback_applied"),
            "fallback_source": item.get("fallback_source"),
            "raw_issues": item.get("raw_issues", []),
            "final_issues": item.get("final_issues", item.get("issues", [])),
            "issues": item.get("final_issues", item.get("issues", [])),
            "extracted_output": item.get("extracted_output", ""),
            "raw_model_output": item.get("raw_model_output", ""),
            "output": item.get("output", ""),
        }
        print(json.dumps(preview, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
