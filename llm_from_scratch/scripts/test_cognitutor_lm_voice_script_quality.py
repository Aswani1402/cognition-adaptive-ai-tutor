from src.concept_resource_loader import load_concept_resources
from src.tutor_lm_service import TutorLMService, VOICE_TASK_TYPES


def main() -> None:
    service = TutorLMService()
    concept = next(c for c in load_concept_resources() if c["domain"] == "Python" and c["concept_id"] == "P1")
    failures = []
    for task in VOICE_TASK_TYPES:
        result = service.generate_task(task, concept)
        output = result["output"]
        if not result["format_valid"] or output.get("voice_ready") is not True:
            failures.append(task)
        if len(output.get("script", "").split()) < 35:
            failures.append(f"{task}:short_script")
        if "audio" in output or "tts" in output:
            failures.append(f"{task}:contains_audio_tts")
    print(f"voice_tasks_checked: {len(VOICE_TASK_TYPES)}")
    print(f"failures: {failures}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
