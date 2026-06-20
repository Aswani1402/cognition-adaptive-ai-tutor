from statistics import mean

from scripts.pretrained_track_utils import REPO_ROOT, write_json, write_md
from src.pretrained_finetuned_inference import generate_tutor_task, load_model
from src.pretrained_output_validator import validate_task_output


TASKS = [
    ("explanation", "Python", "Python Variables", "easy"),
    ("mcq", "Python", "Python Variables", "easy"),
    ("debug_task", "Python", "Python Variables", "medium"),
    ("output_prediction", "Python", "Python Variables", "medium"),
    ("flashcard", "Python", "Python Variables", "easy"),
    ("mindmap", "Python", "Python Variables", "medium"),
    ("hint", "Python", "Python Variables", "medium"),
    ("feedback", "Python", "Python Variables", "medium"),
    ("doubt_answer", "SQL", "SQL JOIN Operations", "medium"),
    ("revision_summary", "Data Structures", "Data Structures Trees", "hard"),
]


def _checks(task_type, domain, concept, result):
    text = (result.get("raw_output") or "").strip()
    validation = validate_task_output(task_type, text, concept, domain)
    lowered = text.lower()
    return {
        "non_empty": bool(text),
        "concept_match": any(term.lower() in lowered for term in concept.split() if len(term) > 2),
        "domain_match": domain.lower().split()[0] in lowered,
        "task_type_match": task_type.replace("_", " ") in lowered or task_type.split("_")[0] in lowered,
        "format_valid": validation["valid"],
        "repetition_problem": any("repeated" in issue for issue in validation["issues"]),
        "frontend_renderable": bool(text) and len(text) < 12000,
        "quality_score": validation["score"],
        "validator": validation,
    }


def main() -> None:
    load_result = load_model()
    rows = []
    if load_result["status"] != "success":
        status = "WARN"
        reason = load_result.get("error") or "model did not load"
        for task_type, domain, concept, difficulty in TASKS:
            rows.append(
                {
                    "task_type": task_type,
                    "domain": domain,
                    "concept_name": concept,
                    "difficulty": difficulty,
                    "generation": {
                        "status": "warn",
                        "source": "pretrained_finetuning_track",
                        "model_loaded": False,
                        "error": reason,
                    },
                    "checks": {
                        "non_empty": False,
                        "concept_match": False,
                        "domain_match": False,
                        "task_type_match": False,
                        "format_valid": False,
                        "repetition_problem": False,
                        "frontend_renderable": False,
                        "quality_score": 0.0,
                    },
                }
            )
    else:
        reason = None
        for task_type, domain, concept, difficulty in TASKS:
            result = generate_tutor_task(task_type, domain, concept, difficulty)
            checks = _checks(task_type, domain, concept, result)
            rows.append(
                {
                    "task_type": task_type,
                    "domain": domain,
                    "concept_name": concept,
                    "difficulty": difficulty,
                    "generation": result,
                    "checks": checks,
                }
            )
        usable = [row for row in rows if row["generation"].get("status") == "success" and row["checks"]["format_valid"]]
        status = "PASS" if len(usable) == len(rows) else ("WARN" if usable else "FAIL")
        reason = "all outputs passed validation" if status == "PASS" else "one or more outputs failed validation"
    scores = [row["checks"]["quality_score"] for row in rows]
    data = {
        "status": status,
        "reason": reason,
        "model_load": load_result,
        "task_count": len(rows),
        "valid_count": sum(1 for row in rows if row["checks"]["format_valid"]),
        "average_quality_score": round(mean(scores), 3) if scores else 0.0,
        "results": rows,
    }
    write_json(REPO_ROOT / "outputs/evaluation/pretrained_finetuned_generation_test.json", data)
    write_md(
        REPO_ROOT / "outputs/evaluation/pretrained_finetuned_generation_test.md",
        "Pretrained Fine-Tuned Generation Test",
        {
            "Status": status,
            "Reason": reason,
            "Model Load": load_result,
            "Task Summary": {
                "task_count": data["task_count"],
                "valid_count": data["valid_count"],
                "average_quality_score": data["average_quality_score"],
            },
            "Per Task": [
                f"{row['task_type']} / {row['concept_name']}: status={row['generation'].get('status')} score={row['checks']['quality_score']} valid={row['checks']['format_valid']}"
                for row in rows
            ],
        },
    )
    print(status, "generation test saved")


if __name__ == "__main__":
    main()

