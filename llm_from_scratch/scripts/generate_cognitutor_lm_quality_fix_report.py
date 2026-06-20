import json
from collections import Counter
from pathlib import Path

from src.tutor_lm_service import TutorLMService


ROOT_DIR = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT_DIR / "outputs" / "final_reports" / "cognitutor_lm_quality_fix_report.json"
OUT_MD = ROOT_DIR / "outputs" / "final_reports" / "cognitutor_lm_quality_fix_report.md"

REQUIRED_TYPES = {
    "mcq",
    "fill_in_the_blank",
    "true_or_false",
    "debug_task",
    "output_prediction",
    "syntax_completion",
    "coding_prompt",
    "transfer_question",
    "challenge_question",
    "explanation_check",
}


def main() -> None:
    service = TutorLMService()
    concepts = service.list_concepts()
    issues = []
    teaching_lengths = []
    type_counts = Counter()

    for concept in concepts:
        domain = concept["domain"]
        concept_id = concept["concept_id"]
        concept_name = concept["concept_name"]
        for view in ["definition_view", "code_view", "misconception_view", "revision_summary_view", "flashcard_view", "mindmap_view"]:
            teaching = service.get_teaching_view(concept_id=concept_id, domain=domain, artifact_type=view)
            text = str(teaching.get("teaching", ""))
            teaching_lengths.append(len(text.split()))
            if teaching.get("status") != "success":
                issues.append({"concept_id": concept_id, "view": view, "issue": "teaching_not_found"})
            if len(text.split()) < 20:
                issues.append({"concept_id": concept_id, "view": view, "issue": "teaching_too_short"})
            if view == "flashcard_view" and "current concept" in text.lower():
                issues.append({"concept_id": concept_id, "view": view, "issue": "generic_flashcard"})
            if view == "mindmap_view" and ("placeholder content" in text.lower() or "[]" in text):
                issues.append({"concept_id": concept_id, "view": view, "issue": "placeholder_mindmap"})

        assessment = service.get_assessment_questions(concept_id=concept_id, domain=domain, num_questions=10, shuffle=False)
        qtypes = {q.get("question_type") for q in assessment.get("questions", [])}
        type_counts.update(qtypes)
        missing = sorted(REQUIRED_TYPES - qtypes)
        if missing:
            issues.append({"concept_id": concept_id, "concept_name": concept_name, "issue": "missing_assessment_types", "missing": missing})
        signatures = [service._question_signature(q) for q in assessment.get("questions", [])]
        if len(signatures) != len(set(signatures)):
            issues.append({"concept_id": concept_id, "concept_name": concept_name, "issue": "duplicate_session_questions"})

    report = {
        "status": "PASS" if not issues else "WARN",
        "concept_count": len(concepts),
        "avg_teaching_words": round(sum(teaching_lengths) / len(teaching_lengths), 2) if teaching_lengths else 0,
        "required_assessment_types": sorted(REQUIRED_TYPES),
        "observed_assessment_type_counts": dict(type_counts),
        "issue_count": len(issues),
        "issues": issues[:100],
        "improvements": [
            "Teaching responses are enriched from concept_resources.",
            "Flashcard and mindmap views are rebuilt as real structured content.",
            "Assessment selection is deduplicated and supplemented across 10 task types.",
            "Answer evaluation returns correct answer, explanation, mistake type, and next step.",
            "Session packets include guided hints, feedback templates, and revision summaries.",
        ],
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(
        "# CogniTutorLM Quality Fix Report\n\n"
        + "\n".join(f"- {k}: {v}" for k, v in report.items() if k != "issues")
        + "\n\n## Issues\n"
        + ("\n".join(f"- {item}" for item in report["issues"]) if report["issues"] else "- None")
        + "\n",
        encoding="utf-8",
    )
    print(f"status: {report['status']}")
    print(f"issue_count: {report['issue_count']}")
    print(f"report_json: {OUT_JSON}")


if __name__ == "__main__":
    main()
