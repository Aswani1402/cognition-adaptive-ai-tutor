from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from tutor.system.orchestrator import run_orchestrator
from tutor.system.teaching_action_mapper import map_teaching_action
from tutor.system.teaching_content_connector import run_teaching_content_connector


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CORE_DB_PATH = PROJECT_ROOT / "external" / "core_data" / "tutor.db"
EVAL_DIR = PROJECT_ROOT / "evaluation_outputs"
JSON_DIR = EVAL_DIR / "json"
REPORT_DIR = EVAL_DIR / "reports"


def now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_dirs() -> None:
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def connect_db(db_path: Path | str = CORE_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def get_distinct_learners(limit: int = 10) -> List[str]:
    with connect_db() as conn:
        rows = conn.execute(
            """
            SELECT learner_id
            FROM quiz_results
            WHERE learner_id IS NOT NULL
            GROUP BY learner_id
            ORDER BY COUNT(*) DESC, learner_id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [str(r["learner_id"]) for r in rows]


def get_recent_concepts_for_learner(learner_id: str, max_concepts: int = 3) -> List[str]:
    with connect_db() as conn:
        rows = conn.execute(
            """
            SELECT concept_id, MAX(quiz_id) AS latest_quiz
            FROM quiz_results
            WHERE learner_id = ?
              AND concept_id IS NOT NULL
              AND TRIM(concept_id) != ''
            GROUP BY concept_id
            ORDER BY latest_quiz DESC
            LIMIT ?
            """,
            (learner_id, max_concepts),
        ).fetchall()
    return [str(r["concept_id"]) for r in rows]


def evaluate_single_case(learner_id: str, concept_id: str) -> Dict[str, Any]:
    connector_output = run_teaching_content_connector(
        learner_id=learner_id,
        concept_id=concept_id,
    )

    orchestrator = connector_output.get("orchestrator", {})
    teaching_action = connector_output.get("teaching_action", {})
    content_result = connector_output.get("content_result", {})

    promotion_result = orchestrator.get("promotion_result", {})
    guess_result = orchestrator.get("guess_result", {})
    review_result = orchestrator.get("review_result", {})
    evidence_summary = orchestrator.get("evidence_summary", {})

    return {
        "learner_id": learner_id,
        "concept_id": concept_id,
        "final_action": orchestrator.get("final_action"),
        "decision_confidence": orchestrator.get("decision_confidence"),
        "promotion_recommendation": promotion_result.get("recommendation"),
        "promotion_confidence": promotion_result.get("promotion_confidence"),
        "guess_level": guess_result.get("guess_level"),
        "guess_score": guess_result.get("guess_score"),
        "review_recommendation": review_result.get("recommendation"),
        "review_need_score": review_result.get("review_need_score"),
        "urgency_level": review_result.get("urgency_level"),
        "mastery_score": evidence_summary.get("mastery_score"),
        "behaviour_risk": evidence_summary.get("behaviour_risk"),
        "decay_priority": evidence_summary.get("decay_priority"),
        "recent_correctness": evidence_summary.get("recent_correctness"),
        "evidence_confidence": evidence_summary.get("evidence_confidence"),
        "teaching_strategy": teaching_action.get("strategy"),
        "content_type": teaching_action.get("content_type"),
        "difficulty": teaching_action.get("difficulty"),
        "content_found": content_result.get("found"),
        "content_concept_id": connector_output.get("content_concept_id"),
        "content_db_path": content_result.get("db_path"),
        "content_match_level": content_result.get("matched_query_level"),
        "content_preview": (
            content_result.get("content", {}).get("content", "")[:220]
            if content_result.get("found")
            else None
        ),
        "full_output": connector_output,
    }


def run_evaluation(
    learner_ids: Optional[List[str]] = None,
    concepts_per_learner: int = 2,
    learner_limit: int = 5,
) -> Dict[str, Any]:
    ensure_dirs()

    if not learner_ids:
        learner_ids = get_distinct_learners(limit=learner_limit)

    cases: List[Dict[str, Any]] = []

    for learner_id in learner_ids:
        concept_ids = get_recent_concepts_for_learner(
            learner_id=learner_id,
            max_concepts=concepts_per_learner,
        )

        for concept_id in concept_ids:
            try:
                case_result = evaluate_single_case(
                    learner_id=learner_id,
                    concept_id=concept_id,
                )
                cases.append(case_result)
            except Exception as e:
                cases.append(
                    {
                        "learner_id": learner_id,
                        "concept_id": concept_id,
                        "error": str(e),
                    }
                )

    tag = now_tag()

    summary = build_summary(cases)

    output = {
        "evaluation_tag": tag,
        "db_path": str(CORE_DB_PATH),
        "num_learners": len(learner_ids),
        "concepts_per_learner": concepts_per_learner,
        "num_cases": len(cases),
        "summary": summary,
        "cases": cases,
    }

    json_path = JSON_DIR / f"adaptive_evaluation_{tag}.json"
    report_path = REPORT_DIR / f"adaptive_evaluation_report_{tag}.md"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(build_markdown_report(output))

    return {
        "status": "ok",
        "evaluation_tag": tag,
        "json_path": str(json_path),
        "report_path": str(report_path),
        "summary": summary,
    }


def build_summary(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    valid_cases = [c for c in cases if "error" not in c]

    if not valid_cases:
        return {
            "valid_cases": 0,
            "error_cases": len(cases),
        }

    final_action_counts: Dict[str, int] = {}
    guess_level_counts: Dict[str, int] = {}
    review_recommendation_counts: Dict[str, int] = {}
    content_found_count = 0

    decision_confidences = []
    promotion_confidences = []
    review_need_scores = []

    for c in valid_cases:
        final_action = str(c.get("final_action"))
        guess_level = str(c.get("guess_level"))
        review_reco = str(c.get("review_recommendation"))

        final_action_counts[final_action] = final_action_counts.get(final_action, 0) + 1
        guess_level_counts[guess_level] = guess_level_counts.get(guess_level, 0) + 1
        review_recommendation_counts[review_reco] = review_recommendation_counts.get(review_reco, 0) + 1

        if c.get("content_found"):
            content_found_count += 1

        if c.get("decision_confidence") is not None:
            decision_confidences.append(float(c["decision_confidence"]))
        if c.get("promotion_confidence") is not None:
            promotion_confidences.append(float(c["promotion_confidence"]))
        if c.get("review_need_score") is not None:
            review_need_scores.append(float(c["review_need_score"]))

    def avg(values: List[float]) -> float:
        return round(sum(values) / len(values), 4) if values else 0.0

    return {
        "valid_cases": len(valid_cases),
        "error_cases": len(cases) - len(valid_cases),
        "final_action_counts": final_action_counts,
        "guess_level_counts": guess_level_counts,
        "review_recommendation_counts": review_recommendation_counts,
        "content_found_count": content_found_count,
        "content_found_rate": round(content_found_count / len(valid_cases), 4) if valid_cases else 0.0,
        "avg_decision_confidence": avg(decision_confidences),
        "avg_promotion_confidence": avg(promotion_confidences),
        "avg_review_need_score": avg(review_need_scores),
    }


def build_markdown_report(output: Dict[str, Any]) -> str:
    summary = output["summary"]
    lines = []

    lines.append("# Adaptive Evaluation Report")
    lines.append("")
    lines.append(f"- Evaluation tag: `{output['evaluation_tag']}`")
    lines.append(f"- DB path: `{output['db_path']}`")
    lines.append(f"- Number of learners: `{output['num_learners']}`")
    lines.append(f"- Cases evaluated: `{output['num_cases']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Valid cases: `{summary.get('valid_cases', 0)}`")
    lines.append(f"- Error cases: `{summary.get('error_cases', 0)}`")
    lines.append(f"- Content found rate: `{summary.get('content_found_rate', 0.0)}`")
    lines.append(f"- Average decision confidence: `{summary.get('avg_decision_confidence', 0.0)}`")
    lines.append(f"- Average promotion confidence: `{summary.get('avg_promotion_confidence', 0.0)}`")
    lines.append(f"- Average review need score: `{summary.get('avg_review_need_score', 0.0)}`")
    lines.append("")
    lines.append("## Final Action Counts")
    lines.append("")

    for k, v in summary.get("final_action_counts", {}).items():
        lines.append(f"- {k}: `{v}`")

    lines.append("")
    lines.append("## Guess Level Counts")
    lines.append("")

    for k, v in summary.get("guess_level_counts", {}).items():
        lines.append(f"- {k}: `{v}`")

    lines.append("")
    lines.append("## Review Recommendation Counts")
    lines.append("")

    for k, v in summary.get("review_recommendation_counts", {}).items():
        lines.append(f"- {k}: `{v}`")

    lines.append("")
    lines.append("## Case Snapshots")
    lines.append("")

    for case in output["cases"][:10]:
        if "error" in case:
            lines.append(f"- Learner `{case['learner_id']}`, concept `{case['concept_id']}` → ERROR: {case['error']}")
            continue

        lines.append(
            f"- Learner `{case['learner_id']}`, concept `{case['concept_id']}` → "
            f"action=`{case['final_action']}`, promotion=`{case['promotion_recommendation']}`, "
            f"guess=`{case['guess_level']}`, review=`{case['review_recommendation']}`, "
            f"content_found=`{case['content_found']}`"
        )

    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    import pprint

    parser = argparse.ArgumentParser()
    parser.add_argument("--learner_limit", type=int, default=5)
    parser.add_argument("--concepts_per_learner", type=int, default=2)
    parser.add_argument("--learner_ids", nargs="*", default=None)
    args = parser.parse_args()

    result = run_evaluation(
        learner_ids=args.learner_ids,
        concepts_per_learner=args.concepts_per_learner,
        learner_limit=args.learner_limit,
    )
    pprint.pp(result)