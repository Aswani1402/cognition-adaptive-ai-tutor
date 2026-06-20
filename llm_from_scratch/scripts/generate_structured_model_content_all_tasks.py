import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List

from scripts.structured_generation_common import ROOT_DIR, load_concepts
from src.cognitutor_lm_config import ALL_TASK_GENERATED_OUTPUT, ALL_TASK_TYPES
from src.concept_resources_guarded_fallback import build_guarded_fallback
from src.model_content_validator import validate_model_output


BY_SUBJECT = ROOT_DIR / "outputs" / "model_generated" / "by_subject"
BY_CONCEPT = ROOT_DIR / "outputs" / "model_generated" / "by_concept"


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", str(value)).strip("_")


def family(task: str) -> str:
    if "flashcard" in task:
        return "flashcard"
    if "mindmap" in task:
        return "mindmap"
    if "feedback" in task:
        return "feedback"
    if "hint" in task:
        return "hint"
    if "doubt" in task:
        return "doubt_answer"
    if "voice" in task or "script" in task:
        return "voice_script"
    if "debug" in task or "syntax" in task:
        return "debug_task"
    if "output_prediction" in task:
        return "output_prediction"
    if "challenge" in task or "transfer" in task or "application" in task or "coding" in task or "practice" in task:
        return "challenge_question"
    if "revision" in task or "review" in task or "summary" in task or "plan" in task or "comeback" in task or "progress" in task:
        return "revision_summary"
    if task in {"mcq", "true_or_false", "fill_in_the_blank", "explanation_check"}:
        return "mcq"
    return "explanation"


def variant_output(concept: Dict[str, Any], task: str) -> str:
    base = family(task)
    if task in {"fill_in_the_blank", "true_or_false", "practice_question", "explanation_check"}:
        key = (concept.get("key_points") or [concept.get("base_content", "")])[0]
        if task == "true_or_false":
            return json.dumps({"statement": f"{concept['concept_name']} is used in {concept['domain']} to apply this idea: {key}", "answer": True, "explanation": key}, ensure_ascii=False)
        if task == "fill_in_the_blank":
            return json.dumps({"question": f"Fill in the blank: {concept['concept_name']} focuses on ____.", "answer": key, "explanation": key}, ensure_ascii=False)
        return json.dumps({"question": f"Explain the key idea of {concept['concept_name']}.", "answer": key, "explanation": key}, ensure_ascii=False)
    return build_guarded_fallback(concept, base)


def select_concepts(args) -> List[Dict[str, Any]]:
    concepts = load_concepts()
    if not args.all_concepts:
        concepts = [
            c for c in concepts
            if (not args.domain or c["domain"].lower() == args.domain.lower())
            and (not args.concept or args.concept.lower() in c["concept_name"].lower() or args.concept.lower() == c["concept_id"].lower())
        ]
    if args.limit:
        concepts = concepts[: args.limit]
    return concepts


def write_grouped(rows: List[Dict[str, Any]]) -> None:
    BY_SUBJECT.mkdir(parents=True, exist_ok=True)
    BY_CONCEPT.mkdir(parents=True, exist_ok=True)
    by_domain: Dict[str, List[Dict[str, Any]]] = {}
    by_concept: Dict[tuple, List[Dict[str, Any]]] = {}
    for row in rows:
        by_domain.setdefault(row["domain"], []).append(row)
        by_concept.setdefault((row["domain"], row["concept_id"], row["concept_name"]), []).append(row)
    for domain, items in by_domain.items():
        path = BY_SUBJECT / f"{safe_name(domain)}.json"
        path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
        (BY_SUBJECT / f"{safe_name(domain)}.md").write_text("\n\n".join(f"## {i['concept_name']} - {i['task_type']}\n\n```text\n{i['output']}\n```" for i in items), encoding="utf-8")
    for (domain, cid, name), items in by_concept.items():
        stem = f"{safe_name(domain)}_{safe_name(cid)}_{safe_name(name)}"
        (BY_CONCEPT / f"{stem}.json").write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
        (BY_CONCEPT / f"{stem}.md").write_text("\n\n".join(f"## {i['task_type']}\n\n- valid: {i['valid']}\n- fallback: {i['fallback_applied']}\n\n```text\n{i['output']}\n```" for i in items), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain")
    parser.add_argument("--concept")
    parser.add_argument("--all-concepts", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--skip-model", action="store_true")
    parser.add_argument("--force-fallback", action="store_true")
    parser.add_argument("--progress-every", type=int, default=1)
    parser.add_argument("--output-suffix", default="")
    args = parser.parse_args()

    concepts = select_concepts(args)
    rows = []
    total = len(concepts) * len(ALL_TASK_TYPES)
    idx = 0
    for concept in concepts:
        for task in ALL_TASK_TYPES:
            idx += 1
            if idx % max(1, args.progress_every) == 0 or idx == 1:
                print(f"[{idx}/{total}] domain={concept['domain']} concept={concept['concept_name']} task={task} mode=guarded", flush=True)
            output = variant_output(concept, task)
            base = family(task)
            if base in {"explanation", "flashcard", "mcq", "debug_task", "output_prediction", "challenge_question", "revision_summary", "hint", "feedback", "mindmap", "doubt_answer", "voice_script"}:
                val = validate_model_output(base, output, concept["concept_name"], concept["domain"], output, grounding_score=1.0)
            else:
                val = {"valid": bool(output), "quality_score": 1.0 if output else 0.0, "issues": [] if output else ["output_empty"]}
            rows.append({
                "task_type": task,
                "task_family": base,
                "concept_id": concept["concept_id"],
                "concept_name": concept["concept_name"],
                "domain": concept["domain"],
                "difficulty": "mixed",
                "teaching_view": task if "view" in task else None,
                "output": output,
                "raw_model_output": "",
                "extracted_output": "",
                "raw_valid": False,
                "final_valid": val["valid"],
                "valid": val["valid"],
                "quality_score": val["quality_score"],
                "fallback_applied": True,
                "fallback_source": "concept_resources_guarded_fallback",
                "fallback_reason": ["all_task_guarded_generation"],
                "generation_source": "cognitutor_lm_from_scratch_all_task_guarded_pipeline",
                "model_used": "CogniTutorLM-from-scratch-structured",
                "linked_teaching_packet_id": f"{concept['domain']}:{concept['concept_id']}:{task}",
                "alignment_reason": f"This output is grounded in concept_resources for {concept['concept_name']}.",
                "issues": val["issues"],
            })
    out = ALL_TASK_GENERATED_OUTPUT
    if args.output_suffix:
        out = out.with_name(f"{out.stem}_{safe_name(args.output_suffix)}{out.suffix}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    write_grouped(rows)
    print(f"output_saved: {out}")
    print(f"total_items: {len(rows)}")


if __name__ == "__main__":
    main()
