from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tutor.assessment.puzzle_generator import generate_puzzle_bundle
from tutor.assessment.puzzle_schema import PUZZLE_FRONTEND_COMPONENT_MAP, PUZZLE_TYPES
from tutor.evaluation.puzzle_evaluator import evaluate_puzzle_answer


JSON_REPORT = Path("evaluation_outputs/json/puzzle_assessment_report.json")
MD_REPORT = Path("evaluation_outputs/reports/puzzle_assessment_report.md")


def _correct_answer_for(puzzle: dict[str, Any]) -> Any:
    puzzle_type = puzzle["puzzle_type"]
    if puzzle_type == "fill_blank":
        return {"blanks": puzzle["correct_answer"]}
    if puzzle_type in {"arrange_steps", "drag_order"}:
        return {"order": puzzle["correct_order"]}
    if puzzle_type == "match_pairs":
        return {"pairs": puzzle["correct_answer"]}
    if puzzle_type == "syntax_completion":
        return {"completion": puzzle["correct_answer"]}
    return {"answer": puzzle["correct_answer"]}


def build_report() -> dict[str, Any]:
    bundle = generate_puzzle_bundle("py_variables", "Python Variables", "Python", "easy")
    puzzles = bundle["puzzles"]
    results = [
        evaluate_puzzle_answer(puzzle, _correct_answer_for(puzzle))
        for puzzle in puzzles
    ]
    labels = Counter(result["label"] for result in results)
    components = {
        puzzle["puzzle_type"]: puzzle.get("frontend_component")
        for puzzle in puzzles
    }
    missing_components = [
        puzzle_type
        for puzzle_type in PUZZLE_TYPES
        if components.get(puzzle_type) != PUZZLE_FRONTEND_COMPONENT_MAP[puzzle_type]
    ]
    status = "success" if not missing_components and len(puzzles) >= len(PUZZLE_TYPES) else "warning"
    return {
        "status": status,
        "module": "puzzle_assessment_report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "puzzle_types_supported": PUZZLE_TYPES,
        "generated_puzzle_count": len(puzzles),
        "frontend_components_mapped": components,
        "missing_or_mismatched_components": missing_components,
        "evaluator_test_cases": results,
        "label_distribution": dict(labels),
        "scoring_method": {
            "fill_blank": "score = correct_blanks / total_blanks after normalized exact match",
            "arrange_steps": "score = correct_positions / total_positions; sequence_accuracy mirrors score",
            "drag_order": "score = correct_positions / total_positions; sequence_accuracy mirrors score",
            "match_pairs": "score = correct_pairs / total_pairs",
            "code_puzzle": "score = SafeCodeRunner pass rate when executable output exists, otherwise normalized answer match",
            "syntax_completion": "score = normalized completion exact match",
            "labels": "strong >= 0.8; partial >= 0.45; weak < 0.45",
        },
        "limitations": [
            "Puzzle generation is deterministic and template-based, not LLM-generated.",
            "Code puzzle execution is optional and only used when a safe executable Python snippet is available.",
            "Frontend drag/drop rendering is represented as data schema only in this backend test.",
        ],
        "final_report_wording": (
            "Puzzle-style/gamified assessment extends the tutor beyond MCQ and code-answer tasks. "
            "The backend supports fill-in-the-blank, step arrangement, pair matching, drag ordering, "
            "code puzzles, and syntax completion using structured schemas that can be rendered by the "
            "frontend and evaluated with transparent scoring formulas."
        ),
    }


def write_reports(report: dict[str, Any]) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# Puzzle Assessment Report",
        "",
        f"Status: `{report['status']}`",
        "",
        f"Generated puzzle count: `{report['generated_puzzle_count']}`",
        "",
        "## Puzzle Types Supported",
        "",
        *[f"- {item}" for item in report["puzzle_types_supported"]],
        "",
        "## Frontend Components",
        "",
        *[f"- `{key}` -> `{value}`" for key, value in report["frontend_components_mapped"].items()],
        "",
        "## Label Distribution",
        "",
        *[f"- `{key}`: {value}" for key, value in report["label_distribution"].items()],
        "",
        "## Scoring Method",
        "",
        *[f"- `{key}`: {value}" for key, value in report["scoring_method"].items()],
        "",
        "## Limitations",
        "",
        *[f"- {item}" for item in report["limitations"]],
        "",
        "## Final Report Wording",
        "",
        report["final_report_wording"],
        "",
    ]
    MD_REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    report = build_report()
    write_reports(report)
    print(f"STATUS: {report['status']}")
    print("MODULE: puzzle_assessment_report")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
