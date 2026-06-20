from src.concept_resource_loader import load_concept_resources
from src.tutor_lm_service import TEACHING_TASK_TYPES, TutorLMService


def main() -> None:
    service = TutorLMService()
    concept = next(c for c in load_concept_resources() if c["domain"] == "Python" and c["concept_id"] == "P1")
    failures = []
    for task in TEACHING_TASK_TYPES:
        result = service.generate_task(task, concept)
        output = result["output"]
        required = ["definition", "explanation", "example", "key_points", "common_mistake", "mini_check", "next_step"]
        if not result["format_valid"] or any(not output.get(field) for field in required):
            failures.append(task)
        if len(str(output.get("explanation", "")).split()) < 40:
            failures.append(f"{task}:short_explanation")
        if task == "code_view" and not all(output.get(field) for field in ["syntax", "simple_code", "output_explanation"]):
            failures.append("code_view_missing_code_fields")
        if task == "misconception_view" and not all(output.get(field) for field in ["wrong_idea", "correction", "corrected_example"]):
            failures.append("misconception_view_missing_fields")
        if task == "output_prediction_view" and not all(output.get(field) for field in ["code", "line_by_line_trace", "final_output"]):
            failures.append("output_prediction_view_missing_trace")
    print(f"teaching_tasks_checked: {len(TEACHING_TASK_TYPES)}")
    print(f"failures: {failures}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
