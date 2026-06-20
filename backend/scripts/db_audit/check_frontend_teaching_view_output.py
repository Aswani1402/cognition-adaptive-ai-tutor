from tutor.system.run_integrated_tutor_once import run_integrated_tutor_once


def main():
    output = run_integrated_tutor_once(learner_id="14")

    frontend_output = output.get("frontend_teaching_view_output", {})
    demo_summary = output.get("demo_summary", {})

    print("\nFRONTEND TEACHING VIEW OUTPUT AUDIT")

    print("Pipeline status:", output.get("status"))
    print("Adapter status:", frontend_output.get("status"))
    print("Module:", frontend_output.get("module"))

    print("\nSUMMARY")
    print("Final concept:", demo_summary.get("final_concept"))
    print("Final concept name:", demo_summary.get("final_concept_name"))
    print("Teaching view:", demo_summary.get("teaching_view"))
    print("Frontend selected view:", demo_summary.get("frontend_selected_view"))
    print("Frontend display type:", demo_summary.get("frontend_selected_display_type"))
    print("Assessment types:", demo_summary.get("assessment_types"))

    selected_view = frontend_output.get("selected_view", {})
    flashcards = frontend_output.get("flashcards", [])
    mindmap = frontend_output.get("mindmap", {})
    debug_task = frontend_output.get("debug_task", {})

    print("\nSELECTED VIEW")
    print("Selected teaching view:", frontend_output.get("selected_teaching_view"))
    print("View type:", selected_view.get("view_type"))
    print("Display type:", selected_view.get("display_type"))
    print("Title:", selected_view.get("title"))

    print("\nFRONTEND PAYLOAD CHECKS")
    checks = {
        "pipeline_success": output.get("status") == "success",
        "adapter_success": frontend_output.get("status") == "success",
        "selected_view_exists": isinstance(selected_view, dict) and bool(selected_view),
        "display_type_exists": bool(selected_view.get("display_type")),
        "concept_name_exists": bool(frontend_output.get("concept_name")),
        "flashcards_exist": isinstance(flashcards, list) and len(flashcards) > 0,
        "mindmap_exists": isinstance(mindmap, dict) and bool(mindmap.get("center")),
        "frontend_rule_exists": bool(frontend_output.get("frontend_rule")),
    }

    selected_type = frontend_output.get("selected_teaching_view")

    if selected_type == "debug_view":
        checks["debug_task_exists"] = isinstance(debug_task, dict) and bool(debug_task.get("buggy_code"))
        checks["debug_expected_fix_exists"] = isinstance(debug_task, dict) and bool(debug_task.get("expected_fix"))

    if selected_type == "code_view":
        checks["code_blocks_exist"] = bool(selected_view.get("code_blocks"))

    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    failed = [name for name, passed in checks.items() if not passed]

    if failed:
        print("\nSTATUS: failed")
        print("FAILED CHECKS:", failed)
        return

    print("\nSTATUS: success")
    print("MODULE: FrontendTeachingViewOutputAudit")
    print("Frontend teaching view output is ready for UI integration.")


if __name__ == "__main__":
    main()