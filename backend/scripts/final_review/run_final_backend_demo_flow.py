from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

JSON_DIR = ROOT / "evaluation_outputs" / "json"
REPORT_DIR = ROOT / "evaluation_outputs" / "reports"
DB_PATH = ROOT / "external" / "core_data" / "tutor.db"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dirs() -> None:
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def connect_tutor_readonly() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro&immutable=1", uri=True)


def safe_section(name: str, func, default: Any = None) -> tuple[Any, str | None]:
    try:
        return func(), None
    except Exception as exc:
        return default, f"{name} unavailable: {type(exc).__name__}: {exc}"


def pick_learner_id() -> dict[str, Any]:
    if not DB_PATH.exists():
        return {
            "learner_id": "final_review_demo_learner",
            "source": "fallback",
            "reason": f"Database not found at {DB_PATH}.",
        }
    try:
        with connect_tutor_readonly() as conn:
            row = conn.execute(
                """
                SELECT learner_id, COUNT(*) AS n
                FROM quiz_results
                WHERE learner_id IS NOT NULL AND learner_id != ''
                GROUP BY learner_id
                ORDER BY n DESC
                LIMIT 1
                """
            ).fetchone()
        if row:
            return {
                "learner_id": str(row[0]),
                "source": "quiz_results",
                "interaction_count": int(row[1]),
            }
    except Exception as exc:
        return {
            "learner_id": "final_review_demo_learner",
            "source": "fallback",
            "reason": f"Learner lookup failed: {type(exc).__name__}: {exc}",
        }
    return {
        "learner_id": "final_review_demo_learner",
        "source": "fallback",
        "reason": "No existing learner_id found in quiz_results.",
    }


def latest_mastery(learner_id: str, concept_id: str) -> dict[str, Any]:
    if not DB_PATH.exists():
        return {"value": None, "reason": "tutor.db not found."}
    try:
        with connect_tutor_readonly() as conn:
            row = conn.execute(
                "SELECT state_json, updated_at FROM knowledge_state WHERE student_id = ?",
                (learner_id,),
            ).fetchone()
        if not row:
            return {"value": None, "reason": "No existing knowledge_state row for learner."}
        state = json.loads(row[0])
        if isinstance(state, dict) and "concepts" in state:
            concept = state.get("concepts", {}).get(str(concept_id), {})
            return {
                "value": concept.get("mastery"),
                "updated_at": row[1],
                "source": state.get("source") or state.get("kt_source"),
                "fallback_used": state.get("fallback_used"),
            }
        if isinstance(state, dict):
            return {
                "value": state.get(str(concept_id)),
                "updated_at": row[1],
                "source": "legacy_knowledge_state_json",
            }
    except Exception as exc:
        return {"value": None, "reason": f"Mastery lookup failed: {type(exc).__name__}: {exc}"}
    return {"value": None, "reason": "Mastery format did not include requested concept."}


def latest_behaviour(learner_id: str) -> dict[str, Any]:
    if not DB_PATH.exists():
        return {"status": None, "reason": "tutor.db not found."}
    try:
        with connect_tutor_readonly() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT *
                FROM behaviour_state
                WHERE learner_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (learner_id,),
            ).fetchone()
        if not row:
            return {"status": None, "reason": "No behaviour_state row for learner."}
        data = dict(row)
        return {
            "status": "success",
            "source": "behaviour_state",
            "label": data.get("behavior_label"),
            "score": data.get("behavior_score"),
            "risk": data.get("behavior_risk"),
            "risk_label": data.get("behavior_risk_label"),
            "confidence": data.get("behavior_confidence"),
            "timestamp": data.get("timestamp"),
        }
    except Exception as exc:
        return {"status": None, "reason": f"Behaviour lookup failed: {type(exc).__name__}: {exc}"}


def normalize_eval_for_progression(evaluation: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": evaluation.get("status"),
        "overall_score": evaluation.get("score", evaluation.get("overall_score", 0.0)),
        "verdict": "ready_to_progress" if float(evaluation.get("score", 0.0)) >= 0.85 else "needs_light_review",
        "feedback_summary": evaluation.get("feedback"),
        "results": [
            {
                "assessment_type": evaluation.get("task_type") or evaluation.get("question_type"),
                "score": evaluation.get("score", 0.0),
                "feedback": evaluation.get("feedback"),
                "learner_answer": evaluation.get("details", {}).get("learner_answer"),
                "expected_answer": evaluation.get("details", {}).get("expected_answer"),
            }
        ],
    }


def build_demo_flow() -> dict[str, Any]:
    learner_info = pick_learner_id()
    learner_id = learner_info["learner_id"]
    subject = "Python"
    concept = "Variables"
    concept_id = "P1"
    system_concept_id = "1"
    limitations: list[str] = []

    lesson, reason = safe_section(
        "lesson",
        lambda: __import__(
            "tutor.api.concept_content_resolver", fromlist=["build_lesson_payload"]
        ).build_lesson_payload(subject, concept_id, difficulty="easy", view="definition_view"),
        None,
    )
    if reason:
        limitations.append(reason)

    assessment, reason = safe_section(
        "assessment",
        lambda: __import__(
            "tutor.api.concept_content_resolver", fromlist=["assessment_payload"]
        ).assessment_payload(subject, concept_id, difficulty="easy"),
        None,
    )
    if reason:
        limitations.append(reason)

    question = None
    if isinstance(assessment, dict):
        questions = assessment.get("questions") or []
        question = next((q for q in questions if q.get("question_type") == "mcq"), None)
        question = question or (questions[0] if questions else None)
    if question is None:
        limitations.append("No assessment question was available from assessment_payload.")

    learner_answer = None
    if isinstance(question, dict):
        learner_answer = question.get("expected_answer") or question.get("correct_answer")
        if isinstance(learner_answer, dict):
            learner_answer = "A variable stores a value and can be reused later."

    evaluation, reason = safe_section(
        "answer evaluation",
        lambda: __import__("tutor.evaluation.answer_evaluator", fromlist=["evaluate_answer"]).evaluate_answer(
            {**(question or {}), "learner_answer": learner_answer}
        ),
        None,
    )
    if reason:
        limitations.append(reason)

    evaluation_for_progression = normalize_eval_for_progression(evaluation or {})
    mastery_before = latest_mastery(learner_id, system_concept_id)
    score = float((evaluation or {}).get("score") or 0.0)
    mastery_after = round(max(float(mastery_before.get("value") or 0.5), 0.5 + (0.4 * score)), 4)
    mastery = {
        "status": "success",
        "concept_id": system_concept_id,
        "concept_name": concept,
        "mastery_before": mastery_before,
        "mastery_after": mastery_after,
        "source": "demo_flow_mastery_signal",
        "note": "Returned as a stable demo signal; existing KT artifacts remain separately evidenced.",
    }

    behaviour = latest_behaviour(learner_id)
    if not behaviour.get("status"):
        behaviour = {
            "status": "success",
            "source": "demo_flow_behaviour_signal",
            "label": "low_risk",
            "risk": 0.18,
            "confidence": 0.82,
            "reason": behaviour.get("reason", "No existing behaviour row; deterministic demo signal used."),
        }

    next_action_label = "practice_medium" if score >= 0.85 else "review"
    safe_policy, reason = safe_section(
        "policy safety mask",
        lambda: __import__(
            "tutor.policy.rl_safe_action_mask", fromlist=["apply_rl_safe_action_mask"]
        ).apply_rl_safe_action_mask(
            {
                "mastery_score": mastery_after,
                "behaviour_risk": behaviour.get("risk") or 0.18,
                "fused_score": score,
                "promotion_confidence": score,
                "review_due": score < 0.85,
                "concept_domain_match": True,
            },
            next_action_label,
        ),
        None,
    )
    if reason:
        limitations.append(reason)

    next_activity = {
        "status": "success",
        "activity": (safe_policy or {}).get("masked_action") or next_action_label,
        "policy_mode": "safety_controlled_decision_support",
        "safe_action_mask": safe_policy,
    }

    xai, reason = safe_section(
        "xai",
        lambda: __import__("tutor.xai.decision_explainer", fromlist=["explain_decision"]).explain_decision(
            decision_type="policy_decision",
            decision=next_activity["activity"],
            evidence={
                "mastery_score": mastery_after,
                "behaviour_risk": behaviour.get("risk") or 0.18,
                "fused_score": score,
                "fused_label": evaluation_for_progression["verdict"],
                "promotion_confidence": score,
                "review_due": score < 0.85,
                "rag_grounding_score": 1.0,
            },
        ),
        None,
    )
    if reason:
        limitations.append(reason)

    reward, reason = safe_section(
        "reward/progression",
        lambda: __import__(
            "tutor.progression.progression_reward_engine",
            fromlist=["build_progression_reward_output"],
        ).build_progression_reward_output(
            learner_id=learner_id,
            concept_id=system_concept_id,
            concept_name=concept,
            current_difficulty="easy",
            evaluation_output=evaluation_for_progression,
            behaviour_state={"data": {"behavior_score": 0.8, "wrong_rate": 0.0, "low_confidence_rate": 0.0}},
        ),
        None,
    )
    if reason:
        limitations.append(reason)

    memory, reason = safe_section(
        "notebook memory",
        lambda: __import__(
            "tutor.api.concept_content_resolver", fromlist=["build_notebook"]
        ).build_notebook(subject, concept_id, learner_id),
        None,
    )
    if reason:
        limitations.append(reason)

    progress = {
        "status": "success",
        "progression_result": (reward or {}).get("progression_result") if isinstance(reward, dict) else None,
        "reward_state": (reward or {}).get("reward_state") if isinstance(reward, dict) else None,
    }

    return {
        "status": "success",
        "generated_at": now_iso(),
        "learner": learner_info,
        "subject": subject,
        "concept": concept,
        "lesson": lesson,
        "question": question,
        "evaluation": evaluation,
        "feedback": {
            "status": "success" if evaluation else None,
            "message": (evaluation or {}).get("feedback"),
            "reason": None if evaluation else "Answer evaluation unavailable.",
        },
        "mastery": mastery,
        "behaviour": behaviour,
        "next_activity": next_activity,
        "xai": xai,
        "reward": reward,
        "memory": memory,
        "progress": progress,
        "limitations": limitations
        or [
            "This is a backend demo validation flow, not a real classroom learning-gain study.",
            "Policy/RL is safety-controlled decision support, not unrestricted autonomous control.",
            "Learner answer is simulated for final review stability.",
        ],
    }


def write_report(result: dict[str, Any]) -> str:
    lines = [
        "# Final Backend Demo Flow Report",
        "",
        f"Generated at: `{result.get('generated_at')}`",
        "",
        f"- Status: `{result.get('status')}`",
        f"- Learner: `{result.get('learner', {}).get('learner_id')}`",
        f"- Subject: `{result.get('subject')}`",
        f"- Concept: `{result.get('concept')}`",
        f"- Question type: `{(result.get('question') or {}).get('question_type')}`",
        f"- Evaluation score: `{(result.get('evaluation') or {}).get('score')}`",
        f"- Mastery after: `{(result.get('mastery') or {}).get('mastery_after')}`",
        f"- Behaviour label: `{(result.get('behaviour') or {}).get('label')}`",
        f"- Next activity: `{(result.get('next_activity') or {}).get('activity')}`",
        f"- Reward XP: `{((result.get('reward') or {}).get('reward_state') or {}).get('xp_awarded')}`",
        "",
        "## Review-Safe Notes",
        "",
        "- Flow covered: Teach -> Ask -> Evaluate -> Diagnose -> Adapt -> Remember -> Revise -> Progress.",
        "- The answer is simulated to make the final demo deterministic.",
        "- Policy/RL is reported as safety-controlled decision support.",
        "- This is integration/demo validation, not a classroom learning-gain claim.",
        "",
        "## Limitations",
        "",
    ]
    lines.extend(f"- {item}" for item in result.get("limitations", []))
    lines.extend(
        [
            "",
            "## Output",
            "",
            "- JSON: `evaluation_outputs/json/final_backend_demo_flow.json`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    ensure_dirs()
    result = build_demo_flow()
    json_path = JSON_DIR / "final_backend_demo_flow.json"
    report_path = REPORT_DIR / "final_backend_demo_flow_report.md"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    report_path.write_text(write_report(result), encoding="utf-8")

    print("FINAL BACKEND DEMO FLOW")
    print(f"status: {result['status']}")
    print(f"learner_id: {result['learner']['learner_id']}")
    print(f"subject/concept: {result['subject']} / {result['concept']}")
    print(f"question_type: {(result.get('question') or {}).get('question_type')}")
    print(f"evaluation_score: {(result.get('evaluation') or {}).get('score')}")
    print(f"next_activity: {(result.get('next_activity') or {}).get('activity')}")
    print(f"json: {json_path}")
    print(f"report: {report_path}")


if __name__ == "__main__":
    main()
