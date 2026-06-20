import json
from pathlib import Path

from tutor.generation.cognitutor_lm_connector import get_cognitutor_live_guarded_packet

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "evaluation_outputs" / "json" / "cognitutor_live_guarded_connector_report.json"
OUT_MD = ROOT / "evaluation_outputs" / "reports" / "cognitutor_live_guarded_connector_report.md"


def main():
    result = get_cognitutor_live_guarded_packet(
        domain="Python",
        concept="Variables",
        learner_id="backend_live_guarded_demo",
        difficulty="easy",
        teaching_view="definition_view",
    )
    live = result.get("cognitutor_lm_live_guarded_output") or {}
    teaching_content = result.get("teaching_content") or live.get("final_output")
    assessments = result.get("aligned_assessments") or []
    required_present = all(
        [
            live.get("final_source"),
            (live.get("model_attempt") or {}).get("model_attempted") is not None,
            live.get("fallback_used") is not None,
            live.get("learner_facing_safe") is True,
            bool(teaching_content),
            isinstance(assessments, list),
        ]
    )
    report = {
        "status": "PASS" if result.get("status") == "success" and required_present else "WARN",
        "backend_connector_available": True,
        "generation_mode": result.get("generation_mode"),
        "final_source": live.get("final_source"),
        "model_attempted": (live.get("model_attempt") or {}).get("model_attempted"),
        "model_loaded": (live.get("model_attempt") or {}).get("model_loaded"),
        "model_valid": (live.get("model_attempt") or {}).get("model_valid"),
        "fallback_used": live.get("fallback_used"),
        "rag_used": (live.get("rag_context") or {}).get("rag_used"),
        "learner_facing_safe": live.get("learner_facing_safe"),
        "frontend_ready": live.get("frontend_ready"),
        "teaching_content_exists": bool(teaching_content),
        "assessment_count": len(assessments),
        "result_preview": {
            "domain": result.get("domain"),
            "concept_id": result.get("concept_id"),
            "concept_name": result.get("concept_name"),
        },
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = ["# CogniTutor Live Guarded Connector Report", ""]
    for key, value in report.items():
        if key != "result_preview":
            lines.append(f"- {key}: {value}")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
