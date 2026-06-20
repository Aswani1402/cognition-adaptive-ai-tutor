from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

from tutor.evaluation.rubric_evaluator import evaluate_answer_with_rubric
from tutor.evaluation.semantic_answer_evaluator import SemanticAnswerEvaluator


JSON_REPORT = Path("evaluation_outputs/json/semantic_evaluator_report.json")
MD_REPORT = Path("evaluation_outputs/reports/semantic_evaluator_report.md")


CASES = [
    {
        "case_id": "correct_explanation_strong",
        "task_type": "explanation",
        "concept_name": "variable",
        "learner_answer": "A variable stores a value with a name so the program can reuse that value later.",
        "expected_answer": "A variable stores a value with a name so it can be reused later in a program.",
        "key_points": ["stores a value", "has a name", "can be reused later"],
    },
    {
        "case_id": "transfer_question_strong",
        "task_type": "transfer_question",
        "concept_name": "variables",
        "learner_answer": "In a billing program, variables can store price and quantity, then reuse them to calculate the total.",
        "expected_answer": "Variables can store real-world values such as prices and quantities for later calculations.",
        "key_points": ["store prices", "store quantities", "calculate total"],
    },
    {
        "case_id": "rubric_fusion_case",
        "task_type": "explanation",
        "concept_name": "list",
        "learner_answer": "A list stores multiple values in order and can be indexed.",
        "expected_answer": "A list stores multiple ordered values and supports indexing.",
        "key_points": ["multiple values", "ordered", "indexing"],
        "rubric_output": {"overall_score": 0.9, "quality_label": "strong"},
    },
    {
        "case_id": "explanation_partial",
        "task_type": "explanation_check",
        "concept_name": "variable",
        "learner_answer": "A variable stores data.",
        "expected_answer": "A variable stores a value with a name so it can be reused later.",
        "key_points": ["stores a value", "has a name", "can be reused later"],
    },
    {
        "case_id": "challenge_text_partial",
        "task_type": "challenge_question",
        "concept_name": "accumulator loop",
        "learner_answer": "First initialize the total, then loop through each number and add it to the total.",
        "expected_answer": "Initialize an accumulator, iterate through the numbers, and update the accumulator each step.",
        "key_points": ["initialize accumulator", "iterate numbers", "update total"],
    },
    {
        "case_id": "transfer_question_partial",
        "task_type": "transfer_question",
        "concept_name": "variables",
        "learner_answer": "Use a variable for the price.",
        "expected_answer": "Variables can store prices and quantities and reuse them in a calculation.",
        "key_points": ["store prices", "store quantities", "reuse in calculation"],
    },
    {
        "case_id": "irrelevant_explanation",
        "task_type": "explanation",
        "concept_name": "loop",
        "learner_answer": "The weather is cold and the sky is blue.",
        "expected_answer": "A loop repeats a block of code while a condition is true.",
        "key_points": ["repeats code", "condition controls the loop"],
    },
    {
        "case_id": "short_vague_answer",
        "task_type": "explanation",
        "concept_name": "variable",
        "learner_answer": "It stores things.",
        "expected_answer": "A variable stores a named value so it can be reused.",
        "key_points": ["named value", "reused"],
    },
    {
        "case_id": "empty_answer",
        "task_type": "doubt_followup",
        "concept_name": "condition",
        "learner_answer": "",
        "expected_answer": "A condition is an expression that evaluates to true or false.",
        "key_points": ["expression", "true or false"],
    },
]


def build_report() -> dict[str, Any]:
    evaluator = SemanticAnswerEvaluator()
    results = []
    for case in CASES:
        question = {
            "question_type": case["task_type"],
            "expected_answer": case["expected_answer"],
            "concept_name": case["concept_name"],
        }
        rubric = case.get("rubric_output") or evaluate_answer_with_rubric(question, case["learner_answer"])
        semantic = evaluator.evaluate(
            learner_answer=case["learner_answer"],
            expected_answer=case["expected_answer"],
            key_points=case["key_points"],
            concept_name=case["concept_name"],
            task_type=case["task_type"],
            rubric_output=rubric,
        )
        combined = round(0.75 * float(semantic["score"]) + 0.25 * float(rubric.get("overall_score", 0.0)), 4)
        results.append(
            {
                "case_id": case["case_id"],
                "task_type": case["task_type"],
                "old_rubric_score": rubric.get("overall_score"),
                "old_rubric_label": rubric.get("quality_label"),
                "semantic_score": semantic["score"],
                "semantic_label": semantic["label"],
                "combined_semantic_rubric_score": combined,
                "semantic_similarity": semantic["semantic_similarity"],
                "key_point_coverage": semantic["key_point_coverage"],
                "rubric_score_used": semantic["rubric_score"],
                "structure_score": semantic["structure_score"],
                "method": semantic["method"],
            }
        )

    methods = Counter(item["method"] for item in results)
    labels = Counter(item["semantic_label"] for item in results)
    report = {
        "status": "success",
        "module": "semantic_evaluator_report",
        "case_count": len(results),
        "label_distribution": dict(labels),
        "average_semantic_similarity": round(mean([item["semantic_similarity"] for item in results]), 6),
        "average_key_point_coverage": round(mean([item["key_point_coverage"] for item in results]), 6),
        "average_final_score": round(mean([item["semantic_score"] for item in results]), 6),
        "route_coverage": sorted(set(item["task_type"] for item in results)),
        "method_used": dict(methods),
        "results": results,
        "threshold_note": (
            "Strong/partial/weak thresholds are aligned with existing evaluator labels "
            "and should be calibrated further with human-rated answers."
        ),
        "limitations": [
            "This report uses curated test cases, not a human-labeled benchmark.",
            "TF-IDF cosine is local and transparent but weaker than a calibrated domain-specific embedding model.",
            "Key-point coverage still depends on quality of expected key points.",
        ],
    }
    return report


def write_reports(report: dict[str, Any]) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Semantic Evaluator Report",
        "",
        f"Status: **{report['status']}**",
        "",
        f"- Cases: {report['case_count']}",
        f"- Label distribution: {report['label_distribution']}",
        f"- Average semantic similarity: {report['average_semantic_similarity']}",
        f"- Average key-point coverage: {report['average_key_point_coverage']}",
        f"- Average final score: {report['average_final_score']}",
        f"- Methods used: {report['method_used']}",
        "",
        "## Case Results",
        "",
    ]
    for item in report["results"]:
        lines.append(
            f"- {item['case_id']}: task={item['task_type']}, old_rubric={item['old_rubric_score']}, "
            f"semantic={item['semantic_score']} ({item['semantic_label']}), combined={item['combined_semantic_rubric_score']}"
        )
    lines.extend(["", "## Threshold Note", "", report["threshold_note"], "", "## Limitations", ""])
    for limitation in report["limitations"]:
        lines.append(f"- {limitation}")
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_report()
    write_reports(report)
    print(f"STATUS: {report['status']}")
    print("MODULE: semantic_evaluator_report")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
