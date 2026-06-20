import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from src.generate import (
    build_prompt as build_training_style_prompt,
    clean_generated_answer,
    extract_json_object,
    generate_text,
    get_device,
    load_checkpoint,
)
from src.model_content_validator import validate_model_output
from src.rag_connector import RagConnector
from src.rag_grounded_live_generator import (
    DEFAULT_CHECKPOINT,
    FORMAT_EXAMPLES,
    FORMAT_RULES,
    STRUCTURED_TASKS,
    TASK_TOKENS,
    build_compact_prompt,
    build_short_rag_context,
    calculate_grounding_score,
    quality_score,
)
from src.tokenizer_wrapper import CogniTutorTokenizer


ROOT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT_DIR / "outputs" / "diagnostics"
OUTPUT_JSON = OUTPUT_DIR / "structured_generation_prompt_diagnosis.json"
OUTPUT_MD = OUTPUT_DIR / "structured_generation_prompt_diagnosis.md"


TASKS = [
    {
        "concept_id": "S2",
        "concept_name": "SQL SELECT Queries",
        "domain": "SQL",
        "task_type": "mcq",
        "style": "simple",
        "query": "SQL SELECT Queries mcq retrieve columns from tables",
    },
    {
        "concept_id": "P4",
        "concept_name": "Python Loops",
        "domain": "Python",
        "task_type": "debug_task",
        "style": "code_first",
        "query": "Python Loops debug task for loop colon enumerate iterable",
    },
    {
        "concept_id": "G3",
        "concept_name": "Git Commits and History",
        "domain": "Git",
        "task_type": "revision_summary",
        "style": "revision_summary",
        "query": "Git Commits and History revision summary staged changes commit history",
    },
    {
        "concept_id": "D4",
        "concept_name": "Data Structures Stack",
        "domain": "Data Structures",
        "task_type": "challenge_question",
        "style": "challenge_based",
        "query": "Data Structures Stack LIFO push pop stack challenge",
    },
]


def first_context_line(context_text: str) -> str:
    for line in str(context_text or "").splitlines():
        line = line.strip().lstrip("- ").strip()
        if line and not line.endswith(":"):
            return line
    return ""


def context_section(context_text: str, section_name: str) -> str:
    lines = str(context_text or "").splitlines()
    active = False
    collected = []
    for line in lines:
        stripped = line.strip()
        if stripped == f"{section_name}:":
            active = True
            continue
        if active and stripped.endswith(":") and not stripped.startswith("-"):
            break
        if active and stripped:
            collected.append(stripped.lstrip("- ").strip())
    return " | ".join(collected)


def build_format_b(task: Dict[str, Any], context_text: str) -> str:
    task_type = task["task_type"]
    return f"""<bos>
{TASK_TOKENS[task_type]}
<concept> {task['concept_name']}
<domain> {task['domain']}
<context> {first_context_line(context_text)}
<format_rule> {FORMAT_RULES[task_type]}
<answer>"""


def build_format_c(task: Dict[str, Any], context_text: str) -> str:
    return build_training_style_prompt(
        concept_name=task["concept_name"],
        domain=task["domain"],
        difficulty="easy",
        learner_state="low_mastery",
        teaching_style=task["style"],
        task_type=task["task_type"],
        base_content=context_section(context_text, "Definition"),
        key_points=context_section(context_text, "Key points"),
        misconceptions=context_section(context_text, "Misconception"),
        examples=context_section(context_text, "Example"),
    )


def build_format_d(task: Dict[str, Any]) -> str:
    task_type = task["task_type"]
    return f"""<bos>
<instruction> Generate only the required answer. Do not add explanations outside the required format.
{TASK_TOKENS[task_type]}
<concept> {task['concept_name']}
<domain> {task['domain']}
<format_rule>
{FORMAT_RULES[task_type]}
</format_rule>
<answer>"""


def build_format_e(task: Dict[str, Any], context_text: str) -> str:
    task_type = task["task_type"]
    return f"""<bos>
<instruction> Generate tutor output in exactly the required format.
{TASK_TOKENS[task_type]}
<concept> {task['concept_name']}
<domain> {task['domain']}
<format_example>
{FORMAT_EXAMPLES[task_type]}
</format_example>
<context>
{context_text}
</context>
<format_rule>
{FORMAT_RULES[task_type]}
</format_rule>
<answer>"""


def build_prompts(task: Dict[str, Any], context_text: str) -> Dict[str, str]:
    return {
        "Format A": build_compact_prompt(
            concept_name=task["concept_name"],
            domain=task["domain"],
            task_type=task["task_type"],
            short_context=context_text,
            difficulty="easy",
            teaching_style=task["style"],
        ),
        "Format B": build_format_b(task, context_text),
        "Format C": build_format_c(task, context_text),
        "Format D": build_format_d(task),
        "Format E": build_format_e(task, context_text),
    }


def common_failure_reason(results: List[Dict[str, Any]]) -> str:
    failures = []
    for item in results:
        if item["valid"]:
            continue
        failures.extend(item.get("issues") or ["invalid output"])
    if not failures:
        return "none"
    return Counter(failures).most_common(1)[0][0]


def best_prompt_format(results: List[Dict[str, Any]]) -> str:
    valid_results = [item for item in results if item["valid"]]
    if valid_results:
        return sorted(
            valid_results,
            key=lambda item: (item["quality_score"], item["grounding_score"]),
            reverse=True,
        )[0]["prompt_format"]

    return sorted(
        results,
        key=lambda item: (item["quality_score"], item["grounding_score"]),
        reverse=True,
    )[0]["prompt_format"]


def final_recommendation(all_results: List[Dict[str, Any]]) -> str:
    valid_by_task = {}
    for item in all_results:
        key = item["task_type"]
        valid_by_task.setdefault(key, 0)
        if item["valid"]:
            valid_by_task[key] += 1

    if not any(valid_by_task.values()):
        return (
            "No prompt format produced valid structured outputs. The current checkpoint cannot "
            "reliably generate structured MCQ/debug/challenge outputs without retraining or a "
            "separate constrained decoding strategy."
        )

    weak_tasks = [task_type for task_type, count in valid_by_task.items() if count == 0]
    if weak_tasks:
        return (
            "Some prompt formats work for at least one task, but the current checkpoint remains "
            f"unreliable for: {', '.join(weak_tasks)}. Do not proceed to core generation."
        )

    return (
        "Every diagnosed task has at least one valid prompt format. Use only the validated "
        "formats in another micro test before considering core generation."
    )


def build_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Structured Generation Prompt Diagnosis",
        "",
        f"Final recommendation: {report['final_recommendation']}",
        "",
    ]

    for task_report in report["task_reports"]:
        lines.extend(
            [
                f"## {task_report['task_type']} - {task_report['concept_name']}",
                "",
                f"- best_prompt_format: {task_report['best_prompt_format']}",
                f"- valid_count: {task_report['valid_count']}",
                f"- common_failure_reason: {task_report['common_failure_reason']}",
                "",
            ]
        )

        for result in task_report["results"]:
            lines.extend(
                [
                    f"### {result['prompt_format']}",
                    "",
                    f"- valid: {result['valid']}",
                    f"- grounding_score: {result['grounding_score']}",
                    f"- quality_score: {result['quality_score']}",
                    f"- issues: {result['issues']}",
                    "",
                    "Prompt:",
                    "```text",
                    result["prompt"],
                    "```",
                    "",
                    "Raw output:",
                    "```text",
                    result["raw_output"],
                    "```",
                    "",
                ]
            )

    return "\n".join(lines)


def main() -> None:
    device = get_device()
    model, _, _ = load_checkpoint(DEFAULT_CHECKPOINT, device)
    tokenizer = CogniTutorTokenizer()
    rag = RagConnector()

    task_reports = []
    all_results = []

    for task in TASKS:
        rag_result = rag.get_rag_context(
            query=task["query"],
            concept_id=task["concept_id"],
            domain=task["domain"],
            top_k=5,
        )
        short_context = build_short_rag_context(rag_result, max_chars=700)
        context_text = short_context["context_text"]
        prompt_map = build_prompts(task, context_text)

        task_results = []
        for prompt_format, prompt in prompt_map.items():
            raw_output, _ = generate_text(
                model=model,
                tokenizer=tokenizer,
                prompt=prompt,
                device=device,
                max_new_tokens=150,
                temperature=0.45,
                top_k=35,
            )
            raw_output = clean_generated_answer(raw_output)
            if task["task_type"] in STRUCTURED_TASKS:
                raw_output = extract_json_object(raw_output)

            grounding_score = calculate_grounding_score(
                output=raw_output,
                concept_name=task["concept_name"],
                context_text=context_text,
            )
            validation = validate_model_output(
                task_type=task["task_type"],
                generated_text=raw_output,
                concept_name=task["concept_name"],
                domain=task["domain"],
                context_text=context_text,
                grounding_score=grounding_score,
            )

            result = {
                "concept_id": task["concept_id"],
                "concept_name": task["concept_name"],
                "domain": task["domain"],
                "task_type": task["task_type"],
                "prompt_format": prompt_format,
                "prompt": prompt,
                "raw_output": raw_output,
                "valid": validation["valid"],
                "issues": validation.get("errors", []) + validation.get("warnings", []),
                "grounding_score": grounding_score,
                "quality_score": quality_score(validation),
            }
            task_results.append(result)
            all_results.append(result)

        task_report = {
            "concept_name": task["concept_name"],
            "domain": task["domain"],
            "task_type": task["task_type"],
            "best_prompt_format": best_prompt_format(task_results),
            "valid_count": sum(1 for item in task_results if item["valid"]),
            "common_failure_reason": common_failure_reason(task_results),
            "results": task_results,
        }
        task_reports.append(task_report)

    recommendation = final_recommendation(all_results)
    report = {
        "task_reports": task_reports,
        "final_recommendation": recommendation,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    with OUTPUT_MD.open("w", encoding="utf-8") as f:
        f.write(build_markdown(report))

    for task_report in task_reports:
        print(f"task_type: {task_report['task_type']}")
        print(f"best_prompt_format: {task_report['best_prompt_format']}")
        print(f"valid_count: {task_report['valid_count']}")
        print(f"common_failure_reason: {task_report['common_failure_reason']}")
        print(f"final_recommendation: {recommendation}")
        print("")


if __name__ == "__main__":
    main()
