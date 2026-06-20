import json
import re
from collections import Counter
from typing import Any, Dict, List, Tuple

from scripts.structured_generation_common import ROOT_DIR
from src.model_content_validator import DOMAIN_FORBIDDEN, normalize_choice, parse_json_object, words


IN_JSON = ROOT_DIR / "outputs" / "evaluation" / "structured_generation_expanded_micro_eval.json"
OUT_JSON = ROOT_DIR / "outputs" / "evaluation" / "structured_generation_quality_inspection.json"
OUT_MD = ROOT_DIR / "outputs" / "evaluation" / "structured_generation_quality_inspection.md"
MCQ_ANALYSIS_JSON = ROOT_DIR / "outputs" / "evaluation" / "structured_mcq_failure_analysis.json"
MCQ_ANALYSIS_MD = ROOT_DIR / "outputs" / "evaluation" / "structured_mcq_failure_analysis.md"

JSON_TASKS = {"flashcard", "mcq", "debug_task", "output_prediction", "challenge_question"}
DOMAIN_VOCAB = {
    "Python": {"python", "variable", "type", "loop", "function", "class", "object", "file", "print", "assignment", "return", "condition"},
    "SQL": {"sql", "select", "insert", "from", "where", "join", "group", "window", "cte", "query", "table", "row", "dbms", "database"},
    "HTML": {"html", "tag", "element", "attribute", "form", "input", "accessibility", "service", "worker", "component", "content", "page"},
    "Git": {"git", "add", "commit", "push", "branch", "merge", "rebase", "submodule", "log", "status", "remote", "history"},
    "Data Structures": {"stack", "queue", "array", "linked", "list", "tree", "graph", "set", "node", "pointer", "lifo", "fifo", "index"},
}


def norm(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def token_set(text: Any) -> set:
    return {token for token in words(text) if len(token) >= 3}


def has_domain_noise(text: str, domain: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in DOMAIN_FORBIDDEN.get(domain, []))


def concept_relevant(item: Dict[str, Any], *parts: Any) -> bool:
    text = " ".join(str(part or "") for part in parts)
    signals = token_set(item.get("concept_name")) | token_set(item.get("domain"))
    signals = {signal for signal in signals if signal not in {"and", "the", "for"}}
    text_tokens = token_set(text)
    if signals and text_tokens & signals:
        return True
    for signal in signals:
        if signal.endswith("s") and signal[:-1] in text_tokens:
            return True
        if f"{signal}s" in text_tokens:
            return True
    return False


def option_domain_relevant(item: Dict[str, Any], option: Any) -> bool:
    text_tokens = token_set(option)
    domain_vocab = DOMAIN_VOCAB.get(item.get("domain", ""), set())
    return bool(text_tokens & domain_vocab) or concept_relevant(item, option)


def repeated_nonsense(text: str) -> bool:
    toks = words(text)
    if len(toks) < 12:
        return False
    counts = Counter(toks)
    return counts.most_common(1)[0][1] / len(toks) > 0.28


def score_from_checks(checks: List[bool]) -> float:
    if not checks:
        return 1.0
    return round(sum(1 for check in checks if check) / len(checks), 4)


def inspect_mcq(item: Dict[str, Any]) -> Tuple[float, float, List[str]]:
    issues = []
    parsed = parse_json_object(item.get("output", ""))
    if not parsed:
        return 0.0, 0.0, ["mcq_broken_json"]
    options = parsed.get("options")
    answer = parsed.get("answer")
    question = str(parsed.get("question", ""))
    explanation = str(parsed.get("explanation", ""))
    checks = [
        isinstance(options, list) and len(options) == 4,
        bool(answer),
        isinstance(options, list) and normalize_choice(answer) in {normalize_choice(option) for option in options},
        bool(explanation),
        concept_relevant(item, question, explanation, answer),
        not has_domain_noise(json.dumps(parsed, ensure_ascii=False), item.get("domain", "")),
    ]
    option_checks = []
    if isinstance(options, list):
        normalized = [norm(option) for option in options]
        option_checks.extend(
            [
                len(options) == 4,
                len(set(normalized)) == len(normalized),
                all(len(words(option)) >= 3 for option in options),
                all(option_domain_relevant(item, option) for option in options),
                not any("random" in norm(option) or "lorem" in norm(option) for option in options),
            ]
        )
        if len(set(normalized)) != len(normalized):
            issues.append("mcq_duplicate_options")
    else:
        issues.append("mcq_options_not_list")
    if not checks[0]:
        issues.append("mcq_not_exactly_4_options")
    if not checks[2]:
        issues.append("mcq_answer_not_in_options")
    if not checks[4]:
        issues.append("mcq_question_not_target_concept")
    if not concept_relevant(item, explanation, answer):
        issues.append("mcq_explanation_weak_or_unrelated")
        checks.append(False)
    return score_from_checks(checks), score_from_checks(option_checks), issues


def inspect_json_task(item: Dict[str, Any]) -> Tuple[float, List[str]]:
    task = item["task_type"]
    parsed = parse_json_object(item.get("output", ""))
    if not parsed:
        return 0.0, [f"{task}_broken_json"]
    text = json.dumps(parsed, ensure_ascii=False)
    issues = []
    if task == "flashcard":
        checks = [
            bool(parsed.get("front")),
            bool(parsed.get("back")),
            "?" in str(parsed.get("front", "")) or "what" in norm(parsed.get("front", "")),
            concept_relevant(item, parsed.get("front"), parsed.get("back")),
            not has_domain_noise(text, item.get("domain", "")),
        ]
        if not checks[2]:
            issues.append("flashcard_front_not_recall_prompt")
    elif task == "debug_task":
        checks = [
            bool(parsed.get("buggy_code")),
            bool(parsed.get("expected_fix")),
            bool(parsed.get("hint")),
            bool(parsed.get("explanation")),
            concept_relevant(item, text),
            token_set(parsed.get("buggy_code")) & token_set(parsed.get("expected_fix")) != set(),
            not has_domain_noise(text, item.get("domain", "")),
        ]
        if not checks[5]:
            issues.append("debug_bug_fix_not_related")
    elif task == "output_prediction":
        checks = [
            bool(parsed.get("code")),
            bool(parsed.get("answer")),
            bool(parsed.get("explanation")),
            concept_relevant(item, text),
            not has_domain_noise(text, item.get("domain", "")),
        ]
        simple_code = str(parsed.get("code", ""))
        if "print(x)" in simple_code and "x = 20" in simple_code and str(parsed.get("answer", "")).strip() != "20":
            checks.append(False)
            issues.append("output_prediction_answer_mismatch")
    elif task == "challenge_question":
        checks = [
            bool(parsed.get("challenge")),
            bool(parsed.get("solution_outline")),
            concept_relevant(item, parsed.get("challenge"), parsed.get("solution_outline")),
            len(words(parsed.get("solution_outline"))) >= 6,
            not has_domain_noise(text, item.get("domain", "")),
        ]
    else:
        checks = [concept_relevant(item, text), not has_domain_noise(text, item.get("domain", ""))]
    if not checks[-1]:
        issues.append("unrelated_domain_terms")
    return score_from_checks(checks), issues


def inspect_text_task(item: Dict[str, Any]) -> Tuple[float, List[str]]:
    task = item["task_type"]
    text = str(item.get("output", ""))
    lowered = text.lower()
    issues = []
    if task == "explanation":
        checks = [
            all(heading.lower() in lowered for heading in ["Concept:", "Definition:", "Example:", "Why it matters:"]),
            len(words(text)) >= 16,
            concept_relevant(item, text),
            "example:" in lowered and len(text.split("Example:", 1)[-1].split("Why it matters:", 1)[0].strip()) >= 6,
            not repeated_nonsense(text),
            not has_domain_noise(text, item.get("domain", "")),
        ]
        if not checks[3]:
            issues.append("explanation_example_not_concrete")
    elif task == "hint":
        checks = [
            lowered.startswith("hint:"),
            8 <= len(words(text)) <= 35,
            concept_relevant(item, text),
            not has_domain_noise(text, item.get("domain", "")),
        ]
    elif task == "revision_summary":
        checks = [
            all(heading.lower() in lowered for heading in ["Summary:", "Remember:", "Avoid this mistake:"]),
            len(words(text)) >= 14,
            concept_relevant(item, text),
            not repeated_nonsense(text),
            not has_domain_noise(text, item.get("domain", "")),
        ]
    else:
        checks = [len(words(text)) >= 8, concept_relevant(item, text), not has_domain_noise(text, item.get("domain", ""))]
    if not concept_relevant(item, text):
        issues.append("concept_or_domain_irrelevant")
    if repeated_nonsense(text):
        issues.append("repeated_nonsense")
    if has_domain_noise(text, item.get("domain", "")):
        issues.append("unrelated_domain_terms")
    return score_from_checks(checks), issues


def style_match(item: Dict[str, Any]) -> bool:
    task = item["task_type"]
    output = str(item.get("output", "")).strip()
    if task in JSON_TASKS:
        return parse_json_object(output) is not None
    expected = {
        "explanation": ["Concept:", "Definition:", "Example:", "Why it matters:"],
        "hint": ["Hint:"],
        "revision_summary": ["Summary:", "Remember:", "Avoid this mistake:"],
    }
    return all(marker.lower() in output.lower() for marker in expected.get(task, []))


def main() -> None:
    report = json.loads(IN_JSON.read_text(encoding="utf-8"))
    results = report.get("results", [])
    expanded_summary = report.get("summary", {})
    output_counts = Counter(norm(item.get("output")) for item in results)
    duplicate_output_count = sum(1 for output, count in output_counts.items() if output and count > 1)
    repeated_outputs = sum(count for output, count in output_counts.items() if output and count > 1)
    repetition_rate = round(repeated_outputs / len(results), 4) if results else 0.0

    item_reports = []
    semantic_scores = []
    logical_scores = []
    domain_scores = []
    style_scores = []
    mcq_scores = []
    option_scores = []

    for item in results:
        task = item["task_type"]
        issues: List[str] = []
        option_score = None
        if task == "mcq":
            semantic_score, option_score, task_issues = inspect_mcq(item)
            mcq_scores.append(semantic_score)
            option_scores.append(option_score)
        elif task in JSON_TASKS:
            semantic_score, task_issues = inspect_json_task(item)
        else:
            semantic_score, task_issues = inspect_text_task(item)
        issues.extend(task_issues)
        output = str(item.get("output", ""))
        logical_score = 0.0 if not item.get("valid") else semantic_score
        domain_score = 0.0 if has_domain_noise(output, item.get("domain", "")) or not concept_relevant(item, output) else 1.0
        style_score = 1.0 if style_match(item) else 0.0
        semantic_scores.append(semantic_score)
        logical_scores.append(logical_score)
        domain_scores.append(domain_score)
        style_scores.append(style_score)
        passed = (
            item.get("valid") is True
            and item.get("website_ready") is True
            and semantic_score >= 0.85
            and logical_score >= 0.85
            and domain_score >= 0.85
            and style_score >= 0.85
        )
        if task == "mcq" and (semantic_score < 0.85 or (option_score or 0.0) < 0.85):
            passed = False
        item_reports.append(
            {
                "concept_id": item.get("concept_id"),
                "concept_name": item.get("concept_name"),
                "domain": item.get("domain"),
                "task_type": task,
                "valid": item.get("valid"),
                "website_ready": item.get("website_ready"),
                "semantic_score": semantic_score,
                "logical_score": logical_score,
                "domain_score": domain_score,
                "style_score": style_score,
                "option_score": option_score,
                "issues": issues,
                "validation_issues": item.get("issues", []),
                "passed_quality": passed,
                "output": item.get("output", ""),
            }
        )

    failed_quality_items = [item for item in item_reports if not item["passed_quality"]]
    avg = lambda values: round(sum(values) / len(values), 4) if values else 1.0
    semantic_quality_score = avg(semantic_scores)
    logical_consistency_score = avg(logical_scores)
    domain_relevance_score = avg(domain_scores)
    style_match_score = avg(style_scores)
    mcq_quality_score = avg(mcq_scores)
    option_quality_score = avg(option_scores)
    teaching_variation_score = round(max(0.0, 1.0 - repetition_rate - (duplicate_output_count / max(1, len(results)))), 4)

    pass_rule = (
        expanded_summary.get("valid_rate", 0) >= 0.85
        and expanded_summary.get("avg_quality_score", 0) >= 0.85
        and expanded_summary.get("website_ready_rate", 0) >= 0.85
        and semantic_quality_score >= 0.85
        and logical_consistency_score >= 0.85
        and mcq_quality_score >= 0.85
        and teaching_variation_score >= 0.75
        and repetition_rate <= 0.15
    )
    summary = {
        "semantic_quality_score": semantic_quality_score,
        "mcq_quality_score": mcq_quality_score,
        "option_quality_score": option_quality_score,
        "teaching_variation_score": teaching_variation_score,
        "style_match_score": style_match_score,
        "logical_consistency_score": logical_consistency_score,
        "domain_relevance_score": domain_relevance_score,
        "repetition_rate": repetition_rate,
        "duplicate_output_count": duplicate_output_count,
        "failed_quality_items": len(failed_quality_items),
        "status": "PASS" if pass_rule else ("WARN" if results else "FAIL"),
        "core_generation_allowed": bool(pass_rule),
    }
    inspection = {
        "expanded_micro_summary": expanded_summary,
        "summary": summary,
        "failed_quality_examples": failed_quality_items[:20],
        "item_reports": item_reports,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(inspection, indent=2, ensure_ascii=False), encoding="utf-8")

    mcq_failures = [
        {
            "concept_name": item.get("concept_name"),
            "domain": item.get("domain"),
            "raw_output": item.get("output"),
            "validation_issues": item.get("validation_issues"),
            "quality_issues": item.get("issues"),
            "semantic_score": item.get("semantic_score"),
            "option_score": item.get("option_score"),
            "valid": item.get("valid"),
            "passed_quality": item.get("passed_quality"),
        }
        for item in item_reports
        if item.get("task_type") == "mcq" and (not item.get("valid") or not item.get("passed_quality"))
    ]
    mcq_analysis = {
        "mcq_attempted_count": sum(1 for item in item_reports if item.get("task_type") == "mcq"),
        "mcq_failed_count": len(mcq_failures),
        "mcq_failures": mcq_failures,
    }
    MCQ_ANALYSIS_JSON.write_text(json.dumps(mcq_analysis, indent=2, ensure_ascii=False), encoding="utf-8")
    mcq_lines = [
        "# Structured MCQ Failure Analysis",
        "",
        f"- mcq_attempted_count: {mcq_analysis['mcq_attempted_count']}",
        f"- mcq_failed_count: {mcq_analysis['mcq_failed_count']}",
    ]
    for item in mcq_failures:
        mcq_lines.extend(
            [
                "",
                f"## {item['domain']} - {item['concept_name']}",
                f"- valid: {item['valid']}",
                f"- passed_quality: {item['passed_quality']}",
                f"- validation_issues: {item['validation_issues']}",
                f"- quality_issues: {item['quality_issues']}",
                f"- semantic_score: {item['semantic_score']}",
                f"- option_score: {item['option_score']}",
                "",
                "```text",
                str(item["raw_output"]),
                "```",
            ]
        )
    if not mcq_failures:
        mcq_lines.append("- None")
    MCQ_ANALYSIS_MD.write_text("\n".join(mcq_lines) + "\n", encoding="utf-8")

    lines = ["# Structured Generation Quality Inspection", ""]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Failed Quality Items"])
    if failed_quality_items:
        for item in failed_quality_items[:20]:
            lines.extend(
                [
                    "",
                    f"### {item['domain']} {item['concept_name']} - {item['task_type']}",
                    f"- issues: {item['issues']}",
                    f"- semantic_score: {item['semantic_score']}",
                    f"- logical_score: {item['logical_score']}",
                    f"- style_score: {item['style_score']}",
                    "",
                    "```text",
                    str(item["output"]),
                    "```",
                ]
            )
    else:
        lines.append("- None")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"semantic_quality_score: {semantic_quality_score}")
    print(f"mcq_quality_score: {mcq_quality_score}")
    print(f"option_quality_score: {option_quality_score}")
    print(f"teaching_variation_score: {teaching_variation_score}")
    print(f"style_match_score: {style_match_score}")
    print(f"logical_consistency_score: {logical_consistency_score}")
    print(f"domain_relevance_score: {domain_relevance_score}")
    print(f"repetition_rate: {repetition_rate}")
    print(f"duplicate_output_count: {duplicate_output_count}")
    print(f"failed_quality_items: {len(failed_quality_items)}")
    print(f"status: {summary['status']}")
    print(f"core_generation_allowed: {summary['core_generation_allowed']}")


if __name__ == "__main__":
    main()
