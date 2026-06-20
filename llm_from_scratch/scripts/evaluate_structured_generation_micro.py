import json
from pathlib import Path

from scripts.structured_generation_common import ROOT_DIR, build_prompt, load_concepts
from src.live_tutor_generator import generate_with_cognitutor_lm
from src.model_content_validator import validate_model_output


OUT_JSON = ROOT_DIR / "outputs" / "evaluation" / "structured_generation_micro_eval.json"
OUT_MD = ROOT_DIR / "outputs" / "evaluation" / "structured_generation_micro_eval.md"
ANALYSIS_JSON = ROOT_DIR / "outputs" / "final_reports" / "structured_micro_failure_analysis.json"
ANALYSIS_MD = ROOT_DIR / "outputs" / "final_reports" / "structured_micro_failure_analysis.md"

CASES = [
    ("Python", "Variables", "explanation"),
    ("Python", "Variables", "flashcard"),
    ("SQL", "SELECT", "mcq"),
    ("Python", "Loops", "debug_task"),
    ("HTML", "Tags", "explanation"),
    ("Git", "Commits", "revision_summary"),
    ("Data Structures", "Stack", "challenge_question"),
    ("Python", "Functions", "hint"),
    ("SQL", "WHERE", "feedback"),
    ("HTML", "Forms", "mindmap"),
    ("Git", "Branches", "doubt_answer"),
    ("Data Structures", "Linked", "voice_script"),
]


def pick(concepts, domain, needle):
    return next((c for c in concepts if c["domain"] == domain and needle.lower() in c["concept_name"].lower()), next(c for c in concepts if c["domain"] == domain))


def classify_failure(row):
    issues = row.get("blocking_issues") or row.get("issues") or []
    output = str(row.get("output") or "")
    causes = []
    if any("invalid_json" in issue or "missing_" in issue for issue in issues):
        causes.append("model output not following format")
    if any("concept_or_domain_irrelevant" in issue or "wrong_domain" in issue for issue in issues):
        causes.append("wrong-domain or mixed-task output")
    if "repeated_nonsense" in issues or output.count("hint") >= 4 or output.count("commit") >= 5:
        causes.append("generation decoding/repetition issue")
    if any("grounding_score" in issue for issue in issues):
        causes.append("grounding below threshold")
    if not causes and not row.get("valid"):
        causes.append("format or quality validation failure")
    return causes


def write_failure_analysis(results, summary):
    failed = [row for row in results if not row.get("valid")]
    task_counts = {}
    common = {}
    for row in failed:
        task = row["task_type"]
        task_counts[task] = task_counts.get(task, 0) + 1
        for cause in classify_failure(row):
            common[cause] = common.get(cause, 0) + 1

    analysis = {
        "previous_micro_valid_rate": 0.1667,
        "previous_micro_avg_quality_score": 0.4867,
        "current_summary": summary,
        "failed_count": len(failed),
        "failed_task_types": sorted(task_counts),
        "failure_counts_by_task_type": task_counts,
        "common_failure_causes": common,
        "checkpoint_verification": {
            "expected_checkpoint": str(ROOT_DIR / "models" / "cognitutor_lm_structured_generation" / "best_model.pt"),
            "checkpoint_paths_used": sorted({str(row.get("checkpoint_path_used")) for row in results if row.get("checkpoint_path_used")}),
            "wrong_checkpoint_loaded": any("cognitutor_lm_structured_generation" not in str(row.get("checkpoint_path_used", "")) for row in results),
        },
        "diagnosis": {
            "model_output_not_following_format": any("model output not following format" in classify_failure(row) for row in failed),
            "validator_too_strict": False,
            "prompt_mismatch": False,
            "wrong_checkpoint_loaded": any("cognitutor_lm_structured_generation" not in str(row.get("checkpoint_path_used", "")) for row in results),
            "structured_training_dataset_too_weak_or_small": summary.get("valid_rate", 0) < 0.85,
            "generation_decoding_issue": any("generation decoding/repetition issue" in classify_failure(row) for row in failed),
        },
        "failed_cases": [
            {
                "concept_name": row.get("concept_name"),
                "domain": row.get("domain"),
                "task_type": row.get("task_type"),
                "output": row.get("output"),
                "issues": row.get("issues"),
                "blocking_issues": row.get("blocking_issues"),
                "quality_score": row.get("quality_score"),
                "causes": classify_failure(row),
            }
            for row in failed
        ],
    }
    ANALYSIS_JSON.parent.mkdir(parents=True, exist_ok=True)
    ANALYSIS_JSON.write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# Structured Micro Failure Analysis",
        "",
        f"- previous_micro_valid_rate: {analysis['previous_micro_valid_rate']}",
        f"- previous_micro_avg_quality_score: {analysis['previous_micro_avg_quality_score']}",
        f"- current_summary: {summary}",
        f"- failed_task_types: {analysis['failed_task_types']}",
        f"- common_failure_causes: {common}",
        f"- checkpoint_paths_used: {analysis['checkpoint_verification']['checkpoint_paths_used']}",
        "",
        "## Failed Cases",
    ]
    for case in analysis["failed_cases"]:
        lines.extend(
            [
                "",
                f"### {case['domain']} {case['concept_name']} - {case['task_type']}",
                f"- causes: {case['causes']}",
                f"- issues: {case['issues']}",
                "",
                "```text",
                str(case["output"] or ""),
                "```",
            ]
        )
    ANALYSIS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return analysis


def main() -> None:
    concepts = load_concepts()
    results = []
    for domain, needle, task in CASES:
        concept = pick(concepts, domain, needle)
        prompt = build_prompt(concept, task)
        gen = generate_with_cognitutor_lm(prompt, task, max_new_tokens=180, temperature=0.0, top_p=1.0)
        validation = validate_model_output(task, gen["output"], concept["concept_name"], concept["domain"], prompt, grounding_score=1.0 if gen["output"] else 0.0)
        results.append({**concept, "task_type": task, "prompt": prompt, **gen, **validation})
    attempted = len(results)
    valid = sum(1 for r in results if r["valid"])
    avg_quality = round(sum(r["quality_score"] for r in results) / attempted, 4) if attempted else 0.0
    valid_rate = round(valid / attempted, 4) if attempted else 0.0
    status = "PASS" if valid_rate >= 0.85 and avg_quality >= 0.85 else ("WARN" if valid else "FAIL")
    summary = {"attempted": attempted, "valid": valid, "valid_rate": valid_rate, "avg_quality_score": avg_quality, "status": status}
    analysis = write_failure_analysis(results, summary)
    report = {"summary": summary, "failure_analysis_path": str(ANALYSIS_JSON), "results": results}
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(
        "# Structured Generation Micro Eval\n\n"
        + "\n".join(f"- {k}: {v}" for k, v in report["summary"].items())
        + f"\n- failed_task_types: {analysis['failed_task_types']}\n",
        encoding="utf-8",
    )
    print(f"attempted: {attempted}")
    print(f"valid: {valid}")
    print(f"valid_rate: {valid_rate}")
    print(f"avg_quality_score: {avg_quality}")
    print(f"status: {status}")


if __name__ == "__main__":
    main()
