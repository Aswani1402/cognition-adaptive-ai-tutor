import argparse
import json

from src.model_first_parser import parse_model_output
from src.model_first_runtime import generate_model_first_safe, generate_raw_model_output
from src.model_first_validator import validate_model_output
from src.rag_live_context_provider import get_live_rag_context


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True)
    parser.add_argument("--concept", required=True)
    parser.add_argument("--difficulty", default="easy")
    parser.add_argument("--task_type", default="mcq")
    args = parser.parse_args()
    teaching_view = args.task_type if args.task_type.endswith("_view") else "definition_view"
    context = get_live_rag_context(args.domain, args.concept, task_type=args.task_type, difficulty=args.difficulty, teaching_view=teaching_view)
    raw = generate_raw_model_output(args.task_type, context.get("domain") or args.domain, context.get("concept_name") or args.concept, args.difficulty, teaching_view, context)
    parsed = parse_model_output(raw.get("raw_output") or "", args.task_type)
    validation = validate_model_output(parsed.get("parsed_output"), args.task_type, context.get("domain") or args.domain, context.get("concept_name") or args.concept, args.difficulty, teaching_view, context, parser_repair_applied=bool(parsed.get("repair_applied")))
    final = generate_model_first_safe(args.task_type, args.domain, args.concept, args.difficulty, teaching_view, context, max_attempts=1)
    print(json.dumps({
        "prompt": raw.get("prompt"),
        "raw_output": raw.get("raw_output"),
        "parsed_output": parsed.get("parsed_output"),
        "validation": validation,
        "final_decision": "accept_raw" if validation.get("valid") else "fallback",
        "fallback_used": final.get("fallback_used"),
        "final_source": final.get("final_source"),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
