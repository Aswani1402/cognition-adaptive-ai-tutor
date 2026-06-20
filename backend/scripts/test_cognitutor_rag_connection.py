from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COGNI = ROOT / "CogniTutor_LM_from_scratch"


def main() -> None:
    required = [
        COGNI / "src" / "cognitutor_lm_api_service.py",
        COGNI / "src" / "rag_connector.py",
        COGNI / "src" / "tutor_lm_service.py",
        COGNI / "outputs" / "question_bank",
        COGNI / "outputs" / "rag_connector",
        COGNI / "outputs" / "rag_grounded_generation",
        COGNI / "outputs" / "learning_packets",
    ]
    missing = [str(path) for path in required if not path.exists()]
    assert not missing, f"Missing CogniTutorLM/RAG assets: {missing}"

    rag_text = (COGNI / "src" / "rag_connector.py").read_text(encoding="utf-8")
    service_text = (COGNI / "src" / "cognitutor_lm_api_service.py").read_text(encoding="utf-8")
    assert "build_rag_concept_resource" in rag_text
    assert "get_website_session_packet" in service_text
    assert "rag_grounding_status" in service_text
    print("cognitutor rag connection test success")


if __name__ == "__main__":
    main()
