import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT_DIR = Path(__file__).resolve().parents[1]

PROGRESS_DIR = ROOT_DIR / "outputs" / "learning_progress"
VIEW_PROGRESS_PATH = PROGRESS_DIR / "teaching_view_progress.json"


# Full learning coverage sequence.
# Keep this complete list for report/final system.
CORE_VIEW_SEQUENCE = [
    "definition_view",
    "simple_example_view",
    "step_by_step_view",
    "code_view",
    "output_prediction_view",
    "debug_view",
    "misconception_view",
    "transfer_view",
    "challenge_view",
    "revision_summary_view",
    "flashcard_view",
    "mindmap_view",
]


# If learner clearly understands, move faster to the next deeper view.
# This is NOT the full sequence. It is only the fast path.
FAST_FORWARD_MAP = {
    "definition_view": "code_view",
    "simple_example_view": "code_view",
    "step_by_step_view": "code_view",
    "code_view": "output_prediction_view",
    "output_prediction_view": "debug_view",
    "debug_view": "misconception_view",
    "misconception_view": "transfer_view",
    "transfer_view": "challenge_view",
    "challenge_view": "revision_summary_view",
    "revision_summary_view": "flashcard_view",
    "flashcard_view": "mindmap_view",
    "mindmap_view": "challenge_view",
}


VIEW_GROUPS = {
    "foundation": [
        "definition_view",
        "simple_example_view",
        "step_by_step_view",
    ],
    "code_practice": [
        "code_view",
        "output_prediction_view",
        "debug_view",
        "misconception_view",
    ],
    "application": [
        "transfer_view",
        "challenge_view",
    ],
    "revision": [
        "revision_summary_view",
        "flashcard_view",
        "mindmap_view",
    ],
}


VIEW_TO_ASSESSMENT_TYPES = {
    "definition_view": ["mcq", "explanation_check"],
    "simple_example_view": ["mcq", "output_prediction"],
    "step_by_step_view": ["explanation_check", "mcq"],
    "analogy_view": ["mcq", "explanation_check"],
    "code_view": ["output_prediction", "debug_task"],
    "output_prediction_view": ["output_prediction", "mcq"],
    "debug_view": ["debug_task", "output_prediction"],
    "misconception_view": ["mcq", "explanation_check"],
    "transfer_view": ["transfer_question", "mcq"],
    "challenge_view": ["challenge_question", "transfer_question"],
    "revision_summary_view": ["mcq", "output_prediction"],
    "flashcard_view": ["mcq"],
    "mindmap_view": ["explanation_check", "mcq"],
}


FALLBACK_VIEW_BY_WEAKNESS = {
    "mcq": "definition_view",
    "explanation_check": "step_by_step_view",
    "output_prediction": "output_prediction_view",
    "debug_task": "debug_view",
    "transfer_question": "transfer_view",
    "challenge_question": "challenge_view",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def progress_key(learner_id: str, concept_id: str, domain: str) -> str:
    return f"{learner_id}::{domain}::{concept_id}"


def empty_progress(
    learner_id: str,
    concept_id: str,
    concept_name: str,
    domain: str,
) -> Dict[str, Any]:
    return {
        "learner_id": learner_id,
        "concept_id": concept_id,
        "concept_name": concept_name,
        "domain": domain,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "current_view": None,
        "covered_views": [],
        "successful_views": [],
        "weak_views": [],
        "skipped_views": [],
        "view_scores": {},
        "view_attempts": {},
        "last_assessment_type": None,
        "last_score": None,
        "last_mastery_signal": None,
        "next_recommended_view": "definition_view",
        "coverage_status": "not_started",
    }


class TeachingViewProgressionService:
    """
    Tracks and selects teaching views for one learner/concept.

    Main idea:
    - Do not show all content at once.
    - Show one selected teaching view.
    - Assess learner understanding.
    - If understood, move deeper/faster.
    - If weak, change to support view instead of repeating the same content.
    - Eventually cover foundation, code practice, application, and revision.
    """

    def __init__(self, progress_path: Optional[Path] = None):
        self.progress_path = progress_path or VIEW_PROGRESS_PATH

    def _load_store(self) -> Dict[str, Any]:
        if not self.progress_path.exists():
            return {}

        with self.progress_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _save_store(self, store: Dict[str, Any]) -> None:
        self.progress_path.parent.mkdir(parents=True, exist_ok=True)

        with self.progress_path.open("w", encoding="utf-8") as f:
            json.dump(store, f, indent=2, ensure_ascii=False)

    def get_progress(
        self,
        learner_id: str,
        concept_id: str,
        concept_name: str,
        domain: str,
    ) -> Dict[str, Any]:
        store = self._load_store()
        key = progress_key(learner_id, concept_id, domain)

        if key not in store:
            store[key] = empty_progress(
                learner_id=learner_id,
                concept_id=concept_id,
                concept_name=concept_name,
                domain=domain,
            )
            self._save_store(store)

        return store[key]

    def reset_progress(
        self,
        learner_id: str,
        concept_id: str,
        domain: str,
    ) -> None:
        """
        Useful for clean self-tests or starting a concept again.
        """
        store = self._load_store()
        key = progress_key(learner_id, concept_id, domain)

        if key in store:
            del store[key]
            self._save_store(store)

    def choose_start_view(
        self,
        learner_profile: str = "average",
        returning_mode: Optional[str] = None,
        weak_question_types: Optional[List[str]] = None,
    ) -> str:
        weak_question_types = weak_question_types or []

        if returning_mode in {"revision_first", "recovery", "returning_learner"}:
            return "revision_summary_view"

        if "debug_task" in weak_question_types:
            return "debug_view"

        if "output_prediction" in weak_question_types:
            return "output_prediction_view"

        if learner_profile == "weak":
            return "definition_view"

        if learner_profile == "code_confused":
            return "code_view"

        if learner_profile == "strong":
            return "challenge_view"

        return "definition_view"

    def recommend_next_view(
        self,
        progress: Dict[str, Any],
        last_score: Optional[float] = None,
        last_question_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        covered = progress.get("covered_views", [])
        successful = progress.get("successful_views", [])
        weak_views = progress.get("weak_views", [])
        current_view = progress.get("current_view")

        # First view if nothing started.
        if not current_view and not covered:
            next_view = progress.get("next_recommended_view") or "definition_view"
            return {
                "next_view": next_view,
                "reason": "start_concept",
                "assessment_types": VIEW_TO_ASSESSMENT_TYPES.get(next_view, ["mcq"]),
            }

        # If learner failed badly, change view instead of repeating the same view.
        if last_score is not None and last_score < 0.4:
            fallback = FALLBACK_VIEW_BY_WEAKNESS.get(last_question_type)

            if fallback and fallback != current_view:
                return {
                    "next_view": fallback,
                    "reason": f"low_score_switch_to_support_view_for_{last_question_type}",
                    "assessment_types": VIEW_TO_ASSESSMENT_TYPES.get(fallback, ["mcq"]),
                }

            support_view = self._choose_support_view(current_view, weak_views)

            return {
                "next_view": support_view,
                "reason": "low_score_change_view_not_repeat",
                "assessment_types": VIEW_TO_ASSESSMENT_TYPES.get(support_view, ["mcq"]),
            }

        # If partial, use nearby support view.
        if last_score is not None and 0.4 <= last_score < 0.8:
            support_view = self._choose_support_view(current_view, weak_views)

            return {
                "next_view": support_view,
                "reason": "partial_score_support_view",
                "assessment_types": VIEW_TO_ASSESSMENT_TYPES.get(support_view, ["mcq"]),
            }

        # If strong, fast-forward to the next deeper view.
        # Example: definition_view clear -> code_view.
        if last_score is not None and last_score >= 0.8:
            candidate = FAST_FORWARD_MAP.get(current_view)

            if candidate and candidate not in successful:
                return {
                    "next_view": candidate,
                    "reason": f"{current_view}_clear_move_to_{candidate}",
                    "assessment_types": VIEW_TO_ASSESSMENT_TYPES.get(candidate, ["mcq"]),
                }

        # Otherwise continue any uncovered important view from full sequence.
        for view in CORE_VIEW_SEQUENCE:
            if view not in successful:
                return {
                    "next_view": view,
                    "reason": "continue_uncovered_sequence",
                    "assessment_types": VIEW_TO_ASSESSMENT_TYPES.get(view, ["mcq"]),
                }

        return {
            "next_view": "challenge_view",
            "reason": "all_core_views_covered_ready_for_mastery_challenge",
            "assessment_types": VIEW_TO_ASSESSMENT_TYPES.get("challenge_view", ["challenge_question"]),
        }

    def _choose_support_view(
        self,
        current_view: Optional[str],
        weak_views: List[str],
    ) -> str:
        support_map = {
            "definition_view": "simple_example_view",
            "simple_example_view": "step_by_step_view",
            "step_by_step_view": "analogy_view",
            "analogy_view": "simple_example_view",
            "code_view": "output_prediction_view",
            "output_prediction_view": "step_by_step_view",
            "debug_view": "misconception_view",
            "misconception_view": "simple_example_view",
            "transfer_view": "code_view",
            "challenge_view": "transfer_view",
            "revision_summary_view": "flashcard_view",
            "flashcard_view": "definition_view",
            "mindmap_view": "revision_summary_view",
        }

        candidate = support_map.get(current_view or "", "step_by_step_view")

        if candidate in weak_views:
            return "simple_example_view"

        return candidate

    def update_after_view_result(
        self,
        learner_id: str,
        concept_id: str,
        concept_name: str,
        domain: str,
        view: str,
        score: float,
        question_type: str,
    ) -> Dict[str, Any]:
        store = self._load_store()
        key = progress_key(learner_id, concept_id, domain)

        progress = store.get(
            key,
            empty_progress(
                learner_id=learner_id,
                concept_id=concept_id,
                concept_name=concept_name,
                domain=domain,
            ),
        )

        progress["updated_at"] = now_iso()
        progress["current_view"] = view
        progress["last_assessment_type"] = question_type
        progress["last_score"] = score

        if view not in progress["covered_views"]:
            progress["covered_views"].append(view)

        progress["view_attempts"][view] = int(progress["view_attempts"].get(view, 0)) + 1

        old_scores = progress["view_scores"].get(view, [])
        old_scores.append(score)
        progress["view_scores"][view] = old_scores[-5:]

        if score >= 0.8:
            progress["last_mastery_signal"] = "positive"

            if view not in progress["successful_views"]:
                progress["successful_views"].append(view)

            if view in progress["weak_views"]:
                progress["weak_views"].remove(view)

        elif score >= 0.4:
            progress["last_mastery_signal"] = "partial"

            if view not in progress["weak_views"]:
                progress["weak_views"].append(view)

        else:
            progress["last_mastery_signal"] = "weak"

            if view not in progress["weak_views"]:
                progress["weak_views"].append(view)

        recommendation = self.recommend_next_view(
            progress=progress,
            last_score=score,
            last_question_type=question_type,
        )

        progress["next_recommended_view"] = recommendation["next_view"]
        progress["coverage_status"] = self.calculate_coverage_status(progress)

        store[key] = progress
        self._save_store(store)

        return {
            "status": "success",
            "progress": progress,
            "recommendation": recommendation,
        }

    def calculate_coverage_status(self, progress: Dict[str, Any]) -> str:
        successful = set(progress.get("successful_views", []))

        foundation_done = any(view in successful for view in VIEW_GROUPS["foundation"])
        code_done = all(view in successful for view in VIEW_GROUPS["code_practice"])
        application_done = all(view in successful for view in VIEW_GROUPS["application"])
        revision_started = any(view in successful for view in VIEW_GROUPS["revision"])

        if foundation_done and code_done and application_done:
            return "concept_ready_for_mastery_or_next_concept"

        if foundation_done and code_done:
            return "application_remaining"

        if foundation_done:
            return "code_practice_remaining"

        if revision_started:
            return "revision_in_progress"

        if progress.get("covered_views"):
            return "foundation_in_progress"

        return "not_started"

    def build_concept_learning_plan(
        self,
        learner_id: str,
        concept_id: str,
        concept_name: str,
        domain: str,
        learner_profile: str = "average",
        returning_mode: Optional[str] = None,
        weak_question_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        progress = self.get_progress(
            learner_id=learner_id,
            concept_id=concept_id,
            concept_name=concept_name,
            domain=domain,
        )

        if not progress.get("current_view"):
            start_view = self.choose_start_view(
                learner_profile=learner_profile,
                returning_mode=returning_mode,
                weak_question_types=weak_question_types,
            )
            progress["next_recommended_view"] = start_view

        next_view = progress.get("next_recommended_view") or "definition_view"

        return {
            "status": "success",
            "learner_id": learner_id,
            "concept_id": concept_id,
            "concept_name": concept_name,
            "domain": domain,
            "coverage_status": progress.get("coverage_status"),
            "current_view": progress.get("current_view"),
            "covered_views": progress.get("covered_views", []),
            "successful_views": progress.get("successful_views", []),
            "weak_views": progress.get("weak_views", []),
            "next_recommended_view": next_view,
            "next_assessment_types": VIEW_TO_ASSESSMENT_TYPES.get(next_view, ["mcq"]),
            "full_learning_sequence": CORE_VIEW_SEQUENCE,
            "fast_forward_map": FAST_FORWARD_MAP,
            "view_groups": VIEW_GROUPS,
            "rule": (
                "Do not show all views at once. Show one selected view, assess, "
                "then continue, fast-forward, or change support view based on learner result."
            ),
        }


def run_self_test() -> None:
    print("\nTeachingViewProgressionService self-test")
    print("=" * 80)

    service = TeachingViewProgressionService()

    learner_id = "demo_progress_learner_001"
    concept_id = "P1"
    concept_name = "Variables"
    domain = "Python"

    # Clean demo progress so output is predictable.
    service.reset_progress(
        learner_id=learner_id,
        concept_id=concept_id,
        domain=domain,
    )

    print("\nInitial plan")
    print("-" * 80)
    plan = service.build_concept_learning_plan(
        learner_id=learner_id,
        concept_id=concept_id,
        concept_name=concept_name,
        domain=domain,
        learner_profile="weak",
    )
    print(json.dumps(plan, indent=2, ensure_ascii=False))

    simulated_results = [
        {
            "case": "definition clear should fast-forward to code",
            "view": "definition_view",
            "score": 1.0,
            "question_type": "mcq",
        },
        {
            "case": "code weak should move to debug support",
            "view": "code_view",
            "score": 0.2,
            "question_type": "debug_task",
        },
        {
            "case": "debug clear should move to misconception",
            "view": "debug_view",
            "score": 1.0,
            "question_type": "debug_task",
        },
        {
            "case": "misconception clear should move to transfer",
            "view": "misconception_view",
            "score": 1.0,
            "question_type": "mcq",
        },
        {
            "case": "transfer clear should move to challenge",
            "view": "transfer_view",
            "score": 1.0,
            "question_type": "transfer_question",
        },
    ]

    for item in simulated_results:
        print(f"\nUpdate: {item['case']}")
        print("-" * 80)

        result = service.update_after_view_result(
            learner_id=learner_id,
            concept_id=concept_id,
            concept_name=concept_name,
            domain=domain,
            view=item["view"],
            score=item["score"],
            question_type=item["question_type"],
        )

        print(json.dumps(result, indent=2, ensure_ascii=False)[:2600])

    print("\nFinal plan")
    print("-" * 80)
    final_plan = service.build_concept_learning_plan(
        learner_id=learner_id,
        concept_id=concept_id,
        concept_name=concept_name,
        domain=domain,
    )
    print(json.dumps(final_plan, indent=2, ensure_ascii=False))

    print("\nSelf-test complete.")


if __name__ == "__main__":
    run_self_test()