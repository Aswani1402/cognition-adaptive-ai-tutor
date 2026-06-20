from tutor.system.run_integrated_tutor_once import run_integrated_tutor_once


def main():
    output = run_integrated_tutor_once(learner_id="14")

    assessment = output.get("assessment", {})
    demo_summary = output.get("demo_summary", {})
    questions = assessment.get("questions", [])

    print("\nFRONTEND ASSESSMENT OUTPUT AUDIT")

    print("Pipeline status:", output.get("status"))
    print("Assessment status:", assessment.get("status"))
    print("Concept:", assessment.get("concept_id"), "/", assessment.get("concept_name"))
    print("Difficulty:", assessment.get("difficulty"))
    print("Question count:", assessment.get("question_count"))

    print("\nSUMMARY")
    print("Teaching view:", demo_summary.get("teaching_view"))
    print("Assessment types:", demo_summary.get("assessment_types"))
    print("Assessment frontend ready:", demo_summary.get("assessment_frontend_ready"))
    print("Assessment frontend components:", demo_summary.get("assessment_frontend_components"))

    print("\nQUESTION DETAILS")
    for idx, question in enumerate(questions, start=1):
        metadata = question.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}

        print(
            {
                "index": idx,
                "question_id": question.get("question_id"),
                "question_type": question.get("question_type"),
                "assessment_type": question.get("assessment_type"),
                "frontend_component": question.get("frontend_component"),
                "render_mode": metadata.get("render_mode"),
            }
        )

    print("\nFRONTEND ASSESSMENT PAYLOAD CHECKS")

    checks = {
        "pipeline_success": output.get("status") == "success",
        "assessment_success": assessment.get("status") == "success",
        "frontend_ready_true": assessment.get("frontend_ready") is True,
        "question_count_matches": assessment.get("question_count") == len(questions),
        "questions_exist": len(questions) > 0,
        "components_used_exists": bool(assessment.get("frontend_components_used")),
        "supported_question_types_exists": bool(assessment.get("supported_question_types")),
    }

    for idx, question in enumerate(questions, start=1):
        prefix = f"question_{idx}"

        metadata = question.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}

        question_type = question.get("question_type")

        checks[f"{prefix}_has_question_type"] = bool(question.get("question_type"))
        checks[f"{prefix}_has_assessment_type"] = bool(question.get("assessment_type"))
        checks[f"{prefix}_has_frontend_component"] = bool(question.get("frontend_component"))
        checks[f"{prefix}_has_prompt"] = bool(question.get("prompt"))
        checks[f"{prefix}_has_expected_answer"] = question.get("expected_answer") is not None
        checks[f"{prefix}_has_render_mode"] = bool(metadata.get("render_mode"))

        if question_type == "debug":
            checks[f"{prefix}_debug_has_buggy_code"] = bool(metadata.get("buggy_code"))
            checks[f"{prefix}_debug_has_bug_category_or_type"] = bool(
                metadata.get("bug_category") or metadata.get("bug_type")
            )

        if question_type == "output_prediction":
            checks[f"{prefix}_output_prediction_has_code"] = bool(metadata.get("code"))

        if question_type == "mcq":
            checks[f"{prefix}_mcq_has_options"] = bool(question.get("options"))
            checks[f"{prefix}_mcq_has_correct_index"] = question.get("correct_option_index") is not None

    failed = []

    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")
        if not passed:
            failed.append(name)

    if failed:
        print("\nSTATUS: failed")
        print("FAILED CHECKS:", failed)
        return

    print("\nSTATUS: success")
    print("MODULE: FrontendAssessmentOutputAudit")
    print("Frontend assessment output is ready for UI integration.")


if __name__ == "__main__":
    main()