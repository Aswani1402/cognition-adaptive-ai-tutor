from statistics import mean

from scripts.pretrained_track_utils import COGNITUTOR_ROOT, REPO_ROOT, read_json, write_csv, write_json, write_md


def _pretrained_summary():
    gen = read_json(REPO_ROOT / "outputs/evaluation/pretrained_finetuned_generation_test.json") or {}
    artifact = read_json(REPO_ROOT / "outputs/inspection/pretrained_model_artifact_check.json") or {}
    rows = gen.get("results") or []
    return {
        "track": "pretrained fine-tuning track",
        "runnable_status": artifact.get("runtime_status") or gen.get("status") or "UNKNOWN",
        "model_loaded": bool((gen.get("model_load") or {}).get("model_loaded")),
        "task_coverage": len(rows),
        "valid_output_rate": round((gen.get("valid_count", 0) / len(rows)), 3) if rows else 0.0,
        "format_validity": gen.get("valid_count", 0),
        "concept_match": sum(1 for row in rows if row.get("checks", {}).get("concept_match")),
        "grounding_status": "not RAG-grounded",
        "repetition_rate": round(sum(1 for row in rows if row.get("checks", {}).get("repetition_problem")) / len(rows), 3) if rows else 0.0,
        "frontend_renderability": sum(1 for row in rows if row.get("checks", {}).get("frontend_renderable")),
        "fallback_required": artifact.get("status") != "PASS",
        "average_quality_score": gen.get("average_quality_score", 0.0),
        "runtime_safety": "local-only wrapper; remote download disabled",
        "integration_readiness": "comparison-only" if artifact.get("status") != "PASS" or gen.get("status") != "PASS" else "candidate after backend review",
        "reason": artifact.get("reason") or gen.get("reason"),
    }


def _cognitutor_summary():
    output = read_json(COGNITUTOR_ROOT / "outputs/model_generated/structured_model_generated_all_tasks.json")
    quality = read_json(COGNITUTOR_ROOT / "outputs/final_reports/all_89_task_generation_quality_scan.json")
    validation = read_json(COGNITUTOR_ROOT / "outputs/final_reports/full_product_generator_validation.json")
    rag = read_json(COGNITUTOR_ROOT / "outputs/service_tests/rag_cognitutor_connection_test.json")
    task_count = len(output) if isinstance(output, list) else (len(output.keys()) if isinstance(output, dict) else 0)
    return {
        "track": "CogniTutorLM from scratch / guarded product generator",
        "runnable_status": "PASS" if output else "WARN",
        "model_loaded": bool(output),
        "task_coverage": task_count,
        "valid_output_rate": "see source validation report" if quality or validation else 0.0,
        "format_validity": "see source validation report" if validation else "unknown",
        "concept_match": "see source quality report" if quality else "unknown",
        "grounding_status": "RAG evidence available" if rag else "RAG evidence missing",
        "repetition_rate": "see source quality report" if quality else "unknown",
        "frontend_renderability": "see source validation report" if validation else "unknown",
        "fallback_required": False,
        "average_quality_score": "see source quality report" if quality else "unknown",
        "runtime_safety": "guarded generator evidence loaded from existing reports",
        "integration_readiness": "existing product path; not modified",
        "reason": "loaded comparison evidence" if output else "structured output file missing",
    }


def _static_track(track, available=False, grounding="not inspected"):
    return {
        "track": track,
        "runnable_status": "AVAILABLE" if available else "WARN/NOT_FOUND",
        "model_loaded": False,
        "task_coverage": 0,
        "valid_output_rate": 0.0,
        "format_validity": "not run by this comparison",
        "concept_match": "not run by this comparison",
        "grounding_status": grounding,
        "repetition_rate": "not run",
        "frontend_renderability": "not run",
        "fallback_required": True,
        "average_quality_score": 0.0,
        "runtime_safety": "comparison-only metadata",
        "integration_readiness": "not changed",
        "reason": "no local comparison runner found in pretrained fine-tuning track",
    }


def main() -> None:
    rows = [
        _static_track("template/rule baseline"),
        _static_track("concept-resource fallback", grounding="concept DB files present" if (REPO_ROOT / "external/core_data").exists() else "not found"),
        _static_track("RAG-grounded service", grounding="external evidence only"),
        _cognitutor_summary(),
        _pretrained_summary(),
    ]
    pretrained = rows[-1]
    status = "PASS" if pretrained["runnable_status"] else "WARN"
    data = {
        "status": status,
        "pretrained_track_status": "PASS" if pretrained["model_loaded"] else "WARN/PENDING",
        "reason": pretrained["reason"],
        "comparison_rows": rows,
    }
    write_json(REPO_ROOT / "outputs/evaluation/generation_track_comparison.json", data)
    write_csv(REPO_ROOT / "outputs/evaluation/generation_track_comparison.csv", rows)
    write_md(
        REPO_ROOT / "outputs/evaluation/generation_track_comparison.md",
        "Generation Track Comparison",
        {
            "Status": status,
            "Pretrained Track Status": data["pretrained_track_status"],
            "Reason": data["reason"],
            "Tracks": [f"{row['track']}: {row['runnable_status']} integration={row['integration_readiness']}" for row in rows],
        },
    )
    print(status, "comparison saved")


if __name__ == "__main__":
    main()

