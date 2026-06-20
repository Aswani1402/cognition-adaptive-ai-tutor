from src.concept_resource_loader import load_concept_resources
from src.tutor_lm_service import DOUBT_TASK_TYPES, FEEDBACK_TASK_TYPES, HINT_TASK_TYPES, TutorLMService


def main() -> None:
    service = TutorLMService()
    concept = next(c for c in load_concept_resources() if c["domain"] == "Python" and c["concept_id"] == "P1")
    failures = []
    for task in HINT_TASK_TYPES:
        result = service.generate_task(task, concept, question_type="debug")
        if not result["format_valid"] or not all(result["output"].get(field) for field in ["hint_type", "hint", "why_this_helps", "next_step"]):
            failures.append(task)
    for task in FEEDBACK_TASK_TYPES:
        result = service.generate_task(task, concept)
        if not result["format_valid"] or not all(result["output"].get(field) for field in ["feedback_type", "message", "correction", "next_step"]):
            failures.append(task)
    for task in DOUBT_TASK_TYPES:
        result = service.generate_task(task, concept)
        if not result["format_valid"] or not all(result["output"].get(field) for field in ["answer", "example", "source_context_summary", "follow_up_check", "next_step"]):
            failures.append(task)
    print(f"hint_tasks_checked: {len(HINT_TASK_TYPES)}")
    print(f"feedback_tasks_checked: {len(FEEDBACK_TASK_TYPES)}")
    print(f"doubt_tasks_checked: {len(DOUBT_TASK_TYPES)}")
    print(f"failures: {failures}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
