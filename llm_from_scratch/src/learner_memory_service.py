import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT_DIR = Path(__file__).resolve().parents[1]

MEMORY_DIR = ROOT_DIR / "outputs" / "learner_memory"
MEMORY_PATH = MEMORY_DIR / "learner_memory.json"


TIME_GAP_RULES = {
    "minutes": {
        "max_hours": 1,
        "mode": "continue",
        "recommended_views": ["code_view", "output_prediction_view"],
        "summary_style": "short_continue",
        "num_questions": 1,
    },
    "hours": {
        "max_hours": 24,
        "mode": "warmup",
        "recommended_views": ["revision_summary_view", "output_prediction_view"],
        "summary_style": "recap_warmup",
        "num_questions": 2,
    },
    "days": {
        "max_hours": 72,
        "mode": "revision_first",
        "recommended_views": ["revision_summary_view", "flashcard_view", "misconception_view"],
        "summary_style": "revision_summary",
        "num_questions": 3,
    },
    "long_gap": {
        "max_hours": None,
        "mode": "recovery",
        "recommended_views": ["revision_summary_view", "flashcard_view", "misconception_view", "debug_view"],
        "summary_style": "recovery_path",
        "num_questions": 5,
    },
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None

    try:
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        return datetime.fromisoformat(value)
    except Exception:
        return None


def safe_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def load_memory_store() -> Dict[str, Any]:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    if not MEMORY_PATH.exists():
        return {}

    with MEMORY_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_memory_store(store: Dict[str, Any]) -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    with MEMORY_PATH.open("w", encoding="utf-8") as f:
        json.dump(store, f, indent=2, ensure_ascii=False)


def empty_learner_memory(learner_id: str) -> Dict[str, Any]:
    return {
        "learner_id": learner_id,
        "created_at": now_iso(),
        "last_active_at": None,
        "last_concept_id": None,
        "last_concept_name": None,
        "last_domain": None,
        "last_teaching_view": None,
        "last_difficulty": "easy",
        "recent_scores": [],
        "weak_concepts": [],
        "weak_question_types": [],
        "strong_question_types": [],
        "mistake_summary": [],
        "recommended_revision_views": [],
        "next_recommended_action": "start_learning",
        "session_count": 0,
    }


class LearnerMemoryService:
    """
    NotebookLM-style memory layer for returning learners.

    This does not train a new LLM.
    It stores learner history and creates comeback/revision recommendations.
    """

    def __init__(self, memory_path: Optional[Path] = None):
        self.memory_path = memory_path or MEMORY_PATH

    def _load_store(self) -> Dict[str, Any]:
        global MEMORY_PATH
        old_path = MEMORY_PATH
        MEMORY_PATH = self.memory_path
        store = load_memory_store()
        MEMORY_PATH = old_path
        return store

    def _save_store(self, store: Dict[str, Any]) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        with self.memory_path.open("w", encoding="utf-8") as f:
            json.dump(store, f, indent=2, ensure_ascii=False)

    def get_memory(self, learner_id: str) -> Dict[str, Any]:
        store = self._load_store()

        if learner_id not in store:
            store[learner_id] = empty_learner_memory(learner_id)
            self._save_store(store)

        return store[learner_id]

    def update_memory_from_evaluation(
        self,
        learner_id: str,
        evaluation_result: Dict[str, Any],
        teaching_view: Optional[str] = None,
        difficulty: str = "easy",
    ) -> Dict[str, Any]:
        """
        Update memory after learner answers a question.

        evaluation_result is the output from answer_evaluator.evaluate_answer().
        """

        store = self._load_store()
        memory = store.get(learner_id, empty_learner_memory(learner_id))

        concept_id = evaluation_result.get("concept_id")
        concept_name = evaluation_result.get("concept_name")
        domain = evaluation_result.get("domain")
        question_type = evaluation_result.get("question_type")
        score = float(evaluation_result.get("score", 0.0))
        correct = bool(evaluation_result.get("correct", False))
        mistake_type = evaluation_result.get("mistake_type")

        memory["last_active_at"] = now_iso()
        memory["last_concept_id"] = concept_id
        memory["last_concept_name"] = concept_name
        memory["last_domain"] = domain
        memory["last_teaching_view"] = teaching_view or memory.get("last_teaching_view") or "definition_view"
        memory["last_difficulty"] = difficulty
        memory["session_count"] = int(memory.get("session_count", 0)) + 1

        recent_item = {
            "timestamp": now_iso(),
            "concept_id": concept_id,
            "concept_name": concept_name,
            "domain": domain,
            "question_type": question_type,
            "score": score,
            "correct": correct,
            "mistake_type": mistake_type,
        }

        recent_scores = memory.get("recent_scores", [])
        recent_scores.append(recent_item)
        memory["recent_scores"] = recent_scores[-30:]

        memory = self._recompute_strengths_and_weaknesses(memory)

        store[learner_id] = memory
        self._save_store(store)

        return memory

    def _recompute_strengths_and_weaknesses(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        recent_scores = memory.get("recent_scores", [])

        concept_scores = defaultdict(list)
        type_scores = defaultdict(list)
        mistake_counter = Counter()

        for item in recent_scores:
            concept_name = item.get("concept_name")
            question_type = item.get("question_type")
            score = float(item.get("score", 0.0))
            mistake_type = item.get("mistake_type")

            if concept_name:
                concept_scores[concept_name].append(score)

            if question_type:
                type_scores[question_type].append(score)

            if mistake_type:
                mistake_counter[mistake_type] += 1

        weak_concepts = []
        for concept, scores in concept_scores.items():
            avg = sum(scores) / len(scores)
            if avg < 0.6:
                weak_concepts.append(concept)

        weak_question_types = []
        strong_question_types = []

        for qtype, scores in type_scores.items():
            avg = sum(scores) / len(scores)

            if avg < 0.6:
                weak_question_types.append(qtype)

            if avg >= 0.8:
                strong_question_types.append(qtype)

        mistake_summary = []
        for mistake_type, count in mistake_counter.most_common(5):
            mistake_summary.append(f"{mistake_type} occurred {count} time(s)")

        memory["weak_concepts"] = weak_concepts
        memory["weak_question_types"] = weak_question_types
        memory["strong_question_types"] = strong_question_types
        memory["mistake_summary"] = mistake_summary
        memory["recommended_revision_views"] = self._recommend_views(
            weak_question_types=weak_question_types,
            mistake_summary=mistake_summary,
        )
        memory["next_recommended_action"] = self._recommend_next_action(
            weak_question_types=weak_question_types,
            weak_concepts=weak_concepts,
        )

        return memory

    def _recommend_views(
        self,
        weak_question_types: List[str],
        mistake_summary: List[str],
    ) -> List[str]:
        views = []

        if "debug_task" in weak_question_types:
            views.extend(["misconception_view", "debug_view"])

        if "output_prediction" in weak_question_types:
            views.extend(["code_view", "output_prediction_view"])

        if "mcq" in weak_question_types or "explanation_check" in weak_question_types:
            views.extend(["definition_view", "step_by_step_view"])

        if "transfer_question" in weak_question_types or "challenge_question" in weak_question_types:
            views.extend(["transfer_view", "challenge_view"])

        if mistake_summary:
            views.append("revision_summary_view")

        if not views:
            views = ["revision_summary_view", "flashcard_view"]

        # unique preserve order
        unique = []
        for view in views:
            if view not in unique:
                unique.append(view)

        return unique[:5]

    def _recommend_next_action(
        self,
        weak_question_types: List[str],
        weak_concepts: List[str],
    ) -> str:
        if "debug_task" in weak_question_types:
            return "quick_revision_then_debug_practice"

        if "output_prediction" in weak_question_types:
            return "quick_revision_then_output_prediction"

        if weak_concepts:
            return "revision_before_next_concept"

        return "continue_next_concept"

    def calculate_time_gap(self, learner_id: str) -> Dict[str, Any]:
        memory = self.get_memory(learner_id)
        last_active_at = parse_dt(memory.get("last_active_at"))

        if last_active_at is None:
            return {
                "category": "new",
                "hours_since_last_active": None,
                "mode": "new_learner",
                "rule": None,
            }

        current = datetime.now(timezone.utc)
        if last_active_at.tzinfo is None:
            last_active_at = last_active_at.replace(tzinfo=timezone.utc)

        hours = (current - last_active_at).total_seconds() / 3600

        if hours <= TIME_GAP_RULES["minutes"]["max_hours"]:
            category = "minutes"
        elif hours <= TIME_GAP_RULES["hours"]["max_hours"]:
            category = "hours"
        elif hours <= TIME_GAP_RULES["days"]["max_hours"]:
            category = "days"
        else:
            category = "long_gap"

        return {
            "category": category,
            "hours_since_last_active": round(hours, 2),
            "mode": TIME_GAP_RULES[category]["mode"],
            "rule": TIME_GAP_RULES[category],
        }

    def build_comeback_summary(
        self,
        learner_id: str,
        force_category: Optional[str] = None,
    ) -> Dict[str, Any]:
        memory = self.get_memory(learner_id)
        gap = self.calculate_time_gap(learner_id)

        if force_category:
            rule = TIME_GAP_RULES.get(force_category)
            if rule:
                gap = {
                    "category": force_category,
                    "hours_since_last_active": gap.get("hours_since_last_active"),
                    "mode": rule["mode"],
                    "rule": rule,
                }

        if gap["category"] == "new":
            summary = (
                "Welcome. Let’s start your first learning session. "
                "We will teach one concept view at a time and check your understanding."
            )

            return {
                "learner_id": learner_id,
                "mode": "new_learner",
                "time_gap_category": "new",
                "comeback_summary": summary,
                "recommended_views": ["definition_view", "simple_example_view"],
                "recommended_question_types": ["mcq", "output_prediction"],
                "num_questions": 2,
                "last_concept": None,
                "next_action": "start_learning",
            }

        concept_name = memory.get("last_concept_name") or "the last concept"
        domain = memory.get("last_domain") or "the subject"
        weak_types = memory.get("weak_question_types", [])
        strong_types = memory.get("strong_question_types", [])
        mistakes = memory.get("mistake_summary", [])

        rule = gap["rule"]
        category = gap["category"]

        weak_text = ", ".join(weak_types) if weak_types else "no major weak question type yet"
        strong_text = ", ".join(strong_types) if strong_types else "still being measured"
        mistake_text = "; ".join(mistakes[:2]) if mistakes else "no repeated mistake pattern yet"

        if category == "minutes":
            summary = (
                f"Welcome back. You were studying {concept_name} in {domain}. "
                f"Let’s continue from your previous activity."
            )

        elif category == "hours":
            summary = (
                f"Welcome back. Last time you studied {concept_name}. "
                f"You were stronger in: {strong_text}. "
                f"You may need practice in: {weak_text}. "
                "Let’s do a quick recap and one warm-up question."
            )

        elif category == "days":
            summary = (
                f"Welcome back. Since some time has passed, revise {concept_name} before moving on. "
                f"Strong area: {strong_text}. "
                f"Needs practice: {weak_text}. "
                f"Mistake pattern: {mistake_text}. "
                "Start with a revision summary, then try a short practice question."
            )

        else:
            summary = (
                f"Welcome back. It has been a longer gap, so we will rebuild {concept_name} slowly. "
                f"First revise the summary, review a flashcard, then fix one misconception. "
                f"After that, try easy practice before continuing."
            )

        recommended_views = memory.get("recommended_revision_views") or rule["recommended_views"]

        return {
            "learner_id": learner_id,
            "mode": "returning_learner",
            "time_gap_category": category,
            "hours_since_last_active": gap.get("hours_since_last_active"),
            "last_concept": {
                "concept_id": memory.get("last_concept_id"),
                "concept_name": memory.get("last_concept_name"),
                "domain": memory.get("last_domain"),
            },
            "comeback_summary": summary,
            "recommended_views": recommended_views,
            "recommended_question_types": self._recommend_question_types(memory),
            "num_questions": rule["num_questions"],
            "weak_concepts": memory.get("weak_concepts", []),
            "weak_question_types": weak_types,
            "strong_question_types": strong_types,
            "mistake_summary": mistakes,
            "next_action": memory.get("next_recommended_action") or "continue_learning",
        }

    def _recommend_question_types(self, memory: Dict[str, Any]) -> List[str]:
        weak_types = memory.get("weak_question_types", [])

        if weak_types:
            recommended = weak_types + ["mcq"]
        else:
            recommended = ["mcq", "output_prediction"]

        unique = []
        for qtype in recommended:
            if qtype not in unique:
                unique.append(qtype)

        return unique[:3]

    def recommend_revision_packet(self, learner_id: str) -> Dict[str, Any]:
        """
        Returns a learner-memory-only recommendation packet.
        TutorLMService can use this packet to fetch actual teaching/question content.
        """

        summary = self.build_comeback_summary(learner_id)

        if summary["mode"] == "new_learner":
            return summary

        last_concept = summary.get("last_concept") or {}

        return {
            "status": "success",
            "mode": summary["mode"],
            "learner_id": learner_id,
            "time_gap_category": summary["time_gap_category"],
            "last_concept": last_concept,
            "comeback_summary": summary["comeback_summary"],
            "recommended_views": summary["recommended_views"],
            "recommended_question_types": summary["recommended_question_types"],
            "num_questions": summary["num_questions"],
            "next_action": summary["next_action"],
            "weak_concepts": summary["weak_concepts"],
            "weak_question_types": summary["weak_question_types"],
            "strong_question_types": summary["strong_question_types"],
            "mistake_summary": summary["mistake_summary"],
        }


def run_self_test() -> None:
    print("\nLearnerMemoryService self-test")
    print("=" * 80)

    service = LearnerMemoryService()

    learner_id = "demo_learner_001"

    sample_evaluations = [
        {
            "concept_id": "P1",
            "concept_name": "Variables",
            "domain": "Python",
            "question_type": "mcq",
            "score": 1.0,
            "correct": True,
            "mistake_type": None,
        },
        {
            "concept_id": "P1",
            "concept_name": "Variables",
            "domain": "Python",
            "question_type": "debug_task",
            "score": 0.0,
            "correct": False,
            "mistake_type": "debug_runtime_error",
        },
        {
            "concept_id": "P1",
            "concept_name": "Variables",
            "domain": "Python",
            "question_type": "output_prediction",
            "score": 0.3,
            "correct": False,
            "mistake_type": "wrong_output_prediction",
        },
    ]

    print("\nUpdating memory from sample evaluations...")
    for result in sample_evaluations:
        memory = service.update_memory_from_evaluation(
            learner_id=learner_id,
            evaluation_result=result,
            teaching_view="code_view",
            difficulty="easy",
        )

    print("\nCurrent memory:")
    print(json.dumps(memory, indent=2, ensure_ascii=False))

    print("\nComeback summary: minutes")
    print(json.dumps(service.build_comeback_summary(learner_id, force_category="minutes"), indent=2, ensure_ascii=False))

    print("\nComeback summary: hours")
    print(json.dumps(service.build_comeback_summary(learner_id, force_category="hours"), indent=2, ensure_ascii=False))

    print("\nComeback summary: days")
    print(json.dumps(service.build_comeback_summary(learner_id, force_category="days"), indent=2, ensure_ascii=False))

    print("\nComeback summary: long_gap")
    print(json.dumps(service.build_comeback_summary(learner_id, force_category="long_gap"), indent=2, ensure_ascii=False))

    print("\nRevision packet")
    print(json.dumps(service.recommend_revision_packet(learner_id), indent=2, ensure_ascii=False))

    print("\nSelf-test complete.")


if __name__ == "__main__":
    run_self_test()