import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

from scripts.structured_generation_common import ROOT_DIR, build_prompt, load_concepts
from src.live_tutor_generator import generate_with_cognitutor_lm
from src.model_content_validator import validate_model_output


OUT_JSON = ROOT_DIR / "outputs" / "evaluation" / "structured_generation_expanded_micro_eval.json"
OUT_MD = ROOT_DIR / "outputs" / "evaluation" / "structured_generation_expanded_micro_eval.md"

TARGET_CONCEPTS = [
    ("Python", "Variables"),
    ("Python", "Loops"),
    ("Python", "Functions"),
    ("SQL", "Database Basics"),
    ("SQL", "SQL SELECT Queries"),
    ("SQL", "WHERE Filters"),
    ("HTML", "HTML Tags and Elements"),
    ("HTML", "Forms Inputs"),
    ("Git", "Git Commits and History"),
    ("Git", "Git Branches"),
    ("Data Structures", "Linked List"),
    ("Data Structures", "Stack"),
    ("Data Structures", "Arrays"),
]

TASK_TYPES = [
    "explanation",
    "flashcard",
    "mcq",
    "debug_task",
    "output_prediction",
    "challenge_question",
    "hint",
    "revision_summary",
]


def tokens(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", str(text or "").lower())


def fuzzy_match(concepts: List[Dict], domain: str, requested_name: str) -> Tuple[Dict, Dict]:
    domain_concepts = [concept for concept in concepts if concept["domain"] == domain]
    requested_tokens = set(tokens(requested_name))
    best = None
    best_score = -1.0
    for concept in domain_concepts:
        concept_tokens = set(tokens(concept["concept_name"]))
        overlap = len(requested_tokens & concept_tokens)
        score = overlap / max(1, len(requested_tokens | concept_tokens))
        if requested_name.lower() in concept["concept_name"].lower():
            score += 0.5
        if concept["concept_name"].lower() in requested_name.lower():
            score += 0.4
        if score > best_score:
            best = concept
            best_score = score
    if best is None:
        raise ValueError(f"No concepts found for domain {domain}")
    return best, {
        "requested_domain": domain,
        "requested_name": requested_name,
        "resolved_concept_id": best["concept_id"],
        "resolved_concept_name": best["concept_name"],
        "resolved_domain": best["domain"],
        "match_score": round(best_score, 4),
        "exact_match": requested_name.lower() == best["concept_name"].lower(),
    }


def task_plan_for_index(index: int) -> List[str]:
    start = (index * 3) % len(TASK_TYPES)
    return [TASK_TYPES[(start + offset) % len(TASK_TYPES)] for offset in range(4)]


def is_website_ready(item: Dict) -> bool:
    required = [
        "status",
        "concept_id",
        "concept_name",
        "domain",
        "task_type",
        "generation_source",
        "model_used",
        "output",
        "valid",
        "quality_score",
        "issues",
    ]
    return (
        all(key in item for key in required)
        and item["status"] == "success"
        and bool(str(item["output"]).strip())
        and item["valid"] is True
        and float(item["quality_score"]) >= 0.85
        and item["generation_source"] == "cognitutor_lm_from_scratch_structured_model"
        and item["model_used"] == "CogniTutorLM-from-scratch-structured"
    )


def summarize_counts(results: List[Dict], key: str) -> Dict[str, Dict[str, int]]:
    summary = defaultdict(lambda: {"attempted": 0, "valid": 0})
    for row in results:
        bucket = row[key]
        summary[bucket]["attempted"] += 1
        summary[bucket]["valid"] += 1 if row["valid"] else 0
    return dict(summary)


def main() -> None:
    concepts = load_concepts()
    resolved = []
    results = []

    for index, (domain, requested_name) in enumerate(TARGET_CONCEPTS):
        concept, match = fuzzy_match(concepts, domain, requested_name)
        resolved.append(match)
        for task_type in task_plan_for_index(index):
            prompt = build_prompt(concept, task_type)
            generation = generate_with_cognitutor_lm(
                prompt,
                task_type,
                max_new_tokens=180,
                temperature=0.0,
                top_p=1.0,
            )
            validation = validate_model_output(
                task_type=task_type,
                generated_text=generation.get("output", ""),
                concept_name=concept["concept_name"],
                domain=concept["domain"],
                context_text=prompt,
                grounding_score=1.0 if generation.get("output") else 0.0,
            )
            item = {
                "status": generation.get("status"),
                "concept_id": concept["concept_id"],
                "concept_name": concept["concept_name"],
                "domain": concept["domain"],
                "task_type": task_type,
                "generation_source": "cognitutor_lm_from_scratch_structured_model",
                "model_used": generation.get("model_used"),
                "checkpoint_path_used": generation.get("checkpoint_path_used"),
                "requested_concept_name": requested_name,
                "resolved_match_score": match["match_score"],
                "prompt": prompt,
                "output": generation.get("output", ""),
                "valid": validation["valid"],
                "quality_score": validation["quality_score"],
                "issues": validation["issues"],
                "blocking_issues": validation["blocking_issues"],
            }
            item["website_ready"] = is_website_ready(item)
            results.append(item)

    attempted = len(results)
    valid = sum(1 for row in results if row["valid"])
    website_ready_count = sum(1 for row in results if row["website_ready"])
    avg_quality = round(sum(row["quality_score"] for row in results) / attempted, 4) if attempted else 0.0
    valid_rate = round(valid / attempted, 4) if attempted else 0.0
    website_ready_rate = round(website_ready_count / attempted, 4) if attempted else 0.0
    domains = sorted({row["domain"] for row in results})
    represented_tasks = sorted({row["task_type"] for row in results})
    pass_rule = (
        valid_rate >= 0.85
        and avg_quality >= 0.85
        and website_ready_rate >= 0.85
        and len(domains) == 5
        and len(represented_tasks) >= 8
    )
    status = "PASS" if pass_rule else ("WARN" if valid else "FAIL")
    failed_examples = [
        {
            "concept_id": row["concept_id"],
            "concept_name": row["concept_name"],
            "domain": row["domain"],
            "task_type": row["task_type"],
            "output": row["output"],
            "issues": row["issues"],
            "quality_score": row["quality_score"],
        }
        for row in results
        if not row["website_ready"]
    ][:12]

    summary = {
        "attempted": attempted,
        "valid": valid,
        "valid_rate": valid_rate,
        "avg_quality_score": avg_quality,
        "valid_by_domain": summarize_counts(results, "domain"),
        "valid_by_task_type": summarize_counts(results, "task_type"),
        "website_ready_count": website_ready_count,
        "website_ready_rate": website_ready_rate,
        "subjects_represented": domains,
        "task_types_represented": represented_tasks,
        "all_5_subjects_represented": len(domains) == 5,
        "at_least_8_task_types_represented": len(represented_tasks) >= 8,
        "failed_examples": failed_examples,
        "status": status,
    }
    report = {
        "summary": summary,
        "resolved_concepts": resolved,
        "results": results,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Structured Generation Expanded Micro Eval",
        "",
        f"- attempted: {attempted}",
        f"- valid: {valid}",
        f"- valid_rate: {valid_rate}",
        f"- avg_quality_score: {avg_quality}",
        f"- website_ready_count: {website_ready_count}",
        f"- website_ready_rate: {website_ready_rate}",
        f"- subjects_represented: {domains}",
        f"- task_types_represented: {represented_tasks}",
        f"- status: {status}",
        "",
        "## Resolved Concepts",
    ]
    for match in resolved:
        lines.append(
            f"- {match['requested_domain']} / {match['requested_name']} -> "
            f"{match['resolved_concept_id']} {match['resolved_concept_name']} "
            f"(score={match['match_score']})"
        )
    lines.extend(["", "## Failed Examples"])
    if failed_examples:
        for failed in failed_examples:
            lines.extend(
                [
                    "",
                    f"### {failed['domain']} {failed['concept_name']} - {failed['task_type']}",
                    f"- issues: {failed['issues']}",
                    f"- quality_score: {failed['quality_score']}",
                    "",
                    "```text",
                    failed["output"],
                    "```",
                ]
            )
    else:
        lines.append("- None")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"attempted: {attempted}")
    print(f"valid: {valid}")
    print(f"valid_rate: {valid_rate}")
    print(f"avg_quality_score: {avg_quality}")
    print(f"website_ready_count: {website_ready_count}")
    print(f"website_ready_rate: {website_ready_rate}")
    print(f"valid_by_domain: {summary['valid_by_domain']}")
    print(f"valid_by_task_type: {summary['valid_by_task_type']}")
    print(f"status: {status}")


if __name__ == "__main__":
    main()
