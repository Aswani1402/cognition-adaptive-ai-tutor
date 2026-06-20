import json

from src.model_content_validator import parse_json_object
from scripts.structured_generation_common import ROOT_DIR


CORE = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_core.json"
OUT_JSON = ROOT_DIR / "outputs" / "evaluation" / "structured_model_website_readiness_eval.json"
OUT_MD = ROOT_DIR / "outputs" / "evaluation" / "structured_model_website_readiness_eval.md"

REQUIRED = {
    "concept_id",
    "concept_name",
    "domain",
    "task_type",
    "output",
    "valid",
    "quality_score",
    "issues",
    "raw_model_output",
    "extracted_output",
    "raw_valid",
    "final_valid",
    "fallback_applied",
}
JSON_FIELDS = {
    "flashcard": ["front", "back"],
    "mcq": ["question", "options", "answer", "explanation"],
    "debug_task": ["buggy_code", "expected_fix", "hint", "explanation"],
    "output_prediction": ["code", "answer", "explanation"],
    "challenge_question": ["challenge", "solution_outline"],
    "mindmap": ["center", "branches"],
}


def renderable(item):
    task = item.get("task_type")
    if task in JSON_FIELDS:
        parsed = parse_json_object(item.get("output", ""))
        if not parsed:
            return False
        if not all(parsed.get(field) for field in JSON_FIELDS[task]):
            return False
        if task == "mcq" and (not isinstance(parsed.get("options"), list) or len(parsed["options"]) != 4):
            return False
        if task == "mindmap" and not isinstance(parsed.get("branches"), list):
            return False
    if task == "voice_script" and len(str(item.get("output", "")).split()) < 12:
        return False
    return True


def main() -> None:
    items = json.loads(CORE.read_text(encoding="utf-8")) if CORE.exists() else []
    missing = []
    unrenderable = []
    ready = []
    for item in items:
        missing_fields = sorted(REQUIRED - set(item))
        if missing_fields:
            missing.append({"item_id": item.get("item_id"), "missing_fields": missing_fields})
        if not renderable(item):
            unrenderable.append({"item_id": item.get("item_id"), "task_type": item.get("task_type"), "issues": item.get("issues"), "output": item.get("output")})
        if (
            not missing_fields
            and item.get("final_valid", item.get("valid"))
            and float(item.get("final_quality_score", item.get("quality_score", 0.0)) or 0.0) >= 0.85
            and renderable(item)
        ):
            ready.append(item)
    total = len(items)
    rate = round(len(ready) / total, 4) if total else 0.0
    critical_schema_failures = len(missing)
    status = "PASS" if rate >= 0.85 and len(unrenderable) <= max(1, int(total * 0.15)) and critical_schema_failures == 0 else "WARN"
    report = {
        "total_items": total,
        "website_ready_count": len(ready),
        "website_ready_rate": rate,
        "raw_valid_count": sum(1 for item in items if item.get("raw_valid")),
        "raw_valid_rate": round(sum(1 for item in items if item.get("raw_valid")) / total, 4) if total else 0.0,
        "fallback_applied_count": sum(1 for item in items if item.get("fallback_applied")),
        "fallback_rate": round(sum(1 for item in items if item.get("fallback_applied")) / total, 4) if total else 0.0,
        "missing_field_count": len(missing),
        "unrenderable_structured_count": len(unrenderable),
        "critical_schema_failures": critical_schema_failures,
        "website_readiness_status": status,
        "missing_field_examples": missing[:20],
        "unrenderable_examples": unrenderable[:20],
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(
        "# Structured Model Website Readiness Eval\n\n"
        + "\n".join(f"- {key}: {value}" for key, value in report.items() if not key.endswith("examples"))
        + "\n",
        encoding="utf-8",
    )
    print(f"website_ready_count: {len(ready)}")
    print(f"website_ready_rate: {rate}")
    print(f"raw_valid_rate: {report['raw_valid_rate']}")
    print(f"fallback_rate: {report['fallback_rate']}")
    print(f"missing_field_count: {len(missing)}")
    print(f"unrenderable_structured_count: {len(unrenderable)}")
    print(f"website_readiness_status: {status}")


if __name__ == "__main__":
    main()
