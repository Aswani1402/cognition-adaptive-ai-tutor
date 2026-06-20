from __future__ import annotations

from tutor.assessment.puzzle_generator import generate_puzzle_bundle
from tutor.assessment.puzzle_schema import PUZZLE_TYPES
from tutor.evaluation.puzzle_evaluator import evaluate_puzzle_answer


def _by_type(puzzles: list[dict], puzzle_type: str) -> dict:
    return next(puzzle for puzzle in puzzles if puzzle["puzzle_type"] == puzzle_type)


def main() -> None:
    bundle = generate_puzzle_bundle(
        concept_id="py_variables",
        concept_name="Python Variables",
        domain="Python",
        difficulty="easy",
    )
    assert bundle["status"] == "success"
    puzzles = bundle["puzzles"]
    assert set(PUZZLE_TYPES).issubset({puzzle["puzzle_type"] for puzzle in puzzles})
    assert all(puzzle.get("frontend_component") for puzzle in puzzles)

    fill_blank = _by_type(puzzles, "fill_blank")
    arrange_steps = _by_type(puzzles, "arrange_steps")
    match_pairs = _by_type(puzzles, "match_pairs")
    drag_order = _by_type(puzzles, "drag_order")
    syntax_completion = _by_type(puzzles, "syntax_completion")
    code_puzzle = _by_type(puzzles, "code_puzzle")

    results = [
        evaluate_puzzle_answer(fill_blank, {"blanks": fill_blank["correct_answer"]}),
        evaluate_puzzle_answer(
            arrange_steps,
            {"order": list(reversed(arrange_steps["correct_order"]))},
        ),
        evaluate_puzzle_answer(match_pairs, {"pairs": match_pairs["correct_answer"]}),
        evaluate_puzzle_answer(drag_order, {"order": drag_order["correct_order"]}),
        evaluate_puzzle_answer(
            syntax_completion,
            {"completion": syntax_completion["correct_answer"]},
        ),
        evaluate_puzzle_answer(code_puzzle, {"answer": code_puzzle["correct_answer"]}),
    ]

    assert results[0]["score"] == 1.0
    assert results[1]["label"] in {"partial", "weak"}
    assert results[2]["score"] == 1.0
    assert results[3]["score"] == 1.0
    assert results[4]["score"] == 1.0
    assert 0.0 <= results[5]["score"] <= 1.0
    for result in results:
        assert result["status"] == "success"
        assert 0.0 <= result["score"] <= 1.0

    print("STATUS: success")
    print("MODULE: puzzle_assessment_test")


if __name__ == "__main__":
    main()
