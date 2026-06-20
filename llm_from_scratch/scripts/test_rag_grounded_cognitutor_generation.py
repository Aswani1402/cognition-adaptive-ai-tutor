import json
from pathlib import Path
from typing import Any, Dict, List

from src.rag_grounded_live_generator import RagGroundedLiveGenerator


ROOT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT_DIR / "outputs" / "rag_grounded_generation"
OUTPUT_JSON = OUTPUT_DIR / "rag_grounded_generation_test.json"
OUTPUT_MD = OUTPUT_DIR / "rag_grounded_generation_test.md"


TEST_ITEMS = [
    {
        "concept_id": "P1",
        "concept_name": "Python Variables",
        "domain": "Python",
        "task_type": "explanation",
        "teaching_style": "simple",
    },
    {
        "concept_id": "P1",
        "concept_name": "Python Variables",
        "domain": "Python",
        "task_type": "flashcard",
        "teaching_style": "simple",
    },
    {
        "concept_id": "S2",
        "concept_name": "SQL SELECT Queries",
        "domain": "SQL",
        "task_type": "mcq",
        "teaching_style": "simple",
    },
    {
        "concept_id": "P4",
        "concept_name": "Python Loops",
        "domain": "Python",
        "task_type": "debug_task",
        "teaching_style": "code_first",
    },
    {
        "concept_id": "H2",
        "concept_name": "HTML Tags and Elements",
        "domain": "HTML",
        "task_type": "explanation",
        "teaching_style": "simple",
    },
    {
        "concept_id": "G3",
        "concept_name": "Git Commits and History",
        "domain": "Git",
        "task_type": "revision_summary",
        "teaching_style": "revision_summary",
    },
    {
        "concept_id": "D4",
        "concept_name": "Data Structures Stack",
        "domain": "Data Structures",
        "task_type": "challenge_question",
        "teaching_style": "challenge_based",
        "query": "Data Structures Stack LIFO push pop stack challenge",
    },
]


def average(values: List[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)


def summarize(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    attempted = len(TEST_ITEMS)
    success = sum(1 for item in results if item.get("success"))
    valid = sum(1 for item in results if item.get("valid"))
    avg_grounding_score = average([float(item.get("grounding_score") or 0.0) for item in results])
    avg_quality_score = average([float(item.get("quality_score") or 0.0) for item in results])

    if success == attempted and valid == attempted and avg_grounding_score >= 0.5 and avg_quality_score >= 0.7:
        status = "PASS"
    elif success > 0:
        status = "WARN"
    else:
        status = "FAIL"

    return {
        "attempted": attempted,
        "success": success,
        "valid": valid,
        "avg_grounding_score": avg_grounding_score,
        "avg_quality_score": avg_quality_score,
        "status": status,
    }


def build_markdown(report: Dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# RAG-Grounded CogniTutorLM Micro Generation Test",
        "",
        f"- attempted: {summary['attempted']}",
        f"- success: {summary['success']}",
        f"- valid: {summary['valid']}",
        f"- avg_grounding_score: {summary['avg_grounding_score']}",
        f"- avg_quality_score: {summary['avg_quality_score']}",
        f"- status: {summary['status']}",
        "",
    ]

    for item in report["results"]:
        lines.extend(
            [
                f"## {item['domain']} - {item['concept_name']} - {item['task_type']}",
                "",
                f"- success: {item.get('success')}",
                f"- valid: {item.get('valid')}",
                f"- grounding_score: {item.get('grounding_score')}",
                f"- quality_score: {item.get('quality_score')}",
                f"- repair_applied: {item.get('repair_applied')}",
                f"- repair_notes: {item.get('repair_notes', [])}",
                f"- errors: {item.get('validation', {}).get('errors', [])}",
                "",
                "### Raw output",
                "",
                "```text",
                str(item.get("raw_output") or ""),
                "```",
                "",
                "### Final output",
                "",
                "```text",
                str(item.get("output") or ""),
                "```",
                "",
            ]
        )

    return "\n".join(lines)


def main() -> None:
    generator = RagGroundedLiveGenerator()
    results = []

    for item in TEST_ITEMS:
        try:
            results.append(generator.generate_item(item))
        except Exception as exc:
            failed = dict(item)
            failed.update(
                {
                    "success": False,
                    "valid": False,
                    "raw_output": "",
                    "output": "",
                    "repair_applied": False,
                    "repair_notes": [],
                    "issues": [str(exc)],
                    "grounding_score": 0.0,
                    "quality_score": 0.0,
                    "validation": {
                        "valid": False,
                        "errors": [str(exc)],
                        "warnings": [],
                        "parsed": None,
                    },
                }
            )
            results.append(failed)

    summary = summarize(results)
    report = {
        "summary": summary,
        "results": results,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    with OUTPUT_MD.open("w", encoding="utf-8") as f:
        f.write(build_markdown(report))

    print(f"attempted: {summary['attempted']}")
    print(f"success: {summary['success']}")
    print(f"valid: {summary['valid']}")
    print(f"avg_grounding_score: {summary['avg_grounding_score']}")
    print(f"avg_quality_score: {summary['avg_quality_score']}")
    print(f"status: {summary['status']}")


if __name__ == "__main__":
    main()
