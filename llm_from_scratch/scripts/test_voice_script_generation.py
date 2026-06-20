import json
import re
from itertools import combinations
from typing import Any, Dict, List

from src.cognitutor_lm_config import ROOT
from src.concept_resource_loader import find_concept
from src.voice_script_generator import TARGET_WORDS, generate_voice_script


OUT_JSON = ROOT / "outputs" / "service_tests" / "voice_script_generation_test.json"
OUT_MD = ROOT / "outputs" / "service_tests" / "voice_script_generation_test.md"
BAD_MARKERS = ("...", "TODO", "N/A", "placeholder")


CASES = [
    ("Python", "Variables", "easy", "definition_view", "concept_intro_voice_script"),
    ("Python", "Variables", "easy", "definition_view", "teaching_voice_script"),
    ("Python", "Variables", "medium", "code_view", "teaching_voice_script"),
    ("Python", "Variables", "hard", "challenge_view", "teaching_voice_script"),
    ("SQL", "JOIN", "medium", "code_view", "teaching_voice_script"),
    ("Data Structures", "Trees", "hard", "challenge_view", "teaching_voice_script"),
    ("HTML", "Forms", "easy", "definition_view", "revision_voice_script"),
    ("Git", "Branches", "medium", "code_view", "next_step_guidance_script"),
    ("Python", "Variables", "medium", "misconception_view", "mistake_feedback_voice_script"),
    ("SQL", "JOIN", "medium", "step_by_step_view", "doubt_explanation_voice_script"),
]


def words(text: str) -> List[str]:
    return re.findall(r"\b[\w']+\b", text or "")


def similarity(a: str, b: str) -> float:
    aw = set(w.lower() for w in words(a))
    bw = set(w.lower() for w in words(b))
    return len(aw & bw) / max(1, len(aw | bw))


def validate(case: Dict[str, Any], output: Dict[str, Any]) -> List[str]:
    issues = []
    script = output.get("script", "")
    min_words, max_words = TARGET_WORDS[case["voice_type"]]
    count = len(words(script))
    if not script:
        issues.append("empty_script")
    if not (min_words <= count <= max_words):
        issues.append(f"length_out_of_range_{count}_expected_{min_words}_{max_words}")
    if output.get("task_type") != case["voice_type"]:
        issues.append("wrong_task_type")
    if output.get("difficulty") != case["difficulty"]:
        issues.append("wrong_difficulty")
    if not output.get("source_level"):
        issues.append("missing_source_level")
    if output.get("audio_ready") is not True:
        issues.append("audio_not_ready")
    if not all(output.get("voice_sections", {}).get(k) for k in ["opening", "explanation", "example", "check_prompt", "closing"]):
        issues.append("missing_voice_sections")
    if any(marker in json.dumps(output, ensure_ascii=False) for marker in BAD_MARKERS):
        issues.append("bad_marker")
    if re.search(r"\s+[,.!?]", script) or re.search(r"[,:;]\s*[.!?]", script):
        issues.append("broken_punctuation")
    return issues


def main() -> None:
    results = []
    for domain, concept_name, difficulty, teaching_view, voice_type in CASES:
        concept = find_concept(domain, concept=concept_name)
        case = {
            "domain": domain,
            "concept_name": concept_name,
            "difficulty": difficulty,
            "teaching_view": teaching_view,
            "voice_type": voice_type,
        }
        if not concept:
            results.append({"case": case, "status": "FAIL", "issues": ["concept_not_found"], "output": {}})
            continue
        output = generate_voice_script(
            concept,
            task_type=voice_type,
            difficulty=difficulty,
            teaching_view=teaching_view,
        )
        issues = validate(case, output)
        results.append({"case": case, "status": "PASS" if not issues else "FAIL", "issues": issues, "output": output})

    scripts = [r["output"].get("script", "") for r in results if r.get("output")]
    pair_scores = [similarity(a, b) for a, b in combinations(scripts, 2)]
    average_similarity = sum(pair_scores) / len(pair_scores) if pair_scores else 1.0
    voice_difference_score = round(max(0.0, 1.0 - average_similarity), 4)
    type_scripts = {}
    type_duplicate = False
    for r in results:
        task_type = r["case"]["voice_type"]
        script = r["output"].get("script", "")
        if task_type in type_scripts and type_scripts[task_type] == script:
            type_duplicate = True
        type_scripts[task_type] = script
    py_teaching = [r for r in results if r["case"]["domain"] == "Python" and r["case"]["concept_name"] == "Variables" and r["case"]["voice_type"] == "teaching_voice_script"]
    difficulty_unique = len({r["output"].get("script", "") for r in py_teaching}) == len(py_teaching)
    pass_count = sum(1 for r in results if r["status"] == "PASS")
    fail_count = len(results) - pass_count
    overall_issues = []
    if not difficulty_unique:
        overall_issues.append("easy_medium_hard_scripts_not_different")
    if type_duplicate:
        overall_issues.append("voice_type_duplicate_script")
    if voice_difference_score < 0.55:
        overall_issues.append("low_voice_difference_score")
    status = "PASS" if fail_count == 0 and not overall_issues else ("WARN" if fail_count == 0 else "FAIL")
    report = {
        "status": status,
        "voice_cases_tested": len(results),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "voice_difference_score": voice_difference_score,
        "overall_issues": overall_issues,
        "results": results,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(
        "# Voice Script Generation Test\n\n"
        + "\n".join(
            [
                f"- status: {status}",
                f"- voice_cases_tested: {len(results)}",
                f"- pass_count: {pass_count}",
                f"- fail_count: {fail_count}",
                f"- voice_difference_score: {voice_difference_score}",
                f"- overall_issues: {overall_issues}",
            ]
        )
        + "\n\n"
        + "\n".join(f"- {r['case']['domain']} {r['case']['concept_name']} {r['case']['voice_type']}: {r['status']} {r['issues']}" for r in results)
        + "\n",
        encoding="utf-8",
    )
    print(f"voice_cases_tested: {len(results)}")
    print(f"pass_count: {pass_count}")
    print(f"fail_count: {fail_count}")
    print(f"voice_difference_score: {voice_difference_score}")
    print(f"status: {status}")


if __name__ == "__main__":
    main()
