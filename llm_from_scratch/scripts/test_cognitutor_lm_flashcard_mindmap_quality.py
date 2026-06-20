from src.concept_resource_loader import load_concept_resources
from src.tutor_lm_service import FLASHCARD_TASK_TYPES, MINDMAP_TASK_TYPES, TutorLMService


def main() -> None:
    service = TutorLMService()
    concept = next(c for c in load_concept_resources() if c["domain"] == "Python" and c["concept_id"] == "P1")
    failures = []
    for task in FLASHCARD_TASK_TYPES:
        result = service.generate_task(task, concept)
        cards = result["output"].get("cards", [])
        if not result["format_valid"] or len(cards) < 5:
            failures.append(task)
        for card in cards:
            if not all(card.get(field) for field in ["card_type", "front", "back", "explanation", "difficulty"]):
                failures.append(f"{task}:bad_card")
    for task in MINDMAP_TASK_TYPES:
        result = service.generate_task(task, concept)
        branches = result["output"].get("branches", [])
        labels = {b.get("label") for b in branches}
        expected = {"Definition", "Examples", "Key Points", "Common Mistakes", "Real-world Use", "Related Concept"}
        if not result["format_valid"] or not expected.issubset(labels):
            failures.append(task)
    print(f"flashcard_tasks_checked: {len(FLASHCARD_TASK_TYPES)}")
    print(f"mindmap_tasks_checked: {len(MINDMAP_TASK_TYPES)}")
    print(f"failures: {failures}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
