from src.concept_resource_loader import load_concept_resources
from src.tutor_lm_service import ASSESSMENT_TASK_TYPES, TutorLMService


def main() -> None:
    service = TutorLMService()
    concept = next(c for c in load_concept_resources() if c["domain"] == "Python" and c["concept_id"] == "P1")
    question_set = service.generate_assessment_question_set(concept)
    questions = question_set["questions"]
    failures = []
    prompts = [q.get("prompt", "") for q in questions]
    if len(prompts) != len(set(prompts)):
        failures.append("duplicate_prompts")
    if len([q for q in questions if q.get("task_type") == "mcq" or q.get("question_id", "").startswith("P1_mcq")]) < 2:
        failures.append("less_than_2_mcq")
    for task in ASSESSMENT_TASK_TYPES:
        result = service.generate_task(task, concept)
        output = result["output"]
        if not result["format_valid"]:
            failures.append(f"{task}:invalid")
        for field in ["question_id", "task_type", "question_type", "difficulty", "prompt", "correct_answer", "explanation", "hint"]:
            if output.get(field) in ("", None, []):
                failures.append(f"{task}:missing_{field}")
        if task == "mcq" and (len(output.get("options", [])) != 4 or output.get("correct_answer") not in output.get("options", [])):
            failures.append("mcq_options_or_answer")
    print(f"assessment_tasks_checked: {len(ASSESSMENT_TASK_TYPES)}")
    print(f"question_set_size: {len(questions)}")
    print(f"failures: {failures}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
