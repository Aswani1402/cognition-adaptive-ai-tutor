from __future__ import annotations

from scripts.migration.add_learner_memory_tables import run_migration
from tutor.memory.production_learner_memory_store import ProductionLearnerMemoryStore


LEARNER_ID = "demo_memory_learner_001"


def _assert_fields(payload: dict, fields: list[str], label: str) -> None:
    missing = [field for field in fields if field not in payload]
    assert not missing, f"{label} missing fields: {missing}"


def main() -> None:
    migration_report = run_migration()
    assert migration_report["status"] == "success"

    store = ProductionLearnerMemoryStore()

    session = store.log_session(
        learner_id=LEARNER_ID,
        session_id="session_memory_demo_001",
        concept_id="py_variables",
        concept_name="Variables",
        domain="Python",
        selected_view="definition_view",
        difficulty="easy",
        mode="production_memory_test",
        metadata={"source": "test_production_learner_memory_store"},
    )
    mistake = store.log_mistake(
        learner_id=LEARNER_ID,
        concept_id="py_variables",
        concept_name="Variables",
        domain="Python",
        question_id="q_variables_debug_001",
        question_type="debug_task",
        mistake_type="syntax_misunderstanding",
        score=0.4,
        feedback="Variable names cannot start with a number.",
        metadata={"attempt": 1},
    )
    doubt = store.log_doubt(
        learner_id=LEARNER_ID,
        concept_id="py_variables",
        concept_name="Variables",
        domain="Python",
        doubt_text="Why is 2score invalid?",
        doubt_type="syntax_doubt",
        answer_summary="Python variable names cannot start with a digit.",
        rag_context_used=True,
        metadata={"retrieved_sections": ["naming_rules"]},
    )
    revision = store.log_revision(
        learner_id=LEARNER_ID,
        concept_id="py_variables",
        concept_name="Variables",
        domain="Python",
        revision_type="returning_learner",
        recommended_views=["definition_view", "simple_example_view"],
        weak_question_types=["debug_task", "syntax_completion"],
        metadata={"reason": "syntax weakness"},
    )
    progress = store.upsert_view_progress(
        learner_id=LEARNER_ID,
        concept_id="py_variables",
        concept_name="Variables",
        domain="Python",
        view_name="definition_view",
        status="seen",
        score=0.75,
        metadata={"selected_by": "test"},
    )
    state_update = store.update_memory_state(
        learner_id=LEARNER_ID,
        last_concept_id="py_variables",
        last_concept_name="Variables",
        last_domain="Python",
        last_teaching_view="definition_view",
        last_difficulty="easy",
        weak_concepts=[{"concept_id": "py_variables", "concept_name": "Variables"}],
        weak_question_types=["debug_task", "syntax_completion"],
        strong_question_types=["mcq"],
        mistake_summary={"syntax_misunderstanding": 1},
        recommended_revision_views=["definition_view", "simple_example_view"],
        next_recommended_action="show_revision_then_debug_practice",
        recent_scores=[0.4, 0.75],
    )

    memory_state = store.get_memory_state(LEARNER_ID)
    returning_context = store.get_returning_learner_context(LEARNER_ID)
    view_progress = store.get_view_progress(LEARNER_ID, "py_variables")

    for result in [session, mistake, doubt, revision, progress, state_update]:
        assert result["status"] == "success", result

    _assert_fields(
        memory_state,
        [
            "status",
            "learner_id",
            "last_active_at",
            "last_concept_id",
            "last_concept_name",
            "last_domain",
            "last_teaching_view",
            "last_difficulty",
            "weak_concepts",
            "weak_question_types",
            "strong_question_types",
            "mistake_summary",
            "recommended_revision_views",
            "next_recommended_action",
            "recent_scores",
            "updated_at",
        ],
        "memory_state",
    )
    _assert_fields(
        returning_context,
        [
            "status",
            "learner_id",
            "returning_learner_available",
            "memory_state",
            "recent_sessions",
            "recent_mistakes",
            "recent_doubts",
            "recent_revisions",
            "view_progress",
            "recommended_revision_views",
            "weak_concepts",
            "weak_question_types",
            "next_recommended_action",
        ],
        "returning_context",
    )
    assert memory_state["weak_concepts"]
    assert memory_state["weak_question_types"]
    assert memory_state["strong_question_types"]
    assert memory_state["mistake_summary"]
    assert memory_state["recommended_revision_views"]
    assert view_progress
    assert returning_context["returning_learner_available"] is True
    assert returning_context["recent_sessions"]
    assert returning_context["recent_mistakes"]
    assert returning_context["recent_doubts"]
    assert returning_context["recent_revisions"]

    print("production learner memory store test PASS")


if __name__ == "__main__":
    main()
