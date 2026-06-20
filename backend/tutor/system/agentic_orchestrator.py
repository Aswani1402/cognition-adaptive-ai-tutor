from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DB_PATH = Path("external/core_data/tutor.db")
FLOW_GOAL = "Teach -> Ask -> Evaluate -> Diagnose -> Adapt -> Remember -> Revise -> Progress"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _summary(value: Any, limit: int = 180) -> str:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, default=str, sort_keys=True)
    else:
        text = str(value or "")
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _connect(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,),
    ).fetchone()
    return bool(row)


def _loads(value: Any, default: Any = None) -> Any:
    if value in (None, ""):
        return {} if default is None else default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except (TypeError, json.JSONDecodeError):
        return {} if default is None else default


def create_agentic_trace_log_table(db_path: Path | str = DB_PATH) -> dict[str, Any]:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = _connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS agentic_trace_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                learner_id TEXT,
                subject TEXT,
                concept_id TEXT,
                activity_type TEXT,
                goal TEXT,
                plan_json TEXT,
                trace_json TEXT,
                module_outputs_json TEXT,
                safety_checks_json TEXT,
                final_decision_json TEXT,
                created_at TEXT
            )
            """
        )
        existing = {row[1] for row in conn.execute("PRAGMA table_info(agentic_trace_log)").fetchall()}
        required = {
            "learner_id": "TEXT",
            "subject": "TEXT",
            "concept_id": "TEXT",
            "activity_type": "TEXT",
            "goal": "TEXT",
            "plan_json": "TEXT",
            "trace_json": "TEXT",
            "module_outputs_json": "TEXT",
            "safety_checks_json": "TEXT",
            "final_decision_json": "TEXT",
            "created_at": "TEXT",
        }
        added = []
        for column, column_type in required.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE agentic_trace_log ADD COLUMN {column} {column_type}")
                added.append(column)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_agentic_trace_log_learner_created ON agentic_trace_log(learner_id, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_agentic_trace_log_concept ON agentic_trace_log(concept_id)")
        conn.commit()
        return {"status": "success", "table": "agentic_trace_log", "columns_added": added, "db_path": str(db_path)}
    finally:
        conn.close()


def latest_agentic_trace(learner_id: str, db_path: Path | str = DB_PATH) -> dict[str, Any]:
    create_agentic_trace_log_table(db_path)
    conn = _connect(db_path)
    try:
        row = conn.execute(
            """
            SELECT * FROM agentic_trace_log
            WHERE learner_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (str(learner_id),),
        ).fetchone()
        if not row:
            return {
                "status": "warning",
                "message": "No persisted agentic trace found yet. Run adaptive session or answer submit first.",
                "learner_id": str(learner_id),
            }
        data = dict(row)
        return {
            "status": "success",
            "learner_id": data.get("learner_id"),
            "subject": data.get("subject"),
            "concept_id": data.get("concept_id"),
            "activity_type": data.get("activity_type"),
            "goal": data.get("goal"),
            "plan": _loads(data.get("plan_json"), []),
            "trace": _loads(data.get("trace_json"), []),
            "module_outputs": _loads(data.get("module_outputs_json"), {}),
            "safety_checks": _loads(data.get("safety_checks_json"), {}),
            "final_decision": _loads(data.get("final_decision_json"), {}),
            "created_at": data.get("created_at"),
            "orchestrator_type": "safe_tutor_orchestrator",
            "is_fully_autonomous": False,
            "safety_controlled": True,
        }
    finally:
        conn.close()


class SafeTutorOrchestrator:
    """Safe tutor planner/controller over existing backend modules.

    This class coordinates module outputs and applies deterministic safety
    gates. It is not an unrestricted autonomous agent and does not bypass
    dependency, mastery, difficulty progression, retention, or policy masks.
    """

    stage_specs = [
        ("LearnerContextAgent", "tutor.api.dependencies.latest_concept_from_logs"),
        ("ContentGroundingAgent", "tutor.api.concept_content_resolver.resolve_concept_content"),
        ("TeachingAgent", "tutor.api.concept_content_resolver.build_lesson_payload"),
        ("AssessmentAgent", "tutor.api.concept_content_resolver.assessment_payload"),
        ("EvaluatorAgent", "tutor.evaluation.answer_evaluator.AnswerEvaluator"),
        ("DiagnosisAgent", "tutor.evaluation.mistake_type_classifier"),
        ("LearnerStateAgent", "knowledge_state + behaviour_state updates"),
        ("DecisionPolicyAgent", "safe policy bridge + adaptive path safety rules"),
        ("MemoryRevisionAgent", "revision_schedule + learner memory"),
        ("RewardProgressionAgent", "reward_event_log + progression rules"),
        ("XAIReflectionAgent", "tutor.xai + evidence packet"),
        ("FrontendResponseAgent", "frontend response contract fields"),
    ]

    def __init__(self, db_path: Path | str = DB_PATH) -> None:
        self.db_path = Path(db_path)

    def run(
        self,
        request: dict[str, Any],
        module_outputs: dict[str, Any] | None = None,
        *,
        persist: bool = True,
    ) -> dict[str, Any]:
        request = _safe_dict(request)
        module_outputs = _safe_dict(module_outputs)
        learner_id = str(request.get("learner_id") or "")
        subject = str(request.get("subject") or request.get("domain") or "Python")
        concept_id = str(request.get("concept_id") or "")
        concept_name = str(request.get("concept_name") or concept_id or "Current concept")
        activity_type = str(request.get("activity_type") or "lesson")
        difficulty = self._normalize_difficulty(request.get("difficulty") or "easy")

        plan = [
            {"stage": stage, "module": module, "allowed_role": "controlled_orchestration"}
            for stage, module in self.stage_specs
        ]
        normalized_outputs = self._normalize_module_outputs(request, module_outputs)
        safety_checks = self._safety_checks(
            request=request,
            module_outputs=normalized_outputs,
            difficulty=difficulty,
        )
        final_decision = self._final_decision(
            request=request,
            module_outputs=normalized_outputs,
            safety_checks=safety_checks,
            difficulty=difficulty,
        )
        trace = self._build_trace(
            request=request,
            module_outputs=normalized_outputs,
            safety_checks=safety_checks,
            final_decision=final_decision,
        )
        status = "success" if all(step["status"] != "error" for step in trace) else "warning"
        if any(step["status"] == "warning" for step in trace):
            status = "warning" if status == "success" else status

        result = {
            "status": status,
            "orchestrator_type": "safe_tutor_orchestrator",
            "is_fully_autonomous": False,
            "safety_controlled": True,
            "goal": FLOW_GOAL,
            "learner_id": learner_id,
            "subject": subject,
            "concept_id": concept_id,
            "concept_name": concept_name,
            "activity_type": activity_type,
            "plan": plan,
            "trace": trace,
            "module_outputs": normalized_outputs,
            "safety_checks": safety_checks,
            "final_decision": final_decision,
            "agentic_trace": self.compact_trace(
                trace=trace,
                safety_checks=safety_checks,
                final_decision=final_decision,
                status=status,
            ),
            "limitations": [
                "Agentic AI is implemented as a safe tutor orchestration agent, not an unrestricted autonomous agent.",
                "Policy/RL recommendations must pass the safe action mask and do not override progression rules.",
                "Fallback/scoring outputs are reported honestly when trained model inference is not used by the calling route.",
            ],
        }
        if persist:
            result["persistence"] = self.persist_trace(result)
        return result

    def compact_trace(
        self,
        *,
        trace: list[dict[str, Any]],
        safety_checks: dict[str, Any],
        final_decision: dict[str, Any],
        status: str = "success",
    ) -> dict[str, Any]:
        return {
            "status": status,
            "orchestrator_type": "safe_tutor_orchestrator",
            "is_fully_autonomous": False,
            "safety_controlled": True,
            "stage_count": len(trace),
            "final_decision": final_decision,
            "safety_checks": safety_checks,
            "stages": [
                {
                    "stage": item.get("stage"),
                    "status": item.get("status"),
                    "fallback_used": item.get("fallback_used"),
                    "decision_contribution": item.get("decision_contribution"),
                }
                for item in trace
            ],
        }

    def persist_trace(self, result: dict[str, Any]) -> dict[str, Any]:
        create_agentic_trace_log_table(self.db_path)
        conn = _connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO agentic_trace_log (
                    learner_id, subject, concept_id, activity_type, goal,
                    plan_json, trace_json, module_outputs_json, safety_checks_json,
                    final_decision_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.get("learner_id"),
                    result.get("subject"),
                    result.get("concept_id"),
                    result.get("activity_type"),
                    result.get("goal"),
                    json.dumps(result.get("plan", []), default=str),
                    json.dumps(result.get("trace", []), default=str),
                    json.dumps(result.get("module_outputs", {}), default=str),
                    json.dumps(result.get("safety_checks", {}), default=str),
                    json.dumps(result.get("final_decision", {}), default=str),
                    _now_iso(),
                ),
            )
            conn.commit()
            return {"status": "success", "table": "agentic_trace_log"}
        except Exception as exc:
            return {"status": "warning", "reason": f"{type(exc).__name__}: {exc}", "table": "agentic_trace_log"}
        finally:
            conn.close()

    def _normalize_module_outputs(self, request: dict[str, Any], outputs: dict[str, Any]) -> dict[str, Any]:
        evaluation = _safe_dict(outputs.get("evaluation"))
        score = _safe_float(
            outputs.get("score")
            or evaluation.get("score")
            or evaluation.get("overall_score")
            or request.get("score"),
            0.0 if request.get("activity_type") == "answer_submit" else 0.5,
        )
        behaviour = _safe_dict(outputs.get("behaviour_update"))
        behaviour_payload = _safe_dict(request.get("behaviour_payload"))
        if not behaviour:
            confidence = _safe_float(behaviour_payload.get("confidence"), 0.6)
            wrong_rate = 0.0 if score >= 0.8 else 1.0 if request.get("activity_type") == "answer_submit" else 0.0
            slow_rate = 1.0 if _safe_float(behaviour_payload.get("time_taken_sec"), 0.0) > 60 else 0.0
            hint_rate = min(1.0, _safe_float(behaviour_payload.get("hint_count"), 0.0) / 3.0) if behaviour_payload.get("hint_used") else 0.0
            risk = min(1.0, (wrong_rate + slow_rate + hint_rate + (1.0 if confidence < 0.5 else 0.0)) / 4.0)
            behaviour = {
                "status": "success",
                "model_used": "scoring_formula",
                "fallback_used": False,
                "behaviour_risk": round(risk, 4),
                "behaviour_confidence": confidence,
                "behaviour_label": "low_risk" if risk < 0.4 else "needs_support",
            }

        kt = _safe_dict(outputs.get("kt_update"))
        if not kt:
            kt = {
                "status": "warning",
                "model_used": "fallback_cumulative",
                "fallback_used": True,
                "mastery_before": 0.0,
                "mastery_after": round(score, 4),
                "mastery_label": "mastered" if score >= 0.85 else "developing" if score >= 0.45 else "weak",
            }

        path = _safe_dict(outputs.get("path_update"))
        if not path:
            path = {
                "status": "success",
                "current_difficulty": self._normalize_difficulty(request.get("difficulty") or "easy"),
                "difficulty_passed": score >= 0.8,
                "concept_completed": score >= 0.8 and self._normalize_difficulty(request.get("difficulty") or "easy") == "hard",
                "recommended_next_activity": {"type": "assessment", "reason": "Continue controlled tutor flow."},
            }

        policy = _safe_dict(outputs.get("policy_update"))
        if not policy:
            policy = {
                "status": "warning",
                "model_used": "safe_policy_bridge",
                "fallback_used": True,
                "safe_action_applied": True,
                "recommended_action": _safe_dict(path.get("recommended_next_activity")).get("type") or path.get("recommended_action") or "teaching",
                "final_action": _safe_dict(path.get("recommended_next_activity")).get("type") or path.get("recommended_action") or "teaching",
                "reason": "Safe policy bridge fallback used by orchestrator.",
            }

        return {
            "teaching_strategy": _safe_dict(outputs.get("teaching_strategy")) or {
                "status": "success",
                "selected_view": "code_view",
                "model_used": "rule_or_current_context",
                "fallback_used": True,
                "reason": "Default guided teaching view selected when no live teaching strategy output was provided.",
            },
            "assessment": _safe_dict(outputs.get("assessment")),
            "evaluation": evaluation or {"status": "not_run" if request.get("activity_type") != "answer_submit" else "warning", "score": score},
            "kt_update": kt,
            "behaviour_update": behaviour,
            "path_update": path,
            "policy_update": policy,
            "rag_evidence": _safe_dict(outputs.get("rag_evidence") or outputs.get("rag_update")) or {
                "status": "warning",
                "source": "concept_resources_or_request_payload",
                "sections_used": ["request_context"],
                "grounding_score": None,
            },
            "revision_update": _safe_dict(outputs.get("revision_update")),
            "reward_update": _safe_dict(outputs.get("reward_update")),
            "xai": _safe_dict(outputs.get("xai")) or {
                "learner_reason": "The tutor chose the next safe activity from mastery, answer, behaviour, and progression evidence.",
                "top_factors": ["mastery", "difficulty", "behaviour_risk"],
                "reviewer_evidence": {},
            },
        }

    def _safety_checks(self, *, request: dict[str, Any], module_outputs: dict[str, Any], difficulty: str) -> dict[str, Any]:
        score = self._score(module_outputs)
        mastery = _safe_float(_safe_dict(module_outputs.get("kt_update")).get("mastery_after"), score)
        behaviour_risk = _safe_float(_safe_dict(module_outputs.get("behaviour_update")).get("behaviour_risk"), 0.0)
        path = _safe_dict(module_outputs.get("path_update"))
        activity_type = str(request.get("activity_type") or "")
        answer_submitted = activity_type == "answer_submit"
        correct_or_passed = score >= 0.8 or bool(path.get("difficulty_passed"))
        concept_completed = bool(path.get("concept_completed")) and difficulty == "hard" and correct_or_passed
        retention_due = bool(_safe_list(module_outputs.get("revision_update")) or _safe_dict(module_outputs.get("revision_update")))

        concept_dependency_ok = True
        if path.get("locked_reason") and path.get("next_concept_id"):
            concept_dependency_ok = False

        difficulty_progression_ok = True
        if difficulty in {"medium", "hard"} and not correct_or_passed and path.get("next_difficulty") not in {None, difficulty}:
            difficulty_progression_ok = False

        mastery_requirement_met = mastery >= 0.8 or correct_or_passed
        behaviour_risk_ok = behaviour_risk < 0.65
        wrong_or_partial = answer_submitted and score < 0.8
        safe_action_mask_applied = bool(_safe_dict(module_outputs.get("policy_update")).get("safe_action_applied", True))

        promotion_allowed = bool(
            concept_dependency_ok
            and difficulty_progression_ok
            and mastery_requirement_met
            and behaviour_risk_ok
            and safe_action_mask_applied
            and not wrong_or_partial
            and not retention_due
        )
        next_concept_allowed = bool(promotion_allowed and concept_completed)

        return {
            "concept_dependency_ok": concept_dependency_ok,
            "mastery_requirement_met": mastery_requirement_met,
            "difficulty_progression_ok": difficulty_progression_ok,
            "behaviour_risk_ok": behaviour_risk_ok,
            "safe_action_mask_applied": safe_action_mask_applied,
            "retention_due_blocks_new_concept": retention_due,
            "wrong_or_partial_blocks_promotion": wrong_or_partial,
            "promotion_allowed": promotion_allowed,
            "next_concept_allowed": next_concept_allowed,
            "score": round(score, 4),
            "mastery_score": round(mastery, 4),
            "behaviour_risk": round(behaviour_risk, 4),
        }

    def _final_decision(
        self,
        *,
        request: dict[str, Any],
        module_outputs: dict[str, Any],
        safety_checks: dict[str, Any],
        difficulty: str,
    ) -> dict[str, Any]:
        score = self._score(module_outputs)
        policy = _safe_dict(module_outputs.get("policy_update"))
        path = _safe_dict(module_outputs.get("path_update"))
        recommended = _safe_dict(path.get("recommended_next_activity"))
        policy_action = str(policy.get("final_action") or policy.get("recommended_action") or recommended.get("type") or "")

        if safety_checks.get("promotion_allowed") and difficulty == "hard" and path.get("concept_completed"):
            next_activity = "next_concept"
            reason = "Hard level and mastery checks passed, behaviour risk is acceptable, and safe action mask allowed promotion."
            component = "LearningPathPage"
        elif safety_checks.get("promotion_allowed") and score >= 0.8:
            next_activity = "next_difficulty"
            reason = f"{difficulty.title()} level passed; continue same concept at the next safe difficulty."
            component = "AssessmentRenderer"
        elif safety_checks.get("retention_due_blocks_new_concept"):
            next_activity = "revision"
            reason = "Revision is due, so the orchestrator schedules review before new concept promotion."
            component = "FlashcardDeck"
        elif not safety_checks.get("behaviour_risk_ok"):
            next_activity = "hint"
            reason = "Behaviour risk is high, so automatic promotion is blocked and support is recommended."
            component = "HintPanel"
        elif score >= 0.45:
            next_activity = "flashcard"
            reason = "Answer is partial, so recall/revision is safer than promotion."
            component = "FlashcardDeck"
        elif policy_action in {"mindmap_revision", "mindmap"}:
            next_activity = "mindmap"
            reason = "Evaluation indicates the learner needs an overview before retrying."
            component = "MindMapView"
        else:
            next_activity = "similar_question" if request.get("activity_type") == "answer_submit" else "assessment"
            reason = "Mastery or answer evidence is not strong enough for promotion; continue practice safely."
            component = "AssessmentRenderer"

        return {
            "next_activity": next_activity,
            "reason": reason,
            "frontend_component": component,
            "promotion_allowed": bool(safety_checks.get("promotion_allowed")),
            "policy_recommendation": policy_action or None,
            "safe_action_applied": bool(safety_checks.get("safe_action_mask_applied")),
        }

    def _build_trace(
        self,
        *,
        request: dict[str, Any],
        module_outputs: dict[str, Any],
        safety_checks: dict[str, Any],
        final_decision: dict[str, Any],
    ) -> list[dict[str, Any]]:
        stage_outputs = {
            "LearnerContextAgent": {
                "input": {"learner_id": request.get("learner_id"), "activity_type": request.get("activity_type")},
                "output": {"subject": request.get("subject") or request.get("domain"), "concept_id": request.get("concept_id"), "difficulty": request.get("difficulty")},
                "contribution": "Sets learner, subject, concept, difficulty, and activity context.",
                "fallback": False,
            },
            "ContentGroundingAgent": {
                "input": {"subject": request.get("subject") or request.get("domain"), "concept_id": request.get("concept_id")},
                "output": module_outputs.get("rag_evidence"),
                "contribution": "Checks grounding/source evidence for teaching and explanation content.",
                "fallback": _safe_dict(module_outputs.get("rag_evidence")).get("status") == "warning",
            },
            "TeachingAgent": {
                "input": {"concept_name": request.get("concept_name"), "difficulty": request.get("difficulty")},
                "output": module_outputs.get("teaching_strategy"),
                "contribution": "Selects or preserves safe teaching view.",
                "fallback": bool(_safe_dict(module_outputs.get("teaching_strategy")).get("fallback_used")),
            },
            "AssessmentAgent": {
                "input": {"activity_type": request.get("activity_type"), "difficulty": request.get("difficulty")},
                "output": module_outputs.get("assessment"),
                "contribution": "Provides assessment payload or records that assessment was not run in this request.",
                "fallback": not bool(module_outputs.get("assessment")),
            },
            "EvaluatorAgent": {
                "input": {"learner_answer_present": request.get("learner_answer") not in (None, "")},
                "output": module_outputs.get("evaluation"),
                "contribution": "Scores answer evidence where available.",
                "fallback": _safe_dict(module_outputs.get("evaluation")).get("status") in {"warning", "not_run"},
            },
            "DiagnosisAgent": {
                "input": {"score": self._score(module_outputs)},
                "output": {"mistake_type": _safe_dict(module_outputs.get("evaluation")).get("mistake_type")},
                "contribution": "Identifies whether reteaching, revision, or promotion is safe.",
                "fallback": False,
            },
            "LearnerStateAgent": {
                "input": {"kt": module_outputs.get("kt_update"), "behaviour": module_outputs.get("behaviour_update")},
                "output": {"mastery": safety_checks.get("mastery_score"), "behaviour_risk": safety_checks.get("behaviour_risk")},
                "contribution": "Updates/observes KT and behaviour state.",
                "fallback": bool(_safe_dict(module_outputs.get("kt_update")).get("fallback_used")),
            },
            "DecisionPolicyAgent": {
                "input": {"path_update": module_outputs.get("path_update"), "policy_update": module_outputs.get("policy_update")},
                "output": safety_checks,
                "contribution": "Applies concept dependency, progression, behaviour, retention, and safe action mask checks.",
                "fallback": bool(_safe_dict(module_outputs.get("policy_update")).get("fallback_used")),
            },
            "MemoryRevisionAgent": {
                "input": {"revision_update": module_outputs.get("revision_update")},
                "output": {"retention_due_blocks_new_concept": safety_checks.get("retention_due_blocks_new_concept")},
                "contribution": "Blocks new concept when revision/retention evidence requires review.",
                "fallback": False,
            },
            "RewardProgressionAgent": {
                "input": {"reward_update": module_outputs.get("reward_update")},
                "output": {"promotion_allowed": safety_checks.get("promotion_allowed"), "reward_update": module_outputs.get("reward_update")},
                "contribution": "Keeps rewards/progression tied to answer and mastery evidence.",
                "fallback": bool(_safe_dict(module_outputs.get("reward_update")).get("fallback_used")),
            },
            "XAIReflectionAgent": {
                "input": {"safety_checks": safety_checks, "final_decision": final_decision},
                "output": module_outputs.get("xai"),
                "contribution": "Explains the safe next action using evidence.",
                "fallback": False,
            },
            "FrontendResponseAgent": {
                "input": {"final_decision": final_decision},
                "output": {"agentic_trace_summary": final_decision},
                "contribution": "Returns only summarized agentic evidence for frontend/reviewer panels.",
                "fallback": False,
            },
        }
        trace = []
        for stage, module_called in self.stage_specs:
            item = stage_outputs[stage]
            status = "success"
            if item["fallback"]:
                status = "warning"
            trace.append(
                {
                    "stage": stage,
                    "input_summary": _summary(item["input"]),
                    "module_called": module_called,
                    "output_summary": _summary(item["output"]),
                    "status": status,
                    "fallback_used": bool(item["fallback"]),
                    "decision_contribution": item["contribution"],
                }
            )
        return trace

    def _score(self, module_outputs: dict[str, Any]) -> float:
        evaluation = _safe_dict(module_outputs.get("evaluation"))
        return _safe_float(evaluation.get("score") or evaluation.get("overall_score") or _safe_dict(module_outputs.get("kt_update")).get("mastery_after"), 0.0)

    def _normalize_difficulty(self, value: Any) -> str:
        text = str(value or "easy").strip().lower()
        if text in {"easy", "medium", "hard"}:
            return text
        return "easy"


def build_agentic_trace_summary(orchestrator_output: dict[str, Any]) -> dict[str, Any]:
    output = _safe_dict(orchestrator_output)
    trace = _safe_list(output.get("trace"))
    return SafeTutorOrchestrator().compact_trace(
        trace=trace,
        safety_checks=_safe_dict(output.get("safety_checks")),
        final_decision=_safe_dict(output.get("final_decision")),
        status=str(output.get("status") or "warning"),
    )


def write_agentic_orchestrator_upgrade_report(example_output: dict[str, Any] | None = None) -> dict[str, Any]:
    report_dir = Path("evaluation_outputs/reports")
    json_dir = Path("evaluation_outputs/json")
    report_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)
    example_output = example_output or SafeTutorOrchestrator().run(
        {
            "learner_id": "report_demo",
            "subject": "Python",
            "concept_id": "P1",
            "concept_name": "Variables",
            "difficulty": "easy",
            "activity_type": "lesson",
        },
        persist=False,
    )
    payload = {
        "status": "success",
        "existing_agentic_status_before_upgrade": "trace-only/report-oriented. AgenticOrchestrationTrace was observational and did not alter decisions.",
        "previous_implementation_full_autonomous": False,
        "new_orchestrator_file_paths": ["tutor/system/agentic_orchestrator.py", "scripts/migration/create_agentic_trace_log.py"],
        "stages_agents_implemented": [stage for stage, _ in SafeTutorOrchestrator.stage_specs],
        "inputs_accepted": [
            "learner_id",
            "subject",
            "concept_id",
            "concept_name",
            "difficulty",
            "activity_type",
            "learner_answer",
            "question",
            "behaviour_payload",
        ],
        "outputs_returned": [
            "status",
            "orchestrator_type",
            "is_fully_autonomous",
            "safety_controlled",
            "goal",
            "plan",
            "trace",
            "module_outputs",
            "safety_checks",
            "final_decision",
        ],
        "safety_checks": list(_safe_dict(example_output.get("safety_checks")).keys()),
        "api_routes_connected": [
            "GET /tutor/adaptive-session/{learner_id}",
            "POST /answer/submit",
            "GET /agentic/trace/{learner_id}",
            "GET /ai/evidence/{learner_id}",
        ],
        "db_table_persistence_status": create_agentic_trace_log_table(),
        "frontend_visibility": "Backend responses expose summarized agentic_trace for Reviewer Analytics, XAI / Why-this, and AI Evidence panels without redesigning frontend UI.",
        "example_trace": example_output,
        "limitations": [
            "Agentic AI is implemented as a safe tutor orchestration agent. It coordinates tutoring modules and stores a trace. It is not an unrestricted autonomous agent.",
            "The orchestrator uses provided module outputs and safe deterministic wrappers; it does not fake live DKT/LSTM/RL usage.",
            "Sanvia remains comparison-only and is not connected live.",
        ],
        "future_upgrade_plan": [
            "Replace placeholder route evidence with latest persisted module outputs where available.",
            "Run learned policy and RL only in shadow until validated against safe action masks.",
            "Add richer concept dependency evidence per subject database to the trace.",
        ],
    }
    json_path = json_dir / "agentic_orchestrator_upgrade_report.json"
    md_path = report_dir / "agentic_orchestrator_upgrade_report.md"
    json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    lines = [
        "# Agentic Orchestrator Upgrade Report",
        "",
        "Agentic AI is implemented as a safe tutor orchestration agent. It coordinates tutoring modules and stores a trace. It is not an unrestricted autonomous agent.",
        "",
        f"- Existing agentic status before upgrade: {payload['existing_agentic_status_before_upgrade']}",
        f"- Previous implementation full autonomous: {payload['previous_implementation_full_autonomous']}",
        f"- New orchestrator files: {', '.join(payload['new_orchestrator_file_paths'])}",
        f"- DB table/persistence status: {payload['db_table_persistence_status'].get('status')}",
        f"- Frontend visibility: {payload['frontend_visibility']}",
        "",
        "## Stages",
    ]
    lines.extend(f"- {stage}" for stage in payload["stages_agents_implemented"])
    lines.extend(["", "## Safety Checks"])
    lines.extend(f"- {check}" for check in payload["safety_checks"])
    lines.extend(["", "## API Routes Connected"])
    lines.extend(f"- {route}" for route in payload["api_routes_connected"])
    lines.extend(["", "## Limitations"])
    lines.extend(f"- {item}" for item in payload["limitations"])
    lines.extend(["", "## Future Upgrade Plan"])
    lines.extend(f"- {item}" for item in payload["future_upgrade_plan"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": "success", "json_report": str(json_path), "md_report": str(md_path), "report": payload}
